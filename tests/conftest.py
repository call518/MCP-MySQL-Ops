"""Shared fixtures for MCP MySQL Ops test suite."""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

DOCKER_COMPOSE_FILE = str(
    Path(__file__).parent / "docker" / "docker-compose.test.yml"
)

# MySQL version configs: (major, minor, port)
MYSQL_VERSIONS = [
    (5, 7, 3357),
    (8, 0, 3380),
    (8, 4, 3384),
]

MYSQL_USER = "root"
MYSQL_PASSWORD = "testpass"
MYSQL_DB = "testdb"
MYSQL_HOST = "127.0.0.1"

WAIT_TIMEOUT_SEC = 180


def _is_mysql_available(port: int) -> bool:
    """TCP-level check: MySQL is listening."""
    try:
        with socket.create_connection((MYSQL_HOST, port), timeout=2):
            return True
    except (ConnectionRefusedError, OSError):
        return False


def _is_mysql_initialized(port: int) -> bool:
    """SQL-level check: init-test-db.sql has finished (customers table exists)."""
    try:
        import pymysql

        conn = pymysql.connect(
            host=MYSQL_HOST,
            port=port,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            connect_timeout=2,
        )
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema=%s AND table_name='customers'",
                (MYSQL_DB,),
            )
            found = cur.fetchone() is not None
        conn.close()
        return found
    except Exception:
        return False


def _all_mysql_initialized() -> bool:
    """Return True if every MySQL instance is already fully initialized."""
    return all(_is_mysql_initialized(port) for *_, port in MYSQL_VERSIONS)


def _wait_for_all_mysql(timeout: int = WAIT_TIMEOUT_SEC) -> None:
    """Poll until every MySQL container is fully initialized (schema + data ready)."""
    deadline = time.monotonic() + timeout
    pending = list(MYSQL_VERSIONS)
    while pending and time.monotonic() < deadline:
        still_pending = []
        for major, minor, port in pending:
            if _is_mysql_initialized(port):
                print(f"  [ready] MySQL {major}.{minor} (port {port})")
            else:
                still_pending.append((major, minor, port))
        pending = still_pending
        if pending:
            time.sleep(3)
    if pending:
        versions = ", ".join(f"MySQL {v[0]}.{v[1]}" for v in pending)
        raise RuntimeError(
            f"Timed out after {timeout}s waiting for: {versions}"
        )


@pytest.fixture(scope="session")
def docker_compose_mysql():
    """Start test MySQL containers and tear them down after the session.

    NOT autouse — only triggered transitively by `mysql_config` / `setup_env`
    fixtures, which integration tests depend on. Unit tests that don't use
    those fixtures run without Docker.

    Automatically detects if containers are already running (e.g. in CI
    or during repeated local runs) and skips Docker lifecycle in that case.
    """
    if _all_mysql_initialized():
        print("\n[conftest] Containers already running — skipping Docker lifecycle.")
        yield
        return

    print("\n[conftest] Starting test MySQL containers (5.7, 8.0, 8.4)...")
    subprocess.run(
        ["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "up", "-d"],
        check=True,
    )
    try:
        print(
            f"[conftest] Waiting for all instances "
            f"(timeout: {WAIT_TIMEOUT_SEC}s)..."
        )
        _wait_for_all_mysql()
        print("[conftest] All MySQL instances ready.\n")
        yield
    finally:
        print("\n[conftest] Tearing down test containers and volumes...")
        subprocess.run(
            ["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "down", "-v"],
            check=False,
        )
        print("[conftest] Cleanup complete.")


def is_mysql_available(port: int) -> bool:
    """Check if a MySQL instance is reachable (for skipping unavailable versions)."""
    return _is_mysql_available(port)


@pytest.fixture(
    params=MYSQL_VERSIONS,
    ids=[f"MySQL{v[0]}.{v[1]}" for v in MYSQL_VERSIONS],
)
def mysql_config(request: pytest.FixtureRequest, docker_compose_mysql):
    """Parametrized fixture providing (major, minor, port) for each MySQL version.

    Depends on `docker_compose_mysql` so that requesting this fixture
    transitively brings up the test container stack.
    """
    major, minor, port = request.param
    if not is_mysql_available(port):
        pytest.skip(f"MySQL {major}.{minor} not available on port {port}")
    return major, minor, port


@pytest.fixture
def setup_env(monkeypatch: pytest.MonkeyPatch, mysql_config):
    """Set environment variables so MCP tools connect to the right MySQL instance."""
    major, minor, port = mysql_config

    monkeypatch.setenv("MYSQL_HOST", MYSQL_HOST)
    monkeypatch.setenv("MYSQL_PORT", str(port))
    monkeypatch.setenv("MYSQL_USER", MYSQL_USER)
    monkeypatch.setenv("MYSQL_PASSWORD", MYSQL_PASSWORD)
    monkeypatch.setenv("MYSQL_DATABASE", MYSQL_DB)

    # Refresh module-level cached config so the new env vars take effect
    import mcp_mysql_ops.functions as fn

    fn.refresh_configs()
    monkeypatch.setattr(
        fn,
        "MYSQL_CONFIG",
        {
            "host": MYSQL_HOST,
            "port": port,
            "user": MYSQL_USER,
            "password": MYSQL_PASSWORD,
            "db": MYSQL_DB,
            "charset": "utf8mb4",
            "autocommit": True,
        },
    )

    yield major, minor, port
