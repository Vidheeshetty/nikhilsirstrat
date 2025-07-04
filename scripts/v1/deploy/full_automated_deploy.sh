#!/bin/bash

# Full Automated Deployment Pipeline with Version Tracking
# Usage: ./full_automated_deploy.sh [version_tag] [--skip-quick-test]

set -e

# Configuration
VERSION_TAG=${1:-"latest"}
SKIP_QUICK_TEST=${2:-""}
DOCKERFILE="docker/Dockerfile.minimal"
DOCKER_REGISTRY="ntplatform"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

step() {
    echo -e "${CYAN}[STEP]${NC} $1"
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

# Progress tracking
TOTAL_STEPS=4
CURRENT_STEP=0

show_progress() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}         STEP $CURRENT_STEP of $TOTAL_STEPS: $1${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
}

# Version tracking functions
track_version_start() {
    log "📝 Starting version tracking for $VERSION_TAG..."
    ./scripts/deploy/version_manager.sh add "$VERSION_TAG" "in_progress" "Automated deployment started"
}

track_version_success() {
    local duration="$1"
    log "📝 Updating version tracking - SUCCESS"
    ./scripts/deploy/version_manager.sh update "$VERSION_TAG" "success" "$duration"
}

track_version_failure() {
    local failure_reason="$1"
    log "📝 Updating version tracking - FAILED"
    ./scripts/deploy/version_manager.sh update "$VERSION_TAG" "failed" "$failure_reason"
}

# Step 1: Quick Test
run_quick_test() {
    if [ "$SKIP_QUICK_TEST" = "--skip-quick-test" ]; then
        warning "Skipping quick test as requested"
        return 0
    fi
    
    show_progress "QUICK TEST (2-3 minutes)"
    
    log "Running quick validation test..."
    
    if ./scripts/deploy/quick_test.sh; then
        success "✅ Quick test passed!"
    else
        error "❌ Quick test failed!"
        echo ""
        echo "🔧 Troubleshooting tips:"
        echo "1. Check Docker is running"
        echo "2. Verify no port conflicts on 8001"
        echo "3. Review build errors above"
        echo "4. Fix issues and try again"
        track_version_failure "Quick test failed"
        exit 1
    fi
}

# Step 2: Comprehensive Test
run_comprehensive_test() {
    show_progress "COMPREHENSIVE TEST (5-10 minutes)"
    
    log "Running comprehensive validation test..."
    
    if ./scripts/deploy/test_docker_locally.sh $DOCKERFILE $DOCKER_REGISTRY:$VERSION_TAG; then
        success "✅ Comprehensive test passed!"
    else
        error "❌ Comprehensive test failed!"
        echo ""
        echo "🔧 Troubleshooting tips:"
        echo "1. Review detailed test output above"
        echo "2. Check container logs for errors"
        echo "3. Verify all API endpoints are working"
        echo "4. Check resource usage and configuration"
        echo "5. Fix issues and try again"
        track_version_failure "Comprehensive test failed"
        exit 1
    fi
}

# Step 3: Deployment
run_deployment() {
    show_progress "DEPLOYMENT TO SERVER (10-15 minutes)"
    
    log "Starting deployment to server..."
    
    if ./scripts/deploy/deploy_with_backup.sh $VERSION_TAG; then
        success "✅ Deployment completed successfully!"
    else
        error "❌ Deployment failed!"
        echo ""
        echo "🔧 Troubleshooting tips:"
        echo "1. Check server connectivity"
        echo "2. Verify backup was created"
        echo "3. Review deployment logs above"
        echo "4. Rollback may have been attempted automatically"
        echo "5. Check server status with: ./scripts/deploy/deploy_with_backup.sh --status"
        track_version_failure "Server deployment failed"
        exit 1
    fi
}

