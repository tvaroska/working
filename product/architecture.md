# Updater - Technical Architecture

## High-Level System Design and Component Interaction

### Architecture Overview

Updater follows a two-part architecture designed for rapid MVP development and clear separation of concerns. The system separates frontend and backend responsibilities, with TypeScript + Next.js handling the frontend and backend-for-frontend (BFF) layer, while Python-based services handle all backend operations via API routes.

```
┌─────────────────────── Frontend Layer ─────────────────────┐
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │   Mobile App    │  │  Progressive    │  │     Admin    ││
│  │ (React Native)  │  │   Web App       │  │   Dashboard  ││
│  │   iOS/Android   │  │ (Next.js PWA)   │  │   (React)    ││
│  └─────────────────┘  └─────────────────┘  └──────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │           Next.js Frontend + BFF Layer                  ││
│  │  • Server-Side Rendering (SSR)                         ││
│  │  • API Routes for Frontend Logic                       ││
│  │  • Authentication State Management                     ││
│  │  • Static Asset Serving                               ││
│  │  • Progressive Web App Features                       ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
└─────────────────────────────────────────────────────────────┘
                                │
                      ┌─────────▼──────────┐
                      │   Nginx Load       │
                      │   Balancer         │
                      └─────────┬──────────┘
                                │
┌─────────────────────── Backend Layer ──────────────────────┐
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Python API Gateway                         ││
│  │  • FastAPI Request Routing                             ││
│  │  • Authentication & Authorization                      ││
│  │  • Rate Limiting & Throttling                         ││
│  │  • Request Validation & Response Formatting           ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    User      │  │   Content    │  │    AI/ML     │      │
│  │   Service    │  │  Ingestion   │  │  Processing  │      │
│  │              │  │   Service    │  │   Service    │      │
│  │ • Auth API   │  │ • RSS/Feed   │  │ • Summary    │      │
│  │ • Profile    │  │ • Parsing    │  │ • Audio Gen  │      │
│  │ • Settings   │  │ • Dedup      │  │ • Priority   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │Notification  │  │  Analytics   │  │   Content    │      │
│  │   Service    │  │   Service    │  │  Delivery    │      │
│  │              │  │              │  │   Service    │      │
│  │ • Push API   │  │ • Events     │  │ • Feed Gen   │      │
│  │ • Email API  │  │ • Metrics    │  │ • Recommend  │      │
│  │ • SMS API    │  │ • Reports    │  │ • Personal   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────── Data Layer ─────────────────────────┐
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ PostgreSQL   │  │    Redis     │  │ File Storage │      │
│  │  (Docker)    │  │  (Docker)    │  │    (VPS)     │      │
│  │ • Users      │  │ • Cache      │  │ • Audio      │      │
│  │ • Content    │  │ • Sessions   │  │ • Images     │      │
│  │ • Embeddings │  │ • Queues     │  │ • Documents  │      │
│  │ • Analytics  │  │ • Rate Limit │  │ • Backups    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                                │
┌──────────────────── External Services ─────────────────────┐
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   LiteLLM    │  │    Coqui     │  │   Stripe     │      │
│  │ (Multi-LLM)  │  │     TTS      │  │  Payments    │      │
│  │   Provider   │  │ (Self-host)  │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  SMTP/SES    │  │  Plausible   │  │ Prometheus   │      │
│  │    Email     │  │  Analytics   │  │  Monitoring  │      │
│  │              │  │ (Self-host)  │  │   Grafana    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack Decisions and Justifications

### Frontend Technologies

#### React Native (Mobile Applications)
**Decision Rationale:**
- **Cross-platform development** reduces development time and maintenance overhead
- **Performance** near-native for content consumption use cases
- **Offline capabilities** through AsyncStorage and SQLite integration
- **Large ecosystem** with mature libraries for audio playback and content rendering

**Key Libraries:**
```javascript
{
  "react-native": "^0.76.1",
  "@react-native-async-storage/async-storage": "^2.1.0",
  "react-native-sqlite-2": "^3.7.0",
  "react-native-vector-icons": "^10.0.0",
  "@react-navigation/native": "^6.1.18"
}
```

#### React PWA (Web Application)
**Decision Rationale:**
- **Progressive Web App** capabilities for basic offline experience
- **Responsive design** works across desktop and mobile browsers
- **SEO optimization** for organic user acquisition
- **Simple deployment** on VPS with Nginx

**Key Technologies:**
```javascript
{
  "react": "^19.0.0",
  "next.js": "^15.1.2",
  "workbox-webpack-plugin": "^7.3.0",
  "@reduxjs/toolkit": "^2.4.0",
  "socket.io-client": "^4.8.1"
}
```

### Backend Technologies

#### Python with FastAPI (All Backend Services)
**Decision Rationale:**
- **Unified technology stack** reduces complexity and maintenance overhead
- **FastAPI performance** with async support for high concurrency
- **AI/ML ecosystem** natively integrated with content processing
- **Type safety** with Pydantic models reduces bugs across all services

**Architecture Pattern:**
```python
# Service structure
/services
  /user_service          # Authentication, profiles, preferences
  /content_service       # RSS ingestion and processing
  /ai_service           # Content summarization and AI processing
  /api_gateway          # Request routing and auth
