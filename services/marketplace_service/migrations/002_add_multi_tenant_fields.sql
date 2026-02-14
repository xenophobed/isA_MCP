-- Migration 002: Add multi-tenant fields to marketplace tables
-- Adds org_id and is_global to marketplace_packages and package_versions
-- for org-private package support.
-- Existing packages become global (visible to all orgs).

-- marketplace_packages
ALTER TABLE mcp.marketplace_packages ADD COLUMN IF NOT EXISTS org_id UUID;
ALTER TABLE mcp.marketplace_packages ADD COLUMN IF NOT EXISTS is_global BOOLEAN DEFAULT TRUE;
UPDATE mcp.marketplace_packages SET is_global = TRUE WHERE is_global IS NULL;

-- package_versions
ALTER TABLE mcp.package_versions ADD COLUMN IF NOT EXISTS org_id UUID;
ALTER TABLE mcp.package_versions ADD COLUMN IF NOT EXISTS is_global BOOLEAN DEFAULT TRUE;
UPDATE mcp.package_versions SET is_global = TRUE WHERE is_global IS NULL;

-- Replace global unique name constraint with scoped ones
ALTER TABLE mcp.marketplace_packages DROP CONSTRAINT IF EXISTS marketplace_packages_name_key;
CREATE UNIQUE INDEX IF NOT EXISTS idx_marketplace_packages_name_global
    ON mcp.marketplace_packages(name) WHERE is_global = TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS idx_marketplace_packages_name_org
    ON mcp.marketplace_packages(name, org_id) WHERE org_id IS NOT NULL;

-- Composite indexes for tenant filtering
CREATE INDEX IF NOT EXISTS idx_marketplace_packages_tenant_filter
    ON mcp.marketplace_packages(org_id, is_global);
CREATE INDEX IF NOT EXISTS idx_package_versions_tenant_filter
    ON mcp.package_versions(org_id, is_global);

-- DOWN / ROLLBACK:
-- DROP INDEX IF EXISTS idx_package_versions_tenant_filter;
-- DROP INDEX IF EXISTS idx_marketplace_packages_tenant_filter;
-- DROP INDEX IF EXISTS idx_marketplace_packages_name_org;
-- DROP INDEX IF EXISTS idx_marketplace_packages_name_global;
-- ALTER TABLE mcp.marketplace_packages ADD CONSTRAINT marketplace_packages_name_key UNIQUE (name);
-- ALTER TABLE mcp.package_versions DROP COLUMN IF EXISTS is_global;
-- ALTER TABLE mcp.package_versions DROP COLUMN IF EXISTS org_id;
-- ALTER TABLE mcp.marketplace_packages DROP COLUMN IF EXISTS is_global;
-- ALTER TABLE mcp.marketplace_packages DROP COLUMN IF EXISTS org_id;
