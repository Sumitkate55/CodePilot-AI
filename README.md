# CodePilot AI

CodePilot AI turns a repository into an engineering workspace with repository intelligence,
architecture maps, source-grounded chat, AI summaries, code explanations, code review,
refactoring proposals, unit-test generation, and documentation generation.

## Examiner quick start

### Prerequisites

- Docker Desktop running
- Optional for free AI features: [Ollama](https://ollama.com/download) installed on the host machine

### Run the full project

From the repository root:

```bash
docker compose up --build
```

Open these URLs:

- App: http://localhost:5173
- API documentation: http://localhost:8000/docs
- API health: http://localhost:8000/api/v1/health

Create an account, add a public GitHub repository or ZIP file, then choose **Analyze repository**.

### Enable free local AI features

In a second Terminal, run once:

```bash
ollama pull qwen2.5-coder:3b
ollama pull nomic-embed-text
ollama serve
```

Keep that Terminal open. The Docker API connects to Ollama on the host machine, so repository chat,
project summaries, explanations, refactoring, test generation, and documentation work without paid
OpenAI credits.

If Ollama is not installed, authentication, uploads, repository intelligence, architecture graph,
and deterministic code review still work. AI buttons show an actionable local-provider error.

### Stop the project

Press `Control + C` in the Docker Terminal, then run:

```bash
docker compose down
```

This keeps PostgreSQL, Qdrant, and repository data in Docker volumes. To remove all demo data:

```bash
docker compose down -v
```

## Main features

- Authentication with JWT refresh tokens
- GitHub URL and ZIP repository import with immutable version history
- Repository languages, frameworks, dependencies, symbols, services, Docker, environment, and database intelligence
- AI project summary and generated Markdown documentation
- Qdrant-backed, citation-only repository chat
- Interactive architecture graph and source-code explanations
- Repository-wide code review and AI refactoring advisor
- pytest, Jest, and JUnit test generation
- Workspace dashboard and repository activity history

## Development checks

Backend:

```bash
cd apps/api
source .venv/bin/activate
PYTHONPATH=src ruff check src tests
PYTHONPATH=src python -m pytest
```

Frontend:

```bash
cd apps/web
npm run lint
npm run test
npm run build
```
