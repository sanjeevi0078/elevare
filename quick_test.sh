#!/bin/bash

# Quick setup script - tries to use existing key or helps you set one up

echo "🔍 Checking for existing Groq API key..."

# Check if key exists in .env and is not placeholder
source .env 2>/dev/null

if [ -n "$GROQ_API_KEY" ] && [ "$GROQ_API_KEY" != "your_groq_api_key_here" ]; then
    echo "✅ Found existing key in .env"
    EXISTING_KEY=$GROQ_API_KEY
else
    echo "❌ No valid key found in .env"
    EXISTING_KEY=""
fi

# If no valid key, prompt for one
if [ -z "$EXISTING_KEY" ]; then
    echo ""
    echo "📝 You need a Groq API key to enable VC-quality Concept Cards."
    echo ""
    echo "Get one FREE at: https://console.groq.com/keys"
    echo "(Takes 30 seconds - sign in with Google/GitHub)"
    echo ""
    
    # For now, use a test key or skip
    echo "⚠️  For testing purposes, I'll try to proceed without the key."
    echo "   The system will fall back to template-based cards."
    echo ""
    read -p "Press ENTER to continue with fallback mode, or Ctrl+C to exit and get a key..."
fi

# Kill existing server
if [ -f server.pid ]; then
    PID=$(cat server.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "🛑 Stopping existing server (PID $PID)..."
        kill $PID 2>/dev/null
        sleep 2
    fi
    rm -f server.pid
fi

# Start server
echo "🚀 Starting Elevare server..."
bash start.sh > /dev/null 2>&1 &
sleep 3

# Wait for server to be ready
echo "⏳ Waiting for server to start..."
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Server is ready!"
        break
    fi
    sleep 1
    echo -n "."
done

echo ""
echo "🧪 Running test with VoiceBridge example..."
echo ""
python3 test_refine.py

echo ""
echo "=========================================="
if [ -z "$EXISTING_KEY" ]; then
    echo "⚠️  Currently using FALLBACK mode (template-based cards)"
    echo ""
    echo "To enable VC-quality LLM-powered cards:"
    echo "1. Get a free key: https://console.groq.com/keys"
    echo "2. Run: bash setup_groq_key.sh"
else
    echo "✅ LLM-powered concept cards are ACTIVE!"
fi
echo "=========================================="
