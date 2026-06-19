#!/bin/bash
# ============================================================
#  run_extractor.sh — Build and run the Industrial Doc Extractor
#  Run this from inside the industrial-doc-extractor/ folder
# ============================================================
set -e

echo "================================================"
echo "  Industrial Document Extractor"
echo "================================================"

# ── Check .env ────────────────────────────────────────────
if [ ! -f .env ]; then
  echo "[setup] .env not found — copying from .env.example"
  cp .env.example .env
  echo ""
  echo "⚠️  Please edit .env and fill in your credentials:"
  echo "    - AWS_ACCESS_KEY_ID"
  echo "    - AWS_SECRET_ACCESS_KEY"
  echo "    - OPENAI_API_KEY"
  echo ""
  echo "Then re-run this script."
  exit 1
fi

# ── Validate required env vars ────────────────────────────
source .env

MISSING=()
[ -z "$AWS_ACCESS_KEY_ID" ]     && MISSING+=("AWS_ACCESS_KEY_ID")
[ -z "$AWS_SECRET_ACCESS_KEY" ] && MISSING+=("AWS_SECRET_ACCESS_KEY")
[ -z "$OPENAI_API_KEY" ]        && MISSING+=("OPENAI_API_KEY")

if [ ${#MISSING[@]} -ne 0 ]; then
  echo "❌  Missing required values in .env:"
  for var in "${MISSING[@]}"; do
    echo "    - $var"
  done
  exit 1
fi

# ── Ensure shared network exists ─────────────────────────
if ! docker network ls --format '{{.Name}}' | grep -q '^agent-network$'; then
  echo "[1/5] Creating shared Docker network: agent-network"
  docker network create agent-network
else
  echo "[1/5] Docker network 'agent-network' already exists"
fi

# ── Start MongoDB ─────────────────────────────────────────
if docker ps -a --format '{{.Names}}' | grep -q '^mongodb$'; then
  echo "[2/5] MongoDB container already exists — skipping"
else
  echo "[2/5] Starting MongoDB 7.0 container"
  docker run -d \
    --name mongodb \
    --network agent-network \
    -p 27017:27017 \
    -v mongo_data:/data/db \
    mongo:7.0
fi

# Wait for MongoDB to be ready
echo "      Waiting for MongoDB to be ready..."
until docker exec mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; do
  sleep 2
done
echo "      MongoDB is ready."

# ── Build extractor image ─────────────────────────────────
echo "[3/5] Building Docker image: industrial-doc-extractor"
docker build -t industrial-doc-extractor .

# ── Remove existing extractor container ───────────────────
if docker ps -a --format '{{.Names}}' | grep -q '^industrial-doc-extractor$'; then
  echo "[4/5] Removing existing container: industrial-doc-extractor"
  docker rm -f industrial-doc-extractor
fi

# ── Run extractor ─────────────────────────────────────────
echo "[5/5] Starting industrial-doc-extractor container"
docker run -d \
  --name industrial-doc-extractor \
  --network agent-network \
  -p 8000:8000 \
  --env-file .env \
  -e MONGODB_URI=mongodb://mongodb:27017 \
  -e OLLAMA_HOST=http://ollama-llama3:11434 \
  -e OLLAMA_MODEL=llama3 \
  -v "$(pwd)/uploads:/app/uploads" \
  industrial-doc-extractor

echo ""
echo "✅  Industrial Doc Extractor is running."
echo ""
echo "    API:        http://localhost:8000"
echo "    Swagger UI: http://localhost:8000/docs"
echo "    MongoDB:    mongodb://localhost:27017"
echo ""
echo "    Upload a PDF:"
echo '    curl -X POST http://localhost:8000/extract -F "file=@yourfile.pdf"'
echo ""
echo "    Semantic search:"
echo '    curl "http://localhost:8000/search/similar?q=pump+seal+failure"'
echo ""
echo "    View logs:"
echo "    docker logs -f industrial-doc-extractor"
