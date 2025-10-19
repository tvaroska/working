# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered content aggregation platform called "Updater" that processes RSS feeds, generates AI summaries, and delivers personalized content updates. The project uses a microservices architecture with Docker-based infrastructure and separate frontend and backend services.

## Technology Stack

### Infrastructure
- **PostgreSQL 16** (with pgvector extension) - Primary database
- **Redis 7** - Caching and session management
- **Docker & Docker Compose** - Containerization and orchestration

### Backend Services
- **Content Service** - FastAPI-based Python service for RSS feed ingestion and content management (port 8001)
  - Located in `services/content-service/`
  - Uses SQLAlchemy ORM, Alembic for migrations
  - Dependencies: FastAPI, feedparser, httpx, psycopg2-binary

- **AI Processing** - Python scripts using Google Gemini API for content summarization
  - Main script: `process.py`
  - Uses `google-genai` SDK with retry logic via `tenacity`
  - Processes RSS feeds and generates both short (tweet-like) and long (250-word) summaries

### Frontend
- **Next.js 15** with React 19 and TypeScript
  - Located in `services/frontend/`
  - Styling: Tailwind CSS with Headless UI
  - Icons: Heroicons, Lucide React
  - Animations: Framer Motion

- **Flet-based viewer** - Python web app for viewing processed articles
  - Main file: `app.py`
  - Displays articles from `articles.json` with detail view navigation

## Development Commands

### Quick Start
```bash
# First-time setup
just setup              # Start infrastructure + install all dependencies

# Start infrastructure only (PostgreSQL + Redis)
just start

# Start all services in containers
just start-all

# Development mode (infrastructure in Docker, services run locally)
just dev               # Starts infrastructure + auth service + frontend locally

# Development mode (all services containerized)
just dev-containers
```

### Service-Specific Commands

#### Frontend Development
```bash
just frontend-install      # Install npm dependencies
just frontend-dev          # Start dev server (http://localhost:3000)
just frontend-build        # Production build
just frontend-lint         # Run ESLint
just frontend-typecheck    # Run TypeScript type checking
just frontend-check        # Run all checks (lint + typecheck)
```

#### Content Service (Python/FastAPI)
```bash
# Run directly (ensure infrastructure is running first)
cd services/content-service
python -m uvicorn main:app --reload --port 8001
```

#### AI Processing Script
```bash
# Process RSS feeds and generate summaries
python process.py --model gemini-2.0-flash-001 --input settings.json --output articles.json

# View processed articles
python app.py  # Starts Flet web viewer
```

### Database Management
```bash
just psql                  # Connect to PostgreSQL shell
just redis                 # Connect to Redis CLI
just backup                # Create database backup
just restore <file>        # Restore from backup
just health                # Run health checks
just info                  # Show connection information
```

### Monitoring & Logs
```bash
just status                # Show infrastructure status
just status-all            # Show all services status
just logs                  # Infrastructure logs (PostgreSQL + Redis)
just logs-all              # All services logs
just logs-postgres         # PostgreSQL logs only
just logs-redis            # Redis logs only
just logs-frontend         # Frontend logs only
```

### Maintenance
```bash
just stop                  # Stop infrastructure
just stop-all              # Stop all services
just restart               # Restart infrastructure
just restart-all           # Restart all services
just clean-backups         # Remove backups older than 30 days
just disk-usage            # Show disk usage
```

## Architecture Patterns

### Service Organization
The project follows a microservices pattern with clear separation:

```
services/
├── content-service/     # FastAPI Python backend
│   ├── main.py         # Application entry point
│   ├── config.py       # Pydantic settings management
│   ├── database.py     # SQLAlchemy setup
│   ├── routers/        # API route handlers (content, sources, health)
│   ├── models/         # SQLAlchemy ORM models
│   ├── schemas/        # Pydantic request/response schemas
│   ├── services/       # Business logic (rss_service, content_service)
│   └── alembic/        # Database migrations
├── frontend/           # Next.js TypeScript frontend
├── postgres/           # Database initialization scripts
└── redis/              # Redis configuration
```

### Python Code Requirements
All Python modules MUST follow these documentation standards:
- **File-level docstring** at the top of each module
- **Class docstring** for every class definition
- **Function/method docstring** for every function describing parameters and return values

