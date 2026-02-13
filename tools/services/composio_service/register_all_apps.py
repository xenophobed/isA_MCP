#!/usr/bin/env python3
"""
Script to register ALL 745 Composio apps as MCP tools
或者注册特定类别的应用
"""

import asyncio
import json
from typing import List, Optional


# 方案1：修改 composio_mcp_bridge.py 的简单配置
def update_bridge_config(apps_to_register: Optional[List[str]] = None, register_all: bool = False):
    """
    更新 composio_mcp_bridge.py 中的 priority_apps 列表

    Args:
        apps_to_register: 要注册的应用列表，如果为None则使用默认值
        register_all: 如果为True，注册所有745个应用
    """

    if register_all:
        # 方案A：注册所有应用（性能影响大）
        config = """
                # Register ALL apps as individual tools
                # WARNING: This will create 1490+ tools (2 tools per app)
                for app in apps:
                    app_name = app.get("name", "").lower()
                    await self._register_app_as_tools(mcp, app, security_manager)
        """
        print("⚠️  警告：注册745个应用将创建1490+个工具，可能影响性能！")

    elif apps_to_register:
        # 方案B：注册指定的应用列表
        config = f"""
                # Register selected apps as individual tools
                priority_apps = {apps_to_register}
                
                for app in apps:
                    app_name = app.get("name", "").lower()
                    if app_name in priority_apps:
                        await self._register_app_as_tools(mcp, app, security_manager)
        """
    else:
        # 方案C：按类别注册
        config = """
                # Register apps by category
                categories_to_register = ["communication", "productivity", "development", "crm"]
                
                # Get apps by category (需要先实现分类逻辑)
                for app in apps:
                    app_name = app.get("name", "").lower()
                    app_category = self._get_app_category(app_name)  # 需要实现
                    if app_category in categories_to_register:
                        await self._register_app_as_tools(mcp, app, security_manager)
        """

    return config


# 方案2：创建批量注册函数
async def batch_register_composio_apps():
    """
    批量注册Composio应用的更智能方法
    """

    import sys
    import os

    sys.path.append("/Users/xenodennis/Documents/Fun/isA_MCP")

    from tools.mcp_client import MCPClient

    client = MCPClient()

    # 1. 获取所有可用应用
    print("📋 获取所有可用的Composio应用...")
    result = await client.call_tool_and_parse("composio_list_available_apps", {})

    if result.get("status") != "success":
        print(f"❌ 无法获取应用列表: {result}")
        return

    total_apps = result.get("total_apps", 0)
    categories = result.get("categories", {})

    print(f"\n📊 发现 {total_apps} 个应用，分布在以下类别：")
    for category, apps in categories.items():
        if apps:
            print(f"  • {category}: {len(apps)} 个应用")

    # 2. 智能选择要注册的应用
    print("\n🎯 推荐的注册策略：")

    # 高优先级应用（最常用）
    high_priority = [
        # 通信类
        "gmail",
        "slack",
        "discord",
        "telegram",
        "whatsapp",
        "teams",
        # 生产力
        "notion",
        "asana",
        "trello",
        "todoist",
        "googlecalendar",
        "airtable",
        # 开发工具
        "github",
        "gitlab",
        "bitbucket",
        "jira",
        "linear",
        "vercel",
        # CRM & 营销
        "hubspot",
        "salesforce",
        "mailchimp",
        "sendgrid",
        # 存储
        "googledrive",
        "dropbox",
        "onedrive",
        "box",
        # AI & 数据
        "openai",
        "anthropic",
        "pinecone",
        # 社交媒体
        "twitter",
        "linkedin",
        "facebook",
        "instagram",
    ]

    # 中优先级应用（有用但不常用）
    medium_priority = [
        "zoom",
        "meet",
        "calendly",
        "typeform",
        "stripe",
        "paypal",
        "shopify",
        "wordpress",
        "medium",
        "substack",
        "convertkit",
    ]

    return {
        "total_apps": total_apps,
        "high_priority": high_priority,
        "medium_priority": medium_priority,
        "recommendation": f"""
推荐的注册方案：

1. 【保守方案】只注册高优先级应用（约35个）
   - 覆盖90%的常用场景
   - 创建约70个工具
   - 性能影响最小

2. 【平衡方案】注册高+中优先级应用（约50个）
   - 覆盖95%的使用场景
   - 创建约100个工具
   - 性能影响可接受

3. 【完整方案】注册所有745个应用
   - 100%覆盖
   - 创建1490+个工具
   - 可能影响启动速度和搜索性能

建议：从方案1开始，根据用户需求逐步添加
""",
    }


