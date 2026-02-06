-- Migration: 001_create_marketplace_tables.sql
-- Schema: mcp
-- Description: Creates tables for marketplace package management
-- Author: isA Team
-- Date: 2026-01-24

-- ═══════════════════════════════════════════════════════════════════════════════
-- Table: marketplace_packages
-- Purpose: Registry of available MCP packages from all sources
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mcp.marketplace_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Package identification (npm-style naming)
    name VARCHAR(255) NOT NULL UNIQUE,  -- e.g., "@pencil/ui-design"
    display_name VARCHAR(255) NOT NULL, -- e.g., "Pencil UI Design"

    -- Metadata
    description TEXT,
    author VARCHAR(255),
    author_email VARCHAR(255),
    homepage_url TEXT,
    repository_url TEXT,
    documentation_url TEXT,
    license VARCHAR(50),

    -- Categorization
    category VARCHAR(100),  -- "design", "video", "productivity", etc.
    tags TEXT[] DEFAULT '{}',

    -- Registry source
    registry_source VARCHAR(50) NOT NULL,  -- "npm", "github", "isa-cloud", "private"
    registry_url TEXT,  -- Full URL to package in registry

    -- Popularity metrics
    download_count INTEGER DEFAULT 0,
    weekly_downloads INTEGER DEFAULT 0,
    star_count INTEGER DEFAULT 0,

    -- Trust indicators
    verified BOOLEAN DEFAULT FALSE,  -- isA verified publisher
    official BOOLEAN DEFAULT FALSE,  -- Official from service provider
    security_score INTEGER,  -- 0-100 security audit score

    -- Latest version info (denormalized for performance)
    latest_version VARCHAR(50),
    latest_version_id UUID,

    -- Status
    deprecated BOOLEAN DEFAULT FALSE,
    deprecation_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_synced_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT pkg_name_format CHECK (name ~ '^(@[a-z0-9-]+/)?[a-z0-9-]+$'),
    CONSTRAINT pkg_registry_check CHECK (
        registry_source IN ('npm', 'github', 'isa-cloud', 'private', 'local')
    ),
    CONSTRAINT pkg_security_score_check CHECK (
        security_score IS NULL OR (security_score >= 0 AND security_score <= 100)
    )
);

-- Indexes for marketplace_packages
CREATE INDEX IF NOT EXISTS idx_marketplace_pkg_name ON mcp.marketplace_packages(name);
CREATE INDEX IF NOT EXISTS idx_marketplace_pkg_category ON mcp.marketplace_packages(category);
CREATE INDEX IF NOT EXISTS idx_marketplace_pkg_registry ON mcp.marketplace_packages(registry_source);
CREATE INDEX IF NOT EXISTS idx_marketplace_pkg_downloads ON mcp.marketplace_packages(download_count DESC);
CREATE INDEX IF NOT EXISTS idx_marketplace_pkg_stars ON mcp.marketplace_packages(star_count DESC);
CREATE INDEX IF NOT EXISTS idx_marketplace_pkg_verified ON mcp.marketplace_packages(verified) WHERE verified = TRUE;
CREATE INDEX IF NOT EXISTS idx_marketplace_pkg_tags ON mcp.marketplace_packages USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_marketplace_pkg_deprecated ON mcp.marketplace_packages(deprecated) WHERE deprecated = FALSE;

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_marketplace_pkg_search ON mcp.marketplace_packages
    USING GIN (to_tsvector('english',
        coalesce(name, '') || ' ' ||
        coalesce(display_name, '') || ' ' ||
        coalesce(description, '') || ' ' ||
        coalesce(author, '')
    ));

-- Comments
COMMENT ON TABLE mcp.marketplace_packages IS 'Registry of available MCP packages from npm, GitHub, and other sources';
COMMENT ON COLUMN mcp.marketplace_packages.name IS 'Package name in npm format (e.g., @scope/name or name)';
COMMENT ON COLUMN mcp.marketplace_packages.registry_source IS 'Source registry: npm, github, isa-cloud, private, local';
COMMENT ON COLUMN mcp.marketplace_packages.verified IS 'Package verified by isA team for quality and security';
COMMENT ON COLUMN mcp.marketplace_packages.security_score IS 'Security audit score from 0-100';


