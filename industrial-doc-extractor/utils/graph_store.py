

from motor.motor_asyncio import AsyncIOMotorClient
from config import get_settings

_client: AsyncIOMotorClient | None = None


def get_db():
    global _client
    s = get_settings()
    if _client is None:
        _client = AsyncIOMotorClient(s.MONGODB_URI)
    return _client[s.MONGODB_DB]


# ── Node operations ────────────────────────────────────────────────

async def upsert_node(node: dict) -> str:
    """Insert or replace a graph node. Returns node_id."""
    db = get_db()
    await db.nodes.replace_one(
        {"node_id": node["node_id"]},
        node,
        upsert=True,
    )
    return node["node_id"]


async def get_node(node_id: str) -> dict | None:
    return await get_db().nodes.find_one({"node_id": node_id}, {"_id": 0})


async def get_nodes_by_extraction(extraction_id: str) -> list[dict]:
    cursor = get_db().nodes.find(
        {"extraction_id": extraction_id, "node_type": "page"},
        {"_id": 0},
    ).sort("page_number", 1)
    return await cursor.to_list(length=1000)


async def get_nodes_by_doc_type(doc_type: str, limit: int = 100) -> list[dict]:
    cursor = get_db().nodes.find(
        {"meta.doc_type": {"$regex": doc_type, "$options": "i"}},
        {"_id": 0, "text": 0, "embedding": 0},  # exclude heavy fields for listing
    ).limit(limit)
    return await cursor.to_list(length=limit)


async def list_doc_types() -> list[str]:
    return await get_db().nodes.distinct("meta.doc_type")


# ── Edge operations ────────────────────────────────────────────────

async def create_edge(edge: dict) -> str:
    """Insert a directed graph edge. Returns inserted id as str."""
    db = get_db()
    result = await db.edges.insert_one(edge)
    return str(result.inserted_id)


async def get_edges_from(node_id: str) -> list[dict]:
    cursor = get_db().edges.find({"from_node_id": node_id}, {"_id": 0})
    return await cursor.to_list(length=500)


async def get_edges_to(node_id: str) -> list[dict]:
    cursor = get_db().edges.find({"to_node_id": node_id}, {"_id": 0})
    return await cursor.to_list(length=500)


async def get_neighbors(node_id: str) -> dict:
    """Return both outgoing and incoming edges for a node."""
    outgoing = await get_edges_from(node_id)
    incoming = await get_edges_to(node_id)
    return {"outgoing": outgoing, "incoming": incoming}


# ── Semantic similarity edges ──────────────────────────────────────

async def find_similar_nodes(
    embedding: list[float],
    threshold: float = 0.82,
    limit: int = 10,
    exclude_node_id: str = "",
) -> list[dict]:
    """
    Brute-force cosine similarity search across all page nodes.
    For production scale, replace with a vector index (e.g. MongoDB Atlas
    Vector Search or a dedicated vector DB).
    Returns nodes with similarity >= threshold, sorted descending.
    """
    from utils.embedding_client import cosine_similarity

    db = get_db()
    cursor = db.nodes.find(
        {"node_type": "page", "embedding": {"$exists": True, "$ne": []}},
        {"node_id": 1, "pdf_name": 1, "page_number": 1,
         "meta": 1, "embedding": 1, "_id": 0},
    )
    all_nodes = await cursor.to_list(length=5000)

    scored = []
    for node in all_nodes:
        if node.get("node_id") == exclude_node_id:
            continue
        sim = cosine_similarity(embedding, node.get("embedding", []))
        if sim >= threshold:
            scored.append({**node, "similarity": round(sim, 4), "embedding": None})

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:limit]


# ── Extraction summary ─────────────────────────────────────────────

async def store_extraction_summary(doc: dict) -> str:
    db = get_db()
    result = await db.extractions.insert_one(doc)
    return str(result.inserted_id)


async def list_extractions(limit: int = 20, skip: int = 0) -> list[dict]:
    cursor = (
        get_db()
        .extractions.find({}, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)
