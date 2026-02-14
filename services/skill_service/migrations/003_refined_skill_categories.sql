-- Migration: Refined Skill Categories for Better Search Precision
-- Schema: mcp
-- Description: Replaces broad categories with specific, non-overlapping skill domains
--              Goal: Each tool should match 1-3 categories max (not 9+)

BEGIN;

-- ═══════════════════════════════════════════════════════════════════════════════
-- Step 0: Backup existing assignments before destructive operations
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS mcp.tool_skill_assignments_backup_003
    AS SELECT * FROM mcp.tool_skill_assignments;

-- ═══════════════════════════════════════════════════════════════════════════════
-- Step 1: Clear existing categories and assignments for fresh start
-- ═══════════════════════════════════════════════════════════════════════════════

-- Reset tool classifications (will be re-classified with new categories)
UPDATE mcp.tools SET
    skill_ids = ARRAY[]::TEXT[],
    primary_skill_id = NULL,
    is_classified = FALSE
WHERE is_active = TRUE;

-- Reset resource classifications
UPDATE mcp.resources SET
    skill_ids = ARRAY[]::TEXT[],
    primary_skill_id = NULL,
    is_classified = FALSE
WHERE is_active = TRUE;

-- Reset prompt classifications
UPDATE mcp.prompts SET
    skill_ids = ARRAY[]::TEXT[],
    primary_skill_id = NULL,
    is_classified = FALSE
WHERE is_active = TRUE;

-- Delete existing skill assignments
DELETE FROM mcp.tool_skill_assignments;

-- Deactivate old broad categories
UPDATE mcp.skill_categories SET is_active = FALSE, updated_at = NOW();

-- ═══════════════════════════════════════════════════════════════════════════════
-- Step 2: Insert Refined Skill Categories
-- Organized by domain with clear, non-overlapping boundaries
-- ═══════════════════════════════════════════════════════════════════════════════

