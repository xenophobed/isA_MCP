# Staging MCP Service Deployment

## Docker Build

### 1. Build Docker Image

```bash
# Navigate to project root
cd /Users/xenodennis/Documents/Fun/isA_MCP

# Build staging Docker image for x86_64
docker build --platform linux/amd64 \
  -f deployment/staging/Dockerfile.staging \
  -t staging-isa-mcp:amd64 .
```

### 2. Image Info
- **Image Name**: staging-isa-mcp:amd64
- **Original Size**: 954MB
- **Optimized Size**: 652MB (32% reduction)
- **Platform**: linux/amd64
- **Base Image**: python:3.11-slim

## Deployment Commands

### Local Testing (Recommended)
Uses `.env.staging` file with dynamic overrides for local development:

```bash
docker run -d \
    --name mcp-staging-test \
    --env-file /Users/xenodennis/Documents/Fun/isA_MCP/deployment/staging/.env.staging \
    -e CONSUL_HOST=host.docker.internal \
    -e CONSUL_PORT=8500 \
    -e CONSUL_ENABLED=false \
    -e DATABASE_URL="postgresql://postgres:postgres@host.docker.internal:54322/postgres?options=-c%20search_path=dev" \
    -e SUPABASE_LOCAL_URL="http://host.docker.internal:54321" \
    -e SUPABASE_LOCAL_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0" \
    -e SUPABASE_LOCAL_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU" \
    -p 8081:8081 \
    staging-isa-mcp:amd64
```

### Legacy Local Testing (All environment variables)
```bash
docker run -d \
    --name mcp-staging-test \
    -e CONSUL_HOST=host.docker.internal \
    -e CONSUL_PORT=8500 \
    -e DATABASE_URL="postgresql://postgres:postgres@host.docker.internal:54322/postgres?options=-c%20search_path=dev" \
    -e SUPABASE_LOCAL_URL="http://host.docker.internal:54321" \
    -e SUPABASE_LOCAL_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0" \
    -e SUPABASE_LOCAL_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU" \
    -e COMPOSIO_API_KEY="p6btli2ifpa2l2wfdpo5uo" \
    -e COMPOSIO_CACHE_DIR="/app/cache" \
    -p 8081:8081 \
    staging-isa-mcp:amd64
```

### Production Deployment
Uses `.env.staging` file with production overrides:

```bash
docker run -d \
    --name mcp-staging-prod \
    --env-file /path/to/deployment/staging/.env.staging \
    -e CONSUL_HOST=consul.service.consul \
    -e CONSUL_PORT=8500 \
    -e CONSUL_ENABLED=true \
    -e DATABASE_URL="YOUR_PRODUCTION_DATABASE_URL" \
    -e SUPABASE_LOCAL_URL="YOUR_PRODUCTION_SUPABASE_URL" \
    -e SUPABASE_LOCAL_ANON_KEY="YOUR_PRODUCTION_ANON_KEY" \
    -e SUPABASE_LOCAL_SERVICE_ROLE_KEY="YOUR_PRODUCTION_SERVICE_ROLE_KEY" \
    -p 8081:8081 \
    staging-isa-mcp:amd64
```

## Testing & Verification

### 1. Health Check
```bash
curl -f http://localhost:8081/health
```

### 2. MCP Protocol Testing
```bash
# Initialize MCP connection
curl -s -X POST -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {"roots": {"listChanged": true}}, "clientInfo": {"name": "test-client", "version": "1.0"}}}' \
  http://localhost:8081/mcp

# Get available tools list
curl -s -X POST -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}' \
  http://localhost:8081/mcp

# Get available resources list  
curl -s -X POST -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "id": 3, "method": "resources/list", "params": {}}' \
  http://localhost:8081/mcp

# Test tool execution
curl -s -X POST -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "check_security_status", "arguments": {"user_id": "test-user"}}}' \
  http://localhost:8081/mcp
```

### 3. Container Logs
```bash
docker logs mcp-staging-test
```

### 4. Process Status
```bash
docker ps | grep mcp-staging
```

## Optimization Results

- **Original Size**: 954MB  
- **Optimized Size**: 652MB
- **Reduction**: 302MB (32% reduction)

### Optimization Techniques
- Removed OpenCV dependency (180MB)
- Removed unnecessary Python packages (122MB)  
- Cleaned pip cache and bytecode files
- Removed test directories and metadata

