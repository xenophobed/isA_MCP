-- Universal Schema Template based on current dev schema
-- This script can create the same structure in any target schema
-- Usage: 
--   For test: psql -v target_schema=test -f create_schema_template.sql
--   For staging: psql -v target_schema=staging -f create_schema_template.sql

-- Default to test if no variable provided
\set target_schema `echo ${target_schema:-test}`

\echo 'Creating schema structure for:' :target_schema

-- Create schema and permissions
SELECT format('CREATE SCHEMA IF NOT EXISTS %I', :'target_schema') as cmd \gexec
SELECT format('GRANT ALL ON SCHEMA %I TO postgres', :'target_schema') as cmd \gexec
SELECT format('GRANT USAGE ON SCHEMA %I TO anon, authenticated', :'target_schema') as cmd \gexec

-- Create all sequences first
SELECT format('CREATE SEQUENCE IF NOT EXISTS %I.carts_id_seq', :'target_schema') as cmd \gexec
SELECT format('CREATE SEQUENCE IF NOT EXISTS %I.events_id_seq', :'target_schema') as cmd \gexec
SELECT format('CREATE SEQUENCE IF NOT EXISTS %I.sessions_id_seq', :'target_schema') as cmd \gexec
SELECT format('CREATE SEQUENCE IF NOT EXISTS %I.users_id_seq', :'target_schema') as cmd \gexec
SELECT format('CREATE SEQUENCE IF NOT EXISTS %I.mcp_prompts_id_seq', :'target_schema') as cmd \gexec
SELECT format('CREATE SEQUENCE IF NOT EXISTS %I.mcp_resources_id_seq', :'target_schema') as cmd \gexec
SELECT format('CREATE SEQUENCE IF NOT EXISTS %I.mcp_tools_id_seq', :'target_schema') as cmd \gexec
SELECT format('CREATE SEQUENCE IF NOT EXISTS %I.models_id_seq', :'target_schema') as cmd \gexec
-- Add more sequences as needed

-- Create tables (order matters for foreign keys)

-- 1. Users table (foundational)
SELECT format('
CREATE TABLE IF NOT EXISTS %I.users (
    id INTEGER NOT NULL DEFAULT nextval(''%I.users_id_seq''::regclass) PRIMARY KEY,
    user_id CHARACTER VARYING(255) NOT NULL UNIQUE,
    auth0_id CHARACTER VARYING(255),
    email CHARACTER VARYING(255),
    phone CHARACTER VARYING(50),
    name CHARACTER VARYING(255),
    credits_remaining NUMERIC(10,3) DEFAULT 1000,
    credits_total NUMERIC(10,3) DEFAULT 1000,
    subscription_status CHARACTER VARYING(50) DEFAULT ''free'',
    is_active BOOLEAN DEFAULT true,
    shipping_addresses JSONB DEFAULT ''[]''::jsonb,
    payment_methods JSONB DEFAULT ''[]''::jsonb,
    preferences JSONB DEFAULT ''{}''::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
)', :'target_schema', :'target_schema') as cmd \gexec

-- 2. Sessions table
SELECT format('
CREATE TABLE IF NOT EXISTS %I.sessions (
    id INTEGER NOT NULL DEFAULT nextval(''%I.sessions_id_seq''::regclass) PRIMARY KEY,
    session_id TEXT UNIQUE NOT NULL,
    user_id CHARACTER VARYING(255) REFERENCES %I.users(user_id) ON DELETE CASCADE,
    chat_history JSONB DEFAULT ''[]''::jsonb,
    context_state JSONB DEFAULT ''{}''::jsonb,
    session_metadata JSONB DEFAULT ''{}''::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    expires_at TIMESTAMP WITH TIME ZONE
)', :'target_schema', :'target_schema', :'target_schema') as cmd \gexec

-- 3. Core MCP tables
SELECT format('
CREATE TABLE IF NOT EXISTS %I.mcp_tools (
    id INTEGER NOT NULL DEFAULT nextval(''%I.mcp_tools_id_seq''::regclass) PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    input_schema JSONB,
    category TEXT,
    provider TEXT,
    version TEXT DEFAULT ''1.0'',
    is_active BOOLEAN DEFAULT true,
    usage_count INTEGER DEFAULT 0,
    average_rating NUMERIC(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
)', :'target_schema', :'target_schema') as cmd \gexec

-- Add indexes for performance
SELECT format('CREATE INDEX IF NOT EXISTS idx_%I_users_email ON %I.users(email)', :'target_schema', :'target_schema') as cmd \gexec
SELECT format('CREATE INDEX IF NOT EXISTS idx_%I_users_auth0_id ON %I.users(auth0_id)', :'target_schema', :'target_schema') as cmd \gexec
SELECT format('CREATE INDEX IF NOT EXISTS idx_%I_sessions_user_id ON %I.sessions(user_id)', :'target_schema', :'target_schema') as cmd \gexec
SELECT format('CREATE INDEX IF NOT EXISTS idx_%I_sessions_active ON %I.sessions(is_active)', :'target_schema', :'target_schema') as cmd \gexec

\echo 'Schema creation completed for:' :target_schema