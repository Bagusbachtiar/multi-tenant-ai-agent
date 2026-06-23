# Multi-Tenant AI Agent

A production-ready multi-tenant RAG (Retrieval-Augmented Generation) service built with FastAPI and pgvector. Each tenant gets an isolated knowledge base — upload documents, ask questions, get answers grounded in their own data. Includes direct WhatsApp integration via Meta Graph API.

## Architecture

```
 WhatsApp User
       │
       ▼
 Meta Graph API
       │
       ▼
 FastAPI (Python)
 ├── Auth ──────── X-Api-Key header → tenant lookup
 ├── RAG ───────── upload → chunk → embed → store
 │                 query  → embed → search → LLM → answer
 ├── Isolation ─── Postgres Row-Level Security (per tenant)
 └── WhatsApp ──── webhook verify · receive · reply
       │
       ├──────────────────┬──────────────────┐
       ▼                  ▼                  ▼
 Postgres + pgvector   Redis             Ollama
 (vector store, RLS)   (rate limiting)   (LLM + embeddings)
```

## Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI (Python 3.11+) |
| LLM | qwen2.5-coder:7b via Ollama |
| Embeddings | nomic-embed-text via Ollama (768-dim) |
| Vector Store | pgvector (HNSW index, cosine similarity) |
| Database | PostgreSQL 16 |
| Tenant Isolation | Postgres Row Level Security (RLS) |
| Cache / Rate Limit | Redis |
| Migrations | Alembic |
| WhatsApp | Meta Graph API (Cloud API) |
| Dashboard | Next.js 15 (separate repo) |
| Containers | Docker (Postgres + Redis) |

## Features

- **Multi-tenancy** — full data isolation via Postgres RLS. Each tenant's documents and chat history are invisible to other tenants.
- **RAG pipeline** — upload `.txt` or `.md` files, auto-chunked and embedded. Queries retrieve top-k relevant chunks before generating answers.
- **Section-aware chunking** — documents with `=== SECTION HEADER ===` markers split on section boundaries, preserving semantic context. Falls back to recursive character splitting.
- **WhatsApp integration** — single-tenant WhatsApp bot via Meta Graph API. Handles webhook verification, parses incoming messages, sends RAG-powered replies.
- **Rate limiting** — Redis-based, 60 requests/minute per API key.
- **Request logging** — structured logs with method, path, status, duration.

## Project Structure

```
app/
├── api/v1/
│   ├── chat.py          # POST /chat — RAG query
│   ├── documents.py     # CRUD /documents — upload, list, delete
│   ├── health.py        # GET /health
│   ├── tenants.py       # POST /tenants — create tenant
│   └── webhook.py       # GET+POST /webhook/whatsapp-meta
├── middleware/
│   └── http.py          # RequestLoggingMiddleware, RateLimitMiddleware
├── models/
│   ├── document.py      # Document, Chunk (with pgvector embedding)
│   └── tenant.py        # Tenant
├── schemas/             # Pydantic request/response models
├── services/
│   ├── chat.py          # process_message() — RAG orchestration
│   └── embeddings.py    # embed_texts() via Ollama
├── config.py            # Settings from .env
├── database.py          # Async SQLAlchemy engine + session
├── dependencies.py      # get_current_tenant, get_tenant_db
├── logging_config.py    # Stdlib logging setup
└── main.py              # App factory, middleware registration
alembic/versions/
├── 0001_create_tenants.py        # Tenants table + RLS function
├── 0002_create_documents_chunks.py  # Documents + chunks + RLS policies
└── 0003_add_embedding_to_chunks.py  # pgvector column + HNSW index
sample_docs/             # Demo documents for two tenants
```

## Prerequisites

- Python 3.11+
- Docker Desktop
- [Ollama](https://ollama.ai) with models pulled:
  ```
  ollama pull qwen2.5-coder:7b
  ollama pull nomic-embed-text
  ```

## Setup

**1. Start Docker containers**
```bash
docker run -d --name multi-agent-db -e POSTGRES_USER=agent -e POSTGRES_PASSWORD=agent123 -e POSTGRES_DB=multi_agent_db -p 5432:5432 pgvector/pgvector:pg16
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

**2. Create app database user (non-superuser for RLS)**
```bash
docker exec -it multi-agent-db psql -U agent -d multi_agent_db -c "
  CREATE ROLE app_user WITH LOGIN PASSWORD 'apppass123' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
  GRANT USAGE ON SCHEMA public TO app_user;
  GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
  GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_user;
"
```

**3. Python environment**
```bash
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # macOS/Linux
pip install -r requirements.txt
```

**4. Environment variables**

Copy `.env.example` to `.env` and fill in values:
```env
APP_ENV=development
SECRET_KEY=change-me-in-production
DATABASE_URL=postgresql+asyncpg://app_user:apppass123@localhost:5432/multi_agent_db
REDIS_URL=redis://localhost:6379/0
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5-coder:7b
EMBEDDING_MODEL=nomic-embed-text
WHATSAPP_PHONE_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_system_user_token
WHATSAPP_VERIFY_TOKEN=your_verify_token
WHATSAPP_TENANT_API_KEY=api_key_of_whatsapp_tenant
ADMIN_SECRET_KEY=change-me-admin
```

**5. Run migrations**
```bash
alembic upgrade head
```

**6. Start server**
```bash
uvicorn app.main:app --reload
```

API docs available at `http://localhost:8000/docs`

## API Overview

All endpoints (except health and webhook) require `X-Api-Key` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/tenants` | Create tenant (requires admin key) |
| `POST` | `/api/v1/documents` | Upload document (multipart) |
| `GET` | `/api/v1/documents` | List tenant documents |
| `DELETE` | `/api/v1/documents/{id}` | Delete document + chunks |
| `POST` | `/api/v1/chat` | Send message, get RAG answer |
| `GET` | `/api/v1/webhook/whatsapp-meta` | Meta webhook verification |
| `POST` | `/api/v1/webhook/whatsapp-meta` | Receive WhatsApp messages |

## Tenant Isolation

Tenant data isolation is enforced at the database level using Postgres Row Level Security:

```sql
-- Applied to documents and chunks tables
CREATE POLICY tenant_isolation ON documents
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());
```

`current_tenant_id()` reads from a session variable set per-request by `get_tenant_db`. The app connects as `app_user` (non-superuser, no `BYPASSRLS`) so RLS is always enforced — even bugs in application code cannot leak cross-tenant data.

## WhatsApp Setup

1. Create a Meta Developer app with WhatsApp Business Cloud API
2. Set webhook URL to `https://<your-domain>/api/v1/webhook/whatsapp-meta`
3. Set verify token to match `WHATSAPP_VERIFY_TOKEN` in `.env`
4. Generate a System User token and set as `WHATSAPP_ACCESS_TOKEN`
5. Set `WHATSAPP_TENANT_API_KEY` to the API key of the tenant that owns the WhatsApp number
6. For local development: use [ngrok](https://ngrok.com) to expose localhost

## Dashboard

Admin dashboard (Next.js) lives in a separate repo: `multi-tenant-ai-agent-dashboard`

Provides: tenant switcher, document management (upload/delete), and RAG chat testing UI.