-- ═══════════════════════════════════════════════════════════════════════════════
-- Table: package_versions
-- Purpose: Version history for each package with MCP configuration
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mcp.package_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID NOT NULL REFERENCES mcp.marketplace_packages(id) ON DELETE CASCADE,

    -- Version info (semver)
    version VARCHAR(50) NOT NULL,
    version_major INTEGER NOT NULL,
    version_minor INTEGER NOT NULL,
    version_patch INTEGER NOT NULL,
    prerelease VARCHAR(50),  -- e.g., "beta.1", "rc.2"

    -- MCP Configuration (the actual MCP server config)
    -- Example:
    -- {
    --   "transport": "stdio",
    --   "command": "npx",
    --   "args": ["-y", "@anthropic/pencil-mcp"],
    --   "env": {"PENCIL_API_KEY": "{{PENCIL_API_KEY}}"}
    -- }
    mcp_config JSONB NOT NULL,

    -- Tool metadata (discovered or declared in manifest)
    declared_tools JSONB DEFAULT '[]',
    tool_count INTEGER DEFAULT 0,

    -- Requirements
    min_mcp_version VARCHAR(20),
    required_env_vars TEXT[] DEFAULT '{}',
    dependencies JSONB DEFAULT '{}',

    -- Release info
    changelog TEXT,
    release_notes_url TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    published_by VARCHAR(255),

    -- Status
    deprecated BOOLEAN DEFAULT FALSE,
    yanked BOOLEAN DEFAULT FALSE,  -- Security issue, don't allow install

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE (package_id, version),
    CONSTRAINT pkg_version_tool_count CHECK (tool_count >= 0)
);

-- Indexes for package_versions
CREATE INDEX IF NOT EXISTS idx_pkg_versions_package ON mcp.package_versions(package_id);
CREATE INDEX IF NOT EXISTS idx_pkg_versions_semver ON mcp.package_versions(
    package_id, version_major DESC, version_minor DESC, version_patch DESC
);
CREATE INDEX IF NOT EXISTS idx_pkg_versions_published ON mcp.package_versions(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_pkg_versions_yanked ON mcp.package_versions(yanked) WHERE yanked = FALSE;

-- Comments
COMMENT ON TABLE mcp.package_versions IS 'Version history for marketplace packages with MCP configurations';
COMMENT ON COLUMN mcp.package_versions.mcp_config IS 'MCP server configuration (transport, command, args, env)';
COMMENT ON COLUMN mcp.package_versions.declared_tools IS 'Tools declared in package manifest';
COMMENT ON COLUMN mcp.package_versions.yanked IS 'Security issue - do not allow installation';


-- ═══════════════════════════════════════════════════════════════════════════════
-- Table: installed_packages
-- Purpose: Tracks which packages are installed for which user/org
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mcp.installed_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What's installed
    package_id UUID NOT NULL REFERENCES mcp.marketplace_packages(id),
    version_id UUID NOT NULL REFERENCES mcp.package_versions(id),

    -- Links to aggregator
    server_id UUID REFERENCES mcp.external_servers(id) ON DELETE SET NULL,

    -- Ownership (multi-tenant support)
    user_id UUID,      -- Personal installation
    org_id UUID,       -- Enterprise organization
    team_id UUID,      -- Enterprise team (optional)

    -- Installation configuration
    install_config JSONB DEFAULT '{}',  -- User-provided config (API keys, etc.)
    env_overrides JSONB DEFAULT '{}',   -- Environment variable overrides

    -- Update policy
    auto_update BOOLEAN DEFAULT TRUE,
    update_channel VARCHAR(20) DEFAULT 'stable',  -- "stable", "beta", "latest"
    pinned_version BOOLEAN DEFAULT FALSE,

    -- Status
    status VARCHAR(20) DEFAULT 'installed',
    error_message TEXT,

    -- Usage tracking
    last_used_at TIMESTAMPTZ,
    use_count INTEGER DEFAULT 0,

    -- Timestamps
    installed_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_sync_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT installed_pkg_status CHECK (
        status IN ('installed', 'disabled', 'error', 'updating', 'uninstalling')
    ),
    CONSTRAINT installed_pkg_channel CHECK (
        update_channel IN ('stable', 'beta', 'latest')
    ),
    CONSTRAINT installed_pkg_use_count CHECK (use_count >= 0)
);

