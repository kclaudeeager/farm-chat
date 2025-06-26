#!/bin/bash
# Production deployment script

set -e

echo "🚀 Starting Farm Control AI Production Deployment..."

# Check if we're on a server
if [ -z "$SERVER_DOMAIN" ]; then
    echo "⚠️ SERVER_DOMAIN not set. Using localhost for testing."
    SERVER_DOMAIN="localhost"
fi

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️ No .env file found. Creating from template..."
    cp .env.docker .env
    echo "📝 Please edit .env file and set your API keys"
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

# Update nginx config with domain
if [ "$SERVER_DOMAIN" != "localhost" ]; then
    echo "🔧 Updating nginx configuration for domain: $SERVER_DOMAIN"
    sed -i "s/server_name localhost;/server_name $SERVER_DOMAIN;/" nginx.conf
fi

# Stop any existing containers
echo "🧹 Stopping existing containers..."
docker-compose down || true

# Build and start production services
echo "🏗️ Building and starting production services..."
docker-compose --profile production up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 20

# Check service health
echo "🔍 Checking service health..."
for i in {1..60}; do
    if curl -f http://localhost/health >/dev/null 2>&1; then
        echo "✅ Production services are ready!"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "❌ Services failed to start. Check logs:"
        echo "   docker-compose logs"
        exit 1
    fi
    sleep 2
done

echo ""
echo "🎉 Farm Control AI Production Deployment Complete!"
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""
echo "🌐 Access URLs:"
if [ "$SERVER_DOMAIN" = "localhost" ]; then
    echo "   🤖 Main Interface:        http://localhost"
    echo "   🏭 Integration UI:        http://localhost/integration"
    echo "   📊 ThingsBoard:          http://localhost/thingsboard"
else
    echo "   🤖 Main Interface:        http://$SERVER_DOMAIN"
    echo "   🏭 Integration UI:        http://$SERVER_DOMAIN/integration"
    echo "   📊 ThingsBoard:          http://$SERVER_DOMAIN/thingsboard"
fi
echo ""
echo "📋 Management Commands:"
echo "   View logs:     docker-compose logs -f"
echo "   Stop services: docker-compose down"
echo "   Restart:       docker-compose restart"
echo ""

# SSL setup reminder
if [ "$SERVER_DOMAIN" != "localhost" ]; then
    echo "🔐 SSL Setup (Optional):"
    echo "   1. Install certbot: sudo apt install certbot python3-certbot-nginx"
    echo "   2. Get certificate: sudo certbot --nginx -d $SERVER_DOMAIN"
    echo "   3. Auto-renewal: sudo crontab -e"
    echo "      Add: 0 12 * * * /usr/bin/certbot renew --quiet"
    echo ""
fi
