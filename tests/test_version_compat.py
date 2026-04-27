"""Unit tests for version_compat.py — no database required."""
from unittest.mock import AsyncMock, patch

import pytest

from mcp_mysql_ops.version_compat import (
    MySQLVersion,
    get_lock_waits_query,
    get_replication_status_query,
    get_slow_queries_query,
    get_table_io_stats_query,
    get_innodb_status_query,
)


async def _mock_version_call(func, version: MySQLVersion, *args, **kwargs):
    """Call an async query builder with get_mysql_version mocked."""
    with patch(
        "mcp_mysql_ops.version_compat.get_mysql_version",
        new_callable=AsyncMock,
        return_value=version,
    ):
        return await func(*args, **kwargs)


# ============================================================================
# Version property tests
# ============================================================================


class TestMySQLVersionProperties:
    """Test every version property returns correct values for MySQL 5.5–8.4."""

    @pytest.mark.parametrize(
        "major,expected",
        [(5, False), (8, True)],
    )
    def test_is_modern(self, major, expected):
        assert MySQLVersion(major, 0, 0).is_modern is expected

    @pytest.mark.parametrize(
        "major,minor,expected",
        [
            (5, 4, False),
            (5, 5, True),
            (5, 6, True),
            (5, 7, True),
            (8, 0, True),
            (8, 4, True),
        ],
    )
    def test_has_performance_schema(self, major, minor, expected):
        assert MySQLVersion(major, minor, 0).has_performance_schema is expected

    @pytest.mark.parametrize(
        "major,minor,expected",
        [
            (5, 6, False),
            (5, 7, True),
            (8, 0, True),
            (8, 4, True),
        ],
    )
    def test_has_sys_schema(self, major, minor, expected):
        assert MySQLVersion(major, minor, 0).has_sys_schema is expected

    @pytest.mark.parametrize(
        "major,minor,expected",
        [
            (5, 5, True),
            (5, 6, True),
            (5, 7, True),
            (8, 0, True),
        ],
    )
    def test_has_information_schema_innodb_tables(self, major, minor, expected):
        v = MySQLVersion(major, minor, 0)
        assert v.has_information_schema_innodb_tables is expected

    @pytest.mark.parametrize(
        "major,expected",
        [(5, False), (8, True)],
    )
    def test_has_data_locks_table(self, major, expected):
        """data_locks is the MySQL 8.0+ replacement for legacy innodb_locks."""
        assert MySQLVersion(major, 0, 0).has_data_locks_table is expected

    @pytest.mark.parametrize(
        "major,minor,patch,expected",
        [
            (5, 7, 30, False),
            (8, 0, 21, False),
            (8, 0, 22, True),
            (8, 0, 35, True),
            pytest.param(
                8, 4, 0, True,
                marks=pytest.mark.xfail(
                    reason=(
                        "Known bug in version_compat.has_replica_status: "
                        "the check `minor >= 0 AND patch >= 22` ignores the "
                        "minor>0 case. MySQL 8.4.0 should be supported but "
                        "currently returns False. Fix: use tuple comparison "
                        "`(major, minor, patch) >= (8, 0, 22)`."
                    ),
                    strict=True,
                ),
            ),
        ],
    )
    def test_has_replica_status(self, major, minor, patch, expected):
        """SHOW REPLICA STATUS introduced in MySQL 8.0.22."""
        assert MySQLVersion(major, minor, patch).has_replica_status is expected

    @pytest.mark.parametrize(
        "major,minor,expected",
        [
            (5, 5, False),
            (5, 6, True),
            (5, 7, True),
            (8, 0, True),
        ],
    )
    def test_has_innodb_metrics(self, major, minor, expected):
        assert MySQLVersion(major, minor, 0).has_innodb_metrics is expected


# ============================================================================
# Version comparison tests
# ============================================================================


class TestVersionComparison:
    """Test version comparison operators on MySQLVersion."""

    def test_ge_same(self):
        assert MySQLVersion(8, 0, 0) >= MySQLVersion(8, 0, 0)

    def test_ge_higher_major(self):
        assert MySQLVersion(8, 0, 0) >= MySQLVersion(5, 7, 0)

    def test_ge_lower_major(self):
        assert not (MySQLVersion(5, 7, 0) >= MySQLVersion(8, 0, 0))

    def test_ge_same_major_higher_minor(self):
        assert MySQLVersion(5, 7, 0) >= MySQLVersion(5, 6, 0)

    def test_lt(self):
        assert MySQLVersion(5, 7, 0) < MySQLVersion(8, 0, 0)

    def test_not_lt_same(self):
        assert not (MySQLVersion(8, 0, 0) < MySQLVersion(8, 0, 0))

    def test_str_format(self):
        assert str(MySQLVersion(8, 0, 35)) == "8.0.35"

    def test_int_comparison_ge(self):
        v = MySQLVersion(8, 0, 0)
        assert v >= 5
        assert v >= 8
        assert not (v >= 9)

    def test_int_comparison_lt(self):
        assert MySQLVersion(5, 7, 0) < 8
        assert not (MySQLVersion(8, 0, 0) < 8)


