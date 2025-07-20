# 基于Supabase + pgvector的AI Agent记忆系统设计

## 核心设计理念
- **以记忆类型为核心**：按照认知科学的记忆分类进行设计
- **存储提取后的结构化记忆**：不存储原始对话，只存储LLM提取的有价值信息
- **向量检索优先**：利用pgvector进行语义相似度检索

## 1. 事实性记忆表 (factual_memories)

```sql
CREATE TABLE factual_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- 事实内容
    fact_type VARCHAR(50) NOT NULL, -- 'personal_info', 'preference', 'skill', 'experience', 'knowledge'
    subject VARCHAR(200) NOT NULL, -- 事实的主体/主题
    predicate VARCHAR(200) NOT NULL, -- 属性/关系
    object_value TEXT NOT NULL, -- 值/对象
    
    -- 附加信息
    context TEXT, -- 事实的上下文
    confidence FLOAT DEFAULT 0.8 CHECK (confidence >= 0 AND confidence <= 1),
    source_interaction_id UUID, -- 来源交互的ID（可选）
    
    -- 向量检索
    embedding VECTOR(1536),
    
    -- 生命周期
    importance_score FLOAT DEFAULT 0.5,
    last_confirmed_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 避免重复事实
    UNIQUE(user_id, fact_type, subject, predicate)
);

-- 索引
CREATE INDEX idx_factual_user_type ON factual_memories(user_id, fact_type);
CREATE INDEX idx_factual_subject ON factual_memories(user_id, subject);
CREATE INDEX idx_factual_embedding ON factual_memories USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_factual_importance ON factual_memories(importance_score DESC);
```

## 2. 程序性记忆表 (procedural_memories)

```sql
CREATE TABLE procedural_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- 程序内容
    procedure_name VARCHAR(200) NOT NULL,
    domain VARCHAR(100) NOT NULL, -- 'work', 'personal', 'technical', etc.
    trigger_conditions JSONB NOT NULL, -- 触发条件
    steps JSONB NOT NULL, -- 步骤序列
    expected_outcome TEXT,
    
    -- 执行统计
    success_rate FLOAT DEFAULT 0.0,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    
    -- 向量检索
    embedding VECTOR(1536),
    
    -- 元信息
    difficulty_level INTEGER CHECK (difficulty_level >= 1 AND difficulty_level <= 5),
    estimated_time_minutes INTEGER,
    required_tools JSONB DEFAULT '[]',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, procedure_name, domain)
);

CREATE INDEX idx_procedural_user_domain ON procedural_memories(user_id, domain);
CREATE INDEX idx_procedural_embedding ON procedural_memories USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_procedural_usage ON procedural_memories(usage_count DESC);
```

## 3. 情景记忆表 (episodic_memories)

```sql
CREATE TABLE episodic_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- 情景内容
    episode_title VARCHAR(300) NOT NULL,
    summary TEXT NOT NULL,
    participants JSONB DEFAULT '[]', -- 参与者列表
    location VARCHAR(200),
    temporal_context VARCHAR(100), -- 'morning', 'last week', 'during vacation'
    
    -- 情景细节
    key_events JSONB NOT NULL, -- 关键事件序列
    emotional_context VARCHAR(50), -- 'positive', 'stressful', 'exciting'
    outcomes JSONB DEFAULT '[]', -- 结果和后果
    lessons_learned TEXT,
    
    -- 向量检索
    embedding VECTOR(1536),
    
    -- 重要性和回忆
    emotional_intensity FLOAT DEFAULT 0.5 CHECK (emotional_intensity >= 0 AND emotional_intensity <= 1),
    recall_frequency INTEGER DEFAULT 0,
    last_recalled_at TIMESTAMPTZ,
    
    -- 时间信息
    occurred_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_episodic_user_time ON episodic_memories(user_id, occurred_at DESC);
CREATE INDEX idx_episodic_embedding ON episodic_memories USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_episodic_emotional ON episodic_memories(emotional_intensity DESC);
CREATE INDEX idx_episodic_location ON episodic_memories(user_id, location) WHERE location IS NOT NULL;
```

## 4. 语义记忆表 (semantic_memories)

