
import uuid
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi.responses import StreamingResponse
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
import asyncio
from utils.pdf_extractor import extract_pages
from utils.embedding_client import embed_text
from utils.graph_store import (
    get_node,
    get_nodes_by_extraction,
    get_nodes_by_doc_type,
    get_neighbors,
    get_edges_from,
    list_doc_types,
    store_extraction_summary,
    list_extractions,
    find_similar_nodes,
    get_db,
)
from pipeline import process_pdf

app = FastAPI(
    title="Industrial Document Extractor",
    description=(
        "Multi-agent pipeline for industrial PDFs (SOPs, Breakdown Reports, "
        "Electrical Diagrams, Spare Part Lists, etc.). "
        "Classifies pages via AWS Bedrock Claude Sonnet 4.6, generates embeddings "
        "with OpenAI text-embedding-ada-002, and stores a property-graph in MongoDB."
    ),
    version="2.0.0",
)


# ── Health ──────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# ── Extract ─────────────────────────────────────────────────────────

@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    """
    Upload an industrial PDF. The pipeline will:
    1. Extract text page-by-page (PyMuPDF)
    2. Run 5 AI agents per page (AWS Bedrock + Ollama)
    3. Generate text embeddings (OpenAI text-embedding-ada-002)
    4. Build a property-graph in MongoDB (nodes + edges)
    5. Stream immediate updates and return final extraction summary statistics.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        pages = extract_pages(pdf_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"PDF parsing failed: {str(e)}")

    if not pages:
        raise HTTPException(status_code=422, detail="No pages found in PDF.")

    extraction_id = str(uuid.uuid4())

    # ─── STREAM GENERATOR FOR CPU WORKLOADS ───
    async def pipeline_streamer():
        try:
            # 1. Immediate Network Heartbeat Token to secure the TCP socket
            yield json.dumps({
                "status": "processing", 
                "message": f"Pipeline started successfully. Processing {len(pages)} pages on CPU..."
            }) + "\n"
            await asyncio.sleep(0.05)  # Flush network buffer

            # 2. Execute heavy multi-agent process pipeline
            nodes = await process_pdf(file.filename, extraction_id, pages)
            
            # 3. Build doc_type distribution metrics
            doc_type_counts: dict = {}
            action_required_pages = []
            for n in nodes:
                dt = n["meta"].get("doc_type", "Unknown")
                doc_type_counts[dt] = doc_type_counts.get(dt, 0) + 1
                if n["meta"].get("action_required"):
                    action_required_pages.append(n["page_number"])

            # 4. Count database graph edges
            db = get_db()
            edge_count = await db.edges.count_documents(
                {"from_node_id": {"$in": [n["node_id"] for n in nodes]}}
            )

            # 5. Compile full summary package
            summary = {
                "status": "completed",
                "extraction_id": extraction_id,
                "pdf_name": file.filename,
                "total_pages": len(pages),
                "doc_type_distribution": doc_type_counts,
                "graph_nodes_created": len(nodes),
                "graph_edges_created": edge_count,
                "action_required_pages": action_required_pages,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "pages": [
                    {
                        "page_number": n["page_number"],
                        "node_id": n["node_id"],
                        "char_count": n["char_count"],
                        "has_images": n["has_images"],
                        "meta": {k: v for k, v in n["meta"].items() if k != "embedding"},
                    }
                    for n in nodes
                ],
            }
            
            # 1. Persist to Mongo (this adds the non-serializable ObjectId in-place)
            await store_extraction_summary(summary)
            
            # 2. ─── SANITIZE THE OBJECTID ───
            if "_id" in summary:
                summary["_id"] = str(summary["_id"])
            
            # 3. Now it will serialize perfectly!
            yield json.dumps(summary) + "\n"

        except Exception as e:
            # Capture and output internal pipeline stack traces cleanly
            import traceback
            traceback.print_exc()
            
            error_msg = str(e) if str(e) else repr(e)
            yield json.dumps({
                "status": "failed", 
                "detail": f"Pipeline error: {error_msg}"
            }) + "\n"

    return StreamingResponse(pipeline_streamer(), media_type="application/x-ndjson")