# 方案3：创建实际的修改脚本
def create_enhanced_bridge_file():
    """
    创建增强版的 composio_mcp_bridge.py
    支持配置化的应用注册
    """

    enhanced_code = """
# 在 composio_mcp_bridge.py 的第52行附近修改

# 从环境变量或配置文件读取要注册的应用
import os
import yaml

# 方法1：从环境变量读取
COMPOSIO_APPS_TO_REGISTER = os.environ.get('COMPOSIO_APPS_TO_REGISTER', '')
if COMPOSIO_APPS_TO_REGISTER == 'ALL':
    # 注册所有应用
    for app in apps:
        app_name = app.get("name", "").lower()
        await self._register_app_as_tools(mcp, app, security_manager)
        logger.info(f"  ✅ Registered {app_name}")
elif COMPOSIO_APPS_TO_REGISTER:
    # 注册指定的应用
    priority_apps = COMPOSIO_APPS_TO_REGISTER.split(',')
    for app in apps:
        app_name = app.get("name", "").lower()
        if app_name in priority_apps:
            await self._register_app_as_tools(mcp, app, security_manager)
else:
    # 默认注册列表
    priority_apps = ["gmail", "slack", "github", "notion", "googlecalendar"]
    for app in apps:
        app_name = app.get("name", "").lower()
        if app_name in priority_apps:
            await self._register_app_as_tools(mcp, app, security_manager)

# 方法2：从配置文件读取
try:
    with open('config/composio_apps.yaml', 'r') as f:
        config = yaml.safe_load(f)
        if config.get('register_all'):
            # 注册所有
            pass
        else:
            priority_apps = config.get('apps', [])
            # 注册指定应用
except FileNotFoundError:
    # 使用默认值
    pass
"""

    return enhanced_code


# 方案4：创建配置文件
def create_composio_config():
    """
    创建 Composio 应用注册配置文件
    """

    config = {
        "register_all": False,  # 是否注册所有应用
        "register_by_category": True,  # 按类别注册
        "categories": ["communication", "productivity", "development"],
        "apps": [
            # 通信类
            "gmail",
            "slack",
            "discord",
            "telegram",
            # 生产力
            "notion",
            "asana",
            "trello",
            "googlecalendar",
            # 开发
            "github",
            "gitlab",
            "jira",
            "linear",
            # CRM
            "hubspot",
            "salesforce",
            # 存储
            "googledrive",
            "dropbox",
            # AI
            "openai",
            "anthropic",
        ],
        "max_apps": 50,  # 最大注册数量限制
        "performance_mode": "balanced",  # fast | balanced | complete
    }

    config_path = (
        "/Users/xenodennis/Documents/Fun/isA_MCP/config/external_services/composio_apps.yaml"
    )

    import yaml

    yaml_content = yaml.dump(config, default_flow_style=False, sort_keys=False)

    print(f"配置文件内容：\n{yaml_content}")

    return config_path, yaml_content


if __name__ == "__main__":
    # 运行分析
    print("=" * 60)
    print("Composio 应用批量注册方案")
    print("=" * 60)

    # 获取推荐
    result = asyncio.run(batch_register_composio_apps())
    print(result["recommendation"])

    print("\n" + "=" * 60)
    print("实施步骤：")
    print("=" * 60)

    print("""
1. 修改 composio_mcp_bridge.py 第52行：
   
   # 原代码：
   priority_apps = ["gmail", "slack", "github", "notion", "googlecalendar"]
   
   # 新代码（注册更多应用）：
   priority_apps = [
       'gmail', 'slack', 'discord', 'telegram', 'whatsapp',
       'notion', 'asana', 'trello', 'googlecalendar', 'airtable',
       'github', 'gitlab', 'jira', 'linear',
       'hubspot', 'salesforce', 'mailchimp',
       'googledrive', 'dropbox', 'openai', 'anthropic'
   ]
   
2. 或者设置环境变量：
   export COMPOSIO_APPS_TO_REGISTER="gmail,slack,github,notion,asana,trello"
   
3. 或者注册所有应用（慎用）：
   export COMPOSIO_APPS_TO_REGISTER="ALL"
   
4. 重启MCP服务：
   ~/Documents/Fun/isA_Cloud/scripts/service_manager.sh restart mcp
""")
