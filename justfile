# Updater - Just Commands
# Database and Frontend management

# Colors for output
red := '\033[0;31m'
green := '\033[0;32m'
yellow := '\033[1;33m'
nc := '\033[0m'

# Default recipe - show help
default:
    @just --list

# Start infrastructure services only (PostgreSQL and Redis)
start:
    @echo -e "{{green}}[INFO]{{nc}} Starting infrastructure services (PostgreSQL and Redis)..."
    docker compose -f docker-compose.infra.yml up -d
    @echo -e "{{green}}[INFO]{{nc}} Waiting for services to be ready..."
    sleep 10
    @if docker compose -f docker-compose.infra.yml ps | grep -q "healthy"; then \
        echo -e "{{green}}[INFO]{{nc}} Infrastructure services are running and healthy!"; \
    else \
        echo -e "{{yellow}}[WARNING]{{nc}} Services started but health check pending..."; \
    fi

# Start all services (infrastructure + application services)
start-all:
    @echo -e "{{green}}[INFO]{{nc}} Starting all services (infrastructure + applications)..."
    docker compose -f docker-compose.services.yml up -d
    @echo -e "{{green}}[INFO]{{nc}} Waiting for services to be ready..."
    sleep 15
    @if docker compose -f docker-compose.services.yml ps | grep -q "healthy"; then \
        echo -e "{{green}}[INFO]{{nc}} All services are running and healthy!"; \
    else \
        echo -e "{{yellow}}[WARNING]{{nc}} Services started but health check pending..."; \
    fi

# Stop infrastructure services only
stop:
    @echo -e "{{green}}[INFO]{{nc}} Stopping infrastructure services..."
    docker compose -f docker-compose.infra.yml down

# Stop all services
stop-all:
    @echo -e "{{green}}[INFO]{{nc}} Stopping all services..."
    docker compose -f docker-compose.services.yml down

# Restart infrastructure services  
restart:
    @echo -e "{{green}}[INFO]{{nc}} Restarting infrastructure services..."
    docker compose -f docker-compose.infra.yml restart

# Restart all services
restart-all:
    @echo -e "{{green}}[INFO]{{nc}} Restarting all services..."
    docker compose -f docker-compose.services.yml restart

# View infrastructure logs
logs:
    docker compose -f docker-compose.infra.yml logs -f

# View all services logs
logs-all:
    docker compose -f docker-compose.services.yml logs -f

# View PostgreSQL logs only
logs-postgres:
    docker compose -f docker-compose.infra.yml logs -f postgres

# View Redis logs only
logs-redis:
    docker compose -f docker-compose.infra.yml logs -f redis

# View auth service logs only
logs-auth:
    docker compose -f docker-compose.services.yml logs -f auth

# View frontend logs only
logs-frontend:
    docker compose -f docker-compose.services.yml logs -f frontend

# Create database backup
backup:
    #!/usr/bin/env bash
    BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
    BACKUP_PATH="./services/postgres/backups/$BACKUP_FILE"
    echo -e "{{green}}[INFO]{{nc}} Creating database backup: $BACKUP_FILE"
    docker compose -f docker-compose.infra.yml exec postgres pg_dump -U app_user updater_app > "$BACKUP_PATH"
    if [ $? -eq 0 ]; then
        echo -e "{{green}}[INFO]{{nc}} Backup created successfully: $BACKUP_PATH"
    else
        echo -e "{{red}}[ERROR]{{nc}} Backup failed!"
        exit 1
    fi

# Restore database from backup file
restore BACKUP_FILE:
    #!/usr/bin/env bash
    if [ ! -f "{{BACKUP_FILE}}" ]; then
        echo -e "{{red}}[ERROR]{{nc}} Backup file not found: {{BACKUP_FILE}}"
        exit 1
    fi
    echo -e "{{yellow}}[WARNING]{{nc}} This will restore the database from: {{BACKUP_FILE}}"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "{{green}}[INFO]{{nc}} Restoring database..."
        docker compose -f docker-compose.infra.yml exec -T postgres psql -U app_user -d updater_app < "{{BACKUP_FILE}}"
        if [ $? -eq 0 ]; then
            echo -e "{{green}}[INFO]{{nc}} Database restored successfully!"
        else
            echo -e "{{red}}[ERROR]{{nc}} Restore failed!"
            exit 1
        fi
    else
        echo -e "{{green}}[INFO]{{nc}} Restore cancelled."
    fi

# Connect to PostgreSQL shell
psql:
    @echo -e "{{green}}[INFO]{{nc}} Connecting to PostgreSQL..."
    docker compose -f docker-compose.infra.yml exec postgres psql -U app_user -d updater_app

