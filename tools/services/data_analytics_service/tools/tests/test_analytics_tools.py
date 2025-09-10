#!/usr/bin/env python3
"""
Comprehensive test script for data_analytics_tools.py
Tests all major functionality including statistical analysis, EDA, ML modeling, and A/B testing
"""

import asyncio
import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("🚀 Starting comprehensive data analytics tools test...")

def create_test_datasets():
    """Create various test datasets for comprehensive testing"""
    
    # 1. Sales dataset for EDA and time series analysis
    print("📊 Creating sales test dataset...")
    np.random.seed(42)
    dates = pd.date_range('2022-01-01', '2024-12-31', freq='D')
    n_records = len(dates)
    
    sales_data = {
        'date': dates,
        'sales': np.random.normal(1000, 200, n_records) + 
                50 * np.sin(2 * np.pi * np.arange(n_records) / 365) +  # Seasonal trend
                np.random.normal(0, 50, n_records),  # Noise
        'region': np.random.choice(['North', 'South', 'East', 'West'], n_records),
        'product_category': np.random.choice(['Electronics', 'Clothing', 'Food', 'Books'], n_records),
        'marketing_spend': np.random.normal(100, 30, n_records),
        'temperature': np.random.normal(20, 10, n_records),
        'promotion': np.random.choice([0, 1], n_records, p=[0.8, 0.2])
    }
    
    # Add correlation between marketing spend and sales
    sales_data['sales'] += 2 * sales_data['marketing_spend'] + np.random.normal(0, 20, n_records)
    
    sales_df = pd.DataFrame(sales_data)
    sales_df['sales'] = np.maximum(sales_df['sales'], 0)  # Ensure non-negative sales
    
    sales_path = project_root / "test_data_sales.csv"
    sales_df.to_csv(sales_path, index=False)
    print(f"✅ Sales dataset created: {sales_path} ({len(sales_df)} records)")
    
    # 2. A/B testing dataset
    print("🧪 Creating A/B testing dataset...")
    n_ab = 1000
    
    # Control group (baseline conversion rate ~5%)
    control_data = {
        'user_id': np.array(range(1, n_ab//2 + 1)),
        'control_group': np.ones(n_ab//2, dtype=int),
        'treatment_group': np.zeros(n_ab//2, dtype=int),
        'conversion_rate': np.random.binomial(1, 0.05, n_ab//2),
        'revenue': np.random.exponential(20, n_ab//2) * np.random.binomial(1, 0.05, n_ab//2),
        'age': np.random.normal(35, 10, n_ab//2),
        'session_duration': np.random.exponential(180, n_ab//2)
    }
    
    # Treatment group (improved conversion rate ~7%)
    treatment_data = {
        'user_id': np.array(range(n_ab//2 + 1, n_ab + 1)),
        'control_group': np.zeros(n_ab//2, dtype=int),
        'treatment_group': np.ones(n_ab//2, dtype=int),
        'conversion_rate': np.random.binomial(1, 0.07, n_ab//2),
        'revenue': np.random.exponential(25, n_ab//2) * np.random.binomial(1, 0.07, n_ab//2),
        'age': np.random.normal(33, 10, n_ab//2),
        'session_duration': np.random.exponential(200, n_ab//2)
    }
    
    # Combine datasets
    ab_data = {}
    for key in control_data.keys():
        ab_data[key] = np.concatenate([control_data[key], treatment_data[key]])
    
    ab_df = pd.DataFrame(ab_data)
    ab_path = project_root / "test_data_ab.csv"
    ab_df.to_csv(ab_path, index=False)
    print(f"✅ A/B testing dataset created: {ab_path} ({len(ab_df)} records)")
    
    # 3. Statistical analysis dataset with various distributions
    print("📈 Creating statistical analysis dataset...")
    n_stats = 500
    
    stats_data = {
        'normal_var': np.random.normal(0, 1, n_stats),
        'skewed_var': np.random.exponential(2, n_stats),
        'bimodal_var': np.concatenate([
            np.random.normal(-2, 0.5, n_stats//2),
            np.random.normal(2, 0.5, n_stats//2)
        ]),
        'categorical_a': np.random.choice(['A', 'B', 'C'], n_stats, p=[0.5, 0.3, 0.2]),
        'categorical_b': np.random.choice(['X', 'Y', 'Z'], n_stats),
        'correlated_var': None,  # Will be calculated
        'outlier_var': np.random.normal(10, 2, n_stats),
    }
    
    # Create correlation
    stats_data['correlated_var'] = 0.8 * stats_data['normal_var'] + 0.2 * np.random.normal(0, 1, n_stats)
    
    # Add some outliers
    outlier_indices = np.random.choice(n_stats, size=10, replace=False)
    stats_data['outlier_var'][outlier_indices] = np.random.uniform(50, 100, 10)
    
    stats_df = pd.DataFrame(stats_data)
    stats_path = project_root / "test_data_stats.csv"
    stats_df.to_csv(stats_path, index=False)
    print(f"✅ Statistical analysis dataset created: {stats_path} ({len(stats_df)} records)")
    
    return {
        'sales': sales_path,
        'ab_testing': ab_path,
        'statistics': stats_path
    }

async def test_eda_analysis(data_paths):
    """Test EDA analysis functionality"""
    print("\n🔍 Testing EDA Analysis...")
    
    try:
        from tools.services.data_analytics_service.tools.data_analytics_tools import DataAnalyticsTool
        
        tool = DataAnalyticsTool()
        
        # Test EDA on sales data
        print("  📊 Testing EDA on sales data...")
        result = await tool._get_service().perform_exploratory_data_analysis(
            data_path=str(data_paths['sales']),
            target_column='sales',
            include_ai_insights=True,
            request_id='test_eda_001'
        )
        
        print(f"  ✅ EDA Result: {result['success']}")
        if result['success']:
            eda_results = result['eda_results']
            print(f"    📈 Data shape: {eda_results.get('analysis_metadata', {}).get('data_shape', 'unknown')}")
            print(f"    🔍 Statistical analysis: {'✓' if 'statistical_analysis' in eda_results else '✗'}")
            print(f"    🧪 Data quality: {'✓' if 'data_quality_assessment' in eda_results else '✗'}")
            print(f"    🎯 Feature analysis: {'✓' if 'feature_analysis' in eda_results else '✗'}")
            print(f"    🤖 AI insights: {'✓' if 'insights_and_recommendations' in eda_results else '✗'}")
            
            # Print some key insights
            insights = result.get('business_insights', [])
            if insights:
                print(f"    💡 Business insights found: {len(insights)}")
                for i, insight in enumerate(insights[:3]):
                    print(f"      {i+1}. {insight}")
        else:
            print(f"    ❌ EDA failed: {result.get('error_message', 'Unknown error')}")
            
    except Exception as e:
        print(f"  ❌ EDA test failed: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_statistical_analysis(data_paths):
    """Test statistical analysis functionality"""
    print("\n📊 Testing Statistical Analysis...")
    
    try:
        from tools.services.data_analytics_service.tools.data_analytics_tools import DataAnalyticsTool
        
        tool = DataAnalyticsTool()
        
        # Test comprehensive statistical analysis
        print("  🔬 Testing comprehensive statistical analysis...")
        result = await tool._get_service().perform_statistical_analysis(
            data_path=str(data_paths['statistics']),
            analysis_type='comprehensive',
            target_columns=['normal_var', 'skewed_var'],
            request_id='test_stats_001'
        )
        
        print(f"  ✅ Statistical Analysis Result: {result['success']}")
        if result['success']:
            stats_results = result['statistical_results']
            print(f"    📊 Basic statistics: {'✓' if 'basic_statistics' in stats_results else '✗'}")
            print(f"    🔗 Correlation analysis: {'✓' if 'correlation_analysis' in stats_results else '✗'}")
            print(f"    📈 Distribution analysis: {'✓' if 'distribution_analysis' in stats_results else '✗'}")
            print(f"    🧪 Hypothesis tests: {'✓' if 'hypothesis_tests' in stats_results else '✗'}")
            print(f"    🎯 Outlier analysis: {'✓' if 'outlier_analysis' in stats_results else '✗'}")
            
            # Test hypothesis testing specifically
            print("  🧪 Testing hypothesis testing analysis...")
            hyp_result = await tool._get_service().perform_statistical_analysis(
                data_path=str(data_paths['statistics']),
                analysis_type='hypothesis_testing',
                request_id='test_stats_002'
            )
            
            if hyp_result['success']:
                print("    ✅ Hypothesis testing completed")
                hyp_tests = hyp_result['statistical_results'].get('hypothesis_tests', {})
                if 'two_sample_tests' in hyp_tests:
                    significant_tests = [
                        test for test in hyp_tests['two_sample_tests']
                        if test.get('t_test', {}).get('significant_difference', False)
                    ]
                    print(f"    📊 Significant differences found: {len(significant_tests)}")
        else:
            print(f"    ❌ Statistical analysis failed: {result.get('error_message', 'Unknown error')}")
            
    except Exception as e:
        print(f"  ❌ Statistical analysis test failed: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_ab_testing(data_paths):
    """Test A/B testing functionality"""
    print("\n🧪 Testing A/B Testing Analysis...")
    
    try:
        from tools.services.data_analytics_service.tools.data_analytics_tools import DataAnalyticsTool
        
        tool = DataAnalyticsTool()
        
        # Test A/B testing on conversion rate
        print("  📊 Testing A/B testing on conversion rate...")
        result = await tool._get_service().perform_ab_testing(
            data_path=str(data_paths['ab_testing']),
            control_group_column='control_group',
            treatment_group_column='treatment_group',
            metric_column='conversion_rate',
            confidence_level=0.95,
            request_id='test_ab_001'
        )
        
        print(f"  ✅ A/B Testing Result: {result['success']}")
        if result['success']:
            ab_results = result['ab_testing_results']
            interpretation = result['interpretation']
            
            # Sample sizes
            sample_sizes = ab_results.get('sample_sizes', {})
            print(f"    👥 Control group size: {sample_sizes.get('control', 0)}")
            print(f"    👥 Treatment group size: {sample_sizes.get('treatment', 0)}")
            
            # Effect analysis
            effect = ab_results.get('effect_analysis', {})
            rel_diff = effect.get('relative_difference', 0)
            print(f"    📈 Relative difference: {rel_diff:.2f}%")
            
            # Statistical significance
            if 'statistical_tests' in ab_results:
                t_test = ab_results['statistical_tests'].get('t_test', {})
                is_significant = t_test.get('significant', False)
                p_value = t_test.get('p_value', 1.0)
                print(f"    🎯 Statistically significant: {'Yes' if is_significant else 'No'}")
                print(f"    📊 P-value: {p_value:.4f}")
                
                # Effect size
                effect_size = ab_results['statistical_tests'].get('effect_size', {})
                cohens_d = effect_size.get('cohens_d', 0)
                interpretation_text = effect_size.get('interpretation', 'unknown')
                print(f"    💪 Effect size (Cohen's d): {cohens_d:.3f} ({interpretation_text})")
            
            # Business interpretation
            print(f"    💼 Conclusion: {interpretation.get('conclusion', 'No conclusion')}")
            print(f"    🚀 Recommendation: {interpretation.get('recommendation', 'No recommendation')}")
            
        else:
            print(f"    ❌ A/B testing failed: {result.get('error_message', 'Unknown error')}")
            
        # Test A/B testing on revenue
        print("  💰 Testing A/B testing on revenue...")
        revenue_result = await tool._get_service().perform_ab_testing(
            data_path=str(data_paths['ab_testing']),
            control_group_column='control_group',
            treatment_group_column='treatment_group',
            metric_column='revenue',
            confidence_level=0.95,
            request_id='test_ab_002'
        )
        
        if revenue_result['success']:
            effect = revenue_result['ab_testing_results'].get('effect_analysis', {})
            abs_diff = effect.get('absolute_difference', 0)
            print(f"    💰 Revenue difference: ${abs_diff:.2f}")
        
    except Exception as e:
        print(f"  ❌ A/B testing test failed: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_ml_modeling(data_paths):
    """Test ML modeling functionality"""
    print("\n🤖 Testing ML Model Development...")
    
    try:
        from tools.services.data_analytics_service.tools.data_analytics_tools import DataAnalyticsTool
        
        tool = DataAnalyticsTool()
        
        # Test ML modeling on sales data
        print("  📈 Testing ML modeling for sales prediction...")
        result = await tool._get_service().develop_machine_learning_model(
            data_path=str(data_paths['sales']),
            target_column='sales',
            problem_type='regression',
            include_feature_engineering=True,
            include_ai_guidance=True,
            request_id='test_ml_001'
        )
        
        print(f"  ✅ ML Modeling Result: {result['success']}")
        if result['success']:
            modeling_results = result['modeling_results']
            print(f"    🔧 Problem analysis: {'✓' if 'problem_analysis' in modeling_results else '✗'}")
            print(f"    🛠️ Data preparation: {'✓' if 'data_preparation' in modeling_results else '✗'}")
            print(f"    ⚙️ Feature engineering: {'✓' if 'feature_engineering' in modeling_results else '✗'}")
            print(f"    🎯 Model development: {'✓' if 'model_development' in modeling_results else '✗'}")
            print(f"    📊 Model evaluation: {'✓' if 'model_evaluation' in modeling_results else '✗'}")
            print(f"    🤖 AI guidance: {'✓' if 'ai_guidance' in modeling_results else '✗'}")
            
            # Model performance
            if 'model_evaluation' in modeling_results:
                evaluation = modeling_results['model_evaluation']
                if 'best_model' in evaluation:
                    best_model = evaluation['best_model']
                    algorithm = best_model.get('algorithm', 'unknown')
                    metrics = best_model.get('performance_metrics', {})
                    print(f"    🏆 Best algorithm: {algorithm}")
                    
                    if 'r2_score' in metrics:
                        print(f"    📊 R² Score: {metrics['r2_score']:.3f}")
                    if 'mean_squared_error' in metrics:
                        print(f"    📈 MSE: {metrics['mean_squared_error']:.3f}")
                        
        else:
            print(f"    ❌ ML modeling failed: {result.get('error_message', 'Unknown error')}")
            
    except Exception as e:
        print(f"  ❌ ML modeling test failed: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_service_status():
    """Test service status functionality"""
    print("\n⚙️ Testing Service Status...")
    
    try:
        from tools.services.data_analytics_service.tools.data_analytics_tools import DataAnalyticsTool
        
        tool = DataAnalyticsTool()
        
        # Test service status
        print("  📊 Getting service status...")
        result = await tool._get_service().get_service_status()
        
        print(f"  ✅ Service Status Result: {result is not None}")
        if result:
            print(f"    🏢 Service info: {'✓' if 'service_info' in result else '✗'}")
            print(f"    📈 Processing stats: {'✓' if 'processing_statistics' in result else '✗'}")
            print(f"    💾 Database info: {'✓' if 'database_summary' in result else '✗'}")
            
            # Service statistics
            if 'service_info' in result:
                service_info = result['service_info']
                print(f"    🔧 Service name: {service_info.get('service_name', 'unknown')}")
                print(f"    💾 Database: {service_info.get('database_name', 'unknown')}")
        
    except Exception as e:
        print(f"  ❌ Service status test failed: {str(e)}")
        import traceback
        traceback.print_exc()

async def run_comprehensive_tests():
    """Run all comprehensive tests"""
    print("=" * 60)
    print("🧪 COMPREHENSIVE DATA ANALYTICS TOOLS TEST")
    print("=" * 60)
    
    # Create test datasets
    data_paths = create_test_datasets()
    
    # Run all tests
    await test_eda_analysis(data_paths)
    await test_statistical_analysis(data_paths)
    await test_ab_testing(data_paths)
    await test_ml_modeling(data_paths)
    await test_service_status()
    
    print("\n" + "=" * 60)
    print("✅ COMPREHENSIVE TEST COMPLETED")
    print("=" * 60)
    
    # Cleanup test files
    print("\n🧹 Cleaning up test files...")
    for file_path in data_paths.values():
        try:
            Path(file_path).unlink()
            print(f"  🗑️ Deleted: {file_path}")
        except Exception as e:
            print(f"  ⚠️ Could not delete {file_path}: {e}")

if __name__ == "__main__":
    asyncio.run(run_comprehensive_tests())