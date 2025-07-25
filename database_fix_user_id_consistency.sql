-- Database Fix: User ID Consistency Issues
-- 解决 user_id 跨表不一致问题
-- 
-- 问题：
-- 1. session_memories 表的 user_id 是 uuid 类型，其他表都是 varchar(255)
-- 2. 外键关系使用业务键而非主键（不规范）
-- 3. 缺少数据完整性约束
--
-- 解决方案：
-- 1. 统一所有表的 user_id 字段为 varchar(255)
-- 2. 修复外键关系使用数据库主键
-- 3. 添加适当的索引和约束

-- =============================================================================
-- STEP 1: 修复 session_memories 表的 user_id 数据类型
-- =============================================================================

-- 备份当前数据（如果有）
CREATE TABLE IF NOT EXISTS dev.session_memories_backup AS 
SELECT * FROM dev.session_memories;

-- 修改 user_id 字段类型从 uuid 到 varchar(255)
ALTER TABLE dev.session_memories 
ALTER COLUMN user_id TYPE character varying(255);

-- 添加注释说明
COMMENT ON COLUMN dev.session_memories.user_id IS 'Auth0 用户ID，与其他表保持一致的varchar(255)格式';

-- =============================================================================
-- STEP 2: 标准化所有表的 user_id 字段（确保一致性）
-- =============================================================================

-- 确保所有表的 user_id 都是 varchar(255) 类型
ALTER TABLE dev.users ALTER COLUMN user_id TYPE character varying(255);
ALTER TABLE dev.subscriptions ALTER COLUMN user_id TYPE character varying(255);
ALTER TABLE dev.factual_memories ALTER COLUMN user_id TYPE character varying(255);
ALTER TABLE dev.episodic_memories ALTER COLUMN user_id TYPE character varying(255);
ALTER TABLE dev.procedural_memories ALTER COLUMN user_id TYPE character varying(255);
ALTER TABLE dev.semantic_memories ALTER COLUMN user_id TYPE character varying(255);
ALTER TABLE dev.working_memories ALTER COLUMN user_id TYPE character varying(255);
ALTER TABLE dev.events ALTER COLUMN user_id TYPE character varying(255);
ALTER TABLE dev.user_tasks ALTER COLUMN user_id TYPE character varying(255);

-- 处理可能为空的字段
ALTER TABLE dev.user_usage_records ALTER COLUMN user_id TYPE character varying(255);
ALTER TABLE dev.user_credit_transactions ALTER COLUMN user_id TYPE character varying(255);

-- =============================================================================
-- STEP 3: 添加用户表的复合唯一约束（如果不存在）
-- =============================================================================

-- 确保 user_id 在 users 表中是唯一的（业务键）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'users_user_id_unique'
    ) THEN
        ALTER TABLE dev.users ADD CONSTRAINT users_user_id_unique UNIQUE (user_id);
    END IF;
END $$;

-- =============================================================================
-- STEP 4: 修复外键关系 - 使用主键而非业务键
-- =============================================================================

-- 为相关表添加 user_pk_id 字段（引用 users.id 主键）
-- 注意：这是规范的数据库设计做法

-- 4.1 处理 factual_memories 表
DO $$
BEGIN
    -- 添加新的主键外键字段
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'dev' 
        AND table_name = 'factual_memories' 
        AND column_name = 'user_pk_id'
    ) THEN
        ALTER TABLE dev.factual_memories ADD COLUMN user_pk_id INTEGER;
        
        -- 填充数据：通过 user_id 查找对应的主键 id
        UPDATE dev.factual_memories 
        SET user_pk_id = u.id 
        FROM dev.users u 
        WHERE dev.factual_memories.user_id = u.user_id;
        
        -- 添加外键约束
        ALTER TABLE dev.factual_memories 
        ADD CONSTRAINT factual_memories_user_pk_fkey 
        FOREIGN KEY (user_pk_id) REFERENCES dev.users(id) ON DELETE CASCADE;
        
        -- 添加索引提高查询性能
        CREATE INDEX IF NOT EXISTS idx_factual_memories_user_pk_id 
        ON dev.factual_memories(user_pk_id);
    END IF;