# ============================================================================
# SQL generation tests — verify the right query is built per version
# ============================================================================


class TestLockWaitsQuery:
    """get_lock_waits_query branches on data_locks availability (MySQL 8.0+)."""

    async def test_mysql80_uses_data_locks(self):
        v = MySQLVersion(8, 0, 35)
        query = await _mock_version_call(get_lock_waits_query, v)
        assert "performance_schema.data_locks" in query
        assert "lock_status = 'GRANTED'" in query

    async def test_mysql84_uses_data_locks(self):
        v = MySQLVersion(8, 4, 0)
        query = await _mock_version_call(get_lock_waits_query, v)
        assert "performance_schema.data_locks" in query

    async def test_mysql57_falls_back_to_legacy_message(self):
        v = MySQLVersion(5, 7, 30)
        query = await _mock_version_call(get_lock_waits_query, v)
        # Pre-8.0 path: returns a stub SELECT noting MySQL 8.0+ is required
        assert "performance_schema.data_locks" not in query
        assert "Legacy MySQL" in query or "8.0" in query

    async def test_no_perf_schema_raises(self):
        v = MySQLVersion(5, 4, 0)  # no performance_schema (< 5.5)
        with pytest.raises(Exception, match="Performance Schema"):
            await _mock_version_call(get_lock_waits_query, v)


class TestReplicationStatusQuery:
    """get_replication_status_query branches on REPLICA STATUS (MySQL 8.0.22+)."""

    async def test_mysql80_22_uses_replica(self):
        v = MySQLVersion(8, 0, 22)
        query = await _mock_version_call(get_replication_status_query, v)
        assert query == "SHOW REPLICA STATUS"

    async def test_mysql80_35_uses_replica(self):
        v = MySQLVersion(8, 0, 35)
        query = await _mock_version_call(get_replication_status_query, v)
        assert query == "SHOW REPLICA STATUS"

    @pytest.mark.xfail(
        reason=(
            "Same has_replica_status bug — MySQL 8.4.0 currently routes to "
            "legacy SHOW SLAVE STATUS. Will pass after the version_compat "
            "tuple-comparison fix."
        ),
        strict=True,
    )
    async def test_mysql84_uses_replica(self):
        v = MySQLVersion(8, 4, 0)
        query = await _mock_version_call(get_replication_status_query, v)
        assert query == "SHOW REPLICA STATUS"

    async def test_mysql80_21_uses_legacy_slave(self):
        v = MySQLVersion(8, 0, 21)
        query = await _mock_version_call(get_replication_status_query, v)
        assert query == "SHOW SLAVE STATUS"

    async def test_mysql57_uses_legacy_slave(self):
        v = MySQLVersion(5, 7, 30)
        query = await _mock_version_call(get_replication_status_query, v)
        assert query == "SHOW SLAVE STATUS"


class TestSlowQueriesQuery:
    """get_slow_queries_query requires Performance Schema."""

    @pytest.mark.parametrize(
        "major,minor",
        [(5, 7), (8, 0), (8, 4)],
    )
    async def test_returns_digest_query(self, major, minor):
        v = MySQLVersion(major, minor, 0)
        query = await _mock_version_call(get_slow_queries_query, v)
        assert "events_statements_summary_by_digest" in query
        assert "digest_text" in query

    async def test_no_perf_schema_raises(self):
        v = MySQLVersion(5, 4, 0)
        with pytest.raises(Exception, match="Performance Schema"):
            await _mock_version_call(get_slow_queries_query, v)


class TestTableIoStatsQuery:
    """get_table_io_stats_query requires Performance Schema."""

    @pytest.mark.parametrize(
        "major,minor",
        [(5, 7), (8, 0), (8, 4)],
    )
    async def test_returns_table_io_query(self, major, minor):
        v = MySQLVersion(major, minor, 0)
        query = await _mock_version_call(get_table_io_stats_query, v)
        assert "table_io_waits_summary_by_table" in query

    async def test_no_perf_schema_raises(self):
        v = MySQLVersion(5, 4, 0)
        with pytest.raises(Exception, match="Performance Schema"):
            await _mock_version_call(get_table_io_stats_query, v)


class TestInnodbStatusQuery:
    """get_innodb_status_query is version-independent."""

    async def test_returns_show_engine(self):
        # No mocking needed — this function doesn't query the version
        result = await get_innodb_status_query()
        assert result == "SHOW ENGINE INNODB STATUS"
