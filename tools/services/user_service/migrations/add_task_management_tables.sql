-- Task Management Tables Migration
-- Adds missing fields to user_tasks table and creates task_executions and task_templates tables

-- First, update the existing user_tasks table to add missing fields
ALTER TABLE dev.user_tasks 
ADD COLUMN IF NOT EXISTS name VARCHAR(200),
ADD COLUMN IF NOT EXISTS priority VARCHAR(50) DEFAULT 'medium',
ADD COLUMN IF NOT EXISTS schedule JSONB,
ADD COLUMN IF NOT EXISTS next_run_time TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS last_run_time TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS last_success_time TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS run_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS success_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS failure_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS credits_per_run DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS total_credits_consumed DECIMAL(10,2) DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS last_result JSONB,
ADD COLUMN IF NOT EXISTS last_error TEXT,
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS tags TEXT[],
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;

-- Update status column to use new enum values if needed
-- ALTER TABLE dev.user_tasks ALTER COLUMN status TYPE VARCHAR(50);

-- Create task_executions table
CREATE TABLE IF NOT EXISTS dev.task_executions (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(255) UNIQUE NOT NULL,
    task_id UUID NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    
    -- Execution information
    status VARCHAR(50) NOT NULL DEFAULT 'running',
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    
    -- Result information
    result JSONB,
    error_message TEXT,
    error_details JSONB,
    
    -- Resource consumption
    credits_consumed DECIMAL(10,2) DEFAULT 0.0,
    tokens_used INTEGER,
    api_calls_made INTEGER DEFAULT 0,
    
    -- Context information
    trigger_type VARCHAR(50) NOT NULL,
    trigger_data JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Foreign key constraints
    FOREIGN KEY (task_id) REFERENCES dev.user_tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
);

-- Create task_templates table
CREATE TABLE IF NOT EXISTS dev.task_templates (
    id SERIAL PRIMARY KEY,
    template_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    category VARCHAR(100) NOT NULL,
    
    -- Template configuration
    config_schema JSONB NOT NULL,
    default_config JSONB NOT NULL,
    
    -- Permissions and billing
    required_subscription_level VARCHAR(50) DEFAULT 'free',
    credits_per_run DECIMAL(10,2) NOT NULL,
    
    -- Metadata
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for task_executions
CREATE INDEX IF NOT EXISTS idx_task_executions_task_id ON dev.task_executions(task_id);
CREATE INDEX IF NOT EXISTS idx_task_executions_user_id ON dev.task_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_task_executions_status ON dev.task_executions(status);
CREATE INDEX IF NOT EXISTS idx_task_executions_started_at ON dev.task_executions(started_at);
CREATE INDEX IF NOT EXISTS idx_task_executions_execution_id ON dev.task_executions(execution_id);

-- Create indexes for task_templates
CREATE INDEX IF NOT EXISTS idx_task_templates_template_id ON dev.task_templates(template_id);
CREATE INDEX IF NOT EXISTS idx_task_templates_task_type ON dev.task_templates(task_type);
CREATE INDEX IF NOT EXISTS idx_task_templates_category ON dev.task_templates(category);
CREATE INDEX IF NOT EXISTS idx_task_templates_is_active ON dev.task_templates(is_active);

-- Additional indexes for updated user_tasks table
CREATE INDEX IF NOT EXISTS idx_user_tasks_name ON dev.user_tasks(name);
CREATE INDEX IF NOT EXISTS idx_user_tasks_priority ON dev.user_tasks(priority);
CREATE INDEX IF NOT EXISTS idx_user_tasks_next_run_time ON dev.user_tasks(next_run_time);
CREATE INDEX IF NOT EXISTS idx_user_tasks_last_run_time ON dev.user_tasks(last_run_time);
CREATE INDEX IF NOT EXISTS idx_user_tasks_deleted_at ON dev.user_tasks(deleted_at);

-- Insert some default task templates
INSERT INTO dev.task_templates (template_id, name, description, task_type, category, config_schema, default_config, credits_per_run) VALUES 
('daily_weather', '每日天气', '每天定时发送天气预报', 'daily_weather', 'productivity', 
 '{"location": {"type": "string", "required": true}, "notification_time": {"type": "string", "default": "08:00"}}',
 '{"location": "北京", "notification_time": "08:00"}',
 0.5),
('daily_news', '每日新闻', '每天定时发送新闻摘要', 'daily_news', 'productivity',
 '{"categories": {"type": "array", "items": {"type": "string"}}, "notification_time": {"type": "string", "default": "08:00"}}',
 '{"categories": ["科技", "财经"], "notification_time": "08:00"}',
 1.0),
('data_backup', '数据备份', '定期备份重要数据', 'data_backup', 'maintenance',
 '{"backup_path": {"type": "string", "required": true}, "compression": {"type": "boolean", "default": true}}',
 '{"backup_path": "/backup", "compression": true}',
 2.0)
ON CONFLICT (template_id) DO NOTHING;

-- Update existing tasks to have default names if they don't have one
UPDATE dev.user_tasks 
SET name = COALESCE(name, 'Task ' || task_id::text)
WHERE name IS NULL OR name = '';

COMMENT ON TABLE dev.task_executions IS '任务执行记录表，存储每次任务执行的详细信息';
COMMENT ON TABLE dev.task_templates IS '任务模板表，存储预定义的任务模板';
COMMENT ON COLUMN dev.user_tasks.name IS '任务名称';
COMMENT ON COLUMN dev.user_tasks.priority IS '任务优先级：low, medium, high, urgent';
COMMENT ON COLUMN dev.user_tasks.schedule IS '任务调度配置';
COMMENT ON COLUMN dev.user_tasks.metadata IS '任务元数据';
COMMENT ON COLUMN dev.user_tasks.tags IS '任务标签数组';