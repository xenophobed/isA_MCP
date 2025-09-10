-- ===========================================
-- User360 2.0: Hybrid Fact Table Architecture
-- ===========================================
-- 核心设计理念：
-- 1. session_messages + memory 作为核心用户需求捕获
-- 2. user_events 作为行为模式补充
-- 3. 多事实表支持不同分析场景
-- ===========================================

-- ===========================================
-- 核心事实表1: 用户需求与交互事实表
-- ===========================================
CREATE TABLE user_interaction_facts (
    -- 代理键
    interaction_fact_id BIGSERIAL PRIMARY KEY,
    
    -- 维度外键
    user_key BIGINT REFERENCES user_dimension(user_key),
    time_key INTEGER REFERENCES time_dimension(time_key),
    session_key BIGINT REFERENCES session_dimension(session_key),
    content_type_key INTEGER REFERENCES content_type_dimension(content_type_key),
    
    -- 业务键
    source_id VARCHAR(255), -- session_message_id 或 memory_id
    source_type VARCHAR(50), -- 'session_message', 'factual_memory', 'episodic_memory' etc.
    
    -- 内容度量
    content_length INTEGER DEFAULT 0,
    semantic_complexity_score DECIMAL(5,4) DEFAULT 0,
    technical_depth_score DECIMAL(5,4) DEFAULT 0,
    
    -- 需求分类度量 (从内容分析获得)
    need_category VARCHAR(100), -- 'coding_help', 'data_analysis', 'learning', 'problem_solving'
    need_urgency_score DECIMAL(5,4) DEFAULT 0,
    need_complexity_level VARCHAR(20), -- 'simple', 'moderate', 'complex', 'expert'
    
    -- 交互质量度量
    interaction_quality_score DECIMAL(5,4) DEFAULT 0,
    user_satisfaction_indicator DECIMAL(5,4) DEFAULT 0,
    follow_up_questions_count INTEGER DEFAULT 0,
    
    -- 知识域度量 
    primary_domain VARCHAR(100), -- 'python', 'machine_learning', 'web_development'
    domain_confidence_score DECIMAL(5,4) DEFAULT 0,
    cross_domain_indicators TEXT[], -- 跨领域关联
    
    -- 时序行为度量
    session_position INTEGER DEFAULT 0, -- 在会话中的位置
    context_switch_indicator BOOLEAN DEFAULT FALSE,
    continuation_from_previous BOOLEAN DEFAULT FALSE,
    
    -- 原始内容引用 (用于后续深度分析)
    content_summary TEXT,
    extracted_entities JSONB,
    sentiment_score DECIMAL(5,4) DEFAULT 0,
    
    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    etl_batch_id VARCHAR(100)
);

-- ===========================================
-- 核心事实表2: 行为事件补充事实表  
-- ===========================================
CREATE TABLE user_behavior_facts (
    -- 代理键
    behavior_fact_id BIGSERIAL PRIMARY KEY,
    
    -- 维度外键
    user_key BIGINT REFERENCES user_dimension(user_key),
    time_key INTEGER REFERENCES time_dimension(time_key),
    session_key BIGINT REFERENCES session_dimension(session_key),
    event_type_key INTEGER REFERENCES event_type_dimension(event_type_key),
    
    -- 业务键 (来源于user_events)
    event_id VARCHAR(255),
    event_name VARCHAR(100),
    
    -- 行为度量
    duration_seconds INTEGER DEFAULT 0,
    click_count INTEGER DEFAULT 0,
    scroll_distance INTEGER DEFAULT 0,
    interaction_depth_score DECIMAL(5,4) DEFAULT 0,
    
    -- 页面/功能度量
    page_path VARCHAR(500),
    feature_used VARCHAR(100),
    feature_efficiency_score DECIMAL(5,4) DEFAULT 0,
    
    -- 上下文度量
    device_type VARCHAR(50),
    browser_type VARCHAR(50),
    screen_resolution VARCHAR(20),
    network_quality_score DECIMAL(5,4) DEFAULT 0,
    
    -- 性能度量
    response_time_ms INTEGER DEFAULT 0,
    error_occurred BOOLEAN DEFAULT FALSE,
    retry_count INTEGER DEFAULT 0,
    
    -- 会话上下文
    session_progression_score DECIMAL(5,4) DEFAULT 0,
    goal_completion_indicator BOOLEAN DEFAULT FALSE,
    abandonment_risk_score DECIMAL(5,4) DEFAULT 0,
    
    -- 原始事件数据
    event_properties JSONB,
    user_agent TEXT,
    referrer VARCHAR(500),
    
    -- 审计字段
    event_timestamp TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    etl_batch_id VARCHAR(100)
);

