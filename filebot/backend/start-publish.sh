#!/bin/bash
# FileBot Publish Server (port 8002)
# Set DeepSeek API key from openclaw.json
cd "$(dirname "$0")"

# Export DEEPSEEK_API_KEY
export DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-}"

# Start server (no --reload to avoid multiprocess issues)
exec venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8002
