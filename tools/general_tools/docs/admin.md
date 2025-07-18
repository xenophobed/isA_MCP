# Admin Tools Documentation

## Overview

The Admin Tools provide secure administrative functionality for the MCP server, including authorization management, system monitoring, and audit logging. All admin tools require proper authentication and authorization.

## Available Tools

### 1. get_authorization_requests

**Purpose**: Retrieve pending authorization requests (admin only)

**Parameters**:
- `user_id` (string): ID of the requesting user (must be admin)

**Response**:
```json
{
  "status": "success",
  "action": "get_authorization_requests",
  "data": {
    "requests": [
      {
        "id": "req-123",
        "tool_name": "delete_user_data",
        "user_id": "user123",
        "reason": "User requested account deletion",
        "security_level": "HIGH",
        "created_at": "2025-07-12T10:30:00Z",
        "expires_at": "2025-07-12T11:30:00Z"
      }
    ],
    "count": 1
  },
  "timestamp": "2025-07-12T10:45:00Z"
}
```

**Security**: Admin-only access. Non-admin users receive unauthorized error.

### 2. approve_authorization

**Purpose**: Approve a pending authorization request

**Parameters**:
- `request_id` (string, required): ID of the authorization request to approve
- `approved_by` (string, required): ID of the admin approving the request

**Response**:
```json
{
  "status": "success",
  "action": "approve_authorization",
  "data": {
    "request_id": "req-123",
    "approved": true,
    "approved_by": "admin_user",
    "approved_at": "2025-07-12T10:45:00Z"
  },
  "timestamp": "2025-07-12T10:45:00Z"
}
```

**Error Cases**:
- Invalid or non-existent request ID
- Missing required parameters

### 3. get_monitoring_metrics

**Purpose**: Retrieve system monitoring metrics and performance data

**Parameters**:
- `user_id` (string): ID of the requesting user (must be admin)

**Response**:
```json
{
  "status": "success",
  "action": "get_monitoring_metrics",
  "data": {
    "uptime": 86400,
    "total_requests": 1500,
    "security_violations": 0,
    "rate_limit_hits": 5,
    "memory_usage": "245MB",
    "cpu_usage": "15%",
    "active_sessions": 23,
    "error_rate": "0.2%"
  },
  "timestamp": "2025-07-12T10:45:00Z"
}
```

**Security**: Admin-only access. Provides detailed system metrics.

### 4. get_audit_log

**Purpose**: Retrieve audit log entries for security and compliance

**Parameters**:
- `limit` (integer, optional): Maximum number of log entries to return (default: 50)
- `user_id` (string): ID of the requesting user (must be admin)

**Response**:
```json
{
  "status": "success",
  "action": "get_audit_log",
  "data": {
    "logs": [
      {
        "id": "log-456",
        "timestamp": "2025-07-12T10:30:00Z",
        "user_id": "user123",
        "action": "tool_execution",
        "tool_name": "web_search",
        "status": "success",
        "details": "Search query executed successfully"
      }
    ],
    "count": 1,
    "limit": 50
  },
  "timestamp": "2025-07-12T10:45:00Z"
}
```

**Security**: Admin-only access. Contains sensitive security and activity information.

## Testing

### Test Coverage

The admin tools are comprehensively tested using the MCP client:

- **Capabilities Testing**: All tools appear in `/capabilities` endpoint
- **Discovery Testing**: AI can discover admin tools for relevant requests
- **MCP Integration**: Direct tool calls via `mcp_client.py`
- **Authorization Testing**: Admin vs non-admin access control
- **Error Handling**: Invalid inputs and edge cases

### Running Tests

```bash
python -m pytest tools/general_tools/tests/test_admin.py -v
```

### Test Results

 **15/15 tests passing** - All admin tools functionality verified

## Security Considerations

1. **Authentication Required**: All admin tools require valid admin authentication
2. **Authorization Checks**: Non-admin users are denied access to all tools
3. **Audit Logging**: All admin actions are logged for security compliance
4. **Rate Limiting**: Admin tools respect system rate limits
5. **Input Validation**: All parameters are validated before processing

## Usage Examples

### Check Pending Authorizations
```python
# Admin user checking pending requests
response = await client.call_tool("get_authorization_requests", {
    "user_id": "admin_user"
})
```

### Approve Authorization Request
```python
# Admin approving a high-security operation
response = await client.call_tool("approve_authorization", {
    "request_id": "req-123",
    "approved_by": "admin_user"
})
```

### Monitor System Health
```python
# Get comprehensive system metrics
response = await client.call_tool("get_monitoring_metrics", {
    "user_id": "admin_user"
})
```

### Review Security Logs
```python
# Get recent audit log entries
response = await client.call_tool("get_audit_log", {
    "limit": 25,
    "user_id": "admin_user"
})
```

## Keywords

Authorization, security, monitoring, admin, audit, compliance, metrics, system health, management

## Integration

Admin tools integrate with:
- Core security manager for authentication
- Monitoring system for metrics collection
- Audit logging system for compliance
- Authorization manager for request handling