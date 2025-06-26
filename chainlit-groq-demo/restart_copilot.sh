#!/bin/bash
# Restart the ThingsBoard with Copilot service

set -e

echo "🔄 Restarting ThingsBoard with AI Copilot service..."

# Stop the copilot container
echo "🛑 Stopping thingsboard-with-copilot..."
docker-compose stop thingsboard-with-copilot || true

# Rebuild and start the copilot service
echo "🏗️  Rebuilding and starting thingsboard-with-copilot..."
docker-compose up -d --build thingsboard-with-copilot

# Wait for service to be ready
echo "⏳ Waiting for service to start..."
sleep 5

# Check status
echo "🔍 Checking service status..."
if curl -s http://localhost:9001/health > /dev/null; then
    echo "✅ ThingsBoard with AI Copilot is running!"
    echo "🌾 Access: http://localhost:9001"
else
    echo "❌ Service not responding, checking logs..."
    docker-compose logs thingsboard-with-copilot
fi
