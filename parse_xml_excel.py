#!/usr/bin/env python3
"""
解析XML格式的Excel文件并转换为DataFrame
专门处理sales_2y.xls文件
"""

import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
import numpy as np

def parse_xml_excel_to_dataframe(file_path):
    """解析XML格式的Excel文件并转换为DataFrame"""
    print(f"🔍 解析XML Excel文件: {file_path}")
    
    try:
        # 解析XML
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # XML命名空间
        namespaces = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
        
        # 查找工作表
        worksheets = root.findall('.//ss:Worksheet', namespaces)
        print(f"📊 发现 {len(worksheets)} 个工作表")
        
        if not worksheets:
            raise ValueError("未找到工作表")
        
        # 使用第一个工作表
        worksheet = worksheets[0]
        ws_name = worksheet.get('Name', 'Sheet1')
        print(f"📋 处理工作表: {ws_name}")
        
        # 查找表格
        tables = worksheet.findall('.//ss:Table', namespaces)
        if not tables:
            raise ValueError("未找到表格数据")
        
        table = tables[0]
        rows = table.findall('.//ss:Row', namespaces)
        total_rows = len(rows)
        print(f"📈 发现 {total_rows:,} 行数据")
        
        # 解析数据
        data = []
        headers = []
        
        for row_idx, row in enumerate(rows):
            cells = row.findall('.//ss:Cell', namespaces)
            row_data = []
            
            # 处理每个单元格
            for cell in cells:
                data_elem = cell.find('.//ss:Data', namespaces)
                if data_elem is not None and data_elem.text is not None:
                    value = data_elem.text.strip()
                    # 尝试转换数据类型
                    if value.isdigit():
                        value = int(value)
                    elif '.' in value and value.replace('.', '').isdigit():
                        value = float(value)
                    row_data.append(value)
                else:
                    row_data.append(None)
            
            if row_idx == 0:
                # 第一行作为标题
                headers = row_data
                print(f"📋 列名: {headers}")
            else:
                # 确保每行数据长度与标题一致
                while len(row_data) < len(headers):
                    row_data.append(None)
                data.append(row_data[:len(headers)])
            
            # 显示进度
            if row_idx % 50000 == 0 and row_idx > 0:
                print(f"⏳ 已处理 {row_idx:,} 行...")
        
        print(f"✅ 数据解析完成，共 {len(data):,} 行数据")
        
        # 创建DataFrame
        df = pd.DataFrame(data, columns=headers)
        
        # 数据清理和类型转换
        print("🧹 进行数据清理...")
        
        # 转换日期列
        if 'Date' in df.columns:
            print("📅 转换日期格式...")
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
        # 转换数量列
        if 'Sum of Quantity' in df.columns:
            print("🔢 转换数量格式...")
            df['Sum of Quantity'] = pd.to_numeric(df['Sum of Quantity'], errors='coerce')
        
        # 移除空行
        before_rows = len(df)
        df = df.dropna(how='all')
        after_rows = len(df)
        if before_rows > after_rows:
            print(f"🗑️  移除了 {before_rows - after_rows:,} 个空行")
        
        print(f"✨ 最终数据集: {df.shape[0]:,} 行 × {df.shape[1]} 列")
        return df
        
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        return None

def analyze_sales_data(df):
    """分析销售数据"""
    print("\n📊 销售数据分析")
    print("=" * 40)
    
    print(f"📈 数据概览:")
    print(f"   总记录数: {len(df):,}")
    print(f"   数据列: {list(df.columns)}")
    print(f"   数据类型:")
    for col, dtype in df.dtypes.items():
        print(f"     {col}: {dtype}")
    
    print(f"\n🔍 前5行数据:")
    print(df.head())
    
    # 基本统计
    if 'Sum of Quantity' in df.columns:
        print(f"\n📊 销售数量统计:")
        print(df['Sum of Quantity'].describe())
    
    # 市场分析
    if 'Marketplace' in df.columns:
        print(f"\n🏪 市场分布:")
        marketplace_counts = df['Marketplace'].value_counts()
        print(marketplace_counts)
    
    # 时间范围分析
    if 'Date' in df.columns and df['Date'].notna().sum() > 0:
        print(f"\n📅 时间范围:")
        min_date = df['Date'].min()
        max_date = df['Date'].max()
        print(f"   开始日期: {min_date}")
        print(f"   结束日期: {max_date}")
        print(f"   时间跨度: {(max_date - min_date).days} 天")
    
    # 产品分析
    if 'Item' in df.columns:
        print(f"\n🛍️  产品分析:")
        unique_items = df['Item'].nunique()
        print(f"   唯一产品数: {unique_items:,}")
        top_items = df['Item'].value_counts().head(10)
        print(f"   销量前10产品:")
        for item, count in top_items.items():
            print(f"     {item}: {count:,} 次")

def prepare_for_prophet(df):
    """为Prophet准备时间序列数据"""
    print(f"\n🔮 为Prophet时间序列分析准备数据...")
    
    if 'Date' not in df.columns or 'Sum of Quantity' not in df.columns:
        print("❌ 缺少必要的日期或数量列")
        return None
    
    # 按日期聚合销售数据
    daily_sales = df.groupby('Date')['Sum of Quantity'].sum().reset_index()
    daily_sales.columns = ['ds', 'y']  # Prophet要求的列名
    
    # 移除缺失值
    daily_sales = daily_sales.dropna()
    
    print(f"✅ Prophet数据准备完成: {len(daily_sales)} 个数据点")
    print(f"📅 时间范围: {daily_sales['ds'].min()} 到 {daily_sales['ds'].max()}")
    print(f"📊 销售量统计:")
    print(daily_sales['y'].describe())
    
    return daily_sales

def main():
    """主函数"""
    print("🎯 XML Excel文件解析器")
    print("专门处理sales_2y.xls大数据集")
    print("=" * 50)
    
    file_path = "/Users/xenodennis/Documents/Fun/isA_MCP/demo_data/sales_2y.xls"
    
    # 解析XML Excel文件
    df = parse_xml_excel_to_dataframe(file_path)
    
    if df is not None:
        # 分析数据
        analyze_sales_data(df)
        
        # 准备Prophet数据
        prophet_data = prepare_for_prophet(df)
        
        if prophet_data is not None:
            # 保存处理后的数据
            csv_output = "/Users/xenodennis/Documents/Fun/isA_MCP/demo_data/processed_sales_data.csv"
            prophet_output = "/Users/xenodennis/Documents/Fun/isA_MCP/demo_data/prophet_sales_data.csv"
            
            df.to_csv(csv_output, index=False)
            prophet_data.to_csv(prophet_output, index=False)
            
            print(f"\n💾 数据已保存:")
            print(f"   完整数据: {csv_output}")
            print(f"   Prophet数据: {prophet_output}")
            
            return prophet_data
    
    return None

if __name__ == "__main__":
    main()