```sql
CREATE TABLE semantic_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- 概念内容
    concept_name VARCHAR(200) NOT NULL,
    concept_category VARCHAR(100) NOT NULL,
    definition TEXT NOT NULL,
    properties JSONB DEFAULT '{}', -- 概念的属性
    
    -- 关系信息
    related_concepts JSONB DEFAULT '[]', -- 相关概念列表
    hierarchical_level INTEGER DEFAULT 0, -- 概念层级
    parent_concept_id UUID REFERENCES semantic_memories(id),
    
    -- 应用场景
    use_cases JSONB DEFAULT '[]',
    examples JSONB DEFAULT '[]',
    
    -- 向量检索
    embedding VECTOR(1536),
    
    -- 学习信息
    mastery_level FLOAT DEFAULT 0.5 CHECK (mastery_level >= 0 AND mastery_level <= 1),
    learning_source VARCHAR(100),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, concept_name, concept_category)
);

CREATE INDEX idx_semantic_user_category ON semantic_memories(user_id, concept_category);
CREATE INDEX idx_semantic_embedding ON semantic_memories USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_semantic_hierarchy ON semantic_memories(parent_concept_id) WHERE parent_concept_id IS NOT NULL;
CREATE INDEX idx_semantic_mastery ON semantic_memories(mastery_level DESC);
```

## 5. 工作记忆表 (working_memories)

```sql
CREATE TABLE working_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- 工作内容
    context_type VARCHAR(50) NOT NULL, -- 'task', 'conversation', 'problem_solving'
    context_id VARCHAR(200) NOT NULL, -- 关联的上下文ID
    state_data JSONB NOT NULL, -- 当前状态数据
    
    -- 进度信息
    current_step VARCHAR(200),
    progress_percentage FLOAT DEFAULT 0.0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    next_actions JSONB DEFAULT '[]',
    
    -- 依赖和阻塞
    dependencies JSONB DEFAULT '[]',
    blocking_issues JSONB DEFAULT '[]',
    
    -- 向量检索
    embedding VECTOR(1536),
    
    -- 生命周期（工作记忆通常是短期的）
    priority INTEGER DEFAULT 3 CHECK (priority >= 1 AND priority <= 5),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours'),
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, context_type, context_id)
);

CREATE INDEX idx_working_user_type ON working_memories(user_id, context_type);
CREATE INDEX idx_working_embedding ON working_memories USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_working_active ON working_memories(user_id, is_active, expires_at) WHERE is_active = true;
CREATE INDEX idx_working_priority ON working_memories(priority DESC);
```

## 6. 记忆关联表 (memory_associations)

```sql
CREATE TABLE memory_associations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- 关联的记忆
    source_memory_type VARCHAR(20) NOT NULL CHECK (source_memory_type IN ('factual', 'procedural', 'episodic', 'semantic', 'working')),
    source_memory_id UUID NOT NULL,
    target_memory_type VARCHAR(20) NOT NULL CHECK (target_memory_type IN ('factual', 'procedural', 'episodic', 'semantic', 'working')),
    target_memory_id UUID NOT NULL,
    
    -- 关联信息
    association_type VARCHAR(50) NOT NULL, -- 'related_to', 'caused_by', 'example_of', 'used_in'
    strength FLOAT DEFAULT 0.5 CHECK (strength >= 0 AND strength <= 1),
    context TEXT,
    
    -- 学习信息
    auto_discovered BOOLEAN DEFAULT false,
    confirmation_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, source_memory_type, source_memory_id, target_memory_type, target_memory_id, association_type)
);

CREATE INDEX idx_associations_user ON memory_associations(user_id);
CREATE INDEX idx_associations_source ON memory_associations(source_memory_type, source_memory_id);
CREATE INDEX idx_associations_target ON memory_associations(target_memory_type, target_memory_id);
CREATE INDEX idx_associations_strength ON memory_associations(strength DESC);

## 7. 记忆元数据表 (memory_metadata)

```sql
CREATE TABLE memory_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- 记忆引用信息
    memory_type VARCHAR(20) NOT NULL CHECK (memory_type IN ('factual', 'procedural', 'episodic', 'semantic', 'working')),
    memory_id UUID NOT NULL,
    
    -- 访问统计
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    first_accessed_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 修改历史
    modification_count INTEGER DEFAULT 0,
    last_modified_at TIMESTAMPTZ,
    version INTEGER DEFAULT 1,
    
    -- 质量评估
    accuracy_score FLOAT CHECK (accuracy_score >= 0 AND accuracy_score <= 1),
    relevance_score FLOAT CHECK (relevance_score >= 0 AND relevance_score <= 1),
    completeness_score FLOAT CHECK (completeness_score >= 0 AND completeness_score <= 1),
    
    -- 用户反馈
    user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 5),
    user_feedback TEXT,
    feedback_timestamp TIMESTAMPTZ,
    
    -- 系统标记
    system_flags JSONB DEFAULT '{}', -- 系统标记：{'outdated': true, 'conflicting': true, 'needs_review': true}
    priority_level INTEGER DEFAULT 3 CHECK (priority_level >= 1 AND priority_level <= 5),
    
    -- 关联和依赖
    dependency_count INTEGER DEFAULT 0, -- 有多少其他记忆依赖这个
    reference_count INTEGER DEFAULT 0, -- 被引用的次数
    
    -- 生命周期管理
    lifecycle_stage VARCHAR(20) DEFAULT 'active' CHECK (lifecycle_stage IN ('active', 'stale', 'deprecated', 'archived')),
    auto_expire BOOLEAN DEFAULT false,
    expire_after_days INTEGER,
    
    -- 学习和强化
    reinforcement_score FLOAT DEFAULT 0.0, -- 强化学习得分
    learning_curve JSONB DEFAULT '[]', -- 学习曲线数据
    
    -- 元数据时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, memory_type, memory_id)
);

