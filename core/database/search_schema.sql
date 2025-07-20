-- Search Service Database Schema for dev schema
-- Creates tables needed for the unified search service

-- Unified search embeddings table
CREATE TABLE IF NOT EXISTS dev.mcp_unified_search_embeddings (
    id SERIAL PRIMARY KEY,
    item_name TEXT NOT NULL UNIQUE,
    item_type TEXT NOT NULL CHECK (item_type IN ('tool', 'prompt', 'resource')),
    category TEXT NOT NULL,
    description TEXT,
    embedding VECTOR(1536), -- OpenAI text-embedding-3-small dimension
    keywords TEXT[], 
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Search history for analytics
CREATE TABLE IF NOT EXISTS dev.mcp_search_history (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    filters JSONB,
    results_count INTEGER,
    top_results TEXT[],
    result_types TEXT[],
    user_id TEXT,
    session_id TEXT,
    response_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_mcp_unified_search_embeddings_type ON dev.mcp_unified_search_embeddings(item_type);
CREATE INDEX IF NOT EXISTS idx_mcp_unified_search_embeddings_category ON dev.mcp_unified_search_embeddings(category);
CREATE INDEX IF NOT EXISTS idx_mcp_unified_search_embeddings_name ON dev.mcp_unified_search_embeddings(item_name);
CREATE INDEX IF NOT EXISTS idx_mcp_unified_search_embeddings_updated ON dev.mcp_unified_search_embeddings(updated_at);

CREATE INDEX IF NOT EXISTS idx_mcp_search_history_query ON dev.mcp_search_history(query);
CREATE INDEX IF NOT EXISTS idx_mcp_search_history_user ON dev.mcp_search_history(user_id);
CREATE INDEX IF NOT EXISTS idx_mcp_search_history_created ON dev.mcp_search_history(created_at);

-- Vector similarity index (requires pgvector extension)
CREATE INDEX IF NOT EXISTS idx_mcp_unified_search_embeddings_vector 
    ON dev.mcp_unified_search_embeddings 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_mcp_unified_search_embeddings_updated_at 
    BEFORE UPDATE ON dev.mcp_unified_search_embeddings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- View for search analytics
CREATE OR REPLACE VIEW dev.mcp_search_analytics AS
SELECT 
    DATE_TRUNC('day', created_at) as date,
    COUNT(*) as total_searches,
    COUNT(DISTINCT user_id) as unique_users,
    AVG(results_count) as avg_results_count,
    AVG(response_time_ms) as avg_response_time_ms,
    MODE() WITHIN GROUP (ORDER BY query) as most_common_query
FROM dev.mcp_search_history 
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date DESC;