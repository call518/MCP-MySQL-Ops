import aiomysql
import logging
import os
from typing import Any, Dict, List, Optional, Union
import json
from datetime import datetime

# Logger configuration
logger = logging.getLogger(__name__)

# MySQL connection configuration
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "db": os.getenv("MYSQL_DATABASE", "mysql"),
    "charset": "utf8mb4",
    "autocommit": True,
}


def refresh_configs() -> None:
    """Refresh cached MySQL connection details from the current environment."""
    MYSQL_CONFIG.update(
        {
            "host": os.getenv("MYSQL_HOST", MYSQL_CONFIG["host"]),
            "port": int(os.getenv("MYSQL_PORT", MYSQL_CONFIG["port"])),
            "user": os.getenv("MYSQL_USER", MYSQL_CONFIG["user"]),
            "password": os.getenv("MYSQL_PASSWORD", MYSQL_CONFIG["password"]),
            "db": os.getenv("MYSQL_DATABASE", MYSQL_CONFIG["db"]),
        }
    )


async def get_current_database_name(database: str = None) -> str:
    """Get the name of the currently connected database.
    
    Args:
        database: Database name to connect to. If None, uses default from config.
        
    Returns:
        Current database name as string
    """
    try:
        query = "SELECT DATABASE() as database_name"
        result = await execute_query(query, [], database=database)
        return result[0]['database_name'] if result else "unknown"
    except Exception as e:
        logger.error(f"Failed to get current database name: {e}")
        return "unknown"


async def get_db_connection(database: str = None) -> aiomysql.Connection:
    """Create MySQL database connection.
    
    Args:
        database: Database name to connect to. If None, uses default from config.
    """
    try:
        refresh_configs()
        config = MYSQL_CONFIG.copy()
        if database:
            config["db"] = database
            
        conn = await aiomysql.connect(**config)
        logger.debug(f"Connected to MySQL at {config['host']}:{config['port']}/{config['db']}")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to MySQL: {e}")
        raise


async def execute_query(query: str, params: Optional[List] = None, database: str = None) -> List[Dict[str, Any]]:
    """Execute query and return results.
    
    Args:
        query: SQL query to execute
        params: Query parameters
        database: Database name to connect to. If None, uses default from config.
    """
    conn = None
    try:
        conn = await get_db_connection(database)
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            if params:
                await cursor.execute(query, params)
            else:
                await cursor.execute(query)
            
            rows = await cursor.fetchall()
            
            # Convert to list of dicts
            result = []
            for row in rows:
                # Convert datetime and other types to serializable format
                converted_row = {}
                for key, value in row.items():
                    if isinstance(value, datetime):
                        converted_row[key] = value.isoformat()
                    else:
                        converted_row[key] = value
                result.append(converted_row)
        
        logger.debug(f"Query executed successfully, returned {len(result)} rows")
        return result
        
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        logger.debug(f"Failed query: {query}")
        raise
    finally:
        if conn:
            await conn.ensure_closed()


async def execute_single_query(query: str, params: Optional[List] = None, database: str = None) -> Optional[Dict[str, Any]]:
    """Execute query that returns a single result.
    
    Args:
        query: SQL query to execute
        params: Query parameters  
        database: Database name to connect to. If None, uses default from config.
    """
    results = await execute_query(query, params, database)
    return results[0] if results else None


def format_bytes(bytes_value: Union[int, float, None]) -> str:
    """Format byte values into human-readable format."""
    if bytes_value is None:
        return "N/A"
    
    bytes_value = float(bytes_value)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def format_duration(seconds: Union[int, float, None]) -> str:
    """Format seconds into human-readable format."""
    if seconds is None:
        return "N/A"
    
    seconds = float(seconds)
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        return f"{seconds/60:.2f}m"
    else:
        return f"{seconds/3600:.2f}h"


