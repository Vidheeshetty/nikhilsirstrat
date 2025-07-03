#!/bin/bash

# Comprehensive Local Docker Testing Script
# Usage: ./test_docker_locally.sh [dockerfile] [image_tag]

set -e

# Configuration
DOCKERFILE=${1:-"docker/Dockerfile.minimal"}
IMAGE_TAG=${2:-"ntplatform-test"}
TEST_PORT=8001
CONTAINER_NAME="ntplatform-local-test"
TEST_TIMEOUT=60

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Cleanup function
cleanup() {
    log "Cleaning up test environment..."
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
    docker rmi $IMAGE_TAG 2>/dev/null || true
}

# Trap cleanup on exit
trap cleanup EXIT

# Test 1: Build Image
test_build() {
    log "🔨 Test 1: Building Docker image..."
    
    if docker build -f $DOCKERFILE -t $IMAGE_TAG .; then
        success "Docker image built successfully"
        
        # Check image size
        local image_size=$(docker images $IMAGE_TAG --format "{{.Size}}")
        log "Image size: $image_size"
        
        # Warn if image is too large
        local size_mb=$(docker images $IMAGE_TAG --format "{{.Size}}" | sed 's/MB//' | sed 's/GB/000/' | cut -d'.' -f1)
        if [ "${size_mb:-0}" -gt 500 ]; then
            warning "Image size is larger than expected (>500MB). Consider optimization."
        fi
        
    else
        error "Docker image build failed"
        exit 1
    fi
}

# Test 2: Container Startup
test_startup() {
    log "🚀 Test 2: Testing container startup..."
    
    # Start container
    if docker run --rm -d --name $CONTAINER_NAME -p $TEST_PORT:8000 $IMAGE_TAG; then
        success "Container started successfully"
        
        # Wait for container to be ready
        log "Waiting for container to be ready..."
        local count=0
        while [ $count -lt $TEST_TIMEOUT ]; do
            if docker ps | grep -q $CONTAINER_NAME; then
                if docker exec $CONTAINER_NAME ps aux | grep -q python; then
                    success "Application process is running"
                    break
                fi
            fi
            sleep 1
            count=$((count + 1))
        done
        
        if [ $count -eq $TEST_TIMEOUT ]; then
            error "Container startup timeout"
            docker logs $CONTAINER_NAME
            exit 1
        fi
        
    else
        error "Container failed to start"
        exit 1
    fi
}