-- 索引
CREATE INDEX idx_metadata_user_type ON memory_metadata(user_id, memory_type);
CREATE INDEX idx_metadata_memory ON memory_metadata(memory_type, memory_id);
CREATE INDEX idx_metadata_access ON memory_metadata(access_count DESC);
CREATE INDEX idx_metadata_quality ON memory_metadata(accuracy_score DESC, relevance_score DESC);
CREATE INDEX idx_metadata_lifecycle ON memory_metadata(lifecycle_stage);
CREATE INDEX idx_metadata_priority ON memory_metadata(priority_level DESC);
CREATE INDEX idx_metadata_flags ON memory_metadata USING gin(system_flags) WHERE system_flags != '{}';
```

## 8. 记忆统计汇总表 (memory_statistics)

```sql
CREATE TABLE memory_statistics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- 统计时间范围
    period_type VARCHAR(20) NOT NULL CHECK (period_type IN ('daily', 'weekly', 'monthly', 'yearly')),
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    
    -- 各类记忆统计
    factual_count INTEGER DEFAULT 0,
    procedural_count INTEGER DEFAULT 0,
    episodic_count INTEGER DEFAULT 0,
    semantic_count INTEGER DEFAULT 0,
    working_count INTEGER DEFAULT 0,
    
    -- 访问统计
    total_accesses INTEGER DEFAULT 0,
    unique_memories_accessed INTEGER DEFAULT 0,
    avg_access_per_memory FLOAT DEFAULT 0.0,
    
    -- 质量统计
    avg_accuracy_score FLOAT,
    avg_relevance_score FLOAT,
    avg_completeness_score FLOAT,
    
    -- 生命周期统计
    memories_created INTEGER DEFAULT 0,
    memories_updated INTEGER DEFAULT 0,
    memories_archived INTEGER DEFAULT 0,
    memories_expired INTEGER DEFAULT 0,
    
    -- 学习效果统计
    learning_events INTEGER DEFAULT 0,
    reinforcement_events INTEGER DEFAULT 0,
    user_feedback_count INTEGER DEFAULT 0,
    avg_user_rating FLOAT,
    
    -- 存储统计
    total_storage_mb FLOAT DEFAULT 0.0,
    embedding_storage_mb FLOAT DEFAULT 0.0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, period_type, period_start)
);

CREATE INDEX idx_statistics_user_period ON memory_statistics(user_id, period_type, period_start DESC);
CREATE INDEX idx_statistics_period ON memory_statistics(period_start DESC);

## 9. 记忆配置表 (memory_config)

