-- Schema Creation Script based on current dev schema
-- This script extracts the current dev schema structure and creates it in a target schema
-- Usage: psql -v target_schema=test -f this_file.sql

\set target_schema 'test'

-- Create schema if not exists
SELECT format('CREATE SCHEMA IF NOT EXISTS %I', :'target_schema') as create_schema \gexec

-- Grant permissions
SELECT format('GRANT ALL ON SCHEMA %I TO postgres', :'target_schema') as grant_all \gexec
SELECT format('GRANT USAGE ON SCHEMA %I TO anon, authenticated', :'target_schema') as grant_usage \gexec

-- Set search path
SELECT format('SET search_path TO %I, public', :'target_schema') as set_path \gexec

-- Now we'll copy the structure from dev schema to target schema
-- This will be populated with actual table definitions from dev schema