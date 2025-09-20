-- Updater - Complete Database Schema
-- Week 3-4: User Management System

-- =====================================================
-- EXTENSIONS AND SETUP
-- =====================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =====================================================
-- USER MANAGEMENT TABLES
-- =====================================================

-- Core users table with authentication
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255), -- NULL for OAuth-only users
    oauth_provider VARCHAR(50), -- 'google', 'github', 'linkedin', etc.
    oauth_id VARCHAR(255),
    subscription_tier VARCHAR(20) DEFAULT 'free' CHECK (subscription_tier IN ('free', 'premium', 'admin')),
    email_verified BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    
    -- Ensure OAuth users have valid provider + ID
    CONSTRAINT oauth_check CHECK (
        (oauth_provider IS NULL AND oauth_id IS NULL) OR 
        (oauth_provider IS NOT NULL AND oauth_id IS NOT NULL)
    )
);

-- User profiles with preferences and settings
CREATE TABLE user_profiles (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    display_name VARCHAR(100),
    avatar_url VARCHAR(500),
    bio TEXT,
    timezone VARCHAR(50) DEFAULT 'UTC',
    language VARCHAR(10) DEFAULT 'en',
    
    -- User preferences as JSONB
    preferences JSONB DEFAULT '{
        "email_notifications": true,
        "push_notifications": true,
        "digest_frequency": "daily",
        "digest_time": "08:00",
        "content_format": "summary",
        "audio_enabled": false
    }'::jsonb,
    
    -- Notification settings
    notification_settings JSONB DEFAULT '{
        "breaking_news": true,
        "daily_digest": true,
        "weekly_roundup": false,
        "source_updates": true,
        "quiet_hours": {
            "enabled": false,
            "start": "22:00",
            "end": "07:00"
        }
    }'::jsonb,
    
    -- Content consumption preferences
    consumption_preferences JSONB DEFAULT '{
        "reading_speed": "normal",
        "summary_length": "medium",
        "show_images": true,
        "auto_play_audio": false,
        "offline_download": true,
        "dark_mode": false
    }'::jsonb,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (user_id)
);

-- User sessions for JWT token management
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    device_info JSONB DEFAULT '{}', -- User agent, IP, device type
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Email verification tokens
CREATE TABLE email_verification_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Password reset tokens
CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- CONTENT SOURCES AND MANAGEMENT
-- =====================================================

-- Available content sources (newsletters, podcasts, etc.)
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(20) NOT NULL CHECK (type IN ('newsletter', 'podcast', 'blog', 'news')),
    url VARCHAR(500) NOT NULL,
    feed_url VARCHAR(500), -- RSS/Atom feed URL
    website_url VARCHAR(500), -- Main website URL
    logo_url VARCHAR(500),
    category VARCHAR(100),
    language VARCHAR(10) DEFAULT 'en',
    
    -- Source metadata
    metadata JSONB DEFAULT '{}', -- Publisher info, frequency, etc.
    
    -- Source status and configuration
    is_active BOOLEAN DEFAULT true,
    is_featured BOOLEAN DEFAULT false,
    crawl_frequency INTEGER DEFAULT 3600, -- seconds between crawls
    
    -- Statistics
    subscriber_count INTEGER DEFAULT 0,
    content_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_crawled_at TIMESTAMP
);

-- User subscriptions to sources
CREATE TABLE user_sources (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    source_id INTEGER REFERENCES sources(id) ON DELETE CASCADE,
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10), -- 1=highest, 10=lowest
    is_active BOOLEAN DEFAULT true,
    custom_settings JSONB DEFAULT '{}', -- Per-source user preferences
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (user_id, source_id)
);

-- =====================================================
-- CONTENT STORAGE (PREPARED FOR PHASE 2)
-- =====================================================

-- Content items (newsletters, podcast episodes, etc.)
CREATE TABLE content (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id) ON DELETE CASCADE,
    external_id VARCHAR(255), -- ID from original source
    type VARCHAR(20) NOT NULL CHECK (type IN ('newsletter', 'podcast', 'article', 'video')),
    
    -- Basic content info
    title TEXT NOT NULL,
    description TEXT,
    url VARCHAR(500),
    content_text TEXT, -- Full text content
    content_html TEXT, -- Original HTML
    
    -- AI-generated content (for Phase 2)
    ai_summary JSONB, -- Will contain: {text, audio_url, key_points, sentiment, priority}
    
    -- Content metadata
    metadata JSONB DEFAULT '{}', -- Author, publish_date, tags, etc.
    
    -- Vector embedding for similarity search (Phase 2)
    embedding vector(1536), -- OpenAI ada-002 embeddings
    
    -- Status and timestamps
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    published_at TIMESTAMP,
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure external_id is unique per source
    UNIQUE(source_id, external_id)
);

