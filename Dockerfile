FROM python:3.12-slim

WORKDIR /app

# Install the package
COPY . .
RUN pip install --no-cache-dir ".[mcp]"

# MCP servers communicate over stdio
ENTRYPOINT ["python", "-m", "markcrawl.mcp_server"]
