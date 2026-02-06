-- Migration: Create Skill Classification Tables
-- Schema: mcp
-- Description: Stores skill categories, tool-skill assignments, and suggestions

-- ═══════════════════════════════════════════════════════════════════════════════
-- Table: skill_categories
-- Purpose: Predefined skill categories for tool classification
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mcp.skill_categories (
    -- Primary key: human-readable skill ID (e.g., 'calendar-management')
    id VARCHAR(100) PRIMARY KEY,

    -- Display name
    name VARCHAR(255) NOT NULL UNIQUE,

    -- Detailed description for LLM context
    description TEXT NOT NULL,

    -- Keywords for matching (array of terms)
    keywords TEXT[] DEFAULT '{}',

    -- Example tool names/descriptions
    examples TEXT[] DEFAULT '{}',

    -- Parent domain for hierarchy (optional)
    parent_domain VARCHAR(100),

    -- Number of tools assigned to this skill (denormalized for performance)
    tool_count INTEGER DEFAULT 0,

    -- Active status for soft delete
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT skill_categories_id_format CHECK (id ~ '^[a-z0-9-]+$'),
    CONSTRAINT skill_categories_name_length CHECK (char_length(name) >= 2),
    CONSTRAINT skill_categories_tool_count_check CHECK (tool_count >= 0)
);

