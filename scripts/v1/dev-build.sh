#!/bin/bash
# Option 3 - Live-Rebuild Image workflow
# Build the dev image when dependencies change, keep source bind-mounted for instant edits

set -e

echo "🔨 Building ntplatform:dev image..."
DOCKER_BUILDKIT=1 docker build -t ntplatform:dev --target dev -f docker/Dockerfile .

echo "🚀 Starting services with live-reload..."
docker compose -f docker/docker-compose.yml up -d

echo "📊 Services status:"
docker compose -f docker/docker-compose.yml ps

echo ""
echo "🌐 Dashboard: http://localhost:8080"
echo "📝 To attach to dev shell: docker exec -it paper-trading-devshell bash"
echo "🔍 To view logs:"
echo "   docker logs -f paper-trading-daemon"
echo "   docker logs -f paper-trading-server"
echo ""
echo "💡 Code changes in Python files will be reflected immediately via bind mount"
echo "   To rebuild after dependency changes, run this script again" 