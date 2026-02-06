-- Migration: Add External Resource Fields
-- Schema: mcp
-- Description: Extends mcp.resources table to support external MCP server resources
--
-- External resources are discovered from external MCP servers and stored alongside
-- internal resources. They have:
-- - source_server_id: FK to the external server
-- - original_name: The resource name before namespacing (server_name.resource_name)
-- - original_uri: The original URI from the external server
-- - is_external: Flag to distinguish from internal resources

-- Add source_server_id column (FK to external_servers)
ALTER TABLE mcp.resources
ADD COLUMN IF NOT EXISTS source_server_id UUID
REFERENCES mcp.external_servers(id) ON DELETE CASCADE;

-- Add original_name column (resource name before namespacing)
ALTER TABLE mcp.resources
ADD COLUMN IF NOT EXISTS original_name VARCHAR(255);

-- Add original_uri column (original URI from external server)
ALTER TABLE mcp.resources
ADD COLUMN IF NOT EXISTS original_uri VARCHAR(500);

-- Add is_external flag
ALTER TABLE mcp.resources
ADD COLUMN IF NOT EXISTS is_external BOOLEAN NOT NULL DEFAULT FALSE;

-- Create indexes for external resource queries
CREATE INDEX IF NOT EXISTS idx_resources_source_server
    ON mcp.resources(source_server_id)
    WHERE source_server_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_resources_is_external
    ON mcp.resources(is_external)
    WHERE is_external = TRUE;

CREATE INDEX IF NOT EXISTS idx_resources_original_name
    ON mcp.resources(original_name)
    WHERE original_name IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_resources_original_uri
    ON mcp.resources(original_uri)
    WHERE original_uri IS NOT NULL;

-- Add comments
COMMENT ON COLUMN mcp.resources.source_server_id IS 'UUID of the external MCP server this resource came from (NULL for internal resources)';
COMMENT ON COLUMN mcp.resources.original_name IS 'Original resource name before namespacing (e.g., "repo_info" becomes "github-mcp.repo_info")';
COMMENT ON COLUMN mcp.resources.original_uri IS 'Original URI from the external MCP server';
COMMENT ON COLUMN mcp.resources.is_external IS 'TRUE if resource is from an external MCP server, FALSE for internal resources';

-- Update existing resources to have is_external = FALSE (internal resources)
UPDATE mcp.resources SET is_external = FALSE WHERE is_external IS NULL;

-- Grant permissions
GRANT ALL ON TABLE mcp.resources TO postgres;