INSERT INTO mcp.skill_categories (id, name, description, keywords, examples, parent_domain)
VALUES
    -- ═══════════════════════════════════════════════════════════════════════════
    -- PRODUCTIVITY DOMAIN
    -- ═══════════════════════════════════════════════════════════════════════════
    (
        'calendar-events',
        'Calendar & Events',
        'Managing calendar entries, scheduling meetings, appointments, and time-based events. NOT for generic task management.',
        ARRAY['calendar', 'event', 'meeting', 'appointment', 'schedule', 'booking', 'availability', 'invite', 'recurring'],
        ARRAY['create_calendar_event', 'get_today_events', 'update_meeting', 'check_availability', 'sync_calendar'],
        'productivity'
    ),
    (
        'task-management',
        'Task & Project Management',
        'Managing tasks, todos, tickets, issues, and project work items. Includes kanban, sprints, and work tracking.',
        ARRAY['task', 'todo', 'ticket', 'issue', 'project', 'sprint', 'kanban', 'assign', 'priority', 'deadline'],
        ARRAY['create_task', 'update_ticket', 'list_todos', 'assign_issue', 'move_to_sprint'],
        'productivity'
    ),
    (
        'notes-knowledge',
        'Notes & Knowledge Base',
        'Creating, storing, and retrieving notes, documentation, wikis, and knowledge articles. Memory and recall operations.',
        ARRAY['note', 'wiki', 'knowledge', 'documentation', 'memory', 'recall', 'store', 'remember', 'journal'],
        ARRAY['save_note', 'search_knowledge', 'update_wiki', 'recall_memory', 'create_doc'],
        'productivity'
    ),

    -- ═══════════════════════════════════════════════════════════════════════════
    -- DEVELOPMENT DOMAIN
    -- ═══════════════════════════════════════════════════════════════════════════
    (
        'code-generation',
        'Code Generation',
        'Writing, generating, and creating code, scripts, and programs. Includes code completion and scaffolding.',
        ARRAY['generate', 'write', 'create', 'code', 'script', 'program', 'scaffold', 'template', 'boilerplate'],
        ARRAY['generate_code', 'write_function', 'create_class', 'scaffold_project', 'generate_test'],
        'development'
    ),
    (
        'code-analysis',
        'Code Analysis & Quality',
        'Analyzing, reviewing, linting, and improving code quality. Includes refactoring and code metrics.',
        ARRAY['lint', 'analyze', 'review', 'refactor', 'quality', 'metrics', 'complexity', 'coverage', 'smell'],
        ARRAY['lint_code', 'analyze_complexity', 'review_pr', 'refactor_function', 'check_coverage'],
        'development'
    ),
    (
        'version-control',
        'Version Control & Git',
        'Git operations, repository management, commits, branches, and merge operations.',
        ARRAY['git', 'commit', 'branch', 'merge', 'pull', 'push', 'repository', 'diff', 'checkout', 'rebase'],
        ARRAY['git_commit', 'create_branch', 'merge_pr', 'git_diff', 'clone_repo'],
        'development'
    ),
    (
        'testing-debug',
        'Testing & Debugging',
        'Running tests, debugging code, and validating functionality. Includes unit tests, integration tests, and debugging tools.',
        ARRAY['test', 'debug', 'validate', 'assert', 'mock', 'unittest', 'integration', 'e2e', 'breakpoint'],
        ARRAY['run_tests', 'debug_code', 'validate_input', 'create_mock', 'set_breakpoint'],
        'development'
    ),

    -- ═══════════════════════════════════════════════════════════════════════════
    -- DATA DOMAIN
    -- ═══════════════════════════════════════════════════════════════════════════
    (
        'data-query',
        'Data Query & SQL',
        'Querying databases, executing SQL, and retrieving structured data. NOT for full-text search.',
        ARRAY['sql', 'query', 'select', 'join', 'where', 'database', 'table', 'row', 'column', 'postgres', 'mysql'],
        ARRAY['execute_sql', 'query_table', 'join_tables', 'aggregate_data', 'run_query'],
        'data'
    ),
    (
        'data-transform',
        'Data Transformation & ETL',
        'Transforming, cleaning, and processing data. Includes ETL pipelines, data cleaning, and format conversion.',
        ARRAY['transform', 'etl', 'clean', 'normalize', 'convert', 'map', 'filter', 'aggregate', 'pipeline'],
        ARRAY['transform_data', 'clean_dataset', 'run_etl', 'normalize_values', 'convert_format'],
        'data'
    ),
    (
        'data-visualization',
        'Data Visualization & Reports',
        'Creating charts, graphs, dashboards, and visual reports from data.',
        ARRAY['chart', 'graph', 'visualization', 'dashboard', 'plot', 'report', 'histogram', 'pie', 'bar', 'line'],
        ARRAY['create_chart', 'plot_data', 'generate_report', 'build_dashboard', 'render_graph'],
        'data'
    ),
    (
        'data-storage',
        'Data Storage & CRUD',
        'Storing, updating, and deleting data records. Basic CRUD operations on databases and data stores.',
        ARRAY['insert', 'update', 'delete', 'save', 'store', 'persist', 'crud', 'record', 'entity'],
        ARRAY['insert_record', 'update_row', 'delete_entry', 'save_data', 'upsert_record'],
        'data'
    ),

    -- ═══════════════════════════════════════════════════════════════════════════
    -- INTEGRATION DOMAIN
    -- ═══════════════════════════════════════════════════════════════════════════
    (
        'http-api',
        'HTTP & REST APIs',
        'Making HTTP requests, calling REST APIs, and handling web requests/responses.',
        ARRAY['http', 'rest', 'api', 'request', 'response', 'get', 'post', 'put', 'fetch', 'endpoint'],
        ARRAY['fetch_url', 'call_api', 'post_data', 'get_resource', 'make_request'],
        'integration'
    ),
    (
        'webhooks-events',
        'Webhooks & Event Triggers',
        'Setting up webhooks, handling callbacks, and event-driven integrations.',
        ARRAY['webhook', 'callback', 'trigger', 'event', 'subscribe', 'publish', 'hook', 'listener'],
        ARRAY['create_webhook', 'handle_callback', 'trigger_event', 'subscribe_topic', 'register_hook'],
        'integration'
    ),
    (
        'external-services',
        'External Service Integration',
        'Integrating with third-party services like Notion, Slack, Google, AWS, etc.',
        ARRAY['notion', 'slack', 'google', 'aws', 'azure', 'stripe', 'twilio', 'github', 'jira', 'salesforce'],
        ARRAY['sync_notion', 'post_to_slack', 'upload_to_s3', 'create_github_issue', 'send_via_twilio'],
        'integration'
    ),
    (
        'message-queue',
        'Message Queue & Streaming',
        'Working with message queues, pub/sub systems, and data streaming.',
        ARRAY['queue', 'pubsub', 'kafka', 'rabbitmq', 'nats', 'redis', 'stream', 'publish', 'consume', 'message'],
        ARRAY['publish_message', 'consume_queue', 'stream_data', 'subscribe_topic', 'send_to_queue'],
        'integration'
    ),

    -- ═══════════════════════════════════════════════════════════════════════════
    -- COMMUNICATION DOMAIN
    -- ═══════════════════════════════════════════════════════════════════════════
    (
        'email',
        'Email Operations',
        'Sending, receiving, and managing emails. Includes templates and email automation.',
        ARRAY['email', 'mail', 'smtp', 'inbox', 'send', 'receive', 'attachment', 'template', 'newsletter'],
        ARRAY['send_email', 'read_inbox', 'compose_email', 'attach_file', 'send_newsletter'],
        'communication'
    ),
    (
        'chat-messaging',
        'Chat & Instant Messaging',
        'Sending messages via chat platforms, SMS, and instant messaging services.',
        ARRAY['chat', 'message', 'sms', 'slack', 'teams', 'discord', 'telegram', 'whatsapp', 'im'],
        ARRAY['send_message', 'post_to_channel', 'send_sms', 'dm_user', 'create_thread'],
        'communication'
    ),
    (
        'notifications',
        'Notifications & Alerts',
        'Sending push notifications, alerts, and system notifications.',
        ARRAY['notification', 'alert', 'push', 'notify', 'remind', 'alarm', 'warning', 'toast'],
        ARRAY['send_notification', 'create_alert', 'push_to_device', 'schedule_reminder', 'trigger_alarm'],
        'communication'
    ),

    -- ═══════════════════════════════════════════════════════════════════════════
    -- CONTENT DOMAIN
    -- ═══════════════════════════════════════════════════════════════════════════
    (
        'document-processing',
        'Document Processing',
        'Processing documents like PDF, Word, Excel. Includes extraction, conversion, and manipulation.',
        ARRAY['pdf', 'word', 'excel', 'document', 'docx', 'xlsx', 'extract', 'parse', 'convert'],
        ARRAY['extract_pdf_text', 'convert_to_pdf', 'parse_excel', 'merge_documents', 'split_pdf'],
        'content'
    ),
    (
        'image-processing',
        'Image Processing',
        'Processing, manipulating, and generating images. Includes resize, crop, convert, and AI image generation.',
        ARRAY['image', 'photo', 'picture', 'resize', 'crop', 'thumbnail', 'convert', 'compress', 'generate'],
        ARRAY['resize_image', 'crop_photo', 'generate_image', 'convert_format', 'create_thumbnail'],
        'content'
    ),
    (
        'audio-video',
        'Audio & Video Processing',
        'Processing audio and video files. Includes transcription, conversion, and editing.',
        ARRAY['audio', 'video', 'transcribe', 'convert', 'mp3', 'mp4', 'wav', 'recording', 'subtitle'],
        ARRAY['transcribe_audio', 'convert_video', 'extract_audio', 'add_subtitles', 'compress_video'],
        'content'
    ),
    (
        'text-generation',
        'Text & Content Generation',
        'Generating text content using AI/LLM. Includes summaries, translations, and creative writing.',
        ARRAY['generate', 'summarize', 'translate', 'write', 'compose', 'llm', 'gpt', 'claude', 'completion'],
        ARRAY['generate_text', 'summarize_article', 'translate_text', 'write_content', 'complete_text'],
        'content'
    ),

    -- ═══════════════════════════════════════════════════════════════════════════
    -- SECURITY DOMAIN
    -- ═══════════════════════════════════════════════════════════════════════════
    (
        'authentication',
        'Authentication',
        'User authentication, login, logout, and identity verification.',
        ARRAY['auth', 'login', 'logout', 'authenticate', 'token', 'jwt', 'oauth', 'session', 'credential'],
        ARRAY['login_user', 'verify_token', 'refresh_session', 'oauth_callback', 'validate_credentials'],
        'security'
    ),
    (
        'authorization',
        'Authorization & Permissions',
        'Managing permissions, roles, and access control.',
        ARRAY['permission', 'role', 'access', 'authorize', 'acl', 'rbac', 'grant', 'revoke', 'policy'],
        ARRAY['check_permission', 'assign_role', 'grant_access', 'revoke_permission', 'create_policy'],
        'security'
    ),
    (
        'encryption',
        'Encryption & Security',
        'Encrypting, decrypting, hashing, and securing data.',
        ARRAY['encrypt', 'decrypt', 'hash', 'sign', 'verify', 'secret', 'key', 'certificate', 'ssl'],
        ARRAY['encrypt_data', 'decrypt_message', 'hash_password', 'sign_document', 'verify_signature'],
        'security'
    ),

    -- ═══════════════════════════════════════════════════════════════════════════
    -- SYSTEM DOMAIN
    -- ═══════════════════════════════════════════════════════════════════════════
    (
        'file-system',
        'File System Operations',
        'Reading, writing, and managing files and directories on the file system.',
        ARRAY['file', 'read', 'write', 'directory', 'folder', 'path', 'copy', 'move', 'delete', 'rename'],
        ARRAY['read_file', 'write_file', 'list_directory', 'copy_file', 'delete_file'],
        'system'
    ),
    (
        'process-shell',
        'Process & Shell Commands',
        'Running shell commands, managing processes, and executing scripts.',
        ARRAY['process', 'shell', 'command', 'execute', 'run', 'script', 'bash', 'terminal', 'cli'],
        ARRAY['run_command', 'execute_script', 'spawn_process', 'kill_process', 'run_shell'],
        'system'
    ),
    (
        'monitoring-logs',
        'Monitoring & Logging',
        'Monitoring system health, collecting metrics, and managing logs.',
        ARRAY['monitor', 'log', 'metric', 'health', 'status', 'trace', 'observe', 'alert', 'dashboard'],
        ARRAY['check_health', 'collect_metrics', 'tail_logs', 'create_alert', 'track_status'],
        'system'
    ),
    (
        'deployment-devops',
        'Deployment & DevOps',
        'Deploying applications, managing containers, and infrastructure operations.',
        ARRAY['deploy', 'docker', 'kubernetes', 'container', 'ci', 'cd', 'pipeline', 'infrastructure', 'terraform'],
        ARRAY['deploy_app', 'build_container', 'scale_service', 'run_pipeline', 'provision_infra'],
        'system'
    ),

    -- ═══════════════════════════════════════════════════════════════════════════
    -- SEARCH DOMAIN
    -- ═══════════════════════════════════════════════════════════════════════════
    (
        'text-search',
        'Text & Full-Text Search',
        'Searching through text content, documents, and full-text indexes.',
        ARRAY['search', 'find', 'fulltext', 'index', 'match', 'lookup', 'grep', 'filter'],
        ARRAY['search_documents', 'find_text', 'fulltext_search', 'lookup_term', 'filter_results'],
        'search'
    ),
    (
        'vector-semantic',
        'Vector & Semantic Search',
        'Semantic search using embeddings and vector similarity.',
        ARRAY['vector', 'semantic', 'embedding', 'similarity', 'qdrant', 'pinecone', 'nearest', 'cosine'],
        ARRAY['semantic_search', 'find_similar', 'vector_query', 'embedding_search', 'nearest_neighbors'],
        'search'
    ),
    (
        'web-search',
        'Web Search & Scraping',
        'Searching the web and scraping web content.',
        ARRAY['web', 'scrape', 'crawl', 'google', 'bing', 'browser', 'html', 'dom', 'selector'],
        ARRAY['web_search', 'scrape_page', 'crawl_site', 'extract_html', 'parse_dom'],
        'search'
    ),

    -- ═══════════════════════════════════════════════════════════════════════════
    -- SPECIALIZED DOMAINS
    -- ═══════════════════════════════════════════════════════════════════════════
    (
        'weather-environment',
        'Weather & Environment',
        'Getting weather forecasts, environmental data, and location-based information.',
        ARRAY['weather', 'forecast', 'temperature', 'climate', 'location', 'geo', 'map', 'coordinates'],
        ARRAY['get_weather', 'forecast_weather', 'get_location', 'geocode_address', 'get_timezone'],
        'specialized'
    ),
    (
        'payment-billing',
        'Payment & Billing',
        'Processing payments, managing subscriptions, and billing operations.',
        ARRAY['payment', 'billing', 'invoice', 'subscription', 'charge', 'refund', 'stripe', 'checkout'],
        ARRAY['process_payment', 'create_invoice', 'charge_card', 'refund_payment', 'manage_subscription'],
        'specialized'
    ),
    (
        'user-management',
        'User Management',
        'Managing user accounts, profiles, and user-related operations.',
        ARRAY['user', 'account', 'profile', 'registration', 'signup', 'settings', 'preferences'],
        ARRAY['create_user', 'update_profile', 'delete_account', 'get_user', 'update_settings'],
        'specialized'
    ),
    (
        'analytics-metrics',
        'Analytics & Business Metrics',
        'Tracking analytics, business metrics, and usage statistics.',
        ARRAY['analytics', 'metrics', 'statistics', 'tracking', 'usage', 'conversion', 'funnel', 'kpi'],
        ARRAY['track_event', 'get_analytics', 'calculate_metrics', 'generate_stats', 'measure_kpi'],
        'specialized'
    )

ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    keywords = EXCLUDED.keywords,
    examples = EXCLUDED.examples,
    parent_domain = EXCLUDED.parent_domain,
    is_active = TRUE,
    tool_count = 0,
    updated_at = NOW();

-- ═══════════════════════════════════════════════════════════════════════════════
-- Step 3: Log completion
-- ═══════════════════════════════════════════════════════════════════════════════

DO $$
DECLARE
    category_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO category_count FROM mcp.skill_categories WHERE is_active = TRUE;
    RAISE NOTICE 'Refined skill categories: % active categories', category_count;
    RAISE NOTICE 'All tools/resources/prompts reset for re-classification';
END $$;

COMMIT;

-- ═══════════════════════════════════════════════════════════════════════════════
-- DOWN / ROLLBACK
-- ═══════════════════════════════════════════════════════════════════════════════
-- To rollback this migration:
--   BEGIN;
--   DELETE FROM mcp.tool_skill_assignments;
--   INSERT INTO mcp.tool_skill_assignments SELECT * FROM mcp.tool_skill_assignments_backup_003;
--   UPDATE mcp.skill_categories SET is_active = TRUE, updated_at = NOW();
--   DROP TABLE IF EXISTS mcp.tool_skill_assignments_backup_003;
--   COMMIT;
