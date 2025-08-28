"""
Storage Target Selection Service - Step 1 of Storage Pipeline
Analyzes data characteristics and recommends optimal storage targets
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class TargetSelectionResult:
    """Result of storage target selection step"""
    success: bool
    recommended_targets: List[Dict[str, Any]] = field(default_factory=list)
    data_analysis: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

class StorageTargetSelectionService:
    """
    Storage Target Selection Service - Step 1 of Storage Pipeline
    
    Handles:
    - Data characteristics analysis
    - Storage type recommendations based on data patterns
    - Performance and efficiency scoring
    - User preference consideration
    """
    
    def __init__(self):
        self.execution_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'average_duration': 0.0
        }
        
        # Storage type scoring criteria
        self.storage_types = {
            'duckdb': {
                'strengths': ['analytics', 'sql_queries', 'large_datasets', 'numeric_data'],
                'weaknesses': ['interchange', 'simple_exports'],
                'use_cases': ['analytical_workloads', 'data_science', 'reporting']
            },
            'parquet': {
                'strengths': ['compression', 'columnar', 'large_files', 'analytics'],
                'weaknesses': ['row_updates', 'streaming'],
                'use_cases': ['data_warehousing', 'archival', 'analytics']
            },
            'csv': {
                'strengths': ['compatibility', 'human_readable', 'simple', 'interchange'],
                'weaknesses': ['size', 'types', 'performance'],
                'use_cases': ['data_exchange', 'reporting', 'simple_storage']
            }
        }
        
        logger.info("Storage Target Selection Service initialized")
    
    def select_targets(self, 
                      data: pd.DataFrame,
                      selection_config: Dict[str, Any]) -> TargetSelectionResult:
        """
        Analyze data and recommend storage targets
        
        Args:
            data: Input DataFrame to analyze
            selection_config: Configuration for target selection
            
        Returns:
            TargetSelectionResult with recommendations
        """
        start_time = datetime.now()
        
        try:
            # Analyze data characteristics
            data_analysis = self._analyze_data_characteristics(data)
            
            # Score storage types
            storage_scores = self._score_storage_types(data_analysis, selection_config)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(storage_scores, data_analysis)
            
            # Apply user preferences if provided
            if selection_config.get('user_preferences'):
                recommendations = self._apply_user_preferences(
                    recommendations, 
                    selection_config['user_preferences']
                )
            
            # Calculate performance metrics
            duration = (datetime.now() - start_time).total_seconds()
            performance_metrics = {
                'duration_seconds': duration,
                'data_rows_analyzed': len(data),
                'data_columns_analyzed': len(data.columns),
                'storage_types_evaluated': len(self.storage_types),
                'recommendations_generated': len(recommendations)
            }
            
            # Update execution stats
            self._update_stats(True, duration)
            
            return TargetSelectionResult(
                success=True,
                recommended_targets=recommendations,
                data_analysis=data_analysis,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self._update_stats(False, duration)
            
            logger.error(f"Storage target selection failed: {e}")
            return TargetSelectionResult(
                success=False,
                errors=[f"Target selection error: {str(e)}"],
                performance_metrics={'duration_seconds': duration}
            )
    
    def _analyze_data_characteristics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze DataFrame characteristics for storage decisions"""
        try:
            analysis = {
                'basic_stats': {
                    'row_count': len(data),
                    'column_count': len(data.columns),
                    'memory_usage_mb': data.memory_usage(deep=True).sum() / 1024 / 1024,
                    'estimated_size_mb': data.memory_usage(deep=True).sum() / 1024 / 1024 * 1.2  # Rough estimate
                },
                'data_types': {},
                'quality_metrics': {},
                'patterns': {
                    'has_time_series': False,
                    'has_categorical': False,
                    'has_numeric': False,
                    'has_text': False,
                    'has_mixed_types': False
                },
                'complexity_indicators': {
                    'null_percentage': 0,
                    'unique_ratio': 0,
                    'cardinality_distribution': {},
                    'memory_efficiency': 0
                }
            }
            
            # Analyze each column
            numeric_cols = 0
            categorical_cols = 0
            text_cols = 0
            datetime_cols = 0
            total_nulls = 0
            total_unique = 0
            
            for col in data.columns:
                dtype = str(data[col].dtype)
                null_count = data[col].isnull().sum()
                unique_count = data[col].nunique()
                
                # Store column-level info
                analysis['data_types'][col] = {
                    'dtype': dtype,
                    'null_count': null_count,
                    'null_percentage': (null_count / len(data)) * 100,
                    'unique_count': unique_count,
                    'unique_percentage': (unique_count / len(data)) * 100
                }
                
                # Aggregate statistics
                total_nulls += null_count
                total_unique += unique_count
                
                # Categorize data types
                if dtype in ['int64', 'int32', 'float64', 'float32']:
                    numeric_cols += 1
                    analysis['patterns']['has_numeric'] = True
                elif 'datetime' in dtype:
                    datetime_cols += 1
                    analysis['patterns']['has_time_series'] = True
                elif dtype == 'category':
                    categorical_cols += 1
                    analysis['patterns']['has_categorical'] = True
                elif dtype == 'object':
                    # Determine if it's categorical or text
                    unique_ratio = unique_count / len(data)
                    if unique_ratio < 0.1:  # Low cardinality suggests categorical
                        categorical_cols += 1
                        analysis['patterns']['has_categorical'] = True
                    else:
                        text_cols += 1
                        analysis['patterns']['has_text'] = True
            
            # Calculate complexity indicators
            analysis['complexity_indicators']['null_percentage'] = (total_nulls / (len(data) * len(data.columns))) * 100
            analysis['complexity_indicators']['unique_ratio'] = total_unique / (len(data) * len(data.columns))
            
            # Cardinality distribution
            analysis['complexity_indicators']['cardinality_distribution'] = {
                'numeric_columns': numeric_cols,
                'categorical_columns': categorical_cols,
                'text_columns': text_cols,
                'datetime_columns': datetime_cols
            }
            
            # Memory efficiency (how well the data compresses)
            analysis['complexity_indicators']['memory_efficiency'] = self._estimate_memory_efficiency(data)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Data analysis failed: {e}")
            return {'error': str(e)}
    
    def _estimate_memory_efficiency(self, data: pd.DataFrame) -> float:
        """Estimate how efficiently the data can be stored"""
        try:
            # Simple heuristic based on data characteristics
            efficiency_score = 5.0  # Base score
            
            # Numeric data is more efficient
            numeric_ratio = len(data.select_dtypes(include=[np.number]).columns) / len(data.columns)
            efficiency_score += numeric_ratio * 2
            
            # Categorical data with low cardinality is efficient
            for col in data.select_dtypes(include=['object', 'category']).columns:
                unique_ratio = data[col].nunique() / len(data)
                if unique_ratio < 0.1:  # Low cardinality
                    efficiency_score += 1
                elif unique_ratio > 0.8:  # High cardinality
                    efficiency_score -= 0.5
            
            # Null values reduce efficiency
            total_nulls = data.isnull().sum().sum()
            null_ratio = total_nulls / (len(data) * len(data.columns))
            efficiency_score -= null_ratio * 2
            
            return max(0, min(10, efficiency_score))
            
        except Exception:
            return 5.0  # Default score
    
    def _score_storage_types(self, data_analysis: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, float]:
        """Score each storage type based on data characteristics"""
        scores = {}
        
        for storage_type, properties in self.storage_types.items():
            score = 5.0  # Base score
            
            # Analyze data fit
            patterns = data_analysis.get('patterns', {})
            basic_stats = data_analysis.get('basic_stats', {})
            complexity = data_analysis.get('complexity_indicators', {})
            
            # DuckDB scoring
            if storage_type == 'duckdb':
                if patterns.get('has_numeric'):
                    score += 2
                if basic_stats.get('row_count', 0) > 10000:
                    score += 1.5  # Good for large datasets
                if patterns.get('has_time_series'):
                    score += 1  # Good for analytics
                if complexity.get('memory_efficiency', 5) > 7:
                    score += 1
            
            # Parquet scoring  
            elif storage_type == 'parquet':
                if basic_stats.get('row_count', 0) > 100000:
                    score += 2  # Excellent for large datasets
                if patterns.get('has_numeric'):
                    score += 1.5  # Good compression for numeric
                if basic_stats.get('memory_usage_mb', 0) > 100:
                    score += 1  # Good for large files
                if not patterns.get('has_mixed_types'):
                    score += 0.5  # Better for consistent types
            
            # CSV scoring
            elif storage_type == 'csv':
                if basic_stats.get('row_count', 0) < 100000:
                    score += 1  # Better for smaller datasets
                if basic_stats.get('column_count', 0) < 20:
                    score += 1  # Better for fewer columns
                if patterns.get('has_text'):
                    score += 0.5  # Readable text data
                # Penalty for large datasets
                if basic_stats.get('memory_usage_mb', 0) > 500:
                    score -= 2
            
            # Apply use case preferences
            use_case = config.get('use_case', 'general')
            if use_case in properties['use_cases']:
                score += 1.5
            
            # Apply constraint penalties
            constraints = config.get('constraints', [])
            if 'size_efficiency' in constraints and storage_type == 'csv':
                score -= 1
            if 'query_performance' in constraints and storage_type == 'csv':
                score -= 1
            if 'compatibility' in constraints and storage_type in ['duckdb', 'parquet']:
                score -= 0.5
            
            scores[storage_type] = max(0, min(10, score))
        
        return scores
    
    def _generate_recommendations(self, scores: Dict[str, float], data_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate ordered recommendations based on scores"""
        recommendations = []
        
        for storage_type, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            recommendation = {
                'storage_type': storage_type,
                'score': round(score, 2),
                'confidence': self._calculate_confidence(score, scores),
                'reasons': self._get_recommendation_reasons(storage_type, data_analysis),
                'estimated_size_reduction': self._estimate_size_reduction(storage_type, data_analysis),
                'suitability': self._get_suitability_level(score)
            }
            recommendations.append(recommendation)
        
        return recommendations
    
    def _calculate_confidence(self, score: float, all_scores: Dict[str, float]) -> float:
        """Calculate confidence level for recommendation"""
        scores_list = list(all_scores.values())
        max_score = max(scores_list)
        
        if max_score == 0:
            return 0.0
        
        # Confidence based on score gap from second best
        sorted_scores = sorted(scores_list, reverse=True)
        if len(sorted_scores) > 1:
            gap = (score - sorted_scores[1]) / max_score
            confidence = min(1.0, max(0.0, gap + 0.5))
        else:
            confidence = score / 10.0
        
        return round(confidence, 2)
    
    def _get_recommendation_reasons(self, storage_type: str, data_analysis: Dict[str, Any]) -> List[str]:
        """Get reasons for recommendation"""
        reasons = []
        patterns = data_analysis.get('patterns', {})
        basic_stats = data_analysis.get('basic_stats', {})
        
        if storage_type == 'duckdb':
            if patterns.get('has_numeric'):
                reasons.append("Excellent for numeric data analytics")
            if basic_stats.get('row_count', 0) > 10000:
                reasons.append("Optimized for large datasets")
            reasons.append("Supports complex SQL queries")
        
        elif storage_type == 'parquet':
            if basic_stats.get('row_count', 0) > 100000:
                reasons.append("Efficient columnar storage for large datasets")
            reasons.append("Excellent compression ratios")
            reasons.append("Good for archival and data warehousing")
        
        elif storage_type == 'csv':
            reasons.append("Universal compatibility")
            reasons.append("Human-readable format")
            if basic_stats.get('row_count', 0) < 100000:
                reasons.append("Suitable for smaller datasets")
        
        return reasons
    
    def _estimate_size_reduction(self, storage_type: str, data_analysis: Dict[str, Any]) -> float:
        """Estimate size reduction percentage"""
        reductions = {
            'duckdb': 60,    # Good columnar compression
            'parquet': 70,   # Excellent compression
            'csv': -20       # Usually larger than memory
        }
        
        base_reduction = reductions.get(storage_type, 0)
        
        # Adjust based on data characteristics
        patterns = data_analysis.get('patterns', {})
        if patterns.get('has_numeric') and storage_type in ['duckdb', 'parquet']:
            base_reduction += 10  # Numeric data compresses well
        
        return base_reduction
    
    def _get_suitability_level(self, score: float) -> str:
        """Get suitability level based on score"""
        if score >= 8:
            return "highly_recommended"
        elif score >= 6:
            return "recommended" 
        elif score >= 4:
            return "acceptable"
        else:
            return "not_recommended"
    
    def _apply_user_preferences(self, recommendations: List[Dict[str, Any]], preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply user preferences to recommendations"""
        # Adjust scores based on user preferences
        preference_weights = {
            'performance': preferences.get('performance_weight', 1.0),
            'size_efficiency': preferences.get('size_weight', 1.0),
            'compatibility': preferences.get('compatibility_weight', 1.0)
        }
        
        # Re-weight scores (simplified approach)
        for rec in recommendations:
            storage_type = rec['storage_type']
            adjusted_score = rec['score']
            
            # Apply weights based on storage type strengths
            if storage_type == 'duckdb':
                adjusted_score *= preference_weights['performance']
            elif storage_type == 'parquet':
                adjusted_score *= preference_weights['size_efficiency']
            elif storage_type == 'csv':
                adjusted_score *= preference_weights['compatibility']
            
            rec['adjusted_score'] = round(adjusted_score, 2)
        
        # Re-sort by adjusted score
        recommendations.sort(key=lambda x: x.get('adjusted_score', x['score']), reverse=True)
        
        return recommendations
    
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