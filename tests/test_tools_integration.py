"""Integration tests: call every MCP tool against each MySQL version.

Requires Docker Compose test stack running (tests/docker/docker-compose.test.yml).
The session-scoped fixture in conftest.py manages the container lifecycle.
"""
import pytest

import mcp_mysql_ops.mcp_main as _mcp_main


def _fn(name: str):
    """Extract the raw callable from a FunctionTool (fastmcp >= 2.14) or return as-is."""
    tool = getattr(_mcp_main, name)
    return getattr(tool, "fn", tool)


# All @mcp.tool()-decorated functions in mcp_main.py
get_server_info = _fn("get_server_info")
get_active_connections = _fn("get_active_connections")
get_database_list = _fn("get_database_list")
get_table_list = _fn("get_table_list")
get_table_schema_info = _fn("get_table_schema_info")
get_mysql_config = _fn("get_mysql_config")
get_user_list = _fn("get_user_list")
get_server_status = _fn("get_server_status")
get_table_size_info = _fn("get_table_size_info")
get_database_size_info = _fn("get_database_size_info")
get_index_usage_stats = _fn("get_index_usage_stats")
get_connection_info = _fn("get_connection_info")
get_slow_queries = _fn("get_slow_queries")
get_table_io_stats = _fn("get_table_io_stats")
get_lock_monitoring = _fn("get_lock_monitoring")
get_current_database_info = _fn("get_current_database_info")


pytestmark = pytest.mark.asyncio


def assert_tool_result(result, tool_name):
    """Common assertions for all tool results."""
    assert isinstance(result, str), f"{tool_name} did not return a string"
    assert len(result) > 0, f"{tool_name} returned empty string"
    # Should not contain Python tracebacks
    assert "Traceback" not in result, (
        f"{tool_name} returned a traceback: {result[:500]}"
    )


# ============================================================================
# Core tools — should work on all supported MySQL versions (5.7, 8.0, 8.4)
# ============================================================================


class TestCoreTools:
    """Tools that are version-independent (or degrade gracefully)."""

    async def test_get_server_info(self, setup_env):
        major, minor, _ = setup_env
        result = await get_server_info()
        assert_tool_result(result, "get_server_info")
        # Should mention the major version somewhere in the version line
        assert f"{major}." in result, (
            f"get_server_info should mention MySQL {major}.{minor}"
        )

    async def test_get_active_connections(self, setup_env):
        result = await get_active_connections()
        assert_tool_result(result, "get_active_connections")

    async def test_get_active_connections_with_user_filter(self, setup_env):
        result = await get_active_connections(user_filter="root")
        assert_tool_result(result, "get_active_connections(user_filter)")

    async def test_get_database_list(self, setup_env):
        result = await get_database_list()
        assert_tool_result(result, "get_database_list")
        assert "testdb" in result

    async def test_get_table_list(self, setup_env):
        result = await get_table_list(database_name="testdb")
        assert_tool_result(result, "get_table_list")
        assert "customers" in result.lower() or "orders" in result.lower()

    async def test_get_table_schema_info(self, setup_env):
        major, minor, _ = setup_env
        if (major, minor) == (5, 7):
            pytest.xfail(
                "Known bug in mcp_main.get_table_schema_info: SQL queries "
                "select lowercase information_schema columns but the result "
                "dict is read with uppercase keys (e.g. col['COLUMN_NAME']). "
                "MySQL 5.7 returns lowercase keys; 8.0+ returns uppercase. "
                "Fix: use lowercase keys in code, or alias columns to "
                "uppercase in the SQL."
            )
        result = await get_table_schema_info(
            table_name="customers", database_name="testdb"
        )
        assert_tool_result(result, "get_table_schema_info")
        assert "customer" in result.lower() or "email" in result.lower()

    async def test_get_table_schema_info_unknown_table(self, setup_env):
        # Should not throw — should return a "not found" message
        result = await get_table_schema_info(
            table_name="no_such_table_xyz", database_name="testdb"
        )
        assert_tool_result(result, "get_table_schema_info(unknown)")
        assert "not found" in result.lower()

    async def test_get_mysql_config(self, setup_env):
        result = await get_mysql_config()
        assert_tool_result(result, "get_mysql_config")

    async def test_get_mysql_config_filtered(self, setup_env):
        result = await get_mysql_config(search_term="performance_schema")
        assert_tool_result(result, "get_mysql_config(filtered)")
        assert "performance_schema" in result.lower()

    async def test_get_user_list(self, setup_env):
        result = await get_user_list()
        assert_tool_result(result, "get_user_list")
        assert "root" in result.lower()

    async def test_get_server_status(self, setup_env):
        result = await get_server_status()
        assert_tool_result(result, "get_server_status")

    async def test_get_server_status_filtered(self, setup_env):
        result = await get_server_status(search_term="Uptime")
        assert_tool_result(result, "get_server_status(filtered)")

    async def test_get_table_size_info(self, setup_env):
        result = await get_table_size_info(database_name="testdb")
        assert_tool_result(result, "get_table_size_info")

    async def test_get_database_size_info(self, setup_env):
        result = await get_database_size_info()
        assert_tool_result(result, "get_database_size_info")
        assert "testdb" in result

    async def test_get_index_usage_stats(self, setup_env):
        result = await get_index_usage_stats(database_name="testdb")
        assert_tool_result(result, "get_index_usage_stats")

    async def test_get_connection_info(self, setup_env):
        result = await get_connection_info()
        assert_tool_result(result, "get_connection_info")

    async def test_get_slow_queries(self, setup_env):
        # Performance Schema is enabled in all test containers — should return data
        result = await get_slow_queries(limit=5)
        assert_tool_result(result, "get_slow_queries")

    async def test_get_table_io_stats(self, setup_env):
        result = await get_table_io_stats(limit=5)
        assert_tool_result(result, "get_table_io_stats")

    async def test_get_current_database_info(self, setup_env):
        result = await get_current_database_info(database_name="testdb")
        assert_tool_result(result, "get_current_database_info")
        assert "testdb" in result


# ============================================================================
# Version-gated tools — verify behavior across the 5.7 / 8.0+ split
# ============================================================================


class TestVersionGatedTools:
    """Tools whose SQL/output depends on MySQL version."""

    async def test_get_lock_monitoring(self, setup_env):
        """8.0+ uses performance_schema.data_locks; 5.7 returns legacy notice."""
        major, _, _ = setup_env
        result = await get_lock_monitoring()
        assert_tool_result(result, "get_lock_monitoring")
        if major < 8:
            # Pre-8.0 returns a stub indicating MySQL 8.0+ is required
            assert "8.0" in result or "Legacy" in result or "no active" in result.lower()


# ============================================================================
# Version-specific feature verification
# ============================================================================


class TestVersionSpecificFeatures:
    """Verify version-specific output content."""

    async def test_server_info_reports_correct_version(self, setup_env):
        """get_server_info output should contain the MySQL version string."""
        major, minor, _ = setup_env
        result = await get_server_info()
        assert f"{major}.{minor}" in result, (
            f"Expected version {major}.{minor} in get_server_info output"
        )

    async def test_database_list_excludes_system_dbs(self, setup_env):
        """User-facing database list should not show information_schema etc."""
        result = await get_database_list()
        # The query in mcp_main.py excludes these — verify behavior holds
        assert "information_schema" not in result
        assert "performance_schema" not in result
        assert "mysql\n" not in result and "mysql " not in result.split("===")[-1]
