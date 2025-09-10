# User Usage Tracking API Guide

## Overview

The User Usage Tracking API provides comprehensive functionality for recording, retrieving, and analyzing user interactions with AI services. This API is essential for billing, analytics, and monitoring purposes.

**⚠️ Important**: This API **only records usage history** - it does **not consume credits**. For credit consumption, use the [Credit Management API](how_to_user_credit.md).

## Authentication

All usage tracking endpoints require Bearer Token authentication:

```bash
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json
```

**Supported Token Types:**
- **Auth0 JWT**: RS256 signature algorithm  
- **Supabase JWT**: HS256 signature algorithm

## API Endpoints

### 1. Record Usage Event

**POST** `/api/v1/users/{user_id}/usage`

Records detailed AI service usage for billing and analytics purposes.

**Request Example:**
```bash
curl -X POST "http://localhost:8100/api/v1/users/auth0|test456/usage" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "auth0|test456",
    "session_id": "368ef8d4-5f6d-4129-9077-917e65ec33d5",
    "endpoint": "/api/chat/completion",
    "event_type": "ai_text_generation",
    "credits_charged": 15.5,
    "cost_usd": 0.031,
    "tokens_used": 500,
    "prompt_tokens": 300,
    "completion_tokens": 200,
    "model_name": "gpt-4",
    "provider": "openai"
  }'
```

**Success Response:**
```json
{
  "success": true,
  "status": "success",
  "message": "Usage recorded successfully",
  "timestamp": "2025-09-06T12:51:27.928957",
  "data": {
    "id": 471,
    "user_id": "auth0|test456",
    "session_id": "368ef8d4-5f6d-4129-9077-917e65ec33d5",
    "trace_id": null,
    "endpoint": "/api/chat/completion",
    "event_type": "ai_text_generation",
    "credits_charged": 15.5,
    "cost_usd": 0.031,
    "calculation_method": "unknown",
    "tokens_used": 500,
    "prompt_tokens": 300,
    "completion_tokens": 200,
    "model_name": "gpt-4",
    "provider": "openai",
    "tool_name": null,
    "operation_name": null,
    "billing_metadata": {},
    "request_data": {},
    "response_data": {},
    "created_at": "2025-09-06T12:51:27.913917Z"
  }
}
```

**Request Parameters:**
- `user_id` (required): User identifier
- `session_id` (optional): Associated session ID
- `endpoint` (required): API endpoint used
- `event_type` (required): Type of usage event
- `credits_charged` (required): Credits charged for this usage
- `cost_usd` (optional): USD cost of the operation
- `tokens_used` (optional): Total tokens consumed
- `prompt_tokens` (optional): Input tokens
- `completion_tokens` (optional): Output tokens
- `model_name` (optional): AI model used
- `provider` (optional): Service provider (openai, anthropic, etc.)

### 2. Get Usage History

**GET** `/api/v1/users/{user_id}/usage`

Retrieves paginated usage history for a user.

**Request Example:**
```bash
curl "http://localhost:8100/api/v1/users/auth0%7Ctest456/usage?limit=5&offset=0" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Query Parameters:**
- `limit` (optional): Number of records to retrieve (default: 50, max: 100)
- `offset` (optional): Number of records to skip (default: 0)
- `start_date` (optional): Start date filter (ISO format)
- `end_date` (optional): End date filter (ISO format)
- `event_type` (optional): Filter by event type
- `model_name` (optional): Filter by AI model

**Success Response:**
```json
{
  "success": true,
  "status": "success",
  "message": "Retrieved 2 usage records",
  "timestamp": "2025-09-06T12:54:07.863456",
  "data": [
    {
      "id": 471,
      "user_id": "auth0|test456",
      "session_id": "368ef8d4-5f6d-4129-9077-917e65ec33d5",
      "trace_id": null,
      "endpoint": "/api/chat/completion",
      "event_type": "ai_text_generation",
      "credits_charged": 15.5,
      "cost_usd": 0.031,
      "calculation_method": "unknown",
      "tokens_used": 500,
      "prompt_tokens": 300,
      "completion_tokens": 200,
      "model_name": "gpt-4",
      "provider": "openai",
      "tool_name": null,
      "operation_name": null,
      "billing_metadata": {},
      "request_data": {},
      "response_data": {},
      "created_at": "2025-09-06T12:51:27.913917Z"
    },
    {
      "id": 346,
      "user_id": "auth0|test456",
      "session_id": "test_session_billing_001",
      "trace_id": null,
      "endpoint": "/api/chat",
      "event_type": "ai_chat",
      "credits_charged": 5.0,
      "cost_usd": 0.01,
      "calculation_method": "simple_credit_billing",
      "tokens_used": 150,
      "prompt_tokens": 100,
      "completion_tokens": 50,
      "model_name": "gpt-4",
      "provider": "openai",
      "tool_name": "isA_agent",
      "operation_name": "chat_completion",
      "billing_metadata": {
        "tool_calls": 1,
        "model_calls": 2,
        "billing_method": "langchain_custom_events",
        "execution_time": 2.5
      },
      "request_data": {
        "temperature": 0.7
      },
      "response_data": {
        "finish_reason": "stop"
      },
      "created_at": "2025-07-27T09:01:22.013462Z"
    }
  ]
}
```

### 3. Get Usage Statistics

**GET** `/api/v1/users/{user_id}/usage/stats`

Retrieves aggregated usage statistics for analytics and reporting.

**Request Example:**
```bash
curl "http://localhost:8100/api/v1/users/auth0%7Ctest456/usage/stats?start_date=2025-01-01T00:00:00Z&end_date=2025-12-31T23:59:59Z" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Query Parameters:**
- `start_date` (optional): Start date for statistics (ISO format)
- `end_date` (optional): End date for statistics (ISO format)
- `event_type` (optional): Filter by specific event type
- `model_name` (optional): Filter by AI model

