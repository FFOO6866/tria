# Backend Dockerfile for TRIA AI-BPO Platform
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.cargo/bin:$PATH"

# Copy dependency files first for better caching
COPY pyproject.toml .
COPY uv.lock* .

# Install dependencies using uv (creates virtual environment)
RUN uv sync --frozen

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY migrations/ ./migrations/

# Expose port 8001 for FastAPI
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD uv run python -c "import requests; requests.get('http://localhost:8001/health')" || exit 1

# Run the production API with uv
CMD ["uv", "run", "uvicorn", "src.enhanced_api:app", "--host", "0.0.0.0", "--port", "8001"]
