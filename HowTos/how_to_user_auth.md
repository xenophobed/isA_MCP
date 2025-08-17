# User Resource Authorization Management API Guide

## 🎯 Overview

The User Resource Authorization Management system provides fine-grained access control for MCP tools, prompts, and resources. It supports multiple permission sources including personal subscriptions, organization plans, and admin grants.

**🌐 Basic Information**
- **Service URL**: `http://localhost:8100`
- **API Docs**: `http://localhost:8100/docs`
- **Authentication**: Bearer Token (Auth0 JWT or Supabase JWT)
- **Data Format**: JSON

## 🔧 Permission System

### Permission Hierarchy (Priority from high to low)
1. **Admin Special Grants** - Highest priority, can override other restrictions
2. **Organization Permissions** - Based on organization plan and user role
3. **Personal Subscription Permissions** - Based on user subscription level

### Subscription Levels
- **free**: Free users, basic functionality
- **pro**: Professional users, advanced features
- **enterprise**: Enterprise users, full functionality + admin tools

### Access Levels
- **none**: No access
- **read_only**: Read-only access
- **read_write**: Read and write access
- **admin**: Administrator access

## 📚 API Endpoints

### 1. Check Resource Access

Check user's access to a specific resource.

**POST** `/api/v1/resources/check-access`

```bash
# Generate test user token
curl -X POST "http://localhost:8100/auth/dev-token?user_id=auth0%7Ctest123&email=test@test.com"

# Check user access to weather tool
curl -X POST "http://localhost:8100/api/v1/resources/check-access" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "auth0|test123",
    "resource_type": "mcp_tool",
    "resource_name": "weather_get_weather",
    "required_access_level": "read_only"
  }'
```

**Success Response**:
```json
{
  "has_access": true,
  "user_access_level": "read_only",
  "subscription_level": "free",
  "organization_plan": null,
  "access_source": "subscription",
  "reason": "Subscription level: free",
  "resource_info": {
    "subscription_required": "free",
    "resource_category": "weather"
  }
}
```

**Access Denied Response**:
```json
{
  "has_access": false,
  "user_access_level": "none",
  "subscription_level": "free",
  "organization_plan": null,
  "access_source": "personal",
  "reason": "Personal subscription level (free) insufficient for this resource, requires: read_write",
  "resource_info": null
}
```

### 2. Get User Resource Summary

Get user's accessible resources overview.

**GET** `/api/v1/users/{user_id}/resources/summary`

```bash
curl "http://localhost:8100/api/v1/users/auth0%7Ctest123/resources/summary" \
  -H "Authorization: Bearer <jwt_token>"
```

**Response Example**:
```json
{
  "success": true,
  "status": "success",
  "message": "User resource summary retrieved successfully",
  "timestamp": "2025-08-08T10:30:45.123Z",
  "data": {
    "user_id": "auth0|test123",
    "subscription_level": "free",
    "organization_id": null,
    "organization_plan": null,
    "total_accessible_resources": 8,
    "mcp_tools_count": 2,
    "prompts_count": 2,
    "resources_count": 2,
    "personal_granted_count": 6,
    "organization_granted_count": 0,
    "admin_granted_count": 0,
    "expires_soon_count": 0
  }
}
```

### 3. List User Accessible Resources

Get detailed list of user accessible resources.

**GET** `/api/v1/users/{user_id}/resources/accessible`

```bash
# Get all accessible resources
curl "http://localhost:8100/api/v1/users/auth0%7Ctest123/resources/accessible" \
  -H "Authorization: Bearer <jwt_token>"

# Get only MCP tools
curl "http://localhost:8100/api/v1/users/auth0%7Ctest123/resources/accessible?resource_type=mcp_tool" \
  -H "Authorization: Bearer <jwt_token>"
```

**Response Example**:
```json
{
  "success": true,
  "status": "success", 
  "message": "Retrieved 8 accessible resources",
  "timestamp": "2025-08-08T10:35:20.456Z",
  "data": {
    "resources": [
      {
        "resource_type": "mcp_tool",
        "resource_name": "weather_get_weather",
        "access_level": "read_only",
        "access_source": "subscription",
        "subscription_required": "free",
        "expires_at": null
      },
      {
        "resource_type": "mcp_tool", 
        "resource_name": "memory_remember_fact",
        "access_level": "read_write",
        "access_source": "subscription",
        "subscription_required": "free",
        "expires_at": null
      },
      {
        "resource_type": "prompt",
        "resource_name": "user_assistance_prompt",
        "access_level": "read_only",
        "access_source": "subscription",
        "subscription_required": "free",
        "expires_at": null
      }
    ],
    "total_count": 8,
    "resource_type_filter": null
  }
}
```

## 🔧 Admin Operations

### 1. Initialize Default Permissions

Set up basic resource permission configurations for the system.

**POST** `/api/v1/admin/resources/initialize-defaults`

```bash
curl -X POST "http://localhost:8100/api/v1/admin/resources/initialize-defaults" \
  -H "Authorization: Bearer <admin_jwt_token>"
```

