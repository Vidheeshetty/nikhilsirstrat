# Backup & Rollback Strategy for NT Platform

## Overview
This document outlines the backup and rollback strategy for the NT Trading Platform deployment, ensuring zero-downtime deployments and quick recovery capabilities.

## 🎯 Key Objectives
- **Zero-downtime deployments** with automatic rollback on failure
- **Version management** with ability to rollback to any previous version
- **Data protection** with automated backups before each deployment
- **Quick recovery** in case of issues

## 📦 Docker Image Optimization

### Current Status
- **Before**: 1.44GB (with unnecessary dependencies)
- **After**: 343MB (76% reduction)
- **Achieved through**: Alpine Linux + minimal dependencies + multi-stage build

### Minimal Image Benefits
- ✅ Faster builds (less data to process)
- ✅ Faster deployments (less data to transfer)
- ✅ Reduced storage costs
- ✅ Better security (fewer attack vectors)
- ✅ No nautilus_trader reference directory issues

## 🔄 Deployment Strategies

### Option 1: GitHub-based Deployment (Recommended)
```bash
# Tag releases in GitHub
git tag -a v1.2.3 -m "Release v1.2.3"
git push origin v1.2.3

# Deploy specific version
./scripts/deploy/deploy_with_backup.sh v1.2.3

# Rollback to previous version
./scripts/deploy/deploy_with_backup.sh --rollback
```

### Option 2: Manual Deployment
```bash
# Create deployment package
./scripts/deploy/quick_deploy_minimal.sh

# Transfer to server and deploy
scp deploy_minimal_*.tar.gz root@139.84.166.225:/tmp/
ssh root@139.84.166.225 "cd /tmp && tar -xzf deploy_minimal_*.tar.gz"
```

## 🛡️ Backup Strategy

### Automated Backups
- **Before each deployment**: Automatic backup creation
- **Retention policy**: Keep last 5 backups
- **Backup contents**:
  - Docker images and tags
  - Configuration files
  - Application data
  - Runtime logs

### Backup Locations
```
/opt/ntplatform/backups/
├── backup_20241215_143022.tar.gz
├── backup_20241215_143022.images.txt
├── backup_20241214_102030.tar.gz
└── backup_20241214_102030.images.txt
```

### Manual Backup Commands
```bash
# Create immediate backup
./scripts/deploy/deploy_with_backup.sh --create-backup

# List available backups
./scripts/deploy/deploy_with_backup.sh --list-backups

# Check deployment status
./scripts/deploy/deploy_with_backup.sh --status
```

## 🔙 Rollback Procedures

### Automatic Rollback
- **Trigger**: Health check failure after deployment
- **Action**: Automatically restore from latest backup
- **Notification**: Log warnings and errors for investigation

### Manual Rollback
```bash
# Interactive rollback (shows available backups)
./scripts/deploy/deploy_with_backup.sh --rollback

# Rollback to specific backup
./scripts/deploy/deploy_with_backup.sh --rollback backup_20241215_143022.tar.gz
```

### Emergency Rollback (Server-side)
```bash
# If deployment scripts fail, manual server commands:
cd /opt/ntplatform
docker-compose down
cp docker-compose.yml.backup docker-compose.yml
docker-compose up -d
```

## 🏗️ Version Management

### Tagging Strategy
- **Production releases**: `v1.0.0`, `v1.1.0`, `v1.2.0`
- **Hotfixes**: `v1.0.1`, `v1.1.1`
- **Development**: `dev-20241215`, `feature-xyz`

### Image Management
- **Keep last 3 versions** in production
- **Automatic cleanup** of old images
- **Tagged releases** for easy identification

## 🔍 Health Monitoring

### Health Check Endpoints
- **Primary**: `http://139.84.166.225:8080/api/status`
- **Backup**: `http://139.84.166.225:8080/health`

### Monitoring Commands
```bash
# Check service health
curl -f http://139.84.166.225:8080/api/status

# Check Docker containers
docker-compose ps

# Check logs
docker-compose logs --tail=50
```

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] Code reviewed and tested
- [ ] Version tagged in Git
- [ ] Backup strategy confirmed
- [ ] Health check endpoints verified

### During Deployment
- [ ] Automatic backup created
- [ ] New image built and tested
- [ ] Health checks passing
- [ ] Rollback plan ready

### Post-Deployment
- [ ] Service health verified
- [ ] Performance metrics normal
- [ ] Logs reviewed for errors
- [ ] Old images cleaned up

## 🚨 Troubleshooting

### Common Issues
1. **Health check fails**: Automatic rollback triggered
2. **Image too large**: Use minimal Dockerfile
3. **Missing dependencies**: Check requirements-minimal.txt
4. **Configuration errors**: Verify config files included

### Recovery Commands
```bash
# Check container status
docker-compose ps

# View recent logs
docker-compose logs --tail=100

# Restart services
docker-compose restart

# Full reset (emergency)
docker-compose down
docker-compose up -d
```

## 📊 Performance Metrics

### Image Size Comparison
| Version | Size | Reduction |
|---------|------|-----------|
| Original | 1.44GB | - |
| Optimized | 343MB | 76% |
| Target | <300MB | 80% |

### Deployment Times
- **Build time**: ~2-3 minutes (vs 8-10 minutes)
- **Transfer time**: ~30 seconds (vs 2-3 minutes)
- **Startup time**: ~15 seconds (vs 45 seconds)

## 🔗 Related Documentation
- [Docker Optimization Guide](../docker/OPTIMIZATION_GUIDE.md)
- [Deployment Quick Start](DEPLOYMENT_QUICK_START.md)
- [Production Deployment](PRODUCTION_DEPLOYMENT.md) 