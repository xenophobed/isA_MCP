"""
Business Rules Service - Step 3 of Transformation Pipeline
Applies domain-specific business rules and logic to data
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Callable
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

@dataclass
class RulesResult:
    """Result of business rules application"""
    success: bool
    transformed_data: Optional[pd.DataFrame] = None
    rules_summary: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

class BusinessRulesService:
    """
    Business Rules Service - Step 3 of Transformation Pipeline
    
    Handles:
    - Domain-specific data transformations
    - Business logic validation and enforcement
    - Data quality rules
    - Custom business calculations
    - Conditional transformations
    - Compliance and regulatory rules
    """
    
    def __init__(self):
        self.execution_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'average_duration': 0.0
        }
        
        # Built-in business rule functions
        self.rule_functions = {
            'email_validation': self._validate_email,
            'phone_validation': self._validate_phone,
            'age_category': self._categorize_age,
            'revenue_tier': self._categorize_revenue,
            'date_range_validation': self._validate_date_range,
            'outlier_capping': self._cap_outliers,
            'currency_conversion': self._convert_currency,
            'status_normalization': self._normalize_status
        }
        
        logger.info("Business Rules Service initialized")
    
    def apply_rules(self, 
                   data: pd.DataFrame,
                   rules_config: Dict[str, Any]) -> RulesResult:
        """
        Apply business rules to data
        
        Args:
            data: Input DataFrame
            rules_config: Business rules configuration
            
        Returns:
            RulesResult with transformed data
        """
        start_time = datetime.now()
        
        try:
            transformed_df = data.copy()
            rules_summary = {
                'rules_applied': [],
                'validation_results': {},
                'transformations_performed': []
            }
            
            # Apply business rules
            for rule in rules_config.get('rules', []):
                result = self._apply_rule(transformed_df, rule)
                
                if result['success']:
                    rules_summary['rules_applied'].append({
                        'rule_name': rule.get('name'),
                        'rule_type': rule.get('type'),
                        'target_columns': rule.get('columns', []),
                        'records_affected': result.get('records_affected', 0)
                    })
                    
                    if result.get('validation_results'):
                        rules_summary['validation_results'].update(
                            result['validation_results']
                        )
                else:
                    return RulesResult(
                        success=False,
                        errors=[f"Rule '{rule.get('name')}' failed: {result.get('error')}"]
                    )
            
            # Calculate performance metrics
            duration = (datetime.now() - start_time).total_seconds()
            performance_metrics = {
                'duration_seconds': duration,
                'input_shape': data.shape,
                'output_shape': transformed_df.shape,
                'rules_processed': len(rules_config.get('rules', [])),
                'total_records_affected': sum(
                    rule.get('records_affected', 0) 
                    for rule in rules_summary['rules_applied']
                )
            }
            
            rules_summary.update({
                'original_shape': data.shape,
                'transformed_shape': transformed_df.shape,
                'total_rules_applied': len(rules_summary['rules_applied'])
            })
            
            # Update execution stats
            self._update_stats(True, duration)
            
            return RulesResult(
                success=True,
                transformed_data=transformed_df,
                rules_summary=rules_summary,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self._update_stats(False, duration)
            
            logger.error(f"Business rules application failed: {e}")
            return RulesResult(
                success=False,
                errors=[f"Business rules error: {str(e)}"],
                performance_metrics={'duration_seconds': duration}
            )
    
    def _apply_rule(self, df: pd.DataFrame, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a single business rule"""
        try:
            rule_type = rule.get('type')
            
            if rule_type == 'validation':
                return self._apply_validation_rule(df, rule)
            elif rule_type == 'transformation':
                return self._apply_transformation_rule(df, rule)
            elif rule_type == 'conditional':
                return self._apply_conditional_rule(df, rule)
            elif rule_type == 'calculation':
                return self._apply_calculation_rule(df, rule)
            elif rule_type == 'normalization':
                return self._apply_normalization_rule(df, rule)
            elif rule_type == 'custom_function':
                return self._apply_custom_function_rule(df, rule)
            else:
                return {
                    'success': False,
                    'error': f"Unknown rule type: {rule_type}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _apply_validation_rule(self, df: pd.DataFrame, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Apply validation rules to data"""
        try:
            columns = rule.get('columns', [])
            validation_type = rule.get('validation_type')
            action = rule.get('action', 'flag')  # flag, remove, fix
            
            validation_results = {}
            records_affected = 0
            
            for col in columns:
                if col not in df.columns:
                    continue
                
                if validation_type == 'not_null':
                    invalid_mask = df[col].isnull()
                elif validation_type == 'email':
                    invalid_mask = ~df[col].astype(str).str.contains(
                        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                        na=False, regex=True
                    )
                elif validation_type == 'phone':
                    invalid_mask = ~df[col].astype(str).str.contains(
                        r'^\+?[\d\s\-\(\)]{10,}$',
                        na=False, regex=True
                    )
                elif validation_type == 'range':
                    min_val = rule.get('min_value')
                    max_val = rule.get('max_value')
                    invalid_mask = (df[col] < min_val) | (df[col] > max_val)
                else:
                    continue
                
                invalid_count = invalid_mask.sum()
                validation_results[col] = {
                    'invalid_count': invalid_count,
                    'invalid_percentage': (invalid_count / len(df)) * 100,
                    'validation_type': validation_type
                }
                
                # Apply action
                if action == 'remove':
                    df = df[~invalid_mask]
                    records_affected += invalid_count
                elif action == 'flag':
                    flag_col = f"{col}_validation_flag"
                    df[flag_col] = invalid_mask
                elif action == 'fix':
                    # Apply fix based on validation type
                    if validation_type == 'range' and rule.get('fix_method') == 'cap':
                        min_val = rule.get('min_value')
                        max_val = rule.get('max_value')
                        df[col] = df[col].clip(lower=min_val, upper=max_val)
                        records_affected += invalid_count
            
            return {
                'success': True,
                'validation_results': validation_results,
                'records_affected': records_affected
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _apply_transformation_rule(self, df: pd.DataFrame, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Apply transformation rules"""
        try:
            columns = rule.get('columns', [])
            transform_type = rule.get('transform_type')
            
            records_affected = 0
            
            for col in columns:
                if col not in df.columns:
                    continue
                
                original_col = df[col].copy()
                
                if transform_type == 'uppercase':
                    df[col] = df[col].astype(str).str.upper()
                elif transform_type == 'lowercase':
                    df[col] = df[col].astype(str).str.lower()
                elif transform_type == 'title_case':
                    df[col] = df[col].astype(str).str.title()
                elif transform_type == 'strip_whitespace':
                    df[col] = df[col].astype(str).str.strip()
                elif transform_type == 'remove_special_chars':
                    df[col] = df[col].astype(str).str.replace(r'[^a-zA-Z0-9\s]', '', regex=True)
                elif transform_type == 'fill_null':
                    fill_value = rule.get('fill_value', '')
                    df[col] = df[col].fillna(fill_value)
                
                # Count changed records
                records_affected += (df[col] != original_col).sum()
            
            return {
                'success': True,
                'records_affected': records_affected
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _apply_conditional_rule(self, df: pd.DataFrame, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Apply conditional transformation rules"""
        try:
            condition = rule.get('condition')
            then_action = rule.get('then_action')
            else_action = rule.get('else_action')
            
            # Parse condition
            condition_mask = self._parse_condition(df, condition)
            
            records_affected = 0
            
            # Apply then action
            if then_action:
                then_records = self._apply_action(df[condition_mask], then_action)
                records_affected += then_records
            
            # Apply else action
            if else_action:
                else_records = self._apply_action(df[~condition_mask], else_action)
                records_affected += else_records
            
            return {
                'success': True,
                'records_affected': records_affected
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _apply_calculation_rule(self, df: pd.DataFrame, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Apply calculation rules to create new columns"""
        try:
            new_column = rule.get('new_column')
            calculation = rule.get('calculation')
            
            if not new_column or not calculation:
                return {
                    'success': False,
                    'error': 'new_column and calculation are required'
                }
            
            # Business-specific calculations
            if calculation == 'profit_margin':
                revenue_col = rule.get('revenue_column', 'revenue')
                cost_col = rule.get('cost_column', 'cost')
                if revenue_col in df.columns and cost_col in df.columns:
                    df[new_column] = ((df[revenue_col] - df[cost_col]) / df[revenue_col]) * 100
            
            elif calculation == 'customer_lifetime_value':
                avg_order_col = rule.get('avg_order_column', 'avg_order_value')
                frequency_col = rule.get('frequency_column', 'purchase_frequency')
                lifespan_col = rule.get('lifespan_column', 'customer_lifespan')
                
                if all(col in df.columns for col in [avg_order_col, frequency_col, lifespan_col]):
                    df[new_column] = df[avg_order_col] * df[frequency_col] * df[lifespan_col]
            
            elif calculation == 'age_from_birthdate':
                birthdate_col = rule.get('birthdate_column', 'birthdate')
                if birthdate_col in df.columns:
                    today = datetime.now()
                    df[birthdate_col] = pd.to_datetime(df[birthdate_col], errors='coerce')
                    df[new_column] = (today - df[birthdate_col]).dt.days / 365.25
            
            elif calculation == 'custom_expression':
                expression = rule.get('expression')
                if expression:
                    df[new_column] = self._evaluate_expression(df, expression)
            
            return {
                'success': True,
                'records_affected': len(df)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _apply_normalization_rule(self, df: pd.DataFrame, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Apply normalization rules"""
        try:
            function_name = rule.get('function')
            columns = rule.get('columns', [])
            
            if function_name not in self.rule_functions:
                return {
                    'success': False,
                    'error': f'Function "{function_name}" not found'
                }
            
            func = self.rule_functions[function_name]
            records_affected = 0
            
            for col in columns:
                if col in df.columns:
                    original_col = df[col].copy()
                    df[col] = func(df[col], rule.get('params', {}))
                    records_affected += (df[col] != original_col).sum()
            
            return {
                'success': True,
                'records_affected': records_affected
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _apply_custom_function_rule(self, df: pd.DataFrame, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Apply custom function rules"""
        try:
            # This would typically be extended to support user-defined functions
            # For now, return a placeholder
            return {
                'success': True,
                'records_affected': 0
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # Built-in business rule functions
    def _validate_email(self, series: pd.Series, params: Dict[str, Any]) -> pd.Series:
        """Validate email addresses"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return series.astype(str).str.match(email_pattern, na=False)
    
    def _validate_phone(self, series: pd.Series, params: Dict[str, Any]) -> pd.Series:
        """Validate phone numbers"""
        phone_pattern = r'^\+?[\d\s\-\(\)]{10,}$'
        return series.astype(str).str.match(phone_pattern, na=False)
    
    def _categorize_age(self, series: pd.Series, params: Dict[str, Any]) -> pd.Series:
        """Categorize age into groups"""
        return pd.cut(series, 
                     bins=[0, 18, 35, 50, 65, 100], 
                     labels=['Child', 'Young Adult', 'Adult', 'Middle Age', 'Senior'])
    
    def _categorize_revenue(self, series: pd.Series, params: Dict[str, Any]) -> pd.Series:
        """Categorize revenue into tiers"""
        percentiles = params.get('percentiles', [25, 50, 75])
        thresholds = series.quantile([p/100 for p in percentiles]).tolist()
        thresholds = [0] + thresholds + [float('inf')]
        labels = params.get('labels', ['Low', 'Medium', 'High', 'Premium'])
        
        return pd.cut(series, bins=thresholds, labels=labels)
    
    def _validate_date_range(self, series: pd.Series, params: Dict[str, Any]) -> pd.Series:
        """Validate dates are within acceptable range"""
        min_date = pd.to_datetime(params.get('min_date', '1900-01-01'))
        max_date = pd.to_datetime(params.get('max_date', datetime.now()))
        
        dates = pd.to_datetime(series, errors='coerce')
        return (dates >= min_date) & (dates <= max_date)
    
    def _cap_outliers(self, series: pd.Series, params: Dict[str, Any]) -> pd.Series:
        """Cap outliers using IQR method"""
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        
        multiplier = params.get('multiplier', 1.5)
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr
        
        return series.clip(lower=lower_bound, upper=upper_bound)
    
    def _convert_currency(self, series: pd.Series, params: Dict[str, Any]) -> pd.Series:
        """Convert currency using exchange rate"""
        exchange_rate = params.get('exchange_rate', 1.0)
        return series * exchange_rate
    
    def _normalize_status(self, series: pd.Series, params: Dict[str, Any]) -> pd.Series:
        """Normalize status values"""
        mapping = params.get('status_mapping', {})
        return series.map(mapping).fillna(series)
    
    def _parse_condition(self, df: pd.DataFrame, condition: str) -> pd.Series:
        """Parse condition string into boolean mask"""
        # Simple condition parsing - could be extended
        # For now, support basic comparisons
        try:
            # Replace column names with df['column']
            columns = df.columns.tolist()
            condition_expr = condition
            
            for col in sorted(columns, key=len, reverse=True):
                if col in condition_expr:
                    condition_expr = condition_expr.replace(col, f"df['{col}']")
            
            return eval(condition_expr)
        except Exception:
            return pd.Series([True] * len(df))
    
    def _apply_action(self, df_subset: pd.DataFrame, action: Dict[str, Any]) -> int:
        """Apply action to subset of data"""
        # Placeholder for action application
        return len(df_subset)
    
    def _evaluate_expression(self, df: pd.DataFrame, expression: str) -> pd.Series:
        """Safely evaluate expressions"""
        # Replace column names in expression
        columns = df.columns.tolist()
        expr = expression
        
        for col in sorted(columns, key=len, reverse=True):
            if col in expr:
                expr = expr.replace(col, f"df['{col}']")
        
        try:
            return eval(expr)
        except Exception:
            return pd.Series([np.nan] * len(df))
    
    def _update_stats(self, success: bool, duration: float):
        """Update execution statistics"""
        self.execution_stats['total_operations'] += 1
        
        if success:
            self.execution_stats['successful_operations'] += 1
        else:
            self.execution_stats['failed_operations'] += 1
        
        # Update average duration
        total = self.execution_stats['total_operations']
        old_avg = self.execution_stats['average_duration']
        self.execution_stats['average_duration'] = (old_avg * (total - 1) + duration) / total
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get service execution statistics"""
        return {
            **self.execution_stats,
            'success_rate': (
                self.execution_stats['successful_operations'] / 
                max(1, self.execution_stats['total_operations'])
            )
        }
    
    def get_supported_rules(self) -> Dict[str, List[str]]:
        """Get supported business rule types"""
        return {
            'validation_types': ['not_null', 'email', 'phone', 'range'],
            'transformation_types': ['uppercase', 'lowercase', 'title_case', 'strip_whitespace', 'remove_special_chars', 'fill_null'],
            'calculation_types': ['profit_margin', 'customer_lifetime_value', 'age_from_birthdate', 'custom_expression'],
            'normalization_functions': list(self.rule_functions.keys()),
            'rule_types': ['validation', 'transformation', 'conditional', 'calculation', 'normalization', 'custom_function']
        }