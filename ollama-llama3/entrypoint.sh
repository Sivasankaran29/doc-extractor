#!/bin/bash
set -e

echo "Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

echo "Waiting for Ollama to be ready..."
until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
  sleep 1
done

echo "Pulling llama3 model..."
ollama pull llama3

echo "Ollama ready on port 11434"
wait $OLLAMA_PID
