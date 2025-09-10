-- ===========================================
-- User360 2.0: Core Dimension Tables
-- ===========================================
-- 标准Star Schema维度表，支持SCD Type 1/Type 2
-- ===========================================

-- ===========================================
-- 用户维度表 (SCD Type 2 - 慢变化维度)
-- ===========================================
CREATE TABLE user_dimension (
    user_key BIGSERIAL PRIMARY KEY,
    
    -- 业务键
    user_id VARCHAR(255) NOT NULL, -- 来源系统的用户ID
    
    -- 基础属性
    email VARCHAR(500),
    username VARCHAR(255),
    organization_id VARCHAR(255),
    
    -- 账户信息
    subscription_tier VARCHAR(50) DEFAULT 'free', -- free, pro, enterprise
    account_status VARCHAR(50) DEFAULT 'active', -- active, inactive, suspended
    registration_date DATE,
    
    -- 地理和时区信息
    timezone VARCHAR(100),
    locale VARCHAR(10),
    country_code VARCHAR(5),
    region VARCHAR(100),
    
    -- 用户分类 (从行为分析得出)
    user_segment VARCHAR(100), -- 'power_user', 'casual', 'learner', 'professional'
    user_persona VARCHAR(100), -- 'data_scientist', 'developer', 'student', 'researcher'
    experience_level VARCHAR(50), -- 'beginner', 'intermediate', 'advanced', 'expert'
    
    -- 偏好设置
    preferred_language VARCHAR(20),
    communication_style VARCHAR(50), -- 'technical', 'conversational', 'concise', 'detailed'
    ui_preferences JSONB,
    
    -- SCD Type 2 控制字段
    effective_date DATE DEFAULT CURRENT_DATE,
    expiry_date DATE DEFAULT '9999-12-31',
    is_current BOOLEAN DEFAULT TRUE,
    
    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    etl_batch_id VARCHAR(100)
);

-- ===========================================
-- 时间维度表 (详细时间层次)
-- ===========================================
CREATE TABLE time_dimension (
    time_key INTEGER PRIMARY KEY, -- YYYYMMDDHH24MI 格式
    
    -- 完整时间戳
    full_datetime TIMESTAMPTZ NOT NULL,
    
    -- 日期层次
    date_key INTEGER, -- YYYYMMDD
    year INTEGER,
    quarter INTEGER,
    month INTEGER,
    month_name VARCHAR(20),
    week_of_year INTEGER,
    day_of_year INTEGER,
    day_of_month INTEGER,
    day_of_week INTEGER, -- 1=周一, 7=周日
    day_name VARCHAR(20),
    
    -- 时间层次
    hour_24 INTEGER, -- 0-23
    hour_12 INTEGER, -- 1-12
    am_pm VARCHAR(2),
    minute INTEGER,
    
    -- 业务时间分类
    is_weekend BOOLEAN,
    is_holiday BOOLEAN,
    is_business_hour BOOLEAN, -- 9-18点
    time_period VARCHAR(20), -- 'morning', 'afternoon', 'evening', 'night'
    
    -- 季节性标识
    season VARCHAR(20), -- 'spring', 'summer', 'fall', 'winter'
    fiscal_quarter INTEGER,
    fiscal_year INTEGER,
    
    -- 相对时间标识
    is_current_day BOOLEAN DEFAULT FALSE,
    is_current_week BOOLEAN DEFAULT FALSE,
    is_current_month BOOLEAN DEFAULT FALSE,
    days_from_today INTEGER DEFAULT 0
);

-- ===========================================
-- 日期维度表 (简化版本用于快照)
-- ===========================================
CREATE TABLE date_dimension (
    date_key INTEGER PRIMARY KEY, -- YYYYMMDD
    full_date DATE NOT NULL,
    year INTEGER,
    quarter INTEGER,
    month INTEGER,
    month_name VARCHAR(20),
    week_of_year INTEGER,
    day_of_year INTEGER,
    day_of_month INTEGER,
    day_of_week INTEGER,
    day_name VARCHAR(20),
    is_weekend BOOLEAN,
    is_holiday BOOLEAN,
    season VARCHAR(20)
);

-- ===========================================
-- 时间段维度表 (用于行为模式分析)
-- ===========================================
CREATE TABLE time_period_dimension (
    time_period_key INTEGER PRIMARY KEY,
    period_name VARCHAR(100), -- '工作日早晨', '周末下午', '深夜学习时间'
    hour_start INTEGER, -- 9
    hour_end INTEGER,   -- 12
    day_type VARCHAR(20), -- 'weekday', 'weekend', 'all'
    period_category VARCHAR(50), -- 'productive', 'leisure', 'learning', 'exploration'
    typical_activities TEXT[],
    productivity_score DECIMAL(3,2) DEFAULT 0.5
);

