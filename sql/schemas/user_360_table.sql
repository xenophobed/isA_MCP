-- ===========================================
-- User360 大宽表 - 完整的用户画像数据仓库
-- ===========================================
-- 将所有用户相关数据汇聚到一个宽表，支持高效的ML训练和预测
-- 数据源: Memory Service + User Service + Session Service + RudderStack + System Metrics

CREATE TABLE IF NOT EXISTS user_360_profile (
    -- ===========================================
    -- 主键和基础标识
    -- ===========================================
    user_id VARCHAR(255) PRIMARY KEY,
    org_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- ===========================================
    -- 基础用户信息 (来源: users表)
    -- ===========================================
    email TEXT,
    username TEXT,
    registration_date TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    account_status TEXT, -- active, suspended, inactive
    subscription_tier TEXT, -- free, pro, enterprise
    timezone TEXT,
    locale TEXT,
    
    -- ===========================================
    -- 会话统计维度 (来源: sessions表聚合)
    -- ===========================================
    total_sessions INTEGER DEFAULT 0,
    total_session_duration_minutes FLOAT DEFAULT 0,
    avg_session_duration_minutes FLOAT DEFAULT 0,
    max_session_duration_minutes FLOAT DEFAULT 0,
    sessions_last_7_days INTEGER DEFAULT 0,
    sessions_last_30_days INTEGER DEFAULT 0,
    last_session_date TIMESTAMPTZ,
    
    -- 会话模式分析
    peak_usage_hours INTEGER[], -- [9,14,20] 最活跃时间段
    weekly_usage_pattern JSONB, -- {"monday": 0.8, "tuesday": 0.6, "wednesday": 0.9, ...}
    session_frequency_score FLOAT DEFAULT 0, -- 0-1, 会话频率评分
    session_consistency_score FLOAT DEFAULT 0, -- 0-1, 使用规律性评分
    
    -- ===========================================
    -- Memory Service数据聚合 (来源: memory_*表)
    -- ===========================================
    total_messages INTEGER DEFAULT 0,
    total_conversations INTEGER DEFAULT 0,
    avg_messages_per_conversation FLOAT DEFAULT 0,
    
    -- Session Memory统计
    session_memory_count INTEGER DEFAULT 0,
    avg_session_summary_length FLOAT DEFAULT 0,
    session_topic_diversity_score FLOAT DEFAULT 0,
    
    -- Factual Memory统计
    factual_memory_count INTEGER DEFAULT 0,
    knowledge_domains TEXT[], -- ["python", "data_science", "web_dev"]
    expertise_confidence_scores JSONB, -- {"python": 0.9, "ml": 0.7}
    
    -- Episodic Memory统计
    episodic_memory_count INTEGER DEFAULT 0,
    project_completion_rate FLOAT DEFAULT 0,
    success_pattern_indicators JSONB,
    failure_pattern_indicators JSONB,
    
    -- Procedural Memory统计
    procedural_memory_count INTEGER DEFAULT 0,
    skill_acquisition_rate FLOAT DEFAULT 0,
    tool_proficiency_scores JSONB, -- {"jupyter": 0.8, "vscode": 0.9}
    
    -- Working Memory统计
    working_memory_usage_score FLOAT DEFAULT 0,
    context_switching_frequency FLOAT DEFAULT 0,
    
    -- Semantic Memory统计
    semantic_memory_count INTEGER DEFAULT 0,
    conceptual_understanding_score FLOAT DEFAULT 0,
    
    -- ===========================================
    -- 行为模式维度 (来源: RudderStack Events)
    -- ===========================================
    -- 页面访问模式
    total_page_views INTEGER DEFAULT 0,
    unique_pages_visited INTEGER DEFAULT 0,
    avg_time_on_page_seconds FLOAT DEFAULT 0,
    bounce_rate FLOAT DEFAULT 0,
    most_visited_pages JSONB, -- [{"page": "/chat", "count": 150}, ...]
    
    -- 功能使用模式
    feature_usage_counts JSONB, -- {"chat": 200, "file_upload": 50, "memory_search": 30}
    feature_adoption_timeline JSONB, -- 功能首次使用时间
    feature_engagement_scores JSONB, -- 各功能的参与度评分
    
    -- 交互行为模式
    click_patterns JSONB, -- 点击行为分析
    scroll_patterns JSONB, -- 滚动行为分析
    input_patterns JSONB, -- 输入行为模式(平均输入长度、频率等)
    
    -- ===========================================
    -- 任务和项目维度 (来源: 对话内容AI分析)
    -- ===========================================
    primary_use_cases TEXT[], -- ["data_analysis", "coding", "writing"]
    project_types JSONB, -- 项目类型分布
    task_complexity_preference TEXT, -- simple, moderate, complex
    collaboration_style TEXT, -- individual, team, mixed
    
    -- 技能和工具偏好
    programming_languages JSONB, -- {"python": 0.9, "javascript": 0.7}
    frameworks_and_tools JSONB, -- {"react": 0.8, "pandas": 0.9}
    domain_expertise JSONB, -- {"machine_learning": "expert", "web_dev": "intermediate"}
    
    -- ===========================================
    -- 交互风格维度 (来源: 对话模式AI分析)
    -- ===========================================
    communication_style TEXT, -- technical, conversational, direct, detailed
    preferred_explanation_level TEXT, -- beginner, intermediate, expert
    verbosity_preference TEXT, -- concise, moderate, detailed
    question_asking_frequency FLOAT DEFAULT 0, -- 提问频率
    help_seeking_pattern TEXT, -- proactive, reactive, independent
    
    -- ===========================================
    -- 性能和系统维度 (来源: System Metrics)
    -- ===========================================
    -- 资源使用模式
    avg_cpu_usage FLOAT DEFAULT 0,
    avg_memory_usage FLOAT DEFAULT 0,
    avg_response_time_ms FLOAT DEFAULT 0,
    error_rate FLOAT DEFAULT 0,
    
    -- 性能偏好指标
    performance_sensitivity_score FLOAT DEFAULT 0, -- 对性能的敏感度
    resource_efficiency_score FLOAT DEFAULT 0, -- 资源使用效率
    
    -- ===========================================
    -- 时间序列特征 (来源: 时序分析)
    -- ===========================================
    -- 季节性模式
    seasonal_patterns JSONB, -- 季节性使用模式
    trend_indicators JSONB, -- 长期趋势指标
    cyclical_behaviors JSONB, -- 周期性行为模式
    
    -- 时间偏好
    preferred_work_hours JSONB, -- 偏好的工作时间段
    timezone_adaptation_score FLOAT DEFAULT 0, -- 时区适应性
    
    -- ===========================================
    -- 预测相关特征 (来源: ML Feature Engineering)
    -- ===========================================
    -- 用户生命周期
    user_lifecycle_stage TEXT, -- onboarding, active, mature, at_risk, churned
    engagement_trend TEXT, -- increasing, stable, declining
    churn_risk_score FLOAT DEFAULT 0, -- 0-1, 流失风险评分
    
    -- 个性化特征
    personalization_readiness_score FLOAT DEFAULT 0, -- 个性化准备度
    recommendation_acceptance_rate FLOAT DEFAULT 0, -- 推荐接受率
    adaptation_speed_score FLOAT DEFAULT 0, -- 适应新功能的速度
    
    -- ===========================================
    -- 数据质量和元数据
    -- ===========================================
    -- 数据完整性
    data_completeness_score FLOAT DEFAULT 0, -- 0-1, 数据完整性评分
    feature_coverage JSONB, -- 各维度数据覆盖情况
    data_freshness_hours INTEGER DEFAULT 0, -- 数据新鲜度(小时)
    
    -- ETL元数据
    last_etl_run_at TIMESTAMPTZ,
    etl_version TEXT,
    data_sources_used TEXT[], -- ["memory_service", "rudderstack", "sessions"]
    processing_duration_seconds FLOAT,
    
    -- 数据血缘和版本控制
    data_lineage_info JSONB, -- 数据来源追踪
    schema_version TEXT DEFAULT '1.0',
    
    -- ===========================================
    -- 索引和约束
    -- ===========================================
    CONSTRAINT user_360_org_fk FOREIGN KEY (org_id) REFERENCES organizations(organization_id),
    CONSTRAINT user_360_user_fk FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- ===========================================
-- 性能优化索引
-- ===========================================
-- 主要查询模式的复合索引
CREATE INDEX IF NOT EXISTS idx_user_360_org_updated ON user_360_profile(org_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_360_lifecycle ON user_360_profile(user_lifecycle_stage, engagement_trend);
CREATE INDEX IF NOT EXISTS idx_user_360_activity ON user_360_profile(last_session_date DESC, total_sessions DESC);

-- 时间序列分析索引
CREATE INDEX IF NOT EXISTS idx_user_360_temporal ON user_360_profile USING GIN(peak_usage_hours, weekly_usage_pattern);

-- 技能和领域分析索引  
CREATE INDEX IF NOT EXISTS idx_user_360_skills ON user_360_profile USING GIN(knowledge_domains, primary_use_cases);

-- 行为模式分析索引
CREATE INDEX IF NOT EXISTS idx_user_360_behavior ON user_360_profile USING GIN(feature_usage_counts, most_visited_pages);

-- ===========================================
-- 分区策略 (如果用户量大)
-- ===========================================
-- 可选: 按org_id进行分区，提升大组织的查询性能
-- ALTER TABLE user_360_profile PARTITION BY HASH (org_id);

-- ===========================================
-- 行级安全策略 (RLS)
-- ===========================================
ALTER TABLE user_360_profile ENABLE ROW LEVEL SECURITY;

-- 用户只能访问自己的数据
CREATE POLICY user_360_self_access ON user_360_profile
    FOR ALL USING (auth.uid()::text = user_id::text);

-- 组织管理员可以访问组织内用户数据
CREATE POLICY user_360_org_admin_access ON user_360_profile
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM user_organization_roles uor
            WHERE uor.user_id = auth.uid()
            AND uor.organization_id = user_360_profile.org_id
            AND uor.role IN ('admin', 'owner')
        )
    );

-- ===========================================
-- 实时更新触发器
-- ===========================================
CREATE OR REPLACE FUNCTION update_user_360_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_360_update_timestamp
    BEFORE UPDATE ON user_360_profile
    FOR EACH ROW
    EXECUTE FUNCTION update_user_360_timestamp();

-- ===========================================
-- 数据视图 - 常用查询优化
-- ===========================================
-- 活跃用户视图
CREATE OR REPLACE VIEW active_users_360 AS
SELECT *
FROM user_360_profile
WHERE account_status = 'active'
  AND last_session_date >= NOW() - INTERVAL '30 days'
  AND total_sessions > 5;

-- 高价值用户视图 (用于重点分析)
CREATE OR REPLACE VIEW high_value_users_360 AS  
SELECT *
FROM user_360_profile
WHERE subscription_tier IN ('pro', 'enterprise')
  AND engagement_trend IN ('increasing', 'stable')
  AND churn_risk_score < 0.3;

-- 需要干预的用户视图
CREATE OR REPLACE VIEW at_risk_users_360 AS
SELECT *
FROM user_360_profile  
WHERE churn_risk_score > 0.7
  OR engagement_trend = 'declining'
  OR user_lifecycle_stage = 'at_risk';