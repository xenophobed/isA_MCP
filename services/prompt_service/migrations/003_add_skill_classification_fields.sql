-- Migration: Add skill classification fields to prompts table
-- Schema: mcp
-- Description: Enables hierarchical skill-based search for prompts (same pattern as tools/resources)

-- Add skill classification columns
ALTER TABLE mcp.prompts
ADD COLUMN IF NOT EXISTS skill_ids TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN IF NOT EXISTS primary_skill_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS is_classified BOOLEAN DEFAULT FALSE;

-- Create indexes for skill-based queries
CREATE INDEX IF NOT EXISTS idx_prompts_skill_ids ON mcp.prompts USING gin(skill_ids);
CREATE INDEX IF NOT EXISTS idx_prompts_primary_skill ON mcp.prompts(primary_skill_id) WHERE primary_skill_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_prompts_classified ON mcp.prompts(is_classified) WHERE is_classified = TRUE;

-- Add comments
COMMENT ON COLUMN mcp.prompts.skill_ids IS 'Array of skill category IDs this prompt belongs to';
COMMENT ON COLUMN mcp.prompts.primary_skill_id IS 'Primary skill category for hierarchical search routing';
COMMENT ON COLUMN mcp.prompts.is_classified IS 'Whether prompt has been classified into skill categories';

-- Function to get prompts by skill
CREATE OR REPLACE FUNCTION mcp.get_prompts_by_skill(
    skill_id VARCHAR
) RETURNS TABLE (
    id INTEGER,
    name VARCHAR,
    description TEXT,
    primary_skill_id VARCHAR,
    is_classified BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.name,
        p.description,
        p.primary_skill_id,
        p.is_classified
    FROM mcp.prompts p
    WHERE skill_id = ANY(p.skill_ids) AND p.is_active = TRUE
    ORDER BY
        CASE WHEN p.primary_skill_id = skill_id THEN 0 ELSE 1 END,
        p.name;
END;
$$ LANGUAGE plpgsql;