# Step 4: Post-Deployment Verification
run_verification() {
    show_progress "POST-DEPLOYMENT VERIFICATION (2-3 minutes)"
    
    log "Verifying deployment..."
    
    # Wait for services to stabilize
    log "Waiting for services to stabilize..."
    sleep 30
    
    # Check deployment status
    log "Checking deployment status..."
    if ./scripts/deploy/deploy_with_backup.sh --status; then
        success "✅ Deployment status check passed!"
    else
        warning "⚠️ Deployment status check had issues"
    fi
    
    # Verify service health
    log "Verifying service health..."
    local health_check_attempts=0
    local max_attempts=5
    
    while [ $health_check_attempts -lt $max_attempts ]; do
        if curl -f http://139.84.166.225:8080/api/status >/dev/null 2>&1; then
            success "✅ Service health check passed!"
            break
        else
            health_check_attempts=$((health_check_attempts + 1))
            if [ $health_check_attempts -lt $max_attempts ]; then
                warning "Health check attempt $health_check_attempts failed, retrying..."
                sleep 10
            else
                error "❌ Service health check failed after $max_attempts attempts!"
                echo ""
                echo "🔧 Troubleshooting tips:"
                echo "1. Check server logs: ./scripts/deploy/deploy_with_backup.sh --status"
                echo "2. Verify service is running: docker-compose ps"
                echo "3. Check for port conflicts or firewall issues"
                echo "4. Consider rollback if issues persist"
                track_version_failure "Service health check failed"
                exit 1
            fi
        fi
    done
    
    # Performance check
    log "Running performance check..."
    local response_time=$(curl -o /dev/null -s -w '%{time_total}' http://139.84.166.225:8080/api/status)
    if (( $(echo "$response_time < 2.0" | bc -l) )); then
        success "✅ Performance check passed! Response time: ${response_time}s"
    else
        warning "⚠️ Slow response time detected: ${response_time}s"
    fi
}

# Main execution
main() {
    echo -e "${CYAN}🚀 FULL AUTOMATED DEPLOYMENT PIPELINE${NC}"
    echo -e "${CYAN}=====================================${NC}"
    echo ""
    echo "📋 Deployment Configuration:"
    echo "   Version: $VERSION_TAG"
    echo "   Dockerfile: $DOCKERFILE"
    echo "   Registry: $DOCKER_REGISTRY"
    echo "   Target: http://139.84.166.225:8080"
    echo ""
    echo "⏱️ Estimated total time: 20-30 minutes"
    echo ""
    
    # Show current version history
    echo -e "${CYAN}📋 Recent Deployment History:${NC}"
    ./scripts/deploy/version_manager.sh list | tail -8
    echo ""
    
    # Confirmation prompt
    read -p "🤔 Proceed with automated deployment? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled by user."
        exit 0
    fi
    
    # Record start time
    START_TIME=$(date +%s)
    
    # Start version tracking
    track_version_start
    
    # Execute all steps
    run_quick_test
    run_comprehensive_test
    run_deployment
    run_verification
    
    # Calculate total time
    END_TIME=$(date +%s)
    TOTAL_TIME=$((END_TIME - START_TIME))
    MINUTES=$((TOTAL_TIME / 60))
    SECONDS=$((TOTAL_TIME % 60))
    DURATION="${MINUTES}m ${SECONDS}s"
    
    # Update version tracking with success
    track_version_success "$DURATION"
    
    # Final success message
    echo ""
    echo -e "${GREEN}🎉 DEPLOYMENT PIPELINE COMPLETED SUCCESSFULLY!${NC}"
    echo -e "${GREEN}=============================================${NC}"
    echo ""
    echo "📊 Deployment Summary:"
    echo "   ✅ Quick test: PASSED"
    echo "   ✅ Comprehensive test: PASSED"
    echo "   ✅ Deployment: SUCCESSFUL"
    echo "   ✅ Verification: PASSED"
    echo ""
    echo "⏱️ Total time: $DURATION"
    echo "🌐 Service URL: http://139.84.166.225:8080"
    echo "📊 Status: ./scripts/deploy/deploy_with_backup.sh --status"
    echo ""
    echo "📋 Version History:"
    echo "   View: ./scripts/deploy/version_manager.sh list"
    echo "   Table: cat deployment_versions.md"
    echo ""
    echo "🎯 Next steps:"
    echo "1. Monitor service logs for any issues"
    echo "2. Run functional tests if available"
    echo "3. Update documentation if needed"
    echo ""
}

# Error handling
handle_error() {
    local exit_code=$?
    echo ""
    error "❌ Deployment pipeline failed at step $CURRENT_STEP!"
    
    # Track failure if version tracking was started
    if [ -n "$VERSION_TAG" ]; then
        track_version_failure "Pipeline failed at step $CURRENT_STEP"
    fi
    
    echo ""
    echo "🔧 Recovery options:"
    echo "1. Fix the issue and re-run: $0 $VERSION_TAG"
    echo "2. Run individual steps manually"
    echo "3. Check server status: ./scripts/deploy/deploy_with_backup.sh --status"
    echo "4. Rollback if needed: ./scripts/deploy/deploy_with_backup.sh --rollback"
    echo "5. View version history: ./scripts/deploy/version_manager.sh list"
    echo ""
    exit $exit_code
}

# Set error trap
trap handle_error ERR

# Help function
show_help() {
    echo "Usage: $0 [version_tag] [--skip-quick-test]"
    echo ""
    echo "Full automated deployment pipeline that runs all 4 steps:"
    echo "  1. Quick Test (2-3 minutes)"
    echo "  2. Comprehensive Test (5-10 minutes)"
    echo "  3. Deployment to Server (10-15 minutes)"
    echo "  4. Post-Deployment Verification (2-3 minutes)"
    echo ""
    echo "Arguments:"
    echo "  version_tag        Tag for the deployment (default: latest)"
    echo "  --skip-quick-test  Skip the quick test step"
    echo ""
    echo "Examples:"
    echo "  $0                    # Deploy latest version"
    echo "  $0 v1.2.3             # Deploy specific version"
    echo "  $0 latest --skip-quick-test  # Skip quick test"
    echo ""
    echo "Version Management:"
    echo "  ./scripts/deploy/version_manager.sh list     # View version history"
    echo "  ./scripts/deploy/version_manager.sh current  # Current server version"
    echo "  cat deployment_versions.md                   # View detailed table"
    echo ""
    echo "Manual steps (if needed):"
    echo "  ./scripts/deploy/quick_test.sh"
    echo "  ./scripts/deploy/test_docker_locally.sh"
    echo "  ./scripts/deploy/deploy_with_backup.sh"
    echo "  ./scripts/deploy/deploy_with_backup.sh --status"
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