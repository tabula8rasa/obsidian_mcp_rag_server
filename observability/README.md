# Local observability

The Compose stack uses Prometheus for metrics, Grafana for dashboards, Loki
for logs, Alloy for Docker log collection, and cAdvisor for container resource
metrics. The RAG services do not depend on this stack to perform their normal
work.

## Start

Set the absolute Vault path, optionally change the local Grafana credentials,
and start everything:

```bash
export OBSIDIAN_VAULT_PATH=/absolute/path/to/vault
cp .env.example .env  # optional; edit local development credentials
docker compose --profile monitoring up -d --build
```

Without the profile, `docker compose up -d` starts only Qdrant, the RAG API,
and the MCP server. Enable `monitoring` whenever the observability services are
needed.

## Interfaces

- Grafana: <http://127.0.0.1:3000>
- Prometheus: <http://127.0.0.1:9090>
- RAG API: <http://127.0.0.1:8080>
- MCP transport: <http://127.0.0.1:8081/mcp>

Grafana automatically provisions Prometheus and Loki datasources and the
`System Overview` and `RAG / MCP` dashboards. The defaults in `.env.example`
are development-only credentials; override them for any non-local use.

## Verify application metrics and health

```bash
curl -f http://127.0.0.1:8080/metrics
curl -f http://127.0.0.1:8081/metrics
curl -f http://127.0.0.1:8080/health
curl -f http://127.0.0.1:8081/health
```

Open Prometheus and select **Status → Target health** (called **Targets** in
older versions). The `qdrant`, `rag-api`, `mcp-server`, and `cadvisor` targets
should all be `UP`.

## Verify logs

In Grafana, open **Explore**, select the Loki datasource, and run either:

```logql
{service="rag-api"}
```

```logql
{service="mcp-server"}
```

Alloy reads Docker stdout/stderr through the read-only Docker socket and adds
only the bounded `service`, `container`, and `compose_project` labels. Query
contents are intentionally absent from application logs and metric labels.

## Storage and exposure

Prometheus, Grafana, Loki, and Alloy positions use named persistent volumes.
Only Grafana and Prometheus are exposed on host loopback; Loki, Alloy, and
cAdvisor remain internal to the Compose network. Removing Compose volumes also
removes observability history, Qdrant data, model cache, and RAG sync state, so
do not use `docker compose down -v` unless that complete reset is intended.
