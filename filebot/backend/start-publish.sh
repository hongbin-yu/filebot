#!/bin/bash
# FileBot Publish Server (port 8002)
cd "$(dirname "$0")"

# Start server (no --reload to avoid multiprocess issues)
exec venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8002
