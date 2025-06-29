#!/usr/bin/env python3
"""
Real Metadata Service Test
使用真实海关贸易数据测试元数据发现服务
"""

import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tools.services.data_analytics_service.services.metadata_service import MetadataDiscoveryService
from tools.services.data_analytics_service.utils.error_handler import DataAnalyticsError

# 真实数据库配置
REAL_DB_CONFIG = {
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "customs_trade_db",
    "username": "xenodennis",
    "password": "",
    "include_data_analysis": True,
    "sample_size": 1000
}

def test_discover_database_metadata():
    """测试数据库元数据发现"""
    print("🔍 测试数据库元数据发现...")
    
    service = MetadataDiscoveryService()
    
    try:
        metadata = service.discover_database_metadata(REAL_DB_CONFIG)
        
        # 验证基本结构
        if not isinstance(metadata, dict):
            print("❌ 元数据格式错误")
            return False
        
        required_keys = ['source_info', 'tables', 'columns', 'relationships', 'indexes', 'discovery_info']
        for key in required_keys:
            if key not in metadata:
                print(f"❌ 缺少必要键: {key}")
                return False
        
        print("✅ 元数据结构验证通过")
        
        # 验证发现信息
        discovery_info = metadata['discovery_info']
        if discovery_info['service'] != 'MetadataDiscoveryService':
            print(f"❌ 服务名称错误: {discovery_info['service']}")
            return False
        
        if discovery_info['source_type'] != 'database':
            print(f"❌ 源类型错误: {discovery_info['source_type']}")
            return False
        
        if discovery_info['source_subtype'] != 'postgresql':
            print(f"❌ 源子类型错误: {discovery_info['source_subtype']}")
            return False
        
        print("✅ 发现信息验证通过")
        
        # 验证表信息
        tables = metadata['tables']
        expected_tables = ['companies', 'declarations', 'goods_details', 'hs_codes', 'ports']
        table_names = [t['table_name'] for t in tables]
        
        print(f"📋 发现 {len(tables)} 个表:")
        for expected_table in expected_tables:
            if expected_table in table_names:
                print(f"   ✅ {expected_table}")
            else:
                print(f"   ❌ 缺少表: {expected_table}")
                return False
        
        # 验证字段信息
        columns = metadata['columns']
        if len(columns) == 0:
            print("❌ 未发现任何字段")
            return False
        
        print(f"🏷️ 发现 {len(columns)} 个字段")
        
        # 验证companies表的关键字段
        companies_columns = [c for c in columns if c['table_name'] == 'companies']
        companies_column_names = [c['column_name'] for c in companies_columns]
        expected_columns = ['company_code', 'company_name', 'company_type', 'credit_level']
        
        for expected_col in expected_columns:
            if expected_col in companies_column_names:
                print(f"   ✅ companies.{expected_col}")
            else:
                print(f"   ❌ 缺少字段: companies.{expected_col}")
                return False
        
        # 验证关系信息
        relationships = metadata['relationships']
        print(f"🔗 发现 {len(relationships)} 个关系")
        
        if relationships:
            for rel in relationships[:3]:  # 显示前3个关系
                print(f"   - {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']}")
                
                required_rel_keys = ['from_table', 'to_table', 'constraint_type']
                for key in required_rel_keys:
                    if key not in rel:
                        print(f"❌ 关系缺少键: {key}")
                        return False
        
        print("✅ 数据库元数据发现测试通过")
        return True, metadata
        
    except Exception as e:
        print(f"❌ 数据库元数据发现测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_get_summary_statistics(metadata):
    """测试获取汇总统计"""
    print("\n📊 测试获取汇总统计...")
    
    service = MetadataDiscoveryService()
    
    try:
        summary = service.get_summary_statistics(metadata)
        
        # 验证汇总结构
        if not isinstance(summary, dict):
            print("❌ 汇总统计格式错误")
            return False
        
        required_keys = ['totals', 'table_statistics', 'column_statistics', 'relationship_statistics', 'data_quality_overview']
        for key in required_keys:
            if key not in summary:
                print(f"❌ 缺少汇总键: {key}")
                return False
        
        print("✅ 汇总统计结构验证通过")
        
        # 验证totals
        totals = summary['totals']
        print(f"📈 数据总计:")
        print(f"   - 表数量: {totals.get('tables', 0)}")
        print(f"   - 字段数量: {totals.get('columns', 0)}")
        print(f"   - 关系数量: {totals.get('relationships', 0)}")
        
        if not all(isinstance(totals.get(key, 0), int) for key in ['tables', 'columns', 'relationships']):
            print("❌ totals数据类型错误")
            return False
        
        # 验证表统计
        table_stats = summary['table_statistics']
        if table_stats:
            print(f"📋 表统计信息:")
            if 'total_records' in table_stats:
                print(f"   - 总记录数: {table_stats['total_records']}")
            if 'avg_records_per_table' in table_stats:
                print(f"   - 平均每表记录数: {table_stats['avg_records_per_table']:.1f}")
        
        # 验证字段统计
        column_stats = summary['column_statistics']
        if column_stats:
            print(f"🏷️ 字段统计信息:")
            if 'total_columns' in column_stats:
                print(f"   - 总字段数: {column_stats['total_columns']}")
            if 'data_type_distribution' in column_stats:
                print(f"   - 数据类型分布: {len(column_stats['data_type_distribution'])} 种类型")
        
        print("✅ 汇总统计测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 汇总统计测试失败: {e}")
        return False

def test_export_metadata_json(metadata):
    """测试导出元数据到JSON"""
    print("\n💾 测试导出元数据到JSON...")
    
    service = MetadataDiscoveryService()
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
        output_path = tmp_file.name
    
    try:
        # 导出元数据
        success = service.export_metadata(metadata, output_path, 'json')
        
        if not success:
            print("❌ 导出操作失败")
            return False
        
        # 验证文件存在
        output_file = Path(output_path)
        if not output_file.exists():
            print("❌ 输出文件不存在")
            return False
        
        print(f"✅ 文件已导出: {output_file.name}")
        print(f"   文件大小: {output_file.stat().st_size} 字节")
        
        # 验证JSON内容
        with open(output_path, 'r', encoding='utf-8') as f:
            loaded_metadata = json.load(f)
        
        # 验证加载的元数据结构
        required_keys = ['source_info', 'tables', 'columns']
        for key in required_keys:
            if key not in loaded_metadata:
                print(f"❌ 导出文件缺少键: {key}")
                return False
        
        print("✅ JSON导出内容验证通过")
        
        # 验证数据一致性
        if len(loaded_metadata['tables']) != len(metadata['tables']):
            print("❌ 导出的表数量不一致")
            return False
        
        if len(loaded_metadata['columns']) != len(metadata['columns']):
            print("❌ 导出的字段数量不一致")
            return False
        
        print("✅ 数据一致性验证通过")
        print("✅ JSON导出测试通过")
        return True
        
    except Exception as e:
        print(f"❌ JSON导出测试失败: {e}")
        return False
    finally:
        # 清理临时文件
        try:
            Path(output_path).unlink()
        except:
            pass

def test_export_metadata_csv(metadata):
    """测试导出元数据到CSV"""
    print("\n📄 测试导出元数据到CSV...")
    
    service = MetadataDiscoveryService()
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
        output_path = tmp_file.name
    
    try:
        # 导出元数据
        success = service.export_metadata(metadata, output_path, 'csv')
        
        if not success:
            print("❌ CSV导出操作失败")
            return False
        
        # 验证生成的文件
        tables_path = output_path.replace('.csv', '_tables.csv')
        columns_path = output_path.replace('.csv', '_columns.csv')
        
        files_to_check = [
            (tables_path, "表信息"),
            (columns_path, "字段信息")
        ]
        
        for file_path, description in files_to_check:
            file_obj = Path(file_path)
            if not file_obj.exists():
                print(f"❌ {description}文件不存在: {file_obj.name}")
                return False
            
            file_size = file_obj.stat().st_size
            if file_size == 0:
                print(f"❌ {description}文件为空")
                return False
            
            print(f"✅ {description}文件: {file_obj.name} ({file_size} 字节)")
        
        print("✅ CSV导出测试通过")
        return True
        
    except Exception as e:
        print(f"❌ CSV导出测试失败: {e}")
        return False
    finally:
        # 清理临时文件
        cleanup_paths = [
            output_path,
            output_path.replace('.csv', '_tables.csv'),
            output_path.replace('.csv', '_columns.csv'),
            output_path.replace('.csv', '_relationships.csv')
        ]
        
        for path in cleanup_paths:
            try:
                Path(path).unlink()
            except:
                pass

def test_compare_schemas():
    """测试架构比较"""
    print("\n🔄 测试架构比较...")
    
    service = MetadataDiscoveryService()
    
    try:
        # 获取同一个数据库的元数据进行比较
        metadata1 = service.discover_database_metadata(REAL_DB_CONFIG)
        metadata2 = service.discover_database_metadata(REAL_DB_CONFIG)
        
        # 比较架构
        comparison = service.compare_schemas(metadata1, metadata2)
        
        # 验证比较结构
        if not isinstance(comparison, dict):
            print("❌ 比较结果格式错误")
            return False
        
        required_keys = ['comparison_time', 'source1_info', 'source2_info', 'table_comparison', 'column_comparison', 'relationship_comparison']
        for key in required_keys:
            if key not in comparison:
                print(f"❌ 缺少比较键: {key}")
                return False
        
        print("✅ 比较结构验证通过")
        
        # 验证表比较
        table_comp = comparison['table_comparison']
        print(f"📋 表比较结果:")
        print(f"   - 源1表数: {table_comp.get('total_source1', 0)}")
        print(f"   - 源2表数: {table_comp.get('total_source2', 0)}")
        print(f"   - 相似度: {table_comp.get('similarity_score', 0):.2f}")
        
        if not isinstance(table_comp.get('similarity_score'), (int, float)):
            print("❌ 表相似度分数类型错误")
            return False
        
        # 同一数据源应该有100%相似度
        if table_comp.get('similarity_score') != 1.0:
            print("❌ 同一数据源比较相似度应该是1.0")
            return False
        
        # 验证关系比较
        rel_comp = comparison['relationship_comparison']
        print(f"🔗 关系比较结果:")
        print(f"   - 源1关系数: {rel_comp.get('total_source1', 0)}")
        print(f"   - 源2关系数: {rel_comp.get('total_source2', 0)}")
        print(f"   - 相似度: {rel_comp.get('similarity_score', 0):.2f}")
        
        if rel_comp.get('similarity_score') != 1.0:
            print("❌ 同一数据源关系比较相似度应该是1.0")
            return False
        
        print("✅ 架构比较测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 架构比较测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_validation_errors():
    """测试验证和错误处理"""
    print("\n⚠️ 测试验证和错误处理...")
    
    service = MetadataDiscoveryService()
    
    # 测试无效的数据库配置
    invalid_db_config = {
        "type": "postgresql",
        # 缺少必要字段
    }
    
    try:
        service.discover_database_metadata(invalid_db_config)
        print("❌ 应该抛出错误但没有")
        return False
    except DataAnalyticsError:
        print("✅ 无效数据库配置正确抛出DataAnalyticsError")
    except Exception as e:
        print(f"❌ 抛出了错误的异常类型: {type(e)}")
        return False
    
    # 测试不支持的数据库类型
    unsupported_db_config = {
        "type": "unsupported_db",
        "host": "localhost",
        "database": "test",
        "username": "user",
        "password": "pass"
    }
    
    try:
        service.discover_database_metadata(unsupported_db_config)
        print("❌ 应该抛出错误但没有")
        return False
    except DataAnalyticsError:
        print("✅ 不支持的数据库类型正确抛出DataAnalyticsError")
    except Exception as e:
        print(f"❌ 抛出了错误的异常类型: {type(e)}")
        return False
    
    # 测试无效的文件配置
    invalid_file_config = {
        "file_path": "/nonexistent/file.csv"
    }
    
    try:
        service.discover_file_metadata(invalid_file_config)
        print("❌ 应该抛出错误但没有")
        return False
    except DataAnalyticsError:
        print("✅ 无效文件配置正确抛出DataAnalyticsError")
    except Exception as e:
        print(f"❌ 抛出了错误的异常类型: {type(e)}")
        return False
    
    print("✅ 验证和错误处理测试通过")
    return True

def test_metadata_service_configuration():
    """测试元数据服务配置"""
    print("\n⚙️ 测试元数据服务配置...")
    
    service = MetadataDiscoveryService()
    
    # 测试支持的数据库
    expected_databases = ['postgresql', 'mysql', 'sqlserver']
    for db_type in expected_databases:
        if db_type not in service.supported_databases:
            print(f"❌ 缺少支持的数据库类型: {db_type}")
            return False
        print(f"✅ 支持数据库: {db_type}")
    
    # 测试支持的文件类型
    expected_files = ['excel', 'csv']
    for file_type in expected_files:
        if file_type not in service.supported_files:
            print(f"❌ 缺少支持的文件类型: {file_type}")
            return False
        print(f"✅ 支持文件: {file_type}")
    
    # 测试服务组件初始化
    if service.config_manager is None:
        print("❌ 配置管理器未初始化")
        return False
    print("✅ 配置管理器已初始化")
    
    if service.data_validator is None:
        print("❌ 数据验证器未初始化")
        return False
    print("✅ 数据验证器已初始化")
    
    print("✅ 元数据服务配置测试通过")
    return True

def main():
    """主测试函数"""
    print("🚀 开始元数据发现服务真实数据测试")
    print("=" * 60)
    print(f"测试数据库: {REAL_DB_CONFIG['database']}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 先测试数据库元数据发现，获取元数据用于后续测试
    print("🔍 执行主要测试：数据库元数据发现")
    success, metadata = test_discover_database_metadata()
    
    if not success:
        print("❌ 主要测试失败，无法继续其他测试")
        return False
    
    # 定义其他测试
    other_tests = [
        ("获取汇总统计", lambda: test_get_summary_statistics(metadata)),
        ("导出JSON格式", lambda: test_export_metadata_json(metadata)),
        ("导出CSV格式", lambda: test_export_metadata_csv(metadata)),
        ("架构比较", test_compare_schemas),
        ("验证和错误处理", test_validation_errors),
        ("服务配置", test_metadata_service_configuration),
    ]
    
    passed_tests = 1  # 主测试已通过
    failed_tests = 0
    
    for test_name, test_func in other_tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            if test_func():
                passed_tests += 1
                print(f"✅ {test_name} 测试通过")
            else:
                failed_tests += 1
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            failed_tests += 1
            print(f"❌ {test_name} 测试异常: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("📊 测试结果汇总")
    print(f"{'='*60}")
    print(f"✅ 通过: {passed_tests}")
    print(f"❌ 失败: {failed_tests}")
    print(f"📈 成功率: {passed_tests/(passed_tests+failed_tests)*100:.1f}%")
    
    # 保存测试结果
    if metadata:
        result_file = f"metadata_service_test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
        print(f"📄 测试结果已保存到: {result_file}")
    
    if failed_tests == 0:
        print("\n🎉 所有元数据服务测试通过!")
        return True
    else:
        print(f"\n⚠️ 有 {failed_tests} 个测试失败，需要检查")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)