**Response Example**:
```json
{
  "success": true,
  "status": "success",
  "message": "Default resource permissions initialized successfully",
  "timestamp": "2025-08-08T10:40:15.789Z",
  "data": {"initialized": true}
}
```

### 2. Grant User Special Access

Admin can grant users special access beyond their subscription level.

**POST** `/api/v1/admin/resources/grant-access`

```bash
# Grant free user access to pro-level image generation tool
curl -X POST "http://localhost:8100/api/v1/admin/resources/grant-access" \
  -H "Authorization: Bearer <admin_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "auth0|test123",
    "resource_type": "mcp_tool",
    "resource_name": "image_generate_image",
    "access_level": "read_write",
    "granted_by_admin": true,
    "expires_at": "2025-12-31T23:59:59Z",
    "reason": "Beta tester special access"
  }'
```

**Response Example**:
```json
{
  "success": true,
  "status": "success",
  "message": "Resource access granted to user auth0|test123",
  "timestamp": "2025-08-08T10:45:30.123Z",
  "data": {
    "user_id": "auth0|test123",
    "resource_type": "mcp_tool",
    "resource_name": "image_generate_image", 
    "access_level": "read_write",
    "granted_by_admin": true
  }
}
```

### 3. Revoke User Special Access

Revoke previously granted special access permissions.

**DELETE** `/api/v1/admin/resources/revoke-access`

```bash
curl -X DELETE "http://localhost:8100/api/v1/admin/resources/revoke-access" \
  -H "Authorization: Bearer <admin_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "auth0|test123",
    "resource_type": "mcp_tool",
    "resource_name": "image_generate_image",
    "reason": "Beta testing ended"
  }'
```

### 4. Create Custom Resource Permission

Define access rules for new resources.

**POST** `/api/v1/admin/resources/permissions`

```bash
curl -X POST "http://localhost:8100/api/v1/admin/resources/permissions" \
  -H "Authorization: Bearer <admin_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "resource_type": "mcp_tool",
    "resource_name": "custom_ai_assistant",
    "resource_category": "ai",
    "subscription_level": "pro",
    "access_level": "read_write",
    "description": "Custom AI assistant tool for pro users"
  }'
```

## 🏢 Organization Resource Management

### Organization Permission Inheritance
When user is an organization member, permission checks consider:
1. Organization plan level (startup/growth/enterprise)
2. User's role within the organization
3. Organization admin special grants

### Example: Organization User Permission Check

```bash
# Check organization member's resource access
curl -X POST "http://localhost:8100/api/v1/resources/check-access" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "auth0|org_member123",
    "organization_id": "org_startup_001", 
    "resource_type": "mcp_tool",
    "resource_name": "data_analytics_tools",
    "required_access_level": "read_write"
  }'
```

**Organization Permission Response**:
```json
{
  "has_access": true,
  "user_access_level": "read_write",
  "subscription_level": "free",
  "organization_plan": "growth",
  "access_source": "organization",
  "reason": "Organization plan (growth) access",
  "resource_info": {
    "organization_id": "org_startup_001",
    "plan_required": "growth"
  }
}
```

## 🔍 Real-world Usage Scenarios

### Scenario 1: MCP Tool Permission Check
Before calling an MCP tool, check if user has access:

```bash
# 1. Check image generation tool permission
curl -X POST "http://localhost:8100/api/v1/resources/check-access" \
  -H "Authorization: Bearer <jwt_token>" \
  -d '{
    "user_id": "auth0|user123",
    "resource_type": "mcp_tool", 
    "resource_name": "image_generate_image",
    "required_access_level": "read_write"
  }'

# 2. Based on permission result, decide whether to allow tool call
# has_access: true -> Allow tool execution
# has_access: false -> Return permission error or upgrade prompt
```

### Scenario 2: Frontend UI Permission Control
Dynamically show UI based on user's accessible resources:

```bash
# Get all accessible MCP tools for user
curl "http://localhost:8100/api/v1/users/auth0%7Cuser123/resources/accessible?resource_type=mcp_tool" \
  -H "Authorization: Bearer <jwt_token>"

# Frontend displays feature buttons based on returned tool list
```

### Scenario 3: Subscription Upgrade Prompts
When user tries to access premium features, provide upgrade suggestions:

```bash
# User tries to access pro feature
curl -X POST "http://localhost:8100/api/v1/resources/check-access" \
  -d '{
    "user_id": "auth0|free_user",
    "resource_type": "mcp_tool",
    "resource_name": "advanced_analytics", 
    "required_access_level": "read_write"
  }'

# Response: has_access: false, reason contains subscription level info
# Frontend can show "Upgrade to Pro to unlock this feature" prompt
```

## 📊 Permission Monitoring and Cleanup

### Cleanup Expired Permissions

```bash
# Clean up expired permissions in the system
curl -X POST "http://localhost:8100/api/v1/admin/resources/cleanup-expired" \
  -H "Authorization: Bearer <admin_jwt_token>"
```