END $$;

-- 4.2 处理 episodic_memories 表
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'dev' 
        AND table_name = 'episodic_memories' 
        AND column_name = 'user_pk_id'
    ) THEN
        ALTER TABLE dev.episodic_memories ADD COLUMN user_pk_id INTEGER;
        
        UPDATE dev.episodic_memories 
        SET user_pk_id = u.id 
        FROM dev.users u 
        WHERE dev.episodic_memories.user_id = u.user_id;
        
        ALTER TABLE dev.episodic_memories 
        ADD CONSTRAINT episodic_memories_user_pk_fkey 
        FOREIGN KEY (user_pk_id) REFERENCES dev.users(id) ON DELETE CASCADE;
        
        CREATE INDEX IF NOT EXISTS idx_episodic_memories_user_pk_id 
        ON dev.episodic_memories(user_pk_id);
    END IF;
END $$;

-- 4.3 处理 semantic_memories 表
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'dev' 
        AND table_name = 'semantic_memories' 
        AND column_name = 'user_pk_id'
    ) THEN
        ALTER TABLE dev.semantic_memories ADD COLUMN user_pk_id INTEGER;
        
        UPDATE dev.semantic_memories 
        SET user_pk_id = u.id 
        FROM dev.users u 
        WHERE dev.semantic_memories.user_id = u.user_id;
        
        ALTER TABLE dev.semantic_memories 
        ADD CONSTRAINT semantic_memories_user_pk_fkey 
        FOREIGN KEY (user_pk_id) REFERENCES dev.users(id) ON DELETE CASCADE;
        
        CREATE INDEX IF NOT EXISTS idx_semantic_memories_user_pk_id 
        ON dev.semantic_memories(user_pk_id);
    END IF;
END $$;

-- 4.4 处理 procedural_memories 表
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'dev' 
        AND table_name = 'procedural_memories' 
        AND column_name = 'user_pk_id'
    ) THEN
        ALTER TABLE dev.procedural_memories ADD COLUMN user_pk_id INTEGER;
        
        UPDATE dev.procedural_memories 
        SET user_pk_id = u.id 
        FROM dev.users u 
        WHERE dev.procedural_memories.user_id = u.user_id;
        
        ALTER TABLE dev.procedural_memories 
        ADD CONSTRAINT procedural_memories_user_pk_fkey 
        FOREIGN KEY (user_pk_id) REFERENCES dev.users(id) ON DELETE CASCADE;
        
        CREATE INDEX IF NOT EXISTS idx_procedural_memories_user_pk_id 
        ON dev.procedural_memories(user_pk_id);
    END IF;
END $$;

-- 4.5 处理 working_memories 表
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'dev' 
        AND table_name = 'working_memories' 
        AND column_name = 'user_pk_id'
    ) THEN
        ALTER TABLE dev.working_memories ADD COLUMN user_pk_id INTEGER;
        
        UPDATE dev.working_memories 
        SET user_pk_id = u.id 
        FROM dev.users u 
        WHERE dev.working_memories.user_id = u.user_id;
        
        ALTER TABLE dev.working_memories 
        ADD CONSTRAINT working_memories_user_pk_fkey 
        FOREIGN KEY (user_pk_id) REFERENCES dev.users(id) ON DELETE CASCADE;
        
        CREATE INDEX IF NOT EXISTS idx_working_memories_user_pk_id 
        ON dev.working_memories(user_pk_id);
    END IF;
END $$;

-- 4.6 处理 session_memories 表
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'dev' 
        AND table_name = 'session_memories' 
        AND column_name = 'user_pk_id'
    ) THEN
        ALTER TABLE dev.session_memories ADD COLUMN user_pk_id INTEGER;
        
        UPDATE dev.session_memories 
        SET user_pk_id = u.id 
        FROM dev.users u 
        WHERE dev.session_memories.user_id = u.user_id;
        
        ALTER TABLE dev.session_memories 
        ADD CONSTRAINT session_memories_user_pk_fkey 
        FOREIGN KEY (user_pk_id) REFERENCES dev.users(id) ON DELETE CASCADE;
        
        CREATE INDEX IF NOT EXISTS idx_session_memories_user_pk_id 
        ON dev.session_memories(user_pk_id);
    END IF;
