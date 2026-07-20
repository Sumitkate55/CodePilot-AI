# CodePilot AI

CodePilot AI turns a repository into an engineering workspace with repository intelligence,
architecture maps, source-grounded chat, AI summaries, code explanations, code review,
refactoring proposals, unit-test generation, and documentation generation.

## Hosted demonstration

The live evaluator demo is [codepilot-ai-hackathon.vercel.app](https://codepilot-ai-hackathon.vercel.app).
It is backed by a public Railway API with private PostgreSQL, Qdrant, persistent repository storage,
and server-side Gemini. See [DEPLOYMENT.md](DEPLOYMENT.md) for the exact secure deployment layout
and verification steps.

For a quick end-to-end evaluation after opening the hosted application:

1. Create an account.
2. Add the public sample repository `https://github.com/Sumitkate55/CodePilot-AI.git`.
3. Run repository intelligence, generate a summary, index it for chat, and ask a cited question.
4. Inspect the architecture graph, static review, refactoring advisor, and generated documentation.

## Run locally

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

### Enable local AI features

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
and deterministic code review still work. AI buttons show an actionable local-provider error. For
the hosted deployment, set `AI_PROVIDER=gemini` and configure `GEMINI_API_KEY` only on Railway;
never use a frontend `VITE_` variable for a secret.

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

## Privacy and security

- Each repository is scoped to its authenticated owner; IDs alone do not grant access.
- Repository indexing excludes `.env`, credential-like files, and unsafe/binary paths before any
  embedding request is made.
- Production uses private Railway networking for PostgreSQL and Qdrant. Only the FastAPI API receives
  a public domain; repository source is on a persistent API volume. The Railway Free plan can keep one
  application volume, so its private Qdrant index is rebuilt with **Index repository** if the Qdrant
  service is restarted.
- JWT secrets, database URLs, Qdrant addresses, and Gemini credentials are stored as backend
  environment variables. They are never included in the Vite client bundle.
- Repository chat answers are constrained to retrieved source chunks and return traceable file and
  line citations.

## Built with Codex and GPT-5.6

CodePilot AI was developed in iterative, test-backed phases with Codex using GPT-5.6. Codex
accelerated the workflow by analyzing the existing repository before each phase, preserving the
Clean Architecture boundaries, implementing the FastAPI and React features, adding the Gemini
provider abstraction, writing regression tests, preparing Docker/Railway/Vercel deployment assets,
and running the lint, test, migration, Docker-build, and frontend-build checks.

Key implementation decisions were to keep deterministic repository intelligence and static review
separate from AI generation, use Qdrant retrieval plus citation validation to ground chat answers,
exclude secrets before indexing, and keep AI/provider credentials server-side. The runtime can use
local Ollama for a fully local demonstration or Gemini for a normal hosted website.

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
