# Authorization System Documentation

## Overview

The MCP server implements a comprehensive human-in-the-loop authorization system that provides secure approval workflows for sensitive operations. The system consists of two complementary tool sets that work together to create, manage, and approve authorization requests.

## Architecture

### Two-Sided Authorization System

The authorization system is designed with clear separation of concerns:

1. **Client/User Side** (Interaction Tools) - Request authorization
2. **Admin/Server Side** (Admin Tools) - Manage and approve requests

This creates a secure workflow where sensitive operations require explicit human approval from authorized personnel.

## Tool Sets

### 1. Interaction Tools - Client/User Side

**File**: `tools/general_tools/interaction_tools.py`

#### `request_authorization`
- **Purpose**: **CREATE** authorization requests when AI needs permission
- **Who uses it**: AI system or client applications  
- **When**: Before executing sensitive operations
- **Action**: Creates a new authorization request in the system

### 2. Admin Tools - Server/Admin Side

**File**: `tools/general_tools/admin_tools.py`

#### `get_authorization_requests`
- **Purpose**: **VIEW** pending authorization requests
- **Who uses it**: Admins and authorized personnel
- **When**: To review what requests need approval
- **Action**: Retrieves list of pending authorization requests

#### `approve_authorization`
- **Purpose**: **APPROVE** pending authorization requests
- **Who uses it**: Admins and authorized personnel  
- **When**: To grant permission for sensitive operations
- **Action**: Approves specific authorization requests

## Complete Authorization Workflow

### Step 1: Request Authorization (User/AI Side)

When the AI or client needs to perform a sensitive operation, it first requests authorization:

```python
# AI needs to delete user data - requests permission first
response = await client.call_tool("request_authorization", {
    "tool_name": "delete_user_data",
    "reason": "User requested account deletion", 
    "user_id": "user123",
    "tool_args": {"user_id": "user123", "confirm": True}
})

# Response includes request_id for tracking
request_id = response["data"]["request_id"]  # e.g., "auth-req-789"
```

**Response**:
```json
{
  "status": "authorization_requested",
  "action": "request_authorization",
  "data": {
    "request_id": "auth-req-789",
    "tool_name": "delete_user_data",
    "tool_args": {"user_id": "user123", "confirm": true},
    "reason": "User requested account deletion",
    "security_level": "HIGH",
    "user_id": "user123",
    "expires_at": "2025-07-12T11:45:00Z",
    "instruction": "This request requires authorization. The client should handle the approval process."
  },
  "timestamp": "2025-07-12T10:45:00Z"
}
```

### Step 2: Admin Reviews Requests (Admin Side)

Administrators can view all pending authorization requests:

```python
# Admin checks what authorization requests are pending
response = await client.call_tool("get_authorization_requests", {
    "user_id": "admin_user"  # Must be admin
})

# Shows list of pending requests including "auth-req-789"
```

**Response**:
```json
{
  "status": "success",
  "action": "get_authorization_requests",
  "data": {
    "requests": [
      {
        "id": "auth-req-789",
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

### Step 3: Admin Approves (Admin Side)

Admin approves the specific request to grant permission:

```python
# Admin approves the specific request
response = await client.call_tool("approve_authorization", {
    "request_id": "auth-req-789",  # From step 1
    "approved_by": "admin_user"
})

