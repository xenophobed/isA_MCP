-- Migration: Add skill classification fields to resources table
-- Schema: mcp
-- Description: Enables hierarchical skill-based search for resources (same pattern as tools)

-- Add skill classification columns
ALTER TABLE mcp.resources
ADD COLUMN IF NOT EXISTS skill_ids TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN IF NOT EXISTS primary_skill_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS is_classified BOOLEAN DEFAULT FALSE;

-- Create indexes for skill-based queries
CREATE INDEX IF NOT EXISTS idx_resources_skill_ids ON mcp.resources USING gin(skill_ids);
CREATE INDEX IF NOT EXISTS idx_resources_primary_skill ON mcp.resources(primary_skill_id) WHERE primary_skill_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_resources_classified ON mcp.resources(is_classified) WHERE is_classified = TRUE;

-- Add comments
COMMENT ON COLUMN mcp.resources.skill_ids IS 'Array of skill category IDs this resource belongs to';
COMMENT ON COLUMN mcp.resources.primary_skill_id IS 'Primary skill category for hierarchical search routing';
COMMENT ON COLUMN mcp.resources.is_classified IS 'Whether resource has been classified into skill categories';

-- Function to get resources by skill
CREATE OR REPLACE FUNCTION mcp.get_resources_by_skill(
    skill_id VARCHAR
) RETURNS TABLE (
    id INTEGER,
    uri VARCHAR,
    name VARCHAR,
    description TEXT,
    resource_type VARCHAR,
    primary_skill_id VARCHAR,
    is_classified BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.id,
        r.uri,
        r.name,
        r.description,
        r.resource_type,
        r.primary_skill_id,
        r.is_classified
    FROM mcp.resources r
    WHERE skill_id = ANY(r.skill_ids) AND r.is_active = TRUE
    ORDER BY
        CASE WHEN r.primary_skill_id = skill_id THEN 0 ELSE 1 END,
        r.name;
END;
$$ LANGUAGE plpgsql;
