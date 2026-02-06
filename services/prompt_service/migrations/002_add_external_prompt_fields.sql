-- Migration: Add External Prompt Fields
-- Schema: mcp
-- Description: Extends mcp.prompts table to support external MCP server prompts
--
-- External prompts are discovered from external MCP servers and stored alongside
-- internal prompts. They have:
-- - source_server_id: FK to the external server
-- - original_name: The prompt name before namespacing (server_name.prompt_name)
-- - is_external: Flag to distinguish from internal prompts

-- Add source_server_id column (FK to external_servers)
ALTER TABLE mcp.prompts
ADD COLUMN IF NOT EXISTS source_server_id UUID
REFERENCES mcp.external_servers(id) ON DELETE CASCADE;

-- Add original_name column (prompt name before namespacing)
ALTER TABLE mcp.prompts
ADD COLUMN IF NOT EXISTS original_name VARCHAR(255);

-- Add is_external flag
ALTER TABLE mcp.prompts
ADD COLUMN IF NOT EXISTS is_external BOOLEAN NOT NULL DEFAULT FALSE;

-- Create indexes for external prompt queries
CREATE INDEX IF NOT EXISTS idx_prompts_source_server
    ON mcp.prompts(source_server_id)
    WHERE source_server_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_prompts_is_external
    ON mcp.prompts(is_external)
    WHERE is_external = TRUE;

CREATE INDEX IF NOT EXISTS idx_prompts_original_name
    ON mcp.prompts(original_name)
    WHERE original_name IS NOT NULL;

-- Add comments
COMMENT ON COLUMN mcp.prompts.source_server_id IS 'UUID of the external MCP server this prompt came from (NULL for internal prompts)';
COMMENT ON COLUMN mcp.prompts.original_name IS 'Original prompt name before namespacing (e.g., "code_review" becomes "github-mcp.code_review")';
COMMENT ON COLUMN mcp.prompts.is_external IS 'TRUE if prompt is from an external MCP server, FALSE for internal prompts';

-- Update existing prompts to have is_external = FALSE (internal prompts)
UPDATE mcp.prompts SET is_external = FALSE WHERE is_external IS NULL;

-- Grant permissions
GRANT ALL ON TABLE mcp.prompts TO postgres;
