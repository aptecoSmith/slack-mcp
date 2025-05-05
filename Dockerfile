# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY slack_mcp ./slack_mcp
COPY PLANNING.md README.md TASK.md ./

# Expose stdio entrypoint (default)
CMD ["python", "-m", "slack_mcp.main"]
