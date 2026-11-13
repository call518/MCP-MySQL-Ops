"""Check the Claude Desktop bundle manifest against server settings."""

import json
import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "mcpb" / "manifest.json").read_text())
PROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text())
ENV = MANIFEST["server"]["mcp_config"]["env"]
CONFIG = MANIFEST["user_config"]


def test_every_user_config_value_is_passed_and_defined():
    used = {
        match
        for value in ENV.values()
        for match in re.findall(r"\$\{user_config\.(\w+)\}", value)
    }
    assert used == set(CONFIG)


def test_password_is_sensitive_and_defaults_are_usable():
    assert CONFIG["mysql_password"]["sensitive"] is True
    for name, item in CONFIG.items():
        if name != "mysql_password":
            assert item["required"] or item.get("default"), name


def test_titles_name_the_environment_variable_they_set():
    for name, value in ENV.items():
        match = re.fullmatch(r"\$\{user_config\.(\w+)\}", value)
        if match:
            assert f"({name})" in CONFIG[match[1]]["title"]


def test_bundle_runs_the_stdio_entry_point_with_uv():
    server = MANIFEST["server"]
    assert server["type"] == "uv"
    assert server["entry_point"] == "server.py"
    assert (ROOT / "mcpb" / "server.py").is_file()
    assert server["mcp_config"]["args"][1:3] == ["--python", "3.12"]
    assert server["mcp_config"]["args"][-1] == "server.py"


def test_bundle_install_and_runtime_use_python_312():
    python_requirement = ">=3.12,<3.13"
    assert PROJECT["project"]["requires-python"] == python_requirement
    assert MANIFEST["compatibility"]["runtimes"]["python"] == python_requirement


def test_bundle_icon_is_packed_from_the_repository_image():
    assert MANIFEST["icon"] == "icon.png"
    assert (ROOT / "img" / "icon-mysql.png").is_file()
    build = (ROOT / "scripts" / "build-mcpb.sh").read_text()
    assert '"$ROOT/img/icon-mysql.png" "$STAGE/icon.png"' in build
