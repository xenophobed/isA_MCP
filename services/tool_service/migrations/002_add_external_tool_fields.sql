-- Migration: Add External Tool Fields
-- Schema: mcp
-- Description: Extends mcp.tools table to support external MCP server tools
--
-- External tools are discovered from external MCP servers and stored alongside
-- internal tools. They have:
-- - source_server_id: FK to the external server
-- - original_name: The tool name before namespacing (server_name.tool_name)
-- - is_external: Flag to distinguish from internal tools
-- - is_classified: Whether the tool has been classified into skills
-- - skill_ids: Array of assigned skill IDs
-- - primary_skill_id: Primary skill assignment

-- Add source_server_id column (FK to external_servers)
ALTER TABLE mcp.tools
ADD COLUMN IF NOT EXISTS source_server_id UUID
REFERENCES mcp.external_servers(id) ON DELETE CASCADE;

-- Add original_name column (tool name before namespacing)
ALTER TABLE mcp.tools
ADD COLUMN IF NOT EXISTS original_name VARCHAR(255);

-- Add is_external flag
ALTER TABLE mcp.tools
ADD COLUMN IF NOT EXISTS is_external BOOLEAN NOT NULL DEFAULT FALSE;

-- Add is_classified flag (for skill classification tracking)
ALTER TABLE mcp.tools
ADD COLUMN IF NOT EXISTS is_classified BOOLEAN NOT NULL DEFAULT FALSE;

-- Add skill_ids array (for skill classification)
ALTER TABLE mcp.tools
ADD COLUMN IF NOT EXISTS skill_ids TEXT[] DEFAULT '{}';

-- Add primary_skill_id (main skill assignment)
ALTER TABLE mcp.tools
ADD COLUMN IF NOT EXISTS primary_skill_id VARCHAR(255);

-- Create indexes for external tool queries
CREATE INDEX IF NOT EXISTS idx_tools_source_server
    ON mcp.tools(source_server_id)
    WHERE source_server_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_tools_is_external
    ON mcp.tools(is_external)
    WHERE is_external = TRUE;

CREATE INDEX IF NOT EXISTS idx_tools_is_classified
    ON mcp.tools(is_classified);

CREATE INDEX IF NOT EXISTS idx_tools_original_name
    ON mcp.tools(original_name)
    WHERE original_name IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_tools_primary_skill
    ON mcp.tools(primary_skill_id)
    WHERE primary_skill_id IS NOT NULL;

-- Create GIN index for skill_ids array queries
CREATE INDEX IF NOT EXISTS idx_tools_skill_ids
    ON mcp.tools USING GIN(skill_ids);

-- Add comments
COMMENT ON COLUMN mcp.tools.source_server_id IS 'UUID of the external MCP server this tool came from (NULL for internal tools)';
COMMENT ON COLUMN mcp.tools.original_name IS 'Original tool name before namespacing (e.g., "create_issue" becomes "github-mcp.create_issue")';
COMMENT ON COLUMN mcp.tools.is_external IS 'TRUE if tool is from an external MCP server, FALSE for internal tools';
COMMENT ON COLUMN mcp.tools.is_classified IS 'TRUE if tool has been classified into skills';
COMMENT ON COLUMN mcp.tools.skill_ids IS 'Array of skill IDs this tool is assigned to';
COMMENT ON COLUMN mcp.tools.primary_skill_id IS 'Primary skill ID for this tool (highest confidence assignment)';

-- Update existing tools to have is_external = FALSE (internal tools)
UPDATE mcp.tools SET is_external = FALSE WHERE is_external IS NULL;
UPDATE mcp.tools SET is_classified = FALSE WHERE is_classified IS NULL;

-- Grant permissions
GRANT ALL ON TABLE mcp.tools TO postgres;