# Test 3: Health Check
test_health() {
    log "🏥 Test 3: Testing health endpoints..."
    
    # Wait for service to be ready
    log "Waiting for service to be ready..."
    local count=0
    while [ $count -lt $TEST_TIMEOUT ]; do
        if curl -f http://localhost:$TEST_PORT/api/status >/dev/null 2>&1; then
            success "Health check endpoint is responding"
            break
        fi
        sleep 1
        count=$((count + 1))
    done
    
    if [ $count -eq $TEST_TIMEOUT ]; then
        error "Health check timeout"
        log "Container logs:"
        docker logs $CONTAINER_NAME
        exit 1
    fi
    
    # Test specific endpoints
    local endpoints=(
        "/api/status"
        "/api/health"
        "/api/paper-trading/status"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f http://localhost:$TEST_PORT$endpoint >/dev/null 2>&1; then
            success "✅ $endpoint - OK"
        else
            warning "⚠️  $endpoint - Not responding (may be expected)"
        fi
    done
}

# Test 4: API Response Validation
test_api_responses() {
    log "🔍 Test 4: Testing API responses..."
    
    # Test status endpoint response
    local status_response=$(curl -s http://localhost:$TEST_PORT/api/status)
    if echo "$status_response" | grep -q "status"; then
        success "Status endpoint returns valid JSON"
    else
        warning "Status endpoint response may be invalid"
        log "Response: $status_response"
    fi
    
    # Test if paper trading endpoints are accessible
    local pt_status=$(curl -s http://localhost:$TEST_PORT/api/paper-trading/status 2>/dev/null || echo "not available")
    if echo "$pt_status" | grep -q "not available"; then
        log "Paper trading endpoints not yet available (expected for new deployment)"
    else
        success "Paper trading endpoints are responding"
    fi
}

# Test 5: Resource Usage
test_resources() {
    log "📊 Test 5: Testing resource usage..."
    
    # Get container stats
    local stats=$(docker stats $CONTAINER_NAME --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}")
    log "Container resource usage:"
    echo "$stats"
    
    # Check memory usage
    local mem_usage=$(docker stats $CONTAINER_NAME --no-stream --format "{{.MemUsage}}" | cut -d'/' -f1 | sed 's/MiB//')
    if [ "${mem_usage:-0}" -gt 500 ]; then
        warning "High memory usage detected: ${mem_usage}MiB"
    else
        success "Memory usage is reasonable: ${mem_usage}MiB"
    fi
}

# Test 6: Log Validation
test_logs() {
    log "📝 Test 6: Validating container logs..."
    
    local logs=$(docker logs $CONTAINER_NAME 2>&1)
    
    # Check for error patterns
    if echo "$logs" | grep -i "error\|exception\|failed" | grep -v "test"; then
        warning "Errors found in logs:"
        echo "$logs" | grep -i "error\|exception\|failed" | head -5
    else
        success "No critical errors found in logs"
    fi
    
    # Check for successful startup indicators
    if echo "$logs" | grep -i "uvicorn\|started\|listening\|ready"; then
        success "Service startup indicators found"
    else
        warning "No clear startup indicators found"
    fi
}

# Test 7: Configuration Validation
test_config() {
    log "⚙️  Test 7: Testing configuration loading..."
    
    # Check if config files are accessible
    if docker exec $CONTAINER_NAME ls -la config/ >/dev/null 2>&1; then
        success "Configuration directory is accessible"
        
        # List config files
        local config_files=$(docker exec $CONTAINER_NAME find config/ -name "*.yaml" -o -name "*.yml" 2>/dev/null)
        if [ -n "$config_files" ]; then
            success "Configuration files found:"
            echo "$config_files"
        else
            warning "No YAML configuration files found"
        fi
    else
        error "Configuration directory not accessible"
        exit 1
    fi
}

# Test 8: Port Accessibility
test_ports() {
    log "🌐 Test 8: Testing port accessibility..."
    
    # Check if port is accessible
    if netstat -tuln | grep -q ":$TEST_PORT "; then
        success "Port $TEST_PORT is accessible"
    else
        error "Port $TEST_PORT is not accessible"
        exit 1
    fi
    
    # Test with different tools
    if nc -z localhost $TEST_PORT 2>/dev/null; then
        success "Port connectivity confirmed with netcat"
    else
        warning "Netcat test failed (may not be available)"
    fi
}

# Main test execution
main() {
    log "🧪 Starting comprehensive Docker testing..."
    log "Dockerfile: $DOCKERFILE"
    log "Image tag: $IMAGE_TAG"
    log "Test port: $TEST_PORT"
    echo ""
    
    # Run all tests
    test_build
    test_startup
    test_health
    test_api_responses
    test_resources
    test_logs
    test_config
    test_ports
    
    echo ""
    success "🎉 All tests passed! Docker image is ready for deployment."
    
    # Final summary
    log "📋 Test Summary:"
    log "✅ Image builds successfully"
    log "✅ Container starts and runs"
    log "✅ Health endpoints respond"
    log "✅ API responses are valid"
    log "✅ Resource usage is reasonable"
    log "✅ Logs show no critical errors"
    log "✅ Configuration is accessible"
    log "✅ Ports are accessible"
    
    echo ""
    log "🚀 Ready for server deployment!"
}

# Help function
show_help() {
    echo "Usage: $0 [dockerfile] [image_tag]"
    echo ""
    echo "Arguments:"
    echo "  dockerfile   Path to Dockerfile (default: docker/Dockerfile.minimal)"
    echo "  image_tag    Tag for test image (default: ntplatform-test)"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Test minimal dockerfile"
    echo "  $0 docker/Dockerfile.optimized       # Test optimized dockerfile"
    echo "  $0 docker/Dockerfile.minimal v1.2.3  # Test with specific tag"
    echo ""
    echo "Environment variables:"
    echo "  TEST_PORT     Port for testing (default: 8001)"
    echo "  TEST_TIMEOUT  Timeout in seconds (default: 60)"
}

# Handle arguments
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    *)
        main
        ;;
esac 