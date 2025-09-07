#!/bin/bash
set -eo pipefail

# 어디서 실행하든지, 스크립트 위치의 상위 경로에 있는 .env 파일 export 로드
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
env_file="${script_dir%/*}/.env"
if [[ -f "$env_file" ]]; then
  set -o allexport
  . "$env_file"
  set +o allexport
else
  echo "error: .env not found: $env_file" >&2
  return 1 2>/dev/null || exit 1
fi

echo "Starting MCP server with:"
echo "  PYTHONPATH: ${PYTHONPATH}"
echo "  FASTMCP_TYPE: ${FASTMCP_TYPE}"
echo "  FASTMCP_HOST: ${FASTMCP_HOST}"
echo "  FASTMCP_PORT: ${FASTMCP_PORT}"
echo "  MCP_LOG_LEVEL: ${MCP_LOG_LEVEL}"
echo "  MYSQL_VERSION: ${MYSQL_VERSION}"
echo "  MYSQL_HOST: ${MYSQL_HOST}"
echo "  MYSQL_PORT: ${MYSQL_PORT}"
echo "  MYSQL_USER: ${MYSQL_USER}"
echo "  MYSQL_PASSWORD: ${MYSQL_PASSWORD}"
echo "  MYSQL_DATABASE: ${MYSQL_DATABASE}"

python -m mcp_mysql_ops --type ${FASTMCP_TYPE} --host ${FASTMCP_HOST} --port ${FASTMCP_PORT}
