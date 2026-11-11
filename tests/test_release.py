"""Check that tag publication rejects incorrect distributions."""

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.check_release import check_release


def write_distributions(
    directory: Path, version: str, name: str = "mcp-mysql-ops"
) -> None:
    metadata = f"Name: {name}\nVersion: {version}\n".encode()
    with zipfile.ZipFile(directory / "package.whl", "w") as archive:
        archive.writestr("mcp_mysql_ops.dist-info/METADATA", metadata)
    with tarfile.open(directory / "package.tar.gz", "w:gz") as archive:
        member = tarfile.TarInfo("mcp_mysql_ops/PKG-INFO")
        member.size = len(metadata)
        archive.addfile(member, io.BytesIO(metadata))


@pytest.mark.parametrize("tag", ["1.0.1", "v1.0.1", "1.0.1rc1", "v1.0.1a1"])
def test_matching_release(tag: str, tmp_path: Path) -> None:
    write_distributions(tmp_path, tag.removeprefix("v"))
    check_release(tag, tmp_path)


@pytest.mark.parametrize("tag", ["latest", "1.0", "1.0.1+dirty", "01.0.1", "1.0.1-rc1"])
def test_invalid_release_tag(tag: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Use a tag"):
        check_release(tag, tmp_path)


@pytest.mark.parametrize(
    "version,name", [("1.0.2", "mcp-mysql-ops"), ("1.0.1", "other")]
)
def test_wrong_distribution(version: str, name: str, tmp_path: Path) -> None:
    write_distributions(tmp_path, version, name)
    with pytest.raises(ValueError, match="expected mcp-mysql-ops 1.0.1"):
        check_release("1.0.1", tmp_path)


def test_sdist_version_must_also_match(tmp_path: Path) -> None:
    write_distributions(tmp_path, "1.0.2")
    with zipfile.ZipFile(tmp_path / "package.whl", "w") as archive:
        archive.writestr(
            "mcp_mysql_ops.dist-info/METADATA",
            "Name: mcp-mysql-ops\nVersion: 1.0.1\n",
        )
    with pytest.raises(ValueError, match="package.tar.gz"):
        check_release("1.0.1", tmp_path)


def test_incomplete_distributions(tmp_path: Path) -> None:
    write_distributions(tmp_path, "1.0.1")
    (tmp_path / "package.tar.gz").unlink()
    with pytest.raises(ValueError, match="exactly one"):
        check_release("1.0.1", tmp_path)
