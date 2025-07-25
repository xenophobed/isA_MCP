# Unified User Service API Documentation

## Overview

The Unified User Service API provides centralized access to all user-related data operations. Other services MUST use these APIs instead of directly accessing user database tables.

**Base URL**: `http://localhost:8100/api/v1`  
**Authentication**: Bearer token (Auth0 JWT) required for all endpoints

## Service Architecture

```
┌─────────────────────────────────────────────────┐
│           Other Services (clients)              │
└─────────────────┬──────────────────────────────┘
                  │ HTTP API Calls
                  ▼
┌─────────────────────────────────────────────────┐
│           User Service API                      │
│         (Centralized Data Access)               │
└─────────────────┬──────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│              Database                           │
│  (users, sessions, usage_records, etc.)        │
└─────────────────────────────────────────────────┘
```

## Authentication

All endpoints require a valid Auth0 JWT token in the Authorization header:

```http
Authorization: Bearer <jwt_token>
```

## Usage Records API

### Record Usage Event
Record AI usage, API calls, or other user activities.

```http
POST /users/{user_id}/usage
Content-Type: application/json

{
  "user_id": "auth0|123456",
  "session_id": "session-uuid",
  "endpoint": "/api/chat/completion",
  "event_type": "ai_chat",
  "credits_charged": 5.0,
  "cost_usd": 0.01,
  "tokens_used": 1500,
  "prompt_tokens": 1000,
  "completion_tokens": 500,
  "model_name": "gpt-4",
  "provider": "openai",
  "tool_name": "chat_service",
  "operation_name": "generate_response"
}
```

**Response:**
```json
{
  "success": true,
  "status": "success",
  "message": "Usage recorded successfully",
  "data": {
    "id": 123,
    "user_id": "auth0|123456",
    "session_id": "session-uuid",
    "event_type": "ai_chat",
    "credits_charged": 5.0,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Get Usage History
```http
GET /users/{user_id}/usage?limit=50&offset=0&start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z
```

### Get Usage Statistics
```http
GET /users/{user_id}/usage/stats?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_records": 150,
    "total_credits_charged": 750.5,
    "total_cost_usd": 15.01,
    "total_tokens_used": 225000,
    "by_event_type": {
      "ai_chat": 120,
      "api_call": 30
    },
    "by_model": {
      "gpt-4": 100,
      "gpt-3.5-turbo": 50
    }
  }
}
```

## Session Management API

### Create Session
Create a new conversation or interaction session.

```http
POST /users/{user_id}/sessions
Content-Type: application/json

