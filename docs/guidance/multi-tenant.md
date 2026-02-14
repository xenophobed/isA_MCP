# Multi-Tenant Architecture

Complete guide to multi-tenant isolation in ISA MCP platform.

## Overview

The platform supports multi-tenant isolation with:
- **Organization scoping** - Data segregation by org_id
- **Global resources** - Shared across all organizations
- **Tenant switching** - Users can access multiple organizations
- **Performance optimization** - Composite indexes for efficient filtering

## Data Model

### Tenant Fields

All primary entities include tenant fields:

```sql
CREATE TABLE mcp.tools (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    org_id UUID,                    -- Organization owner (NULL for global)
    is_global BOOLEAN DEFAULT TRUE,  -- Visible to all orgs
    -- ... other fields
);
```

**Field Semantics:**
- `org_id = NULL` and `is_global = TRUE`: System-wide resource
- `org_id = <uuid>` and `is_global = FALSE`: Private to organization
- `org_id = <uuid>` and `is_global = TRUE`: Owned by org but shared globally

### Affected Services

Multi-tenant isolation implemented in:

| Service | Tables | Migration |
|---------|--------|-----------|
| **tool_service** | `tools` | `004_add_multi_tenant_fields.sql` |
| **prompt_service** | `prompts` | `004_add_multi_tenant_fields.sql` |
| **resource_service** | `resources` | `004_add_org_id.sql` |
| **skill_service** | `skill_categories`, `tool_skill_assignments` | `004_add_multi_tenant_fields.sql` |
| **marketplace_service** | `marketplace_packages`, `package_versions` | `002_add_multi_tenant_fields.sql` |
| **aggregator_service** | `mcp_servers` | `002_add_multi_tenant_fields.sql` |

## Query Patterns

### Tenant-Aware Queries

```python
# Repository method signature
async def list_skills(
    self,
    org_id: Optional[str] = None,  # Filter by tenant
    is_active: Optional[bool] = True,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """List skills with tenant filtering."""

    conditions = ["is_active = $1"]
    params = [is_active]
    param_idx = 2

    # Tenant filter: show global OR org-specific
    if org_id is not None:
        conditions.append(f"(is_global = TRUE OR org_id = ${param_idx})")
        params.append(org_id)
        param_idx += 1

    query = f"""
        SELECT * FROM mcp.skill_categories
        WHERE {' AND '.join(conditions)}
        ORDER BY name
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    params.extend([limit, offset])

    return await self.db.query(query, params=params)
```

### Performance Indexes

Composite indexes optimize tenant queries:

```sql
-- Efficient for: WHERE (is_global = TRUE OR org_id = $1)
CREATE INDEX idx_tools_tenant_filter
ON mcp.tools(org_id, is_global);

-- Query plan will use this index
EXPLAIN SELECT * FROM mcp.tools
WHERE (is_global = TRUE OR org_id = '123e4567-e89b-12d3-a456-426614174000');
```

## Unique Constraints

### Global vs Per-Org Uniqueness

```sql
-- Tools must have unique names within their scope
-- Global scope: name unique across all global tools
CREATE UNIQUE INDEX idx_tools_name_global
ON mcp.tools(name)
WHERE is_global = TRUE;

-- Per-org scope: name unique within each organization
CREATE UNIQUE INDEX idx_tools_name_org
ON mcp.tools(name, org_id)
WHERE is_global = FALSE;
```

**Example Data:**
```sql
-- Valid: Different scopes
INSERT INTO mcp.tools (name, org_id, is_global) VALUES
    ('weather', NULL, TRUE),           -- Global tool
    ('weather', 'org-A', FALSE),       -- Org A's private tool
    ('weather', 'org-B', FALSE);       -- Org B's private tool

-- Invalid: Duplicate in same scope
INSERT INTO mcp.tools (name, org_id, is_global) VALUES
    ('weather', NULL, TRUE);           -- Error: global 'weather' exists

INSERT INTO mcp.tools (name, org_id, is_global) VALUES
    ('weather', 'org-A', FALSE);       -- Error: org-A 'weather' exists
```

## Tenant Switching

### User Context