-- ===========================================
-- 聚合事实表: 用户时间行为模式
-- ===========================================
CREATE TABLE user_time_behavior_facts (
    -- 代理键
    time_behavior_fact_id BIGSERIAL PRIMARY KEY,
    
    -- 维度外键
    user_key BIGINT REFERENCES user_dimension(user_key),
    time_period_key INTEGER REFERENCES time_period_dimension(time_period_key), -- 小时级别
    behavior_pattern_key INTEGER REFERENCES behavior_pattern_dimension(behavior_pattern_key),
    
    -- 时间窗口定义
    analysis_date DATE,
    hour_of_day INTEGER, -- 0-23
    day_of_week INTEGER, -- 1-7
    
    -- 需求模式聚合 (从user_interaction_facts聚合)
    dominant_need_category VARCHAR(100),
    need_diversity_score DECIMAL(5,4) DEFAULT 0,
    avg_need_complexity DECIMAL(5,4) DEFAULT 0,
    total_interactions INTEGER DEFAULT 0,
    
    -- 行为模式聚合 (从user_behavior_facts聚合)
    dominant_activity VARCHAR(100),
    activity_intensity_score DECIMAL(5,4) DEFAULT 0,
    session_focus_score DECIMAL(5,4) DEFAULT 0,
    total_events INTEGER DEFAULT 0,
    
    -- 综合模式度量
    productivity_score DECIMAL(5,4) DEFAULT 0,
    learning_intensity_score DECIMAL(5,4) DEFAULT 0,
    exploration_vs_execution_ratio DECIMAL(5,4) DEFAULT 0,
    
    -- 习惯稳定性度量
    pattern_consistency_score DECIMAL(5,4) DEFAULT 0,
    routine_strength_indicator DECIMAL(5,4) DEFAULT 0,
    anomaly_detection_score DECIMAL(5,4) DEFAULT 0,
    
    -- 时序特征
    trend_direction VARCHAR(20), -- 'increasing', 'stable', 'declining'
    seasonality_indicator DECIMAL(5,4) DEFAULT 0,
    
    -- 审计字段
    aggregation_period VARCHAR(20), -- 'hourly', 'daily', 'weekly'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ DEFAULT NOW(),
    etl_batch_id VARCHAR(100)
);

-- ===========================================
-- 快照事实表: 用户状态快照 (SCD Type 2)
-- ===========================================
CREATE TABLE user_profile_snapshots (
    -- 代理键
    snapshot_id BIGSERIAL PRIMARY KEY,
    
    -- 维度外键
    user_key BIGINT REFERENCES user_dimension(user_key),
    snapshot_date_key INTEGER REFERENCES date_dimension(date_key),
    
    -- 快照时间控制
    effective_date DATE,
    expiry_date DATE DEFAULT '9999-12-31',
    is_current BOOLEAN DEFAULT TRUE,
    
    -- 综合能力评估 (从交互内容分析)
    technical_skill_level VARCHAR(20), -- 'beginner', 'intermediate', 'advanced', 'expert'
    domain_expertise_scores JSONB, -- {"python": 0.9, "ml": 0.7, "frontend": 0.3}
    learning_velocity_score DECIMAL(5,4) DEFAULT 0,
    problem_solving_maturity VARCHAR(20),
    
    -- 行为特征总结 (从行为事件分析)
    usage_intensity VARCHAR(20), -- 'light', 'moderate', 'heavy', 'power_user'
    preferred_interaction_style VARCHAR(50), -- 'exploratory', 'goal_oriented', 'learning_focused'
    tool_proficiency_scores JSONB,
    efficiency_rating DECIMAL(5,4) DEFAULT 0,
    
    -- 时间模式画像 (从时间行为聚合)
    peak_productivity_hours INTEGER[], -- [9, 14, 20]
    work_pattern_type VARCHAR(50), -- 'morning_person', 'night_owl', 'flexible', 'consistent'
    activity_rhythm_score DECIMAL(5,4) DEFAULT 0,
    
    -- 需求预测特征
    likely_next_needs TEXT[], -- 基于历史模式预测
    churn_risk_score DECIMAL(5,4) DEFAULT 0,
    growth_potential_score DECIMAL(5,4) DEFAULT 0,
    personalization_readiness DECIMAL(5,4) DEFAULT 0,
    
    -- 商业价值指标
    engagement_value_score DECIMAL(5,4) DEFAULT 0,
    feature_adoption_rate DECIMAL(5,4) DEFAULT 0,
    recommendation_acceptance_rate DECIMAL(5,4) DEFAULT 0,
    
    -- 元数据
    data_quality_score DECIMAL(5,4) DEFAULT 0,
    completeness_percentage DECIMAL(5,2) DEFAULT 0,
    confidence_level DECIMAL(5,4) DEFAULT 0,
    
    -- 审计字段
    snapshot_reason VARCHAR(100), -- 'scheduled', 'significant_change', 'manual'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    etl_batch_id VARCHAR(100)
);

