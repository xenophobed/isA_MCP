-- Migration 004: Add multi-tenant fields to mcp.tools
-- Adds org_id and is_global for hybrid multi-tenancy support.
-- Existing tools become global (visible to all orgs).

ALTER TABLE mcp.tools ADD COLUMN IF NOT EXISTS org_id UUID;
ALTER TABLE mcp.tools ADD COLUMN IF NOT EXISTS is_global BOOLEAN DEFAULT TRUE;
UPDATE mcp.tools SET is_global = TRUE WHERE is_global IS NULL;

-- Replace global unique name constraint with scoped ones
-- Global tools: unique name across all global tools
-- Org tools: unique name within each org
ALTER TABLE mcp.tools DROP CONSTRAINT IF EXISTS tools_name_key;
CREATE UNIQUE INDEX IF NOT EXISTS idx_tools_name_global ON mcp.tools(name) WHERE is_global = TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS idx_tools_name_org ON mcp.tools(name, org_id) WHERE org_id IS NOT NULL;

-- Index for efficient tenant filtering queries
CREATE INDEX IF NOT EXISTS idx_tools_tenant_filter ON mcp.tools(org_id, is_global);
