# Docker Image Optimization Guide

## Current State
- **Current Size**: 1.44GB
- **Target Size**: 200-500MB
- **Optimization Potential**: 66-86% reduction

## Size Breakdown Analysis

### Current Dependencies (976MB total)
| Package | Size | Category | Optimization |
|---------|------|----------|--------------|
| nautilus_trader | 269MB | Core | Consider lighter alternatives |
| pyarrow | 140MB | Data | Essential for parquet |
| pandas | 78MB | Data | Essential |
| notebook | 63MB | Dev | Remove from production |
| numpy | 47MB | Data | Essential |
| twisted | 36MB | Network | Check if needed |
| babel | 33MB | i18n | Check if needed |
| jupyterlab | 22MB | Dev | Remove from production |
| debugpy | 22MB | Dev | Remove from production |
| mypy | 18MB | Dev | Remove from production |

## Optimization Strategies

### 1. Production Dependencies Only (150MB savings)
```dockerfile
# Use requirements-production.txt instead of requirements.txt
COPY requirements-production.txt .
RUN pip install --no-cache-dir -r requirements-production.txt
```

### 2. Alpine Linux Base (100MB savings)
```dockerfile
# FROM python:3.11-slim  # 150MB base
FROM python:3.11-alpine  # 50MB base
```

### 3. Multi-stage Build (50MB savings)
```dockerfile
# Build stage for compilation
FROM python:3.11-alpine as builder
# ... build dependencies ...

# Production stage - minimal runtime
FROM python:3.11-alpine as production
COPY --from=builder /opt/venv /opt/venv
```

### 4. Minimal Dependencies (400MB savings)
```dockerfile
# Remove nautilus_trader and other heavy packages
# Use requirements-minimal.txt
```

## Optimization Levels

### Level 1: Production Dependencies
- **Target Size**: ~800MB (44% reduction)
- **Effort**: Low
- **Risk**: None
- **File**: `Dockerfile.optimized`

### Level 2: Alpine + Multi-stage
- **Target Size**: ~500MB (65% reduction)
- **Effort**: Medium
- **Risk**: Low
- **File**: `Dockerfile.optimized`

### Level 3: Minimal Dependencies
- **Target Size**: ~200MB (86% reduction)
- **Effort**: High
- **Risk**: Medium (may need code changes)
- **File**: `Dockerfile.minimal`

## Implementation Steps

1. **Test Level 1 (Safe)**:
   ```bash
   docker build -f docker/Dockerfile.optimized --target production -t paper-trading:optimized .
   ```

2. **Test Level 3 (Aggressive)**:
   ```bash
   docker build -f docker/Dockerfile.minimal -t paper-trading:minimal .
   ```

3. **Compare Results**:
   ```bash
   ./docker/build-comparison.sh
   ```

## Additional Optimizations

### Runtime Optimizations
- Use non-root user (security + size)
- Remove package caches
- Use `.dockerignore` (already implemented)

### Application Optimizations
- Lazy loading of heavy modules
- Optional dependencies
- Modular architecture

## Migration Strategy

1. **Phase 1**: Deploy Level 1 optimization (safe)
2. **Phase 2**: Test Level 2 in staging
3. **Phase 3**: Consider Level 3 for specific use cases

## Expected Results

| Level | Size | Reduction | Trade-offs |
|-------|------|-----------|------------|
| Current | 1.44GB | 0% | Full features |
| Level 1 | ~800MB | 44% | No dev tools |
| Level 2 | ~500MB | 65% | Alpine base |
| Level 3 | ~200MB | 86% | Minimal deps |

## Monitoring

After optimization, monitor:
- Container startup time
- Memory usage
- Application functionality
- Build time
