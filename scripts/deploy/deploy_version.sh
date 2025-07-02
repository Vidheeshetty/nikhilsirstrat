#!/bin/bash
# Deploy specific version to production server (version number only, no 'v' prefix)
set -euo pipefail

function usage() {
    echo "Usage: $0 <version> [--host <host>] [--user <user>] [--dry-run]"
    echo "  version: Version number to deploy (e.g., 1.2.3 - without v prefix)"
    echo "  host:    Target server (default: 139.84.166.225)"
    echo "  user:    SSH user (default: synaptic)"
    echo "  --dry-run: Show what would be deployed without executing"
    echo ""
    echo "Examples:"
    echo "  $0 1.2.3"
    echo "  $0 1.2.3 --host myserver.com --user deploy"
    echo "  $0 1.2.3 --dry-run"
    exit 1
}

# Parse arguments
VERSION=""
HOST="139.84.166.225"
USER="synaptic"
DRY_RUN=false

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
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        [0-9]*)
            VERSION="$1"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

if [[ -z "$VERSION" ]]; then
    echo "Error: Version is required"
    usage
fi

# Validate version format (semantic versioning)
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "❌ Invalid version format. Use semantic versioning (e.g., 1.2.3)"
    exit 1
fi

TAG="v$VERSION"

echo "🚀 Deploying version $VERSION (tag: $TAG) to $USER@$HOST..."

# Verify tag exists locally
if ! git rev-parse --verify "refs/tags/$TAG" >/dev/null 2>&1; then
    echo "❌ Tag $TAG not found locally. Fetching tags..."
    git fetch --tags
    if ! git rev-parse --verify "refs/tags/$TAG" >/dev/null 2>&1; then
        echo "❌ Tag $TAG not found. Available recent tags:"
        git tag -l | tail -10
        echo ""
        echo "💡 To create this version, run:"
        echo "   ./1dev_com.sh --msg 'your changes' && ./2sync_main.sh --yes --msg 'release v$VERSION'"
        exit 1
    fi
fi

if [[ "$DRY_RUN" == "true" ]]; then
    echo "🔍 DRY RUN - Would deploy:"
    echo "  - Version: $VERSION"
    echo "  - Git Tag: $TAG"
    echo "  - Docker Image: docker.io/ntplatform:$VERSION"
    echo "  - Target: $USER@$HOST"
    echo "  - Config: docker/docker-compose.prod.yml"
    exit 0
fi

# Deploy to server
ssh "$USER@$HOST" << EOF
set -euo pipefail

echo "📥 Pulling latest code and checking out $TAG..."
cd ~/NTbasedPlatform

# Configure git to use SSH instead of HTTPS for GitHub
if git remote get-url gitrepo | grep -q "https://github.com"; then
    echo "🔧 Switching to SSH remote for authentication..."
    git remote set-url gitrepo git@github.com:gtalknitin/NTBasedPlatform.git
fi

git fetch --tags gitrepo

# Verify tag exists on server
if ! git rev-parse --verify "refs/tags/$TAG" >/dev/null 2>&1; then
    echo "❌ Tag $TAG not found on server"
    exit 1
fi

# Stash any local changes before checkout
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "💾 Stashing local changes before checkout..."
    git stash push -m "Pre-deployment stash $(date)"
fi

git checkout $TAG

echo "🐳 Checking Docker image for version $VERSION..."
if ! docker image inspect docker.io/ntplatform:$VERSION >/dev/null 2>&1; then
    echo "📦 Image not found locally. Attempting to pull from registry..."
    if ! docker pull docker.io/ntplatform:$VERSION 2>/dev/null; then
        echo "⚠️  Image not available in registry. Building locally..."
        if ! docker build -t docker.io/ntplatform:$VERSION -f docker/Dockerfile --target production .; then
            echo "❌ Failed to build Docker image"
            exit 1
        fi
        echo "✅ Docker image built successfully"
    else
        echo "✅ Docker image pulled from registry"
    fi
else
    echo "✅ Docker image already exists locally"
fi

echo "🔄 Updating production deployment..."
export DEPLOY_TAG=$VERSION

# Stop current services gracefully
echo "⏹️  Stopping current services..."
docker compose -f docker/docker-compose.prod.yml down || true

# Start with new version
echo "🚀 Starting services with version $VERSION..."
docker compose -f docker/docker-compose.prod.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 15

# Health check with retries
echo "🔍 Checking service health..."
for i in {1..6}; do
    if curl -sf http://localhost:8080/api/status >/dev/null; then
        echo "✅ Deployment successful! Dashboard is healthy."
        break
    else
        if [ \$i -eq 6 ]; then
            echo "❌ Dashboard not responding after 90 seconds. Checking logs..."
            docker logs paper-trading-server --tail 20
            docker logs paper-trading-daemon --tail 20
            exit 1
        fi
        echo "⏳ Attempt \$i/6: Dashboard not ready, waiting 15 more seconds..."
        sleep 15
    fi
done

# Show deployment info
echo ""
echo "🎉 Deployment Summary:"
echo "  ✅ Version: $VERSION"
echo "  ✅ Git Tag: $TAG"
echo "  ✅ Docker Image: docker.io/ntplatform:$VERSION"
echo "  ✅ Dashboard: http://localhost:8080"
echo "  ✅ Status: $(curl -s http://localhost:8080/api/status)"

# Cleanup old images (keep last 3 versions)
echo "🧹 Cleaning up old Docker images..."
docker images docker.io/ntplatform --format "table {{.Tag}}\t{{.ID}}" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+' | tail -n +4 | awk '{print \$2}' | xargs -r docker rmi || true

echo "🎉 Deployment of version $VERSION completed successfully!"
EOF

echo "✅ Deployment finished!"
echo "📊 Dashboard: http://$HOST:8080"
echo "🔍 Health check: curl http://$HOST:8080/api/status" 