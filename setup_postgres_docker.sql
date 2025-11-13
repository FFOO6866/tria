-- TRIA AI-BPO Conversation Tables
-- Manual creation to fix DataFlow migration issues
-- Date: 2025-10-23

-- Drop existing tables if any (be careful in production!)
DROP TABLE IF EXISTS conversation_messages CASCADE;
DROP TABLE IF EXISTS conversation_sessions CASCADE;
DROP TABLE IF EXISTS user_interaction_summary CASCADE;

-- ============================================================================
-- CONVERSATION SESSIONS TABLE
-- ============================================================================
CREATE TABLE conversation_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255),
    outlet_id INTEGER,
    language VARCHAR(10) DEFAULT 'en',
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    intents JSONB DEFAULT '{}',
    context JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_sessions_session_id ON conversation_sessions(session_id);
CREATE INDEX idx_sessions_user_id ON conversation_sessions(user_id);
CREATE INDEX idx_sessions_outlet_id ON conversation_sessions(outlet_id);
CREATE INDEX idx_sessions_start_time ON conversation_sessions(start_time);
CREATE INDEX idx_sessions_created_at ON conversation_sessions(created_at);

-- ============================================================================
-- CONVERSATION MESSAGES TABLE
-- ============================================================================
CREATE TABLE conversation_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    language VARCHAR(10) DEFAULT 'en',
    intent VARCHAR(100),
    confidence FLOAT DEFAULT 0.0,
    context JSONB DEFAULT '{}',
    pii_detected BOOLEAN DEFAULT FALSE,
    pii_scrubbed BOOLEAN DEFAULT FALSE,
    pii_categories JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_messages_session_id ON conversation_messages(session_id);
CREATE INDEX idx_messages_role ON conversation_messages(role);
CREATE INDEX idx_messages_intent ON conversation_messages(intent);
CREATE INDEX idx_messages_created_at ON conversation_messages(created_at);
CREATE INDEX idx_messages_pii_detected ON conversation_messages(pii_detected);

-- ============================================================================
-- USER INTERACTION SUMMARY TABLE
-- ============================================================================
CREATE TABLE user_interaction_summary (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    outlet_id INTEGER,
    total_sessions INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    primary_language VARCHAR(10) DEFAULT 'en',
    intents JSONB DEFAULT '{}',
    last_interaction TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_summary_user_id ON user_interaction_summary(user_id);
CREATE INDEX idx_summary_outlet_id ON user_interaction_summary(outlet_id);
CREATE INDEX idx_summary_last_interaction ON user_interaction_summary(last_interaction);

-- Grant permissions (adjust as needed)
-- GRANT ALL PRIVILEGES ON TABLE conversation_sessions TO horme_user;
-- GRANT ALL PRIVILEGES ON TABLE conversation_messages TO horme_user;
-- GRANT ALL PRIVILEGES ON TABLE user_interaction_summary TO horme_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO horme_user;

-- Verify tables created
SELECT 'conversation_sessions' as table_name, count(*) as row_count FROM conversation_sessions
UNION ALL
SELECT 'conversation_messages', count(*) FROM conversation_messages
UNION ALL
SELECT 'user_interaction_summary', count(*) FROM user_interaction_summary;