-- Unique constraints for ownership (one installation per package per user/org/team)
CREATE UNIQUE INDEX IF NOT EXISTS idx_installed_pkg_user
    ON mcp.installed_packages(package_id, user_id)
    WHERE user_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_installed_pkg_org
    ON mcp.installed_packages(package_id, org_id)
    WHERE org_id IS NOT NULL AND team_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_installed_pkg_team
    ON mcp.installed_packages(package_id, org_id, team_id)
    WHERE org_id IS NOT NULL AND team_id IS NOT NULL;

-- Other indexes
CREATE INDEX IF NOT EXISTS idx_installed_pkg_server ON mcp.installed_packages(server_id);
CREATE INDEX IF NOT EXISTS idx_installed_pkg_status ON mcp.installed_packages(status);
CREATE INDEX IF NOT EXISTS idx_installed_pkg_user_id ON mcp.installed_packages(user_id);
CREATE INDEX IF NOT EXISTS idx_installed_pkg_org_id ON mcp.installed_packages(org_id);
CREATE INDEX IF NOT EXISTS idx_installed_pkg_auto_update ON mcp.installed_packages(auto_update) WHERE auto_update = TRUE;
CREATE INDEX IF NOT EXISTS idx_installed_pkg_last_used ON mcp.installed_packages(last_used_at DESC);

-- Comments
COMMENT ON TABLE mcp.installed_packages IS 'User/org package installations with configuration';
COMMENT ON COLUMN mcp.installed_packages.install_config IS 'User-provided configuration (API keys, settings)';
COMMENT ON COLUMN mcp.installed_packages.env_overrides IS 'Environment variable overrides for MCP server';
COMMENT ON COLUMN mcp.installed_packages.update_channel IS 'Update channel: stable, beta, or latest';


-- ═══════════════════════════════════════════════════════════════════════════════
-- Table: package_tool_mappings
-- Purpose: Maps discovered tools back to their source package
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mcp.package_tool_mappings (
    installed_package_id UUID NOT NULL REFERENCES mcp.installed_packages(id) ON DELETE CASCADE,
    tool_id INTEGER NOT NULL REFERENCES mcp.tools(id) ON DELETE CASCADE,

    -- Name mapping
    original_name VARCHAR(255) NOT NULL,      -- Tool name from MCP server
    namespaced_name VARCHAR(255) NOT NULL,    -- Prefixed name: "pencil:create_design"

    -- Skill classification results
    skill_ids TEXT[] DEFAULT '{}',            -- Assigned skill IDs
    primary_skill_id VARCHAR(100) REFERENCES mcp.skill_categories(id) ON DELETE SET NULL,

    -- Timestamps
    discovered_at TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (installed_package_id, tool_id)
);

-- Indexes for package_tool_mappings
CREATE INDEX IF NOT EXISTS idx_pkg_tool_map_installed ON mcp.package_tool_mappings(installed_package_id);
CREATE INDEX IF NOT EXISTS idx_pkg_tool_map_tool ON mcp.package_tool_mappings(tool_id);
CREATE INDEX IF NOT EXISTS idx_pkg_tool_map_skills ON mcp.package_tool_mappings USING GIN (skill_ids);
CREATE INDEX IF NOT EXISTS idx_pkg_tool_map_primary_skill ON mcp.package_tool_mappings(primary_skill_id);
CREATE INDEX IF NOT EXISTS idx_pkg_tool_map_namespaced ON mcp.package_tool_mappings(namespaced_name);

