# Organization Management API Guide

This documentation provides a comprehensive guide for using the Organization Management API based on real testing results.

## Prerequisites

### 1. Service Startup
```bash
python -m tools.services.user_service.api_server
```
Service runs on `http://localhost:8100`

### 2. Authentication Token
```bash
# Get development token
curl -X POST "http://localhost:8100/auth/dev-token?user_id=test-user-123&email=test@example.com"
```

**Response Example:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user_id": "test-user-123",
  "email": "test@example.com",
  "expires_in": 3600,
  "provider": "supabase",
  "timestamp": "2025-08-05T05:15:00.392914"
}
```

**Important:** user_id must follow one of these formats:
- Auth0: `auth0|{uuid}` or `{provider}|{identifier}`
- UUID: Standard 36-character UUID
- Test: `test-user-{number}` (e.g., `test-user-123`)
- Dev: `dev-user` or `dev_user`

## Organization Management

### 1. Create Organization

**Request:**
```bash
curl -X POST "http://localhost:8100/api/v1/organizations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Test Organization",
    "domain": "testorg.com",
    "plan": "startup",
    "billing_email": "billing@testorg.com",
    "settings": {"theme": "dark"}
  }'
```

**Response:**
```json
{
  "success": true,
  "status": "success",
  "message": "Organization created successfully",
  "timestamp": "2025-08-05T07:37:30.421604",
  "data": {
    "organization_id": "org_0905f0cc8256",
    "name": "Test Organization",
    "domain": "testorg.com",
    "plan": "startup",
    "billing_email": "billing@testorg.com",
    "status": "active",
    "credits_pool": 0.0,
    "created_at": "2025-08-05T07:37:30.408733+00:00"
  }
}
```

**Note:** The requesting user automatically becomes the organization owner.

### 2. Get Organization

**Request:**
```bash
curl -X GET "http://localhost:8100/api/v1/organizations/{organization_id}" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "success": true,
  "status": "success",
  "message": "Organization retrieved successfully",
  "timestamp": "2025-08-05T07:42:55.525064",
  "data": {
    "organization_id": "org_0905f0cc8256",
    "name": "Test Organization",
    "domain": "testorg.com",
    "plan": "startup",
    "billing_email": "billing@testorg.com",
    "status": "active",
    "settings": {
      "theme": "dark"
    },
    "credits_pool": 0.0,
    "created_at": "2025-08-05T07:37:30.408733+00:00",
    "updated_at": "2025-08-05T07:37:30.408733+00:00"
  }
}
```

### 3. Update Organization

**Request:**
```bash
curl -X PUT "http://localhost:8100/api/v1/organizations/{organization_id}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Updated Test Organization",
    "settings": {"theme": "light", "notifications": true}
  }'
```

### 4. Delete Organization

**Request:**
```bash
curl -X DELETE "http://localhost:8100/api/v1/organizations/{organization_id}" \
  -H "Authorization: Bearer $TOKEN"
```

**Warning:** Deletes all related member records, usage records, and credit transactions.

## Member Management

### 1. Add Member

**Request:**
```bash
curl -X POST "http://localhost:8100/api/v1/organizations/{organization_id}/members" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "user_id": "test-user-456",
    "role": "member",
    "permissions": ["read", "write"]
  }'
```

**Available Roles:** `owner`, `admin`, `member`

### 2. Get Members

**Request:**
```bash
curl -X GET "http://localhost:8100/api/v1/organizations/{organization_id}/members" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Update Member

**Request:**
```bash
curl -X PUT "http://localhost:8100/api/v1/organizations/{organization_id}/members/{user_id}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "role": "admin",
    "permissions": ["read", "write", "admin"]
  }'
```

### 4. Remove Member

**Request:**
```bash
curl -X DELETE "http://localhost:8100/api/v1/organizations/{organization_id}/members/{user_id}" \
  -H "Authorization: Bearer $TOKEN"
```

## User Organization Query

**Request:**
```bash
curl -X GET "http://localhost:8100/api/v1/users/{user_id}/organizations" \
  -H "Authorization: Bearer $TOKEN"
```

## Organization Statistics

**Request:**
```bash
curl -X GET "http://localhost:8100/api/v1/organizations/{organization_id}/stats" \
  -H "Authorization: Bearer $TOKEN"
```

## Context Switching

### Switch to Organization Context
```bash
curl -X POST "http://localhost:8100/api/v1/users/{user_id}/switch-context" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"organization_id": "org_0905f0cc8256"}'
```

### Switch to Personal Context
```bash
curl -X POST "http://localhost:8100/api/v1/users/{user_id}/switch-context" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{}'
```

## Error Handling

### Common Errors

1. **Invalid User ID Format:**
```json
{
  "detail": "Failed to add owner to organization: Failed to add organization member: 1 validation error for OrganizationMember\nuser_id\n  Value error, Invalid user_id format: Unsupported user ID format: invalid_user_123"
}
```

2. **Organization Not Found:**
```json
{
  "detail": "Access denied: You are not a member of this organization"
}
```

3. **Unauthenticated Access:**
```json
{
  "detail": "Not authenticated"
}
```

4. **Insufficient Permissions:**
```json
{
  "detail": "Access denied: You can only view your own organizations"
}
```

## Current Issues and Limitations

### Known Issues

1. **JSON Parsing in User Organizations**
   - `settings` and `api_keys` fields return JSON strings instead of parsed objects
   - **Impact:** Frontend needs to manually parse these JSON strings
   - **Fix:** Add JSON parsing in `get_user_organizations` method

2. **Hardcoded Database Configuration**
   - Database connection parameters are hardcoded
   - **Impact:** Cannot dynamically configure different environments
   - **Fix:** Read database config from environment variables

3. **Incomplete Permission System**
   - Permissions field exists but no actual permission checking logic
   - **Impact:** Cannot truly restrict user operations
   - **Fix:** Implement permission decorators and checking logic

4. **Inconsistent Error Handling**
   - Some APIs return HTTP 400 instead of more specific error codes (e.g., 404)
   - **Impact:** Frontend difficult to handle different error types
   - **Fix:** Unified error handling and status codes

### Missing Features

1. **Organization Invitation System**
   - Currently only supports adding members with known user_ids
   - **Missing:** Email invitation functionality for new members

2. **Batch Operations**
   - No bulk add/remove members
   - No bulk permission updates

3. **Audit Logs**
   - No audit trail for organization operations
   - Cannot track who performed what operations

4. **Usage Quotas and Limits**
   - credits_pool field exists but no actual usage limiting logic
   - No plan-based feature restrictions

5. **Organization Hierarchy and Departments**
   - No support for sub-organizations or departments
   - Cannot implement complex organizational structures

### Working Features

- ✅ Organization CRUD operations
- ✅ Member management (add, remove, update)
- ✅ Basic permission roles (owner, admin, member)
- ✅ Organization statistics
- ✅ User-organization association queries
- ✅ JSON field handling (settings, permissions)
- ✅ Database transactions and cascading deletes
- ✅ Basic authentication and authorization
- ✅ Error handling and validation

## Database Structure

### Related Tables
1. **organizations** - Basic organization information
2. **organization_members** - Organization member relationships
3. **organization_usage** - Organization usage records
4. **organization_credit_transactions** - Organization credit transactions

### Index Optimization
All tables have appropriate indexes for query performance:
- Organization ID indexes
- User ID indexes
- Status indexes
- Time indexes

## Best Practices

1. **Always use correct user ID format**
2. **Properly handle JSON field serialization/deserialization**
3. **Check API response success field**
4. **Provide appropriate error handling for all requests**
5. **Confirm data importance before deletion operations**