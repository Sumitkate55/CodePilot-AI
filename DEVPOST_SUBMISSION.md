# Devpost submission copy

## Project name

CodePilot AI

## Category

Developer Tools

## One-line pitch

CodePilot AI turns unfamiliar repositories into secure, searchable engineering workspaces with
architecture intelligence, citation-grounded chat, quality review, and actionable refactoring.

## What I built

CodePilot AI lets an authenticated user import a GitHub repository or ZIP archive and explore it as
an engineering system instead of a folder of files. It detects languages, frameworks,
dependencies, services, database artifacts, Docker files, symbols, and folder structure. The
workspace provides an architecture graph, project summary, source-grounded chat, function
explanations, static repository review, refactoring proposals with diffs, generated tests,
documentation, and a dashboard.

The app has a React/Vite frontend and FastAPI backend following Clean Architecture. PostgreSQL
stores accounts and metadata, Qdrant stores embeddings, and Gemini runs only on the server for
structured generation and embeddings. Indexing excludes environment and credential-like files.
Chat uses retrieved source chunks and shows file-and-line citations instead of inventing answers.

## How it works

1. Sign up and import a repository from GitHub or a ZIP file.
2. CodePilot stores a source version and calculates deterministic repository intelligence.
3. View the architecture, run review rules, or use AI tools.
4. For chat, safe files are chunked, embedded, and retrieved from Qdrant before answering.
5. Refactoring proposals show confidence, impact, highlighted code, and a reviewable diff.

## Live demo and source

- Live app: https://codepilot-ai-hackathon.vercel.app
- Public API health: https://api-production-f51d.up.railway.app/api/v1/health
- Source code: https://github.com/Sumitkate55/CodePilot-AI
- Setup and security: [README.md](README.md) and [DEPLOYMENT.md](DEPLOYMENT.md)

## How I used Codex and GPT-5.6

I used Codex with GPT-5.6 as my senior engineering partner through phased delivery. Before each
feature, Codex analyzed the repository and dependencies, preserved Clean Architecture boundaries,
and implemented and tested the next vertical slice. Codex accelerated the React workspace, FastAPI
use cases and adapters, Alembic migrations, tests, RAG safety checks, Gemini provider abstraction,
Docker setup, and Vercel/Railway deployment.

Key decisions made with Codex were separating deterministic analysis from AI generation, excluding
secrets before embedding, using retrieval plus citations for grounded chat, keeping provider keys
server-side, and offering local Ollama alongside hosted Gemini.

## Evaluator path

1. Open the live app and create an account.
2. Import `https://github.com/Sumitkate55/CodePilot-AI.git`.
3. Run intelligence, open the graph, run review, and view the refactoring dashboard.
4. After `GEMINI_API_KEY` is configured in Railway, use Summary, Index, and Chat.

## Important deployment note

The project uses free hosted services for the hackathon. PostgreSQL and repository source storage
are persistent; the private Qdrant index can be recreated with **Index repository** after a service
restart. Repository content remains access-controlled; only approved safe files are sent server-side
to Gemini when an AI feature is requested.
