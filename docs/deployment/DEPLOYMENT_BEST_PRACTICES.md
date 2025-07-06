# Deployment Best Practices for NT Trading Platform

## Overview
This document outlines the essential best practices for deploying the NT Trading Platform, incorporating lessons learned from debugging and optimization efforts.

## 🏷️ Semantic Versioning (x.y.z)

### Version Format
All versions MUST follow semantic versioning: `x.y.z` or `x.y.z-suffix`

```
MAJOR.MINOR.PATCH[-SUFFIX]
  │     │     │      │
  │     │     │      └─ Pre-release (alpha, beta, rc1)
  │     │     └─ Bug fixes, backward compatible
  │     └─ New features, backward compatible  
  └─ Breaking changes, incompatible API changes
```

### Version Bumping Guidelines

#### PATCH (z) - Bug Fixes
- **When**: Bug fixes, security patches, minor improvements
- **Examples**: `1.2.3 → 1.2.4`
- **Impact**: Backward compatible, safe to auto-update

```bash
# Bug fix deployment
./scripts/deploy/semantic_version_manager.sh bump patch "Fix login authentication bug"
```

#### MINOR (y) - New Features  
- **When**: New features, enhancements, API additions
- **Examples**: `1.2.3 → 1.3.0`
- **Impact**: Backward compatible, new functionality added

```bash
# New feature deployment
./scripts/deploy/semantic_version_manager.sh bump minor "Add new trading dashboard"
```

#### MAJOR (x) - Breaking Changes
- **When**: Breaking changes, incompatible API changes, major rewrites
- **Examples**: `1.2.3 → 2.0.0`
- **Impact**: May break existing integrations, requires careful migration

```bash
# Breaking change deployment
./scripts/deploy/semantic_version_manager.sh bump major "Restructure API endpoints"
```

### Pre-release Versions
Use suffixes for pre-release versions:
- `1.2.3-alpha`: Early development version
- `1.2.3-beta`: Feature-complete, testing phase
- `1.2.3-rc1`: Release candidate

## 🚀 Deployment Workflow

### 1. Pre-Deployment Checklist
- [ ] **Code Review**: All changes reviewed and approved
- [ ] **Version Planning**: Determine appropriate version bump (patch/minor/major)
- [ ] **Documentation**: Update relevant documentation
- [ ] **Testing**: All tests passing locally
- [ ] **Dependencies**: Check for dependency updates/conflicts

### 2. Version Management
```bash
# Check current version
./scripts/deploy/semantic_version_manager.sh current

# Bump version with deployment
./scripts/deploy/semantic_version_manager.sh deploy patch "Fix critical security issue"
```

### 3. Automated Deployment Pipeline
```bash
# Full automated deployment (recommended)
./scripts/deploy/full_automated_deploy.sh v1.2.3

# Manual step-by-step (debugging)
./scripts/deploy/quick_test.sh
./scripts/deploy/test_docker_locally.sh
./scripts/deploy/deploy_with_backup.sh v1.2.3
```

### 4. Post-Deployment Verification
- [ ] **Health Checks**: Service responding correctly
- [ ] **Performance**: Response times within acceptable limits
- [ ] **Logs**: No critical errors in application logs
- [ ] **Functionality**: Key features working as expected

## 🐳 Docker Best Practices

### Image Optimization
Based on our optimization experience (7.58GB → 343MB):

#### 1. Use .dockerignore
```dockerignore
# Always exclude these from Docker builds
venv/
nautilus_trader/
data/
raw-data/
runlogs/
legacy_src/
old-code/
debug-code/
*.log
*.parquet
*.csv
```

#### 2. Multi-stage Builds
```dockerfile
# Build stage
FROM python:3.11-alpine as builder
RUN apk add --no-cache gcc g++ musl-dev
COPY requirements-minimal.txt .
RUN pip install --no-cache-dir -r requirements-minimal.txt

# Production stage  
FROM python:3.11-alpine as production
COPY --from=builder /opt/venv /opt/venv
# Only copy essential files
```

#### 3. Minimal Dependencies
- **Production**: Only runtime dependencies
- **Exclude**: jupyter, debugpy, mypy, testing frameworks
- **Use**: Alpine Linux base images

### Image Size Targets
- **Development**: < 1GB
- **Production**: < 500MB  
- **Minimal**: < 350MB

## 🧪 Testing Strategy

### Mandatory Testing Levels
1. **Quick Test** (2-3 minutes): Basic validation
2. **Comprehensive Test** (5-10 minutes): Full validation
3. **Deployment Integration**: Server deployment with rollback

### Testing Commands
```bash
# Level 1: Quick validation
./scripts/deploy/quick_test.sh

# Level 2: Comprehensive testing
./scripts/deploy/test_docker_locally.sh

# Level 3: Test-only mode (no deployment)
./scripts/deploy/deploy_with_backup.sh --test-only
```

