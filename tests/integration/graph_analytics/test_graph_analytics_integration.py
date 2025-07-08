#!/usr/bin/env python3
"""
Integration Test for Graph Analytics Tools v2.0

Tests the complete workflow:
1. Build knowledge graph from the ArXiv paper PDF
2. Perform various intelligent queries
3. Validate results and performance
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.logging import get_logger
from tools.graph_analytics_tools import GraphAnalyticsTools

logger = get_logger(__name__)

class GraphAnalyticsIntegrationTest:
    """Integration test suite for Graph Analytics Tools."""
    
    def __init__(self):
        self.tools = GraphAnalyticsTools()
        self.test_file_path = Path(__file__).parent / "test_paper.pdf"
        self.graph_name = "arxiv_test_paper"
        self.test_results = {}
        
    async def run_all_tests(self):
        """Run complete integration test suite."""
        logger.info("🧪 Starting Graph Analytics Integration Tests")
        logger.info("=" * 60)
        
        # Check if test file exists
        if not self.test_file_path.exists():
            logger.error(f"❌ Test file not found: {self.test_file_path}")
            return False
        
        logger.info(f"📄 Test file: {self.test_file_path}")
        logger.info(f"📊 File size: {self.test_file_path.stat().st_size / (1024*1024):.1f} MB")
        
        try:
            # Test 1: Build Knowledge Graph
            await self.test_build_knowledge_graph()
            
            # Test 2: Basic Queries
            await self.test_basic_queries()
            
            # Test 3: Advanced Queries
            await self.test_advanced_queries()
            
            # Test 4: Performance Analysis
            await self.test_performance_analysis()
            
            # Generate test report
            self.generate_test_report()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Integration test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_build_knowledge_graph(self):
        """Test building knowledge graph from PDF."""
        logger.info("\n🏗️  Test 1: Building Knowledge Graph from PDF")
        logger.info("-" * 40)
        
        start_time = datetime.now()
        
        try:
            # 检查PDF文件大小
            file_size = self.test_file_path.stat().st_size
            logger.info(f"📄 PDF文件大小: {file_size / (1024*1024):.1f} MB")
            
            # Step 1: Initialize services
            init_start = datetime.now()
            logger.info("🔧 初始化服务...")
            await self.tools._initialize_services()
            init_time = (datetime.now() - init_start).total_seconds()
            logger.info(f"✅ 服务初始化完成: {init_time:.2f}秒")
            
            # Step 2: Build knowledge graph from the PDF  
            build_start = datetime.now()
            logger.info(f"📚 开始处理PDF文件: {self.test_file_path.name}")
            
            # 设置更小的批次大小和并发数来加速测试
            original_batch_size = self.tools.batch_builder.batch_size
            original_concurrent = self.tools.batch_builder.max_concurrent_extractions
            
            self.tools.batch_builder.batch_size = 1  # 减小批次
            self.tools.batch_builder.max_concurrent_extractions = 2  # 减少并发
            
            logger.info(f"🔧 调整处理参数: batch_size=1, max_concurrent=2")
            
            try:
                result = await self.tools.batch_builder.build_from_file_list(
                    file_paths=[str(self.test_file_path)],
                    graph_name=self.graph_name
                )
            finally:
                # 恢复原始设置
                self.tools.batch_builder.batch_size = original_batch_size
                self.tools.batch_builder.max_concurrent_extractions = original_concurrent
            
            build_time = (datetime.now() - build_start).total_seconds()
            logger.info(f"📊 PDF处理完成: {build_time:.2f}秒")
            
            # Create response in the same format as the tool would
            # Handle datetime serialization
            def datetime_serializer(obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            result_json = json.dumps({
                "status": result.get("status", "error"),
                "data": result
            }, default=datetime_serializer)
            
            # Parse result
            result = json.loads(result_json)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Validate result
            if result.get("status") == "success":
                data = result.get("data", {})
                build_summary = data.get("build_summary", {})
                
                logger.info(f"✅ Knowledge graph built successfully!")
                logger.info(f"   📄 Documents processed: {build_summary.get('successful_documents', 0)}")
                logger.info(f"   🏷️  Entities created: {build_summary.get('total_entities_created', 0)}")
                logger.info(f"   🔗 Relationships created: {build_summary.get('total_relationships_created', 0)}")
                logger.info(f"   ⏱️  Execution time: {execution_time:.2f}s")
                
                self.test_results["build_graph"] = {
                    "status": "success",
                    "execution_time": execution_time,
                    "entities_created": build_summary.get('total_entities_created', 0),
                    "relationships_created": build_summary.get('total_relationships_created', 0),
                    "documents_processed": build_summary.get('successful_documents', 0)
                }
                
            else:
                logger.error(f"❌ Knowledge graph build failed: {result.get('error', 'Unknown error')}")
                self.test_results["build_graph"] = {
                    "status": "failed",
                    "error": result.get('error', 'Unknown error')
                }
                
        except Exception as e:
            logger.error(f"❌ Build test failed: {e}")
            self.test_results["build_graph"] = {
                "status": "error",
                "error": str(e)
            }
    
    async def test_basic_queries(self):
        """Test basic query functionality."""
        logger.info("\n🔍 Test 2: Basic Queries")
        logger.info("-" * 40)
        
        # Skip if graph build failed
        if self.test_results.get("build_graph", {}).get("status") != "success":
            logger.warning("⚠️  Skipping query tests - graph build failed")
            return
        
        basic_queries = [
            "What is this paper about?",
            "machine learning",
            "neural networks", 
            "algorithms",
            "experimental results"
        ]
        
        query_results = []
        
        for i, query in enumerate(basic_queries):
            logger.info(f"Query {i+1}: {query}")
            
            try:
                start_time = datetime.now()
                
                # Call query aggregator directly
                result = await self.tools.query_aggregator.intelligent_query(
                    query=query,
                    max_results=10,
                    include_analysis=True
                )
                
                # Create response in the same format as the tool would  
                def datetime_serializer(obj):
                    if hasattr(obj, 'isoformat'):
                        return obj.isoformat()
                    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
                
                result_json = json.dumps({
                    "status": result.get("status", "error"),
                    "data": result
                }, default=datetime_serializer)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                result = json.loads(result_json)
                
                if result.get("status") == "success":
                    data = result.get("data", {})
                    results_count = len(data.get("results", []))
                    strategy = data.get("strategy", {})
                    
                    logger.info(f"   ✅ Found {results_count} results in {execution_time:.2f}s")
                    logger.info(f"   📊 Strategy: {strategy}")
                    
                    query_results.append({
                        "query": query,
                        "status": "success",
                        "results_count": results_count,
                        "execution_time": execution_time,
                        "strategy": strategy
                    })
                    
                else:
                    logger.error(f"   ❌ Query failed: {result.get('error', 'Unknown error')}")
                    query_results.append({
                        "query": query,
                        "status": "failed",
                        "error": result.get('error')
                    })
                    
            except Exception as e:
                logger.error(f"   ❌ Query error: {e}")
                query_results.append({
                    "query": query,
                    "status": "error", 
                    "error": str(e)
                })
        
        # Summarize results
        successful_queries = len([r for r in query_results if r["status"] == "success"])
        logger.info(f"\n📊 Basic Query Results: {successful_queries}/{len(basic_queries)} successful")
        
        self.test_results["basic_queries"] = {
            "total_queries": len(basic_queries),
            "successful_queries": successful_queries,
            "results": query_results
        }
    
    async def test_advanced_queries(self):
        """Test advanced query functionality.""" 
        logger.info("\n🧠 Test 3: Advanced Queries")
        logger.info("-" * 40)
        
        # Skip if graph build failed
        if self.test_results.get("build_graph", {}).get("status") != "success":
            logger.warning("⚠️  Skipping advanced query tests - graph build failed")
            return
        
        advanced_queries = [
            {
                "query": "Compare different machine learning approaches mentioned in this paper",
                "context": '{"analysis_type": "comparison", "focus": "methods"}'
            },
            {
                "query": "What are the key contributions and innovations?",
                "context": '{"analysis_type": "summary", "focus": "contributions"}'
            },
            {
                "query": "Show relationships between authors and their institutions",
                "context": '{"analysis_type": "network", "focus": "authors"}'
            },
            {
                "query": "Analyze the experimental methodology and results",
                "context": '{"analysis_type": "analytical", "focus": "experiments"}'
            }
        ]
        
        advanced_results = []
        
        for i, query_info in enumerate(advanced_queries):
            query = query_info["query"]
            context = query_info["context"]
            
            logger.info(f"Advanced Query {i+1}: {query}")
            
            try:
                start_time = datetime.now()
                
                # Parse context
                context_dict = {}
                try:
                    context_dict = json.loads(context)
                except:
                    pass
                
                # Call query aggregator directly
                result = await self.tools.query_aggregator.intelligent_query(
                    query=query,
                    context=context_dict,
                    max_results=15,
                    include_analysis=True
                )
                
                # Create response in the same format as the tool would
                def datetime_serializer(obj):
                    if hasattr(obj, 'isoformat'):
                        return obj.isoformat()
                    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
                
                result_json = json.dumps({
                    "status": result.get("status", "error"),
                    "data": result
                }, default=datetime_serializer)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                result = json.loads(result_json)
                
                if result.get("status") == "success":
                    data = result.get("data", {})
                    results_count = len(data.get("results", []))
                    analysis = data.get("analysis", {})
                    
                    logger.info(f"   ✅ Found {results_count} results in {execution_time:.2f}s")
                    logger.info(f"   🔬 Analysis insights: {len(analysis.get('insights', []))}")
                    
                    advanced_results.append({
                        "query": query,
                        "context": context,
                        "status": "success",
                        "results_count": results_count,
                        "execution_time": execution_time,
                        "analysis": analysis
                    })
                    
                else:
                    logger.error(f"   ❌ Advanced query failed: {result.get('error')}")
                    advanced_results.append({
                        "query": query,
                        "status": "failed",
                        "error": result.get('error')
                    })
                    
            except Exception as e:
                logger.error(f"   ❌ Advanced query error: {e}")
                advanced_results.append({
                    "query": query,
                    "status": "error",
                    "error": str(e)
                })
        
        # Summarize results
        successful_advanced = len([r for r in advanced_results if r["status"] == "success"])
        logger.info(f"\n📊 Advanced Query Results: {successful_advanced}/{len(advanced_queries)} successful")
        
        self.test_results["advanced_queries"] = {
            "total_queries": len(advanced_queries),
            "successful_queries": successful_advanced,
            "results": advanced_results
        }
    
    async def test_performance_analysis(self):
        """Test performance and analyze system behavior."""
        logger.info("\n⚡ Test 4: Performance Analysis")
        logger.info("-" * 40)
        
        performance_data = {
            "build_time": self.test_results.get("build_graph", {}).get("execution_time", 0),
            "entities_created": self.test_results.get("build_graph", {}).get("entities_created", 0),
            "relationships_created": self.test_results.get("build_graph", {}).get("relationships_created", 0),
            "average_query_time": 0,
            "query_success_rate": 0
        }
        
        # Calculate query performance
        all_query_results = []
        if "basic_queries" in self.test_results:
            all_query_results.extend(self.test_results["basic_queries"]["results"])
        if "advanced_queries" in self.test_results:
            all_query_results.extend(self.test_results["advanced_queries"]["results"])
        
        if all_query_results:
            successful_queries = [r for r in all_query_results if r["status"] == "success"]
            if successful_queries:
                avg_time = sum(r["execution_time"] for r in successful_queries) / len(successful_queries)
                performance_data["average_query_time"] = avg_time
            
            performance_data["query_success_rate"] = len(successful_queries) / len(all_query_results) * 100
        
        # Performance assessment
        logger.info(f"📊 Performance Metrics:")
        logger.info(f"   🏗️  Graph build time: {performance_data['build_time']:.2f}s")
        logger.info(f"   🏷️  Entities created: {performance_data['entities_created']}")
        logger.info(f"   🔗 Relationships created: {performance_data['relationships_created']}")
        logger.info(f"   ⚡ Average query time: {performance_data['average_query_time']:.2f}s")
        logger.info(f"   ✅ Query success rate: {performance_data['query_success_rate']:.1f}%")
        
        # Performance thresholds
        performance_score = 0
        if performance_data["build_time"] < 300:  # < 5 minutes
            performance_score += 25
        if performance_data["entities_created"] > 50:
            performance_score += 25
        if performance_data["average_query_time"] < 5:  # < 5 seconds
            performance_score += 25
        if performance_data["query_success_rate"] > 80:  # > 80%
            performance_score += 25
        
        logger.info(f"🎯 Overall Performance Score: {performance_score}/100")
        
        self.test_results["performance"] = {
            **performance_data,
            "performance_score": performance_score
        }
    
    def generate_test_report(self):
        """Generate comprehensive test report."""
        logger.info("\n" + "=" * 60)
        logger.info("📋 GRAPH ANALYTICS INTEGRATION TEST REPORT")
        logger.info("=" * 60)
        
        # Overall status
        overall_success = True
        for test_name, result in self.test_results.items():
            if test_name == "performance":
                continue
            if result.get("status") not in ["success"]:
                overall_success = False
                break
        
        logger.info(f"🎯 Overall Test Status: {'✅ PASSED' if overall_success else '❌ FAILED'}")
        
        # Detailed results
        logger.info("\n📊 Test Results Summary:")
        logger.info("-" * 40)
        
        for test_name, result in self.test_results.items():
            if test_name == "build_graph":
                status = result.get("status", "unknown")
                logger.info(f"🏗️  Build Knowledge Graph: {status.upper()}")
                if status == "success":
                    logger.info(f"   📄 Documents: {result.get('documents_processed', 0)}")
                    logger.info(f"   🏷️  Entities: {result.get('entities_created', 0)}")
                    logger.info(f"   🔗 Relationships: {result.get('relationships_created', 0)}")
            
            elif test_name == "basic_queries":
                success_rate = result.get("successful_queries", 0) / result.get("total_queries", 1) * 100
                logger.info(f"🔍 Basic Queries: {result.get('successful_queries', 0)}/{result.get('total_queries', 0)} ({success_rate:.1f}%)")
            
            elif test_name == "advanced_queries":
                success_rate = result.get("successful_queries", 0) / result.get("total_queries", 1) * 100
                logger.info(f"🧠 Advanced Queries: {result.get('successful_queries', 0)}/{result.get('total_queries', 0)} ({success_rate:.1f}%)")
            
            elif test_name == "performance":
                score = result.get("performance_score", 0)
                logger.info(f"⚡ Performance Score: {score}/100")
        
        # Recommendations
        logger.info("\n💡 Recommendations:")
        logger.info("-" * 40)
        
        if self.test_results.get("build_graph", {}).get("status") != "success":
            logger.info("❌ Fix knowledge graph construction issues")
        else:
            logger.info("✅ Knowledge graph construction working correctly")
        
        performance = self.test_results.get("performance", {})
        if performance.get("average_query_time", 0) > 5:
            logger.info("⚠️  Consider query optimization for better performance")
        
        if performance.get("query_success_rate", 0) < 80:
            logger.info("⚠️  Improve query handling and error recovery")
        
        logger.info("\n🎉 Integration testing completed!")
        logger.info("=" * 60)

async def main():
    """Main test function."""
    test_suite = GraphAnalyticsIntegrationTest()
    success = await test_suite.run_all_tests()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)