-- Comments
COMMENT ON TABLE mcp.package_tool_mappings IS 'Maps discovered tools to their source packages';
COMMENT ON COLUMN mcp.package_tool_mappings.original_name IS 'Original tool name from MCP server';
COMMENT ON COLUMN mcp.package_tool_mappings.namespaced_name IS 'Prefixed name for unified discovery (e.g., pencil:create)';


-- ═══════════════════════════════════════════════════════════════════════════════
-- Table: registry_sync_log
-- Purpose: Tracks registry synchronization history
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mcp.registry_sync_log (
    id SERIAL PRIMARY KEY,

    registry_source VARCHAR(50) NOT NULL,
    sync_type VARCHAR(20) NOT NULL,  -- "full", "incremental", "single_package"

    -- Results
    packages_discovered INTEGER DEFAULT 0,
    packages_updated INTEGER DEFAULT 0,
    packages_deprecated INTEGER DEFAULT 0,
    errors JSONB DEFAULT '[]',

    -- Timing
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,

    -- Status
    status VARCHAR(20) DEFAULT 'running',
    error_message TEXT,

    -- Constraints
    CONSTRAINT sync_log_type CHECK (sync_type IN ('full', 'incremental', 'single_package')),
    CONSTRAINT sync_log_status CHECK (status IN ('running', 'completed', 'failed')),
    CONSTRAINT sync_log_counts CHECK (
        packages_discovered >= 0 AND
        packages_updated >= 0 AND
        packages_deprecated >= 0
    )
);