```sql
CREATE TABLE memory_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- 记忆容量配置
    max_factual_memories INTEGER DEFAULT 10000,
    max_procedural_memories INTEGER DEFAULT 1000,
    max_episodic_memories INTEGER DEFAULT 5000,
    max_semantic_memories INTEGER DEFAULT 3000,
    max_working_memories INTEGER DEFAULT 100,
    
    -- 质量阈值配置
    min_confidence_threshold FLOAT DEFAULT 0.6,
    min_importance_threshold FLOAT DEFAULT 0.3,
    auto_archive_threshold FLOAT DEFAULT 0.2,
    
    -- 生命周期配置
    factual_default_ttl_days INTEGER DEFAULT 365,
    procedural_default_ttl_days INTEGER DEFAULT 180,
    episodic_default_ttl_days INTEGER DEFAULT 90,
    semantic_default_ttl_days INTEGER DEFAULT 730,
    working_default_ttl_days INTEGER DEFAULT 1,
    
    -- 检索配置
    default_similarity_threshold FLOAT DEFAULT 0.7,
    max_results_per_query INTEGER DEFAULT 20,
    enable_cross_memory_associations BOOLEAN DEFAULT true,
    
    -- 学习配置
    learning_rate FLOAT DEFAULT 0.1,
    reinforcement_decay FLOAT DEFAULT 0.95,
    enable_auto_learning BOOLEAN DEFAULT true,
    
    -- 隐私配置
    allow_sensitive_data BOOLEAN DEFAULT false,
    data_retention_days INTEGER DEFAULT 1095, -- 3年
    enable_encryption BOOLEAN DEFAULT true,
    
    -- 系统配置
    enable_background_processing BOOLEAN DEFAULT true,
    processing_batch_size INTEGER DEFAULT 100,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id)
);

CREATE INDEX idx_config_user ON memory_config(user_id);
```

## 10. 触发器和自动化函数

```sql
-- 自动更新元数据的触发器函数
CREATE OR REPLACE FUNCTION update_memory_metadata()
RETURNS TRIGGER AS $
BEGIN
    -- 更新或插入元数据
    INSERT INTO memory_metadata (user_id, memory_type, memory_id, modification_count, last_modified_at, version)
    VALUES (NEW.user_id, TG_TABLE_NAME, NEW.id, 1, NOW(), 1)
    ON CONFLICT (user_id, memory_type, memory_id)
    DO UPDATE SET
        modification_count = memory_metadata.modification_count + 1,
        last_modified_at = NOW(),
        version = memory_metadata.version + 1,
        updated_at = NOW();
    
    RETURN NEW;
END;
$ LANGUAGE plpgsql;

-- 为各个记忆表添加触发器
CREATE TRIGGER factual_metadata_trigger
    AFTER INSERT OR UPDATE ON factual_memories
    FOR EACH ROW EXECUTE FUNCTION update_memory_metadata();

CREATE TRIGGER procedural_metadata_trigger
    AFTER INSERT OR UPDATE ON procedural_memories
    FOR EACH ROW EXECUTE FUNCTION update_memory_metadata();

CREATE TRIGGER episodic_metadata_trigger
    AFTER INSERT OR UPDATE ON episodic_memories
    FOR EACH ROW EXECUTE FUNCTION update_memory_metadata();

CREATE TRIGGER semantic_metadata_trigger
    AFTER INSERT OR UPDATE ON semantic_memories
    FOR EACH ROW EXECUTE FUNCTION update_memory_metadata();

CREATE TRIGGER working_metadata_trigger
    AFTER INSERT OR UPDATE ON working_memories
    FOR EACH ROW EXECUTE FUNCTION update_memory_metadata();

-- 自动清理过期工作记忆的函数
CREATE OR REPLACE FUNCTION cleanup_expired_memories()
RETURNS INTEGER AS $
DECLARE
    expired_count INTEGER;
BEGIN
    -- 清理过期的工作记忆
    WITH expired_memories AS (
        UPDATE working_memories 
        SET is_active = false 
        WHERE expires_at < NOW() AND is_active = true
        RETURNING id
    )
    SELECT COUNT(*) INTO expired_count FROM expired_memories;
    
    -- 更新元数据
    UPDATE memory_metadata 
    SET lifecycle_stage = 'archived', updated_at = NOW()
    WHERE memory_type = 'working' 
    AND memory_id IN (
        SELECT id FROM working_memories 
        WHERE expires_at < NOW() AND is_active = false
    );
    
    RETURN expired_count;
END;
$ LANGUAGE plpgsql;

-- 记忆访问追踪函数
CREATE OR REPLACE FUNCTION track_memory_access(
    p_user_id UUID,
    p_memory_type VARCHAR(20),
    p_memory_id UUID
) RETURNS VOID AS $
BEGIN
    -- 更新元数据中的访问统计
    INSERT INTO memory_metadata (user_id, memory_type, memory_id, access_count, last_accessed_at)
    VALUES (p_user_id, p_memory_type, p_memory_id, 1, NOW())
    ON CONFLICT (user_id, memory_type, memory_id)
    DO UPDATE SET
        access_count = memory_metadata.access_count + 1,
        last_accessed_at = NOW(),
        updated_at = NOW();
END;
$ LANGUAGE plpgsql;
```
```
```

## 7. 记忆提取日志表 (memory_extraction_logs)

