# This Dockerfile is exclusively for smithery.ai.

FROM python:3.11-slim

WORKDIR /app

COPY . .

# Install the project dependencies
RUN pip install uv
RUN uv sync

EXPOSE 8080

# CMD ["python", "-m", "mcp_abmari_api.ambari_api"]
CMD ["uv", "run", "python", "-m", "src.mcp_mysql_ops", "--type", "stdio"]