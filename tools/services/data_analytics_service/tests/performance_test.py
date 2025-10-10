#!/usr/bin/env python3
"""
Digital Analytics Tools Performance Test

Comprehensive performance testing suite for digital analytics tools based on
test cases from how_to_digital.md documentation.

Features:
- All 16 MCP tools from digital_analytics_tools.py
- Timing measurements with proper logging
- Test cases from real documentation examples
- Performance benchmarks and reporting
- Support for different RAG modes
- Image processing performance tests
"""

import asyncio
import time
import json
import tempfile
import shutil
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
import statistics

# Import MCP client and logging
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from tools.mcp_client import MCPClient
from core.logging import get_logger, setup_mcp_logging

# Setup logging
setup_mcp_logging()
logger = get_logger(__name__)

class PerformanceTestRunner:
    """Performance test runner with timing and logging"""
    
    def __init__(self, base_url: str = "http://localhost:8081"):
        self.client = MCPClient(base_url)
        self.results: List[Dict[str, Any]] = []
        self.test_user_id = "perf_test_user_2025"
        
        # Test data from documentation
        self.sample_texts = [
            "人工智能(AI)是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。",
            "Redis是一个开源的内存数据结构存储系统，可用作数据库、缓存和消息代理。",
            "机器学习是人工智能的一个子集，它使计算机能够从数据中自动学习和改进，而无需显式编程。"
        ]
        
        self.long_document = """
        这是一个关于人工智能和机器学习的长文档。它涵盖了各种主题，包括神经网络、深度学习、自然语言处理和计算机视觉。
        文档解释了AI系统如何工作以及它们在不同行业中的应用。人工智能技术正在快速发展，从简单的规则系统发展到复杂的深度学习模型。
        机器学习算法可以分为监督学习、无监督学习和强化学习三大类。监督学习使用标记的训练数据来学习输入和输出之间的映射关系。
        无监督学习试图在没有标记数据的情况下发现数据中的模式和结构。强化学习通过与环境交互并接收奖励或惩罚信号来学习最优行为策略。
        深度学习是机器学习的一个子领域，它使用多层神经网络来学习数据的复杂表示。这些网络能够自动提取特征，无需手动特征工程。
        自然语言处理（NLP）是AI的一个分支，专注于使计算机能够理解、解释和生成人类语言。NLP技术包括文本分类、情感分析、机器翻译等。
        计算机视觉是另一个重要的AI领域，它使计算机能够从图像和视频中提取有意义的信息。这包括对象检测、图像分类、面部识别等任务。
        AI在各行各业都有广泛应用，包括医疗诊断、金融风控、自动驾驶、智能助手、推荐系统等。随着技术的不断进步，AI将继续改变我们的生活和工作方式。
        """
        
        self.rag_modes = ["simple", "raptor", "self_rag", "crag", "plan_rag", "hm_rag"]
        self.test_queries = [
            "什么是人工智能？",
            "介绍一下Redis的特点",
            "机器学习和深度学习有什么区别？",
            "自然语言处理的应用有哪些？"
        ]
        
    async def time_operation(self, operation_name: str, operation_func, *args, **kwargs) -> Dict[str, Any]:
        """Time an operation and log results"""
        start_time = time.perf_counter()
        
        try:
            logger.info(f"Starting {operation_name}", operation=operation_name)
            result = await operation_func(*args, **kwargs)
            
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            # Parse result if it's successful
            success = result.get('status') == 'success' if isinstance(result, dict) else True
            
            test_result = {
                'operation': operation_name,
                'success': success,
                'execution_time': execution_time,
                'timestamp': time.time(),
                'result_size': len(str(result)) if result else 0
            }
            
            if success:
                logger.info(
                    f"✅ {operation_name} completed successfully",
                    operation=operation_name,
                    execution_time=execution_time,
                    success=True
                )
            else:
                logger.error(
                    f"❌ {operation_name} failed", 
                    operation=operation_name,
                    execution_time=execution_time,
                    success=False,
                    error=result.get('error') if isinstance(result, dict) else str(result)
                )
            
            self.results.append(test_result)
            return test_result
            
        except Exception as e:
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            logger.error(
                f"❌ {operation_name} failed with exception",
                operation=operation_name,
                execution_time=execution_time,
                success=False,
                error=str(e),
                exc_info=True
            )
            
            test_result = {
                'operation': operation_name,
                'success': False,
                'execution_time': execution_time,
                'timestamp': time.time(),
                'error': str(e),
                'result_size': 0
            }
            
            self.results.append(test_result)
            return test_result

    async def test_knowledge_management_tools(self) -> None:
        """Test all knowledge management tools with performance timing"""
        logger.info("🚀 Starting Knowledge Management Tools Performance Tests")
        
        stored_knowledge_ids = []
        
        # 1. Test store_knowledge (multiple samples)
        for i, text in enumerate(self.sample_texts):
            await self.time_operation(
                f"store_knowledge_{i+1}",
                self.client.call_tool_and_parse,
                'store_knowledge',
                {
                    'user_id': self.test_user_id,
                    'text': text,
                    'metadata': {'source': 'performance_test', 'index': i}
                }
            )
        
        # 2. Test add_document (chunking)
        result = await self.time_operation(
            "add_document",
            self.client.call_tool_and_parse,
            'add_document',
            {
                'user_id': self.test_user_id,
                'document': self.long_document,
                'chunk_size': 400,
                'overlap': 50,
                'metadata': {'title': 'AI手册', 'author': 'Performance Test'}
            }
        )
        
        # 3. Test list_user_knowledge
        await self.time_operation(
            "list_user_knowledge",
            self.client.call_tool_and_parse,
            'list_user_knowledge',
            {'user_id': self.test_user_id}
        )
        
        # 4. Test search_knowledge with different queries
        for i, query in enumerate(self.test_queries):
            await self.time_operation(
                f"search_knowledge_query_{i+1}",
                self.client.call_tool_and_parse,
                'search_knowledge',
                {
                    'user_id': self.test_user_id,
                    'query': query,
                    'top_k': 5,
                    'enable_rerank': False
                }
            )
        
        # 5. Test search with reranking
        await self.time_operation(
            "search_knowledge_with_rerank",
            self.client.call_tool_and_parse,
            'search_knowledge',
            {
                'user_id': self.test_user_id,
                'query': "内存数据库系统",
                'top_k': 5,
                'enable_rerank': True
            }
        )
        
        # 6. Test retrieve_context
        await self.time_operation(
            "retrieve_context",
            self.client.call_tool_and_parse,
            'retrieve_context',
            {
                'user_id': self.test_user_id,
                'query': "机器学习算法",
                'top_k': 5
            }
        )
        
        # 7. Test generate_rag_response
        await self.time_operation(
            "generate_rag_response",
            self.client.call_tool_and_parse,
            'generate_rag_response',
            {
                'user_id': self.test_user_id,
                'query': "介绍一下Redis的特点",
                'context_limit': 3
            }
        )

    async def test_rag_modes_performance(self) -> None:
        """Test different RAG modes performance"""
        logger.info("🤖 Starting RAG Modes Performance Tests")
        
        test_query = "What is machine learning and how does it work?"
        
        # Test each RAG mode
        for mode in self.rag_modes:
            await self.time_operation(
                f"query_with_mode_{mode}",
                self.client.call_tool_and_parse,
                'query_with_mode',
                {
                    'user_id': self.test_user_id,
                    'query': test_query,
                    'mode': mode
                }
            )
        
        # Test hybrid query
        await self.time_operation(
            "hybrid_query",
            self.client.call_tool_and_parse,
            'hybrid_query',
            {
                'user_id': self.test_user_id,
                'query': test_query,
                'modes': 'simple,self_rag'
            }
        )
        
        # Test recommend_mode
        await self.time_operation(
            "recommend_mode",
            self.client.call_tool_and_parse,
            'recommend_mode',
            {
                'query': "Complex analysis with multiple perspectives",
                'user_id': self.test_user_id
            }
        )

    async def test_system_tools_performance(self) -> None:
        """Test system management tools"""
        logger.info("⚙️ Starting System Tools Performance Tests")
        
        # Test get_rag_capabilities
        await self.time_operation(
            "get_rag_capabilities",
            self.client.call_tool_and_parse,
            'get_rag_capabilities',
            {}
        )
        
        # Test get_analytics_service_status
        await self.time_operation(
            "get_analytics_service_status",
            self.client.call_tool_and_parse,
            'get_analytics_service_status',
            {}
        )

    async def test_image_processing_performance(self) -> None:
        """Test image processing tools (if available)"""
        logger.info("🖼️ Starting Image Processing Performance Tests")
        
        # Create a temporary test image (simple colored rectangle)
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            tmp_image_path = tmp_file.name
        
        try:
            # Create a simple test image using PIL if available
            try:
                from PIL import Image
                img = Image.new('RGB', (100, 100), color='blue')
                img.save(tmp_image_path)
                
                # Test store_image
                await self.time_operation(
                    "store_image",
                    self.client.call_tool_and_parse,
                    'store_image',
                    {
                        'user_id': self.test_user_id,
                        'image_path': tmp_image_path,
                        'metadata': {'category': 'test'},
                        'model': 'gpt-4o-mini'
                    }
                )
                
                # Test search_images
                await self.time_operation(
                    "search_images",
                    self.client.call_tool_and_parse,
                    'search_images',
                    {
                        'user_id': self.test_user_id,
                        'query': 'blue image',
                        'top_k': 2
                    }
                )
                
                # Test generate_image_rag_response
                await self.time_operation(
                    "generate_image_rag_response",
                    self.client.call_tool_and_parse,
                    'generate_image_rag_response',
                    {
                        'user_id': self.test_user_id,
                        'query': 'What images do I have?',
                        'context_limit': 3,
                        'include_images': True
                    }
                )
                
            except ImportError:
                logger.warning("PIL not available, skipping image processing tests")
        
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_image_path):
                os.unlink(tmp_image_path)

    async def cleanup_test_data(self) -> None:
        """Clean up test data after performance tests"""
        logger.info("🧹 Cleaning up test data")
        
        try:
            # Get list of knowledge items
            result = await self.client.call_tool_and_parse(
                'list_user_knowledge',
                {'user_id': self.test_user_id}
            )
            
            if result.get('status') == 'success' and 'data' in result:
                items = result['data'].get('items', [])
                
                # Delete each item
                for item in items:
                    knowledge_id = item.get('knowledge_id')
                    if knowledge_id:
                        await self.time_operation(
                            f"cleanup_delete_{knowledge_id[:8]}",
                            self.client.call_tool_and_parse,
                            'delete_knowledge_item',
                            {
                                'user_id': self.test_user_id,
                                'knowledge_id': knowledge_id
                            }
                        )
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        logger.info("📊 Generating performance report")
        
        if not self.results:
            return {"error": "No test results available"}
        
        # Group results by operation category
        knowledge_ops = [r for r in self.results if any(op in r['operation'] for op in ['store_knowledge', 'search_knowledge', 'add_document', 'list_user', 'retrieve_context', 'generate_rag'])]
        rag_ops = [r for r in self.results if any(op in r['operation'] for op in ['query_with_mode', 'hybrid_query', 'recommend_mode'])]
        system_ops = [r for r in self.results if any(op in r['operation'] for op in ['get_rag_capabilities', 'get_analytics_service_status'])]
        image_ops = [r for r in self.results if any(op in r['operation'] for op in ['store_image', 'search_images', 'generate_image_rag'])]
        cleanup_ops = [r for r in self.results if 'cleanup' in r['operation']]
        
        def analyze_operations(ops: List[Dict], category: str) -> Dict[str, Any]:
            if not ops:
                return {"category": category, "count": 0}
            
            times = [op['execution_time'] for op in ops]
            successful = [op for op in ops if op['success']]
            failed = [op for op in ops if not op['success']]
            
            return {
                "category": category,
                "total_operations": len(ops),
                "successful_operations": len(successful),
                "failed_operations": len(failed),
                "success_rate": len(successful) / len(ops) * 100 if ops else 0,
                "avg_execution_time": statistics.mean(times),
                "median_execution_time": statistics.median(times),
                "min_execution_time": min(times),
                "max_execution_time": max(times),
                "total_execution_time": sum(times),
                "fastest_operation": min(ops, key=lambda x: x['execution_time'])['operation'],
                "slowest_operation": max(ops, key=lambda x: x['execution_time'])['operation']
            }
        
        # Generate category reports
        knowledge_report = analyze_operations(knowledge_ops, "Knowledge Management")
        rag_report = analyze_operations(rag_ops, "RAG Operations") 
        system_report = analyze_operations(system_ops, "System Tools")
        image_report = analyze_operations(image_ops, "Image Processing")
        cleanup_report = analyze_operations(cleanup_ops, "Cleanup Operations")
        
        # Overall statistics
        all_times = [r['execution_time'] for r in self.results]
        total_successful = sum(1 for r in self.results if r['success'])
        total_operations = len(self.results)
        
        # RAG mode performance comparison
        rag_mode_performance = {}
        for mode in self.rag_modes:
            mode_results = [r for r in self.results if f'query_with_mode_{mode}' in r['operation']]
            if mode_results:
                result = mode_results[0]
                rag_mode_performance[mode] = {
                    "execution_time": result['execution_time'],
                    "success": result['success'],
                    "performance_rating": "⚡️" if result['execution_time'] < 2 else "🚀" if result['execution_time'] < 5 else "🐢" if result['execution_time'] < 8 else "🐌"
                }
        
        report = {
            "test_summary": {
                "total_operations": total_operations,
                "successful_operations": total_successful,
                "failed_operations": total_operations - total_successful,
                "overall_success_rate": total_successful / total_operations * 100 if total_operations else 0,
                "total_test_time": sum(all_times),
                "average_operation_time": statistics.mean(all_times) if all_times else 0,
                "test_user_id": self.test_user_id,
                "timestamp": time.time()
            },
            "category_performance": {
                "knowledge_management": knowledge_report,
                "rag_operations": rag_report,
                "system_tools": system_report,
                "image_processing": image_report,
                "cleanup_operations": cleanup_report
            },
            "rag_mode_comparison": rag_mode_performance,
            "detailed_results": self.results,
            "performance_benchmarks": {
                "service_initialization": "< 1s",
                "knowledge_storage": "< 100ms (target)",
                "semantic_search": "< 1s (target)",
                "rag_generation": "2-5s (target)",
                "image_storage": "6-7s (VLM processing)",
                "image_search": "< 1s (target)"
            }
        }
        
        return report

    async def run_full_performance_test(self) -> Dict[str, Any]:
        """Run complete performance test suite"""
        logger.info("🏁 Starting Full Performance Test Suite")
        start_time = time.perf_counter()
        
        try:
            # Run all test categories
            await self.test_knowledge_management_tools()
            await self.test_rag_modes_performance()  
            await self.test_system_tools_performance()
            await self.test_image_processing_performance()
            
            # Generate report before cleanup
            report = self.generate_performance_report()
            
            # Clean up test data
            await self.cleanup_test_data()
            
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
            report["test_summary"]["total_suite_time"] = total_time
            
            logger.info(
                f"🏆 Performance Test Suite Completed",
                total_time=total_time,
                total_operations=len(self.results),
                success_rate=report["test_summary"]["overall_success_rate"]
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Performance test suite failed: {e}", exc_info=True)
            return {"error": str(e), "partial_results": self.results}

async def main():
    """Main function to run performance tests"""
    print("🚀 Digital Analytics Tools Performance Test")
    print("=" * 50)
    
    # Initialize test runner
    test_runner = PerformanceTestRunner()
    
    # Check if MCP server is running
    try:
        capabilities = await test_runner.client.get_capabilities()
        if capabilities.get('status') == 'error':
            print("❌ MCP server not available. Please start the server first.")
            print("Expected server at: http://localhost:8081")
            return
    except Exception as e:
        print(f"❌ Cannot connect to MCP server: {e}")
        return
    
    # Run performance tests
    print("🏁 Running performance tests...")
    report = await test_runner.run_full_performance_test()
    
    # Save detailed report
    report_path = "performance_test_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n📊 Performance Test Results:")
    print("=" * 50)
    
    if "error" in report:
        print(f"❌ Test failed: {report['error']}")
        return
    
    summary = report["test_summary"]
    print(f"✅ Total Operations: {summary['total_operations']}")
    print(f"✅ Success Rate: {summary['overall_success_rate']:.1f}%")
    print(f"⏱️  Total Test Time: {summary['total_test_time']:.2f}s")
    print(f"⚡️ Average Operation Time: {summary['average_operation_time']:.3f}s")
    
    print(f"\n🏆 Category Performance:")
    for category, data in report["category_performance"].items():
        if data["count"] > 0:
            print(f"  {category.replace('_', ' ').title()}: {data['success_rate']:.1f}% success, avg {data['avg_execution_time']:.3f}s")
    
    print(f"\n🤖 RAG Mode Performance:")
    for mode, data in report["rag_mode_comparison"].items():
        status = "✅" if data["success"] else "❌"
        print(f"  {mode}: {status} {data['execution_time']:.2f}s {data['performance_rating']}")
    
    print(f"\n📋 Detailed report saved to: {report_path}")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())