-- ===========================================
-- 性能优化索引
-- ===========================================

-- user_interaction_facts 索引
CREATE INDEX idx_interaction_facts_user_time ON user_interaction_facts(user_key, time_key);
CREATE INDEX idx_interaction_facts_need_category ON user_interaction_facts(need_category, domain_confidence_score DESC);
CREATE INDEX idx_interaction_facts_session ON user_interaction_facts(session_key, session_position);
CREATE INDEX idx_interaction_facts_content_type ON user_interaction_facts USING GIN(extracted_entities);

-- user_behavior_facts 索引
CREATE INDEX idx_behavior_facts_user_time ON user_behavior_facts(user_key, time_key);
CREATE INDEX idx_behavior_facts_event_type ON user_behavior_facts(event_type_key, event_timestamp);
CREATE INDEX idx_behavior_facts_session ON user_behavior_facts(session_key, goal_completion_indicator);
CREATE INDEX idx_behavior_facts_performance ON user_behavior_facts(response_time_ms, error_occurred);

-- user_time_behavior_facts 索引
CREATE INDEX idx_time_behavior_user_period ON user_time_behavior_facts(user_key, analysis_date, hour_of_day);
CREATE INDEX idx_time_behavior_patterns ON user_time_behavior_facts(dominant_need_category, dominant_activity);
CREATE INDEX idx_time_behavior_consistency ON user_time_behavior_facts(pattern_consistency_score DESC, routine_strength_indicator DESC);

-- user_profile_snapshots 索引
CREATE INDEX idx_profile_snapshots_user_current ON user_profile_snapshots(user_key, is_current, effective_date);
CREATE INDEX idx_profile_snapshots_skills ON user_profile_snapshots USING GIN(domain_expertise_scores);
CREATE INDEX idx_profile_snapshots_risk ON user_profile_snapshots(churn_risk_score DESC, growth_potential_score DESC);

-- ===========================================
-- 数据完整性约束
-- ===========================================

-- 确保快照数据的时间一致性
ALTER TABLE user_profile_snapshots ADD CONSTRAINT chk_snapshot_dates 
    CHECK (effective_date <= expiry_date);

-- 确保评分在有效范围内
ALTER TABLE user_interaction_facts ADD CONSTRAINT chk_interaction_scores 
    CHECK (semantic_complexity_score BETWEEN 0 AND 1 AND technical_depth_score BETWEEN 0 AND 1);
    
ALTER TABLE user_behavior_facts ADD CONSTRAINT chk_behavior_scores 
    CHECK (interaction_depth_score BETWEEN 0 AND 1 AND feature_efficiency_score BETWEEN 0 AND 1);

-- 确保时间维度有效性
ALTER TABLE user_time_behavior_facts ADD CONSTRAINT chk_time_validity 
    CHECK (hour_of_day BETWEEN 0 AND 23 AND day_of_week BETWEEN 1 AND 7);