# Configuration Guide

[Back to README](../README.md)

## MySQL connection

| Variable | Default | Purpose |
| --- | --- | --- |
| `MYSQL_HOST` | `localhost` | MySQL host name or address |
| `MYSQL_PORT` | `3306` | MySQL port |
| `MYSQL_USER` | `root` | MySQL account |
| `MYSQL_PASSWORD` | empty | MySQL password |
| `MYSQL_DATABASE` | `mysql` | Default database |

Use a dedicated, least-privilege account in production. Do not commit real
credentials to `.env`, MCP configuration templates, documentation, or images.

## Transport

The command defaults to stdio. For HTTP:

```bash
uv run mcp-mysql-ops --type streamable-http --host 127.0.0.1 --port 8000
```

Equivalent environment variables are `FASTMCP_TYPE`, `FASTMCP_HOST`, and
`FASTMCP_PORT`. CLI values take precedence.

## HTTP authentication

Set both values before exposing the HTTP server outside an isolated local
environment:

```dotenv
REMOTE_AUTH_ENABLE=true
REMOTE_SECRET_KEY=<RANDOM_SECRET>
```

Clients then send `Authorization: Bearer <RANDOM_SECRET>`. Authentication does
not provide TLS; terminate HTTPS in a trusted reverse proxy for remote access.

## Local Docker files

```bash
cp .env.example .env
cp mcp-config.json.http mcp-config.json.http.local
chmod 600 .env mcp-config.json.http.local
```

Both local files are ignored by Git. If Bearer authentication is enabled, the
token in the local MCPO config must match `REMOTE_SECRET_KEY` in `.env`.
Tracked configuration files contain placeholders only.

The Compose stack binds published ports to `127.0.0.1` by default. Change
`DOCKER_BIND_ADDRESS` only after configuring authentication, TLS, and network
controls appropriate for the deployment.
