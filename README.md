# Industrial Document Extractor

Multi-agent pipeline for industrial PDFs with graph storage and semantic search.

## Document Types Recognised

| Type | Description |
|------|-------------|
| SOP | Standard Operating Procedure |
| Breakdown Report | Equipment failure / maintenance incident |
| Electrical Diagram | Wiring schematic, single-line diagram |
| Spare Part List | BOM, parts catalogue, component inventory |
| Maintenance Schedule | Preventive maintenance plan / checklist |
| Inspection Report | Quality / safety inspection findings |
| Work Order | Job card, corrective maintenance |
| Technical Manual | Equipment operation / installation guide |
| Risk Assessment | HAZOP, JSA, FMEA, safety risk register |
| Calibration Record | Instrument calibration certificate |

---

## Architecture

```
PDF Upload
    │
    ▼
Page Extractor (PyMuPDF)
    │  page_number, text, has_images, char_count
    ▼
┌──────────────────────────────────────────────────────────┐
│                  5 Agents (per page, parallel)           │
│                                                          │
│  Agent 1 ──── Doc Type Classifier  (Bedrock/Claude)      │
│  Agent 2 ──── Industrial Entity Extractor (Bedrock)      │
│  Agent 3 ──── Criticality & Hazard Assessor (Bedrock)    │
│  Agent 4 ──── Technical Summary Generator (Ollama/llama3)│
│  Agent 5 ──── Metadata & Relations Decider (Bedrock)     │
│                                                          │
│  + OpenAI text-embedding-ada-002 (1536-dim vector)       │
└──────────────────────────────────────────────────────────┘
    │
    ▼
MongoDB Property Graph
  nodes  ── page text + embedding + full metadata
  edges  ── NEXT_PAGE, SAME_EQUIPMENT, SEMANTICALLY_SIMILAR,
             REFERENCES_PART, RELATED_PROCEDURE,
             INSPECTION_OF, RISK_COVERS, BREAKDOWN_OF
```

---

## Graph Model

### Node (collection: `nodes`)
```json
{
  "node_id": "uuid",
  "node_type": "page",
  "pdf_name": "SOP-PUMP-001.pdf",
  "extraction_id": "uuid",
  "page_number": 3,
  "text": "Full page text...",
  "embedding": [0.012, -0.034, ...],
  "meta": {
    "doc_type": "SOP",
    "sub_type": "Centrifugal Pump Startup SOP",
    "department": "Mechanical",
    "revision": "Rev 4",
    "criticality": "High",
    "hazard_level": "Medium",
    "action_required": false,
    "confidence": 0.94,
    "tags": ["pump", "startup", "P-101", "seal", "isolation"],
    "entities": {
      "equipment_tags": ["P-101", "XV-204"],
      "equipment_types": ["centrifugal pump", "isolation valve"],
      "hazard_indicators": ["rotating equipment", "high pressure"]
    },
    "summary": "Describes the startup procedure for pump P-101..."
  }
}
```

### Edge (collection: `edges`)
```json
{
  "from_node_id": "uuid-page3",
  "to_node_id": "uuid-page7",
  "relation": "SAME_EQUIPMENT",
  "weight": 0.75,
  "meta": { "shared_tags": ["P-101"] }
}
```

### Edge Types
| Relation | Description |
|----------|-------------|
| `NEXT_PAGE` | Sequential pages within the same PDF |
| `SAME_EQUIPMENT` | Pages referencing the same equipment tag |
| `SEMANTICALLY_SIMILAR` | Cosine similarity ≥ 0.82 on embeddings |
| `REFERENCES_PART` | SOP/Work Order → Spare Part List page |
| `RELATED_PROCEDURE` | SOP ↔ SOP or Work Order ↔ Work Order |
| `INSPECTION_OF` | Inspection/Calibration → equipment page |
| `RISK_COVERS` | Risk Assessment → procedure/equipment page |
| `BREAKDOWN_OF` | Breakdown Report → SOP or Technical Manual |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/extract` | Upload PDF for processing |
| `GET` | `/health` | Health check |

---

## Setup

```bash
cp .env.example .env
# Fill in: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, OPENAI_API_KEY

docker-compose up -d --build
```

Swagger UI: http://localhost:8000/docs
