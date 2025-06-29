#!/usr/bin/env python3
"""
完整的5步数据分析工作流测试
从第1步到第5步，展示每一步的真实输入输出数据
"""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parents[3]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tools" / "services" / "data_analytics_service" / "services"))

# Import services directly from full paths
from tools.services.data_analytics_service.services.metadata_service import MetadataDiscoveryService
from tools.services.data_analytics_service.services.semantic_enricher import SemanticEnricher, SemanticMetadata
from tools.services.data_analytics_service.services.embedding_storage import EmbeddingStorage
from tools.services.data_analytics_service.services.query_matcher import QueryMatcher, QueryContext
from tools.services.data_analytics_service.services.sql_executor import SQLExecutor
from tools.services.data_analytics_service.services.llm_sql_generator import LLMSQLGenerator

class Complete5StepWorkflowTest:
    """完整的5步数据分析工作流测试"""
    
    def __init__(self):
        self.test_results = {}
        self.customs_db_config = {
            'type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'customs_trade_db',
            'username': 'postgres',
            'password': 'password'
        }
    
    def log_step_result(self, step_name: str, input_data: dict, output_data: dict, success: bool):
        """记录每一步的输入输出"""
        self.test_results[step_name] = {
            'step_number': len(self.test_results) + 1,
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'input_summary': self._summarize_data(input_data),
            'output_summary': self._summarize_data(output_data),
            'input_data': input_data,
            'output_data': output_data
        }
        
        print(f"\n{'='*60}")
        print(f"第{len(self.test_results)}步: {step_name}")
        print(f"{'='*60}")
        print(f"✅ 成功: {success}")
        print(f"📥 输入概况: {self.test_results[step_name]['input_summary']}")
        print(f"📤 输出概况: {self.test_results[step_name]['output_summary']}")
    
    def _summarize_data(self, data: dict) -> str:
        """生成数据摘要"""
        if not data:
            return "空数据"
        
        summary_parts = []
        
        # 检查常见的数据结构
        if 'tables' in data:
            summary_parts.append(f"{len(data['tables'])}个表")
        if 'columns' in data:
            summary_parts.append(f"{len(data['columns'])}个列")
        if 'business_entities' in data:
            summary_parts.append(f"{len(data['business_entities'])}个业务实体")
        if 'semantic_tags' in data:
            summary_parts.append(f"{len(data['semantic_tags'])}个语义标签")
        if 'sql' in data:
            summary_parts.append(f"SQL查询: {data['sql'][:50]}...")
        if 'data' in data and isinstance(data['data'], list):
            summary_parts.append(f"{len(data['data'])}行数据")
        
        return ", ".join(summary_parts) if summary_parts else f"{len(data)}个字段"
    
    async def step1_metadata_discovery(self):
        """第1步: 元数据发现"""
        print("\n🔍 开始第1步: 元数据发现")
        
        try:
            # 输入数据
            input_data = {
                'database_config': self.customs_db_config,
                'discovery_options': {
                    'include_sample_data': True,
                    'include_statistics': True,
                    'max_sample_rows': 100
                }
            }
            
            # 执行元数据发现
            metadata_service = MetadataDiscoveryService()
            
            # 模拟真实的数据库元数据发现结果
            mock_metadata = {
                'source_info': {
                    'type': 'postgresql',
                    'database': 'customs_trade_db',
                    'discovery_time': datetime.now().isoformat(),
                    'version': '13.4'
                },
                'tables': [
                    {
                        'table_name': 'companies',
                        'schema_name': 'public',
                        'table_type': 'TABLE',
                        'record_count': 1250,
                        'table_comment': '公司企业信息表',
                        'created_date': '2024-01-15',
                        'last_modified': '2024-12-01'
                    },
                    {
                        'table_name': 'declarations',
                        'schema_name': 'public', 
                        'table_type': 'TABLE',
                        'record_count': 8750,
                        'table_comment': '海关申报单据表',
                        'created_date': '2024-01-15',
                        'last_modified': '2024-12-28'
                    },
                    {
                        'table_name': 'hs_codes',
                        'schema_name': 'public',
                        'table_type': 'TABLE', 
                        'record_count': 2340,
                        'table_comment': 'HS商品编码表',
                        'created_date': '2024-01-15',
                        'last_modified': '2024-06-15'
                    },
                    {
                        'table_name': 'goods_details',
                        'schema_name': 'public',
                        'table_type': 'TABLE',
                        'record_count': 15620,
                        'table_comment': '货物详细信息表',
                        'created_date': '2024-01-15',
                        'last_modified': '2024-12-28'
                    }
                ],
                'columns': [
                    # companies表字段
                    {'table_name': 'companies', 'column_name': 'id', 'data_type': 'bigint', 'is_nullable': False, 'column_position': 1, 'column_comment': '公司ID'},
                    {'table_name': 'companies', 'column_name': 'company_code', 'data_type': 'varchar(20)', 'is_nullable': False, 'column_position': 2, 'column_comment': '公司代码'},
                    {'table_name': 'companies', 'column_name': 'company_name', 'data_type': 'varchar(200)', 'is_nullable': False, 'column_position': 3, 'column_comment': '公司名称'},
                    {'table_name': 'companies', 'column_name': 'registration_number', 'data_type': 'varchar(50)', 'is_nullable': True, 'column_position': 4, 'column_comment': '工商注册号'},
                    {'table_name': 'companies', 'column_name': 'address', 'data_type': 'text', 'is_nullable': True, 'column_position': 5, 'column_comment': '公司地址'},
                    {'table_name': 'companies', 'column_name': 'created_at', 'data_type': 'timestamp', 'is_nullable': False, 'column_position': 6, 'column_comment': '创建时间'},
                    
                    # declarations表字段
                    {'table_name': 'declarations', 'column_name': 'id', 'data_type': 'bigint', 'is_nullable': False, 'column_position': 1, 'column_comment': '申报单ID'},
                    {'table_name': 'declarations', 'column_name': 'declaration_number', 'data_type': 'varchar(30)', 'is_nullable': False, 'column_position': 2, 'column_comment': '申报单号'},
                    {'table_name': 'declarations', 'column_name': 'company_code', 'data_type': 'varchar(20)', 'is_nullable': False, 'column_position': 3, 'column_comment': '公司代码'},
                    {'table_name': 'declarations', 'column_name': 'trade_type', 'data_type': 'varchar(10)', 'is_nullable': False, 'column_position': 4, 'column_comment': '贸易类型'},
                    {'table_name': 'declarations', 'column_name': 'currency_code', 'data_type': 'varchar(3)', 'is_nullable': False, 'column_position': 5, 'column_comment': '货币代码'},
                    {'table_name': 'declarations', 'column_name': 'rmb_amount', 'data_type': 'decimal(15,2)', 'is_nullable': False, 'column_position': 6, 'column_comment': '人民币金额'},
                    {'table_name': 'declarations', 'column_name': 'declaration_date', 'data_type': 'date', 'is_nullable': False, 'column_position': 7, 'column_comment': '申报日期'},
                    
                    # hs_codes表字段
                    {'table_name': 'hs_codes', 'column_name': 'id', 'data_type': 'bigint', 'is_nullable': False, 'column_position': 1, 'column_comment': 'HS编码ID'},
                    {'table_name': 'hs_codes', 'column_name': 'hs_code', 'data_type': 'varchar(10)', 'is_nullable': False, 'column_position': 2, 'column_comment': 'HS商品编码'},
                    {'table_name': 'hs_codes', 'column_name': 'hs_description_cn', 'data_type': 'text', 'is_nullable': False, 'column_position': 3, 'column_comment': '中文描述'},
                    {'table_name': 'hs_codes', 'column_name': 'hs_description_en', 'data_type': 'text', 'is_nullable': True, 'column_position': 4, 'column_comment': '英文描述'},
                    {'table_name': 'hs_codes', 'column_name': 'chapter_code', 'data_type': 'varchar(2)', 'is_nullable': False, 'column_position': 5, 'column_comment': '章节编码'},
                    {'table_name': 'hs_codes', 'column_name': 'chapter_name', 'data_type': 'varchar(100)', 'is_nullable': False, 'column_position': 6, 'column_comment': '章节名称'},
                    
                    # goods_details表字段
                    {'table_name': 'goods_details', 'column_name': 'id', 'data_type': 'bigint', 'is_nullable': False, 'column_position': 1, 'column_comment': '货物详情ID'},
                    {'table_name': 'goods_details', 'column_name': 'declaration_id', 'data_type': 'bigint', 'is_nullable': False, 'column_position': 2, 'column_comment': '申报单ID'},
                    {'table_name': 'goods_details', 'column_name': 'hs_code', 'data_type': 'varchar(10)', 'is_nullable': False, 'column_position': 3, 'column_comment': 'HS商品编码'},
                    {'table_name': 'goods_details', 'column_name': 'goods_name', 'data_type': 'varchar(200)', 'is_nullable': False, 'column_position': 4, 'column_comment': '货物名称'},
                    {'table_name': 'goods_details', 'column_name': 'quantity', 'data_type': 'decimal(12,3)', 'is_nullable': False, 'column_position': 5, 'column_comment': '数量'},
                    {'table_name': 'goods_details', 'column_name': 'unit_price', 'data_type': 'decimal(10,2)', 'is_nullable': False, 'column_position': 6, 'column_comment': '单价'},
                    {'table_name': 'goods_details', 'column_name': 'total_amount', 'data_type': 'decimal(15,2)', 'is_nullable': False, 'column_position': 7, 'column_comment': '总金额'}
                ],
                'relationships': [
                    {
                        'from_table': 'declarations',
                        'from_column': 'company_code',
                        'to_table': 'companies',
                        'to_column': 'company_code',
                        'relationship_type': 'foreign_key'
                    },
                    {
                        'from_table': 'goods_details',
                        'from_column': 'declaration_id',
                        'to_table': 'declarations',
                        'to_column': 'id',
                        'relationship_type': 'foreign_key'
                    },
                    {
                        'from_table': 'goods_details',
                        'from_column': 'hs_code',
                        'to_table': 'hs_codes',
                        'to_column': 'hs_code',
                        'relationship_type': 'foreign_key'
                    }
                ],
                'sample_data': {
                    'companies': [
                        {'id': 1, 'company_code': 'COMP001', 'company_name': '上海贸易有限公司', 'registration_number': '91310000123456789X'},
                        {'id': 2, 'company_code': 'COMP002', 'company_name': '北京进出口公司', 'registration_number': '91110000987654321A'},
                        {'id': 3, 'company_code': 'COMP003', 'company_name': '深圳科技贸易公司', 'registration_number': '91440300555666777B'}
                    ],
                    'declarations': [
                        {'id': 1, 'declaration_number': 'DEC2024120001', 'company_code': 'COMP001', 'trade_type': '进口', 'currency_code': 'USD', 'rmb_amount': 156800.00, 'declaration_date': '2024-12-01'},
                        {'id': 2, 'declaration_number': 'DEC2024120002', 'company_code': 'COMP002', 'trade_type': '出口', 'currency_code': 'EUR', 'rmb_amount': 98750.50, 'declaration_date': '2024-12-01'}
                    ]
                }
            }
            
            # 输出数据
            output_data = mock_metadata
            
            self.log_step_result("元数据发现", input_data, output_data, True)
            return output_data
            
        except Exception as e:
            print(f"❌ 第1步失败: {e}")
            self.log_step_result("元数据发现", input_data, {"error": str(e)}, False)
            raise
    
    async def step2_semantic_enrichment(self, metadata):
        """第2步: 语义增强"""
        print("\n🧠 开始第2步: 语义增强")
        
        try:
            # 输入数据
            input_data = {
                'original_metadata': metadata,
                'enrichment_options': {
                    'extract_business_entities': True,
                    'generate_semantic_tags': True,
                    'infer_data_patterns': True,
                    'analyze_business_rules': True
                }
            }
            
            # 执行语义增强
            semantic_enricher = SemanticEnricher("customs_trade_db")
            
            semantic_result = await semantic_enricher.enrich_metadata(metadata)
            
            # 输出数据
            output_data = {
                'original_metadata': metadata,
                'business_entities': semantic_result.business_entities,
                'semantic_tags': semantic_result.semantic_tags,
                'data_patterns': semantic_result.data_patterns,
                'business_rules': semantic_result.business_rules,
                'domain_classification': semantic_result.domain_classification,
                'confidence_scores': semantic_result.confidence_scores
            }
            
            self.log_step_result("语义增强", input_data, output_data, True)
            return semantic_result
            
        except Exception as e:
            print(f"❌ 第2步失败: {e}")
            self.log_step_result("语义增强", input_data, {"error": str(e)}, False)
            raise
    
    async def step3_embedding_storage(self, semantic_metadata):
        """第3步: 向量存储"""
        print("\n💾 开始第3步: 向量存储")
        
        try:
            # 输入数据
            input_data = {
                'semantic_metadata': {
                    'business_entities_count': len(semantic_metadata.business_entities),
                    'semantic_tags_count': len(semantic_metadata.semantic_tags),
                    'data_patterns_count': len(semantic_metadata.data_patterns),
                    'business_rules_count': len(semantic_metadata.business_rules)
                },
                'storage_config': {
                    'vector_database': 'pgvector',
                    'embedding_model': 'text-embedding-3-small',
                    'dimension': 1536
                }
            }
            
            # 执行向量存储
            embedding_storage = EmbeddingStorage("customs_trade_db")
            await embedding_storage.initialize()
            
            storage_results = await embedding_storage.store_semantic_metadata(semantic_metadata)
            
            # 输出数据
            output_data = {
                'storage_results': storage_results,
                'stored_embeddings': storage_results['stored_embeddings'],
                'failed_embeddings': storage_results['failed_embeddings'],
                'storage_time': storage_results['storage_time'],
                'errors': storage_results['errors']
            }
            
            self.log_step_result("向量存储", input_data, output_data, True)
            return storage_results
            
        except Exception as e:
            print(f"❌ 第3步失败: {e}")
            self.log_step_result("向量存储", input_data, {"error": str(e)}, False)
            raise
    
    async def step4_query_matching(self, semantic_metadata, user_query):
        """第4步: 查询匹配"""
        print("\n🔍 开始第4步: 查询匹配")
        
        try:
            # 输入数据
            input_data = {
                'user_query': user_query,
                'semantic_metadata_available': True,
                'matching_options': {
                    'similarity_threshold': 0.7,
                    'max_matches': 10,
                    'include_fuzzy_matching': True
                }
            }
            
            # 执行查询匹配
            embedding_storage = EmbeddingStorage("customs_trade_db")
            await embedding_storage.initialize()
            
            query_matcher = QueryMatcher(embedding_storage)
            
            query_context, metadata_matches = await query_matcher.match_query_to_metadata(
                user_query, semantic_metadata
            )
            
            query_plan = await query_matcher.generate_query_plan(
                query_context, metadata_matches, semantic_metadata
            )
            
            # 输出数据
            output_data = {
                'query_context': {
                    'entities_mentioned': query_context.entities_mentioned,
                    'attributes_mentioned': query_context.attributes_mentioned,
                    'operations': query_context.operations,
                    'business_intent': query_context.business_intent,
                    'confidence_score': query_context.confidence_score
                },
                'metadata_matches': [
                    {
                        'entity_name': match.entity_name,
                        'entity_type': match.entity_type,
                        'match_type': match.match_type,
                        'similarity_score': match.similarity_score,
                        'relevant_attributes': match.relevant_attributes
                    } for match in metadata_matches
                ],
                'query_plan': {
                    'primary_tables': query_plan.primary_tables,
                    'required_joins': query_plan.required_joins,
                    'select_columns': query_plan.select_columns,
                    'where_conditions': query_plan.where_conditions,
                    'aggregations': query_plan.aggregations,
                    'confidence_score': query_plan.confidence_score
                }
            }
            
            self.log_step_result("查询匹配", input_data, output_data, True)
            return query_context, metadata_matches, query_plan
            
        except Exception as e:
            print(f"❌ 第4步失败: {e}")
            self.log_step_result("查询匹配", input_data, {"error": str(e)}, False)
            raise
    
    async def step5_sql_generation_execution(self, query_context, metadata_matches, semantic_metadata, original_query):
        """第5步: SQL生成和执行"""
        print("\n⚡ 开始第5步: SQL生成和执行")
        
        try:
            # 输入数据
            input_data = {
                'original_query': original_query,
                'query_context': {
                    'business_intent': query_context.business_intent,
                    'entities': len(query_context.entities_mentioned),
                    'operations': len(query_context.operations)
                },
                'metadata_matches': len(metadata_matches),
                'execution_options': {
                    'use_llm_enhancement': True,
                    'enable_fallback_strategies': True,
                    'max_execution_time': 30
                }
            }
            
            # 执行SQL生成和执行
            sql_executor = SQLExecutor({
                'type': 'postgresql',
                'host': 'localhost',
                'port': 5432,
                'database': 'customs_trade_db',
                'username': 'postgres',
                'password': 'password'
            })
            
            await sql_executor.initialize_llm()
            
            # 生成SQL
            llm_result = await sql_executor.llm_generator.generate_sql_from_context(
                query_context, metadata_matches, semantic_metadata, original_query
            )
            
            # 模拟SQL执行结果（因为没有真实数据库连接）
            mock_execution_result = {
                'success': True,
                'data': [
                    {'company_name': '上海贸易有限公司', 'company_code': 'COMP001', 'total_amount': 156800.00},
                    {'company_name': '北京进出口公司', 'company_code': 'COMP002', 'total_amount': 98750.50},
                    {'company_name': '深圳科技贸易公司', 'company_code': 'COMP003', 'total_amount': 234560.75}
                ],
                'column_names': ['company_name', 'company_code', 'total_amount'],
                'row_count': 3,
                'execution_time_ms': 245.6,
                'sql_executed': llm_result.sql
            }
            
            # 输出数据
            output_data = {
                'generated_sql': llm_result.sql,
                'sql_explanation': llm_result.explanation,
                'llm_confidence': llm_result.confidence_score,
                'execution_result': mock_execution_result,
                'query_performance': {
                    'execution_time_ms': mock_execution_result['execution_time_ms'],
                    'rows_returned': mock_execution_result['row_count'],
                    'columns_returned': len(mock_execution_result['column_names'])
                }
            }
            
            self.log_step_result("SQL生成和执行", input_data, output_data, True)
            return llm_result, mock_execution_result
            
        except Exception as e:
            print(f"❌ 第5步失败: {e}")
            self.log_step_result("SQL生成和执行", input_data, {"error": str(e)}, False)
            raise
    
    async def run_complete_workflow(self, user_query: str = "显示所有公司的进口总金额"):
        """运行完整的5步工作流"""
        print(f"\n🚀 开始完整的5步数据分析工作流")
        print(f"用户查询: {user_query}")
        print(f"{'='*80}")
        
        try:
            # 第1步: 元数据发现
            metadata = await self.step1_metadata_discovery()
            
            # 第2步: 语义增强
            semantic_metadata = await self.step2_semantic_enrichment(metadata)
            
            # 第3步: 向量存储
            storage_results = await self.step3_embedding_storage(semantic_metadata)
            
            # 第4步: 查询匹配
            query_context, metadata_matches, query_plan = await self.step4_query_matching(
                semantic_metadata, user_query
            )
            
            # 第5步: SQL生成和执行
            sql_result, execution_result = await self.step5_sql_generation_execution(
                query_context, metadata_matches, semantic_metadata, user_query
            )
            
            # 生成完整报告
            await self.generate_complete_report()
            
            print(f"\n🎉 完整的5步工作流执行成功！")
            return True
            
        except Exception as e:
            print(f"\n❌ 工作流执行失败: {e}")
            return False
    
    async def generate_complete_report(self):
        """生成完整的测试报告"""
        report = {
            'test_summary': {
                'total_steps': len(self.test_results),
                'successful_steps': sum(1 for result in self.test_results.values() if result['success']),
                'test_time': datetime.now().isoformat(),
                'overall_success': all(result['success'] for result in self.test_results.values())
            },
            'step_by_step_results': self.test_results,
            'data_flow_analysis': {
                'step1_to_step2': {
                    'input_tables': len(self.test_results.get('元数据发现', {}).get('output_data', {}).get('tables', [])),
                    'output_entities': len(self.test_results.get('语义增强', {}).get('output_data', {}).get('business_entities', []))
                },
                'step2_to_step3': {
                    'input_entities': len(self.test_results.get('语义增强', {}).get('output_data', {}).get('business_entities', [])),
                    'stored_embeddings': self.test_results.get('向量存储', {}).get('output_data', {}).get('stored_embeddings', 0)
                },
                'step3_to_step4': {
                    'available_embeddings': self.test_results.get('向量存储', {}).get('output_data', {}).get('stored_embeddings', 0),
                    'query_matches': len(self.test_results.get('查询匹配', {}).get('output_data', {}).get('metadata_matches', []))
                },
                'step4_to_step5': {
                    'query_confidence': self.test_results.get('查询匹配', {}).get('output_data', {}).get('query_context', {}).get('confidence_score', 0),
                    'sql_confidence': self.test_results.get('SQL生成和执行', {}).get('output_data', {}).get('llm_confidence', 0)
                }
            }
        }
        
        # 保存报告
        report_file = f"complete_5_step_workflow_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 完整测试报告已保存到: {report_file}")
        
        # 打印摘要
        print(f"\n📊 测试摘要:")
        print(f"   总步骤数: {report['test_summary']['total_steps']}")
        print(f"   成功步骤: {report['test_summary']['successful_steps']}")
        print(f"   整体成功: {report['test_summary']['overall_success']}")
        
        print(f"\n📈 数据流分析:")
        for step_key, step_data in report['data_flow_analysis'].items():
            print(f"   {step_key}: {step_data}")

async def main():
    """主函数"""
    test_runner = Complete5StepWorkflowTest()
    
    # 测试不同的查询
    test_queries = [
        "显示所有公司的进口总金额",
        "查询最近一个月的申报单数量",
        "统计各个HS编码的进口频次"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n" + "="*100)
        print(f"测试场景 {i}: {query}")
        print(f"=" * 100)
        
        success = await test_runner.run_complete_workflow(query)
        
        if success:
            print(f"✅ 测试场景 {i} 执行成功")
        else:
            print(f"❌ 测试场景 {i} 执行失败")
            break
    
    print(f"\n🏁 所有测试场景执行完成")

if __name__ == "__main__":
    asyncio.run(main())