# Connect to Redis CLI
redis:
    @echo -e "{{green}}[INFO]{{nc}} Connecting to Redis..."
    docker compose -f docker-compose.infra.yml exec redis redis-cli -a ${REDIS_PASSWORD}

# Show infrastructure services status and resource usage
status:
    @echo -e "{{green}}[INFO]{{nc}} Infrastructure Services Status:"
    docker compose -f docker-compose.infra.yml ps
    @echo
    @echo -e "{{green}}[INFO]{{nc}} Database Sizes:"
    docker compose -f docker-compose.infra.yml exec postgres du -sh /var/lib/postgresql/data 2>/dev/null || echo "PostgreSQL not running"
    docker compose -f docker-compose.infra.yml exec redis du -sh /data 2>/dev/null || echo "Redis not running"
    @echo
    @echo -e "{{green}}[INFO]{{nc}} Container Resource Usage:"
    docker stats --no-stream updater_postgres updater_redis 2>/dev/null || echo "Containers not running"

# Show all services status and resource usage
status-all:
    @echo -e "{{green}}[INFO]{{nc}} All Services Status:"
    docker compose -f docker-compose.services.yml ps
    @echo
    @echo -e "{{green}}[INFO]{{nc}} Database Sizes:"
    docker compose -f docker-compose.services.yml exec postgres du -sh /var/lib/postgresql/data 2>/dev/null || echo "PostgreSQL not running"
    docker compose -f docker-compose.services.yml exec redis du -sh /data 2>/dev/null || echo "Redis not running"
    @echo
    @echo -e "{{green}}[INFO]{{nc}} Container Resource Usage:"
    docker stats --no-stream updater_postgres updater_redis updater_auth updater_frontend 2>/dev/null || echo "Containers not running"

# Initialize fresh database (WARNING: destroys all data)
init:
    #!/usr/bin/env bash
    echo -e "{{red}}[WARNING]{{nc}} This will recreate the database containers and lose all data!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "{{green}}[INFO]{{nc}} Stopping and removing containers..."
        docker compose -f docker-compose.infra.yml down -v
        echo -e "{{green}}[INFO]{{nc}} Starting fresh infrastructure services..."
        docker compose -f docker-compose.infra.yml up -d
        echo -e "{{green}}[INFO]{{nc}} Database initialized successfully!"
    else
        echo -e "{{green}}[INFO]{{nc}} Initialization cancelled."
    fi

# Install/setup just command runner
install-just:
    @echo -e "{{green}}[INFO]{{nc}} Installing 'just' command runner..."
    @if command -v just >/dev/null 2>&1; then \
        echo -e "{{green}}[INFO]{{nc}} 'just' is already installed"; \
        just --version; \
    else \
        echo -e "{{yellow}}[INFO]{{nc}} Installing 'just'..."; \
        curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to ~/bin; \
        echo -e "{{green}}[INFO]{{nc}} Add ~/bin to your PATH:"; \
        echo "export PATH=\"\$$HOME/bin:\$$PATH\""; \
    fi

# Show connection information
info:
    @echo -e "{{green}}Database Connection Information:{{nc}}"
    @echo ""
    @echo "PostgreSQL:"
    @echo "  Host: localhost"
    @echo "  Port: 5432"
    @echo "  Database: updater_app"
    @echo "  Username: app_user"
    @echo "  Password: ${POSTGRES_PASSWORD}"
    @echo "  Connection URI: postgresql://app_user:${POSTGRES_PASSWORD}@localhost:5432/updater_app"
    @echo ""
    @echo "Redis:"
    @echo "  Host: localhost"
    @echo "  Port: 6379"
    @echo "  Password: ${REDIS_PASSWORD}"
    @echo "  Connection URI: redis://:${REDIS_PASSWORD}@localhost:6379/0"

# Run health checks
health:
    @echo -e "{{green}}[INFO]{{nc}} Running health checks..."
    @echo "PostgreSQL:"
    @docker compose -f docker-compose.infra.yml exec postgres pg_isready -U app_user -d updater_app && echo "✅ PostgreSQL is ready" || echo "❌ PostgreSQL is not ready"
    @echo "Redis:"
    @docker compose -f docker-compose.infra.yml exec redis redis-cli -a ${REDIS_PASSWORD} ping 2>/dev/null && echo "✅ Redis is ready" || echo "❌ Redis is not ready"

# Clean up old backups (keeps last 30 days)
clean-backups:
    @echo -e "{{green}}[INFO]{{nc}} Cleaning old backups (older than 30 days)..."
    find ./services/postgres/backups/ -name "backup_*.sql" -mtime +30 -delete
    @echo -e "{{green}}[INFO]{{nc}} Cleanup completed."

