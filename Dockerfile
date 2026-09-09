FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package management (also needed for mcp-grafana via uvx)
RUN pip install --no-cache-dir uv

# Copy requirements first for layer caching
COPY backend/requirements.txt ./backend/requirements.txt
RUN uv pip install --system --no-cache -r backend/requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY .env.example ./.env.example

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/docs || exit 1

# Run with uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
