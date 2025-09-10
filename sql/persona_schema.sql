-- ===========================================
-- User Persona Storage Schema with pgvector
-- ===========================================
-- 存储AI生成的用户画像文本和向量表示
-- 支持语义搜索和个性化推荐
-- ===========================================

-- 启用pgvector扩展（如果还没启用）
CREATE EXTENSION IF NOT EXISTS vector;

-- ===========================================
-- 用户Persona主表
-- ===========================================
CREATE TABLE IF NOT EXISTS user_personas (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- 完整的persona文本
    persona_text TEXT NOT NULL,
    
    -- 结构化persona内容（JSON格式）
    structured_persona JSONB,
    
    -- persona向量表示（用于语义搜索）- 使用1536维匹配text-embedding-3-small
    persona_vector VECTOR(1536),
    
    -- ML特征和金数据摘要
    ml_features_used JSONB,
    gold_data_summary JSONB,
    
    -- persona元数据
    generation_timestamp TIMESTAMPTZ NOT NULL,
    persona_version VARCHAR(20) DEFAULT '1.0',
    confidence_score DECIMAL(3,2) DEFAULT 0.5,
    persona_tags TEXT[] DEFAULT '{}',
    
    -- 使用统计
    last_accessed_at TIMESTAMPTZ,
    access_count INTEGER DEFAULT 0,
    
    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 约束
    CONSTRAINT chk_confidence_score CHECK (confidence_score BETWEEN 0 AND 1)
);

-- ===========================================
-- Persona版本历史表（支持persona演化跟踪）
-- ===========================================
CREATE TABLE IF NOT EXISTS user_persona_versions (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    version VARCHAR(20) NOT NULL,
    
    -- 历史persona数据
    persona_text TEXT NOT NULL,
    structured_persona JSONB,
    persona_vector VECTOR(1536),
    
    -- 版本变更信息
    change_reason VARCHAR(200),
    confidence_score DECIMAL(3,2),
    ml_features_snapshot JSONB,
    gold_data_snapshot JSONB,
    
    -- 版本元数据
    created_at TIMESTAMPTZ DEFAULT NOW(),
    replaced_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT FALSE,
    
    -- 外键
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- 唯一约束
    UNIQUE(user_id, version)
);

