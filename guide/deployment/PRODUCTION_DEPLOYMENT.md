# Production Deployment Guide

## Overview

This guide covers deploying the paper trading platform as a production-ready service on a dedicated server. The platform can run as a background daemon with web-based monitoring and control.

## Architecture Options

### 1. Background Daemon (Silent Thread)
- Runs as a system daemon/service
- No console output (logs to files)
- Remote control via files/API
- Automatic restart on failure
- Process monitoring

### 2. Containerized Deployment
- Docker-based deployment
- Microservices architecture
- Easy scaling and management
- Integrated monitoring stack
- Production-ready setup

### 3. Server Deployment Options
- **Local Server**: Dedicated machine in your network
- **Cloud VPS**: DigitalOcean, AWS EC2, Google Cloud
- **Kubernetes**: For enterprise-scale deployment

## Quick Start

### Option 1: Background Daemon (Recommended for Single Server)

```bash
# 1. Start as background daemon
python scripts/run_paper_trading_daemon.py --daemon

# 2. Start web interface
python scripts/paper_trading_server.py &

# 3. Access dashboard
open http://localhost:8000
```

### Option 2: Docker Deployment (Recommended for Production)

```bash
# 1. Deploy with Docker
./scripts/deploy_server.sh deploy

# 2. Access services
# Web Dashboard: http://localhost:8000
# Grafana: http://localhost:3000
# Prometheus: http://localhost:9090
```

## Detailed Setup

### Prerequisites

#### System Requirements
- **OS**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows
- **RAM**: Minimum 4GB, Recommended 8GB+
- **CPU**: 2+ cores
- **Storage**: 50GB+ free space
- **Network**: Stable internet connection

#### Software Requirements
- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- Git

### Server Setup

#### 1. Initial Server Configuration

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip git curl htop

# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2. Clone and Setup Project

```bash
# Clone repository
git clone <your-repo-url> /opt/paper-trading
cd /opt/paper-trading

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-paper-trading.txt

# Setup configuration
python scripts/setup_paper_trading.py
```

### Deployment Methods

## Method 1: Background Daemon

### Setup as System Service

Create systemd service file:

```bash
sudo nano /etc/systemd/system/paper-trading.service
```

```ini
[Unit]
Description=Paper Trading Platform
After=network.target
Wants=network.target

[Service]
Type=forking
User=trader
Group=trader
WorkingDirectory=/opt/paper-trading
Environment=PYTHONPATH=/opt/paper-trading
ExecStart=/opt/paper-trading/venv/bin/python scripts/run_paper_trading_daemon.py --daemon
ExecStop=/bin/kill -TERM $MAINPID
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
ReadWritePaths=/opt/paper-trading/runlogs

[Install]
WantedBy=multi-user.target
```

Enable and start service:

```bash
# Create user
sudo useradd -r -s /bin/false trader
sudo chown -R trader:trader /opt/paper-trading

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable paper-trading
sudo systemctl start paper-trading

# Check status
sudo systemctl status paper-trading
```

### Web Interface Service

```bash
sudo nano /etc/systemd/system/paper-trading-web.service
```

```ini
[Unit]
Description=Paper Trading Web Interface
After=network.target paper-trading.service
Wants=paper-trading.service

[Service]
Type=simple
User=trader
Group=trader
WorkingDirectory=/opt/paper-trading
Environment=PYTHONPATH=/opt/paper-trading
ExecStart=/opt/paper-trading/venv/bin/python scripts/paper_trading_server.py --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable paper-trading-web
sudo systemctl start paper-trading-web
```

### Daemon Control Commands

```bash
# Start daemon
python scripts/run_paper_trading_daemon.py --daemon

# Stop daemon
python scripts/run_paper_trading_daemon.py --stop

# Check status
python scripts/run_paper_trading_daemon.py --status

# Restart daemon
python scripts/run_paper_trading_daemon.py --restart

# View logs
tail -f runlogs/papertrading/daemon.log
```

## Method 2: Docker Deployment

### Quick Deploy

```bash
# Deploy everything
./scripts/deploy_server.sh deploy

# Management commands
./scripts/deploy_server.sh start    # Start services
./scripts/deploy_server.sh stop     # Stop services
./scripts/deploy_server.sh restart  # Restart services
./scripts/deploy_server.sh logs     # View logs
./scripts/deploy_server.sh status   # Check status
./scripts/deploy_server.sh update   # Update deployment
```

