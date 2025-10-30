-- Migration: Create MCP Prompts Table
-- Schema: mcp
-- Description: Stores MCP prompt templates and metadata

-- Create mcp schema if not exists
CREATE SCHEMA IF NOT EXISTS mcp;

-- Create prompts table
CREATE TABLE IF NOT EXISTS mcp.prompts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(100),

    -- Prompt content and structure
    content TEXT NOT NULL,
    arguments JSONB DEFAULT '[]'::jsonb,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- Usage statistics
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    avg_generation_time_ms INTEGER DEFAULT 0,

    -- Versioning
    version VARCHAR(50) DEFAULT '1.0.0',
    is_deprecated BOOLEAN DEFAULT FALSE,
    deprecation_message TEXT,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT prompts_name_length CHECK (char_length(name) >= 1),
    CONSTRAINT prompts_content_not_empty CHECK (char_length(content) > 0),
    CONSTRAINT prompts_usage_count_check CHECK (usage_count >= 0)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_prompts_name ON mcp.prompts(name);
CREATE INDEX IF NOT EXISTS idx_prompts_category ON mcp.prompts(category);
CREATE INDEX IF NOT EXISTS idx_prompts_active ON mcp.prompts(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_prompts_tags ON mcp.prompts USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_prompts_last_used ON mcp.prompts(last_used_at DESC NULLS LAST);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION mcp.update_prompts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prompts_updated_at_trigger
    BEFORE UPDATE ON mcp.prompts
    FOR EACH ROW
    EXECUTE FUNCTION mcp.update_prompts_updated_at();

-- Add comments
COMMENT ON TABLE mcp.prompts IS 'MCP prompt registry - stores prompt templates and usage metrics';
COMMENT ON COLUMN mcp.prompts.content IS 'Prompt template content with optional placeholders';
COMMENT ON COLUMN mcp.prompts.arguments IS 'JSON array of prompt argument definitions';
COMMENT ON COLUMN mcp.prompts.tags IS 'Array of tags for categorization and search';

-- Grant permissions
GRANT ALL ON TABLE mcp.prompts TO postgres;
GRANT ALL ON SEQUENCE mcp.prompts_id_seq TO postgres;
