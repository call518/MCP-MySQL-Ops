# MCP MySQL Operations Server - AI Coding Agent Instructions

## Architecture Overview

This is a **Model Context Protocol (MCP) server** built with **FastMCP** that provides MySQL database monitoring and operations through natural language queries. The server acts as a safe, read-only bridge between AI assistants and MySQL databases.

### Core Components
- **`mcp_main.py`**: Main MCP server with 11+ `@mcp.tool()` decorated functions
- **`functions.py`**: Database connection layer using `aiomysql` with multi-database support
- **`version_compat.py`**: MySQL 5.7+ and 8.0+ version detection and adaptive feature handling
- **`prompt_template.md`**: Comprehensive prompt definitions loaded via `@mcp.prompt()` decorators
- **Docker stack**: MySQL + MCP server + MCPO proxy + Open WebUI integration

### Key Patterns

**Multi-Database Architecture**: All tools accept optional `database_name` parameter to target specific databases while maintaining a default connection database from `MYSQL_DB` env var.

**Performance Schema Integration**: Core functionality leverages MySQL's Performance Schema and Information Schema. Tools automatically detect available features and adapt accordingly.

**Version-Aware Tools**: Use `version_compat.py` for MySQL 5.7+/8.0+ compatibility. Tools auto-adapt features based on detected version. **MySQL 8.0+ recommended** for enhanced capabilities.

**Tool Structure**: Each MCP tool follows this pattern:
```python
@mcp.tool()
async def get_something(limit: int = 20, database_name: str = None) -> str:
    """Detailed docstring with [Tool Purpose], [Exact Functionality], [Required Use Cases], [Strictly Prohibited Use Cases]"""
    try:
        # Validate inputs (limit constraints: max 1-100)
        # Execute queries via functions.py
        # Return formatted table data
    except Exception as e:
        logger.error(f"Failed to...: {e}")
        return f"Error: {str(e)}"
```

**Version Compatibility Pattern**: Critical for MySQL 5.7 support - many tools use version-aware query builders:
```python
# In functions.py
from .version_compat import get_mysql_version

async def get_database_size_data(database: str = None):
    version = await get_mysql_version()
    # Auto-adapts queries for MySQL 5.7 vs 8.0+ differences
    query = build_version_compatible_query(version)
    return await execute_query(query, database=database)
```

## Development Workflows

### Local Development
```bash
# Primary development command - loads .env, starts MCP Inspector
./scripts/run-mcp-inspector-local.sh

# Direct execution for debugging with custom log levels
python -m src.mcp_mysql_ops.mcp_main --log-level DEBUG --type streamable-http
```

### Docker Development
```bash
# Full stack with MySQL + test data
docker-compose up -d

# Test data generation (creates 4 databases with realistic test data)
./scripts/create-test-data.sh
```

### Environment Configuration
- Copy `.env.example` to `.env` and modify connection parameters
- **Critical**: `MYSQL_DB` serves dual purpose - default connection target AND Docker database creation name
- Use `host.docker.internal` for `MYSQL_HOST` when connecting from containers to host MySQL

## Code Conventions

### Database Connection Pattern
```python
# Multi-database support - database parameter overrides MYSQL_CONFIG default
async def get_db_connection(database: str = None) -> aiomysql.Connection:
    config = MYSQL_CONFIG.copy()
    if database:
        config["db"] = database  # Override default
    return await aiomysql.connect(**config)
```

### Error Handling
- All MCP tools must return `str` (never raise exceptions to MCP layer)
- Log errors with `logger.error()` then return user-friendly error messages
- Mask sensitive information in connection info with `sanitize_connection_info()`

### Query Formatting
- Use `format_table_data(results, title)` for consistent table output
- Apply `format_bytes()` and `format_duration()` for human-readable values
- Enforce limit constraints: `limit = max(1, min(limit, 100))`

