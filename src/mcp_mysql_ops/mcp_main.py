"""
MCP MySQL Operations Server

A professional MCP server for MySQL database server operations, monitoring, and management.

Key Features:
1. Query performance monitoring via Performance Schema
2. Database, table, and user listing  
3. MySQL configuration and status information
4. Connection information and active session monitoring
5. Index usage statistics and performance metrics
6. InnoDB engine monitoring
"""

import argparse
import logging
import os
import sys
from typing import Any, Optional, List
from fastmcp import FastMCP
from fastmcp.server.auth import StaticTokenVerifier
from smithery.decorators import smithery
from .functions import (
    execute_query,
    execute_single_query,
    format_table_data,
    format_bytes,
    format_duration,
    get_server_version,
    check_performance_schema_enabled,
    check_slow_query_log_enabled,
    get_slow_query_data,
    sanitize_connection_info,
    read_prompt_template,
    parse_prompt_sections,
    get_prompt_template,
    get_current_database_name,
    MYSQL_CONFIG,
    refresh_configs,
)
from .version_compat import (
    get_mysql_version,
    get_slow_queries_query,
    get_table_io_stats_query,
    get_lock_waits_query,
    get_innodb_status_query,
    get_replication_status_query
)

# =============================================================================
# Logging configuration
# =============================================================================
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# =============================================================================
# Authentication Setup
# =============================================================================

# Check environment variables for authentication early
_auth_enable = os.environ.get("REMOTE_AUTH_ENABLE", "false").lower() == "true"
_secret_key = os.environ.get("REMOTE_SECRET_KEY", "")

# Initialize the main MCP instance with authentication if configured
if _auth_enable and _secret_key:
    logger.info("Initializing MCP instance with Bearer token authentication (from environment)")
    
    # Create token configuration
    tokens = {
        _secret_key: {
            "client_id": "mysql-ops-client",
            "user": "admin",
            "scopes": ["read", "write"],
            "description": "MySQL Operations access token"
        }
    }
    
    auth = StaticTokenVerifier(tokens=tokens)
    mcp = FastMCP("mcp-mysql-ops", auth=auth)
    logger.info("MCP instance initialized with authentication")
else:
    logger.info("Initializing MCP instance without authentication")
    mcp = FastMCP("mcp-mysql-ops")

# =============================================================================
# Server initialization
# =============================================================================

# Prompt template path
PROMPT_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "prompt_template.md")

# =============================================================================
# Prompt Templates
# =============================================================================

@mcp.prompt()
def prompt_template_full() -> str:
    """Complete MySQL Operations guidance template with all tool descriptions and usage examples."""
    try:
        return read_prompt_template()
    except Exception as e:
        logger.error(f"Failed to load full prompt template: {e}")
        return f"Error loading prompt template: {e}"

@mcp.prompt()
def prompt_template_headings() -> str:
    """List of available prompt template sections and tools."""
    try:
        content = read_prompt_template()
        sections = parse_prompt_sections(content)
        headings = [f"## {heading}" for heading in sections.keys()]
        return "\n".join(headings)
    except Exception as e:
        logger.error(f"Failed to load prompt headings: {e}")
        return f"Error loading prompt headings: {e}"


@mcp.prompt()
def prompt_template_section(section: str = "") -> str:
    """Get a specific section from the prompt template.
    
    Args:
        section: The name of the section to retrieve (if empty, shows available sections)
        
    Returns:
        The content of the specified section or list of available sections
    """
    try:
        if not section or section.strip() == "":
            # If no section specified, show available sections
            content = read_prompt_template()
            sections = parse_prompt_sections(content)
            available_sections = list(sections.keys())
            return f"Available prompt template sections:\n\n" + "\n".join([f"- {s}" for s in available_sections])
        
        return get_prompt_template(section)
    except Exception as e:
        logger.error(f"Failed to load prompt section '{section}': {e}")
        return f"Error loading prompt section '{section}': {e}"

# =============================================================================
# MCP Tools (MySQL Operations Tools)

@mcp.tool()
async def get_server_info(database_name: Optional[str] = None) -> str:
    """
    [Tool Purpose]: Get MySQL server version and basic information
    
    [Exact Functionality]:
    - Show MySQL server version, edition, and compilation info
    - Display server uptime and basic configuration
    - Show available storage engines and default engine
    - Provide server connection details (sanitized)
    
    [Required Use Cases]:
    - When user requests "server info", "MySQL version", "server status"
    - When diagnosing compatibility issues
    - When checking server capabilities
    
    Args:
        database_name: Database name to connect to (uses default if omitted)
    
    Returns:
        Formatted string with MySQL server information
    """
    try:
        # Get server version and info
        version_result = await execute_single_query("SELECT VERSION() as version", database=database_name)
        uptime_result = await execute_single_query("SHOW STATUS LIKE 'Uptime'", database=database_name)
        engines_result = await execute_query("SHOW ENGINES", database=database_name)
        
        # Get server variables
        vars_query = """
        SELECT variable_name, variable_value 
        FROM performance_schema.global_variables 
        WHERE variable_name IN ('port', 'socket', 'datadir', 'default_storage_engine', 'max_connections')
        """
        vars_result = await execute_query(vars_query, database=database_name)
        
        # Format results
        result = ["=== MySQL Server Information ===\n"]
        
        if version_result:
            result.append(f"Version: {version_result['version']}")
            
        if uptime_result:
            uptime_sec = int(uptime_result['Value'])
            result.append(f"Uptime: {format_duration(uptime_sec)}")
            
        result.append("\n=== Configuration ===")
        for var in vars_result:
            result.append(f"{var['variable_name']}: {var['variable_value']}")
            
        result.append("\n=== Available Storage Engines ===")
        for engine in engines_result:
            support = engine['Support']
            if support in ['YES', 'DEFAULT']:
                marker = " (default)" if support == 'DEFAULT' else ""
                result.append(f"- {engine['Engine']}: {engine['Comment']}{marker}")
                
        # Connection info (sanitized)
        conn_info = sanitize_connection_info()
        result.append(f"\n=== Connection ===")
        result.append(f"Host: {conn_info['host']}:{conn_info['port']}")
        result.append(f"Database: {conn_info['db']}")
        result.append(f"User: {conn_info['user']}")
        
        return "\n".join(result)
        
    except Exception as e:
        logger.error(f"Failed to get server info: {e}")
        return f"Error retrieving server info: {e}"


