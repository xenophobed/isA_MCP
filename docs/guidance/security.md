# Security

Security features and best practices for ISA MCP platform.

## Overview

The platform implements multiple layers of security:
- **Authentication** - JWT and API key support
- **Authorization** - Role-based access control with tool-level security
- **Tenant Isolation** - Multi-tenant data segregation
- **Input Validation** - SSRF, path traversal, and injection protection
- **Audit Logging** - Comprehensive security event tracking

## Authentication

### JWT Authentication

```python
headers = {
    "Authorization": "Bearer <jwt_token>",
    "Content-Type": "application/json"
}
```

The JWT payload must include:
- `user_id` - Unique user identifier
- `email` - User email address
- `organization_id` - Primary organization
- `authorized_orgs` - List of organizations user can access
- `subscription_tier` - free, pro, or enterprise

### API Key Authentication

```python
headers = {
    "X-API-Key": "<api_key>",
    "Content-Type": "application/json"
}
```

**Security Notes:**
- API keys should only be sent in headers (query params disabled for security)
- Keys are hashed before storage
- Keys can be scoped to specific tools/prompts/resources

### Organization Switching

Users with access to multiple organizations can switch context:

```python
headers = {
    "Authorization": "Bearer <jwt_token>",
    "X-Organization-Id": "<org_id>",  # Must be in authorized_orgs list
}
```

**Security Validation:**
- The `X-Organization-Id` header is validated against `user_context.authorized_orgs`
- Unauthorized org switch attempts are logged as security events
- User retains access only to data scoped to the selected organization

## Tool Security Levels

Tools are classified by security risk:

| Level | Description | Authorization Required |
|-------|-------------|----------------------|
| `LOW` | Read-only, no external access | No |
| `MEDIUM` | Limited writes, trusted sources | No |
| `HIGH` | Shell execution, file writes, external requests | **Yes** |

### HIGH Security Tools

These tools require explicit user authorization:

- **bash_tools** - Shell command execution
  - Executes commands with full shell interpretation (pipes, redirects, variables)
  - Protected by dangerous command pattern blocking (regex-based)
  - Each execution requires user approval via authorization service

- **file_tools** - File system operations
  - Write/delete operations on local filesystem
  - Protected against path traversal via symlink resolution
  - Sensitive paths (`/etc`, `/usr`, `/bin`, `/sbin`, `/var`, `/root`) blocked

- **web_tools** - External HTTP requests
  - Protected against SSRF attacks via URL allowlisting
  - DNS rebinding protection (though limitation exists, see Security Considerations)
  - Automatic redirect following disabled

### Authorization Flow

```python
# 1. Tool call received
result = await client.call_tool("bash_execute", {
    "command": "ls -la /tmp"
})

# 2. Security check (if HIGH level tool)
#    - Authorization request created with request_id
#    - Error returned to user with request_id
{
    "error": {
        "code": "AUTHORIZATION_REQUIRED",
        "message": "Authorization required for bash_execute",
        "request_id": "auth_123456"
    }
}

# 3. User approves via authorization service
await authz_service.approve_request("auth_123456")

# 4. Retry tool call with same parameters
#    - Authorization check passes
#    - Tool executes
```

## Multi-Tenant Isolation

### Organization Scoping

All data models include tenant fields:

```sql
-- Tools, Prompts, Resources
org_id UUID,
is_global BOOLEAN DEFAULT TRUE
```

**Data Access Rules:**
- `is_global = TRUE`: Visible to all organizations
- `is_global = FALSE`: Visible only to owning org_id
- Query filter: `WHERE (is_global = TRUE OR org_id = $1)`

### Unique Constraints

Names must be unique within scope:

```sql
-- Global scope
CREATE UNIQUE INDEX idx_tools_name_global
ON mcp.tools(name)
WHERE is_global = TRUE;

-- Per-org scope
CREATE UNIQUE INDEX idx_tools_name_org
ON mcp.tools(name, org_id)
WHERE is_global = FALSE;
```

This allows:
- Global tool "weather" (is_global=TRUE)
- Org A tool "weather" (is_global=FALSE, org_id=A)
- Org B tool "weather" (is_global=FALSE, org_id=B)

### Performance Indexes

Tenant filtering uses composite indexes:

```sql
CREATE INDEX idx_tools_tenant_filter
ON mcp.tools(org_id, is_global);
```

This optimizes queries like:
```sql
SELECT * FROM mcp.tools
WHERE (is_global = TRUE OR org_id = $1);
```

## Input Validation

### SSRF Protection (Registry Fetcher)

The marketplace registry fetcher protects against SSRF:

```python
# Allowlisted domains only
_ALLOWED_REGISTRY_HOSTS = {
    "registry.npmjs.org",
    "www.npmjs.com",
    "api.github.com",
    "github.com",
}

# Blocked ranges
- Private IPs (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
- Loopback (127.0.0.0/8)
- Link-local (169.254.0.0/16) - includes cloud metadata endpoints
- IPv6 private/link-local ranges

# Additional protections
- Scheme validation (http/https only)
- Automatic redirect following disabled
- Cloud metadata hostname blocking (metadata.google.internal, etc.)
```

