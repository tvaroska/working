# Updater

> AI-powered content aggregation platform that transforms RSS feeds and newsletters into personalized, digestible summaries

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

## Overview

Updater is an intelligent content curation platform designed for knowledge workers who need to stay informed without information overload. By aggregating RSS feeds and applying advanced AI summarization, users can **get caught up in minutes, not hours** - reducing content consumption time by 60% while never missing critical updates.

### Key Features

- **AI-Powered Summarization** - Automated content summaries using Google Gemini API
  - Short summaries (tweet-length) for quick scanning
  - Long summaries (250 words) optimized for mobile reading
- **RSS Feed Aggregation** - Intelligent ingestion from multiple sources
- **Multi-Platform Support** - Web app (Next.js) and Python viewer
- **PostgreSQL with pgvector** - Vector search and semantic similarity
- **Redis Caching** - Fast session management and data caching
- **Docker-First Infrastructure** - Easy deployment and scaling

## Quick Start

### Prerequisites

- **Docker & Docker Compose** - For running infrastructure services
- **Just** - Command runner for development tasks ([install](https://github.com/casey/just#installation))
- **Node.js 20+** - For frontend development
- **Python 3.10+** - For backend services
- **uv** - Python package manager (optional, for dependency management)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd updater
```

2. **Set up environment variables**
```bash
# PostgreSQL and Redis passwords are set via environment variables
export POSTGRES_PASSWORD="your_secure_password"
export REDIS_PASSWORD="your_secure_password"
```

3. **Complete setup (infrastructure + dependencies)**
```bash
just setup
```

This command will:
- Start PostgreSQL and Redis in Docker containers
- Install frontend and auth service dependencies
- Initialize the database

4. **Start development environment**
```bash
# Option 1: Run services locally (recommended for development)
just dev

# Option 2: Run all services in containers
just dev-containers
```

### Accessing the Application

Once started, the following services are available:

- **Frontend**: http://localhost:3000
- **Content Service**: http://localhost:8001
- **Content Service API Docs**: http://localhost:8001/docs (FastAPI auto-generated)
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Project Structure

```
updater/
├── services/                    # Microservices
│   ├── frontend/               # Next.js 15 + React 19 frontend
│   │   ├── src/               # Application source
│   │   ├── public/            # Static assets
│   │   └── package.json       # Node dependencies
│   ├── content-service/       # FastAPI Python backend
│   │   ├── main.py           # Application entry point
│   │   ├── routers/          # API endpoints
│   │   ├── models/           # Database models
│   │   ├── services/         # Business logic
│   │   ├── schemas/          # Pydantic schemas
│   │   └── alembic/          # Database migrations
│   ├── postgres/              # PostgreSQL configuration
│   │   ├── schema.sql        # Database schema
│   │   └── init.sql          # Initialization scripts
│   └── redis/                 # Redis configuration
├── product/                    # Product documentation
│   ├── PRD.md                 # Product requirements
│   ├── architecture.md        # Technical architecture
│   ├── personas.md            # User personas
│   ├── roadmap.md             # Development roadmap
│   └── interactions/          # User journey flows
├── app.py                      # Flet viewer (legacy)
├── process.py                  # AI processing script
├── justfile                    # Development commands
├── docker-compose.yml          # Infrastructure services
└── pyproject.toml             # Python dependencies
```

## Development

### Common Commands

```bash
# Infrastructure management
just start                      # Start PostgreSQL + Redis
just stop                       # Stop infrastructure
just status                     # Show service status
just logs                       # View logs

# Frontend development
just frontend-dev               # Start dev server (http://localhost:3000)
just frontend-build             # Production build
just frontend-lint              # Run linter
just frontend-typecheck         # TypeScript type checking
just frontend-check             # Run all checks

# Content service development
cd services/content-service
python -m uvicorn main:app --reload --port 8001

# Database management
just psql                       # PostgreSQL shell
just redis                      # Redis CLI
just backup                     # Create database backup
just restore <backup-file>      # Restore from backup
just health                     # Run health checks
```

### Processing RSS Feeds

1. **Configure RSS feeds** in `settings.json`:
```json
{
  "feeds": [
    "https://example.com/feed.xml",
    "https://another-source.com/rss"
  ]
}
```

2. **Process feeds and generate summaries**:
```bash
python process.py --model gemini-2.0-flash-001 --input settings.json --output articles.json
```

3. **View processed articles**:
```bash
python app.py  # Starts Flet web viewer
```

### Database Migrations

When making database schema changes:

```bash
cd services/content-service

# Generate migration
alembic revision --autogenerate -m "Description of changes"

# Review generated migration in alembic/versions/

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### Adding New API Routes

1. Create route handler in `services/content-service/routers/`
2. Define Pydantic schemas in `services/content-service/schemas/`
3. Implement business logic in `services/content-service/services/`
4. Register router in `main.py`
5. Test at http://localhost:8001/docs

## Architecture

### Technology Stack

#### Frontend
- **Next.js 15** - React framework with server-side rendering
- **React 19** - UI component library
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **Headless UI** - Accessible UI components
- **Framer Motion** - Animation library

#### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database interactions
- **Pydantic** - Data validation and settings management
- **Alembic** - Database migration tool
- **feedparser** - RSS feed parsing
- **httpx** - Async HTTP client

#### Infrastructure
- **PostgreSQL 16** with pgvector extension
- **Redis 7** - In-memory data store
- **Docker & Docker Compose** - Containerization
- **Nginx** - Reverse proxy and load balancing

#### AI/ML
- **Google Gemini API** - Content summarization
- **google-genai SDK** - Python client for Gemini
- **Tenacity** - Retry logic for API calls
- **Structured Output** - Pydantic schema-based responses

### Microservices Architecture

The platform follows a two-part architecture:

1. **Frontend Layer** - TypeScript/Next.js handles UI and backend-for-frontend
2. **Backend Layer** - Python services handle all API operations

Services communicate via REST APIs with clear separation of concerns.

## Configuration

### Environment Variables

Key environment variables for services:

```bash
# Database
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql://app_user:${POSTGRES_PASSWORD}@localhost:5432/updater_app

# Redis
REDIS_PASSWORD=your_secure_password
REDIS_URL=redis://:${REDIS_PASSWORD}@localhost:6379/0

# Content Service
RSS_FETCH_TIMEOUT=30
MAX_CONCURRENT_FEEDS=10
CONTENT_BATCH_SIZE=50
FEED_REFRESH_INTERVAL=3600

# AI Service
AI_MODEL=gemini-2.0-flash-001
```

### Python Code Standards

All Python code MUST include:
- **Module-level docstring** at the top of each file
- **Class docstring** for every class
- **Function docstring** for every function with parameters and return values

See `services/content-service/main.py` for reference implementation.

## Testing

```bash
# Frontend tests
cd services/frontend
npm test

# Content service tests
cd services/content-service
pytest

# Run all checks
just frontend-check
```

## Deployment

### Docker Compose Deployment

Production deployment uses containerized services:

```bash
# Start all services in production mode
just prod

# Or manually
docker compose -f docker-compose.services.yml up -d
```

### Environment-Specific Configurations

- **Development**: `docker-compose.infra.yml` (infrastructure only)
- **Production**: `docker-compose.services.yml` (all services)

## Monitoring

### Health Checks

```bash
# Check all services
just health

# View service status and resource usage
just status-all

# Monitor logs
just logs-all              # All services
just logs-frontend         # Frontend only
just logs-postgres         # Database only
```

### Metrics

- **PostgreSQL**: Built-in health checks via `pg_isready`
- **Redis**: Health checks via PING command
- **FastAPI**: Health endpoint at `/health`

## Documentation

### Product Documentation

- **[PRD.md](product/PRD.md)** - Product requirements and vision
- **[architecture.md](product/architecture.md)** - Detailed technical architecture
- **[personas.md](product/personas.md)** - User personas and market analysis
- **[roadmap.md](product/roadmap.md)** - Development roadmap

### User Journeys

- **[product/interactions/](product/interactions/)** - Detailed user interaction flows
  - Primary user journey
  - Mobile app flow
  - Web signup journey

### Development Guides

- **[CLAUDE.md](CLAUDE.md)** - Guidance for AI coding assistants
- **[.clinerules/](.clinerules/)** - Project structure and coding standards

## Contributing

### Development Workflow

1. Create feature branch from `main`
2. Make changes following code standards
3. Run linting and type checks: `just frontend-check`
4. Test locally with `just dev`
5. Create pull request to `main`

### Code Review Standards

- All Python code must have proper docstrings
- TypeScript code must pass type checking
- Frontend changes must be responsive
- Database migrations must be reversible

## Performance

### Targets

- **App Launch**: < 2 seconds to usable content
- **API Response**: < 500ms for feed requests
- **Content Processing**: New content summarized within 15 minutes
- **Uptime**: 99.9% availability

## Security

- **Authentication**: Google OAuth (planned)
- **Data Encryption**: TLS for all connections
- **Database**: Password-protected PostgreSQL and Redis
- **Secrets Management**: Environment variables (production: use secret management)

## Roadmap

### Phase 1: MVP Foundation (Current)
- ✅ RSS feed ingestion
- ✅ AI summarization pipeline
- ✅ Basic web viewer
- ✅ Docker infrastructure
- 🚧 Next.js frontend
- 🚧 Content service API

### Phase 2: Enhanced Experience (Planned)
- Mobile app (React Native)
- User authentication
- Personalized feeds
- Offline support
- Premium features

### Phase 3: Scale & Enterprise (Future)
- Team collaboration
- Analytics dashboard
- API access
- Enterprise features

See **[roadmap.md](product/roadmap.md)** for detailed timeline.

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/updater/issues)
- **Documentation**: See `/product` directory
- **API Documentation**: http://localhost:8001/docs (when running)

## License

Apache 2.0 License - see [LICENSE](LICENSE) file for details

## Acknowledgments

- Built with [Next.js](https://nextjs.org/)
- Powered by [Google Gemini](https://ai.google.dev/)
- UI components by [Headless UI](https://headlessui.com/)
- Icons by [Heroicons](https://heroicons.com/)

---

**Get caught up in minutes, not hours.**
