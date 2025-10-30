-- Migration: Create MCP Resources Table
-- Schema: mcp
-- Description: Stores MCP resource definitions and metadata

-- Create mcp schema if not exists
CREATE SCHEMA IF NOT EXISTS mcp;

-- Create resources table
CREATE TABLE IF NOT EXISTS mcp.resources (
    id SERIAL PRIMARY KEY,
    uri VARCHAR(500) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    resource_type VARCHAR(100),

    -- Resource properties
    mime_type VARCHAR(100),
    size_bytes BIGINT DEFAULT 0,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- Access control
    is_public BOOLEAN DEFAULT FALSE,
    owner_id VARCHAR(255),
    allowed_users TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- Usage statistics
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    download_count INTEGER DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_cached BOOLEAN DEFAULT FALSE,
    cache_expires_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT resources_uri_not_empty CHECK (char_length(uri) > 0),
    CONSTRAINT resources_name_not_empty CHECK (char_length(name) > 0),
    CONSTRAINT resources_access_count_check CHECK (access_count >= 0),
    CONSTRAINT resources_size_check CHECK (size_bytes >= 0)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_resources_uri ON mcp.resources(uri);
CREATE INDEX IF NOT EXISTS idx_resources_name ON mcp.resources(name);
CREATE INDEX IF NOT EXISTS idx_resources_type ON mcp.resources(resource_type);
CREATE INDEX IF NOT EXISTS idx_resources_active ON mcp.resources(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_resources_public ON mcp.resources(is_public) WHERE is_public = TRUE;
CREATE INDEX IF NOT EXISTS idx_resources_owner ON mcp.resources(owner_id);
CREATE INDEX IF NOT EXISTS idx_resources_tags ON mcp.resources USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_resources_last_accessed ON mcp.resources(last_accessed_at DESC NULLS LAST);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION mcp.update_resources_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER resources_updated_at_trigger
    BEFORE UPDATE ON mcp.resources
    FOR EACH ROW
    EXECUTE FUNCTION mcp.update_resources_updated_at();

-- Function to check user access
CREATE OR REPLACE FUNCTION mcp.user_has_resource_access(
    resource_uri VARCHAR,
    user_id VARCHAR
) RETURNS BOOLEAN AS $$
DECLARE
    resource_record RECORD;
BEGIN
    SELECT * INTO resource_record
    FROM mcp.resources
    WHERE uri = resource_uri AND is_active = TRUE;

    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    -- Public resources are accessible to all
    IF resource_record.is_public THEN
        RETURN TRUE;
    END IF;

    -- Owner has access
    IF resource_record.owner_id = user_id THEN
        RETURN TRUE;
    END IF;

    -- Check allowed users list
    IF user_id = ANY(resource_record.allowed_users) THEN
        RETURN TRUE;
    END IF;

    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Add comments
COMMENT ON TABLE mcp.resources IS 'MCP resource registry - stores resource definitions and access control';
COMMENT ON COLUMN mcp.resources.uri IS 'Unique resource identifier (URI format)';
COMMENT ON COLUMN mcp.resources.is_public IS 'Whether resource is publicly accessible';
COMMENT ON COLUMN mcp.resources.allowed_users IS 'Array of user IDs with access permission';

-- Grant permissions
GRANT ALL ON TABLE mcp.resources TO postgres;
GRANT ALL ON SEQUENCE mcp.resources_id_seq TO postgres;