**Success Response:**
```json
{
  "success": true,
  "status": "success",
  "message": "Statistics retrieved successfully",
  "timestamp": "2025-09-06T12:56:48.908412",
  "data": {
    "total_records": 2,
    "total_credits_charged": 20.5,
    "total_cost_usd": 0.041,
    "total_tokens_used": 650,
    "by_event_type": {
      "ai_chat": 1,
      "ai_text_generation": 1
    },
    "by_model": {
      "gpt-4": 2
    },
    "by_provider": {
      "openai": 2
    },
    "date_range": {
      "start_date": "2025-01-01T00:00:00Z",
      "end_date": "2025-12-31T23:59:59Z"
    }
  }
}
```

## Common Event Types

- `ai_chat`: Chat completions
- `ai_text_generation`: Text generation
- `ai_code_generation`: Code generation
- `ai_image_generation`: Image generation
- `ai_image_analysis`: Image analysis
- `api_call`: General API calls
- `tool_execution`: MCP tool executions

## Best Practices

### 1. Comprehensive Recording
Record detailed usage information for accurate billing and analytics:

```javascript
const usageData = {
  user_id: "auth0|user123",
  session_id: sessionId,
  endpoint: "/api/chat/completion",
  event_type: "ai_text_generation",
  credits_charged: calculateCredits(tokens),
  cost_usd: calculateCost(tokens, model),
  tokens_used: response.usage.total_tokens,
  prompt_tokens: response.usage.prompt_tokens,
  completion_tokens: response.usage.completion_tokens,
  model_name: "gpt-4",
  provider: "openai",
  tool_name: toolName,
  operation_name: operationName,
  billing_metadata: {
    request_id: requestId,
    billing_tier: userTier,
    execution_time: executionTime
  },
  request_data: {
    temperature: 0.7,
    max_tokens: maxTokens
  },
  response_data: {
    finish_reason: response.finish_reason,
    model_version: response.model
  }
};
```

### 2. Separation of Concerns
- **Usage Recording**: Use this API to record detailed usage logs
- **Credit Consumption**: Use [Credit API](how_to_user_credit.md) to actually deduct credits
- **Best Practice**: Call both APIs in sequence for complete billing workflow

### 3. Error Handling
Always implement proper error handling for usage recording:

```javascript
async function recordUsage(usageData) {
  try {
    const response = await fetch('/api/v1/users/usage', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(usageData)
    });
    
    if (!response.ok) {
      console.error('Failed to record usage:', await response.text());
      // Don't fail the main operation, but log the error
    }
    
    return await response.json();
  } catch (error) {
    console.error('Usage recording error:', error);
    // Continue with main operation even if usage recording fails
  }
}
```

### 4. Performance Considerations
- Usage recording should not block the main operation
- Consider asynchronous/background recording for high-throughput scenarios
- Batch multiple usage records if possible

### 5. Analytics Integration
Use the statistics API for:
- User dashboard analytics
- Cost tracking and budget alerts
- Usage pattern analysis
- Billing reconciliation

## Integration Examples

### Complete Billing Workflow

```javascript
async function processAIRequest(userId, requestData) {
  let usageId = null;
  
  try {
    // 1. Process AI request
    const aiResponse = await callAIService(requestData);
    
    // 2. Record usage (for analytics)
    const usageRecord = await recordUsage({
      user_id: userId,
      ...calculateUsageMetrics(aiResponse)
    });
    usageId = usageRecord.data.id;
    
    // 3. Consume credits (for billing)
    await consumeCredits(userId, usageRecord.data.credits_charged);
    
    return aiResponse;
    
  } catch (error) {
    // If credit consumption fails, mark usage as failed
    if (usageId) {
      await updateUsageStatus(usageId, 'failed');
    }
    throw error;
  }
}
```

### Analytics Dashboard Data

```javascript
async function getUserAnalytics(userId, dateRange) {
  const [usageStats, creditTransactions] = await Promise.all([
    getUserUsageStats(userId, dateRange),
    getCreditTransactions(userId, dateRange)
  ]);
  
  return {
    usage: usageStats.data,
    billing: creditTransactions.data,
    efficiency: calculateEfficiency(usageStats, creditTransactions)
  };
}
```

## Error Handling

### Common Error Responses

```json
// 401 Unauthorized
{
  "detail": "Could not validate credentials"
}

// 422 Validation Error
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "user_id"],
      "msg": "Field required"
    }
  ]
}

// 404 Not Found
{
  "success": false,
  "message": "User not found"
}
```

### HTTP Status Codes
- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: User or resource not found
- `422 Unprocessable Entity`: Validation errors
- `500 Internal Server Error`: Server error

## Related APIs

- [Credit Management API](how_to_user_credit.md) - For credit consumption
- [Session Management API](how_to_user_api.md#-会话管理-api) - For session tracking
- [User Management API](how_to_user_api.md) - For user operations

---

**📝 Last Updated**: 2025-09-06 | API Version: v1.0 | Status: ✅ Tested and Verified