-- ===========================================
-- Persona标签表（支持标签管理和过滤）
-- ===========================================
CREATE TABLE IF NOT EXISTS persona_tags (
    id SERIAL PRIMARY KEY,
    tag_name VARCHAR(100) UNIQUE NOT NULL,
    tag_category VARCHAR(50), -- 'technical', 'role', 'behavior', 'pattern'
    tag_description TEXT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 预填充常用标签
INSERT INTO persona_tags (tag_name, tag_category, tag_description) VALUES
-- 技术标签
('tech_python', 'technical', 'Python programming skills'),
('tech_javascript', 'technical', 'JavaScript programming skills'),
('tech_sql', 'technical', 'SQL database skills'),
('tech_react', 'technical', 'React framework skills'),
('tech_fastapi', 'technical', 'FastAPI framework skills'),
('tech_aws', 'technical', 'Amazon Web Services skills'),
('tech_docker', 'technical', 'Docker containerization skills'),

-- 角色标签
('role_developer', 'role', 'Software developer/engineer'),
('role_data_professional', 'role', 'Data scientist or analyst'),
('role_learner', 'role', 'Student or learning-focused user'),
('role_researcher', 'role', 'Research or academic focus'),

-- 行为模式标签
('pattern_morning_person', 'behavior', 'Most active in morning hours'),
('pattern_night_owl', 'behavior', 'Most active in evening/night hours'),
('pattern_consistent', 'behavior', 'Consistent usage patterns'),
('pattern_variable', 'behavior', 'Variable usage patterns'),

-- 使用强度标签
('usage_heavy', 'usage', 'Heavy/intensive usage'),
('usage_moderate', 'usage', 'Moderate usage intensity'),
('usage_light', 'usage', 'Light usage intensity')
ON CONFLICT (tag_name) DO NOTHING;

-- ===========================================
-- Persona相似度和推荐表
-- ===========================================
CREATE TABLE IF NOT EXISTS persona_similarities (
    id BIGSERIAL PRIMARY KEY,
    user_id_1 VARCHAR(255) NOT NULL,
    user_id_2 VARCHAR(255) NOT NULL,
    
    -- 相似度计算
    vector_similarity DECIMAL(5,4), -- 向量余弦相似度
    tag_overlap_score DECIMAL(5,4), -- 标签重叠评分
    ml_pattern_similarity DECIMAL(5,4), -- ML模式相似度
    overall_similarity DECIMAL(5,4), -- 综合相似度
    
    -- 计算元数据
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    calculation_version VARCHAR(10) DEFAULT '1.0',
    
    -- 约束
    CONSTRAINT chk_different_users CHECK (user_id_1 != user_id_2),
    CONSTRAINT chk_similarity_range CHECK (
        overall_similarity BETWEEN 0 AND 1 AND
        vector_similarity BETWEEN -1 AND 1
    ),
    
    -- 唯一约束（避免重复计算）
    UNIQUE(user_id_1, user_id_2)
);

-- ===========================================
-- 性能优化索引
-- ===========================================

-- user_personas表索引
CREATE INDEX IF NOT EXISTS idx_personas_user_id ON user_personas(user_id);
CREATE INDEX IF NOT EXISTS idx_personas_confidence ON user_personas(confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_personas_tags ON user_personas USING GIN(persona_tags);
CREATE INDEX IF NOT EXISTS idx_personas_generation_time ON user_personas(generation_timestamp DESC);

-- pgvector向量相似度搜索索引（HNSW算法，适合高维向量）
CREATE INDEX IF NOT EXISTS idx_personas_vector_hnsw ON user_personas 
USING hnsw (persona_vector vector_cosine_ops);

-- 如果需要L2距离搜索，也可以创建L2索引
-- CREATE INDEX IF NOT EXISTS idx_personas_vector_l2 ON user_personas 
-- USING hnsw (persona_vector vector_l2_ops);

-- persona_versions表索引
CREATE INDEX IF NOT EXISTS idx_persona_versions_user ON user_persona_versions(user_id, version);
CREATE INDEX IF NOT EXISTS idx_persona_versions_active ON user_persona_versions(user_id, is_active) WHERE is_active = TRUE;

-- persona_similarities表索引  
CREATE INDEX IF NOT EXISTS idx_similarities_user1 ON persona_similarities(user_id_1, overall_similarity DESC);
CREATE INDEX IF NOT EXISTS idx_similarities_user2 ON persona_similarities(user_id_2, overall_similarity DESC);
CREATE INDEX IF NOT EXISTS idx_similarities_overall ON persona_similarities(overall_similarity DESC);

-- persona_tags表索引
CREATE INDEX IF NOT EXISTS idx_tags_category ON persona_tags(tag_category);
CREATE INDEX IF NOT EXISTS idx_tags_usage ON persona_tags(usage_count DESC);

-- ===========================================
-- 实用的查询视图
-- ===========================================

-- 高质量persona视图（置信度 > 0.7）
CREATE OR REPLACE VIEW high_quality_personas AS
SELECT 
    user_id,
    persona_text,
    structured_persona,
    confidence_score,
    persona_tags,
    generation_timestamp,
    access_count
FROM user_personas
WHERE confidence_score > 0.7
  AND persona_text IS NOT NULL
  AND LENGTH(persona_text) > 500;

-- 最近生成的persona视图
CREATE OR REPLACE VIEW recent_personas AS
SELECT 
    user_id,
    persona_text,
    confidence_score,
    persona_tags,
    generation_timestamp,
    EXTRACT(DAYS FROM NOW() - generation_timestamp) as days_ago
FROM user_personas
WHERE generation_timestamp > NOW() - INTERVAL '30 days'
ORDER BY generation_timestamp DESC;

-- persona标签统计视图
CREATE OR REPLACE VIEW persona_tag_stats AS
SELECT 
    unnest(persona_tags) as tag,
    COUNT(*) as usage_count,
    AVG(confidence_score) as avg_confidence,
    COUNT(*) * 1.0 / (SELECT COUNT(*) FROM user_personas) as tag_frequency
FROM user_personas
WHERE persona_tags IS NOT NULL
GROUP BY unnest(persona_tags)
ORDER BY usage_count DESC;

-- ===========================================
-- 向量搜索和相似度计算函数
-- ===========================================

-- 查找相似的persona用户
CREATE OR REPLACE FUNCTION find_similar_personas(
    target_user_id VARCHAR(255),
    similarity_threshold DECIMAL DEFAULT 0.7,
    max_results INTEGER DEFAULT 10
) RETURNS TABLE (
    similar_user_id VARCHAR(255),
    similarity_score DECIMAL,
    shared_tags TEXT[],
    persona_summary TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p2.user_id,
        (1 - (p1.persona_vector <-> p2.persona_vector))::DECIMAL as similarity,
        ARRAY(
            SELECT DISTINCT unnest(p1.persona_tags) 
            INTERSECT 
            SELECT DISTINCT unnest(p2.persona_tags)
        ) as shared_tags,
        LEFT(p2.persona_text, 200) || '...' as summary
    FROM user_personas p1
    JOIN user_personas p2 ON p1.user_id != p2.user_id
    WHERE p1.user_id = target_user_id
      AND p1.persona_vector IS NOT NULL
      AND p2.persona_vector IS NOT NULL
      AND (1 - (p1.persona_vector <-> p2.persona_vector)) > similarity_threshold
    ORDER BY similarity DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- 更新persona向量的函数
CREATE OR REPLACE FUNCTION update_persona_vector(
    target_user_id VARCHAR(255),
    new_vector VECTOR(1536)
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE user_personas 
    SET persona_vector = new_vector,
        updated_at = NOW()
    WHERE user_id = target_user_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- ===========================================
-- 触发器：自动更新相关统计
-- ===========================================

-- 更新标签使用统计的函数
CREATE OR REPLACE FUNCTION update_tag_usage_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- 增加新标签的使用计数
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        UPDATE persona_tags 
        SET usage_count = usage_count + 1
        WHERE tag_name = ANY(NEW.persona_tags);
    END IF;
    
    -- 减少删除标签的使用计数
    IF TG_OP = 'DELETE' OR TG_OP = 'UPDATE' THEN
        UPDATE persona_tags 
        SET usage_count = GREATEST(0, usage_count - 1)
        WHERE tag_name = ANY(OLD.persona_tags);
    END IF;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- 应用触发器
CREATE TRIGGER trg_update_tag_stats
    AFTER INSERT OR UPDATE OR DELETE ON user_personas
    FOR EACH ROW
    EXECUTE FUNCTION update_tag_usage_stats();

-- 自动更新updated_at字段的触发器
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_personas_updated_at
    BEFORE UPDATE ON user_personas
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ===========================================
-- 示例查询
-- ===========================================

-- 查找技术相关的用户persona
-- SELECT user_id, persona_tags, confidence_score 
-- FROM user_personas 
-- WHERE persona_tags && ARRAY['tech_python', 'tech_javascript', 'role_developer'];

-- 查找最相似的用户
-- SELECT * FROM find_similar_personas('user-123', 0.8, 5);

-- 向量相似度搜索（查找与特定向量最相似的persona）
-- SELECT user_id, persona_vector <-> '[0.1,0.2,...]'::vector as distance
-- FROM user_personas 
-- ORDER BY persona_vector <-> '[0.1,0.2,...]'::vector 
-- LIMIT 10;

-- 统计persona生成效果
-- SELECT 
--     COUNT(*) as total_personas,
--     AVG(confidence_score) as avg_confidence,
--     COUNT(*) FILTER (WHERE confidence_score > 0.8) as high_confidence_count
-- FROM user_personas;