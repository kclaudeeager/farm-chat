#!/bin/bash
# Quick demo deployment with ngrok

set -e

echo "🚀 Starting Farm Control AI for Demo..."

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok not found. Please install ngrok first:"
    echo "   Download from: https://ngrok.com/download"
    echo "   Or install via: brew install ngrok (macOS) / snap install ngrok (Linux)"
    exit 1
fi

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️ No .env file found. Creating from template..."
    cp .env.docker .env
    echo "📝 Please edit .env file and set your GROQ_API_KEY"
    echo "   Get your free key from: https://console.groq.com/"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Load environment variables
source .env

# Check required API keys
if [ -z "$GROQ_API_KEY" ] || [ "$GROQ_API_KEY" = "your_groq_api_key_here" ]; then
    echo "❌ GROQ_API_KEY not set in .env file"
    echo "   Get your free key from: https://console.groq.com/"
    exit 1
fi

echo "✅ Environment configuration loaded"

# Start the services
echo "🏗️ Starting services..."
docker-compose up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 15

# Check if services are healthy
echo "🔍 Checking service health..."
for i in {1..30}; do
    if curl -f http://localhost:8000 >/dev/null 2>&1; then
        echo "✅ Chainlit service is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Service failed to start. Check logs:"
        echo "   docker-compose logs farm-control-demo"
        exit 1
    fi
    sleep 2
done

# Start ngrok for the integrated interface
echo "🌐 Starting ngrok tunnel..."
echo ""
echo "🎉 Farm Control AI is ready!"
echo ""
echo "📱 Local Access:"
echo "   🤖 AI Chat Interface:     http://localhost:8000"
echo "   🏭 Full Integration:       http://localhost:9001"
echo ""
echo "🌍 Starting public tunnel..."
echo "   📤 The public URL will appear below:"
echo ""

# Start ngrok for the integrated interface (port 9001)
ngrok http 9001
