# Database Setup with Docker Compose

This directory contains the Docker Compose configuration for the Updater database services.

## Quick Start

1. **Start the database services:**
   ```bash
   just start
   ```

2. **Check status:**
   ```bash
   just status
   ```

3. **Connect to PostgreSQL:**
   ```bash
   just psql
   ```

4. **Connect to Redis:**
   ```bash
   just redis
   ```

## File Structure

```
├── docker-compose.yml          # Main Docker Compose configuration
├── justfile                    # Just command runner for database operations
├── database/
│   ├── init.sql                # PostgreSQL initialization script
│   ├── redis.conf              # Redis configuration
│   └── backups/                # Database backup directory
└── secrets/
    ├── postgres_password.txt    # PostgreSQL password
    └── redis_password.txt       # Redis password
```

## Services

### PostgreSQL 16
- **Image:** `pgvector/pgvector:pg16`
- **Port:** 5432
- **Database:** updater_app
- **User:** app_user
- **Extensions:** pgvector, pg_trgm, btree_gin, uuid-ossp

### Redis 7
- **Image:** `redis:7-alpine`
- **Port:** 6379
- **Persistence:** AOF + RDB snapshots
- **Configuration:** Custom optimized for session storage

## Management Commands

### Basic Operations
```bash
just start      # Start services
just stop       # Stop services
just restart    # Restart services
just status     # Show status and resource usage
```

### Database Operations
```bash
just backup                          # Create backup
just restore ./path/to/backup.sql    # Restore from backup
just psql                            # PostgreSQL shell
just redis                           # Redis CLI
```

### Monitoring
```bash
just logs              # All logs
just logs-postgres     # PostgreSQL logs only
just logs-redis        # Redis logs only
just health            # Health checks
```

### Development
```bash
just dev-setup         # Start and setup development environment
just init              # Fresh database (WARNING: destroys data)
just info              # Show connection information
```

### Maintenance
```bash
just clean-backups     # Remove backups older than 30 days
just disk-usage        # Show disk usage
just update            # Update Docker images
```

## Connection Details

### PostgreSQL Connection
```
Host: localhost
Port: 5432
Database: updater_app
Username: app_user
Password: (see secrets/postgres_password.txt)
```

### Redis Connection
```
Host: localhost
Port: 6379
Password: (see secrets/redis_password.txt)
Database: 0
```

### Environment Variables for Applications
```bash
# PostgreSQL
POSTGRES_URI="postgresql://app_user:updater_pg_secure_password_2024@localhost:5432/updater_app"

# Redis
REDIS_URL="redis://:updater_redis_secure_password_2024@localhost:6379/0"
```

## Data Persistence

- **PostgreSQL data:** Stored in Docker volume `postgres_data`
- **Redis data:** Stored in Docker volume `redis_data`
- **Backups:** Stored in `./database/backups/`

## Security Notes

1. **Change default passwords** in production:
   - Edit `secrets/postgres_password.txt`
   - Edit `secrets/redis_password.txt`
   - Restart services after password changes

2. **File permissions:**
   ```bash
   chmod 600 secrets/*.txt
   ```

3. **Firewall configuration:**
   - Only expose ports 5432 and 6379 to application servers
   - Block external access in production

## Backup Strategy

### Automated Backups
```bash
# Add to crontab for daily backups
0 2 * * * cd /path/to/project && just backup
```

### Manual Backup
```bash
just backup
```

Backups are stored in `./database/backups/` with timestamp format: `backup_YYYYMMDD_HHMMSS.sql`

## Troubleshooting

### Services won't start
```bash
# Check logs
just logs

# Check health
just health

# Rebuild containers
just stop
just update
just start
```

### Connection refused
```bash
# Check if services are running
just status

# Check health
just health

# Check network connectivity
docker network ls
docker network inspect updater_network
```

### Performance issues
```bash
# Monitor resource usage
just status

# Check PostgreSQL performance
just psql
# Then run: SELECT * FROM pg_stat_activity;
```

### Disk space issues
```bash
# Check disk usage
just disk-usage

# Clean old backups (keep last 30 days)
just clean-backups
```

## Development vs Production

### Development
- Uses local Docker volumes
- Passwords in plain text files
- Direct port exposure

### Production Recommendations
- Use Docker secrets or external secret management
- Set up SSL/TLS connections
- Configure proper firewall rules
- Set up monitoring and alerting
- Implement automated backup rotation
- Use read replicas for scaling