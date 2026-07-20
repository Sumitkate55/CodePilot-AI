# CodePilot AI API

The backend foundation is a FastAPI application organised around Clean Architecture:

- `domain/` contains framework-independent business models and rules.
- `application/` contains use cases and ports.
- `infrastructure/` contains SQLAlchemy, logging, and external adapters.
- `presentation/` contains HTTP routes, middleware, and API errors.

## Local development

1. Copy `.env.example` to `.env` and set a PostgreSQL `DATABASE_URL`.
2. Install the project with `python -m pip install -e '.[dev]'`.
3. Run `alembic upgrade head` before adding feature migrations.
4. Start the server with `python -m uvicorn --app-dir src codepilot_api.main:app --reload`.

Liveness is available at `/api/v1/health`; readiness, including database verification, is at `/api/v1/ready`.

## AI providers

CodePilot supports two provider modes for project summaries and repository chat:

- `AI_PROVIDER=openai` uses GPT-5 plus OpenAI embeddings and needs an API key with paid usage
  allowance.
- `AI_PROVIDER=ollama` runs models locally, so no OpenAI API credits are required. It is the default
  in `.env.example` and is a practical option for local development.

For an Apple Silicon Mac with 8 GB memory, install [Ollama](https://ollama.com/download/mac), open it,
then run these commands once:

```bash
ollama pull qwen2.5-coder:3b
ollama pull nomic-embed-text
```

Set the following in `.env`, restart the API, and use the dashboard as usual:

```dotenv
AI_PROVIDER=ollama
OLLAMA_CHAT_MODEL=qwen2.5-coder:3b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

The summary endpoint uses the latest stored repository intelligence rather than raw repository files,
persists structured output per repository version, and can be refreshed from the repository dashboard.

## Repository chat (RAG)

Repository chat indexes safe UTF-8 source chunks in Qdrant, retrieves only chunks belonging to the
latest stored repository version, and returns answers only with source citations. Environment files,
credential-like files, binaries, oversized files, and dependency/build directories are excluded before
embedding.

Start a local Qdrant instance before indexing a repository:

```bash
docker run --name codepilot-qdrant \
  -p 6333:6333 -p 6334:6334 \
  -v codepilot-qdrant:/qdrant/storage \
  -d qdrant/qdrant
```

Keep `QDRANT_URL=http://localhost:6333` in `.env`, run `alembic upgrade head`, then select **Index
repository** in a repository workspace. Repository chat uses the same selected AI provider as project
summaries. In Ollama mode, repository source stays on your machine; in OpenAI mode, indexing and
answers require API usage allowance.

## Quality checks

Run `ruff check src tests` and `PYTHONPATH=src python -m pytest` from this directory.