```python
@dataclass
class UserContext:
    user_id: str
    organization_id: str              # Current organization
    authorized_orgs: List[str]        # Organizations user can access
    # ... other fields
```

### Switch Organization

```python
# Client request
headers = {
    "Authorization": "Bearer <jwt>",
    "X-Organization-Id": "org-B"  # Switch to org-B
}

# Middleware validation (core/auth/middleware.py)
org_header = request.headers.get("X-Organization-Id", "").strip()
if org_header:
    user_orgs = getattr(user_context, "authorized_orgs", [])
    if org_header in user_orgs:
        request.state.organization_id = org_header
        logger.info(f"User {user_context.user_id} switched to org: {org_header}")
    else:
        logger.warning(
            f"User {user_context.user_id} attempted org switch to "
            f"unauthorized org: {org_header}"
        )
        # Request continues with original org_id
```

### Security Validation

**Authorization Flow:**
1. JWT decoded to extract `authorized_orgs`
2. `X-Organization-Id` header validated against list
3. Unauthorized switches logged as security events
4. User retains access only to switched org's data

**Fallback Behavior:**
- If auth service doesn't provide `authorized_orgs`, uses `organization_id` from JWT
- Empty `authorized_orgs` prevents all org switches (user locked to JWT org)

## Migration Guide

### Adding Multi-Tenant Fields

```sql
-- migration: 004_add_multi_tenant_fields.sql
BEGIN;

-- Add columns with safe defaults
ALTER TABLE mcp.tools
ADD COLUMN IF NOT EXISTS org_id UUID,
ADD COLUMN IF NOT EXISTS is_global BOOLEAN DEFAULT TRUE;

-- Backfill existing data as global
UPDATE mcp.tools
SET is_global = TRUE
WHERE is_global IS NULL;

-- Drop old global unique constraint
ALTER TABLE mcp.tools
DROP CONSTRAINT IF EXISTS tools_name_key;

-- Add scoped unique indexes
CREATE UNIQUE INDEX IF NOT EXISTS idx_tools_name_global
ON mcp.tools(name)
WHERE is_global = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS idx_tools_name_org
ON mcp.tools(name, org_id)
WHERE is_global = FALSE;

-- Add tenant filter index
CREATE INDEX IF NOT EXISTS idx_tools_tenant_filter
ON mcp.tools(org_id, is_global);

COMMIT;

-- Rollback (if needed)
-- BEGIN;
-- DROP INDEX IF EXISTS idx_tools_tenant_filter;
-- DROP INDEX IF EXISTS idx_tools_name_org;
-- DROP INDEX IF EXISTS idx_tools_name_global;
-- ALTER TABLE mcp.tools DROP COLUMN IF EXISTS org_id;
-- ALTER TABLE mcp.tools DROP COLUMN IF EXISTS is_global;
-- COMMIT;
```

### Repository Updates

```python
# Before multi-tenant
async def get_tool_by_name(self, name: str) -> Optional[Dict]:
    query = "SELECT * FROM mcp.tools WHERE name = $1"
    return await self.db.query_row(query, params=[name])

# After multi-tenant
async def get_tool_by_name(
    self,
    name: str,
    org_id: Optional[str] = None
) -> Optional[Dict]:
    """Get tool by name with tenant filtering."""
    if org_id is not None:
        query = """
            SELECT * FROM mcp.tools
            WHERE name = $1
            AND (is_global = TRUE OR org_id = $2)
        """
        return await self.db.query_row(query, params=[name, org_id])
    else:
        # Backward compatibility: no filtering
        query = "SELECT * FROM mcp.tools WHERE name = $1"
        return await self.db.query_row(query, params=[name])
```

## Use Cases

### 1. SaaS Platform

**Scenario:** Multiple customers using same MCP instance

```python
# Customer A creates private tool
await tool_service.create_tool(
    name="customer_analysis",
    org_id="customer-a",
    is_global=False,  # Private to Customer A
    description="Custom analysis tool"
)

# Customer B cannot see Customer A's tool
tools = await tool_service.list_tools(org_id="customer-b")
# Returns only global tools + Customer B's private tools
```

### 2. Enterprise Departments

**Scenario:** Different departments with shared + private resources

