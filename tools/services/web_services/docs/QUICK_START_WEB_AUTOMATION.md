# Web Automation Tools - 快速使用指南 🚀

## 🎯 5 分钟上手

### 1. 注册工具到 MCP Server

在 `main.py` 中添加：

```python
# 在文件顶部导入
from tools.services.web_services.tools.web_automation_tools import register_web_automation_tools

# 在工具注册部分添加
register_web_automation_tools(mcp)
```

**完整示例：**
```python
# main.py
from mcp.server.fastmcp import FastMCP

# 导入所有工具注册函数
from tools.services.web_services.tools.web_search_tools import register_web_search_tools
from tools.services.web_services.tools.web_automation_tools import register_web_automation_tools

# 创建 MCP 服务器
mcp = FastMCP("isA_MCP")

# 注册工具
register_web_search_tools(mcp)      # Web Search
register_web_automation_tools(mcp)  # Web Automation (新增)

# 启动服务器
if __name__ == "__main__":
    mcp.run()
```

---

### 2. 启动 MCP Server

```bash
# 启动服务器
python main.py

# 看到以下输出表示成功：
# ✅ Web Automation Tools registered: 1 enhanced function
# 🤖 web_automation: 5-step workflow + HIL support + progress tracking
```

---

### 3. 运行测试

```bash
# 进入测试目录
cd tools/services/web_services/tests

# 添加执行权限
chmod +x test_web_automation.sh

# 运行测试
./test_web_automation.sh

# 预期输出：
# ✅ All tests passed! 🎉
# Test results saved to: ./results/automation_YYYYMMDD_HHMMSS/
```

---

## 📝 基本使用示例

### 示例 1: 简单搜索

```python
# Python 调用
result = await web_automation(
    url="https://www.google.com",
    task="search for python programming"
)

# 进度输出：
# [📸 CAPTURE] Stage 1/5 (20%): Capturing - loading https://www.google.com
# [🧠 UNDERSTAND] Stage 2/5 (40%): Understanding - search_page (2 elements)
# [🎯 DETECT] Stage 3/5 (60%): Detecting - 3 elements mapped
# [🤖 PLAN] Stage 4/5 (80%): Planning - 3 actions generated (llm)
# [⚡ EXECUTE] Stage 5/5 (100%): Executing - action 1/3 (click)
# [⚡ EXECUTE] Stage 5/5 (100%): Executing - action 2/3 (type)
# [⚡ EXECUTE] Stage 5/5 (100%): Executing - action 3/3 (press)
# [✅ DONE] Web Automation complete | actions_executed=3, task_completed=True

# 返回结果：
{
    "status": "success",
    "action": "web_automation",
    "data": {
        "success": true,
        "initial_url": "https://www.google.com",
        "final_url": "https://www.google.com/search?q=python+programming",
        "task": "search for python programming",
        "workflow_results": {
            "step5_execution": {
                "actions_executed": 3,
                "actions_successful": 3,
                "task_completed": true
            }
        }
    }
}
```

### 示例 2: 表单填写

```python
result = await web_automation(
    url="https://example.com/contact",
    task="fill name 'John Doe', email 'john@example.com', message 'Hello', click submit"
)

# 自动执行：
# 1. 分析表单结构
# 2. 定位输入框
# 3. 填写内容
# 4. 点击提交
```

### 示例 3: 多步骤工作流

```python
result = await web_automation(
    url="https://www.amazon.com",
    task="search for 'wireless headphones', filter by prime, select first result"
)

# 自动执行多个动作：
# - 点击搜索框
# - 输入关键词
# - 点击搜索按钮
# - 筛选 Prime
# - 点击第一个结果
```

---

## 🤚 HIL (Human-in-Loop) 使用

### 场景 1: 登录（有凭证）

