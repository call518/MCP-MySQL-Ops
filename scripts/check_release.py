"""Require distribution metadata versions to match the release tag."""

import argparse
import re
import tarfile
import zipfile
from email.parser import BytesParser
from pathlib import Path


def release_version(tag: str) -> str:
    """Validate a canonical release tag and return its package version."""
    version = tag.removeprefix("v")
    number = r"(?:0|[1-9][0-9]*)"
    if not re.fullmatch(
        rf"{number}\.{number}\.{number}(?:(?:a|b|rc){number})?", version
    ):
        raise ValueError("Use a tag such as 1.0.1, v1.0.1, or 1.0.1rc1")
    return version


def check_release(tag: str, directory: Path) -> None:
    """Validate the tag and the wheel/sdist prepared for upload."""
    version = release_version(tag)
    wheels = list(directory.glob("*.whl"))
    sdists = list(directory.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("Expected exactly one wheel and one source distribution")

    with zipfile.ZipFile(wheels[0]) as archive:
        names = [
            name
            for name in archive.namelist()
            if name.endswith(".dist-info/METADATA")
        ]
        if len(names) != 1:
            raise ValueError("Expected one wheel metadata file")
        wheel_metadata = archive.read(names[0])
    with tarfile.open(sdists[0], "r:gz") as archive:
        members = [
            item for item in archive.getmembers()
            if len(Path(item.name).parts) == 2 and item.name.endswith("/PKG-INFO")
        ]
        if len(members) != 1:
            raise ValueError("Expected one source distribution metadata file")
        stream = archive.extractfile(members[0])
        if stream is None:
            raise ValueError("Source distribution metadata is not a file")
        with stream:
            sdist_metadata = stream.read()

    for path, raw in zip((wheels[0], sdists[0]), (wheel_metadata, sdist_metadata)):
        metadata = BytesParser().parsebytes(raw)
        if (
            metadata.get("Name") != "mcp-mysql-ops"
            or metadata.get("Version") != version
        ):
            raise ValueError(f"{path.name}: expected mcp-mysql-ops {version}")
        print(f"Verified {path.name}: mcp-mysql-ops {version}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        check_release(args.tag, args.directory)
    except ValueError as exc:
        parser.exit(1, f"Release validation failed: {exc}\n")


if __name__ == "__main__":
    main()