```python
# Finance department creates private prompt
await prompt_service.create_prompt(
    name="financial_analysis",
    org_id="dept-finance",
    is_global=False,
    template="Analyze financial data: {data}"
)

# Engineering department shares tool globally
await tool_service.create_tool(
    name="code_review",
    org_id="dept-engineering",
    is_global=True,  # All departments can use
    description="Automated code review"
)
```

### 3. Marketplace Packages

**Scenario:** Organization-specific package installations

```python
# Org A installs package
await marketplace.install_package(
    package_name="mcp-server-weather",
    org_id="org-a",
    is_global=False  # Private installation
)

# Org B installs same package independently
await marketplace.install_package(
    package_name="mcp-server-weather",
    org_id="org-b",
    is_global=False
)

# Both orgs have separate configurations
```

## Testing Multi-Tenancy

### Component Tests

```python
@pytest.mark.asyncio
async def test_tenant_isolation(skill_repository, mock_db):
    """Verify org A cannot see org B's skills."""

    # Create skills for different orgs
    await skill_repository.create_skill_category({
        "id": "skill-a",
        "name": "Private Skill A",
        "org_id": "org-a",
        "is_global": False
    })

    await skill_repository.create_skill_category({
        "id": "skill-b",
        "name": "Private Skill B",
        "org_id": "org-b",
        "is_global": False
    })

    # Query as org A
    skills_a = await skill_repository.list_skills(org_id="org-a")
    assert "skill-a" in [s["id"] for s in skills_a]
    assert "skill-b" not in [s["id"] for s in skills_a]

    # Query as org B
    skills_b = await skill_repository.list_skills(org_id="org-b")
    assert "skill-b" in [s["id"] for s in skills_b]
    assert "skill-a" not in [s["id"] for s in skills_b]
```

### Integration Tests

```python
@pytest.mark.integration
async def test_org_switching(mcp_client):
    """Verify organization switching via headers."""

    # Create tool as org-A
    response = await mcp_client.post(
        "/tools",
        json={"name": "test_tool", "is_global": False},
        headers={
            "Authorization": "Bearer <jwt>",
            "X-Organization-Id": "org-a"
        }
    )
    assert response.status_code == 201

    # Switch to org-B, tool not visible
    response = await mcp_client.get(
        "/tools/test_tool",
        headers={
            "Authorization": "Bearer <jwt>",
            "X-Organization-Id": "org-b"
        }
    )
    assert response.status_code == 404

    # Switch back to org-A, tool visible
    response = await mcp_client.get(
        "/tools/test_tool",
        headers={
            "Authorization": "Bearer <jwt>",
            "X-Organization-Id": "org-a"
        }
    )
    assert response.status_code == 200
```

## Performance Considerations

### Index Usage

```sql
-- Good: Uses idx_tools_tenant_filter
EXPLAIN SELECT * FROM mcp.tools
WHERE (is_global = TRUE OR org_id = 'org-a');

-- Query plan:
-- Index Scan using idx_tools_tenant_filter
--   Index Cond: ((org_id = 'org-a') OR (is_global = true))
```

### Query Optimization

```python
# Efficient: Single query with tenant filter
tools = await db.query("""
    SELECT * FROM mcp.tools
    WHERE (is_global = TRUE OR org_id = $1)
    AND category = $2
""", params=[org_id, category])

# Inefficient: Separate queries + merge
global_tools = await db.query("SELECT * FROM mcp.tools WHERE is_global = TRUE")
org_tools = await db.query("SELECT * FROM mcp.tools WHERE org_id = $1", [org_id])
tools = global_tools + org_tools  # Avoid this pattern
```

## Best Practices

1. **Always filter by org_id** - Never return unfiltered results
2. **Use composite indexes** - (org_id, is_global) for performance
3. **Validate org switches** - Check authorized_orgs before allowing
4. **Log security events** - Track unauthorized access attempts
5. **Test isolation** - Verify tenant boundaries in tests
6. **Migrate safely** - Use transactions and backups

## Next Steps

- [Security](./security) - Authentication and authorization
- [Configuration](./configuration) - Multi-tenant setup
- [Skills](./skills) - Skill-based organization
