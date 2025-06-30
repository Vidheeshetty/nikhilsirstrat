# Quick Server Deployment Guide

## 🚀 Deploy to Server (139.84.166.225)

### One-Command Deployment

```bash
# Full deployment (paper-trading **plus** back-testing units)
./scripts/deploy_to_server.sh full

# Paper-trading-only deployment (skip all back-test services)
./scripts/deploy_to_server.sh paper
```

> 🛈  Use the **`paper`** mode on production boxes dedicated to live/paper trading.  
> It copies the full code-base (for future maintenance) but only registers these systemd services:
> `paper-trading.service`, `paper-trading-web.service`.  No `backtest-*` units are installed or started.

### What This Does

1. **Server Setup**:
   - Updates system packages
   - Installs Python 3, Docker, Nginx
   - Creates `/var/www/paper-trading-platform` directory
   - Sets proper permissions for `synaptic` user

2. **Application Deployment**:
   - Creates deployment package (excludes .git, logs, etc.)
   - Uploads to server via SSH
   - Extracts to `/var/www/paper-trading-platform`
   - Sets up Python virtual environment
   - Installs all dependencies

3. **Service Configuration**:
   - Creates systemd services for background operation
   - Configures Nginx reverse proxy
   - Sets up firewall rules
   - Enables auto-start on boot

4. **Security Setup**:
   - Runs services as `synaptic` user
   - Configures firewall (SSH, HTTP, HTTPS)
   - Sets security headers in Nginx
   - Isolates service permissions

### Access URLs

After deployment:
- **Web Dashboard**: http://139.84.166.225/
- **Direct API**: http://139.84.166.225:8000/
- **SSH Access**: `ssh synaptic@139.84.166.225`

### Management Commands

```bash
# Update code and restart
./scripts/deploy_to_server.sh update

# Restart services
./scripts/deploy_to_server.sh restart

# Check status
./scripts/deploy_to_server.sh status

# View logs
./scripts/deploy_to_server.sh logs
```

### Server Management (via SSH)

```bash
# Connect to server
ssh synaptic@139.84.166.225

# Service control
sudo systemctl start paper-trading paper-trading-web
sudo systemctl stop paper-trading paper-trading-web
sudo systemctl restart paper-trading paper-trading-web
sudo systemctl status paper-trading paper-trading-web

# View logs
sudo journalctl -u paper-trading -f
sudo journalctl -u paper-trading-web -f

# Check application
curl http://localhost:8000/api/status

# Configuration
nano /var/www/paper-trading-platform/config/paper_trading.yaml
```

### Directory Structure on Server

```
/var/www/paper-trading-platform/
├── config/
│   └── paper_trading.yaml
├── runlogs/
│   └── papertrading/
├── scripts/
│   ├── run_paper_trading_daemon.py
│   └── paper_trading_server.py
├── src/
├── utils/
└── venv/
```

### Troubleshooting

#### Service Issues
```bash
# Check service status
sudo systemctl status paper-trading paper-trading-web nginx

# View detailed logs
sudo journalctl -u paper-trading --since "1 hour ago"

# Restart all services
sudo systemctl restart paper-trading paper-trading-web nginx
```

#### Network Issues
```bash
# Check ports
sudo netstat -tlnp | grep -E ":(80|8000)"

# Check firewall
sudo ufw status

# Test local connectivity
curl -I http://localhost:8000/api/status
```

#### Permission Issues
```bash
# Fix ownership
sudo chown -R synaptic:synaptic /var/www/paper-trading-platform

# Check permissions
ls -la /var/www/paper-trading-platform/
```

### Features Enabled

- ✅ Background daemon operation (no console output)
- ✅ Web-based monitoring and control
- ✅ Automatic service restart on failure
- ✅ System service integration (starts on boot)
- ✅ Nginx reverse proxy with security headers
- ✅ Firewall configuration
- ✅ Proper user permissions and isolation
- ✅ Centralized logging via systemd journal
- ✅ Backup system for deployments

### Next Steps

1. **Configure Trading**: Edit `/var/www/paper-trading-platform/config/paper_trading.yaml`
2. **Enable Strategies**: Set `enabled: true` for desired strategies
3. **Monitor Operations**: Access web dashboard at http://139.84.166.225/
4. **Set Up SSL** (optional): Use Let's Encrypt for HTTPS

### Support

For issues:
1. Check service status: `./scripts/deploy_to_server.sh status`
2. View logs: `./scripts/deploy_to_server.sh logs`
3. SSH to server for detailed troubleshooting
4. Restart services if needed: `./scripts/deploy_to_server.sh restart` 