-- Indexes for skill_categories
CREATE INDEX IF NOT EXISTS idx_skill_categories_active ON mcp.skill_categories(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_skill_categories_domain ON mcp.skill_categories(parent_domain);
CREATE INDEX IF NOT EXISTS idx_skill_categories_tool_count ON mcp.skill_categories(tool_count DESC);

-- GIN index for keyword search
CREATE INDEX IF NOT EXISTS idx_skill_categories_keywords ON mcp.skill_categories USING GIN (keywords);

-- Comments
COMMENT ON TABLE mcp.skill_categories IS 'Predefined skill categories for hierarchical tool search';
COMMENT ON COLUMN mcp.skill_categories.id IS 'Human-readable skill ID (e.g., calendar-management)';
COMMENT ON COLUMN mcp.skill_categories.keywords IS 'Array of keywords for LLM matching context';
COMMENT ON COLUMN mcp.skill_categories.examples IS 'Example tool descriptions for LLM context';
COMMENT ON COLUMN mcp.skill_categories.tool_count IS 'Denormalized count of assigned tools';


-- ═══════════════════════════════════════════════════════════════════════════════
-- Table: tool_skill_assignments
-- Purpose: Maps tools to skill categories with confidence scores
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mcp.tool_skill_assignments (
    -- Foreign keys
    tool_id INTEGER NOT NULL REFERENCES mcp.tools(id) ON DELETE CASCADE,
    skill_id VARCHAR(100) NOT NULL REFERENCES mcp.skill_categories(id) ON DELETE CASCADE,

    -- Classification metadata
    confidence NUMERIC(4, 3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    is_primary BOOLEAN DEFAULT FALSE,

    -- Source of assignment
    -- llm_auto: Automated LLM classification
    -- human_manual: Human-assigned
    -- human_override: Human override of LLM assignment
    source VARCHAR(20) DEFAULT 'llm_auto' CHECK (source IN ('llm_auto', 'human_manual', 'human_override')),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Composite primary key (tool can have multiple skills)
    PRIMARY KEY (tool_id, skill_id)
);

-- Indexes for tool_skill_assignments
CREATE INDEX IF NOT EXISTS idx_tool_skill_tool_id ON mcp.tool_skill_assignments(tool_id);
CREATE INDEX IF NOT EXISTS idx_tool_skill_skill_id ON mcp.tool_skill_assignments(skill_id);
CREATE INDEX IF NOT EXISTS idx_tool_skill_primary ON mcp.tool_skill_assignments(tool_id) WHERE is_primary = TRUE;
CREATE INDEX IF NOT EXISTS idx_tool_skill_confidence ON mcp.tool_skill_assignments(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_tool_skill_source ON mcp.tool_skill_assignments(source);

-- Comments
COMMENT ON TABLE mcp.tool_skill_assignments IS 'Maps tools to skill categories with confidence scores';
COMMENT ON COLUMN mcp.tool_skill_assignments.confidence IS 'LLM confidence score (0.0-1.0)';
COMMENT ON COLUMN mcp.tool_skill_assignments.is_primary IS 'Whether this is the primary skill for the tool';
COMMENT ON COLUMN mcp.tool_skill_assignments.source IS 'Origin of assignment: llm_auto, human_manual, human_override';


-- ═══════════════════════════════════════════════════════════════════════════════
-- Table: skill_suggestions
-- Purpose: LLM-suggested new skill categories pending human review
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mcp.skill_suggestions (
    id SERIAL PRIMARY KEY,

    -- Suggested skill details
    suggested_name VARCHAR(255) NOT NULL,
    suggested_description TEXT NOT NULL,

    -- Source context
    source_tool_id INTEGER REFERENCES mcp.tools(id) ON DELETE SET NULL,
    source_tool_name VARCHAR(255) NOT NULL,
    reasoning TEXT NOT NULL,

    -- Review status
    -- pending: Awaiting review
    -- approved: Approved and converted to skill_category
    -- rejected: Rejected by reviewer
    -- merged: Merged into existing skill
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'merged')),

    -- Resolution metadata
    resolved_by VARCHAR(100),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,

    -- If merged, which skill it was merged into
    merged_into_skill_id VARCHAR(100) REFERENCES mcp.skill_categories(id) ON DELETE SET NULL,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for skill_suggestions
CREATE INDEX IF NOT EXISTS idx_skill_suggestions_status ON mcp.skill_suggestions(status);
CREATE INDEX IF NOT EXISTS idx_skill_suggestions_name ON mcp.skill_suggestions(suggested_name);
CREATE INDEX IF NOT EXISTS idx_skill_suggestions_created ON mcp.skill_suggestions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_suggestions_source ON mcp.skill_suggestions(source_tool_id);

-- Comments
COMMENT ON TABLE mcp.skill_suggestions IS 'LLM-suggested new skills pending human review';
COMMENT ON COLUMN mcp.skill_suggestions.reasoning IS 'LLM explanation for why this skill is needed';
COMMENT ON COLUMN mcp.skill_suggestions.merged_into_skill_id IS 'If merged, the skill ID it was merged into';


-- ═══════════════════════════════════════════════════════════════════════════════
-- Triggers
-- ═══════════════════════════════════════════════════════════════════════════════

-- Updated_at trigger for skill_categories
CREATE OR REPLACE FUNCTION mcp.update_skill_categories_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER skill_categories_updated_at_trigger
    BEFORE UPDATE ON mcp.skill_categories
    FOR EACH ROW
    EXECUTE FUNCTION mcp.update_skill_categories_updated_at();

-- Updated_at trigger for tool_skill_assignments
CREATE OR REPLACE FUNCTION mcp.update_tool_skill_assignments_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tool_skill_assignments_updated_at_trigger
    BEFORE UPDATE ON mcp.tool_skill_assignments
    FOR EACH ROW
    EXECUTE FUNCTION mcp.update_tool_skill_assignments_updated_at();

-- Updated_at trigger for skill_suggestions
CREATE OR REPLACE FUNCTION mcp.update_skill_suggestions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER skill_suggestions_updated_at_trigger
    BEFORE UPDATE ON mcp.skill_suggestions
    FOR EACH ROW
    EXECUTE FUNCTION mcp.update_skill_suggestions_updated_at();


-- ═══════════════════════════════════════════════════════════════════════════════
-- Tool count maintenance trigger
-- Purpose: Keep tool_count in sync when assignments change
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION mcp.update_skill_tool_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE mcp.skill_categories
        SET tool_count = tool_count + 1, updated_at = NOW()
        WHERE id = NEW.skill_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE mcp.skill_categories
        SET tool_count = GREATEST(0, tool_count - 1), updated_at = NOW()
        WHERE id = OLD.skill_id;
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' AND OLD.skill_id != NEW.skill_id THEN
        -- Skill changed - decrement old, increment new
        UPDATE mcp.skill_categories
        SET tool_count = GREATEST(0, tool_count - 1), updated_at = NOW()
        WHERE id = OLD.skill_id;
        UPDATE mcp.skill_categories
        SET tool_count = tool_count + 1, updated_at = NOW()
        WHERE id = NEW.skill_id;
        RETURN NEW;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tool_skill_assignments_count_trigger
    AFTER INSERT OR UPDATE OR DELETE ON mcp.tool_skill_assignments
    FOR EACH ROW
    EXECUTE FUNCTION mcp.update_skill_tool_count();


-- ═══════════════════════════════════════════════════════════════════════════════
-- Ensure single primary skill per tool
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION mcp.ensure_single_primary_skill()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_primary = TRUE THEN
        -- Unset any existing primary for this tool
        UPDATE mcp.tool_skill_assignments
        SET is_primary = FALSE, updated_at = NOW()
        WHERE tool_id = NEW.tool_id
          AND skill_id != NEW.skill_id
          AND is_primary = TRUE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ensure_single_primary_skill_trigger
    BEFORE INSERT OR UPDATE OF is_primary ON mcp.tool_skill_assignments
    FOR EACH ROW
    WHEN (NEW.is_primary = TRUE)
    EXECUTE FUNCTION mcp.ensure_single_primary_skill();


-- ═══════════════════════════════════════════════════════════════════════════════
-- Grant permissions
-- ═══════════════════════════════════════════════════════════════════════════════

GRANT ALL ON TABLE mcp.skill_categories TO postgres;
GRANT ALL ON TABLE mcp.tool_skill_assignments TO postgres;
GRANT ALL ON TABLE mcp.skill_suggestions TO postgres;
GRANT ALL ON SEQUENCE mcp.skill_suggestions_id_seq TO postgres;