-- =====================================================
-- USER ACTIVITY AND ANALYTICS
-- =====================================================

-- User actions and interactions
CREATE TABLE user_actions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    content_id INTEGER REFERENCES content(id) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL CHECK (action_type IN (
        'view', 'read', 'save', 'unsave', 'share', 'dismiss', 
        'like', 'dislike', 'play_audio', 'download'
    )),
    consumption_mode VARCHAR(10) CHECK (consumption_mode IN ('text', 'audio')),
    
    -- Action metadata
    metadata JSONB DEFAULT '{}', -- Duration, completion %, device, etc.
    session_id UUID, -- Link to user_sessions
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User saved content (bookmarks)
CREATE TABLE user_saved_content (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    content_id INTEGER REFERENCES content(id) ON DELETE CASCADE,
    folder VARCHAR(100) DEFAULT 'default',
    notes TEXT,
    tags TEXT[], -- Array of user-defined tags
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (user_id, content_id)
);

-- Content performance metrics
CREATE TABLE content_metrics (
    content_id INTEGER PRIMARY KEY REFERENCES content(id) ON DELETE CASCADE,
    view_count INTEGER DEFAULT 0,
    read_count INTEGER DEFAULT 0,
    save_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    dislike_count INTEGER DEFAULT 0,
    
    -- Consumption metrics
    text_consumption_count INTEGER DEFAULT 0,
    audio_consumption_count INTEGER DEFAULT 0,
    avg_read_time INTEGER DEFAULT 0, -- seconds
    avg_completion_rate DECIMAL(5,2) DEFAULT 0, -- percentage
    
    -- Quality metrics
    avg_rating DECIMAL(3,2),
    engagement_score DECIMAL(5,2) DEFAULT 0,
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- SUBSCRIPTION AND BILLING (PREPARED FOR PHASE 4)
-- =====================================================

-- Subscription plans
CREATE TABLE subscription_plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    price_monthly DECIMAL(10,2),
    price_annual DECIMAL(10,2),
    
    -- Plan features as JSONB
    features JSONB DEFAULT '{}',
    
    -- Plan limits
    max_sources INTEGER,
    max_content_per_day INTEGER,
    audio_summaries_included BOOLEAN DEFAULT false,
    api_access BOOLEAN DEFAULT false,
    
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User subscriptions
CREATE TABLE user_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    plan_id INTEGER REFERENCES subscription_plans(id),
    
    -- Payment provider info
    payment_provider VARCHAR(50), -- 'stripe', 'paypal', etc.
    external_subscription_id VARCHAR(255),
    
    -- Subscription status
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN (
        'active', 'canceled', 'past_due', 'paused', 'expired'
    )),
    
    -- Billing periods
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- SYSTEM TABLES
-- =====================================================

-- System configuration
CREATE TABLE system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API rate limiting
CREATE TABLE rate_limits (
    id SERIAL PRIMARY KEY,
    identifier VARCHAR(255) NOT NULL, -- IP address or user ID
    endpoint VARCHAR(255) NOT NULL,
    requests_count INTEGER DEFAULT 1,
    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(identifier, endpoint)
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- User indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_id);
CREATE INDEX idx_users_subscription ON users(subscription_tier);
CREATE INDEX idx_users_active ON users(is_active, created_at);

-- User profile indexes
CREATE INDEX idx_user_profiles_preferences ON user_profiles USING gin(preferences);
CREATE INDEX idx_user_profiles_notifications ON user_profiles USING gin(notification_settings);

-- Session indexes
CREATE INDEX idx_user_sessions_user ON user_sessions(user_id, is_active);
CREATE INDEX idx_user_sessions_token ON user_sessions(refresh_token_hash);
CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);

-- Source indexes
CREATE INDEX idx_sources_type ON sources(type, is_active);
CREATE INDEX idx_sources_category ON sources(category, is_active);
CREATE INDEX idx_sources_featured ON sources(is_featured, is_active);
CREATE INDEX idx_sources_language ON sources(language);

-- User sources indexes
CREATE INDEX idx_user_sources_user ON user_sources(user_id, is_active);
CREATE INDEX idx_user_sources_priority ON user_sources(user_id, priority, is_active);

-- Content indexes
CREATE INDEX idx_content_source ON content(source_id, status);
CREATE INDEX idx_content_type ON content(type, status);
CREATE INDEX idx_content_published ON content(published_at DESC);
CREATE INDEX idx_content_status ON content(status, created_at);
CREATE INDEX idx_content_metadata ON content USING gin(metadata);

