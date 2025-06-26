#!/bin/bash

# Start Smart MCP Server Docker Cluster
echo "🚀 Starting Smart MCP Server Docker Cluster..."

# Check if .env.local exists
if [ ! -f .env.local ]; then
    echo "⚠️  Warning: .env.local not found. Creating minimal environment file..."
    cat > .env.local << EOF
# Minimal environment for Smart MCP Server
OPENAI_API_KEY=your-openai-api-key-here
SHOPIFY_STORE_DOMAIN=example.myshopify.com
SHOPIFY_STOREFRONT_ACCESS_TOKEN=your-token-here
SHOPIFY_ADMIN_API_KEY=your-admin-key-here
REPLICATE_API_TOKEN=your-replicate-token-here
EOF
    echo "📝 Please edit .env.local with your actual API keys"
fi

# Build and start the cluster
echo "🏗️  Building Docker images..."
docker-compose -f docker-compose.smart.yml build

echo "🚀 Starting Smart MCP Server cluster..."
docker-compose -f docker-compose.smart.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "📊 Checking service status..."
docker-compose -f docker-compose.smart.yml ps

# Show logs for first few seconds
echo "📋 Recent logs:"
docker-compose -f docker-compose.smart.yml logs --tail=10

echo ""
echo "✅ Smart MCP Server cluster is starting!"
echo "🌐 Endpoints:"
echo "   • Load Balancer: http://localhost:8081"
echo "   • Server 1: http://localhost:4321"
echo "   • Server 2: http://localhost:4322"
echo "   • Server 3: http://localhost:4323"
echo ""
echo "🧪 To test the cluster:"
echo "   python test_docker_cluster.py"
echo ""
echo "🛑 To stop the cluster:"
echo "   docker-compose -f docker-compose.smart.yml down"