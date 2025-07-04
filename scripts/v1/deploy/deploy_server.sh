#!/bin/bash
# Paper Trading Server Deployment Script

set -e

# Configuration
PROJECT_NAME="paper-trading-platform"
DOCKER_COMPOSE_FILE="docker/docker-compose.yml"
CONFIG_FILE="config/paper_trading.yaml"
BACKUP_DIR="backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
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

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    success "Docker and Docker Compose are available"
}

# Create necessary directories
setup_directories() {
    log "Setting up directories..."
    
    mkdir -p runlogs/papertrading
    mkdir -p config
    mkdir -p $BACKUP_DIR
    mkdir -p docker/grafana/dashboards
    mkdir -p docker/grafana/datasources
    mkdir -p docker/prometheus
    
    success "Directories created"
}

# Create default configuration if it doesn't exist
setup_config() {
    log "Setting up configuration..."
    
    if [ ! -f "$CONFIG_FILE" ]; then
        log "Creating default configuration..."
        python scripts/setup_paper_trading.py --skip-test
    else
        log "Configuration file already exists"
    fi
    
    success "Configuration setup complete"
}

# Create monitoring configuration files
setup_monitoring() {
    log "Setting up monitoring configuration..."
    
    # Prometheus configuration
    cat > docker/prometheus/prometheus.yml << EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'paper-trading'
    static_configs:
      - targets: ['paper-trading:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
EOF

    # Grafana datasource
    cat > docker/grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

    success "Monitoring configuration created"
}

# Backup existing data
backup_data() {
    if [ -d "runlogs" ]; then
        log "Creating backup of existing data..."
        BACKUP_NAME="backup_$(date +%Y%m%d_%H%M%S)"
        tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" runlogs/
        success "Backup created: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
    fi
}

# Build and start services
deploy() {
    log "Building and starting services..."
    
    # Build the application image
    docker-compose -f $DOCKER_COMPOSE_FILE build
    
    # Start services
    docker-compose -f $DOCKER_COMPOSE_FILE up -d
    
    success "Services started successfully"
}

# Check service health
check_health() {
    log "Checking service health..."
    
    # Wait for services to start
    sleep 30
    
    # Check main application
    if curl -f http://localhost:8000/api/status > /dev/null 2>&1; then
        success "Paper trading server is healthy"
    else
        error "Paper trading server is not responding"
        return 1
    fi
    
    # Check other services
    if docker-compose -f $DOCKER_COMPOSE_FILE ps | grep -q "Up"; then
        success "Docker services are running"
    else
        warning "Some Docker services may not be running properly"
    fi
}

# Show service URLs
show_urls() {
    echo ""
    echo "🚀 Paper Trading Platform Deployed Successfully!"
    echo "================================================"
    echo ""
    echo "📊 Web Dashboard:    http://localhost:8000"
    echo "📈 Grafana:          http://localhost:3000 (admin/admin123)"
    echo "🔍 Prometheus:       http://localhost:9090"
    echo "🗄️  PostgreSQL:      localhost:5432 (trader/trading123)"
    echo "📦 Redis:            localhost:6379"
    echo ""
    echo "📁 Data Location:    ./runlogs/papertrading/"
    echo "⚙️  Configuration:   ./config/paper_trading.yaml"
    echo "📋 Logs:            docker-compose -f $DOCKER_COMPOSE_FILE logs -f"
    echo ""
    echo "🔧 Management Commands:"
    echo "   Start:   docker-compose -f $DOCKER_COMPOSE_FILE up -d"
    echo "   Stop:    docker-compose -f $DOCKER_COMPOSE_FILE down"
    echo "   Logs:    docker-compose -f $DOCKER_COMPOSE_FILE logs -f paper-trading"
    echo "   Status:  docker-compose -f $DOCKER_COMPOSE_FILE ps"
    echo ""
}

# Stop services
stop() {
    log "Stopping services..."
    docker-compose -f $DOCKER_COMPOSE_FILE down
    success "Services stopped"
}

# Update deployment
update() {
    log "Updating deployment..."
    backup_data
    docker-compose -f $DOCKER_COMPOSE_FILE down
    docker-compose -f $DOCKER_COMPOSE_FILE build --no-cache
    docker-compose -f $DOCKER_COMPOSE_FILE up -d
    check_health
    success "Update complete"
}

# Show logs
logs() {
    docker-compose -f $DOCKER_COMPOSE_FILE logs -f "${1:-paper-trading}"
}

# Show status
status() {
    echo "Docker Services:"
    docker-compose -f $DOCKER_COMPOSE_FILE ps
    echo ""
    echo "Application Status:"
    curl -s http://localhost:8000/api/status | python -m json.tool || echo "Service not responding"
}

# Cleanup
cleanup() {
    log "Cleaning up..."
    docker-compose -f $DOCKER_COMPOSE_FILE down -v
    docker system prune -f
    success "Cleanup complete"
}

# Main function
main() {
    case "${1:-deploy}" in
        "deploy")
            check_docker
            setup_directories
            setup_config
            setup_monitoring
            backup_data
            deploy
            check_health
            show_urls
            ;;
        "stop")
            stop
            ;;
        "start")
            docker-compose -f $DOCKER_COMPOSE_FILE up -d
            check_health
            ;;
        "restart")
            stop
            docker-compose -f $DOCKER_COMPOSE_FILE up -d
            check_health
            ;;
        "update")
            update
            ;;
        "logs")
            logs "$2"
            ;;
        "status")
            status
            ;;
        "cleanup")
            cleanup
            ;;
        "backup")
            backup_data
            ;;
        *)
            echo "Usage: $0 {deploy|start|stop|restart|update|logs|status|cleanup|backup}"
            echo ""
            echo "Commands:"
            echo "  deploy   - Full deployment (default)"
            echo "  start    - Start services"
            echo "  stop     - Stop services"
            echo "  restart  - Restart services"
            echo "  update   - Update and redeploy"
            echo "  logs     - Show logs (optionally specify service)"
            echo "  status   - Show service status"
            echo "  cleanup  - Remove all containers and volumes"
            echo "  backup   - Backup current data"
            exit 1
            ;;
    esac
}

# Run main function
main "$@" 