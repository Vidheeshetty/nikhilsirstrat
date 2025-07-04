#!/bin/bash

# Quick Docker Test Runner
# Usage: ./quick_test.sh

set -e

echo "🚀 Quick Docker Test Runner"
echo "=========================="

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

# Configuration
IMAGE_TAG="ntplatform-quick-test"
DOCKERFILE="docker/Dockerfile.minimal"

echo "📋 Test Configuration:"
echo "   Dockerfile: $DOCKERFILE"
echo "   Image tag: $IMAGE_TAG"
echo ""

# Quick build test
echo "🔨 Building image..."
if docker build -f $DOCKERFILE -t $IMAGE_TAG . > /dev/null 2>&1; then
    echo "✅ Build successful"
else
    echo "❌ Build failed"
    exit 1
fi

# Check image size
IMAGE_SIZE=$(docker images $IMAGE_TAG --format "{{.Size}}")
echo "📦 Image size: $IMAGE_SIZE"

# Quick startup test
echo "🚀 Testing startup..."
CONTAINER_ID=$(docker run -d -p 8001:8000 $IMAGE_TAG)

# Wait for startup
echo "⏳ Waiting for service..."
sleep 10

# Health check
if curl -f http://localhost:8001/api/status >/dev/null 2>&1; then
    echo "✅ Service is responding"
    STATUS="PASS"
else
    echo "❌ Service not responding"
    STATUS="FAIL"
fi

# Cleanup
docker stop $CONTAINER_ID >/dev/null 2>&1
docker rm $CONTAINER_ID >/dev/null 2>&1
docker rmi $IMAGE_TAG >/dev/null 2>&1

echo ""
echo "📊 Quick Test Results:"
echo "   Build: ✅ PASS"
echo "   Size: $IMAGE_SIZE"
echo "   Health: $([ "$STATUS" = "PASS" ] && echo "✅ PASS" || echo "❌ FAIL")"
echo ""

if [ "$STATUS" = "PASS" ]; then
    echo "🎉 Quick test passed! Ready for comprehensive testing."
    echo ""
    echo "Next steps:"
    echo "1. Run comprehensive tests: ./scripts/deploy/test_docker_locally.sh"
    echo "2. Deploy to server: ./scripts/deploy/deploy_with_backup.sh"
else
    echo "❌ Quick test failed. Fix issues before deployment."
    exit 1
fi 