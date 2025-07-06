#!/bin/bash
# Deploy Paper Trading Platform to Remote Server

set -e

# Configuration
SERVER_USER="synaptic"
SERVER_HOST="139.84.166.225"
SERVER_PATH="/var/www/paper-trading-platform"
LOCAL_PROJECT_PATH="$(pwd)"
BACKUP_DIR="/var/backups/paper-trading"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Check if we can connect to the server
check_server_connection() {
    log "Checking server connection..."
    if ssh -o ConnectTimeout=10 "${SERVER_USER}@${SERVER_HOST}" "echo 'Connection successful'" > /dev/null 2>&1; then
        success "Server connection established"
    else
        error "Cannot connect to server ${SERVER_USER}@${SERVER_HOST}"
        error "Please ensure SSH access is configured and the server is reachable"
        exit 1
    fi
}

# Setup server environment
setup_server_environment() {
    log "Setting up server environment..."
    
    ssh "${SERVER_USER}@${SERVER_HOST}" << 'EOF'
        # Update system
        sudo apt update && sudo apt upgrade -y
        
        # Install required packages
        sudo apt install -y python3 python3-pip python3-venv git curl htop nginx
        
        # Install Docker
        if ! command -v docker &> /dev/null; then
            curl -fsSL https://get.docker.com -o get-docker.sh
            sudo sh get-docker.sh
            sudo usermod -aG docker $USER
            rm get-docker.sh
        fi
        
        # Install Docker Compose
        if ! command -v docker-compose &> /dev/null; then
            sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            sudo chmod +x /usr/local/bin/docker-compose
        fi
        
        # Create application directory
        sudo mkdir -p /var/www/paper-trading-platform
        sudo chown -R synaptic:synaptic /var/www/paper-trading-platform
        
        # Create backup directory
        sudo mkdir -p /var/backups/paper-trading
        sudo chown -R synaptic:synaptic /var/backups/paper-trading
        
        # Create logs directory
        sudo mkdir -p /var/log/paper-trading
        sudo chown -R synaptic:synaptic /var/log/paper-trading
EOF
    
    success "Server environment setup complete"
}

# Create deployment package
create_deployment_package() {
    log "Creating deployment package..."
    
    # Create temporary directory in /tmp to avoid spaces in path (macOS home has spaces)
    TEMP_DIR=$(mktemp -d /tmp/papertrade_pkg_XXXX)
    PACKAGE_NAME="/tmp/paper-trading-$(date +%Y%m%d_%H%M%S).tar.gz"
    
    # Copy project files (excluding unnecessary files)
    rsync -av \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.pytest_cache' \
        --exclude='venv' \
        --exclude='runlogs' \
        --exclude='.DS_Store' \
        --exclude='*.log' \
        --exclude='data' \
        --exclude='raw-data' \
        --exclude='notebooks' \
        --exclude='examples' \
        --exclude='legacy_src' \
        --exclude='legacy_tests' \
        --exclude='_summary.txts' \
        "${LOCAL_PROJECT_PATH}/" "${TEMP_DIR}/paper-trading-platform/"
    
    # Create archive
    cd "${TEMP_DIR}"
    tar -czf "${PACKAGE_NAME}" paper-trading-platform/
    
    # Move to local directory
    mv "${PACKAGE_NAME}" "${LOCAL_PROJECT_PATH}/"
    
    # Cleanup
    rm -rf "${TEMP_DIR}"
    
    echo "${LOCAL_PROJECT_PATH}/${PACKAGE_NAME}"
    success "Deployment package created: ${PACKAGE_NAME}"
}

# Deploy to server
deploy_to_server() {
    local package_file="$1"
    
    log "Deploying to server..."
    
    # Upload package
    log "Uploading deployment package..."
    scp "${package_file}" "${SERVER_USER}@${SERVER_HOST}:/tmp/"
    
    # Extract and setup on server
    ssh "${SERVER_USER}@${SERVER_HOST}" << EOF
        cd /tmp
        
        # Backup existing deployment if it exists
        if [ -d "${SERVER_PATH}" ]; then
            echo "Creating backup of existing deployment..."
            sudo tar -czf "${BACKUP_DIR}/backup_\$(date +%Y%m%d_%H%M%S).tar.gz" -C /var/www paper-trading-platform
        fi
        
        # Extract new deployment
        tar -xzf "$(basename ${package_file})"
        
        # Move to final location
        sudo rm -rf "${SERVER_PATH}"
        sudo mv paper-trading-platform "${SERVER_PATH}"
        sudo chown -R synaptic:synaptic "${SERVER_PATH}"
        
        # Cleanup
        rm "$(basename ${package_file})"
EOF
    
    success "Deployment uploaded to server"
}

