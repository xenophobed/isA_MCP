-- Migration: Create MCP Tools Table
-- Schema: mcp
-- Description: Stores MCP tool definitions and metadata

-- Create mcp schema if not exists
CREATE SCHEMA IF NOT EXISTS mcp;

-- Create tools table
CREATE TABLE IF NOT EXISTS mcp.tools (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(100),

    -- Tool input schema (JSON Schema format)
    input_schema JSONB DEFAULT '{}'::jsonb,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Usage statistics
    call_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    avg_response_time_ms INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_deprecated BOOLEAN DEFAULT FALSE,
    deprecation_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT tools_name_length CHECK (char_length(name) >= 1),
    CONSTRAINT tools_call_count_check CHECK (call_count >= 0),
    CONSTRAINT tools_success_count_check CHECK (success_count >= 0),
    CONSTRAINT tools_failure_count_check CHECK (failure_count >= 0)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_tools_name ON mcp.tools(name);
CREATE INDEX IF NOT EXISTS idx_tools_category ON mcp.tools(category);
CREATE INDEX IF NOT EXISTS idx_tools_active ON mcp.tools(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_tools_last_used ON mcp.tools(last_used_at DESC NULLS LAST);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION mcp.update_tools_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tools_updated_at_trigger
    BEFORE UPDATE ON mcp.tools
    FOR EACH ROW
    EXECUTE FUNCTION mcp.update_tools_updated_at();

-- Create function to calculate success rate
CREATE OR REPLACE FUNCTION mcp.tools_success_rate(tool_id INTEGER)
RETURNS NUMERIC AS $$
DECLARE
    total_calls INTEGER;
    success_calls INTEGER;
BEGIN
    SELECT call_count, success_count INTO total_calls, success_calls
    FROM mcp.tools WHERE id = tool_id;

    IF total_calls = 0 THEN
        RETURN NULL;
    END IF;

    RETURN ROUND((success_calls::NUMERIC / total_calls::NUMERIC) * 100, 2);
END;
$$ LANGUAGE plpgsql;

-- Add comments
COMMENT ON TABLE mcp.tools IS 'MCP tool registry - stores tool definitions and usage metrics';
COMMENT ON COLUMN mcp.tools.input_schema IS 'JSON Schema defining expected tool input parameters';
COMMENT ON COLUMN mcp.tools.metadata IS 'Additional tool metadata (tags, version, etc)';
COMMENT ON COLUMN mcp.tools.is_deprecated IS 'Flag indicating if tool is deprecated';

-- Grant permissions
GRANT ALL ON TABLE mcp.tools TO postgres;
GRANT ALL ON SEQUENCE mcp.tools_id_seq TO postgres;