```sql
CREATE TABLE memory_extraction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- 提取信息
    extraction_session_id UUID NOT NULL,
    source_content_hash VARCHAR(64), -- 原始内容的hash，用于去重
    
    -- 提取结果
    extracted_memories JSONB NOT NULL, -- 提取出的记忆列表
    extraction_method VARCHAR(50) NOT NULL, -- 'llm_structured', 'llm_free_form', 'rule_based'
    
    -- 质量评估
    confidence_score FLOAT,
    human_verified BOOLEAN DEFAULT false,
    verification_feedback TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_extraction_user ON memory_extraction_logs(user_id);
CREATE INDEX idx_extraction_session ON memory_extraction_logs(extraction_session_id);
CREATE INDEX idx_extraction_hash ON memory_extraction_logs(source_content_hash);
```

## 8. RLS安全策略

```sql
-- 启用行级安全
ALTER TABLE factual_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE procedural_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE episodic_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE semantic_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE working_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_associations ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_extraction_logs ENABLE ROW LEVEL SECURITY;

-- 用户只能访问自己的记忆
CREATE POLICY user_factual_policy ON factual_memories FOR ALL USING (auth.uid() = user_id);
CREATE POLICY user_procedural_policy ON procedural_memories FOR ALL USING (auth.uid() = user_id);
CREATE POLICY user_episodic_policy ON episodic_memories FOR ALL USING (auth.uid() = user_id);
CREATE POLICY user_semantic_policy ON semantic_memories FOR ALL USING (auth.uid() = user_id);
CREATE POLICY user_working_policy ON working_memories FOR ALL USING (auth.uid() = user_id);
CREATE POLICY user_associations_policy ON memory_associations FOR ALL USING (auth.uid() = user_id);
CREATE POLICY user_extraction_policy ON memory_extraction_logs FOR ALL USING (auth.uid() = user_id);
```

## 9. 记忆检索函数

```sql
-- 语义相似度检索函数
CREATE OR REPLACE FUNCTION search_memories_by_similarity(
    p_user_id UUID,
    p_query_embedding VECTOR(1536),
    p_memory_types TEXT[] DEFAULT ARRAY['factual', 'procedural', 'episodic', 'semantic'],
    p_limit INTEGER DEFAULT 10,
    p_threshold FLOAT DEFAULT 0.7
) RETURNS TABLE (
    memory_type TEXT,
    memory_id UUID,
    content TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    (
        SELECT 'factual'::TEXT, f.id, f.subject || ': ' || f.object_value, 1 - (f.embedding <=> p_query_embedding)
        FROM factual_memories f
        WHERE f.user_id = p_user_id 
        AND f.is_active = true
        AND 'factual' = ANY(p_memory_types)
        AND 1 - (f.embedding <=> p_query_embedding) > p_threshold
        
        UNION ALL
        
        SELECT 'procedural'::TEXT, pr.id, pr.procedure_name, 1 - (pr.embedding <=> p_query_embedding)
        FROM procedural_memories pr
        WHERE pr.user_id = p_user_id
        AND 'procedural' = ANY(p_memory_types)
        AND 1 - (pr.embedding <=> p_query_embedding) > p_threshold
        
        UNION ALL
        
        SELECT 'episodic'::TEXT, e.id, e.episode_title, 1 - (e.embedding <=> p_query_embedding)
        FROM episodic_memories e
        WHERE e.user_id = p_user_id
        AND 'episodic' = ANY(p_memory_types)
        AND 1 - (e.embedding <=> p_query_embedding) > p_threshold
        
        UNION ALL
        
        SELECT 'semantic'::TEXT, s.id, s.concept_name || ': ' || s.definition, 1 - (s.embedding <=> p_query_embedding)
        FROM semantic_memories s
        WHERE s.user_id = p_user_id
        AND 'semantic' = ANY(p_memory_types)
        AND 1 - (s.embedding <=> p_query_embedding) > p_threshold
    )
    ORDER BY similarity DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;
```

## 使用示例

```sql
-- 检索与"工作流程"相关的记忆
SELECT * FROM search_memories_by_similarity(
    'user-uuid-here',
    '[embedding-vector-here]',
    ARRAY['procedural', 'factual'],
    5,
    0.8
);

-- 获取用户的所有技能类事实记忆
SELECT subject, object_value, confidence 
FROM factual_memories 
WHERE user_id = 'user-uuid' 
AND fact_type = 'skill' 
AND is_active = true
ORDER BY importance_score DESC;
```