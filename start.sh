#!/bin/bash

# Elevare Startup Script
echo "🚀 Starting Elevare Platform..."

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis is not running. Starting Redis..."
    redis-server --daemonize yes
    sleep 2
fi

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create one with your API keys."
    exit 1
fi

echo "✅ Redis is running"
echo "✅ Virtual environment activated"
echo "✅ Environment variables loaded"
echo ""
echo "🌐 Starting FastAPI server..."
echo "📱 Frontend: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
