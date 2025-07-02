#!/bin/bash
# Deploy specific tagged version to production server
set -euo pipefail

function usage() {
    echo "Usage: $0 <tag> [--host <host>] [--user <user>]"
    echo "  tag:  Git tag to deploy (e.g., v1.2.3)"
    echo "  host: Target server (default: 139.84.166.225)"
    echo "  user: SSH user (default: synaptic)"
    echo ""
    echo "Examples:"
    echo "  $0 v1.2.3"
    echo "  $0 v1.2.3 --host myserver.com --user deploy"
    exit 1
}

# Parse arguments
TAG=""
HOST="139.84.166.225"
USER="synaptic"

while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --user)
            USER="$2"
            shift 2
            ;;
        v*)
            TAG="$1"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

if [[ -z "$TAG" ]]; then
    echo "Error: Tag is required"
    usage
fi

echo "🚀 Deploying $TAG to $USER@$HOST..."

# Verify tag exists locally
if ! git rev-parse --verify "refs/tags/$TAG" >/dev/null 2>&1; then
    echo "❌ Tag $TAG not found locally. Fetching tags..."
    git fetch --tags
    if ! git rev-parse --verify "refs/tags/$TAG" >/dev/null 2>&1; then
        echo "❌ Tag $TAG not found. Available tags:"
        git tag -l | tail -10
        exit 1
    fi
fi

# Deploy to server
ssh "$USER@$HOST" << EOF
set -euo pipefail

echo "📥 Pulling latest code and checking out $TAG..."
cd ~/NTbasedPlatform
git fetch --tags
git checkout $TAG

echo "🐳 Pulling Docker image for $TAG..."
docker pull docker.io/ntplatform:$TAG

echo "🔄 Updating production deployment..."
export DEPLOY_TAG=$TAG

# Stop current services
docker compose -f docker/docker-compose.prod.yml down || true

# Start with new tag
docker compose -f docker/docker-compose.prod.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 10

# Check health
if curl -sf http://localhost:8080/api/status >/dev/null; then
    echo "✅ Deployment successful! Dashboard is healthy."
else
    echo "⚠️  Dashboard not responding, checking logs..."
    docker logs paper-trading-server --tail 10
fi

# Cleanup old images
docker image prune -f

echo "🎉 Deployment of $TAG completed!"
EOF

echo "✅ Deployment finished. Dashboard: http://$HOST:8080" 