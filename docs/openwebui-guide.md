# OpenWebUI with Docker Compose

[Back to README](../README.md)

## Components and connection paths

OpenWebUI `v0.13.3` can connect directly to the MCP server. MCPO is an optional
OpenAPI compatibility layer.

| | Direct MCP | Through MCPO |
| --- | --- | --- |
| OpenWebUI connection type | `MCP (Streamable HTTP)` | `OpenAPI` |
| Container URL | `http://mcp-server:8000/mcp` | `http://mcpo-proxy:8000/mcp-mysql-ops` |
| Host URL | `http://localhost:18004/mcp` | `http://localhost:8004/mcp-mysql-ops` |
| REST documentation | None | `http://localhost:8004/mcp-mysql-ops/docs` |
| Use when | Native MCP is available | A client requires OpenAPI |

The MCPO image pins `mcpo==0.0.20`, `mcp==1.30.0`, and
`fastapi==0.128.0`. MCPO 0.0.20 imports the MCP 1.x streamable HTTP client and
does not work with MCP 2.x; this proxy dependency set is intentionally separate
from the MCP server's locked project dependencies.

## Prerequisites and defaults

- Git and Docker with the Compose plugin
- A model provider whose model supports tool calling
- `127.0.0.1` host bindings unless `DOCKER_BIND_ADDRESS` is explicitly changed
- The included MySQL service for tutorial data, or a reachable external MySQL
  server when using `docker-compose.custom-db.yml`

## 1. Configure

```bash
cp .env.example .env
cp mcp-config.json.http mcp-config.json.http.local
chmod 600 .env mcp-config.json.http.local
openssl rand -hex 32   # use the output as WEBUI_SECRET_KEY
vi .env
vi mcp-config.json.http.local
```

Set the MySQL connection and `WEBUI_SECRET_KEY` in `.env`. When
`REMOTE_AUTH_ENABLE=true`, set a strong `REMOTE_SECRET_KEY` and replace
`<REMOTE_SECRET_KEY>` in the ignored local MCPO file with the same value.
Never put the real token in the tracked template.

## 2. Start the stack

```bash
docker compose up -d
docker compose ps
```

The default Compose stack retains its test MySQL and initialization services.
Use the custom stack below for an existing MySQL server.

<a id="use-an-existing-mysql-server"></a>

### Use an existing MySQL server

Set `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, and
`MYSQL_DATABASE` in `.env`, then start the custom database stack:

```bash
docker compose -f docker-compose.custom-db.yml up -d
docker compose -f docker-compose.custom-db.yml ps
```

The custom stack starts only OpenWebUI, the MCP server, and MCPO; it does not
create or modify a MySQL server.

| Service | Host URL | Container URL |
| --- | --- | --- |
| OpenWebUI | `http://localhost:3004` | `http://open-webui:8080` |
| MCP | `http://localhost:18004/mcp` | `http://mcp-server:8000/mcp` |
| MCPO | `http://localhost:8004/mcp-mysql-ops` | `http://mcpo-proxy:8000/mcp-mysql-ops` |

## 3. Configure OpenWebUI 0.13

First configure a model provider under **Settings → Admin → Connections**.

### 3.1 Direct MCP connection

Under **Settings → Admin → Tools → Integrations → External Tool Servers**, add:

| Field | Value |
| --- | --- |
| Type | `MCP (Streamable HTTP)` |
| URL | `http://mcp-server:8000/mcp` |
| Authentication | `None`, or Bearer with `REMOTE_SECRET_KEY` when enabled |

This is the preferred path because it has fewer components.

### 3.2 Optional MCPO connection

MCPO exposes the MCP tools as OpenAPI. It is unnecessary for direct MCP
support, but remains in the standard stack for OpenAPI clients. Its container
mounts the ignored file selected by `MCPO_CONFIG_FILE` read-only.

| Field | Value |
| --- | --- |
| Type | `OpenAPI` |
| URL | `http://mcpo-proxy:8000/mcp-mysql-ops` |

### 3.3 Tool Search

Under **Settings → Admin → System → Interface → Chat**, enable **Tool Search**
and **Defer Built-in Tools**, then set **Deferral Threshold** to `0`. Enable the
connection under **Integrations → Tools** in each new chat.

To omit MCPO:

```bash
docker compose up -d mysql mysql-init-data mcp-server open-webui
```

### 3.4 Reasoning model compatibility

`.env.example` seeds this global value on the first OpenWebUI startup:

```dotenv
DEFAULT_MODEL_PARAMS={"reasoning_effort":"none"}
```

Some OpenAI reasoning models reject function tools through Chat Completions
when reasoning effort is enabled. If the `open-webui-data` volume already
exists, change the model defaults in the Admin UI; editing `.env` alone may not
replace the saved database value. Per-model and per-chat settings can override
the global default. Providers that reject this parameter should remove the
global value and configure only the affected model.

To use reasoning through the Responses API, set `DEFAULT_MODEL_PARAMS={}`
before the first startup and leave **Reasoning Effort** at **Default**. Existing
volumes require the equivalent change in the Admin UI.

Do not delete an existing OpenWebUI volume as a troubleshooting shortcut.

## 4. Verify

Ask `Use mcp-mysql-ops to show the MySQL server version and uptime.` For the
MCPO path, also open `http://localhost:8004/mcp-mysql-ops/docs` and confirm the
generated operations are present.

## Troubleshooting

- `401 Unauthorized`: check `REMOTE_AUTH_ENABLE`, the server secret, the local
  MCPO Authorization header, placeholders, and container recreation.
- Direct MCP works but MCPO fails: inspect the MCPO local config independently;
  the two paths have separate client settings.
- MCPO reports an expired or unknown MCP session after the server restarts:
  run `docker compose restart mcpo-proxy` after `mcp-server` is healthy. To
  recreate both safely, use
  `docker compose up -d --force-recreate mcp-server mcpo-proxy`.
- A container cannot connect to `localhost`: use the container URLs in the
  table above; `localhost` inside a container is that same container.
- MySQL connection fails: verify whether `MYSQL_HOST` is resolvable from the
  MCP container, not only from the host.
