-- Migration 004: Add multi-tenant fields to skill tables
-- Adds org_id and is_global for hybrid multi-tenancy support.
-- Existing skills become global (visible to all orgs).

-- skill_categories
ALTER TABLE mcp.skill_categories ADD COLUMN IF NOT EXISTS org_id UUID;
ALTER TABLE mcp.skill_categories ADD COLUMN IF NOT EXISTS is_global BOOLEAN DEFAULT TRUE;
UPDATE mcp.skill_categories SET is_global = TRUE WHERE is_global IS NULL;

-- tool_skill_assignments
ALTER TABLE mcp.tool_skill_assignments ADD COLUMN IF NOT EXISTS org_id UUID;
ALTER TABLE mcp.tool_skill_assignments ADD COLUMN IF NOT EXISTS is_global BOOLEAN DEFAULT TRUE;
UPDATE mcp.tool_skill_assignments SET is_global = TRUE WHERE is_global IS NULL;

-- Composite index for tenant-filtered queries
CREATE INDEX IF NOT EXISTS idx_skill_categories_tenant_filter
    ON mcp.skill_categories(org_id, is_global);
CREATE INDEX IF NOT EXISTS idx_tool_skill_assignments_tenant_filter
    ON mcp.tool_skill_assignments(org_id, is_global);

-- DOWN / ROLLBACK:
-- DROP INDEX IF EXISTS idx_tool_skill_assignments_tenant_filter;
-- DROP INDEX IF EXISTS idx_skill_categories_tenant_filter;
-- ALTER TABLE mcp.tool_skill_assignments DROP COLUMN IF EXISTS is_global;
-- ALTER TABLE mcp.tool_skill_assignments DROP COLUMN IF EXISTS org_id;
-- ALTER TABLE mcp.skill_categories DROP COLUMN IF EXISTS is_global;
-- ALTER TABLE mcp.skill_categories DROP COLUMN IF EXISTS org_id;
