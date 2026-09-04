# Obsidian MCP RAG Server

A local semantic-search stack for an Obsidian Vault. Markdown notes are chunked
and embedded by a FastAPI service, stored in Qdrant, and exposed to AI clients
through the MCP tool `search_vault`.

The Vault is mounted read-only, and every published port binds to the host's
loopback interface by default.

## Architecture

- **RAG API** loads the Vault, creates embeddings, synchronizes Qdrant, and
  exposes indexing and search endpoints.
- **Qdrant** stores note chunks and their embedding vectors.
- **MCP server** exposes semantic search as the `search_vault` tool over
  Streamable HTTP.
- **Optional monitoring** uses Prometheus, Grafana, Loki, Alloy, and cAdvisor
  for metrics, dashboards, logs, and container resource usage.

## Requirements

- Docker with Docker Compose
- An Obsidian Vault that is also a Git repository
- Enough disk space for Docker images, the embedding model cache, and the
  vector database

Only committed Vault changes are processed by normal synchronization. Commit
new or edited notes before calling `/sync`.

## Quick start

Clone the repository and enter it:

```bash
git clone git@github.com:tabula8rasa/obsidian_mcp_rag_server.git
cd obsidian_mcp_rag_server
```

Set the absolute path to your Vault and start the business services:

```bash
export OBSIDIAN_VAULT_PATH=/absolute/path/to/vault
docker compose up -d --build
```

The first build and startup can take a while because the embedding model must
be downloaded. Check service status and health with:

```bash
docker compose ps
curl -f http://127.0.0.1:8080/health
curl -f http://127.0.0.1:8081/health
```

Build the initial vector index:

```bash
curl -X POST http://127.0.0.1:8080/reindex
```

## Search the Vault

Use the RAG API directly:

```bash
curl -X POST http://127.0.0.1:8080/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"How did I configure semantic search?","limit":5}'
```

Or configure an MCP client that supports remote Streamable HTTP servers to use:

```text
http://127.0.0.1:8081/mcp
```

The server provides one tool:

- `search_vault(query, limit=5)` returns relevant note fragments with their
  source paths, headings, chunk indexes, and similarity scores. `limit` must be
  between 1 and 20.

## Keep the index current

After committing changes in the Vault, run an incremental synchronization:

```bash
curl -X POST http://127.0.0.1:8080/sync
```

Use a full reindex after changing chunking or path-filter rules, changing the
embedding model or vector size, or creating a fresh Qdrant volume:

```bash
curl -X POST http://127.0.0.1:8080/reindex
```

Indexing includes non-empty `.md` files and excludes paths containing `.git`,
`.obsidian`, `.trash`, or `media`. Obsidian embeds are removed before chunking;
notes containing only embeds produce no chunks.

Useful RAG API endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check Vault, Git, Qdrant, and collection health |
| `GET` | `/stats` | Show collection and synchronization state |
| `GET` | `/metrics` | Expose Prometheus metrics |
| `POST` | `/search` | Search indexed note chunks |
| `POST` | `/sync` | Apply committed Vault changes incrementally |
| `POST` | `/reindex` | Rebuild the complete index |

## Monitoring

Start the complete stack with the monitoring profile:

```bash
export OBSIDIAN_VAULT_PATH=/absolute/path/to/vault
export GRAFANA_ADMIN_USER=admin
export GRAFANA_ADMIN_PASSWORD=choose-a-local-password
docker compose --profile monitoring up -d --build
```

Local interfaces:

| Service | URL |
| --- | --- |
| Grafana | <http://127.0.0.1:3000> |
| Prometheus | <http://127.0.0.1:9090> |
| Alloy | <http://127.0.0.1:12345> |
| cAdvisor | <http://127.0.0.1:8082> |
| Qdrant | <http://127.0.0.1:6333> |
| RAG API | <http://127.0.0.1:8080> |
| MCP server | <http://127.0.0.1:8081/mcp> |

Grafana provisions the Prometheus and Loki data sources and the included
dashboards automatically. See [observability/README.md](observability/README.md)
for verification and log-query examples.

## Tests

Run the RAG API unit tests from the repository root:

```bash
PYTHONPATH=rag-api python -m unittest discover -s rag-api/tests -v
```

Run the MCP unit tests after installing `mcp-server/requirements.txt`:

```bash
PYTHONPATH=mcp-server python -m unittest discover -s mcp-server/tests -v
```

With the stack running, execute the MCP protocol smoke test:

```bash
MCP_URL=http://127.0.0.1:8081/mcp \
PYTHONPATH=mcp-server python mcp-server/tests/check_mcp.py
```

## Persistent data and resets

Docker named volumes retain the Qdrant collection, embedding-model cache, RAG
synchronization state, and monitoring data. Do not use
`docker compose down -v` unless you intend to delete all of them.

If the embedding model or vector dimensions change, recreate only the Qdrant
volume and then reindex:

```bash
docker compose down
docker volume ls --filter name=qdrant_storage
docker volume rm <confirmed-project-name>_qdrant_storage
docker compose up -d --build
curl -X POST http://127.0.0.1:8080/reindex
```

Confirm the actual Compose project volume name before removing it. Volume
deletion is irreversible, though it does not modify the read-only Vault.
