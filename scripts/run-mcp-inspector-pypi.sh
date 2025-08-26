#!/bin/bash
set -euo pipefail

# Run MCP Inspector with published package from PyPI
cd "$(dirname "$0")/.."

echo "🔍 Starting MCP Inspector with published package..."
echo "📦 Package: mcp-mysql-ops"

# Check if package name has been customized
if grep -q "mcp-mysql-ops" pyproject.toml; then
    echo "✅ Package name 'mcp-mysql-ops' is properly configured."
else
    echo "⚠️  Warning: Package name 'mcp-mysql-ops' not found in pyproject.toml."
    echo "   Please verify the package configuration."
    echo ""
fi

echo "🚀 Launching MCP Inspector with uvx..."

npx -y @modelcontextprotocol/inspector \
  -- uvx mcp-mysql-ops
