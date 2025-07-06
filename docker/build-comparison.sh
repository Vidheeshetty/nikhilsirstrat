#!/bin/bash

echo "🐳 Docker Image Size Comparison"
echo "================================"

# Build current version
echo "📦 Building current version..."
docker build -f docker/Dockerfile --target dev -t paper-trading:current .

# Build optimized version
echo "📦 Building optimized version..."
docker build -f docker/Dockerfile.optimized --target production -t paper-trading:optimized .

# Build minimal version
echo "📦 Building minimal version..."
docker build -f docker/Dockerfile.minimal --target production -t paper-trading:minimal .

# Show size comparison
echo ""
echo "📊 Size Comparison:"
echo "==================="
docker images | grep "paper-trading" | awk '{print $1":"$2" - "$7$8}'

echo ""
echo "🎯 Optimization Results:"
echo "========================"
CURRENT_SIZE=$(docker images paper-trading:current --format "table {{.Size}}" | tail -1)
OPTIMIZED_SIZE=$(docker images paper-trading:optimized --format "table {{.Size}}" | tail -1)
MINIMAL_SIZE=$(docker images paper-trading:minimal --format "table {{.Size}}" | tail -1)

echo "Current:   $CURRENT_SIZE"
echo "Optimized: $OPTIMIZED_SIZE"
echo "Minimal:   $MINIMAL_SIZE"
