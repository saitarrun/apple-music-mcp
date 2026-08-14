# Dockerfile for Smithery Containerized MCP Execution
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy package definition and source code
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install the package
RUN pip install --no-cache-dir .

# Expose stdio runner
ENTRYPOINT ["apple-music-mcp", "serve"]