See `services/content-service/main.py` and `services/content-service/config.py` for reference implementations.

### Configuration Management
- **Content Service**: Uses `pydantic-settings` with `.env` file support (see `services/content-service/config.py`)
- **Environment variables** are loaded from `.env` files and can be overridden
- **Docker Compose** uses environment variable substitution for secrets (POSTGRES_PASSWORD, REDIS_PASSWORD)

### Database Architecture
- **PostgreSQL** with pgvector extension for vector similarity search
- **Schema initialization**: `services/postgres/schema.sql` (runs on first start)
- **Migrations**: Alembic for Python services (in `services/content-service/alembic/`)
- **Connection pooling** handled by SQLAlchemy

### API Design Patterns
FastAPI services follow standard patterns:
- **Lifespan events** for startup/shutdown tasks (see `main.py`)
- **Dependency injection** for database sessions (`get_db()`)
- **Router-based organization** by resource type (content, sources, health)
- **Pydantic schemas** for request/response validation

### AI Processing Pipeline
The `process.py` script implements a robust article processing pipeline:
1. Fetch articles from RSS feeds (using `feedparser`)
2. Filter articles by publish date
3. Determine content MIME type (supports HTML, YouTube videos)
4. Generate summaries using Gemini API with structured output (Pydantic schemas)
5. Implement retry logic with exponential backoff for rate limiting
6. Use semaphore for concurrency control (max 10 concurrent requests)
7. Output structured JSON with short and long summaries

## Project Documentation Structure

The repository follows a structured documentation approach (see `.clinerules/project_structure.md`):

- **product/** - Product requirements, architecture, personas, roadmap
- **product/interactions/** - User journey flows and interaction patterns
- **product/components/** - Component-level specifications

When referencing or creating documentation, follow the templates defined in `.clinerules/`.

## Connection Information

### PostgreSQL
- Host: localhost
- Port: 5432
- Database: updater_app
- User: app_user
- Password: Set via POSTGRES_PASSWORD env var
- URI format: `postgresql://app_user:${POSTGRES_PASSWORD}@localhost:5432/updater_app`

### Redis
- Host: localhost
- Port: 6379
- Password: Set via REDIS_PASSWORD env var
- URI format: `redis://:${REDIS_PASSWORD}@localhost:6379/0`

### Services
- Frontend: http://localhost:3000
- Content Service: http://localhost:8001
- Content Service Health: http://localhost:8001/health

## Common Workflows

### Adding a New Content Service Route
1. Create route handler in `services/content-service/routers/`
2. Define Pydantic schemas in `services/content-service/schemas/`
3. Add business logic in `services/content-service/services/`
4. Include router in `main.py`
5. Test endpoint at http://localhost:8001/docs (FastAPI auto-generated docs)

### Database Changes
1. Modify SQLAlchemy models in `services/content-service/models/`
2. Generate migration: `cd services/content-service && alembic revision --autogenerate -m "description"`
3. Review generated migration in `alembic/versions/`
4. Apply migration: `alembic upgrade head`

### Frontend Development
1. Components should use TypeScript with proper typing
2. Follow Next.js 15 app router conventions
3. Use Tailwind CSS for styling
4. Run type checks before committing: `just frontend-typecheck`

### Processing New RSS Feeds
1. Add feed URLs to `settings.json` in the "feeds" array
2. Run: `python process.py --input settings.json --output articles.json`
3. View results: `python app.py`

## Python Dependency Management

This project uses **uv** for Python dependency management (see `pyproject.toml` and `uv.lock`):
- Primary dependencies include: flet, feedparser, google-genai, structlog, tqdm, tenacity
- Dev dependencies: black, isort
- Python >= 3.10 required

## Important Notes

- The project has both a legacy Flet-based viewer (`app.py`) and a modern Next.js frontend
- AI processing uses Google Gemini API via Vertex AI (requires GCP authentication)
- Docker Compose files are split: `docker-compose.infra.yml` (PostgreSQL + Redis) and `docker-compose.services.yml` (all services)
- Health checks are configured for all containerized services
- Backup directory: `services/postgres/backups/`

@.clinerules/AGENTS.md
@.clinerules/project_structure.md
@.clinerules/interactions_structure.md
