#!/bin/bash

echo "🔑 Groq API Key Setup"
echo "===================="
echo ""
echo "To enable VC-quality Concept Card generation, you need a Groq API key."
echo ""
echo "📍 Get your FREE key here: https://console.groq.com/keys"
echo ""
echo "Steps:"
echo "1. Visit https://console.groq.com/keys"
echo "2. Sign in with Google/GitHub"
echo "3. Click 'Create API Key'"
echo "4. Copy the key (starts with 'gsk_...')"
echo ""
read -p "Enter your Groq API Key: " GROQ_KEY

if [ -z "$GROQ_KEY" ]; then
    echo "❌ No key entered. Exiting."
    exit 1
fi

# Validate key format (basic check)
if [[ ! "$GROQ_KEY" =~ ^gsk_ ]]; then
    echo "⚠️  Warning: Key doesn't start with 'gsk_'. Are you sure this is correct?"
    read -p "Continue anyway? (y/n): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo "❌ Cancelled."
        exit 1
    fi
fi

# Update .env file
if [ -f .env ]; then
    # Replace the existing GROQ_API_KEY line
    if grep -q "^GROQ_API_KEY=" .env; then
        # macOS-compatible sed with backup
        sed -i.bak "s|^GROQ_API_KEY=.*|GROQ_API_KEY=$GROQ_KEY|" .env
        rm .env.bak
        echo "✅ Updated GROQ_API_KEY in .env"
    else
        # Add if not exists
        echo "GROQ_API_KEY=$GROQ_KEY" >> .env
        echo "✅ Added GROQ_API_KEY to .env"
    fi
else
    echo "❌ .env file not found!"
    exit 1
fi

# Kill existing server if running
if [ -f server.pid ]; then
    PID=$(cat server.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "🛑 Stopping existing server (PID $PID)..."
        kill $PID
        sleep 2
    fi
fi

# Start server with new key
echo "🚀 Starting Elevare server with new API key..."
bash start.sh &

echo ""
echo "✅ Setup Complete!"
echo ""
echo "🧪 Test the VC-quality output:"
echo "   python3 test_refine.py"
echo ""
echo "🌐 Or visit: http://localhost:8000/intake"