**Response Example**:
```json
{
  "success": true,
  "status": "success",
  "message": "Cleaned up 5 expired permissions",
  "timestamp": "2025-08-08T11:00:00.000Z",
  "data": {"cleaned_count": 5}
}
```

## 🚨 Error Handling

### Common Error Responses

```json
// 403 Forbidden - Permission denied
{
  "detail": "Access denied: You can only check your own resource access"
}

// 404 Not Found - User not found
{
  "detail": "User not found or no resource access data"
}

// 400 Bad Request - Invalid parameters
{
  "detail": "Invalid resource type or access level"
}
```

## 🔧 Integration Examples

### Python Client Example

```python
import httpx
import asyncio
from datetime import datetime

class ResourceAuthClient:
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    async def check_resource_access(self, user_id: str, resource_type: str, 
                                   resource_name: str, required_level: str = "read_only"):
        """Check resource access permission"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/resources/check-access",
                headers=self.headers,
                json={
                    "user_id": user_id,
                    "resource_type": resource_type,
                    "resource_name": resource_name,
                    "required_access_level": required_level
                }
            )
            return response.json()
    
    async def get_user_accessible_resources(self, user_id: str, resource_type: str = None):
        """Get user accessible resources"""
        url = f"{self.base_url}/api/v1/users/{user_id}/resources/accessible"
        params = {"resource_type": resource_type} if resource_type else {}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            return response.json()

# Usage example
async def main():
    client = ResourceAuthClient("http://localhost:8100", "your_jwt_token")
    
    # Check permission
    access_result = await client.check_resource_access(
        user_id="auth0|test123",
        resource_type="mcp_tool", 
        resource_name="image_generate_image",
        required_level="read_write"
    )
    
    if access_result["has_access"]:
        print("✅ User has access to image generation tool")
        # Execute related operations
    else:
        print(f"❌ Permission denied: {access_result['reason']}")
        # Show upgrade prompt
    
    # Get all accessible tools
    tools = await client.get_user_accessible_resources(
        user_id="auth0|test123",
        resource_type="mcp_tool"
    )
    print(f"User can access {len(tools['data']['resources'])} MCP tools")

# asyncio.run(main())
```

### JavaScript/Node.js Example

```javascript
class ResourceAuthClient {
  constructor(baseUrl, authToken) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Authorization': `Bearer ${authToken}`,
      'Content-Type': 'application/json'
    };
  }

  async checkResourceAccess(userId, resourceType, resourceName, requiredLevel = 'read_only') {
    const response = await fetch(`${this.baseUrl}/api/v1/resources/check-access`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        user_id: userId,
        resource_type: resourceType,
        resource_name: resourceName,
        required_access_level: requiredLevel
      })
    });
    return response.json();
  }

  async getUserResourceSummary(userId) {
    const response = await fetch(`${this.baseUrl}/api/v1/users/${userId}/resources/summary`, {
      headers: this.headers
    });
    return response.json();
  }
}

// Usage example
const client = new ResourceAuthClient('http://localhost:8100', 'your_jwt_token');

// Permission check decorator
function requireResourceAccess(resourceType, resourceName, requiredLevel = 'read_only') {
  return function(target, propertyName, descriptor) {
    const method = descriptor.value;
    descriptor.value = async function(userId, ...args) {
      const accessCheck = await client.checkResourceAccess(userId, resourceType, resourceName, requiredLevel);
      
      if (!accessCheck.has_access) {
        throw new Error(`Permission denied: ${accessCheck.reason}`);
      }
      
      return method.apply(this, [userId, ...args]);
    };
  };
}

class MCPToolService {
  @requireResourceAccess('mcp_tool', 'image_generate_image', 'read_write')
  async generateImage(userId, prompt) {
    // Actual image generation logic
    console.log(`Generating image for user ${userId}: ${prompt}`);
  }
}
```

## 📝 Best Practices

### 1. Permission Check Timing
- **Before API calls**: Check permissions before executing MCP tools or accessing resources
- **During UI rendering**: Dynamically show feature buttons based on user permissions
- **Periodic checks**: For long-running operations, re-validate permissions periodically

### 2. Caching Strategy
- Client can cache user permission info with reasonable expiration time
- Clear related cache promptly after permission changes
- Recommend real-time permission check for sensitive operations

### 3. Error Handling
- Provide clear error messages and upgrade suggestions when permission denied
- Implement graceful degradation with alternative functionality
- Log permission check failures for user behavior analysis

### 4. Monitoring & Alerting
- Monitor permission check frequency and success rates
- Watch for patterns in permission denials to optimize product strategy
- Regular cleanup of expired permissions to maintain system performance

---

## 📞 Support Information

- **API Documentation**: http://localhost:8100/docs
- **Health Check**: http://localhost:8100/health
- **Database Schema**: Reference `/resources/dbs/supabase/dev/` directory

**📝 Last Updated**: 2025-08-08 | API Version: v1.0 | Status: ✅ Implementation Complete