-- ===========================================
-- 会话维度表 (SCD Type 1)
-- ===========================================
CREATE TABLE session_dimension (
    session_key BIGSERIAL PRIMARY KEY,
    
    -- 业务键
    session_id VARCHAR(255) NOT NULL,
    
    -- 会话属性
    session_start_time TIMESTAMPTZ,
    session_end_time TIMESTAMPTZ,
    session_duration_minutes INTEGER,
    
    -- 会话分类
    session_type VARCHAR(50), -- 'coding', 'learning', 'exploration', 'problem_solving'
    session_goal VARCHAR(200), -- 从内容分析推断的目标
    session_outcome VARCHAR(50), -- 'completed', 'abandoned', 'ongoing'
    
    -- 技术环境
    device_type VARCHAR(50),
    browser_type VARCHAR(100),
    os_type VARCHAR(50),
    screen_resolution VARCHAR(20),
    
    -- 会话质量指标
    interaction_count INTEGER DEFAULT 0,
    avg_response_time_ms INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    satisfaction_score DECIMAL(3,2) DEFAULT 0,
    
    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    etl_batch_id VARCHAR(100)
);

-- ===========================================
-- 内容类型维度表 (层次化分类)
-- ===========================================
CREATE TABLE content_type_dimension (
    content_type_key INTEGER PRIMARY KEY,
    
    -- 层次化分类
    category_level_1 VARCHAR(100), -- 'technical', 'creative', 'learning', 'administrative'
    category_level_2 VARCHAR(100), -- 'programming', 'data_analysis', 'writing', 'planning'
    category_level_3 VARCHAR(100), -- 'python', 'machine_learning', 'blog_post', 'project_plan'
    
    -- 完整路径
    full_category_path VARCHAR(500), -- 'technical/programming/python'
    
    -- 属性
    complexity_level VARCHAR(20), -- 'simple', 'moderate', 'complex', 'expert'
    typical_duration_minutes INTEGER, -- 预期处理时间
    requires_deep_focus BOOLEAN DEFAULT FALSE,
    collaborative_nature BOOLEAN DEFAULT FALSE,
    
    -- 技能要求
    required_skills TEXT[],
    optional_skills TEXT[],
    learning_curve VARCHAR(20), -- 'flat', 'moderate', 'steep'
    
    -- 业务价值
    business_impact VARCHAR(20), -- 'low', 'medium', 'high', 'critical'
    user_satisfaction_typical DECIMAL(3,2) DEFAULT 0.5
);

-- ===========================================
-- 事件类型维度表 (用户行为事件)
-- ===========================================
CREATE TABLE event_type_dimension (
    event_type_key INTEGER PRIMARY KEY,
    
    -- 事件分类
    event_name VARCHAR(100) NOT NULL,
    event_category VARCHAR(50), -- 'navigation', 'interaction', 'content', 'system'
    event_subcategory VARCHAR(50), -- 'click', 'scroll', 'input', 'search'
    
    -- 事件属性
    is_conversion_event BOOLEAN DEFAULT FALSE,
    is_engagement_indicator BOOLEAN DEFAULT TRUE,
    is_performance_metric BOOLEAN DEFAULT FALSE,
    
    -- 分析权重
    engagement_weight DECIMAL(3,2) DEFAULT 1.0,
    conversion_weight DECIMAL(3,2) DEFAULT 1.0,
    satisfaction_impact DECIMAL(3,2) DEFAULT 0.0, -- 对满意度的影响 -1到1
    
    -- 描述
    event_description TEXT,
    typical_frequency VARCHAR(20), -- 'rare', 'occasional', 'frequent', 'constant'
    expected_duration_seconds INTEGER DEFAULT 0
);

-- ===========================================
-- 行为模式维度表 (时间行为分析用)
-- ===========================================
CREATE TABLE behavior_pattern_dimension (
    behavior_pattern_key INTEGER PRIMARY KEY,
    
    -- 模式识别
    pattern_name VARCHAR(200), -- '深度学习专注模式', '快速问题解决模式'
    pattern_type VARCHAR(50), -- 'productive', 'exploratory', 'learning', 'maintenance'
    
    -- 模式特征
    typical_duration_minutes INTEGER,
    interaction_intensity VARCHAR(20), -- 'low', 'medium', 'high', 'burst'
    cognitive_load VARCHAR(20), -- 'light', 'moderate', 'heavy', 'intense'
    
    -- 行为特征
    dominant_actions TEXT[], -- ['coding', 'debugging', 'researching']
    common_sequences JSONB, -- 常见的行为序列
    success_indicators TEXT[],
    
    -- 用户体验
    stress_level VARCHAR(20), -- 'relaxed', 'focused', 'pressured', 'stressed'
    satisfaction_potential DECIMAL(3,2) DEFAULT 0.5,
    learning_opportunity DECIMAL(3,2) DEFAULT 0.5,
    
    -- 推荐策略
    optimal_support_type VARCHAR(100), -- 如何最好地支持这种模式
    intervention_triggers TEXT[], -- 什么情况下需要干预
    personalization_opportunities TEXT[]
);

