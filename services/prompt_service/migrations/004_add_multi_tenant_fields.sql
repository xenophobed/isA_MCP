-- Migration 004: Add multi-tenant fields to mcp.prompts
-- Adds org_id and is_global for hybrid multi-tenancy support.
-- Existing prompts become global (visible to all orgs).

ALTER TABLE mcp.prompts ADD COLUMN IF NOT EXISTS org_id UUID;
ALTER TABLE mcp.prompts ADD COLUMN IF NOT EXISTS is_global BOOLEAN DEFAULT TRUE;
UPDATE mcp.prompts SET is_global = TRUE WHERE is_global IS NULL;

-- Replace global unique name constraint with scoped ones
ALTER TABLE mcp.prompts DROP CONSTRAINT IF EXISTS prompts_name_key;
CREATE UNIQUE INDEX IF NOT EXISTS idx_prompts_name_global ON mcp.prompts(name) WHERE is_global = TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS idx_prompts_name_org ON mcp.prompts(name, org_id) WHERE org_id IS NOT NULL;

-- Index for efficient tenant filtering queries
CREATE INDEX IF NOT EXISTS idx_prompts_tenant_filter ON mcp.prompts(org_id, is_global);

-- DOWN / ROLLBACK:
-- DROP INDEX IF EXISTS idx_prompts_tenant_filter;
-- DROP INDEX IF EXISTS idx_prompts_name_org;
-- DROP INDEX IF EXISTS idx_prompts_name_global;
-- ALTER TABLE mcp.prompts ADD CONSTRAINT prompts_name_key UNIQUE (name);
-- ALTER TABLE mcp.prompts DROP COLUMN IF EXISTS is_global;
-- ALTER TABLE mcp.prompts DROP COLUMN IF EXISTS org_id;
