#!/usr/bin/env python3
"""
Test Security Level Integration with Search Service
测试安全等级与搜索服务的集成
"""

import asyncio
import json
from core.search_service import UnifiedSearchService
from core.security import SecurityPolicy, SecurityLevel

async def test_security_integration():
    """测试安全等级与搜索服务的集成"""
    print("🔒 测试安全等级与搜索服务集成")
    print("="*60)
    
    # 创建搜索服务实例
    search_service = UnifiedSearchService()
    
    # 初始化（不需要MCP服务器，我们手动填充测试数据）
    await search_service.initialize(fallback_mode=True)
    
    # 手动添加一些测试工具数据
    test_tools = {
        'remember_fact': {
            'name': 'remember_fact',
            'description': 'Store a new factual memory',
            'type': 'tool',
            'category': 'memory',
            'keywords': ['memory', 'store', 'fact'],
            'metadata': {
                'security_level': 'MEDIUM',
                'security_level_value': 2,
                'requires_authorization': True
            }
        },
        'forget_memory': {
            'name': 'forget_memory',
            'description': 'Delete a memory permanently',
            'type': 'tool',
            'category': 'memory',
            'keywords': ['memory', 'delete', 'forget'],
            'metadata': {
                'security_level': 'HIGH',
                'security_level_value': 3,
                'requires_authorization': True
            }
        },
        'get_weather': {
            'name': 'get_weather',
            'description': 'Get current weather information',
            'type': 'tool',
            'category': 'weather',
            'keywords': ['weather', 'forecast', 'temperature'],
            'metadata': {
                'security_level': 'LOW',
                'security_level_value': 1,
                'requires_authorization': False
            }
        },
        'admin_reset': {
            'name': 'admin_reset',
            'description': 'Reset system configuration (admin only)',
            'type': 'tool',
            'category': 'admin',
            'keywords': ['admin', 'reset', 'system'],
            'metadata': {
                'security_level': 'CRITICAL',
                'security_level_value': 4,
                'requires_authorization': True
            }
        },
        'calculate': {
            'name': 'calculate',
            'description': 'Perform mathematical calculations',
            'type': 'tool',
            'category': 'general',
            'keywords': ['math', 'calculate', 'compute'],
            'metadata': {
                'security_level': 'MEDIUM',
                'security_level_value': 2,
                'requires_authorization': True
            }
        }
    }
    
    # 填充测试数据到缓存
    search_service.capabilities_cache['tools'] = test_tools
    
    print("📊 测试数据加载完成")
    print(f"   加载了 {len(test_tools)} 个测试工具")
    print()
    
    # 测试1: 获取所有工具的安全等级
    print("🔍 测试1: 获取所有工具的安全等级")
    security_levels = await search_service.get_tool_security_levels()
    
    print("📋 安全等级统计:")
    summary = security_levels.get('summary', {})
    for level, count in summary.get('security_levels', {}).items():
        print(f"   {level}: {count} 个工具")
    
    print(f"\n📊 需要授权的工具: {summary.get('authorization_required', 0)} 个")
    print()
    
    # 测试2: 按安全等级搜索
    print("🔍 测试2: 按安全等级搜索工具")
    
    for level in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
        results = await search_service.search_by_security_level(level)
        print(f"   {level} 级别: {len(results)} 个工具")
        for result in results:
            auth_status = "需要授权" if result.metadata.get('requires_authorization') else "无需授权"
            print(f"     - {result.name}: {result.description[:50]}... ({auth_status})")
    print()
    
    # 测试3: 搜索结果中的安全等级信息
    print("🔍 测试3: 搜索结果中的安全等级信息")
    
    # 搜索内存相关工具
    memory_results = await search_service.search("memory", max_results=10)
    print(f"   搜索 'memory' 找到 {len(memory_results)} 个结果:")
    
    for result in memory_results:
        metadata = result.metadata
        security_level = metadata.get('security_level', 'UNKNOWN')
        requires_auth = metadata.get('requires_authorization', False)
        
        print(f"     - {result.name}")
        print(f"       安全等级: {security_level}")
        print(f"       需要授权: {'是' if requires_auth else '否'}")
        print(f"       相似度: {result.similarity_score:.3f}")
        print()
    
    # 测试4: 详细的安全策略信息
    print("🔍 测试4: 详细的安全策略信息")
    
    print("📋 工具安全策略详情:")
    tools_info = security_levels.get('tools', {})
    
    # 按安全等级分组显示
    levels_groups = {
        'LOW': [],
        'MEDIUM': [],
        'HIGH': [],
        'CRITICAL': [],
        'DEFAULT': []
    }
    
    for tool_name, tool_info in tools_info.items():
        level = tool_info.get('security_level', 'DEFAULT')
        levels_groups[level].append(tool_info)
    
    for level, tools in levels_groups.items():
        if tools:
            print(f"\n   {level} 级别工具 ({len(tools)} 个):")
            for tool in tools:
                auth_indicator = "🔒" if tool['requires_authorization'] else "🔓"
                print(f"     {auth_indicator} {tool['name']} - {tool['category']}")
    
    print()
    print("✅ 安全等级集成测试完成")
    
    return {
        'security_levels': security_levels,
        'search_results': memory_results,
        'test_passed': True
    }

async def test_security_policy_access():
    """测试直接访问安全策略"""
    print("🔐 测试直接访问安全策略")
    print("="*60)
    
    policy = SecurityPolicy()
    
    print("📋 当前安全策略:")
    for tool_name, level in policy.tool_policies.items():
        print(f"   {tool_name}: {level.name} ({level.value})")
    
    print(f"\n📊 频率限制策略:")
    for tool_name, limits in policy.rate_limits.items():
        print(f"   {tool_name}: {limits['calls']} 次/{limits['window']}秒")
    
    print(f"\n🚫 禁止模式 ({len(policy.forbidden_patterns)} 个):")
    for i, pattern in enumerate(policy.forbidden_patterns[:3], 1):
        print(f"   {i}. {pattern}")
    print("   ...")
    
    print()

if __name__ == "__main__":
    async def main():
        await test_security_policy_access()
        print()
        result = await test_security_integration()
        
        # 保存测试结果
        with open('/tmp/security_test_results.json', 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print("📄 测试结果已保存到: /tmp/security_test_results.json")
    
    asyncio.run(main())