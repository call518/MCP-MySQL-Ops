# AGENTS.md

## Maintain the MCP server instructions

`src/mcp_mysql_ops/server_instructions.md` is sent to every client in the
MCP initialize response and enters the model's context as-is.

- Keep only rules that span several tools, such as read-only scope, database
  scope, privileges, result reporting, missing input, the meaning of numbers,
  and top-N limits. Put tool-specific behavior in the tool's docstring and
  parameter descriptions.
- Keep it at 4,096 characters or fewer; `tests/test_server_instructions.py`
  checks the limit. Write short imperative English.
- Every tool name, parameter, and environment variable it mentions must match
  the registered tools and settings. When a change renames or removes them, or
  changes a cross-tool rule, update this file in the same change set.
- Never include credentials, private endpoints, or environment-specific data.
- After changing it, run the unit tests, including
  `tests/test_server_instructions.py`.
