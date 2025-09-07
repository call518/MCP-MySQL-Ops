#!/bin/bash
set -euo pipefail

# Run MCP Inspector with local source using uv
cd "$(dirname "$0")/.."

echo "🔍 Starting MCP Inspector with MySQL Operations server..."
echo "📁 Working directory: $(pwd)"

# Load environment variables if .env exists
if [ -f ".env" ]; then
    echo "📄 Loading environment from .env file"
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set default log level for development
export MCP_LOG_LEVEL=${MCP_LOG_LEVEL:-INFO}

echo "🚀 Launching MCP Inspector..."
echo "   Log Level: $MCP_LOG_LEVEL"
echo "   MySQL Host: ${MYSQL_HOST:-localhost}:${MYSQL_PORT:-3306}"

npx -y @modelcontextprotocol/inspector \
  -- uv run python -m mcp_mysql_ops
