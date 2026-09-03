# Repository Guidelines

## Project Structure & Module Organization

This repository runs a small Obsidian semantic-search stack with Docker Compose. `compose.yaml` defines Qdrant and the FastAPI service. Application code lives in `rag-api/app/`:

- `main.py` creates the FastAPI application and initializes shared resources.
- `api/` defines HTTP routes and request schemas.
- `core/` centralizes environment-variable settings.
- `domain/` contains framework-independent data objects.
- `infrastructure/` integrates with FastEmbed and manages Qdrant storage.
- `services/` handles Markdown chunking, vault loading, and Git synchronization.

Container dependencies are listed in `rag-api/requirements.txt`; the service image is defined by `rag-api/Dockerfile`. Tests live in `rag-api/tests/` and mirror application modules.

## Build, Test, and Development Commands

Set the host vault path before using Compose:

```bash
export OBSIDIAN_VAULT_PATH=/absolute/path/to/vault
docker compose up --build
```

The API is then available at `http://127.0.0.1:8080`; Qdrant binds to `127.0.0.1:6333`. Use `docker compose down` to stop the stack and `docker compose logs -f rag-api` to follow API logs. Quick checks include:

```bash
curl http://127.0.0.1:8080/health
curl -X POST http://127.0.0.1:8080/sync
```

Run tests with `PYTHONPATH=rag-api python -m unittest discover -s rag-api/tests -v`. Use `POST /reindex` only for a forced full rebuild; normal updates use `/sync` after committing Vault changes.

## Coding Style & Naming Conventions

Follow standard Python conventions: four-space indentation, `snake_case` functions and modules, `PascalCase` classes, and uppercase configuration constants. Keep type annotations on public functions and use explicit relative imports within `app`. Prefer small functions with clear error messages. No formatter or linter is configured; keep changes PEP 8-compatible and avoid unrelated reformatting.

## Testing Guidelines

Prioritize unit tests for heading parsing, chunk-size boundaries, ignored `.obsidian` content, deterministic point IDs, and empty-vault behavior. Mock Qdrant and embedding calls in unit tests; reserve container-backed checks for integration tests. Name tests `test_<behavior>` and keep fixtures minimal.

## Commit & Pull Request Guidelines

Git history is unavailable in this checkout, so use concise, imperative commit subjects such as `Add chunking boundary tests`. Keep commits focused. Pull requests should describe behavior changes, list verification commands, note configuration changes, and include sample request/response output for API changes. Link relevant issues and call out any indexing or collection-recreation impact.

## Security & Configuration

Keep vault mounts read-only and never commit note contents, credentials, model caches, or Qdrant data. Document new environment variables in `compose.yaml` and provide safe defaults in `settings.py` where appropriate.
