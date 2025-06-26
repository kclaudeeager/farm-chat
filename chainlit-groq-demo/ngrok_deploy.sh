#!/bin/bash
# Smart ngrok deployment script for Farm Control AI

set -e

echo "🚀 Starting Farm Control AI with ngrok..."

# Function to get ngrok URL
get_ngrok_url() {
    local port=$1
    local retries=10
    for i in $(seq 1 $retries); do
        if curl -s http://localhost:4040/api/tunnels | jq -e '.tunnels[] | select(.config.addr | contains("'$port'"))' > /dev/null 2>&1; then
            curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[] | select(.config.addr | contains("'$port'")) | .public_url' | head -1
            return 0
        fi
        sleep 2
    done
    echo ""
}

# Check if services are running
if ! docker-compose ps | grep -q "Up"; then
    echo "🏗️ Starting services..."
    docker-compose up -d
    echo "⏳ Waiting for services to be ready..."
    sleep 15
fi

# Stop any existing ngrok
pkill ngrok 2>/dev/null || true
sleep 2

echo "🌐 Starting ngrok tunnels..."

# Start ngrok for Chainlit (port 8000) in background
nohup ngrok http 8000 --log=stdout > chainlit_ngrok.log 2>&1 &
CHAINLIT_NGROK_PID=$!

# Start ngrok for integrated interface (port 9001) in background  
nohup ngrok http 9001 --log=stdout > integration_ngrok.log 2>&1 &
INTEGRATION_NGROK_PID=$!

echo "⏳ Waiting for ngrok tunnels to establish..."
sleep 10

# Get ngrok URLs
CHAINLIT_URL=$(get_ngrok_url "8000")
INTEGRATION_URL=$(get_ngrok_url "9001")

if [ -z "$CHAINLIT_URL" ] || [ -z "$INTEGRATION_URL" ]; then
    echo "❌ Failed to get ngrok URLs. Check if ngrok is authenticated:"
    echo "   ngrok config add-authtoken YOUR_TOKEN"
    echo ""
    echo "🔍 Debug info:"
    echo "Chainlit log:"
    tail -5 chainlit_ngrok.log 2>/dev/null || echo "No log found"
    echo "Integration log:"
    tail -5 integration_ngrok.log 2>/dev/null || echo "No log found"
    exit 1
fi

echo "✅ ngrok tunnels established!"
echo ""
echo "🌐 PUBLIC URLs:"
echo "   🤖 Chainlit AI:           $CHAINLIT_URL"
echo "   🏭 Integrated Interface:   $INTEGRATION_URL"
echo ""

# Update the integrated interface to use the correct Chainlit URL
echo "🔧 Updating integrated interface configuration..."

# Recreate the integrated service with correct Chainlit URL
CHAINLIT_URL="$CHAINLIT_URL" docker-compose up -d thingsboard-with-copilot

echo "⏳ Waiting for updated service..."
sleep 10

echo ""
echo "🎉 Farm Control AI is now publicly accessible!"
echo ""
echo "📱 SHARE THESE URLS:"
echo "   🎯 DEMO URL (RECOMMENDED): $INTEGRATION_URL"
echo "      ↳ Complete experience with ThingsBoard + AI"
echo ""
echo "   🤖 AI Chat Only: $CHAINLIT_URL"
echo "      ↳ Just the Chainlit interface"
echo ""
echo "💡 The integrated interface now properly loads the AI copilot widget!"
echo ""
echo "🛑 To stop: Ctrl+C or run './stop_ngrok.sh'"

# Create stop script
cat > stop_ngrok.sh << EOF
#!/bin/bash
echo "🛑 Stopping ngrok tunnels..."
pkill ngrok 2>/dev/null || true
echo "✅ Stopped"
EOF
chmod +x stop_ngrok.sh

# Keep script running
echo "🔄 Monitoring tunnels... (Press Ctrl+C to stop)"
trap 'echo ""; echo "🛑 Stopping..."; pkill ngrok 2>/dev/null || true; exit 0' INT

while true; do
    sleep 60
    if ! pgrep ngrok > /dev/null; then
        echo "⚠️ ngrok stopped unexpectedly. Restarting..."
        exec $0
    fi
done
