# Multi-stage Dockerfile for Tria AIBPO
# Cloud-agnostic, works on any container platform (AWS, GCP, Azure, DigitalOcean, etc.)

# Stage 1: Builder - Create virtual environment and install dependencies
FROM python:3.11-slim as builder

# Install system dependencies required for Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies in virtual environment
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Stage 2: Runtime - Minimal production image
FROM python:3.11-slim

# Install runtime system dependencies (PostgreSQL client, etc.)
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set virtual environment in PATH
ENV PATH="/opt/venv/bin:$PATH"

# Set Python environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app/src:$PYTHONPATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=app:app . /app

# Create directories for persistent data
RUN mkdir -p /app/data/chromadb_cache /app/logs && \
    chown -R app:app /app/data /app/logs

# Switch to non-root user
USER app

# Expose port (configurable via environment)
EXPOSE 8003

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Default command (can be overridden by Kubernetes/docker-compose)
CMD ["uvicorn", "src.enhanced_api:app", "--host", "0.0.0.0", "--port", "8003"]
