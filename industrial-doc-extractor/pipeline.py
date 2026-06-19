"""
Industrial Document Pipeline Orchestrator
==========================================
Runs all 5 agents per page, generates embeddings, builds graph nodes and edges,
and stores everything in MongoDB using a property-graph model.

Graph model summary
-------------------
Nodes  (collection: nodes)
  - One node per PDF page
  - Stores full text, embedding vector, and all agent metadata

Edges  (collection: edges)
  - NEXT_PAGE          : auto-created between consecutive pages
  - SAME_EQUIPMENT     : pages sharing the same equipment tag
  - SEMANTICALLY_SIMILAR: pages with embedding cosine similarity >= 0.82
  - REFERENCES_PART    : SOP/WorkOrder page → Spare Part List page (via Agent 5 suggestion)
  - RELATED_PROCEDURE  : SOP ↔ SOP or WorkOrder ↔ WorkOrder
  - INSPECTION_OF      : Inspection/Calibration → equipment page
  - RISK_COVERS        : Risk Assessment → procedure/equipment page
  - BREAKDOWN_OF       : Breakdown Report → SOP or Technical Manual page
"""

import asyncio
import uuid
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from agents.agent1_doc_type_classifier import classify_doc_type
from agents.agent2_entity_extractor import extract_industrial_entities
from agents.agent3_criticality_assessor import assess_criticality
from agents.agent4_summary_generator import generate_technical_summary
from agents.agent5_metadata_decider import decide_metadata
from utils.embedding_client import embed_text, cosine_similarity
from utils.graph_store import (
    upsert_node,
    create_edge,
    get_nodes_by_extraction,
    find_similar_nodes,
)

_executor = ThreadPoolExecutor(max_workers=12)

SIMILARITY_THRESHOLD = 0.82  # minimum cosine similarity to create a SEMANTICALLY_SIMILAR edge


# ── Single page processing ─────────────────────────────────────────

