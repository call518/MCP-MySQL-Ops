"""
MySQL Version Compatibility Utilities

Provides version detection and compatibility handling for MCP MySQL tools.
"""

import re
import logging
from typing import Tuple, Optional
from .functions import execute_single_query

logger = logging.getLogger(__name__)

class MySQLVersion:
    """MySQL version information and compatibility utilities."""
    
    def __init__(self, major: int, minor: int = 0, patch: int = 0):
        self.major = major
        self.minor = minor  
        self.patch = patch
        
    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"
        
    def __ge__(self, other):
        if isinstance(other, (int, float)):
            return self.major >= other
        if isinstance(other, MySQLVersion):
            return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)
        return False
    
    def __lt__(self, other):
        if isinstance(other, (int, float)):
            return self.major < other
        if isinstance(other, MySQLVersion):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
        return False
        
    @property
    def is_modern(self) -> bool:
        """Check if this is a modern MySQL version (8.0+)."""
        return self.major >= 8
        
    @property
    def has_performance_schema(self) -> bool:
        """Check if Performance Schema is available (MySQL 5.5+)."""
        return self.major >= 5 and (self.major > 5 or self.minor >= 5)
        
    @property
    def has_sys_schema(self) -> bool:
        """Check if sys schema is available (MySQL 5.7+)."""
        return self.major >= 5 and (self.major > 5 or self.minor >= 7)
        
    @property
    def has_information_schema_innodb_tables(self) -> bool:
        """Check if INFORMATION_SCHEMA InnoDB tables are available (MySQL 5.5+)."""
        return self.major >= 5 and (self.major > 5 or self.minor >= 5)
        
    @property
    def has_data_locks_table(self) -> bool:
        """Check if data_locks table is available in Performance Schema (MySQL 8.0+)."""
        return self.major >= 8
        
    @property
    def has_replica_status(self) -> bool:
        """Check if SHOW REPLICA STATUS is available (MySQL 8.0.22+)."""
        return self.major >= 8 and (self.major > 8 or (self.minor >= 0 and self.patch >= 22))
        
    @property
    def has_innodb_metrics(self) -> bool:
        """Check if INFORMATION_SCHEMA.INNODB_METRICS is available (MySQL 5.6+)."""
        return self.major >= 5 and (self.major > 5 or self.minor >= 6)


async def get_mysql_version(database: str = None) -> Optional[MySQLVersion]:
    """Get MySQL version information.
    
    Args:
        database: Database name to connect to
        
    Returns:
        MySQLVersion object or None if detection failed
    """
    try:
        result = await execute_single_query("SELECT VERSION() as version", database=database)
        if not result:
            logger.error("Failed to get MySQL version")
            return None
            
        version_str = result["version"]
        logger.debug(f"Raw MySQL version string: {version_str}")
        
        # Parse version string (e.g., "8.0.35" or "8.0.35-log")
        match = re.match(r"(\d+)\.(\d+)\.(\d+)", version_str)
        if not match:
            logger.error(f"Could not parse MySQL version: {version_str}")
            return None
            
        major, minor, patch = map(int, match.groups())
        version = MySQLVersion(major, minor, patch)
        
        logger.info(f"Detected MySQL version: {version}")
        return version
        
    except Exception as e:
        logger.error(f"Failed to detect MySQL version: {e}")
        return None


async def get_slow_queries_query(database: str = None) -> str:
    """Get version-compatible slow queries query from Performance Schema.
    
    Args:
        database: Database name to connect to
        
    Returns:
        SQL query string
    """
    version = await get_mysql_version(database)
    
    if not version or not version.has_performance_schema:
        raise Exception("Performance Schema not available")
    
    # Base query for slow queries
    base_query = """
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
    """
    
    return base_query


async def get_table_io_stats_query(database: str = None) -> str:
    """Get version-compatible table I/O statistics query.
    
    Args:
        database: Database name to connect to
        
    Returns:
        SQL query string
    """
    version = await get_mysql_version(database)
    
    if not version or not version.has_performance_schema:
        raise Exception("Performance Schema not available")
    
    # Base query for table I/O stats
    base_query = """
    SELECT 
        object_schema as schema_name,
        object_name as table_name,
        count_read as read_requests,
        count_write as write_requests,
        count_fetch as fetch_requests,
        count_insert as insert_requests,
        count_update as update_requests,
        count_delete as delete_requests,
        sum_timer_read/1000000000000 as read_time_sec,
        sum_timer_write/1000000000000 as write_time_sec,
        sum_timer_fetch/1000000000000 as fetch_time_sec,
        sum_timer_insert/1000000000000 as insert_time_sec,
        sum_timer_update/1000000000000 as update_time_sec,
        sum_timer_delete/1000000000000 as delete_time_sec
    FROM performance_schema.table_io_waits_summary_by_table
    WHERE object_schema != 'performance_schema'
    ORDER BY (sum_timer_read + sum_timer_write + sum_timer_fetch + 
              sum_timer_insert + sum_timer_update + sum_timer_delete) DESC
    """
    
    return base_query


async def get_lock_waits_query(database: str = None) -> str:
    """Get version-compatible lock waits query.
    
    Args:
        database: Database name to connect to
        
    Returns:
        SQL query string
    """
    version = await get_mysql_version(database)
    
    if not version or not version.has_performance_schema:
        raise Exception("Performance Schema not available")
    
    if version.has_data_locks_table:
        # MySQL 8.0+ with data_locks table
        base_query = """
        SELECT 
            dl.object_schema as schema_name,
            dl.object_name as table_name,
            dl.lock_type,
            dl.lock_mode,
            dl.lock_status,
            dl.lock_data,
            p.user,
            p.host,
            p.db,
            p.command,
            p.time,
            p.state,
            SUBSTRING(p.info, 1, 100) as query_snippet
        FROM performance_schema.data_locks dl
        LEFT JOIN information_schema.processlist p ON dl.thread_id = p.id
        WHERE dl.lock_status = 'GRANTED'
        ORDER BY dl.thread_id, dl.object_schema, dl.object_name
        """
    else:
        # MySQL 5.7 with innodb_locks table
        base_query = """
        SELECT 
            'N/A' as schema_name,
            'N/A' as table_name,
            'N/A' as lock_type,
            'N/A' as lock_mode,
            'Legacy MySQL' as lock_status,
            'Use MySQL 8.0+ for detailed lock information' as lock_data,
            'N/A' as user,
            'N/A' as host,
            'N/A' as db,
            'N/A' as command,
            0 as time,
            'N/A' as state,
            'Lock monitoring requires MySQL 8.0+' as query_snippet
        """
    
    return base_query


async def get_innodb_status_query(database: str = None) -> str:
    """Get InnoDB status information query.
    
    Args:
        database: Database name to connect to
        
    Returns:
        SQL query string
    """
    # This is available in all MySQL versions with InnoDB
    return "SHOW ENGINE INNODB STATUS"


async def get_replication_status_query(database: str = None) -> str:
    """Get version-compatible replication status query.
    
    Args:
        database: Database name to connect to
        
    Returns:
        SQL query string
    """
    version = await get_mysql_version(database)
    
    if version and version.has_replica_status:
        # MySQL 8.0.22+ uses REPLICA instead of SLAVE
        return "SHOW REPLICA STATUS"
    else:
        # Older versions use SLAVE
        return "SHOW SLAVE STATUS"
