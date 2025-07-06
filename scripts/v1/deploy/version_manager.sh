#!/bin/bash

# Version Management System for NT Platform
# Usage: ./version_manager.sh [command] [options]

set -e

# Configuration
VERSION_FILE="deployment_versions.json"
VERSION_TABLE="deployment_versions.md"
DOCKER_REGISTRY="ntplatform"
SERVER_HOST="139.84.166.225"
SERVER_USER="root"

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

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Initialize version tracking file
init_version_tracking() {
    if [ ! -f "$VERSION_FILE" ]; then
        log "Initializing version tracking..."
        cat > "$VERSION_FILE" << 'EOF'
{
  "versions": [],
  "metadata": {
    "created": "",
    "last_updated": "",
    "total_deployments": 0
  }
}
EOF
        # Update metadata
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        jq ".metadata.created = \"$timestamp\" | .metadata.last_updated = \"$timestamp\"" "$VERSION_FILE" > tmp.$$ && mv tmp.$$ "$VERSION_FILE"
        success "Version tracking initialized"
    fi
}

# Add a new version
add_version() {
    local version_tag="$1"
    local deployment_status="$2"
    local notes="$3"
    
    if [ -z "$version_tag" ]; then
        error "Version tag is required"
        return 1
    fi
    
    init_version_tracking
    
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local local_timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    local git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    local git_branch=$(git branch --show-current 2>/dev/null || echo "unknown")
    
    # Get Docker image size if available
    local image_size="unknown"
    if docker images "$DOCKER_REGISTRY:$version_tag" --format "{{.Size}}" | grep -q .; then
        image_size=$(docker images "$DOCKER_REGISTRY:$version_tag" --format "{{.Size}}")
    fi
    
    # Create version entry
    local version_entry=$(cat << EOF
{
  "version": "$version_tag",
  "timestamp": "$timestamp",
  "local_timestamp": "$local_timestamp",
  "status": "$deployment_status",
  "git_commit": "$git_commit",
  "git_branch": "$git_branch",
  "image_size": "$image_size",
  "notes": "$notes",
  "deployed_by": "$(whoami)",
  "deployment_duration": "unknown"
}
EOF
)
    
    # Add to versions array and update metadata
    jq --argjson entry "$version_entry" \
       --arg timestamp "$timestamp" \
       '.versions += [$entry] | 
        .metadata.last_updated = $timestamp | 
        .metadata.total_deployments += 1' \
       "$VERSION_FILE" > tmp.$$ && mv tmp.$$ "$VERSION_FILE"
    
    success "Version $version_tag added to tracking"
    generate_table
}

# Update version status
update_version_status() {
    local version_tag="$1"
    local new_status="$2"
    local duration="$3"
    
    if [ -z "$version_tag" ] || [ -z "$new_status" ]; then
        error "Version tag and status are required"
        return 1
    fi
    
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Update the version entry
    jq --arg version "$version_tag" \
       --arg status "$new_status" \
       --arg timestamp "$timestamp" \
       --arg duration "$duration" \
       '(.versions[] | select(.version == $version)) |= 
        (.status = $status | .last_updated = $timestamp | .deployment_duration = $duration) |
        .metadata.last_updated = $timestamp' \
       "$VERSION_FILE" > tmp.$$ && mv tmp.$$ "$VERSION_FILE"
    
    success "Version $version_tag status updated to $new_status"
    generate_table
}