### Testing Requirements
- **NEVER** deploy without passing all local tests
- **ALWAYS** test Docker images locally before server deployment
- **VERIFY** all API endpoints respond correctly
- **CHECK** resource usage and performance

## 🛡️ Backup & Rollback Strategy

### Automatic Backups
- **Created**: Before every deployment
- **Retention**: Last 5 versions
- **Contents**: Configuration, data, Docker images
- **Location**: `/opt/ntplatform/backups/`

### Rollback Procedures
```bash
# Automatic rollback (on deployment failure)
# - Triggered automatically if health checks fail
# - Restores from latest backup
# - Verifies rollback success

# Manual rollback
./scripts/deploy/deploy_with_backup.sh --rollback

# Emergency rollback (server-side)
cd /opt/ntplatform
docker-compose down
cp docker-compose.yml.backup docker-compose.yml
docker-compose up -d
```

## 📊 Version Tracking

### Automatic Tracking
Every deployment automatically tracks:
- Version number and timestamp
- Deployment status and duration
- Git commit and branch
- Docker image size
- Deployment notes
- Who deployed it

### Version History
```bash
# View version history
./scripts/deploy/semantic_version_manager.sh list

# Generate detailed table
./scripts/deploy/semantic_version_manager.sh table
cat deployment_versions.md

# Check current server version
./scripts/deploy/semantic_version_manager.sh current
```

## 🔧 Troubleshooting Guide

### Common Issues & Solutions

#### Docker Build Issues
- **Problem**: Large build context (>5GB)
- **Solution**: Check `.dockerignore`, exclude unnecessary files
- **Prevention**: Regular build context size monitoring

#### Event Loop Errors
- **Problem**: "no running event loop" in daemon mode
- **Solution**: Proper asyncio initialization in daemon context
- **Prevention**: Event loop validation in async code

#### Path Resolution Issues
- **Problem**: Relative paths fail in Docker containers
- **Solution**: Use absolute paths in docker-compose
- **Prevention**: Always use absolute paths for mounted files

#### Live Data Connection Issues
- **Problem**: Broker falling back to paper mode
- **Solution**: Separate data source from order execution
- **Prevention**: Proper broker integration testing

### Debugging Commands
```bash
# Check deployment status
./scripts/deploy/deploy_with_backup.sh --status

# View recent logs
ssh root@139.84.166.225 "docker-compose logs --tail=50"

# Check resource usage
ssh root@139.84.166.225 "docker stats"

# Verify health endpoints
curl -f http://139.84.166.225:8080/api/status
```

## 📈 Performance Monitoring

### Key Metrics
- **Response Time**: < 2 seconds for API endpoints
- **Memory Usage**: < 500MB per container
- **CPU Usage**: Monitor during peak loads
- **Image Size**: Track size growth over time

### Monitoring Commands
```bash
# Performance check
curl -w '%{time_total}' http://139.84.166.225:8080/api/status

# Resource monitoring
docker stats --no-stream

# Image size tracking
docker images ntplatform:* --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"
```

## 🔐 Security Best Practices

### Container Security
- **Non-root user**: Always run containers as non-root
- **Minimal attack surface**: Use minimal base images
- **Regular updates**: Keep base images updated
- **Secrets management**: Never hardcode secrets

### Deployment Security
- **SSH keys**: Use key-based authentication
- **Firewall**: Restrict access to necessary ports
- **HTTPS**: Use SSL/TLS for all communications
- **Backup encryption**: Encrypt sensitive backups

## 📋 Deployment Checklist

### Before Deployment
- [ ] Version number determined and validated
- [ ] All tests passing locally
- [ ] Documentation updated
- [ ] Backup strategy confirmed
- [ ] Rollback plan ready

### During Deployment
- [ ] Version tracking started
- [ ] Local tests completed
- [ ] Server backup created
- [ ] Deployment health checks passed
- [ ] Performance verification completed

### After Deployment
- [ ] Service health verified
- [ ] Version tracking updated
- [ ] Performance metrics normal
- [ ] Documentation updated
- [ ] Team notified

## 🔗 Related Documentation
- [Semantic Version Manager](../scripts/deploy/semantic_version_manager.sh)
- [Automated Deployment Pipeline](AUTOMATED_DEPLOYMENT_PIPELINE.md)
- [Local Testing Strategy](LOCAL_TESTING_STRATEGY.md)
- [Backup & Rollback Strategy](BACKUP_ROLLBACK_STRATEGY.md)
- [Docker Optimization Guide](../docker/OPTIMIZATION_GUIDE.md)

## 📞 Emergency Contacts & Procedures

### Emergency Rollback
1. **Immediate**: Use automated rollback scripts
2. **Manual**: SSH to server and restore backup
3. **Critical**: Contact system administrator
4. **Documentation**: Log all emergency actions

### Escalation Path
1. **Level 1**: Automated recovery systems
2. **Level 2**: Manual intervention by developer
3. **Level 3**: System administrator involvement
4. **Level 4**: Business continuity procedures 