{
  "user_id": "auth0|123456",
  "title": "Chat about AI development",
  "metadata": {
    "source": "web_app",
    "type": "chat_session"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 789,
    "session_id": "uuid-generated",
    "user_id": "auth0|123456",
    "title": "Chat about AI development",
    "status": "active",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Get User Sessions
```http
GET /users/{user_id}/sessions?active_only=true&limit=20&offset=0
```

### Update Session Status
```http
PUT /sessions/{session_id}/status
Content-Type: application/json

{
  "status": "completed"
}
```

### Add Session Message
```http
POST /sessions/{session_id}/messages
Content-Type: application/json

{
  "role": "user",
  "content": "Hello, how can AI help with coding?",
  "message_type": "chat",
  "tokens_used": 10,
  "cost_usd": 0.001
}
```

### Get Session Messages
```http
GET /sessions/{session_id}/messages?limit=100&offset=0
```

## Credit Transaction API

### Consume Credits
Deduct credits from user balance for usage.

```http
POST /users/{user_id}/credits/consume
Content-Type: application/json

{
  "amount": 10.5,
  "description": "AI chat completion",
  "usage_record_id": 123
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 456,
    "transaction_id": "txn-uuid",
    "user_id": "auth0|123456",
    "transaction_type": "consume",
    "amount": 10.5,
    "balance_before": 100.0,
    "balance_after": 89.5,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Recharge Credits
Add credits to user balance.

```http
POST /users/{user_id}/credits/recharge
Content-Type: application/json

{
  "amount": 50.0,
  "description": "Monthly subscription refill",
  "reference_id": "stripe_payment_123"
}
```

### Get Credit Balance
```http
GET /users/{user_id}/credits/balance
```

**Response:**
```json
{
  "success": true,
  "data": 89.5,
  "message": "Credit balance retrieved successfully"
}
```

### Get Transaction History
```http
GET /users/{user_id}/credits/transactions?transaction_type=consume&limit=50&offset=0
```

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "status": "error",
  "message": "User not found: auth0|123456",
  "error_code": "UserNotFoundException",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Common HTTP Status Codes

- `200 OK` - Success
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing or invalid auth token
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

## Usage Examples for Other Services

### Memory Service Integration
```python
import httpx
import os

async def record_memory_usage(user_id: str, session_id: str, tokens_used: int):
    """Record memory service usage"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{os.getenv('USER_SERVICE_URL')}/api/v1/users/{user_id}/usage",
            headers={"Authorization": f"Bearer {get_auth_token()}"},
            json={
                "user_id": user_id,
                "session_id": session_id,
                "endpoint": "/memory/store",
                "event_type": "memory_storage",
                "credits_charged": tokens_used * 0.01,
                "tokens_used": tokens_used,
                "tool_name": "memory_service",
                "operation_name": "store_memory"
            }
        )
        return response.json()
```

### Terminal Service Integration
```python
async def create_terminal_session(user_id: str, title: str):
    """Create terminal session via user service"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{os.getenv('USER_SERVICE_URL')}/api/v1/users/{user_id}/sessions",
            headers={"Authorization": f"Bearer {get_auth_token()}"},
            json={
                "user_id": user_id,
                "title": title,
                "metadata": {
                    "source": "terminal_service",
                    "type": "terminal_session"
                }
            }
        )
        return response.json()
```

### Credit Consumption Example
```python
async def consume_credits_for_api_call(user_id: str, credits_needed: float, usage_record_id: int):
    """Consume credits for API usage"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{os.getenv('USER_SERVICE_URL')}/api/v1/users/{user_id}/credits/consume",
            headers={"Authorization": f"Bearer {get_auth_token()}"},
            json={
                "amount": credits_needed,
                "description": "Terminal API execution",
                "usage_record_id": usage_record_id
            }
        )
        
        if response.status_code == 400:
            # Handle insufficient credits
            balance_response = await client.get(
                f"{os.getenv('USER_SERVICE_URL')}/api/v1/users/{user_id}/credits/balance",
                headers={"Authorization": f"Bearer {get_auth_token()}"}
            )
            current_balance = balance_response.json()["data"]
            raise InsufficientCreditsError(f"Need {credits_needed}, have {current_balance}")
        
        return response.json()
```

## Migration Guidelines

### Phase 1: Update Services to Use APIs
1. Replace direct database inserts with HTTP API calls
2. Update service configurations with USER_SERVICE_URL
3. Implement proper error handling for API responses

### Phase 2: Remove Direct Database Access
1. Remove database connection strings from other services
2. Delete direct SQL queries for user tables
3. Update deployment configurations

### Phase 3: Validation
1. Test all user data flows through the API
2. Verify data consistency
3. Monitor API performance and error rates

## Environment Configuration

Services should configure these environment variables:

```bash
# User service endpoint
USER_SERVICE_URL=http://localhost:8100

# Authentication (if needed for service-to-service calls)
USER_SERVICE_API_KEY=your-api-key-here
```

## Best Practices

1. **Always validate user existence** before operations
2. **Handle API failures gracefully** with retry logic
3. **Use appropriate error handling** for different scenarios
4. **Batch operations** when possible to reduce API calls
5. **Monitor API usage** and implement caching where appropriate
6. **Include proper metadata** in usage records for analytics

## Support

For questions about the API or integration help:
- Check the interactive API docs at `http://localhost:8100/docs`
- Review this documentation
- Contact the user service team

---

**Note**: This API enforces proper service boundaries and ensures data consistency. All user-related data operations must go through these endpoints.