# Setup Python environment on server
setup_python_environment() {
    log "Setting up Python environment on server..."
    
    ssh "${SERVER_USER}@${SERVER_HOST}" << EOF
        cd "${SERVER_PATH}"
        
        # Create virtual environment
        python3 -m venv venv
        source venv/bin/activate
        
        # Upgrade pip
        pip install --upgrade pip
        
        # Install requirements
        if [ -f requirements.txt ]; then
            pip install -r requirements.txt
        fi
        
        if [ -f requirements-paper-trading.txt ]; then
            pip install -r requirements-paper-trading.txt
        fi
        
        # Setup configuration
        python scripts/setup_paper_trading.py --skip-test
EOF
    
    success "Python environment setup complete"
}

# Setup systemd services
setup_systemd_services() {
    log "Setting up systemd services..."
    
    ssh "${SERVER_USER}@${SERVER_HOST}" << EOF
        # Create paper trading daemon service
        sudo tee /etc/systemd/system/paper-trading.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=Paper Trading Platform
After=network.target
Wants=network.target

[Service]
Type=forking
User=synaptic
Group=synaptic
WorkingDirectory=${SERVER_PATH}
Environment=PYTHONPATH=${SERVER_PATH}
ExecStart=${SERVER_PATH}/venv/bin/python scripts/run_paper_trading_daemon.py --daemon
ExecStop=/bin/kill -TERM \$MAINPID
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=paper-trading

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${SERVER_PATH}/runlogs
ReadWritePaths=/var/log/paper-trading

[Install]
WantedBy=multi-user.target
SERVICE_EOF

        # Create web interface service
        sudo tee /etc/systemd/system/paper-trading-web.service > /dev/null << 'WEB_SERVICE_EOF'
[Unit]
Description=Paper Trading Web Interface
After=network.target paper-trading.service
Wants=paper-trading.service

[Service]
Type=simple
User=synaptic
Group=synaptic
WorkingDirectory=${SERVER_PATH}
Environment=PYTHONPATH=${SERVER_PATH}
ExecStart=${SERVER_PATH}/venv/bin/python scripts/paper_trading_server.py --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
WEB_SERVICE_EOF

        # Reload systemd and enable services
        sudo systemctl daemon-reload
        sudo systemctl enable paper-trading
        sudo systemctl enable paper-trading-web
EOF
    
    success "Systemd services configured"
}