# Generate markdown table
generate_table() {
    init_version_tracking
    
    log "Generating version table..."
    
    cat > "$VERSION_TABLE" << 'EOF'
# Deployment Version History

## Overview
This table tracks all deployment versions for the NT Trading Platform.

EOF
    
    # Add metadata
    local total_deployments=$(jq -r '.metadata.total_deployments' "$VERSION_FILE")
    local last_updated=$(jq -r '.metadata.last_updated' "$VERSION_FILE")
    local created=$(jq -r '.metadata.created' "$VERSION_FILE")
    
    cat >> "$VERSION_TABLE" << EOF
**Statistics:**
- Total Deployments: $total_deployments
- First Tracked: $created
- Last Updated: $last_updated

## Version History

| Version | Date | Status | Duration | Image Size | Git Commit | Branch | Deployed By | Notes |
|---------|------|--------|----------|------------|------------|---------|-------------|-------|
EOF
    
    # Add version entries (newest first)
    jq -r '.versions | reverse | .[] | 
           [.version, .local_timestamp, .status, .deployment_duration, .image_size, .git_commit, .git_branch, .deployed_by, .notes] | 
           @tsv' "$VERSION_FILE" | while IFS=$'\t' read -r version timestamp status duration size commit branch user notes; do
        
        # Format status with emoji
        case "$status" in
            "success") status_display="✅ Success" ;;
            "failed") status_display="❌ Failed" ;;
            "in_progress") status_display="🔄 In Progress" ;;
            "rolled_back") status_display="🔙 Rolled Back" ;;
            *) status_display="⚪ $status" ;;
        esac
        
        # Truncate long notes
        if [ ${#notes} -gt 30 ]; then
            notes="${notes:0:27}..."
        fi
        
        echo "| $version | $timestamp | $status_display | $duration | $size | $commit | $branch | $user | $notes |" >> "$VERSION_TABLE"
    done
    
    # Add server status section
    cat >> "$VERSION_TABLE" << 'EOF'

## Current Server Status

EOF
    
    # Try to get current server version
    local current_version=$(ssh "$SERVER_USER@$SERVER_HOST" "cd /opt/ntplatform && docker-compose ps --format json 2>/dev/null | jq -r '.[0].Image' 2>/dev/null | cut -d':' -f2" 2>/dev/null || echo "unknown")
    
    cat >> "$VERSION_TABLE" << EOF
- **Current Version**: $current_version
- **Server**: $SERVER_HOST
- **Last Check**: $(date "+%Y-%m-%d %H:%M:%S")

## Commands

\`\`\`bash
# View version history
./scripts/deploy/version_manager.sh list

# Add new version
./scripts/deploy/version_manager.sh add v1.2.3 success "Fixed login issue"

# Update version status
./scripts/deploy/version_manager.sh update v1.2.3 success "25m 30s"

# Show current server version
./scripts/deploy/version_manager.sh current

# Clean old versions (keep last 10)
./scripts/deploy/version_manager.sh clean
\`\`\`
EOF
    
    success "Version table generated: $VERSION_TABLE"
}

# List versions in terminal
list_versions() {
    init_version_tracking
    
    echo -e "${CYAN}📋 Deployment Version History${NC}"
    echo -e "${CYAN}=============================${NC}"
    echo ""
    
    # Show statistics
    local total=$(jq -r '.metadata.total_deployments' "$VERSION_FILE")
    local last_updated=$(jq -r '.metadata.last_updated' "$VERSION_FILE")
    echo -e "${BLUE}Total Deployments:${NC} $total"
    echo -e "${BLUE}Last Updated:${NC} $last_updated"
    echo ""
    
    # Show table header
    printf "%-12s %-20s %-15s %-10s %-10s %-10s %-15s\n" "VERSION" "DATE" "STATUS" "DURATION" "SIZE" "COMMIT" "BRANCH"
    printf "%-12s %-20s %-15s %-10s %-10s %-10s %-15s\n" "--------" "----" "------" "--------" "----" "------" "------"
    
    # Show versions (newest first)
    jq -r '.versions | reverse | .[] | 
           [.version, .local_timestamp, .status, .deployment_duration, .image_size, .git_commit, .git_branch] | 
           @tsv' "$VERSION_FILE" | while IFS=$'\t' read -r version timestamp status duration size commit branch; do
        
        # Color code status
        case "$status" in
            "success") status_color="${GREEN}✅ $status${NC}" ;;
            "failed") status_color="${RED}❌ $status${NC}" ;;
            "in_progress") status_color="${YELLOW}🔄 $status${NC}" ;;
            "rolled_back") status_color="${YELLOW}🔙 $status${NC}" ;;
            *) status_color="⚪ $status" ;;
        esac
        
        # Truncate long fields
        timestamp_short=$(echo "$timestamp" | cut -d' ' -f1,2 | cut -c1-19)
        
        printf "%-12s %-20s %-25s %-10s %-10s %-10s %-15s\n" \
               "$version" "$timestamp_short" "$status_color" "$duration" "$size" "$commit" "$branch"
    done
}

# Get current server version
get_current_version() {
    log "Checking current server version..."
    
    local current_version=$(ssh "$SERVER_USER@$SERVER_HOST" \
        "cd /opt/ntplatform && docker-compose ps --format json 2>/dev/null | jq -r '.[0].Image' 2>/dev/null | cut -d':' -f2" \
        2>/dev/null || echo "unknown")
    
    echo -e "${CYAN}Current Server Version:${NC} $current_version"
    
    # Show version details if available
    if [ "$current_version" != "unknown" ]; then
        local version_info=$(jq -r --arg version "$current_version" \
            '.versions[] | select(.version == $version) | 
             "Deployed: " + .local_timestamp + " | Status: " + .status + " | Size: " + .image_size' \
            "$VERSION_FILE" 2>/dev/null || echo "No local record found")
        
        echo -e "${BLUE}Details:${NC} $version_info"
    fi
}

# Clean old versions
clean_versions() {
    local keep_count=${1:-10}
    
    log "Cleaning old versions (keeping last $keep_count)..."
    
    # Keep only the last N versions
    jq --arg keep "$keep_count" \
       '.versions = (.versions | reverse | .[:($keep | tonumber)] | reverse)' \
       "$VERSION_FILE" > tmp.$$ && mv tmp.$$ "$VERSION_FILE"
    
    success "Cleaned old versions, kept last $keep_count"
    generate_table
}

# Export versions to CSV
export_csv() {
    local csv_file="deployment_versions_$(date +%Y%m%d_%H%M%S).csv"
    
    log "Exporting to CSV: $csv_file"
    
    # CSV header
    echo "Version,Date,Status,Duration,ImageSize,GitCommit,GitBranch,DeployedBy,Notes" > "$csv_file"
    
    # CSV data
    jq -r '.versions | reverse | .[] | 
           [.version, .local_timestamp, .status, .deployment_duration, .image_size, .git_commit, .git_branch, .deployed_by, .notes] | 
           @csv' "$VERSION_FILE" >> "$csv_file"
    
    success "Exported to $csv_file"
}

# Show help
show_help() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  list                    List all versions in terminal"
    echo "  add <version> <status> [notes]  Add new version"
    echo "  update <version> <status> [duration]  Update version status"
    echo "  current                 Show current server version"
    echo "  table                   Generate markdown table"
    echo "  clean [count]           Clean old versions (default: keep 10)"
    echo "  export                  Export to CSV"
    echo "  init                    Initialize version tracking"
    echo ""
    echo "Examples:"
    echo "  $0 list"
    echo "  $0 add v1.2.3 success 'Fixed login bug'"
    echo "  $0 update v1.2.3 success '25m 30s'"
    echo "  $0 current"
    echo "  $0 clean 5"
}

# Main command handler
case "${1:-list}" in
    "list")
        list_versions
        ;;
    "add")
        add_version "$2" "$3" "$4"
        ;;
    "update")
        update_version_status "$2" "$3" "$4"
        ;;
    "current")
        get_current_version
        ;;
    "table")
        generate_table
        ;;
    "clean")
        clean_versions "$2"
        ;;
    "export")
        export_csv
        ;;
    "init")
        init_version_tracking
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac 