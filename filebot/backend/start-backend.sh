#!/bin/bash
# FileBot Backend (port 8001)
# Sets LLM API keys before starting uvicorn
cd "$(dirname "$0")"

# OpenAI API key (set from environment or .env file)
# export OPENAI_API_KEY="your-key-here"

# Start server
exec venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8001