async def process_page(
    pdf_name: str,
    extraction_id: str,
    page: dict,
) -> dict:
    loop = asyncio.get_event_loop()
    text = page["text"]
    page_num = page["page_number"]
    has_images = page.get("has_images", False)

    # Agents 1, 2, 3 — Bedrock (blocking), run concurrently in thread pool
    doc_type_fut = loop.run_in_executor(
        _executor, classify_doc_type, text, has_images
    )
    entities_fut = loop.run_in_executor(
        _executor, extract_industrial_entities, text
    )
    criticality_fut = loop.run_in_executor(
        _executor, assess_criticality, text
    )

    # Agent 4 — Ollama (async)
    summary_fut = generate_technical_summary(text)

    # Embedding — OpenAI (blocking), run in thread pool alongside agents
    embedding_fut = loop.run_in_executor(_executor, embed_text, text)

    doc_type, entities, criticality, summary, embedding = await asyncio.gather(
        doc_type_fut, entities_fut, criticality_fut, summary_fut, embedding_fut
    )

    # Agent 5 — final metadata decision (blocking)
    meta = await loop.run_in_executor(
        _executor, decide_metadata, doc_type, entities, criticality, summary, text
    )

    # Merge agent outputs into meta
    meta["entities"] = entities
    meta["criticality"] = criticality["criticality"]
    meta["hazard_level"] = criticality["hazard_level"]
    meta["action_required"] = criticality["action_required"]
    meta["urgency_keywords"] = criticality["urgency_keywords"]
    meta["summary"] = summary

    node_id = str(uuid.uuid4())
    node = {
        "node_id": node_id,
        "node_type": "page",
        "pdf_name": pdf_name,
        "extraction_id": extraction_id,
        "page_number": page_num,
        "char_count": page["char_count"],
        "has_images": has_images,
        "text": text,
        "embedding": embedding,
        "meta": meta,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await upsert_node(node)
    return node


# ── Edge builders ──────────────────────────────────────────────────

async def build_sequential_edges(nodes: list[dict]) -> None:
    """NEXT_PAGE edges between consecutive pages of the same PDF."""
    sorted_nodes = sorted(nodes, key=lambda n: n["page_number"])
    for i in range(len(sorted_nodes) - 1):
        await create_edge({
            "from_node_id": sorted_nodes[i]["node_id"],
            "to_node_id": sorted_nodes[i + 1]["node_id"],
            "relation": "NEXT_PAGE",
            "weight": 1.0,
            "meta": {"pdf_name": sorted_nodes[i]["pdf_name"]},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })


async def build_equipment_edges(nodes: list[dict]) -> None:
    """SAME_EQUIPMENT edges between pages sharing at least one equipment tag."""
    for i, node_a in enumerate(nodes):
        tags_a = set(node_a["meta"].get("entities", {}).get("equipment_tags", []))
        if not tags_a:
            continue
        for node_b in nodes[i + 1:]:
            tags_b = set(node_b["meta"].get("entities", {}).get("equipment_tags", []))
            shared = tags_a & tags_b
            if shared:
                await create_edge({
                    "from_node_id": node_a["node_id"],
                    "to_node_id": node_b["node_id"],
                    "relation": "SAME_EQUIPMENT",
                    "weight": len(shared) / max(len(tags_a), len(tags_b)),
                    "meta": {"shared_tags": list(shared)},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })


async def build_semantic_edges(nodes: list[dict]) -> None:
    """SEMANTICALLY_SIMILAR edges based on embedding cosine similarity."""
    for node in nodes:
        embedding = node.get("embedding", [])
        if not embedding:
            continue
        similar = await find_similar_nodes(
            embedding,
            threshold=SIMILARITY_THRESHOLD,
            limit=5,
            exclude_node_id=node["node_id"],
        )
        for sim_node in similar:
            await create_edge({
                "from_node_id": node["node_id"],
                "to_node_id": sim_node["node_id"],
                "relation": "SEMANTICALLY_SIMILAR",
                "weight": sim_node["similarity"],
                "meta": {
                    "doc_type_from": node["meta"].get("doc_type"),
                    "doc_type_to": sim_node["meta"].get("doc_type"),
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
            })


async def build_suggested_relation_edges(nodes: list[dict]) -> None:
    """
    Build edges for relationships suggested by Agent 5.
    Pairs pages whose doc_types are complementary based on the relation type.
    """
    relation_map = {
        "REFERENCES_PART":    (["SOP", "Work Order"], ["Spare Part List"]),
        "RELATED_PROCEDURE":  (["SOP", "Work Order"], ["SOP", "Work Order"]),
        "INSPECTION_OF":      (["Inspection Report", "Calibration Record"], ["Technical Manual", "SOP"]),
        "RISK_COVERS":        (["Risk Assessment"], ["SOP", "Work Order", "Technical Manual"]),
        "BREAKDOWN_OF":       (["Breakdown Report"], ["SOP", "Technical Manual"]),
    }

    for node_a in nodes:
        suggested = node_a["meta"].get("suggested_relations", [])
        doc_type_a = node_a["meta"].get("doc_type", "")

        for relation, (from_types, to_types) in relation_map.items():
            if relation not in suggested:
                continue
            if not any(ft.lower() in doc_type_a.lower() for ft in from_types):
                continue

            # Find candidate target nodes
            for node_b in nodes:
                if node_b["node_id"] == node_a["node_id"]:
                    continue
                doc_type_b = node_b["meta"].get("doc_type", "")
                if any(tt.lower() in doc_type_b.lower() for tt in to_types):
                    await create_edge({
                        "from_node_id": node_a["node_id"],
                        "to_node_id": node_b["node_id"],
                        "relation": relation,
                        "weight": node_a["meta"].get("confidence", 0.5),
                        "meta": {
                            "doc_type_from": doc_type_a,
                            "doc_type_to": doc_type_b,
                        },
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })


# ── Full PDF pipeline ──────────────────────────────────────────────

async def process_pdf(
    pdf_name: str,
    extraction_id: str,
    pages: list[dict],
) -> list[dict]:
    """
    1. Process all pages through 5 agents + embeddings (concurrent, max 5 at a time)
    2. Build graph edges: sequential, equipment, semantic, suggested relations
    3. Return list of processed page nodes
    """
    semaphore = asyncio.Semaphore(5)

    async def limited(page):
        async with semaphore:
            return await process_page(pdf_name, extraction_id, page)

    nodes = await asyncio.gather(*[limited(p) for p in pages])
    nodes = list(nodes)

    # Build all graph edges
    await asyncio.gather(
        build_sequential_edges(nodes),
        build_equipment_edges(nodes),
        build_suggested_relation_edges(nodes),
    )

    # Semantic edges require DB lookup — run after nodes are stored
    await build_semantic_edges(nodes)

    return nodes

