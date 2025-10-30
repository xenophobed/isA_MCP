# Context 序列化问题 - 完整解决方案

## 问题现象

```
Error executing tool: Object of type Context is not JSON serializable
```

## 根本原因

**`@wraps(func)` 保留了原函数的 `__annotations__`，其中包含 `ctx: Context` 类型注解。**

FastMCP 在处理工具时：
1. 读取函数的 `__annotations__` 来生成 schema
2. 看到 `ctx: Context` 类型注解
3. 尝试序列化 Context 对象（即使返回值中没有）
4. 失败：Context 不可序列化

## 解决方案

### 核心修改（`tools/base_tool.py:898-913`）

```python
# CRITICAL: Remove Context from type annotations to prevent serialization
# FastMCP reads __annotations__ to generate schema, but Context type causes serialization issues
if hasattr(wrapped_func, '__annotations__'):
    # Create a clean copy of annotations without Context types
    clean_annotations = {}
    for param_name, param_type in wrapped_func.__annotations__.items():
        # Skip Context types entirely
        if 'Context' not in str(param_type):
            clean_annotations[param_name] = param_type
        # For ctx parameter, use Any instead of Context
        elif param_name == 'ctx':
            from typing import Any
            clean_annotations[param_name] = Any

    wrapped_func.__annotations__ = clean_annotations
    logger.debug(f"Cleaned Context from annotations for '{func.__name__}'")
```

### 为什么有效

1. ✅ 保留 `@wraps(func)` - FastMCP 需要完整函数签名来解析参数
2. ✅ 清除 Context 类型注解 - 防止 FastMCP 尝试序列化 Context
3. ✅ 使用 `Any` 类型 - FastMCP 仍然知道有 `ctx` 参数，会正常注入 Context
4. ✅ 工具代码不变 - 仍然可以使用 `ctx: Context` 编写工具

## 验证结果

### ✅ 测试 1: Context 信息提取工具

```bash
curl -X POST http://localhost:8081/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"test_context_info","arguments":{"test_message":"Test"}}}'
```

**结果：** ✅ 成功
```json
{
  "status": "success",
  "data": {
    "context_extracted": {
      "request_id": null,
      "client_id": null,
      "session_id": null,
      "timestamp": "2025-10-19T09:31:54.598286"
    }
  }
}
```

### ✅ 测试 2: Weather 工具

```bash
curl -X POST http://localhost:8081/mcp \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_weather","arguments":{"city":"Beijing"}}}'
```

**结果：** ✅ 成功
```json
{
  "status": "success",
  "data": {
    "city": "Beijing",
    "current": {...}
  }
}
```

## 优化总结

### 代码简化

| 组件 | 优化前 | 优化后 | 减少 |
|------|--------|--------|------|
| `register_tool()` wrapper | ~180 行 | ~60 行 | **-120 行** |
| `create_response()` | ~50 行 | ~30 行 | **-20 行** |
| **总计** | **~230 行** | **~90 行** | **-140 行 (-61%)** |

### 新增功能

#### 1. `extract_context_info()` 方法

安全提取 Context 中的可序列化信息：

```python
def extract_context_info(self, ctx: Optional[Context]) -> Dict[str, Any]:
    """
    从 Context 中提取可序列化的信息

    Returns:
        {
            "request_id": str | None,
            "client_id": str | None,
            "session_id": str | None,
            "timestamp": str
        }
    """
```

**使用示例：**

```python
from tools.base_tool import BaseTool
from mcp.server.fastmcp import Context

class MyTool(BaseTool):
    async def my_tool(
        self,
        data: str,
        ctx: Context = None  # FastMCP 自动注入
    ) -> Dict[str, Any]:
        # 使用 Context 进行日志和进度报告
        await self.log_info(ctx, "Processing...")
        await self.report_progress(ctx, 1, 3)

        # 提取 Context 信息（可序列化）
        context_info = self.extract_context_info(ctx)

        # 返回业务数据 + Context 元数据
        return self.create_response(
            status="success",
            action="my_tool",
            data={
                "result": process(data),
                "context": context_info  # ✅ 可序列化
            }
        )
```

#### 2. 简化的 `create_response()`

不再需要复杂的序列化逻辑，直接返回字典：

```python
def create_response(
    self,
    status: str,
    action: str,
    data: Dict[str, Any],
    error_message: Optional[str] = None
) -> Dict[str, Any]:
    """创建统一格式的响应（返回可序列化的字典）"""
    if status == "success":
        return {
            "status": "success",
            "action": action,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "status": "error",
            "action": action,
            "error": error_message or "Unknown error",
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
```

#### 3. Context 类型注解清理

自动清除 `__annotations__` 中的 Context 类型，防止序列化问题。

### 关键原则

> **Context 只用于操作，永远不要返回**

✅ **正确用法：**
- 使用 Context 进行：日志、进度报告、资源访问、LLM 采样
- 使用 `extract_context_info(ctx)` 提取元数据
- 返回可 JSON 序列化的数据

❌ **错误用法：**
- 返回 Context 对象本身
- 返回包含 Context 的数据结构

## FastMCP Context API 参考

### Context 可用方法

| 方法 | 用途 |
|------|------|
| `ctx.report_progress(progress, total, message)` | 进度报告 |
| `ctx.info(message)` | 记录日志 |
| `ctx.debug(message)` | 调试日志 |
| `ctx.warning(message)` | 警告日志 |
| `ctx.error(message)` | 错误日志 |
| `ctx.read_resource(uri)` | 读取资源 |
| `ctx.sample(messages)` | LLM 采样 |

### Context 可提取属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `ctx.request_id` | `str \| None` | 请求唯一 ID |
| `ctx.client_id` | `str \| None` | 客户端 ID |
| `ctx.session_id` | `str \| None` | 会话 ID (HTTP only) |

## 文件变更清单

### 修改的文件

1. **`tools/base_tool.py`**
   - 添加 `extract_context_info()` 方法
   - 简化 `create_response()` 方法
   - 优化 `register_tool()` wrapper（-120 行）
   - 添加 Context 类型注解清理逻辑

### 新增的文件

1. **`tools/test_tools/context_test_tools.py`**
   - Context 信息提取测试工具
   - 验证序列化功能

## 测试checklist

- [x] 直接调用工具函数
- [x] HTTP 调用工具（通过 FastMCP）
- [x] Context 信息提取
- [x] Context 信息序列化
- [x] Weather 工具测试
- [x] 所有返回值可 JSON 序列化

## 参考文档

- [FastMCP Context API](https://gofastmcp.com/servers/context)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

---

**优化日期：** 2025-10-19
**问题状态：** ✅ 已解决
**测试状态：** ✅ 所有测试通过
