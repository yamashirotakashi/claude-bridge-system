# Claude Bridge System - Production Dockerfile
# Multi-stage build for optimized production deployment

FROM python:3.11-slim as builder

# Build-time arguments
ARG BUILD_VERSION=latest
ARG BUILD_TIMESTAMP

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    pkg-config \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
COPY requirements-dev.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Production image
FROM python:3.11-slim as runtime

# Runtime arguments
ARG BUILD_VERSION=latest
ARG BUILD_TIMESTAMP
ARG ENVIRONMENT=production

# Labels for image metadata
LABEL maintainer="Claude Bridge System"
LABEL version="$BUILD_VERSION"
LABEL build-timestamp="$BUILD_TIMESTAMP"
LABEL environment="$ENVIRONMENT"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r claude && useradd -r -g claude claude

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY claude_bridge/ ./claude_bridge/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY setup.py .
COPY README.md .
COPY CHANGELOG.md .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/certs /app/backups \
    && chown -R claude:claude /app

# Install the application
RUN pip install -e .

# Copy configuration files
COPY docker/production.yaml ./config/production.yaml
COPY docker/logging.yaml ./config/logging.yaml

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV LOG_LEVEL=INFO
ENV BRIDGE_CONFIG_PATH=/app/config/production.yaml

# Health check
COPY docker/healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Switch to non-root user
USER claude

# Expose ports
EXPOSE 8080 8443 9090

# Volume mounts for persistent data
VOLUME ["/app/data", "/app/logs", "/app/certs"]

# Default command
CMD ["python", "-m", "claude_bridge.cli.main", "server", "--config", "/app/config/production.yaml"]