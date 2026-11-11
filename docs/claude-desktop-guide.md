# Claude Desktop Guide

[Back to README](../README.md)

## MCPB installation

Requirements: Claude Desktop, network access from the desktop to the target
MySQL server, and a MySQL account with only the permissions needed for the
monitoring data you intend to expose.

1. Download `mcp-mysql-ops-<version>.mcpb` from the latest
   [GitHub Release](https://github.com/call518/MCP-MySQL-Ops/releases).
2. Open **Settings → Extensions → Advanced settings → Install Extension…**.
3. Select the bundle.
4. Enter `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, and
   `MYSQL_DATABASE`. Claude Desktop stores the password as a sensitive value.
5. Ask `Show the MySQL server version and uptime.`

The bundle runs the server locally over stdio with `uv` and Python 3.12. HTTP
transport, Bearer authentication, OpenWebUI, and MCPO settings do not apply to
this path.

## Configuration file for the other local options

Open Claude Desktop **Settings → Developer → Edit Config**, or edit the file:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

Merge an entry into the existing `mcpServers` object, then quit and restart
Claude Desktop. This file stores credentials in plain text; keep it private and
never commit it.

## Install from PyPI with uvx

Requirements: [uv](https://docs.astral.sh/uv/) and network access for the first
download. Prepare the cached environment once:

```bash
uvx --python 3.12 mcp-mysql-ops --help
```

Add this server to the Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "mcp-mysql-ops": {
      "command": "uvx",
      "args": ["--python", "3.12", "mcp-mysql-ops", "--type", "stdio"],
      "env": {
        "MYSQL_HOST": "127.0.0.1",
        "MYSQL_PORT": "3306",
        "MYSQL_USER": "monitoring_user",
        "MYSQL_PASSWORD": "<MYSQL_PASSWORD>",
        "MYSQL_DATABASE": "mysql"
      }
    }
  }
}
```

Restart Claude Desktop after changing its configuration.

## Source checkout with uv

Use this for unreleased changes. Replace `/path/to/MCP-MySQL-Ops` with the
absolute path to the clone. On Windows, clone on Windows rather than inside WSL
and escape backslashes in JSON.

```bash
git clone https://github.com/call518/MCP-MySQL-Ops.git /path/to/MCP-MySQL-Ops
uv --directory /path/to/MCP-MySQL-Ops sync
```

```json
{
  "mcpServers": {
    "mcp-mysql-ops-source": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/MCP-MySQL-Ops",
        "run",
        "mcp-mysql-ops",
        "--type",
        "stdio"
      ],
      "env": {
        "MYSQL_HOST": "127.0.0.1",
        "MYSQL_PORT": "3306",
        "MYSQL_USER": "monitoring_user",
        "MYSQL_PASSWORD": "<MYSQL_PASSWORD>",
        "MYSQL_DATABASE": "mysql"
      }
    }
  }
}
```

Restart Claude Desktop after `git pull` to load updated source.

## Existing Docker HTTP server with npx

Claude Desktop local configuration starts stdio commands; it does not accept an
HTTP URL directly. To use the Compose `mcp-server`, install Node.js 18 or later
and use the pinned third-party `mcp-remote` bridge. Use the MCP `/mcp` URL, not
the MCPO OpenAPI URL.

With `REMOTE_AUTH_ENABLE=false`:

```json
{
  "mcpServers": {
    "mcp-mysql-ops-docker": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@0.15.2",
        "http://127.0.0.1:18004/mcp",
        "--transport",
        "http-only"
      ]
    }
  }
}
```

When authentication is enabled, use:

```json
{
  "mcpServers": {
    "mcp-mysql-ops-docker": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@0.15.2",
        "http://127.0.0.1:18004/mcp",
        "--transport",
        "http-only",
        "--header",
        "Authorization:${REMOTE_SECRET_KEY}"
      ],
      "env": {
        "REMOTE_SECRET_KEY": "Bearer <REMOTE_SECRET_KEY>"
      }
    }
  }
}
```

The `Bearer ` prefix is required. Use plain HTTP only on loopback; use HTTPS for
another host.

## Remote custom connector

This is configured under Claude **Customize → Connectors → Add custom
connector**, not in `claude_desktop_config.json`. Anthropic's cloud must be able
to reach the server through a public HTTPS URL; localhost, private networks, and
VPN-only addresses are not reachable.

This server does not implement OAuth. With `REMOTE_AUTH_ENABLE=true`, choose
**No sign-in** and, if the organization supports custom request headers, add
`authorization: Bearer <REMOTE_SECRET_KEY>`. Anyone holding that token can use
the configured MySQL account, so use a least-privilege database user and never
expose an unauthenticated server.

## Troubleshooting

- Connection refused: verify host, port, firewall, and MySQL bind address from
  the desktop computer.
- Access denied: verify the account and grant only the required read access.
- Missing Performance Schema results: enable Performance Schema and grant the
  account access to the relevant metadata.
- Bundle installation failure: use a release asset ending in `.mcpb`, not a
  source archive.
