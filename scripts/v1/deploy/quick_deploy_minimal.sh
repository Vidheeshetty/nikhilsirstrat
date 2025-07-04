#!/bin/bash

# Quick deployment script for minimal Docker image (343MB)
# Usage: ./quick_deploy_minimal.sh

set -e

SERVER_HOST="139.84.166.225"
SERVER_USER="root"
IMAGE_NAME="ntplatform-minimal"
VERSION_TAG="$(date +%Y%m%d_%H%M%S)"

echo "🚀 Deploying minimal Docker image to server..."
echo "📦 Image will be ~343MB (vs 1.44GB previously)"

# Step 1: Build the minimal image locally (if Docker were available)
echo "📋 Instructions for deployment:"
echo ""
echo "1. On your server, run these commands:"
echo ""
echo "   # Create backup first"
echo "   cd /opt/ntplatform"
echo "   docker-compose down"
echo "   cp docker-compose.yml docker-compose.yml.backup"
echo ""
echo "   # Build the new minimal image"
echo "   docker build -f docker/Dockerfile.minimal -t $IMAGE_NAME:$VERSION_TAG ."
echo ""
echo "   # Test the image"
echo "   docker run --rm -d --name test-minimal -p 8001:8000 $IMAGE_NAME:$VERSION_TAG"
echo "   sleep 5"
echo "   curl http://localhost:8001/api/status"
echo "   docker stop test-minimal"
echo ""
echo "   # Update docker-compose.yml to use minimal image"
echo "   sed -i 's/image: .*/image: $IMAGE_NAME:$VERSION_TAG/' docker-compose.yml"
echo ""
echo "   # Deploy"
echo "   docker-compose up -d"
echo ""
echo "   # Verify deployment"
echo "   sleep 10"
echo "   curl http://localhost:8080/api/status"
echo ""
echo "   # Check image size"
echo "   docker images $IMAGE_NAME:$VERSION_TAG"
echo ""
echo "2. If something goes wrong, rollback:"
echo "   docker-compose down"
echo "   cp docker-compose.yml.backup docker-compose.yml"
echo "   docker-compose up -d"
echo ""

# Create the files needed for deployment
echo "📄 Creating deployment files..."

# Create a deployment package
tar -czf deploy_minimal_$(date +%Y%m%d_%H%M%S).tar.gz \
    docker/Dockerfile.minimal \
    requirements-minimal.txt \
    src/ \
    utils/ \
    scripts/paper_trading/ \
    scripts/__init__.py \
    config/ \
    web_dashboard/ \
    VERSION \
    docker/docker-compose.yml

echo "✅ Deployment package created: deploy_minimal_$(date +%Y%m%d_%H%M%S).tar.gz"
echo ""
echo "📤 Transfer this file to your server and extract it, then run the commands above."
echo ""
echo "🎯 Expected results:"
echo "   - Image size: ~343MB (76% reduction from 1.44GB)"
echo "   - Faster builds and deployments"
echo "   - Same functionality with minimal dependencies"
echo "   - No nautilus_trader reference directory issues" 