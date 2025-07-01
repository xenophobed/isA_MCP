#!/usr/bin/env python3
"""
Real data visualization tests - no mocks, actual service testing
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from tools.services.data_analytics_service.services.data_visualization import (
    DataVisualizationService,
    ChartType
)
from tools.services.data_analytics_service.services.sql_executor import ExecutionResult
from tools.services.data_analytics_service.services.query_matcher import QueryContext
from tools.services.data_analytics_service.services.semantic_enricher import SemanticMetadata


def create_real_sales_data():
    """Create realistic sales data for testing"""
    return [
        {"product": "iPhone 15", "sales": 25000, "quarter": "Q1", "region": "North America"},
        {"product": "iPhone 15", "sales": 28000, "quarter": "Q2", "region": "North America"},
        {"product": "iPhone 15", "sales": 32000, "quarter": "Q3", "region": "North America"},
        {"product": "iPhone 15", "sales": 35000, "quarter": "Q4", "region": "North America"},
        {"product": "Samsung Galaxy", "sales": 18000, "quarter": "Q1", "region": "North America"},
        {"product": "Samsung Galaxy", "sales": 20000, "quarter": "Q2", "region": "North America"},
        {"product": "Samsung Galaxy", "sales": 22000, "quarter": "Q3", "region": "North America"},
        {"product": "Samsung Galaxy", "sales": 24000, "quarter": "Q4", "region": "North America"},
        {"product": "Google Pixel", "sales": 8000, "quarter": "Q1", "region": "North America"},
        {"product": "Google Pixel", "sales": 9500, "quarter": "Q2", "region": "North America"},
        {"product": "Google Pixel", "sales": 11000, "quarter": "Q3", "region": "North America"},
        {"product": "Google Pixel", "sales": 12500, "quarter": "Q4", "region": "North America"}
    ]


def create_real_financial_data():
    """Create realistic financial time series data"""
    return [
        {"date": "2024-01-01", "revenue": 150000, "expenses": 120000, "profit": 30000},
        {"date": "2024-02-01", "revenue": 165000, "expenses": 125000, "profit": 40000},
        {"date": "2024-03-01", "revenue": 180000, "expenses": 130000, "profit": 50000},
        {"date": "2024-04-01", "revenue": 195000, "expenses": 135000, "profit": 60000},
        {"date": "2024-05-01", "revenue": 210000, "expenses": 140000, "profit": 70000},
        {"date": "2024-06-01", "revenue": 225000, "expenses": 145000, "profit": 80000},
        {"date": "2024-07-01", "revenue": 240000, "expenses": 150000, "profit": 90000},
        {"date": "2024-08-01", "revenue": 255000, "expenses": 155000, "profit": 100000},
        {"date": "2024-09-01", "revenue": 270000, "expenses": 160000, "profit": 110000},
        {"date": "2024-10-01", "revenue": 285000, "expenses": 165000, "profit": 120000},
        {"date": "2024-11-01", "revenue": 300000, "expenses": 170000, "profit": 130000},
        {"date": "2024-12-01", "revenue": 315000, "expenses": 175000, "profit": 140000}
    ]


def create_real_price_quantity_data():
    """Create realistic price vs quantity data for scatter plot"""
    return [
        {"price": 10.00, "quantity_sold": 1500},
        {"price": 12.50, "quantity_sold": 1200},
        {"price": 15.00, "quantity_sold": 980},
        {"price": 17.50, "quantity_sold": 800},
        {"price": 20.00, "quantity_sold": 650},
        {"price": 22.50, "quantity_sold": 520},
        {"price": 25.00, "quantity_sold": 400},
        {"price": 27.50, "quantity_sold": 300},
        {"price": 30.00, "quantity_sold": 200},
        {"price": 32.50, "quantity_sold": 150},
        {"price": 35.00, "quantity_sold": 100},
        {"price": 37.50, "quantity_sold": 75},
        {"price": 40.00, "quantity_sold": 50}
    ]


def create_real_market_share_data():
    """Create realistic market share data for pie chart"""
    return [
        {"company": "Apple", "market_share": 45.2},
        {"company": "Samsung", "market_share": 28.7},
        {"company": "Google", "market_share": 12.1},
        {"company": "OnePlus", "market_share": 6.8},
        {"company": "Others", "market_share": 7.2}
    ]


def create_real_kpi_data():
    """Create realistic KPI data for metric visualization"""
    return [
        {"total_revenue": 2750000.50}
    ]


def create_real_query_context(intent, entities, attributes):
    """Create realistic query context"""
    return QueryContext(
        business_intent=intent,
        entities_mentioned=entities,
        attributes_mentioned=attributes,
        operations=["analyze", "compare"],
        confidence_score=0.85
    )


def create_real_semantic_metadata(tables, columns):
    """Create realistic semantic metadata"""
    return SemanticMetadata(
        original_metadata={
            "tables": tables,
            "columns": columns
        },
        business_entities=["Product", "Sales", "Revenue", "Customer"],
        semantic_tags={"sales": "metric", "revenue": "financial"},
        data_patterns=["time_series", "categorical"],
        business_rules=["sales_must_be_positive"],
        domain_classification={"primary_domain": "business_analytics"},
        confidence_scores={"entity_detection": 0.9, "pattern_recognition": 0.8}
    )


async def test_bar_chart_real_data():
    """Test bar chart with real sales data"""
    print("\n=== Testing Bar Chart with Real Sales Data ===")
    
    viz_service = DataVisualizationService()
    sales_data = create_real_sales_data()
    
    # Aggregate data for bar chart (total sales by product)
    aggregated_data = {}
    for record in sales_data:
        product = record["product"]
        if product not in aggregated_data:
            aggregated_data[product] = 0
        aggregated_data[product] += record["sales"]
    
    chart_data = [{"product": k, "total_sales": v} for k, v in aggregated_data.items()]
    
    execution_result = ExecutionResult(
        success=True,
        data=chart_data,
        column_names=["product", "total_sales"],
        row_count=len(chart_data),
        execution_time_ms=120.5,
        sql_executed="SELECT product, SUM(sales) as total_sales FROM sales GROUP BY product"
    )
    
    query_context = create_real_query_context(
        "analyze total sales by product",
        ["sales", "product"],
        ["product", "total_sales"]
    )
    
    semantic_metadata = create_real_semantic_metadata(
        [{"table_name": "sales"}],
        [
            {"table_name": "sales", "column_name": "product"},
            {"table_name": "sales", "column_name": "total_sales"}
        ]
    )
    
    result = await viz_service.generate_visualization_spec(
        execution_result=execution_result,
        query_context=query_context,
        semantic_metadata=semantic_metadata,
        preferred_library="chartjs"
    )
    
    print(f"Status: {result['status']}")
    print(f"Chart Type: {result['visualization']['type']}")
    print(f"Title: {result['visualization']['title']}")
    print(f"Confidence: {result['visualization']['confidence_score']}")
    print(f"Data Points: {len(result['visualization']['data']['datasets'][0]['data'])}")
    print(f"Insights: {len(result['visualization']['insights'])}")
    
    # Verify the JSON structure
    assert result["status"] == "success"
    assert result["visualization"]["type"] == "bar"
    assert "chartjs" in result["visualization"]["library"]
    assert len(result["visualization"]["data"]["labels"]) == 3
    
    print("✅ Bar Chart Test Passed")
    return result


async def test_line_chart_real_data():
    """Test line chart with real time series data"""
    print("\n=== Testing Line Chart with Real Financial Data ===")
    
    viz_service = DataVisualizationService()
    financial_data = create_real_financial_data()
    
    execution_result = ExecutionResult(
        success=True,
        data=financial_data,
        column_names=["date", "revenue", "expenses", "profit"],
        row_count=len(financial_data),
        execution_time_ms=85.3,
        sql_executed="SELECT date, revenue, expenses, profit FROM financials ORDER BY date"
    )
    
    query_context = create_real_query_context(
        "analyze financial trends over time",
        ["revenue", "expenses", "profit"],
        ["date", "revenue", "expenses", "profit"]
    )
    
    semantic_metadata = create_real_semantic_metadata(
        [{"table_name": "financials"}],
        [
            {"table_name": "financials", "column_name": "date"},
            {"table_name": "financials", "column_name": "revenue"},
            {"table_name": "financials", "column_name": "expenses"},
            {"table_name": "financials", "column_name": "profit"}
        ]
    )
    
    result = await viz_service.generate_visualization_spec(
        execution_result=execution_result,
        query_context=query_context,
        semantic_metadata=semantic_metadata,
        preferred_library="recharts"
    )
    
    print(f"Status: {result['status']}")
    print(f"Chart Type: {result['visualization']['type']}")
    print(f"Library: {result['visualization']['library']}")
    print(f"Number of Lines: {len(result['visualization']['data']['datasets'])}")
    print(f"Time Points: {len(result['visualization']['data']['labels'])}")
    
    # Verify multiple datasets for multiple metrics
    assert result["status"] == "success"
    assert result["visualization"]["type"] == "line"
    assert len(result["visualization"]["data"]["datasets"]) >= 2  # Multiple lines
    assert len(result["visualization"]["data"]["labels"]) == 12  # 12 months
    
    print("✅ Line Chart Test Passed")
    return result


async def test_scatter_plot_real_data():
    """Test scatter plot with real price/quantity data"""
    print("\n=== Testing Scatter Plot with Real Price/Quantity Data ===")
    
    viz_service = DataVisualizationService()
    price_data = create_real_price_quantity_data()
    
    execution_result = ExecutionResult(
        success=True,
        data=price_data,
        column_names=["price", "quantity_sold"],
        row_count=len(price_data),
        execution_time_ms=95.7,
        sql_executed="SELECT price, quantity_sold FROM products"
    )
    
    query_context = create_real_query_context(
        "analyze price vs quantity relationship",
        ["price", "quantity"],
        ["price", "quantity_sold"]
    )
    
    semantic_metadata = create_real_semantic_metadata(
        [{"table_name": "products"}],
        [
            {"table_name": "products", "column_name": "price"},
            {"table_name": "products", "column_name": "quantity_sold"}
        ]
    )
    
    result = await viz_service.generate_visualization_spec(
        execution_result=execution_result,
        query_context=query_context,
        semantic_metadata=semantic_metadata,
        preferred_library="chartjs"
    )
    
    print(f"Status: {result['status']}")
    print(f"Chart Type: {result['visualization']['type']}")
    print(f"Correlation: {result['visualization']['data']['metadata'].get('correlation', 'N/A')}")
    print(f"Data Points: {len(result['visualization']['data']['datasets'][0]['data'])}")
    
    # Verify scatter plot structure
    assert result["status"] == "success"
    assert result["visualization"]["type"] == "scatter"
    
    # Check that data points have x,y structure
    scatter_data = result["visualization"]["data"]["datasets"][0]["data"]
    assert all("x" in point and "y" in point for point in scatter_data)
    
    print("✅ Scatter Plot Test Passed")
    return result


async def test_pie_chart_real_data():
    """Test pie chart with real market share data"""
    print("\n=== Testing Pie Chart with Real Market Share Data ===")
    
    viz_service = DataVisualizationService()
    market_data = create_real_market_share_data()
    
    execution_result = ExecutionResult(
        success=True,
        data=market_data,
        column_names=["company", "market_share"],
        row_count=len(market_data),
        execution_time_ms=75.2,
        sql_executed="SELECT company, market_share FROM market_analysis"
    )
    
    query_context = create_real_query_context(
        "analyze market share distribution",
        ["company", "market_share"],
        ["company", "market_share"]
    )
    
    semantic_metadata = create_real_semantic_metadata(
        [{"table_name": "market_analysis"}],
        [
            {"table_name": "market_analysis", "column_name": "company"},
            {"table_name": "market_analysis", "column_name": "market_share"}
        ]
    )
    
    result = await viz_service.generate_visualization_spec(
        execution_result=execution_result,
        query_context=query_context,
        semantic_metadata=semantic_metadata,
        preferred_library="chartjs",
        chart_type_hint=ChartType.PIE
    )
    
    print(f"Status: {result['status']}")
    print(f"Chart Type: {result['visualization']['type']}")
    print(f"Segments: {len(result['visualization']['data']['labels'])}")
    print(f"Total Share: {sum(result['visualization']['data']['datasets'][0]['data']):.1f}%")
    
    # Verify pie chart structure
    assert result["status"] == "success"
    assert result["visualization"]["type"] == "pie"
    assert len(result["visualization"]["data"]["labels"]) == 5
    
    # Check colors are assigned
    dataset = result["visualization"]["data"]["datasets"][0]
    assert "backgroundColor" in dataset
    assert len(dataset["backgroundColor"]) == len(market_data)
    
    print("✅ Pie Chart Test Passed")
    return result


async def test_metric_visualization_real_data():
    """Test metric visualization with real KPI data"""
    print("\n=== Testing Metric Visualization with Real KPI Data ===")
    
    viz_service = DataVisualizationService()
    kpi_data = create_real_kpi_data()
    
    execution_result = ExecutionResult(
        success=True,
        data=kpi_data,
        column_names=["total_revenue"],
        row_count=1,
        execution_time_ms=45.8,
        sql_executed="SELECT SUM(revenue) as total_revenue FROM sales"
    )
    
    query_context = create_real_query_context(
        "show total revenue KPI",
        ["revenue"],
        ["total_revenue"]
    )
    
    semantic_metadata = create_real_semantic_metadata(
        [{"table_name": "sales"}],
        [{"table_name": "sales", "column_name": "total_revenue"}]
    )
    
    result = await viz_service.generate_visualization_spec(
        execution_result=execution_result,
        query_context=query_context,
        semantic_metadata=semantic_metadata,
        preferred_library="chartjs"
    )
    
    print(f"Status: {result['status']}")
    print(f"Chart Type: {result['visualization']['type']}")
    print(f"KPI Value: ${result['visualization']['data']['datasets'][0]['value']:,.2f}")
    print(f"Format: {result['visualization']['data']['metadata']['format']}")
    
    # Verify metric structure
    assert result["status"] == "success"
    assert result["visualization"]["type"] == "metric"
    assert result["visualization"]["data"]["datasets"][0]["value"] == 2750000.50
    
    print("✅ Metric Visualization Test Passed")
    return result


async def test_large_dataset_table():
    """Test table visualization with large dataset"""
    print("\n=== Testing Table Visualization with Large Dataset ===")
    
    viz_service = DataVisualizationService()
    
    # Create large dataset (1500 records)
    large_data = []
    for i in range(1500):
        large_data.append({
            "transaction_id": f"TXN_{i:06d}",
            "customer_id": f"CUST_{i % 100:03d}",
            "amount": round(50 + (i * 0.5) % 1000, 2),
            "product": f"Product_{i % 20}",
            "date": f"2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}"
        })
    
    execution_result = ExecutionResult(
        success=True,
        data=large_data,
        column_names=["transaction_id", "customer_id", "amount", "product", "date"],
        row_count=len(large_data),
        execution_time_ms=250.3,
        sql_executed="SELECT * FROM transactions"
    )
    
    query_context = create_real_query_context(
        "view all transaction data",
        ["transactions"],
        ["transaction_id", "customer_id", "amount", "product", "date"]
    )
    
    semantic_metadata = create_real_semantic_metadata(
        [{"table_name": "transactions"}],
        [
            {"table_name": "transactions", "column_name": "transaction_id"},
            {"table_name": "transactions", "column_name": "customer_id"},
            {"table_name": "transactions", "column_name": "amount"},
            {"table_name": "transactions", "column_name": "product"},
            {"table_name": "transactions", "column_name": "date"}
        ]
    )
    
    result = await viz_service.generate_visualization_spec(
        execution_result=execution_result,
        query_context=query_context,
        semantic_metadata=semantic_metadata,
        preferred_library="chartjs"
    )
    
    print(f"Status: {result['status']}")
    print(f"Chart Type: {result['visualization']['type']}")
    print(f"Total Records: {len(result['visualization']['data']['datasets'][0]['data'])}")
    print(f"Columns: {len(result['visualization']['data']['datasets'][0]['columns'])}")
    print(f"Paginated: {result['visualization']['data']['metadata']['paginated']}")
    
    # Large datasets should default to table
    assert result["status"] == "success"
    assert result["visualization"]["type"] == "table"
    assert result["visualization"]["data"]["metadata"]["paginated"] is True
    
    print("✅ Large Dataset Table Test Passed")
    return result


def print_sample_json_output(result):
    """Print sample JSON output for React integration"""
    print("\n=== SAMPLE JSON OUTPUT FOR REACT ===")
    print(json.dumps({
        "type": result["visualization"]["type"],
        "data": result["visualization"]["data"],
        "config": result["visualization"]["config"],
        "library": result["visualization"]["library"],
        "title": result["visualization"]["title"],
        "insights": result["visualization"]["insights"][:2]  # First 2 insights
    }, indent=2))


async def main():
    """Run all visualization tests with real data"""
    print("🧪 Starting Real Data Visualization Tests")
    print("=" * 50)
    
    try:
        # Run all tests
        bar_result = await test_bar_chart_real_data()
        line_result = await test_line_chart_real_data()
        scatter_result = await test_scatter_plot_real_data()
        pie_result = await test_pie_chart_real_data()
        metric_result = await test_metric_visualization_real_data()
        table_result = await test_large_dataset_table()
        
        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 50)
        
        # Show sample JSON output
        print_sample_json_output(bar_result)
        
        print("\n📊 Summary:")
        print(f"✅ Bar Chart: {bar_result['visualization']['type']}")
        print(f"✅ Line Chart: {line_result['visualization']['type']}")
        print(f"✅ Scatter Plot: {scatter_result['visualization']['type']}")
        print(f"✅ Pie Chart: {pie_result['visualization']['type']}")
        print(f"✅ Metric: {metric_result['visualization']['type']}")
        print(f"✅ Table: {table_result['visualization']['type']}")
        
        print("\n🚀 React Integration Ready!")
        print("The JSON specifications can be consumed directly by:")
        print("- Chart.js components")
        print("- Recharts components")
        print("- Custom React visualization components")
        
    except Exception as e:
        print(f"\n❌ Test Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)