-- Indexes for registry_sync_log
CREATE INDEX IF NOT EXISTS idx_sync_log_registry ON mcp.registry_sync_log(registry_source);
CREATE INDEX IF NOT EXISTS idx_sync_log_started ON mcp.registry_sync_log(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_log_status ON mcp.registry_sync_log(status);

-- Comments
COMMENT ON TABLE mcp.registry_sync_log IS 'Registry synchronization history for auditing';
COMMENT ON COLUMN mcp.registry_sync_log.sync_type IS 'Type of sync: full, incremental, or single_package';


-- ═══════════════════════════════════════════════════════════════════════════════
-- Table: featured_packages
-- Purpose: Curated list of featured/recommended packages
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mcp.featured_packages (
    id SERIAL PRIMARY KEY,
    package_id UUID NOT NULL REFERENCES mcp.marketplace_packages(id) ON DELETE CASCADE,

    -- Display
    display_order INTEGER NOT NULL DEFAULT 0,
    feature_reason TEXT,  -- Why this package is featured
    badge VARCHAR(50),    -- "staff-pick", "trending", "new", "popular"

    -- Targeting
    category VARCHAR(100),  -- Feature for specific category page

    -- Validity
    featured_from TIMESTAMPTZ DEFAULT NOW(),
    featured_until TIMESTAMPTZ,  -- NULL = no expiry

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE (package_id, category)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_featured_pkg_active ON mcp.featured_packages(is_active, display_order)
    WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_featured_pkg_category ON mcp.featured_packages(category);

-- Comments
COMMENT ON TABLE mcp.featured_packages IS 'Curated featured packages for marketplace homepage';


-- ═══════════════════════════════════════════════════════════════════════════════
-- Triggers
-- ═══════════════════════════════════════════════════════════════════════════════

-- Updated_at trigger for marketplace_packages
CREATE OR REPLACE FUNCTION mcp.update_marketplace_pkg_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS marketplace_pkg_updated_at_trigger ON mcp.marketplace_packages;
CREATE TRIGGER marketplace_pkg_updated_at_trigger
    BEFORE UPDATE ON mcp.marketplace_packages
    FOR EACH ROW
    EXECUTE FUNCTION mcp.update_marketplace_pkg_updated_at();


-- Updated_at trigger for installed_packages
CREATE OR REPLACE FUNCTION mcp.update_installed_pkg_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS installed_pkg_updated_at_trigger ON mcp.installed_packages;
CREATE TRIGGER installed_pkg_updated_at_trigger
    BEFORE UPDATE ON mcp.installed_packages
    FOR EACH ROW
    EXECUTE FUNCTION mcp.update_installed_pkg_updated_at();


-- Trigger to update latest_version_id when new version is added
CREATE OR REPLACE FUNCTION mcp.update_latest_version()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the package's latest version reference
    UPDATE mcp.marketplace_packages
    SET
        latest_version = NEW.version,
        latest_version_id = NEW.id,
        updated_at = NOW()
    WHERE id = NEW.package_id
      AND (
          latest_version IS NULL
          OR (NEW.version_major, NEW.version_minor, NEW.version_patch) > (
              SELECT (version_major, version_minor, version_patch)
              FROM mcp.package_versions
              WHERE id = mcp.marketplace_packages.latest_version_id
          )
      )
      AND NEW.yanked = FALSE
      AND NEW.deprecated = FALSE;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS pkg_version_update_latest_trigger ON mcp.package_versions;
CREATE TRIGGER pkg_version_update_latest_trigger
    AFTER INSERT ON mcp.package_versions
    FOR EACH ROW
    EXECUTE FUNCTION mcp.update_latest_version();


-- Trigger to increment download count
CREATE OR REPLACE FUNCTION mcp.increment_pkg_download()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE mcp.marketplace_packages
    SET download_count = download_count + 1
    WHERE id = NEW.package_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS installed_pkg_increment_download_trigger ON mcp.installed_packages;
CREATE TRIGGER installed_pkg_increment_download_trigger
    AFTER INSERT ON mcp.installed_packages
    FOR EACH ROW
    EXECUTE FUNCTION mcp.increment_pkg_download();


-- ═══════════════════════════════════════════════════════════════════════════════
-- Views
-- ═══════════════════════════════════════════════════════════════════════════════

-- View: Popular packages with install count
CREATE OR REPLACE VIEW mcp.v_popular_packages AS
SELECT
    p.*,
    COUNT(DISTINCT i.id) as install_count,
    COUNT(DISTINCT i.user_id) as user_count,
    COUNT(DISTINCT i.org_id) as org_count
FROM mcp.marketplace_packages p
LEFT JOIN mcp.installed_packages i ON p.id = i.package_id AND i.status = 'installed'
WHERE p.deprecated = FALSE
GROUP BY p.id
ORDER BY p.download_count DESC, p.star_count DESC;

-- View: Installed packages with package details
CREATE OR REPLACE VIEW mcp.v_installed_packages_detail AS
SELECT
    i.*,
    p.name as package_name,
    p.display_name,
    p.description,
    p.category,
    p.tags,
    p.author,
    p.verified,
    v.version,
    v.mcp_config,
    v.tool_count,
    p.latest_version,
    (v.version != p.latest_version) as update_available
FROM mcp.installed_packages i
JOIN mcp.marketplace_packages p ON i.package_id = p.id
JOIN mcp.package_versions v ON i.version_id = v.id;


-- ═══════════════════════════════════════════════════════════════════════════════
-- Permissions
-- ═══════════════════════════════════════════════════════════════════════════════

GRANT ALL ON TABLE mcp.marketplace_packages TO postgres;
GRANT ALL ON TABLE mcp.package_versions TO postgres;
GRANT ALL ON TABLE mcp.installed_packages TO postgres;
GRANT ALL ON TABLE mcp.package_tool_mappings TO postgres;
GRANT ALL ON TABLE mcp.registry_sync_log TO postgres;
GRANT ALL ON TABLE mcp.featured_packages TO postgres;
GRANT ALL ON SEQUENCE mcp.registry_sync_log_id_seq TO postgres;
GRANT ALL ON SEQUENCE mcp.featured_packages_id_seq TO postgres;
GRANT SELECT ON mcp.v_popular_packages TO postgres;
GRANT SELECT ON mcp.v_installed_packages_detail TO postgres;
