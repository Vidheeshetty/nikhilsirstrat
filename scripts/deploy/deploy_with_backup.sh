#!/bin/bash

# Enhanced deployment script with backup and rollback capability
# Includes local testing, backup creation, and automatic rollback on failure

set -e  # Exit on any error

# Configuration
DEPLOY_CONFIG_FILE="deployment_versions.json"
BACKUP_DIR="/tmp/paper_trading_backups"
MAX_BACKUPS=5
SERVER_HOST="139.84.166.225"
SERVER_PORT="22"
SERVER_USER="synaptic"
SERVER_PATH="/home/synaptic/NTbasedPlatform"
TARGET_URL="http://139.84.166.225:8080"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Get current version
get_current_version() {
    if [ -f "VERSION" ]; then
        cat VERSION | tr -d '\n'
    else
        echo "unknown"
    fi
}

# Update deployment tracking
update_deployment_status() {
    local version="$1"
    local status="$2"
    local duration="$3"
    local size="$4"
    
    if [ ! -f "$DEPLOY_CONFIG_FILE" ]; then
        echo '{"deployments": [], "last_updated": ""}' > "$DEPLOY_CONFIG_FILE"
    fi
    
    # Update the deployment record
    python3 -c "
import json
import datetime
from pathlib import Path

config_file = '$DEPLOY_CONFIG_FILE'
version = '$version'
status = '$status'
duration = '$duration'
size = '$size'

# Read existing config
try:
    with open(config_file, 'r') as f:
        config = json.load(f)
except:
    config = {'deployments': [], 'last_updated': ''}

# Find and update existing deployment or add new one
deployments = config.get('deployments', [])
updated = False

for deployment in deployments:
    if deployment.get('version') == version and deployment.get('status') in ['🔄 in_progress', '⚪ created']:
        deployment['status'] = status
        deployment['duration'] = duration
        deployment['size'] = size
        deployment['timestamp'] = datetime.datetime.now().isoformat() + 'Z'
        updated = True
        break

if not updated:
    # Add new deployment record
    deployments.append({
        'version': version,
        'timestamp': datetime.datetime.now().isoformat() + 'Z',
        'status': status,
        'duration': duration,
        'size': size,
        'commit': '$(git rev-parse --short HEAD 2>/dev/null || echo unknown)',
        'branch': '$(git branch --show-current 2>/dev/null || echo unknown)'
    })

config['deployments'] = deployments[-10:]  # Keep last 10 deployments
config['last_updated'] = datetime.datetime.now().isoformat() + 'Z'

with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)
"
}

# Pre-deployment: Clean Mac hidden files
clean_mac_files() {
    log_info "Cleaning Mac hidden files to prevent parquet corruption..."
    if [ -f "scripts/deploy/clean_mac_files.sh" ]; then
        ./scripts/deploy/clean_mac_files.sh
    else
        log_warning "Mac files cleaning script not found, cleaning manually..."
        find catalog-data -name '._*' -type f -delete 2>/dev/null || true
        find catalog-data -name '.DS_Store' -type f -delete 2>/dev/null || true
        log_success "Mac hidden files cleaned"
    fi
}

# Create backup on server
create_backup() {
    local backup_name="$1"
    
    log_info "Creating backup: $backup_name"
    
    ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST "
        mkdir -p $BACKUP_DIR
        cd $SERVER_PATH
        
        # Stop containers before backup
        docker-compose -f docker/docker-compose.yml down 2>/dev/null || true
        
        # Create backup
        tar -czf $BACKUP_DIR/$backup_name.tar.gz \
            --exclude='runlogs' \
            --exclude='logs' \
            --exclude='.git' \
            --exclude='venv' \
            --exclude='__pycache__' \
            .
            
        # Cleanup old backups (keep last $MAX_BACKUPS)
        cd $BACKUP_DIR
        ls -t *.tar.gz 2>/dev/null | tail -n +\$((MAX_BACKUPS + 1)) | xargs rm -f 2>/dev/null || true
        
        echo 'Backup created successfully'
    "
}

# Rollback to previous backup
rollback_deployment() {
    local backup_name="$1"
    
    log_warning "Rolling back to backup: $backup_name"
    
    ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST "
        cd $SERVER_PATH
        
        # Stop current containers
        docker-compose -f docker/docker-compose.yml down 2>/dev/null || true
        
        # Restore from backup
        if [ -f $BACKUP_DIR/$backup_name.tar.gz ]; then
            tar -xzf $BACKUP_DIR/$backup_name.tar.gz
            
            # Start containers
            docker-compose -f docker/docker-compose.yml up -d
            
            echo 'Rollback completed successfully'
        else
            echo 'Backup file not found: $backup_name.tar.gz'
            exit 1
        fi
    "
}

# Health check
health_check() {
    local max_attempts=6
    local attempt=1
    
    log_info "Performing health check..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$TARGET_URL/api/status" > /dev/null 2>&1; then
            log_success "Health check passed (attempt $attempt/$max_attempts)"
            return 0
        fi
        
        log_warning "Health check failed (attempt $attempt/$max_attempts), retrying in 10s..."
        sleep 10
        attempt=$((attempt + 1))
    done
    
    log_error "Health check failed after $max_attempts attempts"
    return 1
}

# Main deployment function
deploy() {
    local start_time=$(date +%s)
    local version=$(get_current_version)
    local backup_name="backup_${version}_$(date +%Y%m%d_%H%M%S)"
    
    log_info "🚀 Starting deployment of version $version"
    
    # Update status to in_progress
    update_deployment_status "$version" "🔄 in_progress" "unknown" "unknown"
    
    # Step 1: Clean Mac files
    clean_mac_files
    
    # Step 2: Create backup
    create_backup "$backup_name"
    
    # Step 3: Deploy to server
    log_info "Deploying to server..."
    
    ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST "
        cd $SERVER_PATH
        
        # Pull latest changes (if using git)
        git pull 2>/dev/null || echo 'Git pull skipped'
        
        # Stop containers
        docker-compose -f docker/docker-compose.yml down
        
        # Start containers
        docker-compose -f docker/docker-compose.yml up -d
        
        echo 'Deployment completed'
    "
    
    # Step 4: Health check
    if health_check; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        # Get deployment size (approximate)
        local size=$(du -sh . 2>/dev/null | cut -f1 || echo "unknown")
        
        update_deployment_status "$version" "✅ success" "${duration}s" "$size"
        log_success "🎉 Deployment successful! Version $version is live at $TARGET_URL"
        
        # Cleanup temporary files
        rm -f /tmp/trading-platform-*.tar.gz 2>/dev/null || true
        
    else
        log_error "Deployment failed health check, rolling back..."
        
        # Rollback
        if rollback_deployment "$backup_name"; then
            update_deployment_status "$version" "❌ failed (rolled back)" "unknown" "unknown"
            log_warning "Rollback completed. Previous version restored."
        else
            update_deployment_status "$version" "💥 failed (rollback failed)" "unknown" "unknown"
            log_error "Rollback failed! Manual intervention required."
        fi
        
        exit 1
    fi
}

# Script execution
if [ "$1" = "--rollback" ]; then
    if [ -z "$2" ]; then
        log_error "Usage: $0 --rollback <backup_name>"
        exit 1
    fi
    rollback_deployment "$2"
elif [ "$1" = "--list-backups" ]; then
    log_info "Available backups:"
    ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST "ls -la $BACKUP_DIR/*.tar.gz 2>/dev/null || echo 'No backups found'"
else
    deploy
fi 