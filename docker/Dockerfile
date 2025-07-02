# Paper Trading Platform Docker Image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_DEFAULT_TIMEOUT=600

# Set working directory
WORKDIR /app

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

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p runlogs/papertrading
RUN mkdir -p config
RUN mkdir -p data

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash trader
RUN chown -R trader:trader /app

# Switch to non-root user
USER trader

# Expose ports
EXPOSE 8000 8888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/status || exit 1

# Default command
CMD ["python", "-m", "scripts.paper_trading.paper_trading_server", "--host", "0.0.0.0", "--port", "8000"] 