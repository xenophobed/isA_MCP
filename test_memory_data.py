#!/usr/bin/env python3
"""
测试脚本：向记忆系统添加一些示例数据
"""
import asyncio
import json
import sys
import os

# 添加项目根目录到path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.memory_tools import _memory_manager

async def populate_test_data():
    """填充测试数据"""
    print("🧠 开始添加测试记忆数据...")
    
    user_id = "anonymous"  # 使用已存在的用户的user_id字段
    
    try:
        # 验证用户存在
        print("👤 验证用户...")
        supabase = _memory_manager.supabase
        existing_user = supabase.table('users').select('*').eq('user_id', user_id).execute()
        if existing_user.data:
            print(f"✅ 用户存在: {existing_user.data[0]['name']} (ID: {user_id})")
        else:
            print(f"❌ 用户不存在，请检查用户ID")
            return
        # 1. 添加事实记忆
        print("\n📚 添加事实记忆...")
        
        facts = [
            {
                "fact_type": "personal_info",
                "subject": "张三",
                "predicate": "职业是",
                "object_value": "软件工程师",
                "context": "全栈开发，专长Python和React",
                "confidence": 0.9
            },
            {
                "fact_type": "knowledge",
                "subject": "Python",
                "predicate": "是一种",
                "object_value": "编程语言",
                "context": "高级、解释型、通用型编程语言",
                "confidence": 1.0
            },
            {
                "fact_type": "preference",
                "subject": "张三",
                "predicate": "喜欢",
                "object_value": "喝咖啡",
                "context": "每天早上必须喝一杯美式咖啡",
                "confidence": 0.8
            },
            {
                "fact_type": "skill",
                "subject": "张三",
                "predicate": "掌握",
                "object_value": "机器学习",
                "context": "有3年ML项目经验，熟悉深度学习",
                "confidence": 0.85
            }
        ]
        
        for fact in facts:
            result = await _memory_manager.store_factual_memory(
                user_id=user_id,
                **fact
            )
            print(f"✅ 存储事实: {fact['subject']} {fact['predicate']} {fact['object_value']}")
        
        # 2. 添加程序记忆
        print("\n⚙️ 添加程序记忆...")
        
        procedures = [
            {
                "procedure_name": "部署Python应用",
                "domain": "软件开发",
                "trigger_conditions": {"环境": "生产环境", "语言": "Python"},
                "steps": [
                    {"step": 1, "action": "运行测试", "command": "pytest"},
                    {"step": 2, "action": "构建镜像", "command": "docker build"},
                    {"step": 3, "action": "推送到仓库", "command": "docker push"},
                    {"step": 4, "action": "部署到K8s", "command": "kubectl apply"}
                ],
                "expected_outcome": "应用成功部署到生产环境",
                "difficulty_level": 3,
                "estimated_time_minutes": 30
            },
            {
                "procedure_name": "冲咖啡",
                "domain": "日常生活",
                "trigger_conditions": {"时间": "早上", "状态": "疲惫"},
                "steps": [
                    {"step": 1, "action": "准备咖啡豆", "description": "选择中度烘焙豆子"},
                    {"step": 2, "action": "研磨咖啡豆", "description": "中等粗细度"},
                    {"step": 3, "action": "加热水", "temperature": "92-96°C"},
                    {"step": 4, "action": "冲泡", "time": "4分钟"}
                ],
                "expected_outcome": "一杯美味的手冲咖啡",
                "difficulty_level": 2,
                "estimated_time_minutes": 15
            }
        ]
        
        for proc in procedures:
            result = await _memory_manager.store_procedural_memory(
                user_id=user_id,
                **proc
            )
            print(f"✅ 存储程序: {proc['procedure_name']}")
        
        # 3. 添加情景记忆
        print("\n🎬 添加情景记忆...")
        
        episodes = [
            {
                "episode_title": "第一次使用ISA MCP系统",
                "summary": "初次体验智能MCP服务器，学习了记忆管理功能",
                "key_events": [
                    {"time": "09:00", "event": "启动MCP服务器"},
                    {"time": "09:15", "event": "测试store_fact工具"},
                    {"time": "09:30", "event": "发现billing功能很有用"},
                    {"time": "10:00", "event": "成功存储第一条记忆"}
                ],
                "occurred_at": "2024-12-20T09:00:00",
                "participants": ["张三", "ISA系统"],
                "location": "家里办公室",
                "emotional_context": "兴奋和好奇",
                "emotional_intensity": 0.8,
                "lessons_learned": "MCP工具很强大，可以大大提高开发效率"
            },
            {
                "episode_title": "解决复杂bug的经历",
                "summary": "花了整个下午调试一个诡异的内存泄漏问题",
                "key_events": [
                    {"time": "14:00", "event": "发现系统内存使用异常"},
                    {"time": "15:30", "event": "使用profiler定位问题"},
                    {"time": "17:00", "event": "找到循环引用的root cause"},
                    {"time": "17:30", "event": "修复问题并验证"}
                ],
                "occurred_at": "2024-12-19T14:00:00",
                "participants": ["张三"],
                "location": "公司",
                "emotional_context": "最初困扰，后来成就感",
                "emotional_intensity": 0.7,
                "lessons_learned": "复杂问题需要系统性的调试方法，工具很重要"
            }
        ]
        
        for episode in episodes:
            # 转换occurred_at为datetime对象
            from datetime import datetime
            episode['occurred_at'] = datetime.fromisoformat(episode['occurred_at'].replace('Z', '+00:00'))
            
            result = await _memory_manager.store_episodic_memory(
                user_id=user_id,
                **episode
            )
            print(f"✅ 存储情景: {episode['episode_title']}")
        
        # 4. 添加语义记忆
        print("\n🧠 添加语义记忆...")
        
        concepts = [
            {
                "concept_name": "MCP",
                "concept_category": "技术协议",
                "definition": "Model Context Protocol，一种让AI模型与外部工具交互的标准协议",
                "properties": {
                    "类型": "通信协议",
                    "用途": "AI工具集成",
                    "优势": "标准化、可扩展"
                },
                "related_concepts": ["AI", "工具集成", "API", "JSON-RPC"],
                "use_cases": ["AI助手增强", "工具链集成", "自动化任务"],
                "examples": ["Claude MCP", "智能客服", "自动化运维"],
                "mastery_level": 0.7
            },
            {
                "concept_name": "向量数据库",
                "concept_category": "数据库技术",
                "definition": "专门用于存储和检索高维向量数据的数据库系统",
                "properties": {
                    "维度": "高维",
                    "检索方式": "相似度搜索",
                    "应用": "AI和机器学习"
                },
                "related_concepts": ["嵌入", "相似度检索", "AI", "机器学习"],
                "use_cases": ["语义搜索", "推荐系统", "图像检索"],
                "examples": ["Pinecone", "Weaviate", "Supabase pgvector"],
                "mastery_level": 0.6
            },
            {
                "concept_name": "认知科学",
                "concept_category": "学科领域",
                "definition": "研究心智和认知过程的跨学科科学领域",
                "properties": {
                    "研究对象": "认知过程",
                    "方法": "跨学科",
                    "应用": "AI和教育"
                },
                "related_concepts": ["心理学", "神经科学", "人工智能", "哲学"],
                "use_cases": ["AI系统设计", "教育技术", "人机交互"],
                "examples": ["记忆模型", "学习理论", "认知负荷"],
                "mastery_level": 0.5
            }
        ]
        
        for concept in concepts:
            result = await _memory_manager.store_semantic_memory(
                user_id=user_id,
                **concept
            )
            print(f"✅ 存储语义: {concept['concept_name']}")
        
        print(f"\n🎉 成功为用户 {user_id} 添加了所有测试数据！")
        
        # 5. 获取统计信息
        print("\n📊 获取记忆统计...")
        stats = await _memory_manager.get_memory_statistics(user_id)
        print(f"统计结果: {json.dumps(stats, indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(populate_test_data())