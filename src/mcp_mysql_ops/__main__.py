"""
Entry point for running the MCP MySQL Operations Server as a module.

This allows running the server with:
    python -m mcp_mysql_ops

Instead of:
    python -m mcp_mysql_ops.mcp_main
"""

from .mcp_main import main

if __name__ == "__main__":
    main()
