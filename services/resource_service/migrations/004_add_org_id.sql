-- Migration 004: Add org_id to mcp.resources
-- Resources already have owner_id/is_public/allowed_users for access control.
-- Adding org_id enables organization-scoped resource filtering.

ALTER TABLE mcp.resources ADD COLUMN IF NOT EXISTS org_id UUID;

-- Index for org-scoped resource queries
CREATE INDEX IF NOT EXISTS idx_resources_org_id ON mcp.resources(org_id);