## Environment Variables

### Configuration Approach
The deployment uses a **hybrid approach**:
- **Static configuration**: Stored in `.env.staging` file
- **Dynamic overrides**: Passed as `-e` parameters for environment-specific values

### Static Variables (in .env.staging)
| Variable | Description | Value |
|----------|-------------|-------|
| `COMPOSIO_API_KEY` | Composio API key for 300+ app integrations | `p6btli2ifpa2l2wfdpo5uo` |
| `BRAVE_TOKEN` | Brave search API token | `BSANDoKsk...` |
| `MCP_API_KEY` | MCP authentication key | `mcp_vyL0yj...` |
| `COMPOSIO_CACHE_DIR` | Composio cache directory | `/app/cache` |
| `LAZY_LOAD_AI_SELECTORS` | Background AI selector loading | `true` |
| `LAZY_LOAD_EXTERNAL_SERVICES` | Background external service loading | `true` |
| `HARDWARE_AUTO_SCAN` | Hardware SDK auto-scan | `false` |

### Dynamic Override Variables
| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `CONSUL_HOST` | No | Consul server host | `host.docker.internal` |
| `CONSUL_PORT` | No | Consul server port | `8500` |
| `CONSUL_ENABLED` | No | Enable Consul discovery | `false` |
| `DATABASE_URL` | Yes | PostgreSQL database URL | `postgresql://...` |
| `SUPABASE_LOCAL_URL` | Yes | Supabase URL | `http://host.docker.internal:54321` |
| `SUPABASE_LOCAL_ANON_KEY` | Yes | Supabase anonymous key | `eyJhbGciOi...` |
| `SUPABASE_LOCAL_SERVICE_ROLE_KEY` | Yes | Supabase service role key | `eyJhbGciOi...` |

## Troubleshooting

### Common Issues

1. **Container startup failure**
   ```bash
   docker logs mcp-staging-test
   ```

2. **Database connection issues**
   - Check DATABASE_URL format
   - Verify database is accessible

3. **Consul connection issues**
   - Set CONSUL_ENABLED=false to disable Consul
   - Verify CONSUL_HOST connectivity

4. **Port conflicts**
   ```bash
   # Check port usage
   lsof -i :8081
   
   # Use different port
   docker run ... -p 8082:8081 ...
   ```

## Test Results

### MCP Service Status
- **42-94 Tools** available (42 base tools + 52 Composio tools when API key is valid)
- **46 Prompts** available (analysis, creation, execution, specialized categories)
- **9 Resources** available (symbolic, guardrail categories)
- **Search API** working correctly for tools/prompts/resources discovery
- **Health endpoint** responsive
- **All tools/services** from directories successfully registered

### Composio Integration Status ✅
- **Package**: Successfully installed (v1.0.0-rc2)
- **Environment**: Configured via `.env.staging` file
- **API Connection**: Connects to 815 available apps
- **Tool Registration**: 52 Composio tools registered when API key is valid
- **Priority Apps**: Gmail, GitHub, Notion, Slack, HubSpot, Linear, Airtable, Jira, Discord, Asana, Shopify, Salesforce, Trello, Stripe, Mailchimp, Dropbox, Zoom, Telegram
- **Cache Directory**: `/app/cache` for optimized performance
- **Background Loading**: Enabled for faster startup

## Deployment Approach Benefits

### Hybrid Configuration Model
- **Static Variables**: API keys, optimization settings, cache configuration stored in `.env.staging`
- **Dynamic Overrides**: Environment-specific values (Consul, database URLs) passed as `-e` parameters
- **Cleaner Commands**: Reduced command line complexity while maintaining flexibility
- **Version Control**: Static configuration can be tracked in git (with secret masking)
- **Environment Isolation**: Easy to override just the variables that change between environments

### Advantages
1. **Maintainability**: Central configuration file reduces duplication
2. **Flexibility**: Dynamic overrides for environment-specific deployments  
3. **Security**: Sensitive values can be externally managed while defaults are in config
4. **Consistency**: Same base configuration across all staging environments
5. **Simplicity**: Single env file + minimal overrides vs. long command lines

## Deployment Notes

- **Date**: 2025-10-11  
- **Version**: v1.0.1
- **Build Time**: 2025-10-11 03:29:00
- **Configuration**: Hybrid model with `.env.staging` + dynamic overrides
- **Composio Integration**: Full integration with v1.0.0-rc2