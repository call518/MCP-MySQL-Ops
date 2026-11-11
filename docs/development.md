# Development and Release Guide

[Back to README](../README.md)

## Local checks

```bash
uv sync --extra dev
uv run pytest -q
bash -n scripts/*.sh
python -m json.tool mcpb/manifest.json
python -m json.tool mcp-config.json.http
```

Integration tests start dedicated MySQL 5.7, 8.0, and 8.4 containers. Docker
must be available to run them.

## Build an MCPB locally

```bash
scripts/build-mcpb.sh 0.0.0 /tmp/mcp-mysql-ops-mcpb-check
unzip -l /tmp/mcp-mysql-ops-mcpb-check/mcp-mysql-ops-0.0.0.mcpb
```

The script uses an allowlist: the entry point, package metadata, lockfile,
README, license, and `src/mcp_mysql_ops` package. It does not pack `.env`,
local MCP configuration, tests, caches, or Git metadata.

The manifest selects Python 3.12 explicitly. Allowing `uv` to select Python
3.15 currently fails because a locked PyO3 dependency supports up to Python
3.14.

## Build the Docker images

```bash
docker build -f Dockerfile.MCP-Server -t mcp-mysql-ops-server:check .
docker build -f Dockerfile.MCPO-Proxy -t mcp-mysql-ops-mcpo:check .
```

The MCP Server image exports its dependency set from `uv.lock` with
`uv==0.7.20`; project source is mounted by Compose. The MCPO image is a separate
compatibility proxy pinned to `mcpo==0.0.20`, `mcp==1.30.0`, and
`fastapi==0.128.0` and does not install this project's runtime dependencies.

## Release flow

A canonical tag such as `v1.0.1` triggers:

1. release automation tests;
2. wheel and source distribution build and version verification;
3. MCPB validation and packaging;
4. TestPyPI and PyPI trusted publication;
5. GitHub Release creation with the MCPB attached.

The release job rejects missing assets, moved tags, duplicate releases, and
distribution versions that do not match the tag. Prerelease tags such as
`v1.1.0rc1` create prerelease GitHub Releases.

Creating a tag or release is a separate, explicitly approved Git operation;
the build commands above do not perform one.
