-- Migration: Create External Servers Table
-- Schema: mcp
-- Description: Stores external MCP server registrations for the aggregator service
--
-- This table tracks external MCP servers that provide additional tools/prompts/resources
-- The aggregator service connects to these servers and aggregates their capabilities

-- Ensure mcp schema exists
CREATE SCHEMA IF NOT EXISTS mcp;

-- Create enum for transport types
DO $$ BEGIN
    CREATE TYPE mcp.server_transport_type AS ENUM (
        'STDIO',           -- Standard input/output (local process)
        'SSE',             -- Server-Sent Events (HTTP streaming)
        'HTTP',            -- Standard HTTP request/response
        'STREAMABLE_HTTP'  -- MCP Streamable HTTP (bidirectional)
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Create enum for server status
DO $$ BEGIN
    CREATE TYPE mcp.server_status AS ENUM (
        'CONNECTED',       -- Server connected and healthy
        'DISCONNECTED',    -- Server intentionally disconnected
        'ERROR',           -- Server unreachable or failing
        'CONNECTING',      -- Connection in progress
        'DEGRADED'         -- Connected but elevated errors
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Create external servers table
CREATE TABLE IF NOT EXISTS mcp.external_servers (
    -- Primary key (UUID for distributed environments)
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Server identification
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,

    -- Connection configuration
    transport_type mcp.server_transport_type NOT NULL,
    connection_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    health_check_url TEXT,

    -- Connection status
    status mcp.server_status NOT NULL DEFAULT 'DISCONNECTED',
    error_message TEXT,

    -- Tool count (cached for performance)
    tool_count INTEGER NOT NULL DEFAULT 0,

    -- Timestamps
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    connected_at TIMESTAMPTZ,
    last_health_check TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT external_servers_name_length CHECK (char_length(name) >= 1),
    CONSTRAINT external_servers_name_format CHECK (name ~ '^[a-z][a-z0-9_-]*$'),
    CONSTRAINT external_servers_tool_count_check CHECK (tool_count >= 0)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_external_servers_name
    ON mcp.external_servers(name);

CREATE INDEX IF NOT EXISTS idx_external_servers_status
    ON mcp.external_servers(status);

CREATE INDEX IF NOT EXISTS idx_external_servers_connected
    ON mcp.external_servers(status)
    WHERE status = 'CONNECTED';

CREATE INDEX IF NOT EXISTS idx_external_servers_registered_at
    ON mcp.external_servers(registered_at DESC);

-- Create updated_at trigger (add column if we want tracking)
-- Note: Not adding updated_at to keep schema minimal, but registration info stays constant

-- Add comments
COMMENT ON TABLE mcp.external_servers IS 'Registry of external MCP servers for tool aggregation';
COMMENT ON COLUMN mcp.external_servers.id IS 'Unique server identifier (UUID)';
COMMENT ON COLUMN mcp.external_servers.name IS 'Server name used for namespacing (lowercase, hyphen-allowed)';
COMMENT ON COLUMN mcp.external_servers.transport_type IS 'MCP transport protocol (STDIO, SSE, HTTP, STREAMABLE_HTTP)';
COMMENT ON COLUMN mcp.external_servers.connection_config IS 'Transport-specific connection configuration (command/args/env for STDIO, url/headers for SSE/HTTP)';
COMMENT ON COLUMN mcp.external_servers.health_check_url IS 'Optional HTTP endpoint for health checks';
COMMENT ON COLUMN mcp.external_servers.status IS 'Current connection status';
COMMENT ON COLUMN mcp.external_servers.tool_count IS 'Number of tools discovered from this server';
COMMENT ON COLUMN mcp.external_servers.registered_at IS 'When the server was registered';
COMMENT ON COLUMN mcp.external_servers.connected_at IS 'Last successful connection time';
COMMENT ON COLUMN mcp.external_servers.last_health_check IS 'Last health check timestamp';

-- Grant permissions
GRANT ALL ON TABLE mcp.external_servers TO postgres;
