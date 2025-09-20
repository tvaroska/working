-- Updater - Database Initialization
-- PostgreSQL 16 with pgvector extension
-- This file loads the complete database schema

-- Load the complete schema
\i /docker-entrypoint-initdb.d/schema.sql

-- Create application user with proper permissions
-- Note: Password should be changed in production
GRANT ALL PRIVILEGES ON DATABASE updater_app TO app_user;

-- Grant permissions on public schema
GRANT ALL ON SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO app_user;

-- Enable vector operations
ALTER DATABASE updater_app SET shared_preload_libraries = 'vector';