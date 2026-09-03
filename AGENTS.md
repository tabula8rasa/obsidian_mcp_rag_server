# Repository Guidelines

## Project Overview

This repository runs a local Obsidian semantic-search stack with Docker
Compose. The stack has three services:

- `qdrant` stores note chunks and their vectors.
- `rag-api` loads the Vault, creates embeddings, synchronizes Qdrant, and
  exposes search and indexing HTTP endpoints.
- `mcp-server` exposes the RAG search endpoint as the MCP tool
  `search_vault`.

The host Vault is mounted read-only at `/vault`. Synchronization is Git-aware:
normal `/sync` operations process committed Vault changes only.

## Project Structure & Module Responsibilities

### RAG API

Application code lives in `rag-api/app/`:

- `main.py` creates the FastAPI application and initializes Qdrant and the
  embedding model during startup.
- `api/routes.py` defines health, statistics, sync, reindex, and search HTTP
  endpoints; `api/schemas.py` contains request schemas.
- `core/settings.py` owns environment-backed configuration.
- `core/indexing.py` defines the shared rules for indexable Vault paths.
- `domain/chunk.py` contains the framework-independent `Chunk` data object.
- `infrastructure/embedding_model.py` loads FastEmbed and converts model
  output to the configured vector size.
- `infrastructure/qdrant_store.py` owns collection setup, point persistence,
  deletion, rebuilding, statistics, and vector search.
- `services/markdown_chunker.py` removes Obsidian embeds and splits Markdown
  into searchable chunks.
- `services/vault_loader.py` validates paths and loads notes from the mounted
  Vault.
- `services/vault_sync.py` calculates committed Git changes and applies full
  or incremental index updates.

Tests live in `rag-api/tests/` and mirror the `infrastructure/` and `services/`
packages.

### MCP Server

Application code lives in `mcp-server/app/`:

- `main.py` is the process entrypoint and starts the configured transport.
- `server.py` is the composition root that constructs dependencies and
  registers tools and routes.
- `core/settings.py` loads MCP runtime configuration; `core/logging.py`
  configures logging.
- `clients/rag_api.py` owns asynchronous HTTP communication with the RAG API
  and translates transport/response failures into client errors.
- `tools/vault_search.py` validates and registers the `search_vault` MCP tool.
- `routes/health.py` provides the container liveness endpoint.

Focused MCP tests mirror these packages under `mcp-server/tests/`.
`mcp-server/tests/check_mcp.py` is the end-to-end protocol smoke test.

Container dependencies and images are defined independently in each
service's `requirements.txt` and `Dockerfile`.

## Indexing Behavior

- Only `.md` files are indexable.
- Any path containing `.git`, `.obsidian`, `.trash`, or `media` is excluded
  from loading, incremental synchronization, and search results.
- Every non-empty Markdown note is indexable, including short notes without
  headings.
- Notes containing only removed Obsidian embeds produce no chunks.
- Point IDs are deterministic from `source_path` and `chunk_index`.
- The configured FastEmbed model emits 384-dimensional vectors. Both document
  and query vectors are currently truncated to `VECTOR_SIZE=32` before being
  sent to Qdrant. Keep these paths symmetrical.
- Changing `MODEL_NAME` or `VECTOR_SIZE` requires collection recreation and a
  full reindex; existing vectors are not compatible across such changes.

## Build, Test & Development Commands

Set the absolute host Vault path before using Compose:

```bash
export OBSIDIAN_VAULT_PATH=/absolute/path/to/vault
docker compose up -d --build
```

Local endpoints:

- RAG API: `http://127.0.0.1:8080`
- MCP transport: `http://127.0.0.1:8081/mcp`
- MCP health: `http://127.0.0.1:8081/health`
- Qdrant: `http://127.0.0.1:6333`

Useful commands:

```bash
docker compose ps
docker compose logs -f rag-api mcp-server
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/stats
curl -X POST http://127.0.0.1:8080/sync
curl -X POST http://127.0.0.1:8080/reindex
curl http://127.0.0.1:8081/health
```

Use `/sync` after committing ordinary Vault changes. Use `/reindex` for a
forced rebuild, chunking-rule changes, path-filter changes, or after creating
a fresh Qdrant volume.

Run RAG unit tests from the repository root:

```bash
PYTHONPATH=rag-api python -m unittest discover -s rag-api/tests -v
```

Run MCP unit tests in an environment containing `mcp-server/requirements.txt`:

```bash
PYTHONPATH=mcp-server python -m unittest discover -s mcp-server/tests -v
```

After the stack is running, execute the MCP protocol smoke test with:

```bash
MCP_URL=http://127.0.0.1:8081/mcp \
PYTHONPATH=mcp-server python mcp-server/tests/check_mcp.py
```

If host dependencies are unavailable, build the MCP image and mount the source
tree to run its unit tests in the runtime environment:

```bash
docker compose build mcp-server
docker run --rm \
  -v "$PWD/mcp-server:/workspace:ro" \
  -w /workspace \
  -e PYTHONPATH=/workspace \
  obsidian-rag-vault-mcp-server \
  python -m unittest discover -s tests -v
```

## Qdrant Volume Recreation

Recreate only the Qdrant volume when vector dimensions or embedding
compatibility changes. Confirm the Compose project volume name before removal;
volume deletion is irreversible but does not delete the read-only Vault.

For this repository's current Compose project name:

```bash
docker compose down
docker volume rm obsidian-rag-vault_qdrant_storage
docker compose up -d --build
curl -X POST http://127.0.0.1:8080/reindex
```

Do not use `docker compose down -v` for this operation because it also removes
the embedding-model cache and RAG synchronization-state volumes.

## Coding Style & Naming Conventions

Follow standard Python conventions: four-space indentation, `snake_case`
functions and modules, `PascalCase` classes, and uppercase constants. Keep type
annotations on public functions and use explicit relative imports within each
`app` package. Prefer small functions with one clear responsibility and useful
error messages. No formatter or linter is configured; keep changes PEP
8-compatible and avoid unrelated reformatting.

Preserve dependency direction:

- API and MCP protocol layers may call application services or clients.
- Services may use domain objects and infrastructure adapters.
- Domain objects must remain framework-independent.
- The MCP RAG client must not contain MCP registration or input-validation
  logic.
- Tool modules must not duplicate HTTP transport details.

## Testing Guidelines

Add or update tests in the package corresponding to the changed behavior.
Prioritize coverage for:

- heading parsing and chunk-size boundaries;
- short heading-free notes and embed-only notes;
- ignored Vault directory segments;
- safe relative paths and empty-Vault behavior;
- deterministic point IDs and embedding dimensions;
- incremental add, modify, delete, and rename behavior;
- RAG client transport and response errors;
- MCP input normalization, validation, and error translation.

Mock Qdrant, FastEmbed, and outbound HTTP calls in unit tests. Use the running
Compose stack only for integration and protocol-level checks. Name tests
`test_<behavior>` and keep fixtures minimal.

## Commit & Pull Request Guidelines

Use concise, imperative commit subjects such as `Add chunking boundary tests`.
Keep commits focused. Before committing, run `git diff --check` and the
relevant test suites.

Pull requests should describe behavior changes, list verification commands,
note configuration changes, and include sample request/response output for API
or MCP contract changes. Explicitly call out changes that require collection
recreation or full reindexing.

## Security & Configuration

Keep Vault mounts read-only. Never commit note contents, credentials, model
caches, Qdrant data, or RAG state. Preserve loopback-only host port bindings
unless external access is explicitly required. Document new environment
variables in `compose.yaml` and provide safe defaults in the relevant
`core/settings.py` module.