```python
result = await web_automation(
    url="https://accounts.google.com/signin",
    task="login to gmail",
    user_id="user123"  # 重要：用于 Vault 查询
)

# 如果 Vault 中有凭证，返回：
{
    "status": "authorization_required",
    "action": "request_authorization",
    "message": "Found stored credentials for Google. Do you authorize using them?",
    "data": {
        "intervention_type": "login",
        "provider": "google",
        "credential_preview": {
            "vault_id": "vault_google_123"
        }
    }
}

# Agent 处理流程：
# 1. 询问用户："是否使用 Vault 中的 Google 凭证？"
# 2. 用户同意 → 从 Vault 获取完整凭证
# 3. 重新调用 web_automation（带凭证）
# 4. 完成登录
```

### 场景 2: 登录（无凭证）

```python
result = await web_automation(
    url="https://github.com/login",
    task="login to github",
    user_id="user123"
)

# 如果 Vault 中无凭证，返回：
{
    "status": "credential_required",
    "action": "ask_human",
    "message": "No stored credentials found for GitHub. Please provide login credentials.",
    "data": {
        "intervention_type": "login",
        "provider": "github",
        "instructions": "Please click the OAuth button or enter credentials manually"
    }
}

# Agent 处理流程：
# 1. 提示用户："需要 GitHub 登录，请手动登录"
# 2. 用户完成登录
# 3. 询问："是否保存凭证到 Vault？"
# 4. 继续任务
```

### 场景 3: CAPTCHA

```python
result = await web_automation(
    url="https://example.com/search",
    task="search for something"
)

# 遇到 CAPTCHA，返回：
{
    "status": "human_required",
    "action": "ask_human",
    "message": "CAPTCHA detected. Please solve the CAPTCHA manually.",
    "data": {
        "intervention_type": "captcha",
        "screenshot": "/tmp/captcha_screenshot.png",
        "instructions": "Please solve the CAPTCHA and notify when complete"
    }
}

# Agent 处理流程：
# 1. 显示截图给用户
# 2. 提示："请解决 CAPTCHA"
# 3. 等待用户确认完成
# 4. 重新调用 web_automation 继续任务
```

---

## 🎨 进度跟踪

### 5步工作流进度

```python
# 使用 MCP Context 自动报告进度
async def my_automation_task(ctx: Context):
    result = await web_automation(
        url="https://example.com",
        task="do something",
        ctx=ctx  # 传入 Context
    )
    
    # MCP 客户端会收到以下进度通知：
    # Progress 1/5: Capturing
    # Progress 2/5: Understanding
    # Progress 3/5: Detecting
    # Progress 4/5: Planning
    # Progress 5/5: Executing
```

### 日志输出

```
[📸 CAPTURE] Stage 1/5 (20%): Capturing - loading https://example.com
[🧠 UNDERSTAND] Stage 2/5 (40%): Understanding - search_page (2 elements required)
[🎯 DETECT] Stage 3/5 (60%): Detecting - 3 elements mapped
[🤖 PLAN] Stage 4/5 (80%): Planning - 5 actions generated (llm)
[⚡ EXECUTE] Stage 5/5 (100%): Executing - action 1/5 (click)
[⚡ EXECUTE] Stage 5/5 (100%): Executing - action 2/5 (type)
[⚡ EXECUTE] Stage 5/5 (100%): Executing - action 3/5 (scroll)
[⚡ EXECUTE] Stage 5/5 (100%): Executing - action 4/5 (hover)
[⚡ EXECUTE] Stage 5/5 (100%): Executing - action 5/5 (press)
[⚡ EXECUTE] Stage 5/5 (100%): Executing - completed: 5/5 successful, 0 failed
[✅ DONE] Web Automation complete | actions_executed=5, task_completed=True
```

---

## 🔧 高级用法

### 自定义 User ID

```python
# 为不同用户使用不同的凭证
result = await web_automation(
    url="https://accounts.google.com",
    task="login",
    user_id="alice@example.com"  # 查询 Alice 的凭证
)

result = await web_automation(
    url="https://accounts.google.com",
    task="login",
    user_id="bob@example.com"  # 查询 Bob 的凭证
)
```

### 复杂任务描述

```python
# 任务描述支持自然语言
result = await web_automation(
    url="https://www.amazon.com",
    task="""
    1. Search for 'wireless keyboard'
    2. Filter by 4+ stars rating
    3. Filter by Prime shipping
    4. Sort by price low to high
    5. Click the first result
    6. Take a screenshot
    """
)
```