# Now the AI can proceed with the original operation
```

**Response**:
```json
{
  "status": "success",
  "action": "approve_authorization",
  "data": {
    "request_id": "auth-req-789",
    "approved": true,
    "approved_by": "admin_user",
    "approved_at": "2025-07-12T10:45:00Z"
  },
  "timestamp": "2025-07-12T10:45:00Z"
}
```

### Step 4: Execute Original Operation

Once approved, the system can safely proceed with the original sensitive operation.

## Key Differences Between Tool Sets

| Aspect | Interaction Tools | Admin Tools |
|--------|------------------|-------------|
| **Purpose** | Request permission | Manage permissions |
| **User** | AI/Client | Admin/Manager |
| **Action** | Creates requests | Reviews/Approves requests |
| **Security** | Any authenticated user | Admin-only |
| **Direction** | Bottom-up (request) | Top-down (approve) |
| **File** | `interaction_tools.py` | `admin_tools.py` |

## Security Levels

The system automatically assigns security levels based on the requested operation:

- **`MEDIUM`**: Standard tools (e.g., `get_user_info`)
- **`HIGH`**: Sensitive operations (e.g., `forget_user_data`, `delete_all_users`)
- **`CRITICAL`**: System-level operations (e.g., `admin_reset_system`)

Higher security levels may require additional approval steps or higher-level administrators.

## Use Cases

### Use `request_authorization` when:
- AI needs to perform sensitive operations
- Client wants human approval before proceeding
- Implementing safety guardrails
- Following compliance requirements
- Data deletion or modification operations
- System configuration changes

### Use admin tools when:
- Managing authorization workflows
- Auditing security requests
- Implementing approval hierarchies
- Monitoring system security
- Compliance reporting
- Security incident response

## Complete Example Workflow

```python
async def secure_user_deletion_workflow():
    """Complete workflow for securely deleting user data with authorization"""
    
    # 1. AI requests permission to delete data
    print("= Requesting authorization for user deletion...")
    auth_response = await client.call_tool("request_authorization", {
        "tool_name": "delete_user_data",
        "reason": "User clicked 'Delete Account' button",
        "user_id": "user123",
        "tool_args": {"user_id": "user123", "permanent": True}
    })
    
    request_id = auth_response["data"]["request_id"]
    print(f"=Ë Authorization request created: {request_id}")
    
    # 2. Admin checks pending requests
    print("=h=¼ Admin checking pending requests...")
    pending = await client.call_tool("get_authorization_requests", {
        "user_id": "admin_user" 
    })
    
    print(f"=Ê Found {pending['data']['count']} pending requests")
    
    # 3. Admin reviews and approves the request
    print(" Admin approving the request...")
    approval = await client.call_tool("approve_authorization", {
        "request_id": request_id,
        "approved_by": "admin_user"
    })
    
    if approval["data"]["approved"]:
        print("<‰ Authorization approved!")
        # 4. Now AI can safely proceed with the deletion
        # (The actual deletion would happen via another tool)
        print("=Ñ Proceeding with user data deletion...")
    else:
        print("L Authorization denied")
        
    return approval
```

## Security Considerations

1. **Authentication Required**: All authorization tools require valid authentication
2. **Role-Based Access**: Admin tools restricted to authorized personnel only
3. **Audit Logging**: All authorization requests and approvals are logged
4. **Time-Based Expiry**: Authorization requests expire after a set time
5. **Request Tracking**: Unique request IDs for full audit trails
6. **Security Level Enforcement**: Higher security operations require appropriate clearance

## Error Handling

### Common Error Scenarios

1. **Unauthorized Access**: Non-admin users accessing admin tools
2. **Invalid Request IDs**: Approving non-existent requests
3. **Expired Requests**: Attempting to approve expired authorization requests
4. **Missing Parameters**: Required fields not provided
5. **Insufficient Permissions**: User lacks required security clearance

### Example Error Response

```json
{
  "status": "error",
  "action": "approve_authorization",
  "error": "Authorization request not found or expired",
  "request_id": "invalid-req-123",
  "timestamp": "2025-07-12T10:45:00Z"
}
```

## Integration Points

The authorization system integrates with:

- **Core Security Manager**: For authentication and role validation
- **Monitoring System**: For tracking authorization metrics
- **Audit Logging**: For compliance and security reporting
- **Client Applications**: For human interaction handling
- **MCP Server**: For secure tool execution

## Testing

Both tool sets have comprehensive test coverage:

- **Admin Tools**: `tools/general_tools/tests/test_admin.py` (15/15 tests passing)
- **Interaction Tools**: `tools/general_tools/tests/test_interaction.py` (16/17 tests passing)

Run tests:
```bash
# Test admin tools
python -m pytest tools/general_tools/tests/test_admin.py -v

# Test interaction tools  
python -m pytest tools/general_tools/tests/test_interaction.py -v
```

## Keywords

Authorization, approval, security, human-in-the-loop, workflow, admin, permissions, compliance, audit, safety, guardrails

## Related Documentation

- [Admin Tools Documentation](./admin.md)
- [Interaction Tools Documentation](./interaction.md)
- Core Security Manager Documentation
- MCP Server Security Guidelines