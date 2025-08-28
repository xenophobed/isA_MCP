#!/usr/bin/env python3
"""
Wireless Router Certification Business Rules Configuration
Configures existing BusinessRulesService for certification domain
"""

import pandas as pd
from typing import Dict, List, Any

def get_certification_business_rules() -> Dict[str, Any]:
    """
    Get business rules configuration for wireless router certification
    Uses existing BusinessRulesService with domain-specific rules
    """
    
    return {
        "domain": "wireless_certification",
        "description": "Business rules for wireless router certification testing",
        "rules": [
            # Power Compliance Validation Rules
            {
                "name": "fcc_power_compliance",
                "type": "validation",
                "description": "Check FCC power limits compliance",
                "columns": ["eirp_dbm", "certification_standard"],
                "validation_type": "custom_function",
                "function": "validate_fcc_power_limits",
                "action": "flag",
                "severity": "critical"
            },
            
            # SAR Compliance Validation Rules
            {
                "name": "sar_limit_compliance", 
                "type": "validation",
                "description": "Check SAR exposure limits",
                "columns": ["sar_1g_w_kg", "sar_10g_w_kg", "certification_standard"],
                "validation_type": "custom_function", 
                "function": "validate_sar_limits",
                "action": "flag",
                "severity": "critical"
            },
            
            # Frequency Band Validation
            {
                "name": "frequency_band_validation",
                "type": "validation", 
                "description": "Validate frequency bands against standards",
                "columns": ["center_frequency_mhz", "certification_standard"],
                "validation_type": "custom_function",
                "function": "validate_frequency_bands",
                "action": "flag",
                "severity": "high"
            },
            
            # Test Result Status Calculation
            {
                "name": "compliance_status_calculation",
                "type": "calculation",
                "description": "Calculate compliance status based on measurements vs limits",
                "output_column": "compliance_status",
                "calculation_type": "custom_function",
                "function": "calculate_compliance_status",
                "input_columns": ["eirp_dbm", "limit_value", "test_result"]
            },
            
            # Margin Calculation
            {
                "name": "safety_margin_calculation", 
                "type": "calculation",
                "description": "Calculate safety margin from regulatory limits",
                "output_column": "margin_db",
                "calculation_type": "subtraction",
                "operand1": "limit_value",
                "operand2": "eirp_dbm"
            },
            
            # Project Status Business Rules
            {
                "name": "project_status_update",
                "type": "conditional",
                "description": "Update project status based on test completion",
                "condition": "test_completion_rate >= 0.9",
                "true_action": {
                    "type": "set_value",
                    "column": "project_status", 
                    "value": "testing_complete"
                },
                "false_action": {
                    "type": "set_value",
                    "column": "project_status",
                    "value": "testing_in_progress"
                }
            },
            
            # Cost Calculation Rules
            {
                "name": "per_test_cost_calculation",
                "type": "calculation",
                "description": "Calculate cost per test",
                "output_column": "cost_per_test",
                "calculation_type": "division",
                "operand1": "total_cost",
                "operand2": "total_tests"
            },
            
            # Data Quality Rules
            {
                "name": "test_data_completeness",
                "type": "validation",
                "description": "Ensure critical test parameters are not null",
                "columns": ["eirp_dbm", "center_frequency_mhz", "test_result"],
                "validation_type": "not_null",
                "action": "flag",
                "severity": "medium"
            }
        ],
        
        # Custom validation functions for certification domain
        "custom_functions": {
            "validate_fcc_power_limits": {
                "description": "Validate FCC power limits by frequency band",
                "code": """
def validate_fcc_power_limits(df):
    violations = []
    for idx, row in df.iterrows():
        if row['certification_standard'] == 'FCC':
            freq = row.get('center_frequency_mhz', 0)
            power = row.get('eirp_dbm', 0)
            
            # FCC Part 15.247 limits
            if 2400 <= freq <= 2483.5 and power > 20:  # 2.4GHz ISM band
                violations.append(idx)
            elif 5150 <= freq <= 5350 and power > 23:  # 5GHz U-NII-1
                violations.append(idx)
            elif 5470 <= freq <= 5725 and power > 30:  # 5GHz U-NII-2
                violations.append(idx)
    
    return {'violations': violations, 'total_checked': len(df)}
"""
            },
            
            "validate_sar_limits": {
                "description": "Validate SAR exposure limits",
                "code": """
def validate_sar_limits(df):
    violations = []
    for idx, row in df.iterrows():
        standard = row.get('certification_standard', '')
        sar_1g = row.get('sar_1g_w_kg', 0)
        sar_10g = row.get('sar_10g_w_kg', 0)
        
        if standard == 'FCC' and sar_1g > 1.6:  # FCC limit 1.6 W/kg
            violations.append(idx)
        elif standard == 'CE' and sar_10g > 2.0:  # CE limit 2.0 W/kg
            violations.append(idx)
        elif standard == 'IC' and sar_1g > 1.6:  # IC limit 1.6 W/kg
            violations.append(idx)
    
    return {'violations': violations, 'total_checked': len(df)}
"""
            },
            
            "validate_frequency_bands": {
                "description": "Validate frequency bands against certification standards",
                "code": """
def validate_frequency_bands(df):
    violations = []
    for idx, row in df.iterrows():
        freq = row.get('center_frequency_mhz', 0)
        standard = row.get('certification_standard', '')
        
        valid_bands = {
            'FCC': [(2400, 2483.5), (5150, 5250), (5250, 5350), (5470, 5725), (5725, 5850)],
            'CE': [(2400, 2483.5), (5150, 5350), (5470, 5725)], 
            'IC': [(2400, 2483.5), (5150, 5250), (5250, 5350), (5470, 5725)]
        }
        
        if standard in valid_bands:
            is_valid = any(start <= freq <= end for start, end in valid_bands[standard])
            if not is_valid:
                violations.append(idx)
    
    return {'violations': violations, 'total_checked': len(df)}
"""
            },
            
            "calculate_compliance_status": {
                "description": "Calculate overall compliance status",
                "code": """
def calculate_compliance_status(df):
    status_list = []
    for idx, row in df.iterrows():
        power = row.get('eirp_dbm', 0)
        limit = row.get('limit_value', float('inf'))
        test_result = row.get('test_result', 'pending')
        
        if test_result == 'pass' and power <= limit:
            status_list.append('compliant')
        elif test_result == 'fail' or power > limit:
            status_list.append('non_compliant')  
        else:
            status_list.append('pending_review')
    
    return pd.Series(status_list, index=df.index)
"""
            }
        },
        
        # Configuration metadata
        "metadata": {
            "version": "1.0.0",
            "created_for": "wireless_router_certification",
            "compatible_standards": ["FCC", "IC", "CE"],
            "frequency_bands": ["2.4GHz", "5GHz", "6GHz"],
            "last_updated": "2024-01-01"
        }
    }

