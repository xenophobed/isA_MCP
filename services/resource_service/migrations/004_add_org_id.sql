-- Migration 004: Add org_id to mcp.resources
-- Resources already have owner_id/is_public/allowed_users for access control.
-- Adding org_id enables organization-scoped resource filtering.

ALTER TABLE mcp.resources ADD COLUMN IF NOT EXISTS org_id UUID;
ALTER TABLE mcp.resources ADD COLUMN IF NOT EXISTS is_global BOOLEAN DEFAULT TRUE;
UPDATE mcp.resources SET is_global = TRUE WHERE is_global IS NULL;

-- Composite index matching tools/prompts pattern for tenant-filtered queries
-- Supports: WHERE (is_global = TRUE OR org_id = $1)
CREATE INDEX IF NOT EXISTS idx_resources_tenant_filter ON mcp.resources(org_id, is_global);
-- Keep single-column index for backwards compatibility
CREATE INDEX IF NOT EXISTS idx_resources_org_id ON mcp.resources(org_id);

-- DOWN / ROLLBACK:
-- DROP INDEX IF EXISTS idx_resources_org_id;
-- ALTER TABLE mcp.resources DROP COLUMN IF EXISTS org_id;