-- Content full-text search index (prepared for Phase 2)
CREATE INDEX idx_content_search ON content USING gin(
    to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, '') || ' ' || coalesce(content_text, ''))
);

-- Vector similarity index (prepared for Phase 2)
-- CREATE INDEX idx_content_embedding ON content USING ivfflat (embedding vector_cosine_ops);

-- User activity indexes
CREATE INDEX idx_user_actions_user ON user_actions(user_id, created_at DESC);
CREATE INDEX idx_user_actions_content ON user_actions(content_id, action_type);
CREATE INDEX idx_user_actions_session ON user_actions(session_id);

-- Saved content indexes
CREATE INDEX idx_user_saved_content_user ON user_saved_content(user_id, saved_at DESC);
CREATE INDEX idx_user_saved_content_folder ON user_saved_content(user_id, folder);
CREATE INDEX idx_user_saved_content_tags ON user_saved_content USING gin(tags);

-- Rate limiting indexes
CREATE INDEX idx_rate_limits_identifier ON rate_limits(identifier, window_start);

-- =====================================================
-- FUNCTIONS AND TRIGGERS
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sources_updated_at BEFORE UPDATE ON sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_content_updated_at BEFORE UPDATE ON content
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_subscriptions_updated_at BEFORE UPDATE ON user_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to update content metrics
CREATE OR REPLACE FUNCTION update_content_metrics()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO content_metrics (content_id) 
    VALUES (NEW.content_id)
    ON CONFLICT (content_id) DO NOTHING;
    
    -- Update counters based on action type
    UPDATE content_metrics 
    SET 
        view_count = CASE WHEN NEW.action_type = 'view' THEN view_count + 1 ELSE view_count END,
        read_count = CASE WHEN NEW.action_type = 'read' THEN read_count + 1 ELSE read_count END,
        save_count = CASE WHEN NEW.action_type = 'save' THEN save_count + 1 
                          WHEN NEW.action_type = 'unsave' THEN save_count - 1 
                          ELSE save_count END,
        share_count = CASE WHEN NEW.action_type = 'share' THEN share_count + 1 ELSE share_count END,
        like_count = CASE WHEN NEW.action_type = 'like' THEN like_count + 1 ELSE like_count END,
        dislike_count = CASE WHEN NEW.action_type = 'dislike' THEN dislike_count + 1 ELSE dislike_count END,
        text_consumption_count = CASE WHEN NEW.consumption_mode = 'text' THEN text_consumption_count + 1 ELSE text_consumption_count END,
        audio_consumption_count = CASE WHEN NEW.consumption_mode = 'audio' THEN audio_consumption_count + 1 ELSE audio_consumption_count END,
        updated_at = CURRENT_TIMESTAMP
    WHERE content_id = NEW.content_id;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to update content metrics on user actions
CREATE TRIGGER update_content_metrics_on_action 
    AFTER INSERT ON user_actions
    FOR EACH ROW EXECUTE FUNCTION update_content_metrics();

-- =====================================================
-- INITIAL DATA
-- =====================================================

-- Insert default subscription plans
INSERT INTO subscription_plans (name, description, price_monthly, price_annual, features, max_sources, max_content_per_day, audio_summaries_included) VALUES
('Free', 'Perfect for getting started', 0.00, 0.00, '{"ai_summaries": true, "basic_search": true}', 10, 50, false),
('Premium', 'For power users and professionals', 19.99, 199.99, '{"ai_summaries": true, "audio_summaries": true, "advanced_search": true, "custom_sources": true, "export": true}', 100, 500, true),
('Team', 'For teams and organizations', 49.99, 499.99, '{"ai_summaries": true, "audio_summaries": true, "advanced_search": true, "custom_sources": true, "export": true, "team_sharing": true, "admin_dashboard": true}', 500, 2000, true);

-- Insert system configuration
INSERT INTO system_config (key, value, description) VALUES
('app_version', '"1.0.0"', 'Current application version'),
('maintenance_mode', 'false', 'Whether the app is in maintenance mode'),
('registration_enabled', 'true', 'Whether new user registration is enabled'),
('email_verification_required', 'true', 'Whether email verification is required for new users'),
('max_sources_per_user_free', '10', 'Maximum sources for free users'),
('max_sources_per_user_premium', '100', 'Maximum sources for premium users');

-- Insert admin user
INSERT INTO users (email, subscription_tier, email_verified, is_active) 
VALUES ('admin@updater.com', 'admin', true, true)
ON CONFLICT (email) DO NOTHING;

-- Insert admin user profile
INSERT INTO user_profiles (user_id, display_name) 
SELECT id, 'Admin User' FROM users WHERE email = 'admin@updater.com'
ON CONFLICT (user_id) DO NOTHING;