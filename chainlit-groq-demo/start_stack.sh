#!/bin/bash
# Complete Farm Control + ThingsBoard Stack Deployment

set -e

echo "🌾 Starting Complete Farm IoT Stack..."

# Check if Docker and Docker Compose are available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed or not in PATH"
    exit 1
fi

# Check for environment file
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.docker .env
    echo "📝 Please edit .env file and set your API keys:"
    echo "   - GROQ_API_KEY"
    echo "   - OPENAI_PROJECT_API_KEY"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Load environment variables
source .env

# Check required API keys
if [ -z "$GROQ_API_KEY" ] || [ "$GROQ_API_KEY" = "your_groq_api_key_here" ]; then
    echo "❌ GROQ_API_KEY not set in .env file"
    exit 1
fi

echo "✅ Environment configuration loaded"

# Stop any existing containers
echo "🧹 Cleaning up existing containers..."
docker-compose down --remove-orphans || true

# Pull latest images
echo "📥 Pulling latest images..."
docker-compose pull --ignore-pull-failures || true

# Build and start the stack
echo "🏗️  Building and starting the farm control stack..."
docker-compose up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "🔍 Checking service status..."
docker-compose ps

echo ""
echo "🎉 Farm IoT Platform with AI Copilot is now running!"
echo ""
echo "📱 Access your services:"
echo "   🌾 ThingsBoard with AI Copilot: http://localhost:9001 (PRIMARY INTERFACE)"
echo "   🏭 ThingsBoard Platform:        http://localhost:8080"
echo "   🤖 Farm AI Copilot:            http://localhost:8000"
echo ""
echo "🔐 Default ThingsBoard credentials:"
echo "   Username: tenant@thingsboard.org"
echo "   Password: tenant"
echo ""
echo "✨ The integrated interface provides:"
echo "   • Full ThingsBoard IoT platform in iframe"
echo "   • Floating Chainlit AI copilot widget (bottom-right)"
echo "   • Real-time interaction between IoT data and AI"
echo "   • Context-aware AI assistance"
echo ""
echo "📊 To view logs:"
echo "   docker-compose logs -f [service-name]"
echo ""
echo "🛑 To stop the stack:"
echo "   docker-compose down"