# Show disk usage
disk-usage:
    @echo -e "{{green}}[INFO]{{nc}} Docker volumes disk usage:"
    docker system df
    @echo ""
    @echo -e "{{green}}[INFO]{{nc}} Project directory disk usage:"
    du -sh ./services/postgres/backups/ || echo "No backups directory"
    
# Development helpers
dev-setup: start
    @echo -e "{{green}}[INFO]{{nc}} Development environment ready!"
    @echo "Run 'just psql' to connect to PostgreSQL"
    @echo "Run 'just redis' to connect to Redis"
    @echo "Run 'just logs' to view logs"

# Production helpers  
prod-setup: start backup
    @echo -e "{{green}}[INFO]{{nc}} Production environment ready with initial backup!"

# Update infrastructure Docker images
update:
    @echo -e "{{green}}[INFO]{{nc}} Updating infrastructure Docker images..."
    docker compose -f docker-compose.infra.yml pull
    docker compose -f docker-compose.infra.yml up -d --build

# Update all Docker images
update-all:
    @echo -e "{{green}}[INFO]{{nc}} Updating all Docker images..."
    docker compose -f docker-compose.services.yml pull
    docker compose -f docker-compose.services.yml up -d --build

# =====================================================
# FRONTEND MANAGEMENT
# =====================================================

# Install frontend dependencies
frontend-install:
    @echo -e "{{green}}[INFO]{{nc}} Installing frontend dependencies..."
    cd services/frontend && npm install

# Start frontend development server
frontend-dev:
    @echo -e "{{green}}[INFO]{{nc}} Starting frontend development server..."
    @if [ ! -d "services/frontend/node_modules" ]; then \
        echo -e "{{yellow}}[INFO]{{nc}} Installing frontend dependencies first..."; \
        cd services/frontend && npm install; \
    fi
    @echo -e "{{yellow}}[INFO]{{nc}} Frontend will be available at http://localhost:3000"
    cd services/frontend && npm run dev

# Build frontend for production
frontend-build:
    @echo -e "{{green}}[INFO]{{nc}} Building frontend for production..."
    cd services/frontend && npm run build

# Start frontend production server
frontend-start:
    @echo -e "{{green}}[INFO]{{nc}} Starting frontend production server..."
    @echo -e "{{yellow}}[INFO]{{nc}} Frontend will be available at http://localhost:3000"
    cd services/frontend && npm run start

# Run frontend linting
frontend-lint:
    @echo -e "{{green}}[INFO]{{nc}} Running frontend linting..."
    cd services/frontend && npm run lint

# Run frontend type checking
frontend-typecheck:
    @echo -e "{{green}}[INFO]{{nc}} Running frontend type checking..."
    cd services/frontend && npm run type-check

# Install frontend dependencies and start development
frontend-setup: frontend-install frontend-dev

# Full frontend production build and start
frontend-prod: frontend-build frontend-start

# Run all frontend checks
frontend-check: frontend-lint frontend-typecheck
    @echo -e "{{green}}[INFO]{{nc}} All frontend checks completed!"

# =====================================================
# AUTHENTICATION SERVICE MANAGEMENT
# =====================================================

# Install auth service dependencies
auth-install:
    @echo -e "{{green}}[INFO]{{nc}} Installing auth service dependencies..."
    cd services/auth && npm install

# Start auth service in development mode
auth-dev:
    @echo -e "{{green}}[INFO]{{nc}} Starting auth service in development mode..."
    @if [ ! -d "services/auth/node_modules" ]; then \
        echo -e "{{yellow}}[INFO]{{nc}} Installing auth service dependencies first..."; \
        cd services/auth && npm install; \
    fi
    @if [ ! -f "services/auth/.env" ]; then \
        echo -e "{{yellow}}[INFO]{{nc}} Creating .env file with database password..."; \
        just auth-create-env; \
    fi
    @echo -e "{{yellow}}[INFO]{{nc}} Auth service will be available at http://localhost:3001"
    cd services/auth && npm run dev

# Start auth service in production mode
auth-start:
    @echo -e "{{green}}[INFO]{{nc}} Starting auth service in production mode..."
    @if [ ! -d "services/auth/node_modules" ]; then \
        echo -e "{{yellow}}[INFO]{{nc}} Installing auth service dependencies first..."; \
        cd services/auth && npm install; \
    fi
    @if [ ! -f "services/auth/.env" ]; then \
        echo -e "{{yellow}}[INFO]{{nc}} Creating .env file with database password..."; \
        just auth-create-env; \
    fi
    @echo -e "{{yellow}}[INFO]{{nc}} Auth service will be available at http://localhost:3001"
    cd services/auth && npm run start

