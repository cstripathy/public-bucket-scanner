#!/bin/bash
set -e

echo "🚀 Bucket Scanner - Quick Start Script"
echo "======================================"
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose plugin is not installed. Please install Docker Compose plugin first."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Setup environment
echo "⚙️  Setting up environment..."
cd docker

if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created. Please edit docker/.env with your configuration."
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🐳 Starting Docker containers..."
docker compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "🔍 Checking service status..."
docker compose ps

echo ""
echo "✅ Testing API..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API is running and healthy!"
else
    echo "⚠️  API might not be ready yet. Check logs with: docker compose logs -f api"
fi

echo ""
echo "======================================"
echo "✅ Bucket Scanner is ready!"
echo ""
echo "📍 Access points:"
echo "   • API: http://localhost:8000"
echo "   • API Docs: http://localhost:8000/docs"
echo "   • Grafana: http://localhost:3000 (admin/admin)"
echo "   • Prometheus: http://localhost:9090"
echo ""
echo "📖 Quick examples:"
echo ""
echo "   # Scan a bucket"
echo "   curl -X POST http://localhost:8000/api/v1/scan/immediate \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"bucket_name\": \"example-bucket\"}'"
echo ""
echo "   # Get statistics"
echo "   curl http://localhost:8000/api/v1/statistics"
echo ""
echo "   # View logs"
echo "   docker compose logs -f"
echo ""
echo "📚 Documentation:"
echo "   • README.md - Overview"
echo "   • docs/API.md - API reference"
echo "   • docs/DEPLOYMENT.md - Production deployment"
echo "   • docs/DEVELOPMENT.md - Development guide"
echo ""
echo "🛑 To stop:"
echo "   cd docker && docker compose down"
echo ""
