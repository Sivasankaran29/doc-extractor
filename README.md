# Industrial Document Extractor

A robust, multi-agent document processing platform designed for industrial environments. The system parses PDFs, extracts domain-specific knowledge, generates semantic embeddings, and builds a property graph directly inside MongoDB for advanced retrieval, analytics, and relationship discovery.

---

## ⚙️ Features

* Multi-agent PDF analysis pipeline
* Industrial document classification
* Equipment and entity extraction
* Hazard and criticality assessment
* Technical summarization
* Semantic embedding generation
* MongoDB Property Graph construction
* Relationship discovery across documents
* Docker-based deployment
* Local LLM support through Ollama
* AWS Bedrock integration
* Azure OpenAI embedding generation

---

## 🏗️ Architecture

```text
PDF Upload
    │
    ▼
Page Extractor (PyMuPDF)
    │
    │ [page_number, text, has_images, char_count]
    ▼

┌──────────────────────────────────────────────────────────┐
│                  5 Agents (per page, parallel)           │
│                                                          │
│  Agent 1 ──── Doc Type Classifier (Bedrock/Claude)       │
│  Agent 2 ──── Industrial Entity Extractor (Bedrock)      │
│  Agent 3 ──── Criticality & Hazard Assessor (Bedrock)    │
│  Agent 4 ──── Technical Summary Generator (Ollama)       │
│  Agent 5 ──── Metadata & Relations Decider (Bedrock)     │
│                                                          │
│  + Azure OpenAI Embeddings (1536 Dimensions)             │
└──────────────────────────────────────────────────────────┘
    │
    ▼

MongoDB Property Graph

Nodes:
  - Page text
  - Embeddings
  - Metadata
  - Summaries
  - Extracted entities

Edges:
  - NEXT_PAGE
  - SAME_EQUIPMENT
  - SEMANTICALLY_SIMILAR
  - REFERENCES_PART
  - RELATED_PROCEDURE
  - INSPECTION_OF
  - RISK_COVERS
  - BREAKDOWN_OF
```

---

## 📄 Supported Document Types

| Document Type        | Description                                 |
| -------------------- | ------------------------------------------- |
| SOP                  | Standard Operating Procedures               |
| Breakdown Report     | Equipment failure and maintenance incidents |
| Electrical Diagram   | Wiring schematics and single-line diagrams  |
| Spare Part List      | BOMs and component inventories              |
| Maintenance Schedule | Preventive maintenance plans                |
| Inspection Report    | Quality and safety inspections              |
| Work Order           | Corrective maintenance job cards            |
| Technical Manual     | Equipment operation manuals                 |
| Risk Assessment      | HAZOP, JSA, FMEA and safety studies         |
| Calibration Record   | Instrument calibration certificates         |

---

# 📊 Graph Database Schema

The system stores all extracted information using a Property Graph architecture implemented in MongoDB.

## Node Collection (`nodes`)

```json
{
  "node_id": "uuid-v4-string",
  "node_type": "page",
  "pdf_name": "SOP-PUMP-001.pdf",
  "extraction_id": "uuid-v4-string",
  "page_number": 3,
  "text": "Full extracted page text details...",
  "embedding": [0.012, -0.034, 0.912],
  "meta": {
    "doc_type": "SOP",
    "sub_type": "Centrifugal Pump Startup SOP",
    "department": "Mechanical",
    "revision": "Rev 4",
    "criticality": "High",
    "hazard_level": "Medium",
    "action_required": false,
    "confidence": 0.94,
    "tags": [
      "pump",
      "startup",
      "P-101",
      "seal",
      "isolation"
    ],
    "entities": {
      "equipment_tags": [
        "P-101",
        "XV-204"
      ],
      "equipment_types": [
        "centrifugal pump",
        "isolation valve"
      ],
      "hazard_indicators": [
        "rotating equipment",
        "high pressure"
      ]
    },
    "summary": "Describes the startup procedure for pump P-101..."
  }
}
```

---

## Edge Collection (`edges`)