def get_certification_transformation_config() -> Dict[str, Any]:
    """
    Get transformation service configuration for certification data
    Uses existing TransformationService with certification-specific settings
    """
    
    return {
        "transformation_config": {
            "aggregation_enabled": True,
            "feature_engineering_enabled": True, 
            "business_rules_enabled": True,
            "validation_level": "strict",
            "preserve_original": True,
            "batch_size": 1000
        },
        
        "aggregation_rules": [
            {
                "name": "project_test_summary",
                "group_by": ["project_id"],
                "aggregations": {
                    "total_tests": {"column": "id", "function": "count"},
                    "passed_tests": {"column": "test_result", "function": "count", "filter": "pass"},
                    "failed_tests": {"column": "test_result", "function": "count", "filter": "fail"},
                    "avg_power": {"column": "eirp_dbm", "function": "mean"},
                    "max_sar": {"column": "sar_1g_w_kg", "function": "max"}
                }
            },
            
            {
                "name": "standard_compliance_rates",
                "group_by": ["certification_standard"],
                "aggregations": {
                    "total_tests": {"column": "id", "function": "count"},
                    "compliance_rate": {"column": "compliance_status", "function": "pass_rate"}
                }
            }
        ],
        
        "feature_engineering": [
            {
                "name": "test_efficiency_metrics",
                "features": [
                    {
                        "name": "tests_per_day",
                        "calculation": "total_tests / project_duration_days"
                    },
                    {
                        "name": "cost_effectiveness", 
                        "calculation": "passed_tests / total_cost"
                    }
                ]
            }
        ]
    }

# Convenience function for easy access
def configure_analytics_service_for_certification():
    """
    Configure DataAnalyticsService for wireless certification business domain
    Returns configuration that can be passed to existing services
    """
    
    return {
        "domain": "wireless_certification",
        "business_rules": get_certification_business_rules(),
        "transformation_config": get_certification_transformation_config(),
        "database_config": {
            "type": "duckdb",
            "database": "./resources/dbs/duckdb/wireless_certification.duckdb",
            "schema_tables": [
                "certification_products",
                "certification_projects", 
                "certification_test_records",
                "certification_regulatory_limits",
                "certification_certificates"
            ]
        }
    }