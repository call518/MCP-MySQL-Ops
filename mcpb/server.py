"""MCPB entry point for the MCP MySQL Operations server."""

from mcp_mysql_ops.mcp_main import main


if __name__ == "__main__":
    main(["--type", "stdio"])
