#!/bin/bash
# ============================================================
#  run_ollama.sh — Build and run the Ollama llama3 image
#  Run this from inside the ollama-llama3/ folder
# ============================================================
set -e

echo "================================================"
echo "  Ollama llama3 Docker Image"
echo "================================================"

# Create shared network if it doesn't exist
if ! docker network ls --format '{{.Name}}' | grep -q '^agent-network$'; then
  echo "[1/4] Creating shared Docker network: agent-network"
  docker network create agent-network
else
  echo "[1/4] Docker network 'agent-network' already exists"
fi

# Build the image
echo "[2/4] Building Docker image: ollama-llama3"
docker build -t ollama-llama3 .

# Remove existing container if present
if docker ps -a --format '{{.Names}}' | grep -q '^ollama-llama3$'; then
  echo "[3/4] Removing existing container: ollama-llama3"
  docker rm -f ollama-llama3
fi

# Run the container
echo "[4/4] Starting container..."
docker run -d \
  --name ollama-llama3 \
  --network agent-network \
  -p 11434:11434 \
  -v ollama_data:/root/.ollama \
  ollama-llama3

echo ""
echo "✅  Ollama container started."
echo "    The llama3 model (~4.7 GB) will be pulled automatically on first start."
echo "    Monitor progress:  docker logs -f ollama-llama3"
echo "    API endpoint:      http://localhost:11434"
echo ""
echo "    Test when ready:"
echo '    curl http://localhost:11434/api/chat -d '"'"'{"model":"llama3","messages":[{"role":"user","content":"ping"}]}'"'"''