### Manual Docker Setup

```bash
# Build and start core service
cd docker
docker-compose up -d paper-trading

# Start with monitoring stack
docker-compose up -d

# View logs
docker-compose logs -f paper-trading

# Scale if needed
docker-compose up -d --scale paper-trading=2
```

### Service URLs

- **Web Dashboard**: http://localhost:8000
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **PostgreSQL**: localhost:5432 (trader/trading123)

## Remote Access Setup

### Secure Remote Access

#### 1. Reverse Proxy with Nginx

```bash
sudo apt install nginx

# Create configuration
sudo nano /etc/nginx/sites-available/paper-trading
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
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
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/paper-trading /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 2. SSL Certificate with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

#### 3. Firewall Configuration

```bash
# Enable UFW
sudo ufw enable

# Allow necessary ports
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8000  # Direct access (optional)

# Check status
sudo ufw status
```

### VPN Access (Recommended)

For secure access, set up a VPN:

```bash
# Install WireGuard
sudo apt install wireguard

# Generate keys and configure
# (Follow WireGuard setup guide)
```

## Monitoring and Alerting

### Built-in Monitoring

The platform includes comprehensive monitoring:

1. **Health Checks**: Automatic health monitoring
2. **Performance Metrics**: CPU, memory, trading metrics
3. **Log Aggregation**: Centralized logging
4. **Real-time Dashboard**: Web-based monitoring

### External Monitoring

#### 1. Grafana Dashboards

Access Grafana at http://localhost:3000:

- **Login**: admin/admin123
- **Import dashboards** for trading metrics
- **Set up alerts** for critical events

#### 2. Prometheus Metrics

Custom metrics available at `/metrics` endpoint:

- Trading performance
- System resources
- Error rates
- Response times

#### 3. Log Monitoring

```bash
# Real-time log monitoring
tail -f runlogs/papertrading/daemon.log

# Log rotation setup
sudo nano /etc/logrotate.d/paper-trading
```

```
/opt/paper-trading/runlogs/papertrading/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 trader trader
}
```

### Alerting Setup

#### Email Alerts

Configure email alerts in `config/paper_trading.yaml`:

```yaml
alerting:
  email:
    enabled: true
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    username: "your-email@gmail.com"
    password: "app-password"
    recipients:
      - "trader@example.com"
  
  triggers:
    daily_loss_limit: 50000
    drawdown_limit: 0.15
    error_rate: 0.05
```

#### Webhook Alerts

```yaml
alerting:
  webhook:
    enabled: true
    url: "https://hooks.slack.com/your-webhook-url"
    
  triggers:
    emergency_stop: true
    large_loss: 25000
    system_error: true
```

## Security Considerations

### 1. System Security

```bash
# Update system regularly
sudo apt update && sudo apt upgrade

# Configure automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades

# Disable root login
sudo passwd -l root

# Configure SSH key authentication
# (Copy your public key to ~/.ssh/authorized_keys)
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart ssh
```

### 2. Application Security

- **API Authentication**: Implement API keys for web interface
- **Data Encryption**: Encrypt sensitive configuration data
- **Access Control**: Limit access to specific IP addresses
- **Regular Backups**: Automated backup of trading data

### 3. Network Security

- **Firewall**: Configure UFW or iptables
- **VPN**: Use VPN for remote access
- **SSL/TLS**: Use HTTPS for web interface
- **Network Monitoring**: Monitor for unusual traffic

## Backup and Recovery

### Automated Backups

```bash
# Create backup script
nano /opt/paper-trading/scripts/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/paper-trading"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup data
tar -czf "$BACKUP_DIR/data_$DATE.tar.gz" /opt/paper-trading/runlogs/

# Backup configuration
cp /opt/paper-trading/config/paper_trading.yaml "$BACKUP_DIR/config_$DATE.yaml"

# Clean old backups (keep 30 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

```bash
chmod +x /opt/paper-trading/scripts/backup.sh

# Add to crontab
crontab -e
# Add: 0 2 * * * /opt/paper-trading/scripts/backup.sh
```

