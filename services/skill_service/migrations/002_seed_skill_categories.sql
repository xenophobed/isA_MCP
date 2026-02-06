-- Migration: Seed Initial Skill Categories
-- Schema: mcp
-- Description: Populates initial skill categories for tool classification

-- ═══════════════════════════════════════════════════════════════════════════════
-- Core Skill Categories
-- These represent common capability domains for MCP tools
-- ═══════════════════════════════════════════════════════════════════════════════

INSERT INTO mcp.skill_categories (id, name, description, keywords, examples, parent_domain)
VALUES
    -- Calendar & Scheduling
    (
        'calendar-management',
        'Calendar Management',
        'Tools for managing calendars, scheduling events, meetings, and appointments. Includes creating, updating, deleting, and querying calendar entries.',
        ARRAY['calendar', 'event', 'meeting', 'appointment', 'schedule', 'booking', 'reminder', 'invite', 'availability'],
        ARRAY['create_calendar_event', 'list_events', 'update_meeting', 'check_availability', 'send_meeting_invite'],
        'productivity'
    ),

    -- File Operations
    (
        'file-operations',
        'File Operations',
        'Tools for reading, writing, managing, and manipulating files and directories. Includes CRUD operations, file search, and file system navigation.',
        ARRAY['file', 'read', 'write', 'directory', 'folder', 'path', 'upload', 'download', 'copy', 'move', 'delete'],
        ARRAY['read_file', 'write_file', 'list_directory', 'create_folder', 'move_file', 'delete_file'],
        'system'
    ),

    -- Code & Development
    (
        'code-development',
        'Code & Development',
        'Tools for writing, analyzing, refactoring, and managing code. Includes code generation, linting, formatting, and repository operations.',
        ARRAY['code', 'programming', 'development', 'git', 'repository', 'commit', 'branch', 'refactor', 'lint', 'format'],
        ARRAY['run_code', 'git_commit', 'create_branch', 'lint_code', 'format_code', 'analyze_code'],
        'development'
    ),

    -- Data Analysis
    (
        'data-analysis',
        'Data Analysis',
        'Tools for analyzing, transforming, and visualizing data. Includes statistical analysis, data transformation, and charting.',
        ARRAY['data', 'analysis', 'statistics', 'visualization', 'chart', 'graph', 'transform', 'aggregate', 'query', 'sql'],
        ARRAY['analyze_data', 'create_chart', 'run_query', 'aggregate_data', 'transform_data'],
        'analytics'
    ),

    -- Web & API
    (
        'web-api',
        'Web & API Operations',
        'Tools for making HTTP requests, interacting with web APIs, web scraping, and browser automation.',
        ARRAY['http', 'api', 'request', 'fetch', 'web', 'url', 'rest', 'graphql', 'scrape', 'browser'],
        ARRAY['fetch_url', 'make_api_call', 'scrape_webpage', 'browser_navigate', 'parse_html'],
        'integration'
    ),

    -- Communication
    (
        'communication',
        'Communication',
        'Tools for sending messages, emails, notifications, and managing communication channels.',
        ARRAY['email', 'message', 'notification', 'chat', 'slack', 'sms', 'send', 'notify', 'alert'],
        ARRAY['send_email', 'send_message', 'post_to_slack', 'send_notification', 'send_sms'],
        'productivity'
    ),

    -- Search & Retrieval
    (
        'search-retrieval',
        'Search & Retrieval',
        'Tools for searching, querying, and retrieving information from various sources including databases, documents, and the web.',
        ARRAY['search', 'find', 'query', 'retrieve', 'lookup', 'discover', 'filter', 'semantic', 'vector'],
        ARRAY['search_documents', 'find_files', 'query_database', 'semantic_search', 'web_search'],
        'information'
    ),

    -- AI & ML
    (
        'ai-ml',
        'AI & Machine Learning',
        'Tools for AI-powered operations including LLM interactions, embeddings, image generation, and ML model inference.',
        ARRAY['ai', 'ml', 'llm', 'embedding', 'generate', 'inference', 'model', 'vision', 'audio', 'transcribe'],
        ARRAY['generate_text', 'create_embedding', 'generate_image', 'transcribe_audio', 'analyze_image'],
        'intelligence'
    ),

    -- Document Processing
    (
        'document-processing',
        'Document Processing',
        'Tools for processing documents including PDF, Word, markdown, and other document formats. Includes extraction, conversion, and manipulation.',
        ARRAY['document', 'pdf', 'word', 'markdown', 'extract', 'convert', 'parse', 'ocr', 'text'],
        ARRAY['extract_pdf_text', 'convert_document', 'parse_markdown', 'ocr_image', 'create_pdf'],
        'content'
    ),

    -- Database Operations
    (
        'database-operations',
        'Database Operations',
        'Tools for interacting with databases including CRUD operations, schema management, and query execution.',
        ARRAY['database', 'sql', 'query', 'insert', 'update', 'delete', 'schema', 'table', 'migration'],
        ARRAY['execute_query', 'insert_record', 'update_record', 'create_table', 'run_migration'],
        'data'
    ),

    -- Image & Media
    (
        'image-media',
        'Image & Media Processing',
        'Tools for processing images, videos, and audio files. Includes manipulation, conversion, and analysis.',
        ARRAY['image', 'video', 'audio', 'media', 'resize', 'crop', 'convert', 'compress', 'thumbnail'],
        ARRAY['resize_image', 'convert_video', 'extract_audio', 'create_thumbnail', 'compress_media'],
        'content'
    ),

    -- Authentication & Security
    (
        'auth-security',
        'Authentication & Security',
        'Tools for authentication, authorization, encryption, and security-related operations.',
        ARRAY['auth', 'authentication', 'authorization', 'security', 'encrypt', 'decrypt', 'token', 'password', 'oauth'],
        ARRAY['authenticate_user', 'generate_token', 'encrypt_data', 'verify_signature', 'manage_permissions'],
        'security'
    ),

    -- Task Management
    (
        'task-management',
        'Task Management',
        'Tools for managing tasks, projects, tickets, and work items. Includes creation, updating, and tracking.',
        ARRAY['task', 'todo', 'ticket', 'issue', 'project', 'jira', 'trello', 'asana', 'kanban'],
        ARRAY['create_task', 'update_ticket', 'list_issues', 'move_card', 'assign_task'],
        'productivity'
    ),

    -- System Administration
    (
        'system-admin',
        'System Administration',
        'Tools for system administration including process management, monitoring, and configuration.',
        ARRAY['system', 'process', 'monitor', 'config', 'environment', 'deploy', 'container', 'docker', 'kubernetes'],
        ARRAY['run_command', 'check_status', 'deploy_service', 'manage_container', 'set_config'],
        'system'
    ),

    -- Knowledge Management
    (
        'knowledge-management',
        'Knowledge Management',
        'Tools for managing knowledge bases, wikis, notes, and documentation.',
        ARRAY['knowledge', 'wiki', 'notes', 'documentation', 'memory', 'store', 'recall', 'organize'],
        ARRAY['save_note', 'search_knowledge', 'update_wiki', 'recall_memory', 'organize_docs'],
        'information'
    )
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    keywords = EXCLUDED.keywords,
    examples = EXCLUDED.examples,
    parent_domain = EXCLUDED.parent_domain,
    updated_at = NOW();

-- Log seed completion
DO $$
BEGIN
    RAISE NOTICE 'Seeded % skill categories', (SELECT COUNT(*) FROM mcp.skill_categories);
END $$;