```json
{
  "from_node_id": "uuid-page3",
  "to_node_id": "uuid-page7",
  "relation": "SAME_EQUIPMENT",
  "weight": 0.75,
  "meta": {
    "shared_tags": [
      "P-101"
    ]
  }
}
```

---

## 🔗 Supported Relationships

### NEXT_PAGE

Maintains sequential page structure within a document.

### SAME_EQUIPMENT

Connects pages discussing the same equipment tag.

Example:

```text
P-101 Startup SOP
        │
        ▼
P-101 Breakdown Report
```

### SEMANTICALLY_SIMILAR

Generated automatically when cosine similarity exceeds the configured threshold.

Default Threshold:

```text
Cosine Similarity ≥ 0.82
```

### REFERENCES_PART

Links procedures and operational content to spare parts and BOM records.

### RELATED_PROCEDURE

Connects procedures that belong to the same maintenance or operational workflow.

### INSPECTION_OF

Links inspections to target equipment.

### RISK_COVERS

Connects risk assessments to affected assets and procedures.

### BREAKDOWN_OF

Associates incident reports with equipment and systems.

---

# 🚀 Quick Start

## Step 1: Create Docker Network

```bash
docker network create ai_bridge
```

---

## Step 2: Start Ollama Container

```bash
docker run -d \
  --name ollama-llama3 \
  --network ai_bridge \
  --network-alias ollama-llama3 \
  -e OLLAMA_HOST=0.0.0.0 \
  -v ollama_data:/root/.ollama \
  siva0429/ollama-llama3
```

---

## Step 3: Launch Industrial Document Extractor

```bash
docker run -d \
  --name industrial-doc-extractor \
  --network ai_bridge \
  -p 8000:8000 \
  -e OLLAMA_HOST=http://ollama-llama3:11434 \
  siva0429/industrial-doc-extractor
```

---

# 🔑 Environment Variables

Create a `.env` file:

```env
# AWS Bedrock

AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=your_region

# Azure OpenAI

AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_API_VERSION=2023-05-15
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/

# MongoDB

MONGODB_URI=mongodb://username:password@host:27017/
MONGODB_DB=pdf_extractions

# Ollama

OLLAMA_HOST=http://ollama-llama3:11434
OLLAMA_MODEL=llama3
```

---

# 🛣️ API Endpoints

| Method | Endpoint   | Description                             |
| ------ | ---------- | --------------------------------------- |
| GET    | `/health`  | Validate all services and dependencies  |
| POST   | `/extract` | Upload and process industrial documents |

---

## Example Extraction Request

```bash
curl -X POST \
  "http://localhost:8000/extract" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample.pdf"
```

---

# 📚 Swagger Documentation

Once the application is running:

```text
http://localhost:8000/docs
```

The Swagger dashboard provides:

* API testing
* Request validation
* Endpoint documentation
* Response schemas

---

# 🧠 Embedding Strategy

The system uses Azure OpenAI embeddings:

```text
Model: text-embedding-ada-002
Dimensions: 1536
```

Embeddings are generated for every page and stored directly in MongoDB for:

* Semantic Search
* Similarity Detection
* Knowledge Discovery
* Graph Relationship Generation

---

# 🔍 Example Use Cases

### Maintenance Knowledge Search

```text
Find all documents related to Pump P-101 seal failure.
```

### Incident Investigation

```text
Show breakdown reports connected to compressor C-201.
```

### Procedure Discovery

```text
Find startup procedures related to equipment mentioned in inspection reports.
```

### Risk Analysis

```text
List high-criticality documents involving rotating equipment hazards.
```

---

# 📈 Benefits

* Eliminates document silos
* Creates a connected industrial knowledge graph
* Enables semantic search across thousands of PDFs
* Supports predictive maintenance initiatives
* Accelerates root cause investigations
* Improves operational knowledge accessibility
* Enables future Graph-RAG implementations

---

# 📝 License

Internal/Enterprise Use Only.

Copyright © Industrial Document Extractor

