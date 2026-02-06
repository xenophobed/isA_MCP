-- Migration: Add is_default Field for Default Tools
-- Schema: mcp
-- Description: Adds is_default flag to identify meta-tools that should
--              always be available in the agent context.
--
-- Default tools = meta_tools only (~8 tools):
-- - discover, get_tool_schema, execute (gateway to all other tools)
-- - list_skills, list_prompts, get_prompt, list_resources, read_resource
--
-- All other tools are accessed via discover → execute pattern.
-- SDK can add additional tools via allowed_tools option.

-- Add is_default column
ALTER TABLE mcp.tools
ADD COLUMN IF NOT EXISTS is_default BOOLEAN NOT NULL DEFAULT FALSE;

-- Create index for efficient default tool queries
CREATE INDEX IF NOT EXISTS idx_tools_is_default
    ON mcp.tools(is_default)
    WHERE is_default = TRUE;

-- Add comment
COMMENT ON COLUMN mcp.tools.is_default IS 'TRUE for meta-tools that are always available. Other tools accessed via discover/execute.';

-- Mark meta-tools as default (gateway tools for accessing all other capabilities)
UPDATE mcp.tools
SET is_default = TRUE
WHERE name IN (
    'discover',
    'get_tool_schema',
    'execute',
    'list_skills',
    'list_prompts',
    'get_prompt',
    'list_resources',
    'read_resource'
);

-- Grant permissions
GRANT ALL ON TABLE mcp.tools TO postgres;
