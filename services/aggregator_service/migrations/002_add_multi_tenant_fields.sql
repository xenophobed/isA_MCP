-- Migration 002: Add multi-tenant fields to mcp.external_servers
-- Adds org_id and is_global for hybrid multi-tenancy support.
-- Existing servers become global (visible to all orgs).

ALTER TABLE mcp.external_servers ADD COLUMN IF NOT EXISTS org_id UUID;
ALTER TABLE mcp.external_servers ADD COLUMN IF NOT EXISTS is_global BOOLEAN DEFAULT TRUE;
UPDATE mcp.external_servers SET is_global = TRUE WHERE is_global IS NULL;

-- Replace global unique name constraint with scoped ones
ALTER TABLE mcp.external_servers DROP CONSTRAINT IF EXISTS external_servers_name_key;
CREATE UNIQUE INDEX IF NOT EXISTS idx_external_servers_name_global ON mcp.external_servers(name) WHERE is_global = TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS idx_external_servers_name_org ON mcp.external_servers(name, org_id) WHERE org_id IS NOT NULL;

-- Index for efficient tenant filtering queries
CREATE INDEX IF NOT EXISTS idx_external_servers_tenant_filter ON mcp.external_servers(org_id, is_global);
