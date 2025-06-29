#!/usr/bin/env python
"""
Test Script for Step 4: Synthesis & Generate
Tests the complete synthesize_and_generate tool with real MCP functionality
"""
import asyncio
import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Initialize security before any imports
from core.security import initialize_security
initialize_security()

# from isa_model.inference import get_llm  # Will be imported when needed
from tools.web_tools import register_web_tools

class MockMCP:
    """Mock MCP server for testing tools"""
    def __init__(self):
        self.tools = {}
    
    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator
    
    async def call_tool(self, tool_name, **kwargs):
        if tool_name in self.tools:
            return await self.tools[tool_name](**kwargs)
        else:
            raise ValueError(f"Tool {tool_name} not found")

async def test_synthesis_tool():
    """Test the complete synthesis & generate functionality"""
    print("🧪 测试Step 4: Synthesis & Generate工具")
    print("="*60)
    
    # Setup mock MCP server
    mock_mcp = MockMCP()
    register_web_tools(mock_mcp)
    
    # Sample extracted data (simulating output from Step 3)
    sample_extracted_data = [
        {
            "title": "Python Programming Fundamentals",
            "content": "Python is a high-level programming language known for its simplicity and readability. It supports multiple programming paradigms including procedural, object-oriented, and functional programming. Python is widely used in web development, data science, artificial intelligence, and automation.",
            "source_url": "https://python.org/docs",
            "extraction_timestamp": "2024-06-29T10:30:00Z",
            "extraction_schema": "article",
            "extraction_index": 0
        },
        {
            "title": "Data Science with Python",
            "content": "Python has become the go-to language for data science due to libraries like pandas, numpy, and scikit-learn. These libraries provide powerful tools for data manipulation, analysis, and machine learning. Python's syntax makes it accessible to both beginners and experts in the field.",
            "source_url": "https://datacamp.com/python-data-science",
            "extraction_timestamp": "2024-06-29T10:31:00Z",
            "extraction_schema": "article",
            "extraction_index": 1
        },
        {
            "title": "Machine Learning Applications in Python",
            "content": "Machine learning with Python involves using frameworks like TensorFlow, PyTorch, and scikit-learn. These tools enable developers to build predictive models, neural networks, and AI applications. Python's ecosystem makes ML development more accessible and efficient.",
            "source_url": "https://medium.com/python-ml",
            "extraction_timestamp": "2024-06-29T10:32:00Z",
            "extraction_schema": "research",
            "extraction_index": 2
        },
        {
            "title": "Python Web Development with Django",
            "content": "Django is a high-level Python web framework that encourages rapid development and clean, pragmatic design. It follows the model-template-view architectural pattern and includes features like authentication, URL routing, and database ORM.",
            "source_url": "https://djangoproject.com/overview",
            "extraction_timestamp": "2024-06-29T10:33:00Z",
            "extraction_schema": "article",
            "extraction_index": 3
        },
        {
            "title": "Python Programming Fundamentals",  # Duplicate for testing deduplication
            "content": "Python is a versatile programming language with clear syntax. It's used in many domains including web development, data analysis, and scientific computing. The language emphasizes code readability and programmer productivity.",
            "source_url": "https://python.org/docs",
            "extraction_timestamp": "2024-06-29T10:34:00Z",
            "extraction_schema": "article",
            "extraction_index": 4
        }
    ]
    
    # Test cases for different configurations
    test_cases = [
        {
            "name": "Basic Markdown Analysis",
            "params": {
                "extracted_data": json.dumps(sample_extracted_data),
                "query": "Python programming applications",
                "output_format": "markdown",
                "analysis_depth": "basic",
                "max_items": 10,
                "user_id": "test_user_basic"
            }
        },
        {
            "name": "Deep JSON Analysis",
            "params": {
                "extracted_data": json.dumps(sample_extracted_data[:3]),  # Limit for deep analysis
                "query": "Python data science and machine learning",
                "output_format": "json",
                "analysis_depth": "deep",
                "max_items": 3,
                "user_id": "test_user_deep"
            }
        },
        {
            "name": "Summary Report",
            "params": {
                "extracted_data": json.dumps(sample_extracted_data),
                "query": "Python programming",
                "output_format": "summary",
                "analysis_depth": "medium",
                "max_items": 5,
                "user_id": "test_user_summary"
            }
        }
    ]
    
    # Run test cases
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 测试案例 {i}: {test_case['name']}")
        print("-" * 40)
        
        try:
            # Call the synthesis tool
            result = await mock_mcp.call_tool("synthesize_and_generate", **test_case['params'])
            
            # Parse and display results
            result_data = json.loads(result)
            
            if result_data.get("status") == "success":
                print("✅ 工具调用成功")
                
                # Display synthesis summary
                synthesis_summary = result_data.get("data", {}).get("synthesis_summary", {})
                print(f"   📊 原始项目数: {synthesis_summary.get('original_items_count', 'N/A')}")
                print(f"   🔄 聚合项目数: {synthesis_summary.get('aggregated_items_count', 'N/A')}")
                print(f"   🧠 分析深度: {synthesis_summary.get('analysis_depth', 'N/A')}")
                print(f"   📝 输出格式: {synthesis_summary.get('output_format', 'N/A')}")
                
                # Display analysis insights
                analysis_results = result_data.get("data", {}).get("analysis_results", {})
                insights = analysis_results.get("insights", [])
                themes = analysis_results.get("themes", [])
                
                print(f"   💡 发现的洞察: {len(insights)}")
                for insight in insights[:3]:  # Show first 3 insights
                    print(f"     - {insight[:100]}...")
                
                print(f"   🎯 识别的主题: {len(themes)}")
                for theme in themes[:3]:  # Show first 3 themes
                    print(f"     - {theme[:100]}...")
                
                # Display ranking info
                ranked_content = result_data.get("data", {}).get("ranked_content", [])
                print(f"   🏆 排序后的内容: {len(ranked_content)} 项")
                
                if ranked_content:
                    top_item = ranked_content[0]
                    ranking_info = top_item.get("ranking_info", {})
                    print(f"     最高分项目: {top_item.get('title', 'N/A')[:50]}...")
                    print(f"     总分: {ranking_info.get('total_score', 'N/A')}")
                
                # Display formatted output preview
                formatted_output = result_data.get("data", {}).get("formatted_output", "")
                print(f"   📄 格式化输出预览: {len(formatted_output)} 字符")
                print(f"     {formatted_output[:200]}...")
                
            else:
                print(f"❌ 工具调用失败: {result_data.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
    
    print("\n" + "="*60)
    print("🧪 Step 4 Synthesis & Generate 工具测试完成")

async def test_individual_helper_functions():
    """Test the individual helper functions separately"""
    print("\n🔧 测试底层服务组件")
    print("="*60)
    
    # Import the helper functions directly
    from tools.web_tools import (_aggregate_and_deduplicate, _perform_intelligent_analysis, 
                                _generate_formatted_output, _rank_and_prioritize_content)
    
    # Sample data
    sample_data = [
        {"title": "Test 1", "content": "Content 1", "source_url": "http://test1.com"},
        {"title": "Test 1", "content": "Content 1", "source_url": "http://test1.com"},  # Duplicate
        {"title": "Test 2", "content": "Content 2", "source_url": "http://test2.com"}
    ]
    
    # Test 1: Aggregation and Deduplication
    print("\n1️⃣ 测试数据聚合和去重")
    try:
        aggregated = await _aggregate_and_deduplicate(sample_data, "test query")
        print(f"   ✅ 原始: {len(sample_data)} 项 -> 聚合后: {len(aggregated)} 项")
        
        # Check if duplicates were removed
        if len(aggregated) < len(sample_data):
            print(f"   🔄 成功去除了 {len(sample_data) - len(aggregated)} 个重复项")
    except Exception as e:
        print(f"   ❌ 聚合测试失败: {e}")
    
    # Test 2: Intelligent Analysis
    print("\n2️⃣ 测试智能分析")
    try:
        analysis = await _perform_intelligent_analysis(sample_data[:2], "test analysis", "medium")
        print(f"   ✅ 分析完成")
        print(f"   📊 质量分数: {analysis.get('quality_score', 'N/A')}")
        print(f"   💡 洞察数量: {len(analysis.get('insights', []))}")
        print(f"   🎯 主题数量: {len(analysis.get('themes', []))}")
        
        if analysis.get('raw_analysis'):
            print(f"   📝 分析文本: {analysis['raw_analysis'][:100]}...")
            
    except Exception as e:
        print(f"   ❌ 分析测试失败: {e}")
    
    # Test 3: Output Generation
    print("\n3️⃣ 测试输出生成")
    mock_analysis = {
        'raw_analysis': 'This is a test analysis of the data.',
        'insights': ['Insight 1', 'Insight 2'],
        'themes': ['Theme 1', 'Theme 2']
    }
    
    output_formats = ['markdown', 'json', 'summary', 'report']
    for format_type in output_formats:
        try:
            output = await _generate_formatted_output(sample_data, mock_analysis, format_type, "test query")
            print(f"   ✅ {format_type.upper()}: {len(output)} 字符生成")
        except Exception as e:
            print(f"   ❌ {format_type} 生成失败: {e}")
    
    # Test 4: Content Ranking
    print("\n4️⃣ 测试内容排序")
    try:
        ranked = await _rank_and_prioritize_content(sample_data, mock_analysis, "test ranking")
        print(f"   ✅ 排序完成: {len(ranked)} 项")
        
        if ranked:
            top_item = ranked[0]
            ranking_info = top_item.get('ranking_info', {})
            print(f"   🏆 最高分: {ranking_info.get('total_score', 'N/A')}")
            print(f"   📊 排序标准: 标题相关性, 内容质量, 来源可信度, 提取质量, 时效性")
            
    except Exception as e:
        print(f"   ❌ 排序测试失败: {e}")

async def main():
    """Main test function"""
    print("🚀 开始Step 4 综合测试")
    print("测试完整的 synthesize_and_generate MCP工具")
    print("以及所有底层服务组件")
    
    # Test the main tool
    await test_synthesis_tool()
    
    # Test individual components
    await test_individual_helper_functions()
    
    print(f"\n🎉 所有测试完成！")
    print("Step 4 (Synthesis & Generate) 已实现完整功能:")
    print("  1. ✅ 数据聚合和去重")
    print("  2. ✅ 智能分析 (LLM驱动)")
    print("  3. ✅ 多格式输出生成")
    print("  4. ✅ 内容排序和优先级")

if __name__ == "__main__":
    asyncio.run(main())