def format_table_data(data: List[Dict[str, Any]], title: str = "") -> str:
    """Convert table data into formatted string."""
    if not data:
        return f"No data found{' for ' + title if title else ''}"
    
    result = []
    if title:
        result.append(f"=== {title} ===\n")
    
    # Format as table
    if len(data) == 1:
        # Display single record as key-value pairs
        for key, value in data[0].items():
            if isinstance(value, (int, float)) and key.endswith(('_bytes', '_size')):
                value = format_bytes(value)
            elif isinstance(value, (int, float)) and key.endswith(('_time', '_duration')):
                value = format_duration(value)
            result.append(f"{key}: {value}")
    else:
        # Display multiple records as table format
        headers = list(data[0].keys())
        
        # Add headers
        result.append(" | ".join(headers))
        result.append("-" * (sum(len(h) for h in headers) + len(headers) * 3 - 1))
        
        # Add data rows
        for row in data:
            formatted_row = []
            for key, value in row.items():
                if isinstance(value, (int, float)) and key.endswith(('_bytes', '_size')):
                    formatted_row.append(format_bytes(value))
                elif isinstance(value, (int, float)) and key.endswith(('_time', '_duration')):
                    formatted_row.append(format_duration(value))
                else:
                    formatted_row.append(str(value) if value is not None else "NULL")
            result.append(" | ".join(formatted_row))
    
    return "\n".join(result)


async def get_server_version() -> str:
    """Return MySQL server version."""
    try:
        result = await execute_single_query("SELECT VERSION() as version")
        return result["version"] if result else "Unknown"
    except Exception as e:
        logger.error(f"Failed to get server version: {e}")
        return f"Error: {e}"


async def check_performance_schema_enabled() -> bool:
    """Check if Performance Schema is enabled."""
    try:
        query = "SELECT @@performance_schema as enabled"
        result = await execute_single_query(query)
        return bool(result["enabled"]) if result else False
    except Exception:
        return False


async def check_slow_query_log_enabled() -> bool:
    """Check if slow query log is enabled."""
    try:
        query = "SELECT @@slow_query_log as enabled"
        result = await execute_single_query(query)
        return bool(result["enabled"]) if result else False
    except Exception:
        return False


# Performance Schema related functions
async def get_performance_schema_data(table_name: str, limit: int = 20, database: str = None) -> List[Dict[str, Any]]:
    """Get data from Performance Schema tables.
    
    Args:
        table_name: Performance Schema table name
        limit: Maximum number of results to return
        database: Database name to query (uses default if omitted)
    """
    try:
        query = f"SELECT * FROM performance_schema.{table_name} LIMIT %s"
        return await execute_query(query, [limit], database=database)
    except Exception as e:
        logger.error(f"Failed to fetch performance_schema.{table_name} data: {e}")
        raise Exception(f"Failed to fetch performance_schema.{table_name} data: {e}")


# Slow query related functions
async def get_slow_query_data(limit: int = 20, database: str = None) -> List[Dict[str, Any]]:
    """Get slow query data from Performance Schema.
    
    Args:
        limit: Maximum number of results to return
        database: Database name to query (uses default if omitted)
    """
    try:
        query = """
        SELECT 
            digest_text as query,
            count_star as exec_count,
            sum_timer_wait/1000000000000 as total_time_sec,
            avg_timer_wait/1000000000000 as avg_time_sec,
            sum_rows_examined as rows_examined,
            sum_rows_sent as rows_sent,
            first_seen,
            last_seen
        FROM performance_schema.events_statements_summary_by_digest 
        WHERE digest_text IS NOT NULL
        ORDER BY sum_timer_wait DESC 
        LIMIT %s
        """
        return await execute_query(query, [limit], database=database)
    except Exception as e:
        logger.error(f"Failed to fetch slow query data: {e}")
        raise Exception(f"Failed to fetch slow query data: {e}")


def sanitize_connection_info() -> Dict[str, Any]:
    """Remove sensitive information from connection info."""
    config = MYSQL_CONFIG.copy()
    config["password"] = "***"
    return config


def read_prompt_template(path: str) -> str:
    """
    Reads the MCP prompt template file and returns its content as a string.
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def parse_prompt_sections(template: str):
    """
    Parses the prompt template into section headings and sections.
    Returns (headings, sections).
    """
    lines = template.splitlines()
    sections = []
    current = []
    headings = []
    for line in lines:
        if line.startswith("## "):
            if current:
                sections.append("\n".join(current))
                current = []
            headings.append(line[3:].strip())  # Remove "## "
        current.append(line)
    if current:
        sections.append("\n".join(current))
    return headings, sections


def get_prompt_template(section: str = None) -> str:
    """
    Returns the prompt template content, optionally filtered by section.
    """
    # Get the directory where this file is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, "prompt_template.md")
    
    if not os.path.exists(template_path):
        return "Prompt template not found."
    
    template = read_prompt_template(template_path)
    
    if section is None:
        return template
    
    headings, sections = parse_prompt_sections(template)
    
    # Find the section
    for i, heading in enumerate(headings):
        if heading.lower() == section.lower():
            return sections[i]
    
    return f"Section '{section}' not found in prompt template."