END $$;

-- 4.7 处理 subscriptions 表
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'dev' 
        AND table_name = 'subscriptions' 
        AND column_name = 'user_pk_id'
    ) THEN
        ALTER TABLE dev.subscriptions ADD COLUMN user_pk_id INTEGER;
        
        UPDATE dev.subscriptions 
        SET user_pk_id = u.id 
        FROM dev.users u 
        WHERE dev.subscriptions.user_id = u.user_id;
        
        ALTER TABLE dev.subscriptions 
        ADD CONSTRAINT subscriptions_user_pk_fkey 
        FOREIGN KEY (user_pk_id) REFERENCES dev.users(id) ON DELETE CASCADE;
        
        CREATE INDEX IF NOT EXISTS idx_subscriptions_user_pk_id 
        ON dev.subscriptions(user_pk_id);
    END IF;
END $$;

-- =============================================================================
-- STEP 5: 添加性能优化索引
-- =============================================================================

-- 为 user_id 业务键添加索引（用于快速查找）
CREATE INDEX IF NOT EXISTS idx_users_user_id ON dev.users(user_id);
CREATE INDEX IF NOT EXISTS idx_factual_memories_user_id ON dev.factual_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_episodic_memories_user_id ON dev.episodic_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_semantic_memories_user_id ON dev.semantic_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_procedural_memories_user_id ON dev.procedural_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_working_memories_user_id ON dev.working_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_session_memories_user_id ON dev.session_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON dev.subscriptions(user_id);

-- =============================================================================
-- STEP 6: 数据验证查询
-- =============================================================================

-- 验证所有表的 user_id 字段类型一致性
SELECT 
    table_name,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'dev' 
  AND column_name = 'user_id'
ORDER BY table_name;

-- 验证外键关系
SELECT 
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND tc.table_schema = 'dev'
  AND (kcu.column_name LIKE '%user%' OR ccu.column_name LIKE '%user%')
ORDER BY tc.table_name;

-- 验证数据完整性：检查是否有孤立的 user_id
SELECT 
    'factual_memories' as table_name,
    COUNT(*) as orphaned_records
FROM dev.factual_memories fm
LEFT JOIN dev.users u ON fm.user_id = u.user_id
WHERE u.user_id IS NULL

UNION ALL

SELECT 
    'episodic_memories' as table_name,
    COUNT(*) as orphaned_records
FROM dev.episodic_memories em
LEFT JOIN dev.users u ON em.user_id = u.user_id
WHERE u.user_id IS NULL

UNION ALL

SELECT 
    'subscriptions' as table_name,
    COUNT(*) as orphaned_records
FROM dev.subscriptions s
LEFT JOIN dev.users u ON s.user_id = u.user_id
WHERE u.user_id IS NULL;

-- =============================================================================
-- 完成消息
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'User ID 一致性修复完成!';
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE '修复内容:';
    RAISE NOTICE '1. 统一所有表的 user_id 字段为 varchar(255)';
    RAISE NOTICE '2. 添加了标准的主键外键关系 (user_pk_id)';
    RAISE NOTICE '3. 保留了业务键 (user_id) 用于应用层查询';
    RAISE NOTICE '4. 添加了性能优化索引';
    RAISE NOTICE '5. 添加了数据完整性约束';
    RAISE NOTICE '';
    RAISE NOTICE '注意事项:';
    RAISE NOTICE '- user_id 字段继续用于应用层查询 (Auth0 ID)';
    RAISE NOTICE '- user_pk_id 字段用于数据库层面的外键关系';
    RAISE NOTICE '- 请运行上方的验证查询确认修复结果';
    RAISE NOTICE '=============================================================================';
END $$;