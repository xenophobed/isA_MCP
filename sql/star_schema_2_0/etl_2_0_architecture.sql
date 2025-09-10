-- ===========================================
-- User360 ETL 2.0: Data Flow Architecture
-- ===========================================
-- 核心设计原则：
-- 1. session_messages + memory 为核心数据源
-- 2. user_events 作为行为补充
-- 3. 实时内容分析 + 批量聚合处理
-- 4. 多层ETL管道：Extract -> Analyze -> Transform -> Load
-- ===========================================

-- ===========================================
-- ETL元数据管理表
-- ===========================================
CREATE TABLE etl_job_registry (
    job_id VARCHAR(100) PRIMARY KEY,
    job_name VARCHAR(200) NOT NULL,
    job_type VARCHAR(50), -- 'real_time', 'batch', 'streaming', 'adhoc'
    job_schedule VARCHAR(100), -- cron表达式
    data_sources TEXT[], -- ['session_messages', 'factual_memories', 'user_events']
    target_tables TEXT[], -- 目标表列表
    dependencies TEXT[], -- 依赖的其他job
    is_active BOOLEAN DEFAULT TRUE,
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    success_rate DECIMAL(5,2) DEFAULT 0.0
);

CREATE TABLE etl_execution_log (
    execution_id BIGSERIAL PRIMARY KEY,
    job_id VARCHAR(100) REFERENCES etl_job_registry(job_id),
    batch_id VARCHAR(100) NOT NULL,
    execution_type VARCHAR(50), -- 'scheduled', 'manual', 'trigger'
    
    -- 执行状态
    status VARCHAR(50), -- 'running', 'completed', 'failed', 'cancelled'
    start_time TIMESTAMPTZ DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    duration_seconds INTEGER,
    
    -- 数据量统计
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    
    -- 错误处理
    error_message TEXT,
    error_details JSONB,
    retry_count INTEGER DEFAULT 0,
    
    -- 资源使用
    memory_peak_mb DECIMAL(10,2),
    cpu_usage_avg DECIMAL(5,2),
    
    -- 数据质量
    quality_score DECIMAL(5,4),
    completeness_percentage DECIMAL(5,2),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================
-- 数据质量检查规则
-- ===========================================
CREATE TABLE data_quality_rules (
    rule_id VARCHAR(100) PRIMARY KEY,
    rule_name VARCHAR(200) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    column_name VARCHAR(100),
    rule_type VARCHAR(50), -- 'completeness', 'uniqueness', 'validity', 'consistency'
    
    -- 规则定义
    rule_sql TEXT, -- SQL检查语句
    expected_result VARCHAR(20), -- 'zero_rows', 'positive_count', 'within_range'
    threshold_min DECIMAL(10,4),
    threshold_max DECIMAL(10,4),
    
    -- 严重程度
    severity VARCHAR(20), -- 'critical', 'major', 'minor', 'info'
    action_on_fail VARCHAR(50), -- 'stop_pipeline', 'warn_continue', 'log_only'
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================
-- 增量处理控制表 (CDC - Change Data Capture)
-- ===========================================
CREATE TABLE etl_watermarks (
    source_table VARCHAR(100) PRIMARY KEY,
    last_processed_timestamp TIMESTAMPTZ,
    last_processed_id BIGINT,
    processing_lag_seconds INTEGER DEFAULT 0,
    records_per_batch INTEGER DEFAULT 1000,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================
-- ETL 2.0 核心管道定义
-- ===========================================

-- Pipeline 1: 实时用户交互内容分析
INSERT INTO etl_job_registry VALUES 
('realtime_interaction_analysis', '实时用户交互分析', 'real_time', '*/5 * * * *', 
 ARRAY['session_messages', 'factual_memories', 'episodic_memories', 'semantic_memories'], 
 ARRAY['user_interaction_facts'], 
 ARRAY[]::TEXT[], TRUE, NULL, NOW());

-- Pipeline 2: 用户行为事件处理  
INSERT INTO etl_job_registry VALUES
('behavior_events_processing', '用户行为事件处理', 'real_time', '*/2 * * * *',
 ARRAY['user_events'],
 ARRAY['user_behavior_facts'],
 ARRAY[]::TEXT[], TRUE, NULL, NOW());

-- Pipeline 3: 时间行为模式聚合
INSERT INTO etl_job_registry VALUES
('time_behavior_aggregation', '时间行为模式聚合', 'batch', '0 2 * * *',
 ARRAY['user_interaction_facts', 'user_behavior_facts'],
 ARRAY['user_time_behavior_facts'],
 ARRAY['realtime_interaction_analysis', 'behavior_events_processing'], TRUE, NULL, NOW());

-- Pipeline 4: 用户画像快照
INSERT INTO etl_job_registry VALUES
('user_profile_snapshots', '用户画像快照生成', 'batch', '0 4 * * *',
 ARRAY['user_interaction_facts', 'user_behavior_facts', 'user_time_behavior_facts'],
 ARRAY['user_profile_snapshots'],
 ARRAY['time_behavior_aggregation'], TRUE, NULL, NOW());

-- Pipeline 5: 维度数据刷新
INSERT INTO etl_job_registry VALUES
('dimension_refresh', '维度表数据刷新', 'batch', '0 1 * * *',
 ARRAY['users', 'sessions'],
 ARRAY['user_dimension', 'session_dimension'],
 ARRAY[]::TEXT[], TRUE, NULL, NOW());

-- ===========================================
-- 数据质量规则定义
-- ===========================================

-- 用户交互事实表质量规则
INSERT INTO data_quality_rules VALUES
('interaction_completeness', '交互内容完整性', 'user_interaction_facts', 'content_summary', 'completeness',
 'SELECT COUNT(*) FROM user_interaction_facts WHERE content_summary IS NULL OR LENGTH(content_summary) < 10', 
 'zero_rows', 0, 0, 'major', 'warn_continue', TRUE, NOW());

INSERT INTO data_quality_rules VALUES
('interaction_score_validity', '交互评分有效性', 'user_interaction_facts', 'semantic_complexity_score', 'validity',
 'SELECT COUNT(*) FROM user_interaction_facts WHERE semantic_complexity_score < 0 OR semantic_complexity_score > 1',
 'zero_rows', 0, 0, 'critical', 'stop_pipeline', TRUE, NOW());

-- 用户行为事实表质量规则
INSERT INTO data_quality_rules VALUES
('behavior_timestamp_consistency', '行为时间戳一致性', 'user_behavior_facts', 'event_timestamp', 'consistency',
 'SELECT COUNT(*) FROM user_behavior_facts WHERE event_timestamp > NOW() + INTERVAL ''1 hour''',
 'zero_rows', 0, 0, 'major', 'warn_continue', TRUE, NOW());

-- 时间行为聚合质量规则
INSERT INTO data_quality_rules VALUES
('time_behavior_coverage', '时间行为覆盖度', 'user_time_behavior_facts', 'total_interactions', 'completeness',
 'SELECT COUNT(DISTINCT user_key) FROM user_time_behavior_facts WHERE analysis_date = CURRENT_DATE',
 'positive_count', 1, 999999, 'major', 'warn_continue', TRUE, NOW());

-- ===========================================
-- ETL数据处理视图 (用于增量处理)
-- ===========================================

-- 新增用户消息视图 (增量)
CREATE OR REPLACE VIEW v_new_session_messages AS
SELECT 
    sm.id,
    sm.session_id,
    sm.user_id,
    sm.content,
    sm.message_type,
    sm.created_at,
    sm.updated_at,
    s.organization_id,
    -- 增强字段
    LENGTH(sm.content) as content_length,
    CASE 
        WHEN sm.message_type = 'user' THEN 'user_input'
        WHEN sm.message_type = 'assistant' THEN 'ai_response'
        ELSE 'system_message'
    END as interaction_type
FROM session_messages sm
JOIN sessions s ON sm.session_id = s.id
WHERE sm.updated_at > COALESCE(
    (SELECT last_processed_timestamp FROM etl_watermarks WHERE source_table = 'session_messages'),
    '1900-01-01'::timestamptz
)
AND sm.content IS NOT NULL
AND LENGTH(sm.content) > 10; -- 过滤掉太短的消息

-- 新增Memory数据视图 (增量)  
CREATE OR REPLACE VIEW v_new_memory_content AS
SELECT 
    'factual' as memory_type,
    fm.id,
    fm.user_id,
    fm.created_at,
    CONCAT(fm.subject, ' ', COALESCE(fm.predicate, ''), ' ', COALESCE(fm.object_value, '')) as content,
    fm.context,
    fm.confidence_score
FROM factual_memories fm
WHERE fm.updated_at > COALESCE(
    (SELECT last_processed_timestamp FROM etl_watermarks WHERE source_table = 'factual_memories'),
    '1900-01-01'::timestamptz
)
UNION ALL
SELECT 
    'episodic' as memory_type,
    em.id,
    em.user_id, 
    em.created_at,
    CONCAT(em.episode_title, ' ', COALESCE(em.summary, '')) as content,
    em.context,
    em.confidence_score
FROM episodic_memories em  
WHERE em.updated_at > COALESCE(
    (SELECT last_processed_timestamp FROM etl_watermarks WHERE source_table = 'episodic_memories'),
    '1900-01-01'::timestamptz
)
UNION ALL
SELECT 
    'semantic' as memory_type,
    sem.id,
    sem.user_id,
    sem.created_at,
    CONCAT(sem.concept, ' ', COALESCE(sem.definition, ''), ' ', COALESCE(sem.related_concepts::text, '')) as content,
    sem.context,
    sem.confidence_score
FROM semantic_memories sem
WHERE sem.updated_at > COALESCE(
    (SELECT last_processed_timestamp FROM etl_watermarks WHERE source_table = 'semantic_memories'),
    '1900-01-01'::timestamptz
);

-- 新增用户事件视图 (增量)
CREATE OR REPLACE VIEW v_new_user_events AS
SELECT 
    ue.*,
    -- 解析事件属性
    (ue.properties->>'duration')::INTEGER as duration_seconds,
    (ue.properties->>'click_count')::INTEGER as click_count,
    ue.properties->>'page_path' as page_path,
    ue.properties->>'feature_used' as feature_used
FROM user_events ue
WHERE ue.timestamp > COALESCE(
    (SELECT last_processed_timestamp FROM etl_watermarks WHERE source_table = 'user_events'),
    '1900-01-01'::timestamptz
)
AND ue.event_name IS NOT NULL;

-- ===========================================
-- ETL处理函数 (存储过程)
-- ===========================================

-- 内容分析处理函数
CREATE OR REPLACE FUNCTION process_interaction_content(
    p_batch_size INTEGER DEFAULT 100,
    p_batch_id VARCHAR DEFAULT NULL
) RETURNS TABLE (
    processed_count INTEGER,
    success_count INTEGER,
    error_count INTEGER
) AS $$
DECLARE
    v_batch_id VARCHAR := COALESCE(p_batch_id, 'batch_' || EXTRACT(EPOCH FROM NOW())::TEXT);
    v_processed INTEGER := 0;
    v_success INTEGER := 0;
    v_errors INTEGER := 0;
    rec RECORD;
BEGIN
    -- 处理session_messages的新数据
    FOR rec IN 
        SELECT * FROM v_new_session_messages 
        ORDER BY created_at 
        LIMIT p_batch_size
    LOOP
        BEGIN
            -- 这里会调用LangExtractor进行内容分析
            -- 实际实现中需要通过API调用Python服务
            INSERT INTO user_interaction_facts (
                user_key,
                time_key, 
                session_key,
                content_type_key,
                source_id,
                source_type,
                content_length,
                content_summary,
                need_category,
                primary_domain,
                etl_batch_id,
                created_at
            )
            SELECT 
                ud.user_key,
                to_char(rec.created_at, 'YYYYMMDDHH24MI')::INTEGER,
                sd.session_key,
                1, -- 默认内容类型，实际中需要通过分析确定
                rec.id,
                'session_message',
                rec.content_length,
                LEFT(rec.content, 500), -- 摘要
                'general', -- 需要通过AI分析确定
                'unknown', -- 需要通过AI分析确定
                v_batch_id,
                NOW()
            FROM user_dimension ud
            JOIN session_dimension sd ON sd.session_id = rec.session_id
            WHERE ud.user_id = rec.user_id AND ud.is_current = TRUE
            LIMIT 1;
            
            v_success := v_success + 1;
            
        EXCEPTION WHEN OTHERS THEN
            v_errors := v_errors + 1;
            -- 记录错误但继续处理
            INSERT INTO etl_execution_log (job_id, batch_id, status, error_message, records_failed)
            VALUES ('realtime_interaction_analysis', v_batch_id, 'partial_failure', SQLERRM, 1);
        END;
        
        v_processed := v_processed + 1;
    END LOOP;
    
    -- 更新watermark
    INSERT INTO etl_watermarks (source_table, last_processed_timestamp, updated_at)
    VALUES ('session_messages', NOW(), NOW())
    ON CONFLICT (source_table) DO UPDATE SET
        last_processed_timestamp = NOW(),
        updated_at = NOW();
    
    RETURN QUERY SELECT v_processed, v_success, v_errors;
END;
$$ LANGUAGE plpgsql;

-- 用户行为事件处理函数  
CREATE OR REPLACE FUNCTION process_behavior_events(
    p_batch_size INTEGER DEFAULT 100,
    p_batch_id VARCHAR DEFAULT NULL
) RETURNS TABLE (
    processed_count INTEGER,
    success_count INTEGER, 
    error_count INTEGER
) AS $$
DECLARE
    v_batch_id VARCHAR := COALESCE(p_batch_id, 'batch_' || EXTRACT(EPOCH FROM NOW())::TEXT);
    v_processed INTEGER := 0;
    v_success INTEGER := 0;
    v_errors INTEGER := 0;
    rec RECORD;
BEGIN
    -- 处理user_events的新数据
    FOR rec IN 
        SELECT * FROM v_new_user_events 
        ORDER BY timestamp 
        LIMIT p_batch_size
    LOOP
        BEGIN
            INSERT INTO user_behavior_facts (
                user_key,
                time_key,
                session_key,
                event_type_key,
                event_id,
                event_name,
                duration_seconds,
                click_count,
                page_path,
                feature_used,
                event_timestamp,
                etl_batch_id,
                created_at
            )
            SELECT 
                ud.user_key,
                to_char(rec.timestamp, 'YYYYMMDDHH24MI')::INTEGER,
                COALESCE(sd.session_key, -1), -- 默认值如果找不到session
                COALESCE(etd.event_type_key, 1), -- 默认事件类型
                rec.id,
                rec.event_name,
                rec.duration_seconds,
                rec.click_count,
                rec.page_path,
                rec.feature_used,
                rec.timestamp,
                v_batch_id,
                NOW()
            FROM user_dimension ud
            LEFT JOIN session_dimension sd ON sd.session_id = rec.session_id
            LEFT JOIN event_type_dimension etd ON etd.event_name = rec.event_name
            WHERE ud.user_id = rec.user_id AND ud.is_current = TRUE
            LIMIT 1;
            
            v_success := v_success + 1;
            
        EXCEPTION WHEN OTHERS THEN
            v_errors := v_errors + 1;
        END;
        
        v_processed := v_processed + 1;
    END LOOP;
    
    -- 更新watermark
    INSERT INTO etl_watermarks (source_table, last_processed_timestamp, updated_at)
    VALUES ('user_events', NOW(), NOW())
    ON CONFLICT (source_table) DO UPDATE SET
        last_processed_timestamp = NOW(),
        updated_at = NOW();
    
    RETURN QUERY SELECT v_processed, v_success, v_errors;
END;
$$ LANGUAGE plpgsql;

-- ===========================================
-- 初始化ETL控制数据
-- ===========================================

-- 初始化watermarks
INSERT INTO etl_watermarks (source_table, last_processed_timestamp) VALUES
('session_messages', '2024-01-01 00:00:00+00'),
('factual_memories', '2024-01-01 00:00:00+00'),
('episodic_memories', '2024-01-01 00:00:00+00'),
('semantic_memories', '2024-01-01 00:00:00+00'),
('procedural_memories', '2024-01-01 00:00:00+00'),
('working_memories', '2024-01-01 00:00:00+00'),
('session_memories', '2024-01-01 00:00:00+00'),
('user_events', '2024-01-01 00:00:00+00')
ON CONFLICT (source_table) DO NOTHING;

-- 创建ETL监控视图
CREATE OR REPLACE VIEW v_etl_dashboard AS
SELECT 
    jr.job_name,
    jr.job_type,
    jr.last_run_at,
    jr.success_rate,
    el.status as last_status,
    el.duration_seconds,
    el.records_processed,
    el.quality_score,
    CASE 
        WHEN el.end_time < NOW() - INTERVAL '1 day' THEN 'stale'
        WHEN el.status = 'failed' THEN 'failed' 
        WHEN el.status = 'running' AND el.start_time < NOW() - INTERVAL '2 hours' THEN 'stuck'
        ELSE 'healthy'
    END as health_status
FROM etl_job_registry jr
LEFT JOIN LATERAL (
    SELECT * FROM etl_execution_log 
    WHERE job_id = jr.job_id 
    ORDER BY start_time DESC 
    LIMIT 1
) el ON true
WHERE jr.is_active = TRUE;