### Tool Compatibility Matrix
When adding new tools, **must** update the compatibility matrix in `README.md`:
- Classify as Core MySQL Monitoring Tools or Version-Enhanced Tools
- Document MySQL version support (5.7+/8.0+)
- List Information Schema/Performance Schema tables used
- Update tool count statistics

### Recent Major Changes
- **MySQL Focus**: Completely migrated from MySQL to MySQL operations
- **Comprehensive MySQL 5.7+/8.0+ Support**: All tools work on MySQL 5.7+ with enhanced 8.0+ features
- **Performance Schema Integration**: Leveraging MySQL's built-in monitoring capabilities
- **Enhanced Storage Analysis**: New tools for table sizes, index usage, and database capacity planning

## Project-Specific Integrations

### Prompt Template System
The server loads prompts from `prompt_template.md` using a custom parsing system:
- `@mcp.prompt("prompt_template_full")` - complete template
- `@mcp.prompt("prompt_template_headings")` - section list only
- `get_prompt_template(section="specific_section")` - targeted content

### Docker Multi-Service Architecture
- **mysql**: MySQL 8.0 (version from `MYSQL_VERSION` env var, default 8.0)
- **mysql-init-data**: One-shot container that creates comprehensive test data
- **mcp-server**: Main MCP server container
- **mcpo-proxy**: HTTP proxy for web-based MCP clients
- **open-webui**: Web interface for testing

### Critical Dependencies
```python
# Required for all database operations
import aiomysql  # Not PyMySQL - uses aiomysql exclusively for async operations

# MCP framework
from fastmcp import FastMCP

# Version checks are recommended for enhanced features
version = await get_mysql_version()
```

### MySQL Version Compatibility Patterns
The major work focuses on MySQL version compatibility. Key patterns:

**Information Schema vs Performance Schema**: MySQL 8.0+ has enhanced Performance Schema tables while 5.7 uses basic ones:
```python
# In version_compat.py
if version.supports_enhanced_performance_schema:  # MySQL 8.0+
    query = "SELECT * FROM performance_schema.events_statements_summary_by_digest"
else:  # MySQL 5.7
    query = "SELECT * FROM information_schema.tables"
```

**Feature Detection**: MySQL 8.0+ has additional features like JSON functions, CTEs, window functions:
```python
if version.supports_json_functions:  # MySQL 8.0+
    json_columns = ["JSON_EXTRACT(data, '$.field') as extracted_field"]
else:  # MySQL 5.7
    json_columns = ["NULL as extracted_field"]
```

## Testing Strategy

### Test Data Generation
- Run `./scripts/create-test-data.sh` to create 4 realistic databases:
  - `test_ecommerce`: E-commerce with products, orders, customers
  - `test_analytics`: Web analytics and sales data
  - `test_inventory`: Warehouse management
  - `test_hr`: Employee and payroll data

### Natural Language Testing
Test tools with realistic prompts - never use function names directly:
- ✅ "Show me the current server status"
- ❌ "Run get_server_status"

### Configuration Files
- `mcp-config.json.stdio`: Standard CLI integration
- `mcp-config.json.http`: HTTP mode for web clients
- Both must have matching port configurations with `docker-compose.yml`

## Common Pitfalls

1. **Database Parameter Confusion**: `MYSQL_DB` is the default connection database, not a constraint on which databases can be accessed
2. **Performance Schema Assumptions**: Check Performance Schema availability before using enhanced monitoring tools
3. **Port Misalignment**: `FASTMCP_PORT`, Docker external port, and MCP config files must all match
4. **Environment Loading**: Use `scripts/run-mcp-inspector-local.sh` which properly loads `.env` - direct Python execution won't load environment
5. **Query Limits**: All tools enforce 1-100 limits for performance; don't assume unlimited results
6. **aiomysql Parameter Binding**: Use `%s` format, not `$1, $2, ...` - all SQL queries must use aiomysql-compatible parameter binding
7. **MySQL Version Support**: Currently supports 5.7+/8.0+; latest versions support pending testing
8. **Version-Specific Features**: Always use `version_compat.py` patterns for new tools that query system tables
