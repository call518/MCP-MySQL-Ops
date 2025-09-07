#!/bin/bash
set -eo pipefail

# Get the directory where this script is located and navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔍 Starting MCP Inspector with MySQL Operations server..."
echo "📁 Working directory: $(pwd)"

# Load environment variables if .env exists
if [ -f ".env" ]; then
    echo "📄 Loading environment from .env file"
    set -o allexport
    source .env
    set +o allexport
fi

# Set default values for authentication variables if not defined
export REMOTE_AUTH_ENABLE="${REMOTE_AUTH_ENABLE:-false}"
export REMOTE_SECRET_KEY="${REMOTE_SECRET_KEY:-}"

# Set default log level for development
export MCP_LOG_LEVEL=${MCP_LOG_LEVEL:-INFO}

echo "🚀 Launching MCP Inspector..."
echo "   Log Level: $MCP_LOG_LEVEL"
echo "   MySQL Host: ${MYSQL_HOST:-localhost}:${MYSQL_PORT:-3306}"
echo "   Auth Enabled: $REMOTE_AUTH_ENABLE"

npx -y @modelcontextprotocol/inspector \
    -e PYTHONPATH='./src' \
    -- uv run python -m mcp_mysql_ops
