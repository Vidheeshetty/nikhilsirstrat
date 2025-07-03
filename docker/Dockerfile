# Paper Trading Platform Docker Image - Optimized Multi-stage
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_DEFAULT_TIMEOUT=600

# Set working directory
WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
COPY requirements-paper-trading.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-paper-trading.txt

# Production stage
FROM base as production

# Copy only necessary application files
COPY src/ src/
COPY utils/ utils/
COPY scripts/ scripts/
COPY config/ config/
COPY tests/ tests/
COPY web_dashboard/ web_dashboard/
COPY VERSION .
COPY mypy.ini .
COPY requirements.txt .
COPY requirements-paper-trading.txt .

# Create necessary directories
RUN mkdir -p runlogs/papertrading
RUN mkdir -p logs
RUN mkdir -p data

# Expose ports
EXPOSE 8000 8888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/status || exit 1

# Default command
CMD ["python", "-m", "scripts.paper_trading.paper_trading_server", "--host", "0.0.0.0", "--port", "8000"]

# Development stage - extends base with dev tools
FROM base as dev

# Install development tools
RUN pip install --no-cache-dir \
    pytest-xdist \
    debugpy \
    ipython \
    jupyter

# Copy all files for development
COPY . .

# Create necessary directories
RUN mkdir -p runlogs/papertrading
RUN mkdir -p logs
RUN mkdir -p data

# Expose additional dev ports
EXPOSE 8000 8888 2345

# Default to bash for development
CMD ["bash"] 