### Cloud Backups

```bash
# Install rclone for cloud backups
curl https://rclone.org/install.sh | sudo bash

# Configure cloud storage
rclone config

# Automated cloud backup
rclone sync /opt/backups/paper-trading remote:paper-trading-backups
```

## Performance Optimization

### 1. System Optimization

```bash
# Increase file limits
echo "trader soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "trader hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Optimize network settings
echo "net.core.rmem_max = 16777216" | sudo tee -a /etc/sysctl.conf
echo "net.core.wmem_max = 16777216" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 2. Application Optimization

- **Database Indexing**: Optimize database queries
- **Caching**: Use Redis for session caching
- **Connection Pooling**: Optimize broker connections
- **Async Processing**: Use async/await for I/O operations

### 3. Resource Monitoring

```bash
# Monitor system resources
htop
iotop
nethogs

# Monitor application
docker stats  # For Docker deployment
systemctl status paper-trading  # For systemd service
```

## Troubleshooting

### Common Issues

#### 1. Service Won't Start

```bash
# Check logs
sudo journalctl -u paper-trading -f

# Check configuration
python -c "import yaml; yaml.safe_load(open('config/paper_trading.yaml'))"

# Check permissions
ls -la /opt/paper-trading/
```

#### 2. Web Interface Not Accessible

```bash
# Check if service is running
curl http://localhost:8000/api/status

# Check firewall
sudo ufw status

# Check nginx (if using)
sudo nginx -t
sudo systemctl status nginx
```

#### 3. Performance Issues

```bash
# Check system resources
free -h
df -h
top

# Check application logs
tail -f runlogs/papertrading/daemon.log

# Monitor network
netstat -tuln
```

### Recovery Procedures

#### 1. Service Recovery

```bash
# Restart services
sudo systemctl restart paper-trading
sudo systemctl restart paper-trading-web

# Or for Docker
docker-compose restart
```

#### 2. Data Recovery

```bash
# Restore from backup
tar -xzf /opt/backups/paper-trading/data_YYYYMMDD_HHMMSS.tar.gz -C /

# Restore configuration
cp /opt/backups/paper-trading/config_YYYYMMDD_HHMMSS.yaml config/paper_trading.yaml
```

## Maintenance

### Regular Maintenance Tasks

#### Daily
- Check system status
- Review trading logs
- Monitor performance metrics

#### Weekly
- Update system packages
- Review backup integrity
- Check disk space

#### Monthly
- Security audit
- Performance optimization
- Configuration review

### Update Procedures

```bash
# For systemd deployment
git pull origin main
sudo systemctl restart paper-trading

# For Docker deployment
./scripts/deploy_server.sh update
```

## Scaling Considerations

### Horizontal Scaling

- **Multiple Instances**: Run multiple trading instances
- **Load Balancing**: Use nginx for load balancing
- **Database Clustering**: Scale database for high availability

### Vertical Scaling

- **Resource Allocation**: Increase CPU/RAM
- **SSD Storage**: Use fast storage for logs
- **Network Optimization**: Optimize network settings

### Cloud Deployment

For large-scale deployment, consider:

- **Kubernetes**: Container orchestration
- **Cloud Services**: AWS ECS, Google Cloud Run
- **Managed Databases**: RDS, Cloud SQL
- **CDN**: CloudFlare for global access

## Cost Optimization

### Server Costs

- **VPS Providers**: DigitalOcean ($5-20/month), Linode, Vultr
- **Cloud Providers**: AWS t3.micro (free tier), Google Cloud e2-micro
- **Dedicated Servers**: Hetzner, OVH for high performance

### Resource Optimization

- **Memory Usage**: Optimize Python memory usage
- **CPU Usage**: Use async programming patterns
- **Storage**: Compress logs and data
- **Network**: Minimize API calls

## Conclusion

This production deployment guide provides multiple options for running the paper trading platform as a background service on dedicated servers. Choose the deployment method that best fits your requirements:

- **Systemd Service**: Simple, lightweight, direct control
- **Docker Deployment**: Scalable, portable, full monitoring stack
- **Cloud Deployment**: Highly available, managed infrastructure

The platform is designed to run reliably in production with comprehensive monitoring, alerting, and recovery capabilities. 