# Create .env file for auth service with correct database password
auth-create-env:
    @echo -e "{{green}}[INFO]{{nc}} Creating auth service .env file..."
    @cp services/auth/.env.example services/auth/.env
    @sed -i "s/your_password_here/${POSTGRES_PASSWORD}/g" services/auth/.env && \
     sed -i "s/your_jwt_access_secret_here_64_chars_minimum/7a9c8e6f4d2b1a5c9e8f7d3b6a4c2e1f9d8c7b5a3e6f4d2a1c9e8f7d3b6a4c2e1f/g" services/auth/.env && \
     sed -i "s/your_jwt_refresh_secret_here_64_chars_minimum/3f7e9d2a8c6b4e1a7d3f9c5e2b8a6d4f1c7e9d2a8c6b4e1a7d3f9c5e2b8a6d4f1c/g" services/auth/.env
    @echo -e "{{green}}[INFO]{{nc}} .env file created successfully!"

# Install auth service dependencies and start development
auth-setup: auth-install auth-dev

# =====================================================
# FULL STACK MANAGEMENT
# =====================================================

# Install all dependencies
install: frontend-install auth-install
    @echo -e "{{green}}[INFO]{{nc}} All dependencies installed!"

# Start development stack (infrastructure + local development services)
dev: start auth-dev frontend-dev
    @echo -e "{{green}}[INFO]{{nc}} Development stack started!"
    @echo -e "{{yellow}}[INFO]{{nc}} Infrastructure: Running (Docker)"
    @echo -e "{{yellow}}[INFO]{{nc}} Auth Service: http://localhost:3001 (Local)"
    @echo -e "{{yellow}}[INFO]{{nc}} Frontend: http://localhost:3000 (Local)"

# Start containerized development stack
dev-containers: start-all
    @echo -e "{{green}}[INFO]{{nc}} Containerized development stack started!"
    @echo -e "{{yellow}}[INFO]{{nc}} All services running in containers"
    @echo -e "{{yellow}}[INFO]{{nc}} Frontend: http://localhost:3000"
    @echo -e "{{yellow}}[INFO]{{nc}} Auth Service: http://localhost:3001"

# Start full production stack (all containerized)
prod: start-all
    @echo -e "{{green}}[INFO]{{nc}} Production stack started!"
    @echo -e "{{yellow}}[INFO]{{nc}} All services containerized and running"
    @echo -e "{{yellow}}[INFO]{{nc}} Frontend: http://localhost:3000"
    @echo -e "{{yellow}}[INFO]{{nc}} Auth Service: http://localhost:3001"

# Show service URLs and status
service-urls:
    @echo ""
    @echo -e "{{green}}[INFO]{{nc}} Service URLs:"
    @echo "  Frontend: http://localhost:3000"
    @echo "  Auth API: http://localhost:3001"
    @echo "  Auth Health: http://localhost:3001/health"
    @echo "  Auth OAuth Config: http://localhost:3001/api/auth/oauth/config"

# Quick setup for new developers
setup: dev-setup install
    @echo -e "{{green}}[INFO]{{nc}} Development environment fully set up!"
    @echo ""
    @echo "🚀 Quick start commands:"
    @echo "  just dev              # Start development stack (infra + local services)"
    @echo "  just dev-containers   # Start all services in containers"
    @echo "  just start            # Start infrastructure only"
    @echo "  just start-all        # Start all services in containers"
    @echo "  just frontend-dev     # Start only frontend locally"
    @echo "  just auth-dev         # Start only auth service locally"
    @echo "  just psql             # Connect to database"
    @echo "  just logs             # View infrastructure logs"
    @echo "  just logs-all         # View all service logs"

# Check installation status
check-install:
    @echo -e "{{green}}[INFO]{{nc}} Checking installation status..."
    @echo ""
    @echo "Frontend dependencies:"
    @if [ -d "services/frontend/node_modules" ]; then \
        echo "  ✅ Frontend dependencies installed"; \
    else \
        echo "  ❌ Frontend dependencies not installed (run: just frontend-install)"; \
    fi
    @echo ""
    @echo "Auth service:"
    @if [ -d "services/auth/node_modules" ]; then \
        echo "  ✅ Auth service dependencies installed"; \
    else \
        echo "  ❌ Auth service dependencies not installed (run: just auth-install)"; \
    fi
    @if [ -f "services/auth/.env" ]; then \
        echo "  ✅ Auth service .env file exists"; \
    else \
        echo "  ❌ Auth service .env file missing (run: just auth-create-env)"; \
    fi
    @echo ""
    @echo "Database:"
    @if docker compose -f docker-compose.infra.yml ps | grep -q "updater_postgres.*healthy"; then \
        echo "  ✅ Database is running and healthy"; \
    elif docker compose -f docker-compose.infra.yml ps | grep -q "updater_postgres"; then \
        echo "  ⚠️  Database is running but not healthy"; \
    else \
        echo "  ❌ Database is not running (run: just start)"; \
    fi