-- ===========================================
-- 知识域维度表 (技能和专业领域)
-- ===========================================
CREATE TABLE knowledge_domain_dimension (
    domain_key INTEGER PRIMARY KEY,
    
    -- 域分类
    domain_name VARCHAR(100) NOT NULL, -- 'Python', 'Machine Learning', 'Web Development'
    domain_category VARCHAR(50), -- 'programming_language', 'technology_stack', 'methodology'
    parent_domain_key INTEGER REFERENCES knowledge_domain_dimension(domain_key),
    
    -- 层次路径
    domain_path VARCHAR(500), -- 'Technology/Programming/Languages/Python'
    domain_level INTEGER DEFAULT 1, -- 1=顶级, 2=二级, etc.
    
    -- 属性
    learning_curve VARCHAR(20), -- 'gentle', 'moderate', 'steep', 'expert_only'
    market_demand VARCHAR(20), -- 'niche', 'moderate', 'high', 'critical'
    evolution_pace VARCHAR(20), -- 'stable', 'slow', 'moderate', 'rapid'
    
    -- 关联信息
    related_domains TEXT[], -- 相关的其他domains
    prerequisite_domains TEXT[], -- 前置要求的domains
    complementary_tools TEXT[], -- 常用配套工具
    
    -- 行业信息
    industry_relevance JSONB, -- {"fintech": 0.9, "healthcare": 0.6}
    career_impact DECIMAL(3,2) DEFAULT 0.5,
    
    -- 学习资源
    typical_learning_time_hours INTEGER,
    difficulty_rating DECIMAL(3,2) DEFAULT 0.5 -- 0=easy, 1=very_difficult
);

-- ===========================================
-- 性能索引
-- ===========================================

-- user_dimension 索引
CREATE INDEX idx_user_dim_business_key ON user_dimension(user_id, is_current);
CREATE INDEX idx_user_dim_current ON user_dimension(is_current, effective_date, expiry_date);
CREATE INDEX idx_user_dim_segment ON user_dimension(user_segment, user_persona);
CREATE INDEX idx_user_dim_org ON user_dimension(organization_id) WHERE is_current = TRUE;

-- time_dimension 索引
CREATE INDEX idx_time_dim_date_hour ON time_dimension(date_key, hour_24);
CREATE INDEX idx_time_dim_business ON time_dimension(is_business_hour, is_weekend);
CREATE INDEX idx_time_dim_period ON time_dimension(time_period, day_of_week);

-- session_dimension 索引
CREATE INDEX idx_session_dim_business_key ON session_dimension(session_id);
CREATE INDEX idx_session_dim_time ON session_dimension(session_start_time, session_type);
CREATE INDEX idx_session_dim_quality ON session_dimension(satisfaction_score DESC, error_count);

-- content_type_dimension 索引
CREATE INDEX idx_content_type_hierarchy ON content_type_dimension(category_level_1, category_level_2, category_level_3);
CREATE INDEX idx_content_type_complexity ON content_type_dimension(complexity_level, business_impact);

-- knowledge_domain_dimension 索引  
CREATE INDEX idx_knowledge_domain_hierarchy ON knowledge_domain_dimension(parent_domain_key, domain_level);
CREATE INDEX idx_knowledge_domain_market ON knowledge_domain_dimension(market_demand, career_impact DESC);

-- ===========================================
-- 预填充基础数据
-- ===========================================

-- 填充时间段维度基础数据
INSERT INTO time_period_dimension (time_period_key, period_name, hour_start, hour_end, day_type, period_category) VALUES
(1, '早晨专注时间', 6, 9, 'weekday', 'productive'),
(2, '上午工作时间', 9, 12, 'weekday', 'productive'),
(3, '下午协作时间', 13, 17, 'weekday', 'productive'),
(4, '傍晚学习时间', 18, 21, 'all', 'learning'),
(5, '深夜探索时间', 22, 2, 'all', 'exploration'),
(6, '周末项目时间', 10, 16, 'weekend', 'productive'),
(7, '休闲学习时间', 19, 22, 'weekend', 'learning');

-- 填充基础内容类型
INSERT INTO content_type_dimension (content_type_key, category_level_1, category_level_2, category_level_3, full_category_path, complexity_level) VALUES
(1, 'technical', 'programming', 'python', 'technical/programming/python', 'moderate'),
(2, 'technical', 'programming', 'javascript', 'technical/programming/javascript', 'moderate'),
(3, 'technical', 'data_science', 'machine_learning', 'technical/data_science/machine_learning', 'complex'),
(4, 'technical', 'data_science', 'data_analysis', 'technical/data_science/data_analysis', 'moderate'),
(5, 'learning', 'tutorial', 'basic_concepts', 'learning/tutorial/basic_concepts', 'simple'),
(6, 'learning', 'research', 'advanced_topics', 'learning/research/advanced_topics', 'complex'),
(7, 'creative', 'writing', 'documentation', 'creative/writing/documentation', 'simple'),
(8, 'administrative', 'planning', 'project_management', 'administrative/planning/project_management', 'moderate');