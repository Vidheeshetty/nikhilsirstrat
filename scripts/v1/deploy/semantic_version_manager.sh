#!/bin/bash

# Semantic Version Manager for NT Platform
# Follows x.y.z (major.minor.patch) versioning best practices
# Synchronized with VERSION file for automation compatibility
# Usage: ./semantic_version_manager.sh [command] [options]

set -e

# Configuration
VERSION_FILE="deployment_versions.json"
VERSION_TABLE="deployment_versions.md"
CURRENT_VERSION_FILE=".current_version"
AUTOMATION_VERSION_FILE="VERSION"  # Main VERSION file for automation
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

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Validate semantic version format
validate_version() {
    local version="$1"
    
    # Remove 'v' prefix if present
    version=${version#v}
    
    # Check if version matches x.y.z pattern
    if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
        error "Invalid semantic version format: $version"
        echo "Expected format: x.y.z (e.g., 1.2.3) or x.y.z-suffix (e.g., 1.2.3-beta)"
        echo ""
        echo "Semantic Versioning Guidelines:"
        echo "- MAJOR (x): Breaking changes, incompatible API changes"
        echo "- MINOR (y): New features, backward compatible"
        echo "- PATCH (z): Bug fixes, backward compatible"
        echo "- SUFFIX: pre-release identifiers (alpha, beta, rc1, etc.)"
        return 1
    fi
    
    return 0
}

# Get current version from VERSION file (primary source)
get_current_version() {
    if [ -f "$AUTOMATION_VERSION_FILE" ]; then
        local version=$(cat "$AUTOMATION_VERSION_FILE" | tr -d '\n' | tr -d ' ')
        # Remove 'v' prefix if present
        version=${version#v}
        echo "$version"
    else
        echo "0.0.0"
    fi
}

# Set current version in both VERSION file and local tracking
set_current_version() {
    local version="$1"
    
    # Update main VERSION file (for automation)
    echo "v$version" > "$AUTOMATION_VERSION_FILE"
    
    # Update local tracking file
    echo "$version" > "$CURRENT_VERSION_FILE"
    
    log "Updated VERSION file to v$version"
}

# Sync version from VERSION file to local tracking
sync_version_from_file() {
    local file_version=$(get_current_version)
    local tracking_version="0.0.0"
    
    if [ -f "$CURRENT_VERSION_FILE" ]; then
        tracking_version=$(cat "$CURRENT_VERSION_FILE" | tr -d '\n' | tr -d ' ')
    fi
    
    if [ "$file_version" != "$tracking_version" ]; then
        warning "Version mismatch detected:"
        echo "  VERSION file: $file_version"
        echo "  Tracking:     $tracking_version"
        echo ""
        echo "Synchronizing to VERSION file..."
        echo "$file_version" > "$CURRENT_VERSION_FILE"
        success "Synchronized to version $file_version"
    fi
}

# Compare versions (returns 0 if v1 < v2, 1 if v1 >= v2)
version_compare() {
    local v1="$1"
    local v2="$2"
    
    # Remove 'v' prefix and any suffix
    v1=${v1#v}
    v2=${v2#v}
    v1=${v1%%-*}
    v2=${v2%%-*}
    
    # Split into components
    IFS='.' read -ra V1 <<< "$v1"
    IFS='.' read -ra V2 <<< "$v2"
    
    # Compare each component
    for i in 0 1 2; do
        local n1=${V1[i]:-0}
        local n2=${V2[i]:-0}
        
        if [ "$n1" -lt "$n2" ]; then
            return 0
        elif [ "$n1" -gt "$n2" ]; then
            return 1
        fi
    done
    
    return 1  # Equal versions
}

# Bump version
bump_version() {
    local bump_type="$1"
    local notes="$2"
    
    # Sync with VERSION file first
    sync_version_from_file
    
    local current_version=$(get_current_version)
    
    # Remove 'v' prefix and any suffix
    current_version=${current_version#v}
    current_version=${current_version%%-*}
    
    # Split into components
    IFS='.' read -ra VERSION <<< "$current_version"
    local major=${VERSION[0]:-0}
    local minor=${VERSION[1]:-0}
    local patch=${VERSION[2]:-0}
    
    case "$bump_type" in
        "major")
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        "minor")
            minor=$((minor + 1))
            patch=0
            ;;
        "patch")
            patch=$((patch + 1))
            ;;
        *)
            error "Invalid bump type: $bump_type"
            echo "Valid types: major, minor, patch"
            return 1
            ;;
    esac
    
    local new_version="$major.$minor.$patch"
    
    echo ""
    echo -e "${CYAN}📋 Version Bump Summary${NC}"
    echo "Current: $current_version"
    echo "New:     $new_version"
    echo "Type:    $bump_type"
    echo "Notes:   $notes"
    echo ""
    echo "This will update:"
    echo "  - VERSION file (for automation)"
    echo "  - Local version tracking"
    echo "  - Deployment history"
    echo ""
    
    read -p "🤔 Proceed with version bump? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Version bump cancelled."
        return 1
    fi
    
    set_current_version "$new_version"
    success "Version bumped to $new_version"
    
    # Add to version tracking
    add_version "$new_version" "created" "$notes"
    
    echo "$new_version"
}

# Set version to specific value (for migration)
set_version() {
    local target_version="$1"
    local notes="$2"
    
    if [ -z "$target_version" ]; then
        error "Target version is required"
        return 1
    fi
    
    # Validate version format
    if ! validate_version "$target_version"; then
        return 1
    fi
    
    # Remove 'v' prefix
    target_version=${target_version#v}
    
    local current_version=$(get_current_version)
    
    echo ""
    echo -e "${CYAN}📋 Version Set Summary${NC}"
    echo "Current: $current_version"
    echo "Target:  $target_version"
    echo "Notes:   $notes"
    echo ""
    echo "This will update:"
    echo "  - VERSION file (for automation)"
    echo "  - Local version tracking"
    echo "  - Deployment history"
    echo ""
    
    read -p "🤔 Proceed with version set? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Version set cancelled."
        return 1
    fi
    
    set_current_version "$target_version"
    success "Version set to $target_version"
    
    # Add to version tracking
    add_version "$target_version" "created" "$notes"
    
    echo "$target_version"
}

# Initialize version tracking
init_version_tracking() {
    if [ ! -f "$VERSION_FILE" ]; then
        log "Initializing semantic version tracking..."
        cat > "$VERSION_FILE" << 'EOF'
{
  "versions": [],
  "metadata": {
    "created": "",
    "last_updated": "",
    "total_deployments": 0,
    "versioning_scheme": "semantic"
  }
}
EOF
        # Update metadata
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        jq ".metadata.created = \"$timestamp\" | .metadata.last_updated = \"$timestamp\"" "$VERSION_FILE" > tmp.$$ && mv tmp.$$ "$VERSION_FILE"
        success "Semantic version tracking initialized"
    fi
    
    # Sync with VERSION file
    sync_version_from_file
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
    
    # Validate version format
    if ! validate_version "$version_tag"; then
        return 1
    fi
    
    init_version_tracking
    
    # Check if version already exists
    if jq -e --arg version "$version_tag" '.versions[] | select(.version == $version)' "$VERSION_FILE" >/dev/null 2>&1; then
        warning "Version $version_tag already exists, updating..."
        update_version_status "$version_tag" "$deployment_status" "unknown"
        return 0
    fi
    
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local local_timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    local git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    local git_branch=$(git branch --show-current 2>/dev/null || echo "unknown")
    
    # Get Docker image size if available (skip if Docker not available)
    local image_size="unknown"
    if command -v docker >/dev/null 2>&1; then
        if docker images "$DOCKER_REGISTRY:$version_tag" --format "{{.Size}}" 2>/dev/null | grep -q .; then
            image_size=$(docker images "$DOCKER_REGISTRY:$version_tag" --format "{{.Size}}")
        fi
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
    
    # Update VERSION file if deployment successful
    if [ "$new_status" = "success" ]; then
        set_current_version "$version_tag"
        success "Current version updated to $version_tag"
    fi
    
    success "Version $version_tag status updated to $new_status"
    generate_table
}

# Generate markdown table with semantic versioning info
generate_table() {
    init_version_tracking
    
    log "Generating semantic version table..."
    
    cat > "$VERSION_TABLE" << 'EOF'
# Semantic Version History

## Overview
This table tracks all deployment versions using semantic versioning (x.y.z) for the NT Trading Platform.
Synchronized with the main VERSION file for automation compatibility.

### Semantic Versioning Guidelines
- **MAJOR (x)**: Breaking changes, incompatible API changes
- **MINOR (y)**: New features, backward compatible  
- **PATCH (z)**: Bug fixes, backward compatible
- **SUFFIX**: Pre-release identifiers (alpha, beta, rc1, etc.)

EOF
    
    # Add metadata
    local total_deployments=$(jq -r '.metadata.total_deployments' "$VERSION_FILE")
    local last_updated=$(jq -r '.metadata.last_updated' "$VERSION_FILE")
    local created=$(jq -r '.metadata.created' "$VERSION_FILE")
    local current_version=$(get_current_version)
    local version_file_content=$(cat "$AUTOMATION_VERSION_FILE" 2>/dev/null || echo "not found")
    
    cat >> "$VERSION_TABLE" << EOF
**Statistics:**
- Current Version: **$current_version**
- VERSION File: **$version_file_content**
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
            "created") status_display="📝 Created" ;;
            *) status_display="⚪ $status" ;;
        esac
        
        # Truncate long notes
        if [ ${#notes} -gt 30 ]; then
            notes="${notes:0:27}..."
        fi
        
        echo "| $version | $timestamp | $status_display | $duration | $size | $commit | $branch | $user | $notes |" >> "$VERSION_TABLE"
    done
    
    # Add commands section
    cat >> "$VERSION_TABLE" << 'EOF'

## Version Management Commands

```bash
# Show current version (from VERSION file)
./scripts/deploy/semantic_version_manager.sh current

# Bump version
./scripts/deploy/semantic_version_manager.sh bump patch "Bug fixes"
./scripts/deploy/semantic_version_manager.sh bump minor "New features"
./scripts/deploy/semantic_version_manager.sh bump major "Breaking changes"

# Set specific version (for migration)
./scripts/deploy/semantic_version_manager.sh set 0.3.0 "Implement new versioning system"

# Deploy with auto-versioning
./scripts/deploy/semantic_version_manager.sh deploy patch "Fix login issue"

# List version history
./scripts/deploy/semantic_version_manager.sh list

# Validate version format
./scripts/deploy/semantic_version_manager.sh validate 1.2.3

# Sync with VERSION file
./scripts/deploy/semantic_version_manager.sh sync
```

## File Synchronization
- **VERSION file**: Primary source for automation (`cat VERSION`)
- **Local tracking**: Synchronized automatically (`cat .current_version`)
- **Deployment history**: Complete metadata in JSON format
EOF
    
    success "Semantic version table generated: $VERSION_TABLE"
}

# Deploy with automatic version bumping
deploy_with_versioning() {
    local bump_type="$1"
    local notes="$2"
    
    if [ -z "$bump_type" ]; then
        error "Bump type is required (major, minor, patch)"
        return 1
    fi
    
    # Bump version
    local new_version=$(bump_version "$bump_type" "$notes")
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    # Deploy with the new version
    log "Starting deployment with version $new_version..."
    if ./scripts/deploy/full_automated_deploy.sh "$new_version"; then
        success "Deployment completed successfully!"
        return 0
    else
        error "Deployment failed!"
        return 1
    fi
}

# Show help
show_help() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Semantic Version Management Commands:"
    echo "  current                     Show current version (from VERSION file)"
    echo "  bump <type> [notes]         Bump version (major/minor/patch)"
    echo "  set <version> [notes]       Set specific version"
    echo "  deploy <type> [notes]       Bump version and deploy"
    echo "  add <version> <status> [notes]  Add version manually"
    echo "  update <version> <status> [duration]  Update version status"
    echo "  list                        List all versions"
    echo "  table                       Generate markdown table"
    echo "  validate <version>          Validate version format"
    echo "  sync                        Sync with VERSION file"
    echo "  init                        Initialize version tracking"
    echo ""
    echo "Examples:"
    echo "  $0 current"
    echo "  $0 bump patch 'Fix login bug'"
    echo "  $0 bump minor 'Add new dashboard'"
    echo "  $0 bump major 'Breaking API changes'"
    echo "  $0 set 0.3.0 'Implement new versioning system'"
    echo "  $0 deploy patch 'Critical security fix'"
    echo "  $0 validate 1.2.3"
    echo "  $0 sync"
    echo ""
    echo "File Synchronization:"
    echo "  VERSION file: Primary source for automation"
    echo "  .current_version: Local tracking (auto-synced)"
    echo "  deployment_versions.json: Complete history"
    echo ""
    echo "Semantic Versioning Guidelines:"
    echo "  MAJOR: Breaking changes, incompatible API changes"
    echo "  MINOR: New features, backward compatible"
    echo "  PATCH: Bug fixes, backward compatible"
}

# Main command handler
case "${1:-current}" in
    "current")
        local version=$(get_current_version)
        local file_content=$(cat "$AUTOMATION_VERSION_FILE" 2>/dev/null || echo "not found")
        echo "Current version: $version"
        echo "VERSION file: $file_content"
        ;;
    "bump")
        bump_version "$2" "$3"
        ;;
    "set")
        set_version "$2" "$3"
        ;;
    "deploy")
        deploy_with_versioning "$2" "$3"
        ;;
    "add")
        add_version "$2" "$3" "$4"
        ;;
    "update")
        update_version_status "$2" "$3" "$4"
        ;;
    "list")
        # Use the original version manager for listing
        ./scripts/deploy/version_manager.sh list 2>/dev/null || echo "No version history available"
        ;;
    "table")
        generate_table
        ;;
    "validate")
        if validate_version "$2"; then
            success "Version $2 is valid"
        fi
        ;;
    "sync")
        sync_version_from_file
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