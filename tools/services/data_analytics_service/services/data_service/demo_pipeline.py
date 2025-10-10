"""
End-to-End Data Pipeline Demo

Demonstrates the complete capabilities of the data_service module using
real-world scenarios.

Scenarios:
1. E-Commerce Customer Analytics Pipeline
2. Financial Transaction Processing Pipeline
3. Healthcare Patient Data Pipeline
"""

import pandas as pd
import numpy as np
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

from .pipeline_orchestrator import (
    DataPipelineOrchestrator,
    PipelineConfig,
    PipelineResult
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_ecommerce_data(num_records: int = 500) -> pd.DataFrame:
    """Generate synthetic e-commerce customer data"""
    np.random.seed(42)

    # Generate customer data
    customer_ids = [f"CUST{str(i).zfill(5)}" for i in range(num_records)]

    # Demographics
    ages = np.random.randint(18, 75, num_records)
    genders = np.random.choice(['M', 'F', 'Other'], num_records, p=[0.48, 0.48, 0.04])
    countries = np.random.choice(['US', 'UK', 'CA', 'AU', 'DE'], num_records, p=[0.4, 0.2, 0.15, 0.15, 0.1])

    # Purchase behavior
    total_purchases = np.random.randint(1, 50, num_records)
    total_revenue = np.random.uniform(50, 5000, num_records).round(2)
    avg_order_value = (total_revenue / total_purchases).round(2)

    # Engagement metrics
    days_since_last_purchase = np.random.randint(0, 365, num_records)
    email_open_rate = np.random.uniform(0, 1, num_records).round(2)
    product_views = np.random.randint(10, 500, num_records)

    # Customer segments (to be derived)
    lifetime_value = (total_revenue * (1 + email_open_rate * 0.3)).round(2)

    # Add some missing values (realistic data quality issues)
    email_open_rate[np.random.choice(num_records, 30, replace=False)] = np.nan
    countries[np.random.choice(num_records, 10, replace=False)] = None

    # Add some duplicates
    duplicate_indices = np.random.choice(num_records, 5, replace=False)

    df = pd.DataFrame({
        'customer_id': customer_ids,
        'age': ages,
        'gender': genders,
        'country': countries,
        'total_purchases': total_purchases,
        'total_revenue': total_revenue,
        'avg_order_value': avg_order_value,
        'days_since_last_purchase': days_since_last_purchase,
        'email_open_rate': email_open_rate,
        'product_views': product_views,
        'lifetime_value': lifetime_value,
        'registration_date': [
            (datetime.now() - timedelta(days=np.random.randint(30, 730))).strftime('%Y-%m-%d')
            for _ in range(num_records)
        ]
    })

    # Add duplicates
    duplicates = df.iloc[duplicate_indices].copy()
    df = pd.concat([df, duplicates], ignore_index=True)

    return df


def generate_financial_data(num_records: int = 300) -> pd.DataFrame:
    """Generate synthetic financial transaction data"""
    np.random.seed(123)

    transaction_ids = [f"TXN{str(i).zfill(6)}" for i in range(num_records)]
    account_ids = [f"ACC{str(i).zfill(4)}" for i in np.random.randint(1, 100, num_records)]

    # Transaction details
    amounts = np.random.uniform(10, 10000, num_records).round(2)
    transaction_types = np.random.choice(['debit', 'credit', 'transfer'], num_records, p=[0.5, 0.3, 0.2])

    # Add anomalies (potential fraud)
    fraud_indices = np.random.choice(num_records, 15, replace=False)
    amounts[fraud_indices] = np.random.uniform(50000, 100000, 15).round(2)

    # Merchant categories
    categories = np.random.choice(
        ['grocery', 'dining', 'shopping', 'travel', 'utilities', 'entertainment'],
        num_records,
        p=[0.25, 0.2, 0.2, 0.15, 0.1, 0.1]
    )

    # Locations
    locations = np.random.choice(['US', 'UK', 'CA', 'MX', 'EU'], num_records, p=[0.6, 0.15, 0.1, 0.1, 0.05])

    # Add data quality issues
    categories[np.random.choice(num_records, 20, replace=False)] = None
    amounts[np.random.choice(num_records, 10, replace=False)] = -999  # Invalid values

    df = pd.DataFrame({
        'transaction_id': transaction_ids,
        'account_id': account_ids,
        'amount': amounts,
        'transaction_type': transaction_types,
        'category': categories,
        'location': locations,
        'timestamp': [
            (datetime.now() - timedelta(hours=np.random.randint(1, 720))).strftime('%Y-%m-%d %H:%M:%S')
            for _ in range(num_records)
        ],
        'merchant_name': [f"Merchant_{i % 50}" for i in range(num_records)],
        'is_international': np.random.choice([True, False], num_records, p=[0.15, 0.85])
    })

    return df


def generate_healthcare_data(num_records: int = 200) -> pd.DataFrame:
    """Generate synthetic healthcare patient data"""
    np.random.seed(456)

    patient_ids = [f"PAT{str(i).zfill(5)}" for i in range(num_records)]

    # Demographics
    ages = np.random.randint(18, 90, num_records)
    genders = np.random.choice(['M', 'F'], num_records, p=[0.48, 0.52])

    # Clinical data
    diagnoses = np.random.choice(
        ['Diabetes', 'Hypertension', 'Asthma', 'Heart Disease', 'Arthritis'],
        num_records,
        p=[0.25, 0.25, 0.2, 0.15, 0.15]
    )

    # Risk factors
    bmi = np.random.uniform(18, 45, num_records).round(1)
    blood_pressure_systolic = np.random.randint(90, 180, num_records)
    cholesterol = np.random.randint(120, 300, num_records)

    # Treatment data
    num_visits = np.random.randint(1, 20, num_records)
    medications_count = np.random.randint(0, 10, num_records)

    # Outcomes
    readmission_30day = np.random.choice([True, False], num_records, p=[0.15, 0.85])
    treatment_adherence = np.random.uniform(0.3, 1.0, num_records).round(2)

    # Add data quality issues
    bmi[np.random.choice(num_records, 15, replace=False)] = np.nan
    blood_pressure_systolic[np.random.choice(num_records, 10, replace=False)] = 0  # Invalid
    diagnoses[np.random.choice(num_records, 5, replace=False)] = None

    df = pd.DataFrame({
        'patient_id': patient_ids,
        'age': ages,
        'gender': genders,
        'diagnosis': diagnoses,
        'bmi': bmi,
        'blood_pressure_systolic': blood_pressure_systolic,
        'cholesterol': cholesterol,
        'num_visits': num_visits,
        'medications_count': medications_count,
        'readmission_30day': readmission_30day,
        'treatment_adherence': treatment_adherence,
        'admission_date': [
            (datetime.now() - timedelta(days=np.random.randint(1, 365))).strftime('%Y-%m-%d')
            for _ in range(num_records)
        ]
    })

    return df


# Pipeline Configurations

ECOMMERCE_PIPELINE_CONFIG = PipelineConfig(
    enable_preprocessing=True,
    enable_augmentation=False,  # No external data for demo
    enable_transformation=True,
    enable_quality=True,
    enable_metadata=True,
    enable_analytics=True,
    enable_storage=False,  # Skip storage for demo

    preprocessing_config={
        'remove_nulls': True,
        'remove_duplicates': True,
        'remove_outliers': True,
        'outlier_method': 'iqr',
        'outlier_threshold': 3.0
    },

    transformation_spec={
        'filters': [
            {'column': 'total_purchases', 'operator': '>', 'value': 0},
            {'column': 'total_revenue', 'operator': '>', 'value': 0}
        ],
        'aggregations': [
            {
                'group_by': 'country',
                'metrics': {
                    'total_revenue': 'sum',
                    'total_purchases': 'sum',
                    'customer_id': 'count'
                }
            }
        ],
        'feature_engineering': [
            {
                'type': 'segmentation',
                'name': 'customer_segment',
                'rules': [
                    {'condition': 'lifetime_value > 2000', 'value': 'VIP'},
                    {'condition': 'lifetime_value > 1000', 'value': 'High Value'},
                    {'condition': 'lifetime_value > 500', 'value': 'Medium Value'},
                    {'default': True, 'value': 'Low Value'}
                ]
            },
            {
                'type': 'binning',
                'column': 'age',
                'bins': [18, 25, 35, 50, 75],
                'labels': ['18-24', '25-34', '35-49', '50+']
            }
        ]
    },

    quality_config={
        'checks': ['completeness', 'consistency', 'accuracy'],
        'thresholds': {
            'completeness': 0.9,
            'consistency': 0.85,
            'accuracy': 0.8
        }
    },

    analytics_config={
        'generate_summary': True,
        'detect_patterns': True,
        'create_visualizations': True
    },

    quality_threshold=0.7,
    stop_on_error=False
)


FINANCIAL_PIPELINE_CONFIG = PipelineConfig(
    enable_preprocessing=True,
    enable_augmentation=False,
    enable_transformation=True,
    enable_quality=True,
    enable_metadata=True,
    enable_analytics=True,
    enable_storage=False,

    preprocessing_config={
        'remove_nulls': True,
        'remove_duplicates': True,
        'remove_outliers': False,  # Keep outliers for fraud detection
        'validation_rules': [
            {'column': 'amount', 'rule': 'positive', 'action': 'remove'},
            {'column': 'transaction_type', 'rule': 'not_null', 'action': 'remove'}
        ]
    },

    transformation_spec={
        'filters': [
            {'column': 'amount', 'operator': '>', 'value': 0}
        ],
        'aggregations': [
            {
                'group_by': 'account_id',
                'metrics': {
                    'amount': ['sum', 'mean', 'count'],
                    'transaction_id': 'count'
                }
            },
            {
                'group_by': 'category',
                'metrics': {
                    'amount': 'sum'
                }
            }
        ],
        'feature_engineering': [
            {
                'type': 'anomaly_score',
                'column': 'amount',
                'method': 'zscore'
            },
            {
                'type': 'segmentation',
                'name': 'risk_level',
                'rules': [
                    {'condition': 'amount > 10000 and is_international == True', 'value': 'High Risk'},
                    {'condition': 'amount > 5000', 'value': 'Medium Risk'},
                    {'default': True, 'value': 'Low Risk'}
                ]
            }
        ]
    },

    quality_config={
        'checks': ['completeness', 'consistency', 'validity', 'accuracy'],
        'anomaly_detection': True,
        'thresholds': {
            'completeness': 0.95,
            'consistency': 0.9
        }
    },

    analytics_config={
        'generate_summary': True,
        'detect_anomalies': True,
        'time_series_analysis': True
    },

    quality_threshold=0.75,
    stop_on_error=False
)


HEALTHCARE_PIPELINE_CONFIG = PipelineConfig(
    enable_preprocessing=True,
    enable_augmentation=False,
    enable_transformation=True,
    enable_quality=True,
    enable_metadata=True,
    enable_analytics=True,
    enable_storage=False,

    preprocessing_config={
        'remove_nulls': True,
        'remove_duplicates': True,
        'impute_missing': True,
        'imputation_strategy': 'median',
        'validation_rules': [
            {'column': 'bmi', 'rule': 'range', 'min': 10, 'max': 60, 'action': 'flag'},
            {'column': 'blood_pressure_systolic', 'rule': 'range', 'min': 70, 'max': 200, 'action': 'flag'}
        ]
    },

    transformation_spec={
        'filters': [
            {'column': 'age', 'operator': '>=', 'value': 18}
        ],
        'aggregations': [
            {
                'group_by': 'diagnosis',
                'metrics': {
                    'patient_id': 'count',
                    'num_visits': 'mean',
                    'readmission_30day': 'sum'
                }
            },
            {
                'group_by': 'gender',
                'metrics': {
                    'bmi': 'mean',
                    'cholesterol': 'mean',
                    'blood_pressure_systolic': 'mean'
                }
            }
        ],
        'feature_engineering': [
            {
                'type': 'risk_score',
                'name': 'patient_risk_score',
                'factors': ['age', 'bmi', 'blood_pressure_systolic', 'cholesterol'],
                'weights': [0.2, 0.3, 0.3, 0.2]
            },
            {
                'type': 'segmentation',
                'name': 'risk_category',
                'rules': [
                    {'condition': 'patient_risk_score > 0.7', 'value': 'High Risk'},
                    {'condition': 'patient_risk_score > 0.4', 'value': 'Medium Risk'},
                    {'default': True, 'value': 'Low Risk'}
                ]
            }
        ]
    },

    quality_config={
        'checks': ['completeness', 'consistency', 'validity'],
        'phi_detection': True,  # Protected Health Information
        'thresholds': {
            'completeness': 0.9,
            'consistency': 0.95
        }
    },

    analytics_config={
        'generate_summary': True,
        'correlation_analysis': True,
        'predictive_insights': True
    },

    quality_threshold=0.8,
    stop_on_error=False
)


async def run_ecommerce_pipeline():
    """Run E-Commerce Customer Analytics Pipeline"""
    print("\n" + "="*80)
    print("E-COMMERCE CUSTOMER ANALYTICS PIPELINE")
    print("="*80)

    # Generate data
    print("\n[1/4] Generating e-commerce customer data...")
    data = generate_ecommerce_data(500)
    print(f"✓ Generated {len(data)} customer records")
    print(f"  Columns: {', '.join(data.columns.tolist())}")
    print(f"  Data shape: {data.shape}")

    # Initialize orchestrator
    print("\n[2/4] Initializing pipeline orchestrator...")
    orchestrator = DataPipelineOrchestrator()
    print("✓ Orchestrator initialized with all services")

    # Execute pipeline
    print("\n[3/4] Executing end-to-end pipeline...")
    print("  Stages: Preprocessing → Transformation → Quality → Metadata → Analytics")

    result = await orchestrator.execute_pipeline(data, ECOMMERCE_PIPELINE_CONFIG)

    # Display results
    print("\n[4/4] Pipeline Results:")
    print(f"  Status: {'✓ SUCCESS' if result.success else '✗ FAILED'}")
    print(f"  Total Duration: {result.total_duration_seconds:.2f}s")
    print(f"  Records Processed: {result.records_processed}")
    print(f"  Quality Score: {result.quality_score:.2%}")

    if result.final_data is not None:
        print(f"  Final Data Shape: {result.final_data.shape}")

    print(f"\n  Stage Breakdown:")
    for stage_result in result.stage_results:
        status = "✓" if stage_result.success else "✗"
        print(f"    {status} {stage_result.stage.value.title()}: {stage_result.duration_seconds:.2f}s")
        if stage_result.metrics:
            for key, value in list(stage_result.metrics.items())[:3]:  # Show top 3 metrics
                print(f"      - {key}: {value}")

    # Show sample output
    if result.final_data is not None and len(result.final_data) > 0:
        print(f"\n  Sample Output (first 3 rows):")
        print(result.final_data.head(3).to_string(index=False))

    return result


async def run_financial_pipeline():
    """Run Financial Transaction Processing Pipeline"""
    print("\n" + "="*80)
    print("FINANCIAL TRANSACTION PROCESSING PIPELINE")
    print("="*80)

    # Generate data
    print("\n[1/4] Generating financial transaction data...")
    data = generate_financial_data(300)
    print(f"✓ Generated {len(data)} transaction records")
    print(f"  Columns: {', '.join(data.columns.tolist())}")
    print(f"  Data shape: {data.shape}")

    # Initialize orchestrator
    print("\n[2/4] Initializing pipeline orchestrator...")
    orchestrator = DataPipelineOrchestrator()
    print("✓ Orchestrator initialized")

    # Execute pipeline
    print("\n[3/4] Executing end-to-end pipeline...")
    print("  Stages: Preprocessing → Transformation → Quality → Metadata → Analytics")

    result = await orchestrator.execute_pipeline(data, FINANCIAL_PIPELINE_CONFIG)

    # Display results
    print("\n[4/4] Pipeline Results:")
    print(f"  Status: {'✓ SUCCESS' if result.success else '✗ FAILED'}")
    print(f"  Total Duration: {result.total_duration_seconds:.2f}s")
    print(f"  Records Processed: {result.records_processed}")
    print(f"  Quality Score: {result.quality_score:.2%}")

    if result.final_data is not None:
        print(f"  Final Data Shape: {result.final_data.shape}")

    print(f"\n  Stage Breakdown:")
    for stage_result in result.stage_results:
        status = "✓" if stage_result.success else "✗"
        print(f"    {status} {stage_result.stage.value.title()}: {stage_result.duration_seconds:.2f}s")
        if stage_result.metrics:
            for key, value in list(stage_result.metrics.items())[:3]:
                print(f"      - {key}: {value}")

    # Show sample output
    if result.final_data is not None and len(result.final_data) > 0:
        print(f"\n  Sample Output (first 3 rows):")
        print(result.final_data.head(3).to_string(index=False))

    return result


async def run_healthcare_pipeline():
    """Run Healthcare Patient Data Pipeline"""
    print("\n" + "="*80)
    print("HEALTHCARE PATIENT DATA PIPELINE")
    print("="*80)

    # Generate data
    print("\n[1/4] Generating healthcare patient data...")
    data = generate_healthcare_data(200)
    print(f"✓ Generated {len(data)} patient records")
    print(f"  Columns: {', '.join(data.columns.tolist())}")
    print(f"  Data shape: {data.shape}")

    # Initialize orchestrator
    print("\n[2/4] Initializing pipeline orchestrator...")
    orchestrator = DataPipelineOrchestrator()
    print("✓ Orchestrator initialized")

    # Execute pipeline
    print("\n[3/4] Executing end-to-end pipeline...")
    print("  Stages: Preprocessing → Transformation → Quality → Metadata → Analytics")

    result = await orchestrator.execute_pipeline(data, HEALTHCARE_PIPELINE_CONFIG)

    # Display results
    print("\n[4/4] Pipeline Results:")
    print(f"  Status: {'✓ SUCCESS' if result.success else '✗ FAILED'}")
    print(f"  Total Duration: {result.total_duration_seconds:.2f}s")
    print(f"  Records Processed: {result.records_processed}")
    print(f"  Quality Score: {result.quality_score:.2%}")

    if result.final_data is not None:
        print(f"  Final Data Shape: {result.final_data.shape}")

    print(f"\n  Stage Breakdown:")
    for stage_result in result.stage_results:
        status = "✓" if stage_result.success else "✗"
        print(f"    {status} {stage_result.stage.value.title()}: {stage_result.duration_seconds:.2f}s")
        if stage_result.metrics:
            for key, value in list(stage_result.metrics.items())[:3]:
                print(f"      - {key}: {value}")

    # Show sample output
    if result.final_data is not None and len(result.final_data) > 0:
        print(f"\n  Sample Output (first 3 rows):")
        print(result.final_data.head(3).to_string(index=False))

    return result


async def run_all_demos():
    """Run all pipeline demonstrations"""
    print("\n" + "="*80)
    print("DATA SERVICE END-TO-END PIPELINE DEMONSTRATIONS")
    print("="*80)
    print("\nDemonstrating complete data_service capabilities across 3 scenarios:")
    print("1. E-Commerce Customer Analytics")
    print("2. Financial Transaction Processing")
    print("3. Healthcare Patient Data")

    # Run all pipelines
    ecommerce_result = await run_ecommerce_pipeline()
    financial_result = await run_financial_pipeline()
    healthcare_result = await run_healthcare_pipeline()

    # Summary
    print("\n" + "="*80)
    print("OVERALL SUMMARY")
    print("="*80)

    results = {
        'E-Commerce': ecommerce_result,
        'Financial': financial_result,
        'Healthcare': healthcare_result
    }

    for name, result in results.items():
        print(f"\n{name} Pipeline:")
        print(f"  Status: {'✓ SUCCESS' if result.success else '✗ FAILED'}")
        print(f"  Duration: {result.total_duration_seconds:.2f}s")
        print(f"  Records: {result.records_processed}")
        print(f"  Quality: {result.quality_score:.2%}")
        print(f"  Stages: {len(result.stage_results)}")

    total_duration = sum(r.total_duration_seconds for r in results.values())
    total_records = sum(r.records_processed for r in results.values())
    avg_quality = sum(r.quality_score for r in results.values()) / len(results)

    print(f"\nAggregate Metrics:")
    print(f"  Total Duration: {total_duration:.2f}s")
    print(f"  Total Records Processed: {total_records:,}")
    print(f"  Average Quality Score: {avg_quality:.2%}")
    print(f"  Pipelines Executed: {len(results)}")
    print(f"  Success Rate: {sum(1 for r in results.values() if r.success) / len(results):.0%}")

    print("\n" + "="*80)
    print("All demonstrations completed successfully!")
    print("="*80 + "\n")


if __name__ == "__main__":
    # Run all demos
    asyncio.run(run_all_demos())
