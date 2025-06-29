#!/usr/bin/env python3
"""
Real PostgreSQL Adapter Test
使用真实海关贸易数据测试PostgreSQL适配器
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tools.services.data_analytics_service.adapters.database_adapters.postgresql_adapter import PostgreSQLAdapter
from tools.services.data_analytics_service.core.metadata_extractor import TableInfo, ColumnInfo, RelationshipInfo, IndexInfo

# 真实数据库配置
REAL_DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "customs_trade_db",
    "username": "xenodennis",
    "password": "",
    "include_data_analysis": True,
    "sample_size": 100
}

def test_postgresql_connection():
    """测试PostgreSQL连接功能"""
    print("🔌 测试PostgreSQL连接...")
    
    adapter = PostgreSQLAdapter()
    
    # 测试连接
    connection_result = adapter.connect(REAL_DB_CONFIG)
    if not connection_result:
        print("❌ 数据库连接失败")
        return False
    
    print("✅ 数据库连接成功")
    
    # 测试连接状态
    if not adapter.test_connection():
        print("❌ 连接状态检查失败")
        return False
    
    print("✅ 连接状态正常")
    
    # 获取数据库信息
    db_info = adapter.get_database_info()
    print(f"📊 数据库信息:")
    print(f"   - 类型: {db_info.get('database_type', 'Unknown')}")
    print(f"   - 连接状态: {db_info.get('connected', False)}")
    print(f"   - 数据库名: {db_info.get('database_name', 'Unknown')}")
    
    # 获取版本信息
    version = adapter.get_database_version()
    print(f"   - 版本: {version}")
    
    adapter.disconnect()
    print("✅ PostgreSQL连接测试通过")
    return True

def test_get_tables():
    """测试获取表信息"""
    print("\n📋 测试获取表信息...")
    
    adapter = PostgreSQLAdapter()
    if not adapter.connect(REAL_DB_CONFIG):
        print("❌ 数据库连接失败")
        return False
    
    # 获取所有表
    tables = adapter.get_tables()
    
    if not isinstance(tables, list):
        print("❌ 返回的表信息格式错误")
        return False
    
    print(f"✅ 成功获取 {len(tables)} 个表:")
    
    # 检查关键表是否存在
    expected_tables = ['companies', 'declarations', 'goods_details', 'hs_codes', 'ports']
    table_names = [t.table_name for t in tables]
    
    for expected_table in expected_tables:
        if expected_table in table_names:
            print(f"   ✅ {expected_table}")
        else:
            print(f"   ❌ 缺少表: {expected_table}")
            adapter.disconnect()
            return False
    
    # 显示表的详细信息
    print("\n📊 主要表的详细信息:")
    for table in tables:
        if table.table_name in expected_tables:
            print(f"   - {table.table_name}:")
            print(f"     * 类型: {table.table_type}")
            print(f"     * Schema: {table.schema_name}")
            print(f"     * 记录数: {table.record_count}")
            
            # 验证TableInfo对象结构
            if not isinstance(table, TableInfo):
                print(f"     ❌ 表信息对象类型错误")
                adapter.disconnect()
                return False
    
    adapter.disconnect()
    print("✅ 表信息测试通过")
    return True

def test_get_columns():
    """测试获取字段信息"""
    print("\n🏷️ 测试获取字段信息...")
    
    adapter = PostgreSQLAdapter()
    if not adapter.connect(REAL_DB_CONFIG):
        print("❌ 数据库连接失败")
        return False
    
    # 测试companies表的字段
    test_table = 'companies'
    columns = adapter.get_columns(test_table)
    
    if not isinstance(columns, list):
        print(f"❌ {test_table}表字段信息格式错误")
        adapter.disconnect()
        return False
    
    print(f"✅ {test_table}表有 {len(columns)} 个字段:")
    
    # 检查关键字段
    expected_columns = ['company_code', 'company_name', 'company_type', 'credit_level']
    column_names = [c.column_name for c in columns]
    
    for expected_col in expected_columns:
        if expected_col in column_names:
            print(f"   ✅ {expected_col}")
        else:
            print(f"   ❌ 缺少字段: {expected_col}")
            adapter.disconnect()
            return False
    
    # 显示字段详细信息
    print(f"\n📝 {test_table}表字段详情:")
    for column in columns[:8]:  # 显示前8个字段
        print(f"   - {column.column_name}:")
        print(f"     * 类型: {column.data_type}")
        print(f"     * 可空: {column.is_nullable}")
        print(f"     * 位置: {column.ordinal_position}")
        
        # 验证ColumnInfo对象结构
        if not isinstance(column, ColumnInfo):
            print(f"     ❌ 字段信息对象类型错误")
            adapter.disconnect()
            return False
    
    if len(columns) > 8:
        print(f"   ... 还有 {len(columns) - 8} 个字段")
    
    adapter.disconnect()
    print("✅ 字段信息测试通过")
    return True

def test_get_relationships():
    """测试获取关系信息"""
    print("\n🔗 测试获取关系信息...")
    
    adapter = PostgreSQLAdapter()
    if not adapter.connect(REAL_DB_CONFIG):
        print("❌ 数据库连接失败")
        return False
    
    # 获取所有关系
    relationships = adapter.get_relationships()
    
    if not isinstance(relationships, list):
        print("❌ 返回的关系信息格式错误")
        adapter.disconnect()
        return False
    
    print(f"✅ 成功获取 {len(relationships)} 个外键关系:")
    
    # 显示关系信息
    for rel in relationships[:10]:  # 显示前10个关系
        print(f"   - {rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column}")
        print(f"     约束类型: {rel.constraint_type}")
        
        # 验证RelationshipInfo对象结构
        if not isinstance(rel, RelationshipInfo):
            print(f"     ❌ 关系信息对象类型错误")
            adapter.disconnect()
            return False
    
    if len(relationships) > 10:
        print(f"   ... 还有 {len(relationships) - 10} 个关系")
    
    # 检查关键关系
    expected_relationships = [
        ('declarations', 'company_code', 'companies', 'company_code'),
        ('goods_details', 'declaration_no', 'declarations', 'declaration_no'),
        ('goods_details', 'hs_code', 'hs_codes', 'hs_code')
    ]
    
    found_relationships = []
    for rel in relationships:
        rel_tuple = (rel.from_table, rel.from_column, rel.to_table, rel.to_column)
        if rel_tuple in expected_relationships:
            found_relationships.append(rel_tuple)
    
    print(f"\n✅ 找到 {len(found_relationships)} 个预期的关键关系")
    for rel_tuple in found_relationships:
        print(f"   ✅ {rel_tuple[0]}.{rel_tuple[1]} -> {rel_tuple[2]}.{rel_tuple[3]}")
    
    adapter.disconnect()
    print("✅ 关系信息测试通过")
    return True

def test_get_indexes():
    """测试获取索引信息"""
    print("\n📇 测试获取索引信息...")
    
    adapter = PostgreSQLAdapter()
    if not adapter.connect(REAL_DB_CONFIG):
        print("❌ 数据库连接失败")
        return False
    
    # 测试companies表的索引
    test_table = 'companies'
    indexes = adapter.get_indexes(test_table)
    
    if not isinstance(indexes, list):
        print(f"❌ {test_table}表索引信息格式错误")
        adapter.disconnect()
        return False
    
    print(f"✅ {test_table}表有 {len(indexes)} 个索引:")
    
    # 查找主键索引
    primary_key_found = False
    for idx in indexes:
        print(f"   - {idx.index_name}:")
        print(f"     * 字段: {', '.join(idx.column_names)}")
        print(f"     * 主键: {idx.is_primary}")
        print(f"     * 唯一: {idx.is_unique}")
        
        if idx.is_primary:
            primary_key_found = True
            if 'company_code' not in idx.column_names:
                print(f"     ❌ 主键应该包含company_code字段")
                adapter.disconnect()
                return False
        
        # 验证IndexInfo对象结构
        if not isinstance(idx, IndexInfo):
            print(f"     ❌ 索引信息对象类型错误")
            adapter.disconnect()
            return False
    
    if not primary_key_found:
        print(f"   ❌ 未找到主键索引")
        adapter.disconnect()
        return False
    
    print(f"   ✅ 主键索引验证通过")
    
    adapter.disconnect()
    print("✅ 索引信息测试通过")
    return True

def test_data_analysis():
    """测试数据分析功能"""
    print("\n📊 测试数据分析功能...")
    
    adapter = PostgreSQLAdapter()
    if not adapter.connect(REAL_DB_CONFIG):
        print("❌ 数据库连接失败")
        return False
    
    # 测试数值字段分析
    test_table = 'declarations'
    test_column = 'rmb_amount'
    
    analysis = adapter.analyze_data_distribution(test_table, test_column)
    
    if not isinstance(analysis, dict):
        print(f"❌ 数据分析结果格式错误")
        adapter.disconnect()
        return False
    
    if 'error' in analysis:
        print(f"❌ 数据分析出错: {analysis['error']}")
        adapter.disconnect()
        return False
    
    print(f"✅ {test_table}.{test_column} 数据分析结果:")
    print(f"   - 总记录数: {analysis.get('total_count', 'N/A')}")
    print(f"   - 唯一值数: {analysis.get('unique_count', 'N/A')}")
    print(f"   - 空值比例: {analysis.get('null_percentage', 'N/A')}%")
    
    if 'min_value' in analysis:
        print(f"   - 最小值: {analysis['min_value']}")
        print(f"   - 最大值: {analysis['max_value']}")
        print(f"   - 平均值: {analysis.get('avg_value', 'N/A')}")
    
    # 显示样本数据
    sample_values = analysis.get('sample_values', [])
    if sample_values:
        print(f"   - 样本值: {sample_values[:5]}")
    
    adapter.disconnect()
    print("✅ 数据分析测试通过")
    return True

def test_sample_data():
    """测试获取样本数据"""
    print("\n🔍 测试获取样本数据...")
    
    adapter = PostgreSQLAdapter()
    if not adapter.connect(REAL_DB_CONFIG):
        print("❌ 数据库连接失败")
        return False
    
    # 获取companies表的样本数据
    test_table = 'companies'
    sample_size = 5
    
    sample_data = adapter.get_sample_data(test_table, sample_size)
    
    if not isinstance(sample_data, list):
        print(f"❌ 样本数据格式错误")
        adapter.disconnect()
        return False
    
    if sample_data and 'error' in sample_data[0]:
        print(f"❌ 获取样本数据出错: {sample_data[0]['error']}")
        adapter.disconnect()
        return False
    
    print(f"✅ 成功获取 {len(sample_data)} 条 {test_table} 样本数据:")
    
    for i, record in enumerate(sample_data):
        if not isinstance(record, dict):
            print(f"❌ 记录格式错误")
            adapter.disconnect()
            return False
        
        print(f"   {i+1}. 企业: {record.get('company_name', 'N/A')}")
        print(f"      类型: {record.get('company_type', 'N/A')}")
        print(f"      信用等级: {record.get('credit_level', 'N/A')}")
        
        # 验证必要字段
        if 'company_code' not in record or 'company_name' not in record:
            print(f"❌ 缺少必要字段")
            adapter.disconnect()
            return False
    
    adapter.disconnect()
    print("✅ 样本数据测试通过")
    return True

def test_table_size():
    """测试获取表大小信息"""
    print("\n📏 测试获取表大小信息...")
    
    adapter = PostgreSQLAdapter()
    if not adapter.connect(REAL_DB_CONFIG):
        print("❌ 数据库连接失败")
        return False
    
    # 测试几个主要表的大小
    test_tables = ['companies', 'declarations', 'goods_details']
    
    for table_name in test_tables:
        size_info = adapter.get_table_size(table_name)
        
        if not isinstance(size_info, dict):
            print(f"❌ {table_name}表大小信息格式错误")
            continue
        
        if 'error' in size_info:
            print(f"❌ 获取{table_name}表大小出错: {size_info['error']}")
            continue
        
        print(f"✅ {table_name}表大小信息:")
        print(f"   - 总大小: {size_info.get('total_size', 'N/A')}")
        print(f"   - 表大小: {size_info.get('table_size', 'N/A')}")
        print(f"   - 索引大小: {size_info.get('index_size', 'N/A')}")
    
    adapter.disconnect()
    print("✅ 表大小测试通过")
    return True

def test_full_metadata_extraction():
    """测试完整元数据提取"""
    print("\n🎯 测试完整元数据提取...")
    
    adapter = PostgreSQLAdapter()
    
    # 提取完整元数据
    metadata = adapter.extract_full_metadata(REAL_DB_CONFIG)
    
    if not isinstance(metadata, dict):
        print("❌ 元数据格式错误")
        return False
    
    # 验证元数据结构
    required_keys = ['source_info', 'tables', 'columns', 'relationships', 'indexes']
    for key in required_keys:
        if key not in metadata:
            print(f"❌ 缺少元数据键: {key}")
            return False
    
    print("✅ 元数据结构验证通过")
    
    # 验证数据内容
    tables = metadata['tables']
    columns = metadata['columns']
    relationships = metadata['relationships']
    indexes = metadata['indexes']
    
    print(f"📊 元数据统计:")
    print(f"   - 表数量: {len(tables)}")
    print(f"   - 字段数量: {len(columns)}")
    print(f"   - 关系数量: {len(relationships)}")
    print(f"   - 索引数量: {len(indexes)}")
    
    # 验证关键表存在
    table_names = [t['table_name'] for t in tables]
    expected_tables = ['companies', 'declarations', 'goods_details', 'hs_codes']
    
    for expected_table in expected_tables:
        if expected_table in table_names:
            print(f"   ✅ 包含表: {expected_table}")
        else:
            print(f"   ❌ 缺少表: {expected_table}")
            return False
    
    # 验证companies表的字段
    companies_columns = [c for c in columns if c['table_name'] == 'companies']
    if len(companies_columns) == 0:
        print("❌ 未找到companies表的字段")
        return False
    
    companies_column_names = [c['column_name'] for c in companies_columns]
    expected_columns = ['company_code', 'company_name', 'company_type']
    
    for expected_col in expected_columns:
        if expected_col in companies_column_names:
            print(f"   ✅ 包含字段: companies.{expected_col}")
        else:
            print(f"   ❌ 缺少字段: companies.{expected_col}")
            return False
    
    print("✅ 完整元数据提取测试通过")
    return True

def main():
    """主测试函数"""
    print("🚀 开始PostgreSQL适配器真实数据测试")
    print("=" * 60)
    print(f"测试数据库: {REAL_DB_CONFIG['database']}")
    print()
    
    tests = [
        ("PostgreSQL连接", test_postgresql_connection),
        ("获取表信息", test_get_tables),
        ("获取字段信息", test_get_columns),
        ("获取关系信息", test_get_relationships),
        ("获取索引信息", test_get_indexes),
        ("数据分析功能", test_data_analysis),
        ("获取样本数据", test_sample_data),
        ("获取表大小", test_table_size),
        ("完整元数据提取", test_full_metadata_extraction),
    ]
    
    passed_tests = 0
    failed_tests = 0
    
    for test_name, test_func in tests:
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
    
    if failed_tests == 0:
        print("\n🎉 所有PostgreSQL适配器测试通过!")
        return True
    else:
        print(f"\n⚠️ 有 {failed_tests} 个测试失败，需要检查")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)