# Setup Nginx reverse proxy
setup_nginx() {
    log "Setting up Nginx reverse proxy..."
    
    ssh "${SERVER_USER}@${SERVER_HOST}" << 'EOF'
        # Create Nginx configuration
        sudo tee /etc/nginx/sites-available/paper-trading > /dev/null << 'NGINX_EOF'
server {
    listen 80;
    server_name _;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Static files (if any)
    location /static/ {
        alias /var/www/paper-trading-platform/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
NGINX_EOF

        # Enable site
        sudo ln -sf /etc/nginx/sites-available/paper-trading /etc/nginx/sites-enabled/
        sudo rm -f /etc/nginx/sites-enabled/default
        
        # Test configuration
        sudo nginx -t
        
        # Restart Nginx
        sudo systemctl restart nginx
        sudo systemctl enable nginx
EOF
    
    success "Nginx reverse proxy configured"
}

# Setup firewall
setup_firewall() {
    log "Setting up firewall..."
    
    ssh "${SERVER_USER}@${SERVER_HOST}" << 'EOF'
        # Enable UFW
        sudo ufw --force enable
        
        # Allow SSH (important!)
        sudo ufw allow ssh
        
        # Allow HTTP and HTTPS
        sudo ufw allow 80
        sudo ufw allow 443
        
        # Allow direct access to app (optional)
        sudo ufw allow 8000
        
        # Show status
        sudo ufw status
EOF
    
    success "Firewall configured"
}

# Start services
start_services() {
    log "Starting services..."
    
    ssh "${SERVER_USER}@${SERVER_HOST}" << EOF
        cd "${SERVER_PATH}"
        
        # Start services
        sudo systemctl start paper-trading
        sudo systemctl start paper-trading-web
        
        # Check status
        sleep 5
        sudo systemctl status paper-trading --no-pager
        sudo systemctl status paper-trading-web --no-pager
EOF
    
    success "Services started"
}

# Verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    # Check if services are running
    ssh "${SERVER_USER}@${SERVER_HOST}" << 'EOF'
        echo "=== Service Status ==="
        sudo systemctl is-active paper-trading
        sudo systemctl is-active paper-trading-web
        sudo systemctl is-active nginx
        
        echo "=== Port Status ==="
        sudo netstat -tlnp | grep :80
        sudo netstat -tlnp | grep :8000
        
        echo "=== Application Health ==="
        curl -s http://localhost:8000/api/status || echo "API not responding"
EOF
    
    # Get server IP for external access
    SERVER_IP=$(ssh "${SERVER_USER}@${SERVER_HOST}" "curl -s ifconfig.me || echo 'IP detection failed'")
    
    success "Deployment verification complete"
    
    echo ""
    echo "🚀 Paper Trading Platform Deployed Successfully!"
    echo "================================================"
    echo ""
    echo "📊 Web Dashboard:    http://${SERVER_IP}/"
    echo "🔗 Direct Access:    http://${SERVER_IP}:8000/"
    echo "🖥️  Server SSH:       ssh ${SERVER_USER}@${SERVER_HOST}"
    echo ""
    echo "📁 Server Path:      ${SERVER_PATH}"
    echo "📋 Logs Command:     ssh ${SERVER_USER}@${SERVER_HOST} 'sudo journalctl -u paper-trading -f'"
    echo "⚙️  Config File:      ${SERVER_PATH}/config/paper_trading.yaml"
    echo ""
    echo "🔧 Management Commands (run on server):"
    echo "   Start:    sudo systemctl start paper-trading paper-trading-web"
    echo "   Stop:     sudo systemctl stop paper-trading paper-trading-web"
    echo "   Restart:  sudo systemctl restart paper-trading paper-trading-web"
    echo "   Status:   sudo systemctl status paper-trading paper-trading-web"
    echo "   Logs:     sudo journalctl -u paper-trading -f"
    echo ""
}

# Cleanup local files
cleanup() {
    log "Cleaning up local files..."
    if [ -f "${LOCAL_PROJECT_PATH}/paper-trading-"*.tar.gz ]; then
        rm -f "${LOCAL_PROJECT_PATH}/paper-trading-"*.tar.gz
        success "Local deployment package cleaned up"
    fi
}

# Main deployment function
main() {
    echo "🚀 Paper Trading Platform Server Deployment"
    echo "============================================"
    echo ""
    echo "Target Server: ${SERVER_USER}@${SERVER_HOST}"
    echo "Deploy Path:   ${SERVER_PATH}"
    echo ""
    
    case "${1:-full}" in
        "full")
            check_server_connection
            setup_server_environment
            package_file=$(create_deployment_package)
            deploy_to_server "${package_file}"
            setup_python_environment
            setup_systemd_services
            setup_nginx
            setup_firewall
            start_services
            verify_deployment
            cleanup
            ;;
        "update")
            check_server_connection
            package_file=$(create_deployment_package)
            deploy_to_server "${package_file}"
            setup_python_environment
            ssh "${SERVER_USER}@${SERVER_HOST}" "sudo systemctl restart paper-trading paper-trading-web"
            verify_deployment
            cleanup
            ;;
        "restart")
            check_server_connection
            ssh "${SERVER_USER}@${SERVER_HOST}" "sudo systemctl restart paper-trading paper-trading-web nginx"
            verify_deployment
            ;;
        "status")
            check_server_connection
            ssh "${SERVER_USER}@${SERVER_HOST}" << 'EOF'
                echo "=== Service Status ==="
                sudo systemctl status paper-trading --no-pager
                sudo systemctl status paper-trading-web --no-pager
                sudo systemctl status nginx --no-pager
                
                echo "=== Application Status ==="
                curl -s http://localhost:8000/api/status | python3 -m json.tool || echo "API not responding"
EOF
            ;;
        "logs")
            check_server_connection
            ssh "${SERVER_USER}@${SERVER_HOST}" "sudo journalctl -u paper-trading -u paper-trading-web -f"
            ;;
        "prep")
            # Only prepare the server: install packages and create directories. No code upload.
            check_server_connection
            setup_server_environment
            echo "\n🛠️  Server prepared. You can deploy later with ./scripts/deploy_to_server.sh update or full.";
            ;;
        *)
            echo "Usage: $0 {full|update|restart|status|logs|prep}"
            echo ""
            echo "Commands:"
            echo "  full     - Full deployment (default)"
            echo "  update   - Update code and restart services"
            echo "  restart  - Restart services"
            echo "  status   - Check service status"
            echo "  logs     - Show live logs"
            echo "  prep     - Prepare the server for deployment"
            exit 1
            ;;
    esac
}

# Run main function
main "$@" 