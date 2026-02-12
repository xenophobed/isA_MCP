 MCP Platform — Hybrid Multi-Tenancy                                                                                                                                             │
│                                                                                                                                                                                 │
│ Context                                                                                                                                                                         │
│                                                                                                                                                                                 │
│ The MCP platform currently operates as single-tenant: all tools, prompts, servers, and search results are global. Every user sees the same data. The user wants each            │
│ organization to have its own MCP instance — their own servers, custom tools, and scoped search — while still sharing a global catalog of built-in tools and skills.             │
│                                                                                                                                                                                 │
│ Hybrid model: Global shared catalog + per-org custom layer. Users see global tools plus their org's tools merged together.                                                      │
│                                                                                                                                                                                 │
│ What Already Exists                                                                                                                                                             │
│                                                                                                                                                                                 │
│ - mcp.installed_packages already has user_id, org_id, team_id columns                                                                                                           │
│ - mcp.resources already has owner_id, is_public, allowed_users                                                                                                                  │
│ - Auth middleware already sets request.state.organization_id from JWT                                                                                                           │
│ - Qdrant vector DB has multi-tenant filtering support (built, unused)                                                                                                           │
│ - Frontend useAgentResources already loads user's org list                                                                                                                      │
│ - Agent system already supports org_id scoping                                                                                                                                  │
│                                                                                                                                                                                 │
│ What's Missing                                                                                                                                                                  │
│                                                                                                                                                                                 │
│ - mcp.tools, mcp.prompts, mcp.external_servers have no org_id                                                                                                                   │
│ - Repositories have no tenant filtering in queries                                                                                                                              │
│ - Search service has no org-scoped filtering                                                                                                                                    │
│ - Frontend auth context has no current org concept                                                                                                                              │
│ - MCPAdminService sends no X-Organization-Id header                                                                                                                             │
│                                                                                                                                                                                 │
│ ---                                                                                                                                                                             │
│ Phase 1: Database Migrations                                                                                                                                                    │
│                                                                                                                                                                                 │
│ Add org_id UUID and is_global BOOLEAN to 3 tables. All existing data becomes global.                                                                                            │
│                                                                                                                                                                                 │
│ 1A. mcp.tools                                                                                                                                                                   │
│                                                                                                                                                                                 │
│ Create: services/tool_service/migrations/004_add_multi_tenant_fields.sql                                                                                                        │
│                                                                                                                                                                                 │
│ ALTER TABLE mcp.tools ADD COLUMN IF NOT EXISTS org_id UUID;                                                                                                                     │
│ ALTER TABLE mcp.tools ADD COLUMN IF NOT EXISTS is_global BOOLEAN DEFAULT TRUE;                                                                                                  │
│ UPDATE mcp.tools SET is_global = TRUE WHERE is_global IS NULL;                                                                                                                  │
│                                                                                                                                                                                 │
│ -- Replace global unique name constraint with scoped ones                                                                                                                       │
│ ALTER TABLE mcp.tools DROP CONSTRAINT IF EXISTS tools_name_key;                                                                                                                 │
│ CREATE UNIQUE INDEX IF NOT EXISTS idx_tools_name_global ON mcp.tools(name) WHERE is_global = TRUE;                                                                              │
│ CREATE UNIQUE INDEX IF NOT EXISTS idx_tools_name_org ON mcp.tools(name, org_id) WHERE org_id IS NOT NULL;                                                                       │
│                                                                                                                                                                                 │
│ CREATE INDEX IF NOT EXISTS idx_tools_tenant_filter ON mcp.tools(org_id, is_global);                                                                                             │
│                                                                                                                                                                                 │
│ 1B. mcp.prompts                                                                                                                                                                 │
│                                                                                                                                                                                 │
│ Create: services/prompt_service/migrations/002_add_multi_tenant_fields.sql                                                                                                      │
│                                                                                                                                                                                 │
│ Same pattern — add org_id, is_global, scoped unique index.                                                                                                                      │
│                                                                                                                                                                                 │
│ 1C. mcp.external_servers                                                                                                                                                        │
│                                                                                                                                                                                 │
│ Create: services/aggregator_service/migrations/002_add_multi_tenant_fields.sql                                                                                                  │
│                                                                                                                                                                                 │
│ Same pattern. Existing servers get is_global = TRUE.                                                                                                                            │
│                                                                                                                                                                                 │
│ 1D. mcp.resources                                                                                                                                                               │
│                                                                                                                                                                                 │
│ Create: services/resource_service/migrations/002_add_org_id.sql                                                                                                                 │
│                                                                                                                                                                                 │
│ Add org_id UUID (resources already have owner_id/is_public for access control).                                                                                                 │
│                                                                                                                                                                                 │
│ mcp.skill_categories stays global — taxonomy is shared across all orgs.                                                                                                         │
│                                                                                                                                                                                 │
│ ---                                                                                                                                                                             │
│ Phase 2: Backend — Org Context Extraction                                                                                                                                       │
│                                                                                                                                                                                 │
│ 2A. Auth middleware enhancement                                                                                                                                                 │
│                                                                                                                                                                                 │
│ File: /Users/xenodennis/Documents/Fun/isA/isA_MCP/core/auth/middleware.py (line 219-224)                                                                                        │
│                                                                                                                                                                                 │
│ The middleware already sets request.state.organization_id from JWT. Add X-Organization-Id header override for multi-org users:                                                  │
│                                                                                                                                                                                 │
│ # After auth succeeds (line ~223):                                                                                                                                              │
│ org_header = request.headers.get("X-Organization-Id", "").strip()                                                                                                               │
│ if org_header:                                                                                                                                                                  │
│     request.state.organization_id = org_header  # User's active org                                                                                                             │
│ # else: keep JWT org_id as-is                                                                                                                                                   │
│                                                                                                                                                                                 │
│ 2B. Org context helper                                                                                                                                                          │
│                                                                                                                                                                                 │
│ Create: /Users/xenodennis/Documents/Fun/isA/isA_MCP/core/auth/org_context.py                                                                                                    │
│                                                                                                                                                                                 │
│ def get_org_id(request) -> Optional[str]:                                                                                                                                       │
│     return getattr(request.state, 'organization_id', None)                                                                                                                      │
│                                                                                                                                                                                 │
│ ---                                                                                                                                                                             │
│ Phase 3: Backend — Repository Layer                                                                                                                                             │
│                                                                                                                                                                                 │
│ Core pattern for every repository: WHERE (is_global = TRUE OR org_id = $param)                                                                                                  │
│                                                                                                                                                                                 │
│ When org_id is None, only global items returned (backward compatible).                                                                                                          │
│                                                                                                                                                                                 │
│ 3A. ToolRepository                                                                                                                                                              │
│                                                                                                                                                                                 │
│ File: services/tool_service/tool_repository.py                                                                                                                                  │
│                                                                                                                                                                                 │
│ - list_tools() (line 94): Add org_id param, append (is_global = TRUE OR org_id = $N) to WHERE                                                                                   │
│ - create_tool() / create_external_tool(): Accept org_id, is_global                                                                                                              │
│ - list_external_tools(): Add org_id filter                                                                                                                                      │
│ - Cache keys: Include org_id → f"list:{org_id}:{category}:{is_active}:{limit}:{offset}"                                                                                         │
│                                                                                                                                                                                 │
│ 3B. PromptRepository                                                                                                                                                            │
│                                                                                                                                                                                 │
│ File: services/prompt_service/prompt_repository.py                                                                                                                              │
│                                                                                                                                                                                 │
│ Same pattern as ToolRepository.                                                                                                                                                 │
│                                                                                                                                                                                 │
│ 3C. ResourceRepository                                                                                                                                                          │
│                                                                                                                                                                                 │
│ File: services/resource_service/resource_repository.py                                                                                                                          │
│                                                                                                                                                                                 │
│ Combined logic: (is_public = TRUE OR org_id = $param OR owner_id = $user_param)                                                                                                 │
│                                                                                                                                                                                 │
│ 3D. ServerRegistry                                                                                                                                                              │
│                                                                                                                                                                                 │
│ File: services/aggregator_service/server_registry.py                                                                                                                            │
│                                                                                                                                                                                 │
│ - add(): Accept + store org_id                                                                                                                                                  │
│ - list(): Filter (is_global = TRUE OR org_id = $param)                                                                                                                          │
│ - _insert_server_db(): Include org_id in INSERT                                                                                                                                 │
│                                                                                                                                                                                 │
│ ---                                                                                                                                                                             │
│ Phase 4: Backend — API Endpoints                                                                                                                                                │
│                                                                                                                                                                                 │
│ File: /Users/xenodennis/Documents/Fun/isA/isA_MCP/main.py                                                                                                                       │
│                                                                                                                                                                                 │
│ Every list/create endpoint extracts org_id and passes to repository:                                                                                                            │
│                                                                                                                                                                                 │
│ from core.auth.org_context import get_org_id                                                                                                                                    │
│ org_id = get_org_id(request)                                                                                                                                                    │
│                                                                                                                                                                                 │
│ Endpoints to modify:                                                                                                                                                            │
│ - aggregator_list_servers_endpoint — pass org_id to filter                                                                                                                      │
│ - aggregator_register_server_endpoint — include org_id in server config                                                                                                         │
│ - api_search_endpoint — pass org_id to search service                                                                                                                           │
│ - Tool/prompt/resource list endpoints — pass org_id to repositories                                                                                                             │
│ - Server connect/disconnect — validate server belongs to user's org                                                                                                             │
│                                                                                                                                                                                 │
│ ---                                                                                                                                                                             │
│ Phase 5: Backend — Search Service (Qdrant)                                                                                                                                      │
│                                                                                                                                                                                 │
│ 5A. Enrich Qdrant payloads                                                                                                                                                      │
│                                                                                                                                                                                 │
│ File: services/vector_service/vector_repository.py                                                                                                                              │
│                                                                                                                                                                                 │
│ Add org_id and is_global to vector payloads. Create field indexes.                                                                                                              │
│                                                                                                                                                                                 │
│ 5B. HierarchicalSearchService                                                                                                                                                   │
│                                                                                                                                                                                 │
│ File: services/search_service/hierarchical_search_service.py                                                                                                                    │
│                                                                                                                                                                                 │
│ Add org_id filter to search() and _search_tools():                                                                                                                              │
│                                                                                                                                                                                 │
│ # Qdrant filter for hybrid tenancy                                                                                                                                              │
│ filter = {                                                                                                                                                                      │
│     "should": [                                                                                                                                                                 │
│         {"field": "is_global", "match": {"boolean": True}},                                                                                                                     │
│         {"field": "org_id", "match": {"keyword": org_id}}                                                                                                                       │
│     ]                                                                                                                                                                           │
│ }                                                                                                                                                                               │
│                                                                                                                                                                                 │
│ 5C. SyncService                                                                                                                                                                 │
│                                                                                                                                                                                 │
│ File: services/sync_service/sync_service.py                                                                                                                                     │
│                                                                                                                                                                                 │
│ Include org_id, is_global in metadata when syncing to Qdrant. After deployment, run full re-sync to populate existing vectors.                                                  │
│                                                                                                                                                                                 │
│ ---                                                                                                                                                                             │
│ Phase 6: Backend — Aggregator Org Threading                                                                                                                                     │
│                                                                                                                                                                                 │
│ When an org-scoped server is connected and tools discovered, org_id propagates to created tools.                                                                                │
│                                                                                                                                                                                 │
│ File: services/aggregator_service/tool_aggregator.py                                                                                                                            │
│                                                                                                                                                                                 │
│ In discover_tools(): look up server's org_id, set tool_data['org_id'] and is_global=False for all discovered tools.                                                             │
│                                                                                                                                                                                 │
│ ---                                                                                                                                                                             │
│ Phase 7: Frontend — Auth Context + Org Header                                                                                                                                   │
│                                                                                                                                                                                 │
│ 7A. Extend AuthContext                                                                                                                                                          │
│                                                                                                                                                                                 │
│ File: /Users/xenodennis/Documents/Fun/isA/isA_Console/src/lib/auth-context.tsx                                                                                                  │
│                                                                                                                                                                                 │
│ Add currentOrgId + setCurrentOrgId to context. Persist in localStorage:                                                                                                         │
│                                                                                                                                                                                 │
│ interface AuthContextType {                                                                                                                                                     │
│   // ...existing...                                                                                                                                                             │
│   currentOrgId: string | null;                                                                                                                                                  │
│   setCurrentOrgId: (id: string) => void;                                                                                                                                        │
│ }                                                                                                                                                                               │
│                                                                                                                                                                                 │
│ 7B. MCPAdminService — Send org header                                                                                                                                           │
│                                                                                                                                                                                 │
│ File: /Users/xenodennis/Documents/Fun/isA/isA_Console/src/lib/mcp-admin-service.ts                                                                                              │
│                                                                                                                                                                                 │
│ In getAuthHeaders(): add X-Organization-Id from localStorage.                                                                                                                   │
│                                                                                                                                                                                 │
│ 7C. Org selector in sidebar/header                                                                                                                                              │
│                                                                                                                                                                                 │
│ File: /Users/xenodennis/Documents/Fun/isA/isA_Console/src/components/layout/Sidebar.tsx                                                                                         │
│                                                                                                                                                                                 │
│ Reuse the org-loading pattern from useAgentResources.ts. Show dropdown when user has multiple orgs. On change, update currentOrgId.                                             │
│                                                                                                                                                                                 │
│ ---                                                                                                                                                                             │
│ Backward Compatibility                                                                                                                                                          │
│                                                                                                                                                                                 │
│ - Existing tools/prompts/servers get is_global=TRUE via migration — visible to everyone                                                                                         │
│ - Null org_id in requests → only global items returned (same as today)                                                                                                          │
│ - All new columns are nullable with defaults — existing INSERTs keep working                                                                                                    │
│ - SmartMCPServer stays singleton — filtering is at query layer only                                                                                                             │
│ - Cache keys include org_id — no cross-tenant cache leakage                                                                                                                     │
│                                                                                                                                                                                 │
│ ---                                                                                                                                                                             │
│ Verification                                                                                                                                                                    │
│                                                                                                                                                                                 │
│ 1. Run migrations, verify all existing data has is_global=TRUE                                                                                                                  │
│ 2. Restart MCP service, confirm all existing endpoints return same data as before                                                                                               │
│ 3. Register an org-scoped server (with X-Organization-Id header), verify its tools are invisible to other orgs                                                                  │
│ 4. Search with org context — verify global + org tools appear, other orgs' tools don't                                                                                          │
│ 5. Frontend: switch orgs in selector, verify MCP pages show different data                                                                                                      │
│ 6. Run full Qdrant re-sync, verify search results respect org filtering