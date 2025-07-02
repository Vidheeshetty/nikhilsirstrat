# Deployment Automation

## Overview

This platform uses a **quality-controlled deployment** approach:
1. **Development → Main**: Automated via scripts with quality gates
2. **Main → Docker Production**: **Manual version-only deployment** for quality control

## 🎯 Quality-Controlled Deployment Flow

### 1. Development to Main (Automated Quality Gates)
```bash
# Quality gates + commit + release in one go
./1dev_com.sh --msg "feat: new feature" && ./2sync_main.sh --yes --msg "Production release"
```

This will:
- ✅ Run lint, format, type-check, tests
- ✅ Commit to `development` branch
- ✅ Merge to `main` (fast-forward)
- ✅ Auto-bump version (e.g., `v1.2.3`)
- ✅ Create git tag and push

### 2. Docker Deployment (Manual Quality Control)

**🔒 Manual Trigger Only** - You specify which version gets deployed:

#### Option A: GitHub Actions (Recommended)
1. Go to **GitHub Actions** tab
2. Select **"Docker Deployment"** workflow
3. Click **"Run workflow"**
4. Enter version number: `1.2.3` (without 'v' prefix)
5. Select environment: `production` or `staging`

#### Option B: Command Line
```bash
# Deploy specific version
./scripts/deploy/deploy_version.sh 1.2.3

# Dry run (see what would be deployed)
./scripts/deploy/deploy_version.sh 1.2.3 --dry-run
```

## 🛡️ Quality Assurance Features

### Version Validation
- ✅ **Tag must exist** in git repository
- ✅ **Semantic versioning** enforced (1.2.3 format)
- ✅ **Quality gates passed** (from dev workflow)
- ✅ **Manual approval** required for deployment

### Deployment Safety
- 🔍 **Pre-deployment validation**
- 🔄 **Graceful service restart**
- 🏥 **Health checks with retries**
- 🧹 **Automatic cleanup** of old images
- 📊 **Deployment summary** and status

## 📋 Complete Workflow Example

```bash
# 1. Development with quality gates
./1dev_com.sh --msg "feat: add new trading strategy"

# 2. Release to main (creates v1.2.3 tag)
./2sync_main.sh --yes --msg "New strategy ready for production"

# 3. Manual quality check - test the version
git checkout v1.2.3
# ... manual testing, validation ...

# 4. Deploy only when satisfied with quality
./scripts/deploy/deploy_version.sh 1.2.3
```

## 🚀 Deployment Commands

### Development Workflow
```bash
# Individual steps
./1dev_com.sh --msg "commit message"    # Dev → development branch
./2sync_main.sh --yes --msg "release"   # development → main + tag

# Combined (recommended)
./1dev_com.sh --msg "feat: deployment automation" && ./2sync_main.sh --yes --msg "Quality deployment ready"
```

### Production Deployment (Version Control)
```bash
# Check what would be deployed
./scripts/deploy/deploy_version.sh 1.2.3 --dry-run

# Deploy specific version
./scripts/deploy/deploy_version.sh 1.2.3

# Deploy to different server
./scripts/deploy/deploy_version.sh 1.2.3 --host myserver.com --user deploy

# Get current deployed version
curl http://139.84.166.225:8080/api/status
```

## 📁 File Structure

```
.github/workflows/
  docker-deploy.yml           # Manual-trigger GitHub Actions

docker/
  docker-compose.yml          # Development (Option 3: bind mounts)
  docker-compose.prod.yml     # Production (versioned images)
  Dockerfile                  # Multi-stage build

scripts/
  deploy/
    deploy_version.sh         # Version-controlled deployment
    deploy_tagged_version.sh  # Legacy (tag-based)
  1dev_com.sh                 # Development workflow
  2sync_main.sh               # Release workflow
```

## ⚙️ Setup Required

### GitHub Secrets (for GitHub Actions deployment)
```
DOCKER_USERNAME=your_dockerhub_username
DOCKER_PASSWORD=your_dockerhub_token
DEPLOY_HOST=139.84.166.225
DEPLOY_USER=synaptic
DEPLOY_SSH_KEY=your_private_ssh_key
```

### Server Requirements
- Docker & Docker Compose installed
- SSH access configured
- Git repository cloned to `~/NTbasedPlatform`

## 🔍 Monitoring & Validation

- **Dashboard**: http://139.84.166.225:8080
- **Health Check**: `curl http://139.84.166.225:8080/api/status`
- **Version Check**: Check git tag in dashboard response
- **Logs**: `docker logs paper-trading-server`

## 🎯 Benefits of Version-Only Deployment

1. **Quality Control**: Only manually approved versions reach production
2. **Traceability**: Clear version numbers for every deployment
3. **Rollback**: Easy to deploy previous versions
4. **Testing**: Can validate specific versions before deployment
5. **Safety**: No accidental auto-deployments from commits 