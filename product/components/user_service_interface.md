# User Service Interface Document

## Service Overview

The User Service handles authentication, user profiles, preferences, and subscription management. It serves as the central authority for user identity and settings across the platform.

**Primary Functions:**
- User authentication and authorization
- Profile management
- Preference storage and retrieval
- Subscription tier management

## API Interface

### Authentication Endpoints

#### POST /api/auth/oauth
**Purpose:** Handle OAuth authentication flow
**Request:**
```json
{
  "provider": "google|github|twitter",
  "code": "string",
  "redirect_uri": "string"
}
```
**Response:**
```json
{
  "user": {
    "id": "integer",
    "email": "string",
    "display_name": "string",
    "subscription_tier": "free|premium|enterprise"
  },
  "token": "string",
  "expires_at": "timestamp"
}
```

#### POST /api/auth/refresh
**Purpose:** Refresh authentication token
**Request:**
```json
{
  "refresh_token": "string"
}
```
**Response:**
```json
{
  "token": "string",
  "expires_at": "timestamp"
}
```

#### DELETE /api/auth/logout
**Purpose:** Logout and invalidate tokens
**Headers:** `Authorization: Bearer {token}`
**Response:** `204 No Content`

### Profile Management Endpoints

#### GET /api/users/profile
**Purpose:** Retrieve user profile
**Headers:** `Authorization: Bearer {token}`
**Response:**
```json
{
  "id": "integer",
  "email": "string",
  "display_name": "string",
  "preferences": {
    "content_types": ["text", "audio"],
    "notification_frequency": "instant|daily|weekly",
    "theme": "light|dark|auto"
  },
  "notification_settings": {
    "email_enabled": "boolean",
    "push_enabled": "boolean",
    "realtime_enabled": "boolean"
  },
  "consumption_preferences": {
    "preferred_mode": "text|audio|both",
    "reading_speed": "integer",
    "audio_speed": "float"
  }
}
```

#### PUT /api/users/profile
**Purpose:** Update user profile
**Headers:** `Authorization: Bearer {token}`
**Request:**
```json
{
  "display_name": "string",
  "preferences": "object",
  "notification_settings": "object",
  "consumption_preferences": "object"
}
```
**Response:** Same as GET profile

#### GET /api/users/sources
**Purpose:** Get user's subscribed content sources
**Headers:** `Authorization: Bearer {token}`
**Response:**
```json
{
  "sources": [
    {
      "id": "integer",
      "name": "string",
      "type": "rss|newsletter",
      "url": "string",
      "priority": "integer",
      "custom_source": "boolean",
      "added_at": "timestamp"
    }
  ]
}
```

#### POST /api/users/sources
**Purpose:** Add content source to user's subscriptions
**Headers:** `Authorization: Bearer {token}`
**Request:**
```json
{
  "source_id": "integer",
  "priority": "integer"
}
```
**Response:**
```json
{
  "id": "integer",
  "user_id": "integer",
  "source_id": "integer",
  "priority": "integer",
  "added_at": "timestamp"
}
```

#### DELETE /api/users/sources/{source_id}
**Purpose:** Remove content source from user's subscriptions
**Headers:** `Authorization: Bearer {token}`
**Response:** `204 No Content`

### Subscription Management Endpoints

#### GET /api/users/subscription
**Purpose:** Get current subscription details
**Headers:** `Authorization: Bearer {token}`
**Response:**
```json
{
  "plan": {
    "id": "integer",
    "name": "string",
    "price_monthly": "decimal",
    "price_annual": "decimal",
    "features": "object"
  },
  "status": "active|canceled|past_due|unpaid",
  "current_period_start": "timestamp",
  "current_period_end": "timestamp",
  "payment_provider": "stripe|paypal"
}
```

#### POST /api/users/subscription/upgrade
**Purpose:** Upgrade subscription plan
**Headers:** `Authorization: Bearer {token}`
**Request:**
```json
{
  "plan_id": "integer",
  "payment_method": "string"
}
```
**Response:**
```json
{
  "checkout_url": "string",
  "session_id": "string"
}
```

## Database Access Interface

### Tables Used

#### Primary Tables
- **users**: Core user account information
- **user_profiles**: Extended profile data and preferences
- **user_sources**: User content source subscriptions
- **user_subscriptions**: Subscription and billing data
- **subscription_plans**: Available subscription tiers

#### Read Operations
```sql
-- Get user with profile
SELECT u.*, up.preferences, up.notification_settings, up.consumption_preferences
FROM users u
LEFT JOIN user_profiles up ON u.id = up.user_id
WHERE u.id = $1;

-- Get user sources with priorities
SELECT s.*, us.priority, us.added_at
FROM sources s
JOIN user_sources us ON s.id = us.source_id
WHERE us.user_id = $1
ORDER BY us.priority DESC, us.added_at DESC;

-- Get user subscription
SELECT us.*, sp.name, sp.features, sp.price_monthly, sp.price_annual
FROM user_subscriptions us
JOIN subscription_plans sp ON us.plan_id = sp.id
WHERE us.user_id = $1 AND us.status = 'active';
```

#### Write Operations
```sql
-- Create new user
INSERT INTO users (email, oauth_provider, oauth_id, subscription_tier)
VALUES ($1, $2, $3, 'free')
RETURNING id, email, subscription_tier, created_at;

-- Update user profile
INSERT INTO user_profiles (user_id, display_name, preferences, notification_settings, consumption_preferences)
VALUES ($1, $2, $3, $4, $5)
ON CONFLICT (user_id) 
DO UPDATE SET 
  display_name = EXCLUDED.display_name,
  preferences = EXCLUDED.preferences,
  notification_settings = EXCLUDED.notification_settings,
  consumption_preferences = EXCLUDED.consumption_preferences;

-- Add user source
INSERT INTO user_sources (user_id, source_id, priority)
VALUES ($1, $2, $3)
ON CONFLICT (user_id, source_id) 
DO UPDATE SET priority = EXCLUDED.priority;

-- Update subscription
UPDATE user_subscriptions 
SET status = $2, current_period_end = $3
WHERE user_id = $1 AND id = $4;
```

### Connection Requirements

**Database:** PostgreSQL with JSON support
**Connection Pool:** 10-50 connections depending on load
**Transactions:** Required for user creation and subscription changes
**Indexes:**
```sql
-- Performance indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_id);
CREATE INDEX idx_user_sources_user_id ON user_sources(user_id);
CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_status ON user_subscriptions(status);
```

## Dependencies

### Internal Services
- **Content Delivery Service**: For personalized content recommendations
- **Analytics Service**: For user behavior tracking

### External Services
- **OAuth Providers**: Google, GitHub, Twitter APIs
- **Payment Processors**: Stripe API for subscription management
- **Email Service**: SMTP/SES for transactional emails

### Configuration
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/newsletter_app
REDIS_URL=redis://localhost:6379
JWT_SECRET=secure_random_string
OAUTH_GOOGLE_CLIENT_ID=google_client_id
OAUTH_GOOGLE_CLIENT_SECRET=google_client_secret
STRIPE_SECRET_KEY=stripe_secret_key
STRIPE_WEBHOOK_SECRET=stripe_webhook_secret
```

## Performance Specifications

**Response Times:**
- Authentication: < 200ms
- Profile operations: < 100ms
- Source management: < 150ms

**Throughput:**
- 1000 concurrent users
- 100 req/sec per endpoint
- 10,000 daily active users

**Caching Strategy:**
- User profiles: Redis cache (1 hour TTL)
- Subscription data: Redis cache (15 minutes TTL)
- Source lists: Redis cache (30 minutes TTL)