### 条件操作

```python
result = await web_automation(
    url="https://example.com/form",
    task="if there is a name field, fill it with 'John', otherwise skip"
)
```

---

## 📊 监控和调试

### 查看执行日志

```python
# 所有进度都会记录到日志
import logging
logging.basicConfig(level=logging.INFO)

# 运行自动化
result = await web_automation(...)

# 查看日志输出
# [INFO] 🚀 Starting web automation: 'search for python' on https://google.com
# [INFO] [📸 CAPTURE] Stage 1/5 (20%): Capturing - loading...
# ...
```

### 检查执行结果

```python
result = await web_automation(
    url="https://example.com",
    task="search for something"
)

# 检查是否成功
if result["status"] == "success":
    workflow = result["data"]["workflow_results"]
    
    # 查看每步结果
    print(f"Step 2 Analysis: {workflow['step2_analysis']}")
    print(f"Step 3 UI Detection: {workflow['step3_ui_detection']}")
    print(f"Step 4 Actions: {workflow['step4_actions']}")
    
    # 查看执行详情
    execution = workflow["step5_execution"]
    print(f"Actions executed: {execution['actions_executed']}")
    print(f"Actions successful: {execution['actions_successful']}")
    print(f"Task completed: {execution['task_completed']}")
```

### 调试失败任务

```python
result = await web_automation(
    url="https://example.com",
    task="do something"
)

if result["status"] == "error":
    print(f"Error: {result['error_message']}")
    
    # 查看截图
    if "data" in result and "workflow_results" in result["data"]:
        screenshot = result["data"]["workflow_results"].get("step1_screenshot")
        print(f"Initial screenshot: {screenshot}")
```

---

## ⚡ 性能优化建议

### 1. 批量任务

```python
# 不推荐：串行执行
for url in urls:
    result = await web_automation(url, task)

# 推荐：并发执行
tasks = [web_automation(url, task) for url in urls]
results = await asyncio.gather(*tasks)
```

### 2. 重用 Session（由 Agent 层处理）

```python
# MCP 工具层每次调用都是独立 session
# 如需保持登录状态，由 Agent 层管理：
# 1. 第一次调用触发 HIL 登录
# 2. Agent 保存 session/cookie
# 3. 后续调用使用相同 session
```

### 3. 超时设置

```python
# 当前固定超时（60秒页面加载 + 执行时间）
# 如需自定义，修改 WebAutomationService
```

---

## 🐛 常见问题

### Q1: 进度不显示？

**A:** 确保传入了 `ctx` 参数：
```python
result = await web_automation(url, task, ctx=ctx)
```

### Q2: HIL 一直不触发？

**A:** 检查：
1. 页面是否真的需要登录（有些网站无需登录）
2. Vision Model 是否正确识别（查看日志）
3. user_id 是否传入

### Q3: 动作执行失败？

**A:** 查看执行日志：
```python
execution_log = result["data"]["workflow_results"]["step5_execution"]["execution_log"]
print(execution_log)

# 常见原因：
# - 元素定位不准确
# - 页面加载太慢
# - 网站结构改变
```

### Q4: 如何添加新的 action type？

**A:** 参考 `strategies/actions/` 目录：
1. 创建新的 action strategy 文件
2. 实现 `ActionStrategy` 接口
3. 注册到 `ActionExecutor`

---

## 📚 相关文档

- [完整实现文档](./WEB_AUTOMATION_TOOLS_IMPLEMENTATION.md)
- [HIL 流程图](./HIL_FLOW_DIAGRAM.md)
- [HIL 实现总结](./HIL_IMPLEMENTATION_SUMMARY.md)
- [Web 自动化增强](./web_automation_enhance.md)
- [测试脚本](./tests/test_web_automation.sh)

---

## 🎉 开始使用

```bash
# 1. 注册工具（在 main.py）
# 2. 启动服务器
python main.py

# 3. 运行测试
cd tools/services/web_services/tests
./test_web_automation.sh

# 4. 开始使用
# 在你的 Agent 或应用中调用 web_automation 工具
```

**Happy Automating! 🤖**