@mcp.tool()
async def get_active_connections(database_name: Optional[str] = None, user_filter: Optional[str] = None, db_filter: Optional[str] = None) -> str:
    """
    [Tool Purpose]: Monitor active MySQL connections and processes
    
    [Exact Functionality]:
    - List all active connections with process ID, user, host, database
    - Show current command being executed by each connection
    - Display connection time and state information
    - Filter by user or database name
    
    [Required Use Cases]:
    - When user requests "active connections", "current sessions", "process list"
    - When diagnosing connection issues or monitoring user activity
    - When checking for long-running queries
    
    Args:
        database_name: Database name to connect to (uses default if omitted)
        user_filter: Filter connections by username
        db_filter: Filter connections by database name
    
    Returns:
        Formatted string with active connection information
    """
    try:
        query = """
        SELECT 
            id as process_id,
            user,
            host,
            db as database_name,
            command,
            time as duration_sec,
            state,
            SUBSTRING(info, 1, 100) as query_snippet
        FROM information_schema.processlist
        WHERE command != 'Sleep' OR info IS NOT NULL
        ORDER BY time DESC
        """
        
        result = await execute_query(query, database=database_name)
        
        # Apply filters
        if user_filter:
            result = [r for r in result if r['user'] and user_filter.lower() in r['user'].lower()]
        if db_filter:
            result = [r for r in result if r['database_name'] and db_filter.lower() in r['database_name'].lower()]
        
        if not result:
            filter_info = ""
            if user_filter or db_filter:
                filters = []
                if user_filter:
                    filters.append(f"user: {user_filter}")
                if db_filter:
                    filters.append(f"database: {db_filter}")
                filter_info = f" (filtered by {', '.join(filters)})"
            return f"No active connections found{filter_info}"
        
        # Format duration for better readability
        for row in result:
            row['duration'] = format_duration(row['duration_sec'])
            
        return format_table_data(result, "Active MySQL Connections")
        
    except Exception as e:
        logger.error(f"Failed to get active connections: {e}")
        return f"Error retrieving active connections: {e}"


@mcp.tool()
async def get_database_list(database_name: Optional[str] = None) -> str:
    """
    [Tool Purpose]: List all databases in MySQL server
    
    [Exact Functionality]:
    - Show all databases with names and character sets
    - Display database size information if available
    - Show collation and default character set
    
    [Required Use Cases]:
    - When user requests "database list", "show databases", "available databases"
    - When exploring server structure
    
    Args:
        database_name: Database name to connect to (uses default if omitted)
    
    Returns:
        Formatted string with database list
    """
    try:
        query = """
        SELECT 
            schema_name as database_name,
            default_character_set_name as charset,
            default_collation_name as collation,
            COALESCE(
                (SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2)
                 FROM information_schema.tables 
                 WHERE table_schema = s.schema_name), 0
            ) as size_mb
        FROM information_schema.schemata s
        WHERE schema_name NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
        ORDER BY schema_name
        """
        
        result = await execute_query(query, database=database_name)
        
        if not result:
            return "No user databases found"
            
        # Format size for better readability
        for row in result:
            size_mb = row.get('size_mb', 0)
            if size_mb:
                row['size'] = format_bytes(size_mb * 1024 * 1024)
            else:
                row['size'] = 'N/A'
                
        return format_table_data(result, "MySQL Databases")
        
    except Exception as e:
        logger.error(f"Failed to get database list: {e}")
        return f"Error retrieving database list: {e}"


@mcp.tool()
async def get_table_list(database_name: Optional[str] = None, table_type: Optional[str] = None) -> str:
    """
    [Tool Purpose]: List all tables in specified database or all databases
    
    [Exact Functionality]:
    - If database_name provided: Show tables in that specific database
    - If database_name empty: Show tables from all user databases with database names
    - Display table type (BASE TABLE, VIEW), engine, rows count, and size information
    - Show creation and update timestamps
    - Filter by table type if specified
    
    [Required Use Cases]:
    - When user requests "table list", "show tables", "database tables"
    - When exploring database structure
    
    Args:
        database_name: Database name to analyze (if empty, shows tables from all databases)
        table_type: Filter by table type ("BASE TABLE", "VIEW")
    
    Returns:
        Formatted string with table information
    """
    try:
        # If no database specified, show tables from all user databases
        if not database_name:
            # Try to use current database first
            current_db = await get_current_database_name()
            if current_db and current_db != "unknown":
                database_name = current_db
            else:
                # Show tables from all user databases
                return await get_all_databases_tables(table_type)
        
        query = """
        SELECT 
            table_name,
            table_type,
            engine,
            table_rows,
            ROUND((data_length + index_length) / 1024 / 1024, 2) as size_mb,
            ROUND(data_length / 1024 / 1024, 2) as data_mb,
            ROUND(index_length / 1024 / 1024, 2) as index_mb,
            create_time,
            update_time,
            table_comment
        FROM information_schema.tables
        WHERE table_schema = %s
        """
        
        params = [database_name]
        
        if table_type:
            query += " AND table_type = %s"
            params.append(table_type.upper())
            
        query += " ORDER BY table_name"
        
        result = await execute_query(query, params, database=database_name)
        
        if not result:
            type_filter = f" of type '{table_type}'" if table_type else ""
            return f"No tables found in database '{database_name}'{type_filter}"
        
        # Format sizes for better readability
        for row in result:
            row['size'] = format_bytes((row.get('size_mb', 0) or 0) * 1024 * 1024)
            row['data_size'] = format_bytes((row.get('data_mb', 0) or 0) * 1024 * 1024)
            row['index_size'] = format_bytes((row.get('index_mb', 0) or 0) * 1024 * 1024)
            
        return format_table_data(result, f"Tables in '{database_name}' Database")
        
    except Exception as e:
        logger.error(f"Failed to get table list: {e}")
        return f"Error retrieving table list: {e}"


