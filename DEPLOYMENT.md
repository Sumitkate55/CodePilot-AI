# Production deployment

This deployment uses Vercel for the public React application and Railway for the private API,
PostgreSQL, Qdrant, and repository file storage. Only the API is publicly reachable. PostgreSQL,
Qdrant, and the uploaded/cloned repositories remain on Railway's private network or attached
volumes. The live demo is https://codepilot-ai-hackathon.vercel.app and its API health endpoint is
https://api-production-f51d.up.railway.app/api/v1/health.

## Hosted architecture

```text
Browser
  │ HTTPS
  ▼
Vercel (React/Vite)
  │ HTTPS API requests, CORS restricted to the Vercel origin
  ▼
Railway API (FastAPI)
  ├── Railway PostgreSQL (private managed service)
  ├── Railway Qdrant (private Docker service)
  ├── Railway repository volume at /app/data/repositories
  └── Gemini API (server-side only; its key is never sent to the browser)
```

## 1. Create the Gemini server key

In Google AI Studio, create a key for this project and enable the paid tier if you are processing
private repository code. Store the key only in Railway as `GEMINI_API_KEY`; do not add it to the
repository, Vercel, browser console, or a `VITE_` variable.

CodePilot uses `gemini-2.5-flash` for structured generation and
`gemini-embedding-001` at 768 dimensions for Qdrant retrieval. Gemini requests originate only
from the FastAPI service.

## 2. Create the Railway services

Create one Railway project named **CodePilot AI** and add:

1. A managed **PostgreSQL** service named `Postgres`.
2. A **Docker Image** service named `Qdrant` using `qdrant/qdrant:v1.13.6`.
   Do not generate a public domain for it.
3. A GitHub repository service named `API` from this repository's `main` branch. Railway reads
   the root `railway.toml` and `Dockerfile.railway`. Attach a Railway volume at
   `/app/data/repositories`. On Railway Free, use this one available application volume for source;
   Qdrant indexes can be rebuilt from source with **Index repository**.

Generate a public domain only for the `API` service.

Set these variables on the `API` service. Railway reference variables keep internal addresses and
database credentials out of Git:

```dotenv
APP_ENV=production
DEBUG=false
DATABASE_URL=${{Postgres.DATABASE_URL}}
QDRANT_URL=http://${{Qdrant.RAILWAY_PRIVATE_DOMAIN}}:6333
REPOSITORY_STORAGE_ROOT=/app/data/repositories
AI_PROVIDER=gemini
GEMINI_API_KEY=<paste the key from Google AI Studio>
GEMINI_GENERATION_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_EMBEDDING_DIMENSIONS=768
JWT_SECRET_KEY=<new random secret, at least 32 characters>
# Railway's internal health probe uses an internal Host header. This is intentionally `*`; public
# access is still protected by HTTPS, owner-scoped authorization, private data services, and CORS.
TRUSTED_HOSTS=*
```

Generate the JWT secret locally with `openssl rand -hex 32`, then paste only its output into the
Railway variable editor. The backend accepts Railway's normal `postgresql://` database URL and
converts it internally to SQLAlchemy's async driver URL.

Railway runs the Alembic migration before FastAPI starts and checks `/api/v1/health` before marking
the release healthy.

## 3. Create the Vercel frontend

Import the same GitHub repository into Vercel. Set **Root Directory** to `apps/web`; Vercel then
uses `apps/web/vercel.json` for the Vite build and React Router fallback.

After the Railway API domain exists, add this Vercel environment variable for Production and
redeploy:

```dotenv
VITE_API_BASE_URL=https://<your-railway-api-domain>/api/v1
```

`VITE_API_BASE_URL` is intentionally public because it only identifies the API endpoint. Never put
JWT, Gemini, PostgreSQL, Qdrant, or Railway values in Vercel environment variables with the
`VITE_` prefix.

Copy the resulting Vercel production URL and add it to the API's Railway variables, then redeploy
the API:

```dotenv
CORS_ORIGINS=https://codepilot-ai-hackathon.vercel.app
```

Production refresh cookies use `Secure; HttpOnly; SameSite=None` because the Vercel UI and Railway
API are different HTTPS origins. The API allows credentialed browser requests only from the exact
Vercel origin.

## 4. Verify before sharing

1. Open the Vercel URL in an incognito window.
2. Create a new account, then sign out and sign back in.
3. Add the public sample repository URL:
   `https://github.com/Sumitkate55/CodePilot-AI.git`.
4. Run repository intelligence, generate a summary, index it for chat, ask a cited question, and
   open the architecture graph.
5. Confirm Railway's API health URL returns `{"status":"healthy", ...}`.
6. Confirm the Qdrant service has no public domain and that only the API has a public domain.

## Local fallback

The Docker Compose workflow remains supported for local development and demonstrations. It uses
local Ollama instead of Gemini; see the README for the commands.