```

#### Core Dependencies and Libraries
**FastAPI Ecosystem:**
- **FastAPI** for high-performance API development
- **Uvicorn** for ASGI server implementation
- **SQLAlchemy** for database ORM with PostgreSQL
- **Celery** for background job processing
- **Redis** for caching and job queues

**AI/ML Stack:**
```python
# Core dependencies
fastapi==0.115.6
uvicorn==0.32.1
litellm==1.57.7
celery==5.4.0
redis==5.2.1
psycopg[binary]==3.2.3
pgvector==0.3.6
feedparser==6.0.10
requests==2.31.0
```

**Docker Compose Database Setup:**
```bash
# Database management commands
# Start database services
docker-compose up -d postgres redis

# View logs
docker-compose logs -f postgres
docker-compose logs -f redis

# Backup database
docker-compose exec postgres pg_dump -U app_user newsletter_app > backup.sql

# Restore database
docker-compose exec -T postgres psql -U app_user -d newsletter_app < backup.sql

# Monitor resources
docker-compose stats
```

**Database Initialization Script:**
```sql
-- init.sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Create application user and database
CREATE USER app_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE newsletter_app TO app_user;

-- Enable vector operations
ALTER DATABASE newsletter_app SET shared_preload_libraries = 'vector';
```

### Database Architecture

#### PostgreSQL (Primary Relational Data)
**Use Cases:**
- User accounts, profiles, and authentication
- Subscription management and billing
- Source configurations and user preferences
- Relationship data requiring ACID compliance

**Schema Design:**
```sql
-- Core tables
users (id, email, created_at, subscription_tier)
user_profiles (user_id, preferences, settings)
sources (id, name, type, url, active)
user_sources (user_id, source_id, priority, created_at)
subscriptions (user_id, plan_id, status, billing_cycle)
```

#### PostgreSQL with pgvector (Unified Data Storage)
**Use Cases:**
- All relational data (users, subscriptions, etc.)
- RSS feed articles and content
- AI-generated summaries and metadata
- Vector embeddings for similarity search
- Analytics and metrics data

**Content Table Structure:**
```sql
-- Content storage with JSON and vector support
CREATE TABLE content (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    type VARCHAR(20) NOT NULL, -- 'rss' or 'newsletter'
    title TEXT NOT NULL,
    original_content TEXT,
    ai_summary JSONB, -- {
                      --   "text": "...",
                      --   "keyPoints": [...],
                      --   "sentiment": "...",
                      --   "priority": 5
                      -- }
    metadata JSONB,   -- {
                      --   "publishedAt": "2024-01-01",
                      --   "readTime": 300,
                      --   "tags": [...],
                      --   "sourceUrl": "..."
                      -- }
    embedding vector(1536), -- OpenAI ada-002 embeddings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- Vector similarity index for fast semantic search
CREATE INDEX ON content USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

#### Redis (Caching and Sessions)
**Use Cases:**
- Session management and user authentication tokens
- Content feed caching for performance
- Rate limiting and request throttling
- Background job queues for processing

#### Vector Search with pgvector
**Use Cases:**
- Content similarity search and recommendations
- Semantic search across summaries
- Duplicate content detection
- Cross-content relationship mapping
- Native SQL queries with vector operations

**Vector Operations:**
```sql
-- Similarity search example
SELECT id, title, ai_summary->>'text' as summary,
       1 - (embedding <=> $1::vector) as similarity
FROM content 
WHERE 1 - (embedding <=> $1::vector) > 0.8
ORDER BY embedding <=> $1::vector
LIMIT 10;

-- Hybrid search (text + vector)
SELECT c.*, 
       ts_rank(to_tsvector('english', title || ' ' || (ai_summary->>'text')), 
               plainto_tsquery('english', $1)) as text_rank,
       1 - (embedding <=> $2::vector) as vector_similarity
FROM content c
WHERE to_tsvector('english', title || ' ' || (ai_summary->>'text')) 
      @@ plainto_tsquery('english', $1)
   OR 1 - (embedding <=> $2::vector) > 0.7
ORDER BY (text_rank * 0.3 + vector_similarity * 0.7) DESC;
```

### External Service Integrations

#### AI and Machine Learning Services

**LiteLLM Integration (Multiple LLM Providers)**
```python
# Summarization pipeline with LiteLLM
import litellm

async def generate_summary(content: str) -> Summary:
    # LiteLLM supports multiple providers: OpenAI, Anthropic, Cohere, etc.
    response = await litellm.acompletion(
        model="gpt-4o-mini",  # Falls back to other providers if needed
        messages=[
            {"role": "system", "content": SUMMARIZATION_PROMPT},
            {"role": "user", "content": content}
        ],
        max_tokens=500,
        temperature=0.3,
        fallbacks=["claude-3-haiku", "gemini-pro"]  # Provider redundancy
    )
    return parse_summary(response.choices[0].message.content)
```

**Vector Search and Embeddings**
```python
# Semantic search and content similarity with pgvector
import litellm
from pgvector.sqlalchemy import Vector

class ContentProcessor:
    def __init__(self):
        self.llm_client = litellm

    async def generate_embeddings(self, text: str) -> list[float]:
        # Generate embeddings for semantic search
        response = await litellm.aembedding(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

    async def find_similar_content(self, query_embedding: list[float], limit: int = 10):
        # Find semantically similar content using pgvector
        # Implementation would use SQLAlchemy with vector similarity search
        pass
```

## Database Schema and Data Flow Diagrams

### Core Database Schema

```sql
-- User Management Schema
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    oauth_provider VARCHAR(50),
    oauth_id VARCHAR(255),
    subscription_tier VARCHAR(20) DEFAULT 'free',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_profiles (
    user_id INTEGER REFERENCES users(id),
    display_name VARCHAR(100),
    preferences JSONB,
    notification_settings JSONB,
    consumption_preferences JSONB, -- text vs audio preferences
    PRIMARY KEY (user_id)
);

-- Content Source Management
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL, -- 'rss' or 'newsletter'
    url VARCHAR(500) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    active BOOLEAN DEFAULT true,
    crawl_frequency INTEGER DEFAULT 3600, -- seconds
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_sources (
    user_id INTEGER REFERENCES users(id),
    source_id INTEGER REFERENCES sources(id),
    priority INTEGER DEFAULT 5, -- 1-10 scale
    custom_source BOOLEAN DEFAULT false,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, source_id)
);

-- Subscription and Billing
CREATE TABLE subscription_plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    price_monthly DECIMAL(10,2),
    price_annual DECIMAL(10,2),
    features JSONB,
    active BOOLEAN DEFAULT true
);

CREATE TABLE user_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    plan_id INTEGER REFERENCES subscription_plans(id),
    payment_provider VARCHAR(50), -- stripe, paypal, etc.
    external_subscription_id VARCHAR(255),
    status VARCHAR(20),
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Content table (defined above)
CREATE TABLE content (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    type VARCHAR(20) NOT NULL,
    title TEXT NOT NULL,
    original_content TEXT,
    ai_summary JSONB,
    metadata JSONB,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- User Activity Tracking
CREATE TABLE user_actions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    content_id INTEGER REFERENCES content(id),
    action_type VARCHAR(50), -- 'view', 'save', 'share', 'dismiss'
    consumption_mode VARCHAR(10), -- 'text' or 'audio'
    session_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analytics and Metrics
CREATE TABLE content_metrics (
    content_id INTEGER PRIMARY KEY REFERENCES content(id),
    view_count INTEGER DEFAULT 0,
    save_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    avg_rating DECIMAL(3,2),
    text_consumption_count INTEGER DEFAULT 0,
    audio_consumption_count INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Data Flow Architecture

#### Content Ingestion Flow
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Content       │    │   Content        │    │   AI/ML         │
│   Sources       │───▶│   Ingestion      │───▶│   Processing    │
│                 │    │   Service        │    │   Service       │
│ • RSS Feeds     │    │                  │    │                 │
│ • Newsletter    │    │ • Fetch Content  │    │ • Generate      │
│   APIs          │    │ • Parse & Clean  │    │   Summary       │
│ • Web Scraping  │    │ • Deduplication  │    │ • Create Audio  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │                  │    │ Local Storage   │
│  (+ pgvector)   │    │                  │    │     (VPS)       │
│ • Raw Content   │    │                  │    │ • Audio Files   │
│ • Metadata      │    │                  │    │ • Images        │
│ • AI Summaries  │    │                  │    │ • Documents     │
│ • Embeddings    │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

#### User Content Delivery Flow
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client        │    │   API Gateway    │    │   Content       │
│   Application   │───▶│                  │───▶│   Delivery      │
│                 │    │ • Authentication │    │   Service       │
│ • Mobile App    │    │ • Rate Limiting  │    │                 │
│ • Web App       │    │ • Request        │    │ • Personalize   │
│ • PWA           │    │   Routing        │    │ • Prioritize    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Redis Cache   │    │   PostgreSQL     │    │                 │
│                 │    │  (+ pgvector)    │    │                 │
│ • Feed Cache    │    │ • User Prefs     │    │ • Content       │
│ • Session Data  │    │ • Subscriptions  │    │ • Summaries     │
│ • Rate Limits   │    │ • Activity       │    │ • Embeddings    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Integration Patterns and External Dependencies

### Authentication and Authorization Flow

```javascript
// OAuth Integration Pattern
class AuthenticationService {
  async authenticateWithOAuth(provider, code) {
    // Exchange code for tokens
    const tokens = await this.exchangeCodeForTokens(provider, code);
    
    // Fetch user profile from provider
    const profile = await this.fetchUserProfile(provider, tokens.access_token);
    
    // Create or update user in database
    const user = await this.upsertUser({
      email: profile.email,
      name: profile.name,
      oauth_provider: provider,
      oauth_id: profile.id
    });
    
    // Generate JWT token
    const jwt = await this.generateJWT(user);
    
    return { user, token: jwt };
  }
}
```

### Content Processing Pipeline

```python
# Async content processing workflow
class ContentProcessor:
    def __init__(self):
        self.llm_client = litellm  # Multi-provider LLM client
        self.feed_processor = FeedProcessor()  # RSS feed processing
        self.vector_db = PostgreSQLVector()  # PostgreSQL with pgvector
    
    async def process_content(self, raw_content):
        # Generate text summary
        summary = await self.generate_summary(raw_content)
        
        # Create embeddings for similarity search
        embeddings = await self.generate_embeddings(summary.text)
        
        # Store in database
        content_doc = {
            'original': raw_content,
            'summary': summary,
            'embeddings': embeddings,
            'processed_at': datetime.utcnow()
        }
        
        await self.store_content_with_embeddings(content_doc, embeddings)
        
        return content_doc
```

### Real-time Notification System

```javascript
// WebSocket-based real-time updates
class NotificationService {
  constructor() {
    this.io = new SocketIO.Server();
    this.redisClient = new Redis();
  }
  
  async notifyUserOfNewContent(userId, content) {
    // Check user preferences
    const preferences = await this.getUserNotificationPreferences(userId);
    
    if (preferences.realtime_enabled) {
      // Send WebSocket notification
      this.io.to(`user_${userId}`).emit('new_content', {
        id: content.id,
        title: content.title,
        summary: content.summary.text,
        priority: content.priority,
        priority: content.priority
      });
    }
    
    // Queue email/push notifications based on preferences
    if (preferences.email_enabled) {
      await this.queueEmailNotification(userId, content);
    }
    
    if (preferences.push_enabled) {
      await this.queuePushNotification(userId, content);
    }
  }
}
```

## Scalability and Performance Considerations

### VPS Deployment and Scaling Strategy

#### Infrastructure Overview
```
VPS Infrastructure (Single-server MVP setup)
┌─────────────────────────────────────────────────────────────┐
│                    VPS-1 (All Services)                    │
│                                                             │
│ • Nginx (Load Balancer & Static Files)                     │
│ • Node.js API Services                                      │
│ • Python AI/ML Services                                     │
│ • PostgreSQL (Docker)                                       │
│ • Redis (Docker)                                            │
│ • LiteLLM Integration                                       │
│ • SSL/Certs & Monitoring                                    │
└─────────────────────────────────────────────────────────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                    ┌─────────────────┐
                    │ Future Scaling  │
                    │                 │
                    │ • Separate DB   │
                    │ • Monitor VPS   │
                    │ • CDN/Cache     │
                    └─────────────────┘
```

#### Direct VPS Deployment
**Service Management:**
```bash
# Traditional service deployment on VPS
# Using systemd for service management

# Example systemd service file: /etc/systemd/system/content-delivery.service
[Unit]
Description=Content Delivery Service
After=network.target postgresql.service

[Service]
Type=simple
User=app
WorkingDirectory=/opt/newsletter-app/services/content-delivery
ExecStart=/opt/newsletter-app/venv/bin/python server.py
Restart=always
RestartSec=10
Environment=POSTGRES_URI_FILE=/etc/newsletter-app/secrets/postgres-uri
Environment=LITELLM_API_KEY_FILE=/etc/newsletter-app/secrets/litellm-api-key

[Install]
WantedBy=multi-user.target
```

**Load Balancer Configuration:**
```nginx
# /etc/nginx/sites-available/newsletter-app
upstream content_delivery {
    server 127.0.0.1:3001;
    server 127.0.0.1:3002;
    server 127.0.0.1:3003;
}

server {
    listen 80;
    listen 443 ssl;
    server_name app.example.com;
    
    location /api/ {
        proxy_pass http://content_delivery;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location / {
        root /opt/newsletter-app/static;
        try_files $uri $uri/ @react;
    }
    
    location @react {
        proxy_pass http://127.0.0.1:3000;
    }
}
```

#### Database Scaling Patterns

**PostgreSQL Scaling with Docker:**
- **Read Replicas** using Docker Compose multi-container setup
- **Connection Pooling** with PgBouncer container
- **Partitioning** for content, user_actions and metrics tables by date
- **Vector Index Optimization** with IVFFlat for large datasets
- **Docker Volume Management** for data persistence and backups
- **Container Health Checks** for automatic restart on failure
- **JSONB Indexing** for fast metadata and summary queries

**Docker Compose Scaling Example:**
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  postgres-primary:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_REPLICATION_MODE: master
      POSTGRES_REPLICATION_USER: replicator
    volumes:
      - postgres_primary:/var/lib/postgresql/data
  
  postgres-replica:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_REPLICATION_MODE: slave
      POSTGRES_MASTER_HOST: postgres-primary
    depends_on:
      - postgres-primary
  
  pgbouncer:
    image: pgbouncer/pgbouncer:latest
    environment:
      POOL_MODE: transaction
      SERVER_RESET_QUERY: DISCARD ALL
    depends_on:
      - postgres-primary
```

```sql
-- PostgreSQL indexing strategy
-- Partition tables by date for better performance
CREATE TABLE content_y2024m01 PARTITION OF content
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Composite indexes for common queries
CREATE INDEX idx_content_type_date ON content (type, created_at DESC);
CREATE INDEX idx_content_source_date ON content (source_id, created_at DESC);
CREATE INDEX idx_content_priority ON content ((ai_summary->>'priority')::int DESC, created_at DESC);

-- JSONB GIN indexes for metadata queries
CREATE INDEX idx_content_metadata_gin ON content USING gin (metadata);
CREATE INDEX idx_content_summary_gin ON content USING gin (ai_summary);

-- Full-text search index
CREATE INDEX idx_content_fts ON content USING gin (
    to_tsvector('english', title || ' ' || coalesce(original_content, '') || ' ' || (ai_summary->>'text'))
);

-- Vector similarity index (already defined above)
CREATE INDEX idx_content_embedding_cosine ON content USING ivfflat (embedding vector_cosine_ops);
```
```

### Performance Optimization

#### Content Delivery Optimization
```javascript
// Multi-level caching strategy
class ContentCache {
  constructor() {
    this.l1Cache = new NodeCache({ stdTTL: 300 }); // 5 minutes
    this.l2Cache = new Redis({ ttl: 3600 }); // 1 hour
    this.staticCache = new NginxCache({ ttl: 86400 }); // 24 hours
  }
  
  async getContent(userId, contentId) {
    // L1: In-memory cache
    let content = this.l1Cache.get(`${userId}:${contentId}`);
    if (content) return content;
    
    // L2: Redis cache
    content = await this.l2Cache.get(`${userId}:${contentId}`);
    if (content) {
      this.l1Cache.set(`${userId}:${contentId}`, content);
      return content;
    }
    
    // L3: Database with CDN for static assets
    content = await this.fetchFromDatabase(contentId);
    
    // Populate caches
    await this.l2Cache.set(`${userId}:${contentId}`, content);
    this.l1Cache.set(`${userId}:${contentId}`, content);
    
    return content;
  }
}
```

#### Audio Content Optimization
```python
# Audio processing and delivery optimization
class AudioOptimizer:
    def __init__(self):
        self.compression_settings = {
            'mobile': {'bitrate': '64k', 'format': 'mp3'},
            'desktop': {'bitrate': '128k', 'format': 'mp3'},
            'premium': {'bitrate': '256k', 'format': 'flac'}
        }
    
    async def optimize_audio_for_delivery(self, audio_file, user_device, subscription_tier):
        settings = self.compression_settings.get(
            subscription_tier if subscription_tier == 'premium' else user_device
        )
        
        # Process audio with optimal settings
        optimized_audio = await self.compress_audio(audio_file, settings)
        
        # Store locally and serve via Nginx
        local_urls = await self.store_audio_locally(optimized_audio)
        
        return local_urls
```

### Load Testing and Monitoring

#### Performance Benchmarks
```javascript
// Load testing configuration
const loadTestConfig = {
  scenarios: {
    content_fetch: {
      executor: 'ramping-vus',
      startVUs: 10,
      stages: [
        { duration: '5m', target: 100 },
        { duration: '10m', target: 500 },
        { duration: '5m', target: 1000 },
        { duration: '10m', target: 1000 },
        { duration: '5m', target: 0 }
      ]
    }
  },
  thresholds: {
    http_req_duration: ['p(95)<200'], // 95% of requests under 200ms
    http_req_failed: ['rate<0.01'],   // Error rate under 1%
  }
};
```

#### Monitoring and Alerting
```yaml
# Prometheus + Grafana monitoring configuration
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'content-delivery'
    static_configs:
      - targets: ['content-delivery:3000']
    metrics_path: '/metrics'
  
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

rule_files:
  - "alert_rules.yml"

# alert_rules.yml
groups:
  - name: api_alerts
    rules:
      - alert: HighResponseTime
        expr: http_request_duration_seconds{quantile="0.95"} > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API response time is high"
      
      - alert: DatabaseConnectionsHigh
        expr: postgresql_connections_used / postgresql_connections_max > 0.8
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool utilization is above 80%"
```

This hybrid technical architecture provides a robust foundation for Updater, ensuring scalability, performance, and reliability while maintaining complete data sovereignty. The architecture uses Docker Compose for database services (PostgreSQL + Redis) to ensure consistency and easy management, while application services run directly on the VPS using systemd for better performance and debugging capabilities.

*[Cross-references: See PRD.md for business requirements, personas.md for user context, and interactions/ for user experience specifications]*