@mcp.tool()
async def get_table_schema_info(table_name: str, database_name: Optional[str] = None) -> str:
    """
    [Tool Purpose]: Get detailed schema information for a specific table or entire database
    
    [Exact Functionality]:
    - If table_name provided: Show all columns, indexes, foreign keys for that table
    - If table_name empty: Show overview of all tables in the database
    - Display table statistics, constraints, and engine information
    - Include column comments and default values
    
    [Required Use Cases]:
    - When user requests "table schema", "table structure", "describe table"
    - When analyzing table design and constraints
    - When requesting database-wide schema analysis with empty table_name
    
    Args:
        table_name: Name of the table to analyze (empty string for database overview)
        database_name: Database containing the table (uses current database if omitted)
    
    Returns:
        Formatted string with detailed table schema information or database overview
    """
    try:
        # Use current database if not specified
        if not database_name:
            current_db = await get_current_database_name()
            if current_db and current_db != "unknown":
                database_name = current_db
            else:
                # Provide helpful guidance with available databases
                db_list = await get_database_list()
                return f"No database specified and no current database selected.\n\nTo get table schema information, please specify a database name.\n\n{db_list}"
        
        # If table_name is empty, return database overview
        if not table_name or table_name.strip() == "":
            return await get_database_overview(database_name)
        
        # Validate that the table exists
        table_check_query = """
        SELECT COUNT(*) as count
        FROM information_schema.tables
        WHERE table_schema = %s AND table_name = %s
        """
        
        table_exists = await execute_query(table_check_query, [database_name, table_name], database=database_name)
        
        if not table_exists or table_exists[0]['count'] == 0:
            # Provide available tables in the database
            tables_query = """
            SELECT TABLE_NAME as table_name, TABLE_TYPE as table_type, ENGINE, TABLE_ROWS as table_rows
            FROM information_schema.tables
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
            ORDER BY TABLE_NAME
            """
            available_tables = await execute_query(tables_query, [database_name], database=database_name)
            
            if available_tables:
                tables_list = format_table_data(available_tables, f"Available tables in '{database_name}' database")
                return f"Table '{table_name}' not found in database '{database_name}'.\n\n{tables_list}"
            else:
                return f"Table '{table_name}' not found in database '{database_name}' and no tables exist in this database."
        
        # Continue with existing table-specific logic...
        
        # Get column information
        columns_query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            extra,
            column_key,
            column_comment,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        """
        
        # Get indexes
        indexes_query = """
        SELECT 
            index_name,
            column_name,
            seq_in_index,
            non_unique,
            index_type,
            index_comment
        FROM information_schema.statistics
        WHERE table_schema = %s AND table_name = %s
        ORDER BY index_name, seq_in_index
        """
        
        # Get foreign keys
        fk_query = """
        SELECT 
            kcu.constraint_name,
            kcu.column_name,
            kcu.referenced_table_schema,
            kcu.referenced_table_name,
            kcu.referenced_column_name,
            rc.update_rule,
            rc.delete_rule
        FROM information_schema.key_column_usage kcu
        JOIN information_schema.referential_constraints rc 
            ON kcu.constraint_name = rc.constraint_name 
            AND kcu.constraint_schema = rc.constraint_schema
        WHERE kcu.table_schema = %s AND kcu.table_name = %s
        ORDER BY kcu.constraint_name, kcu.ordinal_position
        """
        
        params = [database_name, table_name]
        
        columns = await execute_query(columns_query, params, database=database_name)
        indexes = await execute_query(indexes_query, params, database=database_name)
        foreign_keys = await execute_query(fk_query, params, database=database_name)
        
        if not columns:
            # Provide helpful guidance with available tables
            table_list_result = await get_table_list(database_name)
            return f"Table '{table_name}' not found in database '{database_name}'.\n\nAvailable tables:\n{table_list_result}"
        
        result = [f"=== Table Schema: {database_name}.{table_name} ===\n"]
        
        # Column information
        result.append("=== Columns ===")
        for col in columns:
            col_def = f"{col['COLUMN_NAME']} {col['DATA_TYPE']}"
            
            # Add length/precision
            if col['CHARACTER_MAXIMUM_LENGTH']:
                col_def += f"({col['CHARACTER_MAXIMUM_LENGTH']})"
            elif col['NUMERIC_PRECISION']:
                if col['NUMERIC_SCALE']:
                    col_def += f"({col['NUMERIC_PRECISION']},{col['NUMERIC_SCALE']})"
                else:
                    col_def += f"({col['NUMERIC_PRECISION']})"
            
            # Add constraints
            if col['IS_NULLABLE'] == 'NO':
                col_def += " NOT NULL"
            if col['COLUMN_DEFAULT'] is not None:
                col_def += f" DEFAULT {col['COLUMN_DEFAULT']}"
            if col['EXTRA']:
                col_def += f" {col['EXTRA']}"
            if col['COLUMN_KEY']:
                col_def += f" ({col['COLUMN_KEY']})"
            if col['COLUMN_COMMENT']:
                col_def += f" COMMENT '{col['COLUMN_COMMENT']}'"
                
            result.append(f"  {col_def}")
        
        # Index information
        if indexes:
            result.append("\n=== Indexes ===")
            current_index = None
            index_columns = []
            
            for idx in indexes:
                if current_index != idx['INDEX_NAME']:
                    if current_index:
                        unique = "" if index_columns[0]['NON_UNIQUE'] else "UNIQUE "
                        cols = ", ".join([ic['COLUMN_NAME'] for ic in index_columns])
                        index_type = index_columns[0].get('INDEX_TYPE', '')
                        result.append(f"  {unique}{current_index} ({cols}) {index_type}")
                    
                    current_index = idx['INDEX_NAME']
                    index_columns = [idx]
                else:
                    index_columns.append(idx)
            
            # Add last index
            if current_index and index_columns:
                unique = "" if index_columns[0]['NON_UNIQUE'] else "UNIQUE "
                cols = ", ".join([ic['COLUMN_NAME'] for ic in index_columns])
                index_type = index_columns[0].get('INDEX_TYPE', '')
                result.append(f"  {unique}{current_index} ({cols}) {index_type}")
        
        # Foreign key information
        if foreign_keys:
            result.append("\n=== Foreign Keys ===")
            for fk in foreign_keys:
                fk_def = f"{fk['CONSTRAINT_NAME']}: {fk['COLUMN_NAME']} -> {fk['REFERENCED_TABLE_SCHEMA']}.{fk['REFERENCED_TABLE_NAME']}.{fk['REFERENCED_COLUMN_NAME']}"
                if fk['UPDATE_RULE'] != 'RESTRICT' or fk['DELETE_RULE'] != 'RESTRICT':
                    fk_def += f" (ON UPDATE {fk['UPDATE_RULE']}, ON DELETE {fk['DELETE_RULE']})"
                result.append(f"  {fk_def}")
        
        return "\n".join(result)
        
    except Exception as e:
        logger.error(f"Failed to get table schema info: {e}")
        return f"Error retrieving table schema info: {e}"


async def get_all_databases_tables(table_type: Optional[str] = None) -> str:
    """Helper function to get table list from all user databases"""
    try:
        query = """
        SELECT 
            table_schema as database_name,
            table_name,
            table_type,
            engine,
            table_rows,
            ROUND((data_length + index_length) / 1024 / 1024, 2) as size_mb,
            table_comment
        FROM information_schema.tables
        WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
        """
        
        params = []
        if table_type:
            query += " AND table_type = %s"
            params.append(table_type.upper())
            
        query += " ORDER BY table_schema, table_name LIMIT 50"
        
        result = await execute_query(query, params)
        if not result:
            type_filter = f" of type '{table_type}'" if table_type else ""
            return f"No user-created tables found{type_filter}.\n\nAvailable databases:\n" + await get_database_list()
        
        # Format sizes for better readability    
        for row in result:
            row['size'] = format_bytes((row.get('size_mb', 0) or 0) * 1024 * 1024)
            
        title = f"Tables from All User Databases (showing up to 50)"
        if table_type:
            title += f" - Type: {table_type}"
            
        return format_table_data(result, title)
    except Exception as e:
        logger.error(f"Failed to get all databases tables: {e}")
        return f"Error retrieving tables from all databases: {e}"


async def get_all_databases_table_sizes(limit: int = 20) -> str:
    """Helper function to get table sizes from all user databases"""
    try:
        query = """
        SELECT 
            table_schema as database_name,
            table_name,
            table_rows,
            ROUND(data_length / 1024 / 1024, 2) as data_mb,
            ROUND(index_length / 1024 / 1024, 2) as index_mb,
            ROUND((data_length + index_length) / 1024 / 1024, 2) as total_mb,
            ROUND(data_length / table_rows, 2) as avg_row_bytes
        FROM information_schema.tables
        WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
          AND table_type = 'BASE TABLE'
          AND (data_length + index_length) > 0
        ORDER BY (data_length + index_length) DESC
        LIMIT %s
        """
        
        result = await execute_query(query, [limit])
        
        if not result:
            return "No tables with size data found in any user database"
        
        # Format sizes for better readability
        for row in result:
            row['data_size'] = format_bytes((row.get('data_mb', 0) or 0) * 1024 * 1024)
            row['index_size'] = format_bytes((row.get('index_mb', 0) or 0) * 1024 * 1024)
            row['total_size'] = format_bytes((row.get('total_mb', 0) or 0) * 1024 * 1024)
            row['avg_row_size'] = format_bytes(row.get('avg_row_bytes', 0) or 0)
            
        return format_table_data(result, f"Top {limit} Tables by Size Across All Databases")
        
    except Exception as e:
        logger.error(f"Failed to get all databases table sizes: {e}")
        return f"Error retrieving table sizes from all databases: {e}"


async def get_database_overview(database_name: str) -> str:
    """Helper function to get database overview with all tables"""
    try:
        overview_query = """
        SELECT 
            table_name,
            table_type,
            engine,
            table_rows,
            ROUND(data_length / 1024 / 1024, 2) as data_mb,
            ROUND(index_length / 1024 / 1024, 2) as index_mb,
            ROUND((data_length + index_length) / 1024 / 1024, 2) as total_mb,
            table_comment
        FROM information_schema.tables
        WHERE table_schema = %s
        ORDER BY table_type, table_name
        """
        
        result = await execute_query(overview_query, [database_name])
        
        if not result:
            return f"No tables found in database '{database_name}'"
        
        # Format sizes for better readability
        for row in result:
            data_mb = row.get('data_mb', 0) or 0
            index_mb = row.get('index_mb', 0) or 0
            total_mb = row.get('total_mb', 0) or 0
            
            row['data_size'] = format_bytes(data_mb * 1024 * 1024) if data_mb > 0 else "0 B"
            row['index_size'] = format_bytes(index_mb * 1024 * 1024) if index_mb > 0 else "0 B"
            row['total_size'] = format_bytes(total_mb * 1024 * 1024) if total_mb > 0 else "0 B"
            
        return format_table_data(result, f"Database Overview for '{database_name}'")
        
    except Exception as e:
        logger.error(f"Failed to get database overview: {e}")
        return f"Error retrieving database overview: {e}"


@mcp.tool()
async def get_mysql_config(database_name: Optional[str] = None, search_term: Optional[str] = None) -> str:
    """
    [Tool Purpose]: Get MySQL server configuration variables
    
    [Exact Functionality]:
    - Show server configuration variables and their values
    - Filter by search term if provided
    - Display both global and session variables
    - Show variable descriptions where available
    
    [Required Use Cases]:
    - When user requests "MySQL config", "server variables", "configuration"
    - When diagnosing configuration issues
    - When checking specific settings
    
    Args:
        database_name: Database name to connect to (uses default if omitted)
        search_term: Filter variables by name containing this term
    
    Returns:
        Formatted string with MySQL configuration
    """
    try:
        query = """
        SELECT 
            variable_name,
            variable_value
        FROM performance_schema.global_variables
        """
        
        params = []
        if search_term:
            query += " WHERE variable_name LIKE %s"
            params.append(f"%{search_term}%")
            
        query += " ORDER BY variable_name"
        
        result = await execute_query(query, params, database=database_name)
        
        if not result:
            search_info = f" matching '{search_term}'" if search_term else ""
            return f"No configuration variables found{search_info}"
        
        title = f"MySQL Configuration"
        if search_term:
            title += f" (filtered by '{search_term}')"
            
        return format_table_data(result, title)
        
    except Exception as e:
        logger.error(f"Failed to get MySQL config: {e}")
        return f"Error retrieving MySQL config: {e}"


@mcp.tool()
async def get_user_list(database_name: Optional[str] = None) -> str:
    """
    [Tool Purpose]: List all MySQL users and their privileges
    
    [Exact Functionality]:
    - Show all MySQL users with their host patterns
    - Display account status and authentication info
    - Show password expiration and locking status
    - Include SSL and resource limit information
    
    [Required Use Cases]:
    - When user requests "user list", "MySQL users", "account info"
    - When managing user access and security
    - When auditing user accounts
    
    Args:
        database_name: Database name to connect to (uses default if omitted)
    
    Returns:
        Formatted string with user account information
    """
    try:
        query = """
        SELECT 
            user,
            host,
            account_locked,
            password_expired,
            password_last_changed,
            password_lifetime,
            plugin,
            authentication_string,
            ssl_type,
            max_connections,
            max_user_connections
        FROM mysql.user
        ORDER BY user, host
        """
        
        result = await execute_query(query, database=database_name)
        
        if not result:
            return "No users found"
        
        # Format the results for better readability
        for row in result:
            # Convert Y/N to Yes/No
            row['account_locked'] = 'Yes' if row['account_locked'] == 'Y' else 'No'
            row['password_expired'] = 'Yes' if row['password_expired'] == 'Y' else 'No'
            
            # Hide authentication string for security
            if row['authentication_string']:
                row['authentication_string'] = '***'
            
        return format_table_data(result, "MySQL Users")
        
    except Exception as e:
        logger.error(f"Failed to get user list: {e}")
        return f"Error retrieving user list: {e}"


@mcp.tool()
async def get_server_status(database_name: Optional[str] = None, search_term: Optional[str] = None) -> str:
    """
    [Tool Purpose]: Get MySQL server status variables and performance counters
    
    [Exact Functionality]:
    - Show server status variables with current values
    - Display performance counters and operational metrics
    - Filter by search term if provided
    - Include connection, query, and resource statistics
    
    [Required Use Cases]:
    - When user requests "server status", "MySQL status", "performance metrics"
    - When monitoring server health and performance
    - When diagnosing operational issues
    
    Args:
        database_name: Database name to connect to (uses default if omitted)
        search_term: Filter status variables by name containing this term
    
    Returns:
        Formatted string with server status information
    """
    try:
        query = "SHOW STATUS"
        
        if search_term:
            query += f" LIKE '%{search_term}%'"
        
        result = await execute_query(query, database=database_name)
        
        if not result:
            search_info = f" matching '{search_term}'" if search_term else ""
            return f"No status variables found{search_info}"
        
        # Convert to consistent format
        formatted_result = []
        for row in result:
            # Handle different column name formats
            var_name = row.get('Variable_name') or row.get('variable_name')
            var_value = row.get('Value') or row.get('variable_value')
            formatted_result.append({
                'variable_name': var_name,
                'value': var_value
            })
        
        title = f"MySQL Server Status"
        if search_term:
            title += f" (filtered by '{search_term}')"
            
        return format_table_data(formatted_result, title)
        
    except Exception as e:
        logger.error(f"Failed to get server status: {e}")
        return f"Error retrieving server status: {e}"


@mcp.tool()
async def get_table_size_info(database_name: Optional[str] = None, limit: int = 20) -> str:
    """
    [Tool Purpose]: Get table size information and storage analysis
    
    [Exact Functionality]:
    - Show table sizes with data and index breakdown
    - Display size ratios and storage efficiency
    - Order by total size (largest first)
    - Include row counts and average row sizes
    
    [Required Use Cases]:
    - When user requests "table sizes", "largest tables", "storage analysis"
    - When planning database optimization
    - When monitoring storage usage
    
    Args:
        database_name: Database name to analyze (uses current database if omitted, shows all if none)
        limit: Maximum number of tables to return (default: 20)
    
    Returns:
        Formatted string with table size information
    """
    try:
        # If no database specified, analyze all databases
        if not database_name:
            current_db = await get_current_database_name()
            if current_db and current_db != "unknown":
                database_name = current_db
            else:
                return await get_all_databases_table_sizes(limit)
        
        query = """
        SELECT 
            table_name,
            table_rows,
            ROUND(data_length / 1024 / 1024, 2) as data_mb,
            ROUND(index_length / 1024 / 1024, 2) as index_mb,
            ROUND((data_length + index_length) / 1024 / 1024, 2) as total_mb,
            ROUND(data_length / table_rows, 2) as avg_row_bytes,
            ROUND((index_length / (data_length + index_length)) * 100, 2) as index_ratio_pct
        FROM information_schema.tables
        WHERE table_schema = %s 
          AND table_type = 'BASE TABLE'
          AND (data_length + index_length) > 0
        ORDER BY (data_length + index_length) DESC
        LIMIT %s
        """
        
        result = await execute_query(query, [database_name, limit], database=database_name)
        
        if not result:
            return f"No tables with size data found in database '{database_name}'"
        
        # Format sizes for better readability
        for row in result:
            row['data_size'] = format_bytes((row.get('data_mb', 0) or 0) * 1024 * 1024)
            row['index_size'] = format_bytes((row.get('index_mb', 0) or 0) * 1024 * 1024)
            row['total_size'] = format_bytes((row.get('total_mb', 0) or 0) * 1024 * 1024)
            row['avg_row_size'] = format_bytes(row.get('avg_row_bytes', 0) or 0)
            
        return format_table_data(result, f"Top {limit} Tables by Size in '{database_name}' Database")
        
    except Exception as e:
        logger.error(f"Failed to get table size info: {e}")
        return f"Error retrieving table size info: {e}"


@mcp.tool()
async def get_database_size_info(database_name: Optional[str] = None) -> str:
    """
    [Tool Purpose]: Get database size information and storage distribution
    
    [Exact Functionality]:
    - Show database sizes with table counts
    - Display total, data, and index size breakdown
    - Compare databases by storage usage
    - Include average table sizes
    
    [Required Use Cases]:
    - When user requests "database sizes", "storage usage", "database capacity"
    - When planning database resources
    - When monitoring growth trends
    
    Args:
        database_name: Specific database name to analyze (analyzes all databases if omitted)
    
    Returns:
        Formatted string with database size information
    """
    try:
        if database_name:
            # Analyze specific database
            query = """
            SELECT 
                table_schema as database_name,
                COUNT(*) as table_count,
                ROUND(SUM(data_length) / 1024 / 1024, 2) as data_mb,
                ROUND(SUM(index_length) / 1024 / 1024, 2) as index_mb,
                ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as total_mb,
                ROUND(AVG(data_length + index_length) / 1024 / 1024, 2) as avg_table_mb
            FROM information_schema.tables
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
            GROUP BY table_schema
            """
            params = [database_name]
        else:
            # Analyze all user databases
            query = """
            SELECT 
                table_schema as database_name,
                COUNT(*) as table_count,
                ROUND(SUM(data_length) / 1024 / 1024, 2) as data_mb,
                ROUND(SUM(index_length) / 1024 / 1024, 2) as index_mb,
                ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as total_mb,
                ROUND(AVG(data_length + index_length) / 1024 / 1024, 2) as avg_table_mb
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
              AND table_type = 'BASE TABLE'
            GROUP BY table_schema
            ORDER BY SUM(data_length + index_length) DESC
            """
            params = []
        
        result = await execute_query(query, params, database=database_name)
        
        if not result:
            target = f"database '{database_name}'" if database_name else "any user databases"
            return f"No size data found for {target}"
        
        # Format sizes for better readability
        for row in result:
            row['data_size'] = format_bytes((row.get('data_mb', 0) or 0) * 1024 * 1024)
            row['index_size'] = format_bytes((row.get('index_mb', 0) or 0) * 1024 * 1024)
            row['total_size'] = format_bytes((row.get('total_mb', 0) or 0) * 1024 * 1024)
            row['avg_table_size'] = format_bytes((row.get('avg_table_mb', 0) or 0) * 1024 * 1024)
            
        title = f"Database Size Information"
        if database_name:
            title += f" for '{database_name}'"
            
        return format_table_data(result, title)
        
    except Exception as e:
        logger.error(f"Failed to get database size info: {e}")
        return f"Error retrieving database size info: {e}"


@mcp.tool()
async def get_index_usage_stats(database_name: Optional[str] = None, limit: int = 20) -> str:
    """
    [Tool Purpose]: Get index usage statistics and efficiency analysis
    
    [Exact Functionality]:
    - Show index information with cardinality and selectivity
    - Display index types and usage patterns
    - Identify potentially unused or inefficient indexes
    - Order by cardinality and selectivity metrics
    
    [Required Use Cases]:
    - When user requests "index stats", "index analysis", "index optimization"
    - When optimizing query performance
    - When identifying redundant indexes
    
    Args:
        database_name: Database name to analyze (uses current database if omitted)
        limit: Maximum number of indexes to return (default: 20)
    
    Returns:
        Formatted string with index usage statistics
    """
    try:
        # Use current database if not specified
        if not database_name:
            current_db = await get_current_database_name()
            if current_db and current_db != "unknown":
                database_name = current_db
            else:
                # Provide helpful guidance with available databases
                db_list = await get_database_list()
                return f"No database specified and no current database selected.\n\nTo get index statistics, please specify a database name.\n\n{db_list}"
        
        query = """
        SELECT 
            table_name,
            index_name,
            column_name,
            seq_in_index,
            cardinality,
            index_type,
            non_unique,
            CASE 
                WHEN cardinality = 0 THEN 0
                ELSE ROUND((cardinality / (SELECT table_rows FROM information_schema.tables t WHERE t.table_schema = s.table_schema AND t.table_name = s.table_name)) * 100, 2)
            END as selectivity_pct,
            CASE 
                WHEN non_unique = 0 THEN 'UNIQUE'
                WHEN index_name = 'PRIMARY' THEN 'PRIMARY'
                ELSE 'INDEX'
            END as index_category
        FROM information_schema.statistics s
        WHERE table_schema = %s
        ORDER BY cardinality DESC, table_name, index_name, seq_in_index
        LIMIT %s
        """
        
        result = await execute_query(query, [database_name, limit], database=database_name)
        
        if not result:
            return f"No index statistics found for database '{database_name}'"
        
        # Format the results
        for row in result:
            # Add recommendations based on selectivity
            selectivity = row.get('selectivity_pct', 0) or 0
            if selectivity < 1:
                row['recommendation'] = 'Low selectivity - consider reviewing'
            elif selectivity > 90:
                row['recommendation'] = 'High selectivity - efficient'
            else:
                row['recommendation'] = 'Normal selectivity'
            
        return format_table_data(result, f"Top {limit} Index Statistics for '{database_name}' Database")
        
    except Exception as e:
        logger.error(f"Failed to get index usage stats: {e}")
        return f"Error retrieving index usage stats: {e}"


@mcp.tool()
async def get_connection_info(database_name: Optional[str] = None) -> str:
    """
    [Tool Purpose]: Get current connection and process information
    
    [Exact Functionality]:
    - Show active connections with detailed process information
    - Display connection duration, state, and current operations
    - Include user, host, and database context for each connection
    - Filter out system processes for clarity
    
    [Required Use Cases]:
    - When user requests "connection info", "active processes", "session details"
    - When monitoring database activity and user sessions
    - When diagnosing connection issues
    
    Args:
        database_name: Database name to connect to (uses default if omitted)
    
    Returns:
        Formatted string with connection information
    """
    try:
        query = """
        SELECT 
            id as connection_id,
            user,
            host,
            db as database_name,
            command,
            time as duration_sec,
            state,
            SUBSTRING(COALESCE(info, ''), 1, 100) as current_query
        FROM information_schema.processlist
        WHERE user != 'system user' AND user IS NOT NULL
        ORDER BY time DESC, id
        """
        
        result = await execute_query(query, database=database_name)
        
        if not result:
            return "No active connections found"
        
        # Format duration for better readability
        for row in result:
            duration_sec = row.get('duration_sec', 0) or 0
            row['duration'] = format_duration(duration_sec)
            
            # Clean up query display
            current_query = row.get('current_query', '') or ''
            if len(current_query.strip()) == 0:
                row['current_query'] = '(idle)'
            elif current_query == 'NULL':
                row['current_query'] = '(no current query)'
            
        return format_table_data(result, "Current Database Connections")
        
    except Exception as e:
        logger.error(f"Failed to get connection info: {e}")
        return f"Error retrieving connection info: {e}"


@mcp.tool()
async def get_slow_queries(database_name: Optional[str] = None, limit: int = 20) -> str:
    """
    [Tool Purpose]: Get slow queries from Performance Schema
    
    [Exact Functionality]:
    - Show slowest queries with execution statistics
    - Display query text, execution count, and timing information
    - Show rows examined and returned
    - Order by total execution time
    
    [Required Use Cases]:
    - When user requests "slow queries", "performance analysis", "query optimization"
    - When diagnosing performance issues
    - When identifying problematic queries
    
    Args:
        database_name: Database name to connect to (uses default if omitted)
        limit: Maximum number of queries to return (default: 20)
    
    Returns:
        Formatted string with slow query information
    """
    try:
        # Check if Performance Schema is enabled
        if not await check_performance_schema_enabled():
            return "Performance Schema is not enabled. Cannot retrieve slow query data."
        
        query = await get_slow_queries_query(database=database_name)
        query += f" LIMIT {limit}"
        
        result = await execute_query(query, database=database_name)
        
        if not result:
            return "No slow query data found"
        
        # Format the results for better readability
        for row in result:
            # Format query text to be more readable
            if row.get('query'):
                query_text = row['query']
                if len(query_text) > 100:
                    row['query'] = query_text[:97] + "..."
                else:
                    row['query'] = query_text
            
            # Format timing columns
            row['total_time'] = format_duration(row.get('total_time_sec', 0))
            row['avg_time'] = format_duration(row.get('avg_time_sec', 0))
            
        return format_table_data(result, f"Top {limit} Slow Queries")
        
    except Exception as e:
        logger.error(f"Failed to get slow queries: {e}")
        return f"Error retrieving slow queries: {e}"


@mcp.tool()
async def get_table_io_stats(database_name: Optional[str] = None, limit: int = 20) -> str:
    """
    [Tool Purpose]: Get table I/O statistics from Performance Schema
    
    [Exact Functionality]:
    - Show I/O statistics for tables including reads, writes, and timing
    - Display fetch, insert, update, delete operations
    - Order by total I/O time
    - Show both request counts and timing information
    
    [Required Use Cases]:
    - When user requests "table I/O", "table performance", "I/O statistics"
    - When analyzing table access patterns
    - When identifying heavily used tables
    
    Args:
        database_name: Database name to connect to (uses default if omitted)
        limit: Maximum number of tables to return (default: 20)
    
    Returns:
        Formatted string with table I/O statistics
    """
    try:
        # Check if Performance Schema is enabled
        if not await check_performance_schema_enabled():
            return "Performance Schema is not enabled. Cannot retrieve I/O statistics."
        
        query = await get_table_io_stats_query(database=database_name)
        query += f" LIMIT {limit}"
        
        result = await execute_query(query, database=database_name)
        
        if not result:
            return "No table I/O statistics found"
        
        # Format the results for better readability
        for row in result:
            # Format timing columns
            for time_col in ['read_time_sec', 'write_time_sec', 'fetch_time_sec', 
                           'insert_time_sec', 'update_time_sec', 'delete_time_sec']:
                if time_col in row and row[time_col]:
                    time_key = time_col.replace('_sec', '')
                    row[time_key] = format_duration(row[time_col])
            
        return format_table_data(result, f"Top {limit} Tables by I/O Activity")
        
    except Exception as e:
        logger.error(f"Failed to get table I/O stats: {e}")
        return f"Error retrieving table I/O stats: {e}"


@mcp.tool()
async def get_lock_monitoring(database_name: Optional[str] = None) -> str:
    """
    [Tool Purpose]: Monitor current locks in MySQL
    
    [Exact Functionality]:
    - Show current lock information from Performance Schema
    - Display lock types, modes, and status
    - Show which sessions are holding or waiting for locks
    - Include query information for lock holders
    
    [Required Use Cases]:
    - When user requests "lock monitoring", "deadlock check", "blocked sessions"
    - When diagnosing locking issues
    - When checking for lock contention
    
    Args:
        database_name: Database name to connect to (uses default if omitted)
    
    Returns:
        Formatted string with lock monitoring information
    """
    try:
        # Check if Performance Schema is enabled
        if not await check_performance_schema_enabled():
            return "Performance Schema is not enabled. Cannot retrieve lock information."
        
        query = await get_lock_waits_query(database=database_name)
        
        result = await execute_query(query, database=database_name)
        
        if not result:
            return "No active locks found"
        
        # Format the results for better readability
        for row in result:
            # Format duration
            if row.get('time'):
                row['duration'] = format_duration(row['time'])
        
        return format_table_data(result, "Current Lock Information")
        
    except Exception as e:
        logger.error(f"Failed to get lock monitoring: {e}")
        return f"Error retrieving lock monitoring: {e}"


@mcp.tool()
async def get_current_database_info(database_name: Optional[str] = None) -> str:
    """
    [Tool Purpose]: Get information about the currently connected or specified database
    
    [Exact Functionality]:
    - Show database name, character set, and collation
    - Display database size and table count
    - Show creation time if available
    - Include storage engine distribution
    
    [Required Use Cases]:
    - When user requests "current database", "database info", "database details"
    - When getting context about the working database
    
    Args:
        database_name: Database name to analyze (uses current database if omitted, shows available databases if none)
    
    Returns:
        Formatted string with database information or available databases
    """
    try:
        # Use current database if not specified
        if not database_name:
            current_db = await get_current_database_name()
            if current_db and current_db != "unknown":
                database_name = current_db
            else:
                # Provide helpful guidance with available databases
                db_list = await get_database_list()
                return f"No database specified and no current database selected.\n\nTo get database information, please specify a database name.\n\n{db_list}"
        
        # Get database info
        db_query = """
        SELECT 
            schema_name as database_name,
            default_character_set_name as charset,
            default_collation_name as collation
        FROM information_schema.schemata
        WHERE schema_name = %s
        """
        
        # Get table count and size
        tables_query = """
        SELECT 
            COUNT(*) as table_count,
            ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as total_size_mb,
            ROUND(SUM(data_length) / 1024 / 1024, 2) as data_size_mb,
            ROUND(SUM(index_length) / 1024 / 1024, 2) as index_size_mb
        FROM information_schema.tables
        WHERE table_schema = %s
        """
        
        # Get storage engine distribution
        engines_query = """
        SELECT 
            ENGINE,
            COUNT(*) as table_count
        FROM information_schema.tables
        WHERE table_schema = %s AND table_type = 'BASE TABLE'
        GROUP BY ENGINE
        ORDER BY table_count DESC
        """
        
        params = [database_name]
        
        db_info = await execute_single_query(db_query, params, database=database_name)
        tables_info = await execute_single_query(tables_query, params, database=database_name)
        engines_info = await execute_query(engines_query, params, database=database_name)
        
        if not db_info:
            # Provide helpful guidance with available databases
            db_list = await get_database_list()
            return f"Database '{database_name}' not found.\n\nAvailable databases:\n{db_list}"
        
        result = [f"=== Database Information: {database_name} ===\n"]
        
        # Basic info
        result.append(f"Character Set: {db_info['charset']}")
        result.append(f"Collation: {db_info['collation']}")
        
        # Size and table info
        if tables_info:
            result.append(f"Table Count: {tables_info['table_count']}")
            if tables_info['total_size_mb']:
                result.append(f"Total Size: {format_bytes(tables_info['total_size_mb'] * 1024 * 1024)}")
                result.append(f"Data Size: {format_bytes(tables_info['data_size_mb'] * 1024 * 1024)}")
                result.append(f"Index Size: {format_bytes(tables_info['index_size_mb'] * 1024 * 1024)}")
        
        # Storage engines
        if engines_info:
            result.append("\n=== Storage Engines ===")
            for engine in engines_info:
                engine_name = engine.get('ENGINE') or engine.get('engine', 'Unknown')
                table_count = engine.get('table_count', 0)
                result.append(f"{engine_name}: {table_count} tables")
        
        return "\n".join(result)
        
    except Exception as e:
        logger.error(f"Failed to get current database info: {e}")
        return f"Error retrieving database info: {e}"


def main(argv: Optional[List[str]] = None):
    """Entrypoint for MCP MySQL Operations server.

    Supports optional CLI arguments (e.g. --log-level DEBUG) while remaining
    backward-compatible with stdio launcher expectations.
    """
    global mcp
    
    parser = argparse.ArgumentParser(prog="mcp-mysql-ops", description="MCP MySQL Operations Server")
    parser.add_argument(
        "--log-level",
        dest="log_level",
        help="Logging level override (DEBUG, INFO, WARNING, ERROR, CRITICAL). Overrides MCP_LOG_LEVEL env if provided.",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    parser.add_argument(
        "--type",
        dest="transport_type",
        help="Transport type (stdio or streamable-http). Default: stdio",
        choices=["stdio", "streamable-http"],
    )
    parser.add_argument(
        "--host",
        dest="host",
        help="Host address for streamable-http transport. Default: 127.0.0.1",
    )
    parser.add_argument(
        "--port",
        dest="port",
        type=int,
        help="Port number for streamable-http transport. Default: 8000",
    )
    parser.add_argument(
        "--auth-enable",
        dest="auth_enable",
        action="store_true",
        help="Enable Bearer token authentication for streamable-http mode. Default: False",
    )
    parser.add_argument(
        "--secret-key",
        dest="secret_key",
        help="Secret key for Bearer token authentication. Required when auth is enabled.",
    )
    # Allow future extension without breaking unknown args usage
    args = parser.parse_args(argv)

    # Determine log level: CLI arg > environment variable > default
    log_level = args.log_level or os.getenv("MCP_LOG_LEVEL", "INFO")
    
    # Set logging level
    logging.getLogger().setLevel(log_level)
    logger.setLevel(log_level)
    
    if args.log_level:
        logger.info("Log level set via CLI to %s", args.log_level)
    elif os.getenv("MCP_LOG_LEVEL"):
        logger.info("Log level set via environment variable to %s", log_level)
    else:
        logger.info("Using default log level: %s", log_level)

    # 우선순위: 실행옵션 > 환경변수 > 기본값
    # Transport type 결정
    transport_type = args.transport_type or os.getenv("FASTMCP_TYPE", "stdio")
    
    # Host 결정
    host = args.host or os.getenv("FASTMCP_HOST", "127.0.0.1")
    
    # Port 결정 (간결하게)
    port = args.port or int(os.getenv("FASTMCP_PORT", 8000))
    
    # Authentication 설정 결정
    auth_enable = args.auth_enable or os.getenv("REMOTE_AUTH_ENABLE", "false").lower() in ("true", "1", "yes", "on")
    secret_key = args.secret_key or os.getenv("REMOTE_SECRET_KEY", "")
    
    # Validation for streamable-http mode with authentication
    if transport_type == "streamable-http":
        if auth_enable:
            if not secret_key:
                logger.error("ERROR: Authentication is enabled but no secret key provided.")
                logger.error("Please set REMOTE_SECRET_KEY environment variable or use --secret-key argument.")
                return
            logger.info("Authentication enabled for streamable-http transport")
        else:
            logger.warning("WARNING: streamable-http mode without authentication enabled!")
            logger.warning("This server will accept requests without Bearer token verification.")
            logger.warning("Set REMOTE_AUTH_ENABLE=true and REMOTE_SECRET_KEY to enable authentication.")

    # Note: MCP instance with authentication is already initialized at module level
    # based on environment variables. CLI arguments will override if different.
    if auth_enable != _auth_enable or secret_key != _secret_key:
        logger.warning("CLI authentication settings differ from environment variables.")
        logger.warning("Environment settings take precedence during module initialization.")

    # Transport 모드에 따른 실행
    if transport_type == "streamable-http":
        logger.info(f"Starting streamable-http server on {host}:{port}")
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        logger.info("Starting stdio transport for local usage")
        mcp.run(transport='stdio')


@smithery.server()
def create_server() -> FastMCP:
    """Factory used by Smithery deployments to obtain the FastMCP server instance."""
    refresh_configs()
    # logger.info(
    #     "Smithery create_server invoked with MySQL target %s:%s/%s",
    #     MYSQL_CONFIG["host"],
    #     MYSQL_CONFIG["port"],
    #     MYSQL_CONFIG["db"],
    # )
    return mcp


if __name__ == "__main__":
    main()