**Limitations:**
- DNS rebinding attacks still possible (allowlisted domain could resolve to internal IP)
- For production, consider DNS validation at request time or use proxy with DNS pinning

### Path Traversal Protection (File Tools)

```python
# Symlink resolution
resolved = path.resolve()

# Prefix matching with boundary check
for sensitive in ["/etc", "/usr", "/bin", "/sbin", "/var", "/root"]:
    if str(resolved) == sensitive or str(resolved).startswith(sensitive + "/"):
        raise ValueError(f"Access denied: {sensitive}")
```

**Edge Cases:**
- Hard links (require existing file on same filesystem, minimal risk)
- TOCTOU race conditions (file could be replaced between check and operation)

### Shell Injection (Bash Tools)

**Design Decision:** Bash tools intentionally execute commands through shell (`/bin/sh -c`) to support shell features (pipes, redirects, variables). Security relies on:

1. **Pattern-based blocking** - Regex detection of dangerous commands:
   - `rm -rf /` variants
   - Filesystem operations on `/dev/sda`
   - `mkfs` commands
   - Fork bombs
   - Destructive `dd` operations
   - World-writable root (`chmod 777 /`)

2. **Authorization requirement** - HIGH security level requires user approval

3. **Audit logging** - All commands logged for review

**Pattern Bypass Potential:**
- Encoding/obfuscation (IFS variables, base64, shell expansions)
- For untrusted input, consider sandboxing or disabling bash_tools entirely

## Data Safety

### Migration Safety

All schema migrations include:

```sql
-- Transactional execution
BEGIN;

-- Backup before destructive operations
CREATE TABLE IF NOT EXISTS mcp.backup_table_name AS
SELECT * FROM mcp.original_table;

-- Migration changes
ALTER TABLE ...;

COMMIT;

-- Rollback instructions (commented)
-- DROP TABLE IF EXISTS mcp.new_table;
-- ALTER TABLE mcp.table DROP COLUMN new_column;
```

### Atomic Operations

Delete operations use CTE-based atomic counting:

```python
delete_sql = """
    WITH deleted AS (
        DELETE FROM mcp.tools
        WHERE source_server_id = $1
        RETURNING 1
    )
    SELECT COUNT(*) as count FROM deleted
"""
```

This eliminates race conditions between COUNT and DELETE.

## Security Considerations

### DNS Rebinding (Partial Mitigation)

**Issue:** Allowlisted domains (npmjs.org, github.com) could theoretically resolve to internal IPs if attacker controls DNS.

**Current Mitigation:**
- URL validation before request
- Redirect following disabled
- Short DNS cache TTL

**Recommended Production Hardening:**
- Validate resolved IP after DNS lookup
- Use HTTP proxy with DNS pinning
- Implement request-time IP validation

### Subprocess Execution

**bash_tools** uses `/bin/sh -c` which allows full shell interpretation. This is intentional for functionality but creates risk:

**Mitigations:**
- Dangerous command pattern blocking
- User authorization required
- Audit logging

**Recommendations:**
- Disable bash_tools for untrusted users
- Use allow-list of safe commands only
- Consider sandboxing (Docker, chroot, seccomp)

### Session Security

**UserContext Fields:**
```python
@dataclass
class UserContext:
    user_id: str
    email: Optional[str]
    organization_id: Optional[str]
    authorized_orgs: List[str]  # Organizations user can switch to
    subscription_tier: SubscriptionTier
    is_authenticated: bool
    permissions: Dict[str, AccessLevel]
    metadata: Dict[str, Any]
```

**Security Best Practices:**
- Never log `authorized_orgs` or `permissions` in plain text
- Validate org switches against `authorized_orgs`
- Refresh JWT tokens regularly (recommended: 1 hour expiry)

## Audit Logging

Security events logged:

```python
# Failed authorization attempts
logger.warning(f"User {user_id} attempted org switch to unauthorized org: {org_id}")

# Tool execution (HIGH security)
logger.info(f"bash_execute: Started shell command: {command[:50]}...")

# Authentication failures
logger.warning(f"Token verification failed: {error}")
```

## Best Practices

1. **Principle of Least Privilege**
   - Grant minimum required `authorized_orgs`
   - Use read-only tokens when possible
   - Scope API keys to specific tools

2. **Defense in Depth**
   - Combine allowlisting, pattern blocking, and authorization
   - Log suspicious activity
   - Regular security audits of HIGH security tool usage

3. **Secure Defaults**
   - API keys in headers only (no query params)
   - Automatic redirect following disabled
   - Sensitive path blocking enabled

4. **Monitoring**
   - Track org switch attempts (authorized and denied)
   - Monitor HIGH security tool usage
   - Alert on pattern blocking triggers

## Next Steps

- [Configuration](./configuration) - Environment setup
- [Multi-Tenant Guide](./multi-tenant) - Tenant isolation details
- [Tools](./tools) - Tool security annotations
