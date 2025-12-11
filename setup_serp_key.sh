#!/bin/bash

# Event Scout SERP API Key Setup
# This script helps configure the SERP API key for live event discovery

echo "🔍 Event Scout - SERP API Key Setup"
echo "===================================="
echo ""
echo "To enable AI-powered event discovery, you need a SERP API key."
echo ""
echo "📍 Get your FREE key here: https://serper.dev/"
echo ""
echo "Steps:"
echo "1. Visit https://serper.dev/"
echo "2. Sign up with Google (free tier: 2,500 searches/month)"
echo "3. Copy your API key (starts with 'sk_...')"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating one..."
    touch .env
fi

# Check if SERP_API_KEY already exists
if grep -q "SERP_API_KEY" .env; then
    echo "✅ SERP_API_KEY already exists in .env"
    echo ""
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing key."
        exit 0
    fi
    # Remove old key
    sed -i.bak '/SERP_API_KEY/d' .env
fi

# Prompt for key
echo ""
read -p "Enter your SERP API key: " serp_key

if [ -z "$serp_key" ]; then
    echo "❌ No key entered. Exiting."
    exit 1
fi

# Add to .env
echo "SERP_API_KEY=$serp_key" >> .env

echo ""
echo "✅ SERP API key saved to .env"
echo ""
echo "🧪 Testing configuration..."

# Test if key works
export SERP_API_KEY=$serp_key

python3 -c "
import os
import requests
import json

key = os.getenv('SERP_API_KEY')
if not key:
    print('❌ Key not loaded')
    exit(1)

print('🔍 Testing SERP API...')
try:
    response = requests.post(
        'https://google.serper.dev/search',
        headers={
            'X-API-KEY': key,
            'Content-Type': 'application/json'
        },
        json={'q': 'test', 'num': 1}
    )
    if response.status_code == 200:
        print('✅ SERP API is working!')
        print(f'   Credits remaining: Check dashboard at https://serper.dev/')
    else:
        print(f'❌ API error: {response.status_code}')
        print(f'   Response: {response.text}')
except Exception as e:
    print(f'❌ Connection failed: {e}')
"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Restart your server: uvicorn main:app --reload"
echo "2. Visit: http://localhost:8000/events"
echo "3. Watch AI discover real events! 🚀"
