"""
Quality Monitoring Service - Step 3 of Quality Management Pipeline
Monitors and tracks data quality over time with alerts and reporting
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Callable
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class MonitoringConfig:
    """Configuration for quality monitoring"""
    enable_alerts: bool = True
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'missing_percentage': 10.0,
        'duplicate_percentage': 5.0,
        'completeness_drop': 10.0,
        'quality_score_drop': 0.1
    })
    monitoring_frequency: str = "daily"  # daily, weekly, monthly
    store_history: bool = True
    history_retention_days: int = 90
    enable_trend_analysis: bool = True
    comparison_baseline: str = "previous"  # previous, historical_avg, initial

@dataclass
class QualityAlert:
    """Quality alert definition"""
    alert_id: str
    alert_type: str
    severity: str  # low, medium, high, critical
    message: str
    metric_name: str
    current_value: float
    threshold_value: float
    timestamp: datetime
    dataset_info: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MonitoringResult:
    """Result of quality monitoring step"""
    success: bool
    monitoring_summary: Dict[str, Any] = field(default_factory=dict)
    quality_trends: Dict[str, Any] = field(default_factory=dict)
    alerts_generated: List[QualityAlert] = field(default_factory=list)
    compliance_status: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

class QualityMonitoringService:
    """
    Quality Monitoring Service - Step 3 of Quality Management Pipeline
    
    Handles:
    - Continuous quality monitoring and tracking
    - Quality trend analysis and reporting
    - Alert generation for quality degradation
    - Compliance monitoring against quality standards
    - Historical quality data management
    - Quality dashboard and reporting metrics
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.execution_stats = {
            'total_monitoring_operations': 0,
            'successful_monitoring_operations': 0,
            'failed_monitoring_operations': 0,
            'total_alerts_generated': 0,
            'average_monitoring_time': 0.0
        }
        
        # Quality history storage
        self.storage_path = Path(storage_path) if storage_path else Path("./quality_monitoring")
        self.storage_path.mkdir(exist_ok=True, parents=True)
        
        # In-memory history for current session
        self.quality_history = []
        self.alert_history = []
        self.baseline_metrics = {}
        
        # Load existing history
        self._load_historical_data()
        
        logger.info("Quality Monitoring Service initialized")
    
    def monitor_quality(self,
                       current_metrics: Dict[str, Any],
                       dataset_info: Dict[str, Any],
                       config: MonitoringConfig) -> MonitoringResult:
        """
        Monitor data quality and generate alerts/reports
        
        Args:
            current_metrics: Current quality metrics from assessment
            dataset_info: Information about the dataset being monitored
            config: Monitoring configuration
            
        Returns:
            MonitoringResult with monitoring summary and alerts
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting quality monitoring for dataset: {dataset_info.get('name', 'unknown')}")
            
            # Initialize result
            result = MonitoringResult(success=False)
            
            # Store current metrics in history
            if config.store_history:
                self._store_quality_metrics(current_metrics, dataset_info, start_time)
            
            # Generate monitoring summary
            monitoring_summary = self._generate_monitoring_summary(current_metrics, dataset_info)
            
            # Analyze quality trends
            quality_trends = {}
            if config.enable_trend_analysis:
                quality_trends = self._analyze_quality_trends(
                    current_metrics, dataset_info, config
                )
            
            # Generate alerts based on thresholds
            alerts_generated = []
            if config.enable_alerts:
                alerts_generated = self._generate_quality_alerts(
                    current_metrics, dataset_info, config, quality_trends
                )
                
                # Store alerts
                self.alert_history.extend(alerts_generated)
            
            # Check compliance status
            compliance_status = self._check_compliance_status(
                current_metrics, dataset_info, config
            )
            
            # Generate recommendations
            recommendations = self._generate_monitoring_recommendations(
                current_metrics, quality_trends, alerts_generated, compliance_status
            )
            
            # Clean up old history if needed
            if config.store_history:
                self._cleanup_old_history(config.history_retention_days)
            
            # Success
            result.success = True
            result.monitoring_summary = monitoring_summary
            result.quality_trends = quality_trends
            result.alerts_generated = alerts_generated
            result.compliance_status = compliance_status
            result.recommendations = recommendations
            
            return self._finalize_monitoring_result(result, start_time)
            
        except Exception as e:
            logger.error(f"Quality monitoring failed: {e}")
            result.errors.append(f"Monitoring error: {str(e)}")
            return self._finalize_monitoring_result(result, start_time)
    
    def _store_quality_metrics(self,
                              metrics: Dict[str, Any],
                              dataset_info: Dict[str, Any],
                              timestamp: datetime):
        """Store quality metrics in history"""
        try:
            quality_record = {
                'timestamp': timestamp.isoformat(),
                'dataset_name': dataset_info.get('name', 'unknown'),
                'dataset_id': dataset_info.get('id', 'unknown'),
                'metrics': metrics,
                'dataset_info': dataset_info
            }
            
            # Add to in-memory history
            self.quality_history.append(quality_record)
            
            # Save to disk
            history_file = self.storage_path / f"quality_history_{datetime.now().strftime('%Y%m')}.json"
            
            # Load existing history for the month
            existing_history = []
            if history_file.exists():
                try:
                    with open(history_file, 'r') as f:
                        existing_history = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not load existing history: {e}")
            
            # Append new record
            existing_history.append(quality_record)
            
            # Save updated history
            with open(history_file, 'w') as f:
                json.dump(existing_history, f, indent=2, default=str)
            
            logger.debug(f"Stored quality metrics for {dataset_info.get('name')}")
            
        except Exception as e:
            logger.error(f"Failed to store quality metrics: {e}")
    
    def _generate_monitoring_summary(self,
                                   current_metrics: Dict[str, Any],
                                   dataset_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive monitoring summary"""
        try:
            summary = {
                'dataset_name': dataset_info.get('name', 'unknown'),
                'monitoring_timestamp': datetime.now().isoformat(),
                'current_quality_score': current_metrics.get('overall_quality_score', 0),
                'key_metrics': {
                    'missing_percentage': current_metrics.get('missing_values', {}).get('missing_percentage', 0),
                    'duplicate_percentage': current_metrics.get('duplicates', {}).get('duplicate_percentage', 0),
                    'completeness': current_metrics.get('completeness', {}).get('overall_completeness', 0),
                    'consistency_score': current_metrics.get('consistency', {}).get('consistency_score', 0)
                },
                'data_characteristics': {
                    'total_rows': dataset_info.get('shape', [0, 0])[0],
                    'total_columns': dataset_info.get('shape', [0, 0])[1],
                    'last_updated': dataset_info.get('last_updated'),
                    'data_source': dataset_info.get('source')
                }
            }
            
            # Add quality categorization
            quality_score = summary['current_quality_score']
            if quality_score >= 0.9:
                summary['quality_category'] = 'excellent'
            elif quality_score >= 0.7:
                summary['quality_category'] = 'good'
            elif quality_score >= 0.5:
                summary['quality_category'] = 'fair'
            else:
                summary['quality_category'] = 'poor'
            
            return summary
            
        except Exception as e:
            logger.error(f"Monitoring summary generation failed: {e}")
            return {}
    
    def _analyze_quality_trends(self,
                               current_metrics: Dict[str, Any],
                               dataset_info: Dict[str, Any],
                               config: MonitoringConfig) -> Dict[str, Any]:
        """Analyze quality trends over time"""
        try:
            dataset_name = dataset_info.get('name', 'unknown')
            
            # Get historical data for this dataset
            historical_data = [
                record for record in self.quality_history
                if record['dataset_name'] == dataset_name
            ]
            
            if len(historical_data) < 2:
                return {
                    'trend_analysis': 'insufficient_data',
                    'message': 'Need at least 2 data points for trend analysis'
                }
            
            # Sort by timestamp
            historical_data.sort(key=lambda x: x['timestamp'])
            
            trends = {}
            
            # Analyze key metrics trends
            key_metrics = [
                'overall_quality_score',
                ('missing_values', 'missing_percentage'),
                ('duplicates', 'duplicate_percentage'),
                ('completeness', 'overall_completeness')
            ]
            
            for metric in key_metrics:
                if isinstance(metric, tuple):
                    metric_category, metric_name = metric
                    values = []
                    for record in historical_data:
                        metric_value = record['metrics'].get(metric_category, {}).get(metric_name)
                        if metric_value is not None:
                            values.append(metric_value)
                    trend_key = f"{metric_category}_{metric_name}"
                else:
                    values = []
                    for record in historical_data:
                        metric_value = record['metrics'].get(metric)
                        if metric_value is not None:
                            values.append(metric_value)
                    trend_key = metric
                
                if len(values) >= 2:
                    trends[trend_key] = self._calculate_trend(values)
            
            # Compare with baseline
            baseline_comparison = self._compare_with_baseline(
                current_metrics, dataset_name, config.comparison_baseline
            )
            
            return {
                'trends': trends,
                'baseline_comparison': baseline_comparison,
                'historical_data_points': len(historical_data),
                'trend_period': f"{historical_data[0]['timestamp']} to {historical_data[-1]['timestamp']}"
            }
            
        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return {'error': str(e)}
    
    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend direction and magnitude"""
        try:
            if len(values) < 2:
                return {'trend': 'unknown', 'change': 0}
            
            # Calculate linear trend
            x = np.arange(len(values))
            y = np.array(values)
            
            # Simple linear regression
            slope = np.polyfit(x, y, 1)[0]
            
            # Calculate percentage change
            recent_avg = np.mean(values[-3:]) if len(values) >= 3 else values[-1]
            older_avg = np.mean(values[:3]) if len(values) >= 3 else values[0]
            
            percentage_change = ((recent_avg - older_avg) / abs(older_avg)) * 100 if older_avg != 0 else 0
            
            # Determine trend direction
            if abs(slope) < 0.001:  # Very small change
                trend_direction = 'stable'
            elif slope > 0:
                trend_direction = 'improving'
            else:
                trend_direction = 'declining'
            
            return {
                'trend': trend_direction,
                'slope': slope,
                'percentage_change': percentage_change,
                'current_value': values[-1],
                'previous_value': values[-2] if len(values) >= 2 else None,
                'volatility': np.std(values) if len(values) > 1 else 0
            }
            
        except Exception as e:
            logger.error(f"Trend calculation failed: {e}")
            return {'trend': 'unknown', 'error': str(e)}
    
    def _compare_with_baseline(self,
                              current_metrics: Dict[str, Any],
                              dataset_name: str,
                              baseline_type: str) -> Dict[str, Any]:
        """Compare current metrics with baseline"""
        try:
            if baseline_type == "initial":
                # Compare with first recorded metrics
                baseline_data = next(
                    (record for record in self.quality_history 
                     if record['dataset_name'] == dataset_name),
                    None
                )
            elif baseline_type == "historical_avg":
                # Compare with historical average
                dataset_records = [
                    record for record in self.quality_history
                    if record['dataset_name'] == dataset_name
                ]
                if not dataset_records:
                    return {'comparison': 'no_baseline_data'}
                
                # Calculate averages
                baseline_data = {'metrics': {}}
                for record in dataset_records:
                    for key, value in record['metrics'].items():
                        if isinstance(value, dict):
                            if key not in baseline_data['metrics']:
                                baseline_data['metrics'][key] = {}
                            for subkey, subvalue in value.items():
                                if isinstance(subvalue, (int, float)):
                                    if subkey not in baseline_data['metrics'][key]:
                                        baseline_data['metrics'][key][subkey] = []
                                    baseline_data['metrics'][key][subkey].append(subvalue)
                
                # Convert lists to averages
                for key, value in baseline_data['metrics'].items():
                    if isinstance(value, dict):
                        for subkey, subvalues in value.items():
                            if isinstance(subvalues, list):
                                baseline_data['metrics'][key][subkey] = np.mean(subvalues)
            
            else:  # previous
                # Compare with previous measurement
                dataset_records = [
                    record for record in self.quality_history
                    if record['dataset_name'] == dataset_name
                ]
                if len(dataset_records) < 2:
                    return {'comparison': 'insufficient_history'}
                
                # Sort by timestamp and get second-to-last
                dataset_records.sort(key=lambda x: x['timestamp'])
                baseline_data = dataset_records[-2]
            
            if not baseline_data:
                return {'comparison': 'no_baseline_data'}
            
            # Calculate differences
            comparisons = {}
            
            # Overall quality score
            current_score = current_metrics.get('overall_quality_score', 0)
            baseline_score = baseline_data['metrics'].get('overall_quality_score', 0)
            
            comparisons['overall_quality_score'] = {
                'current': current_score,
                'baseline': baseline_score,
                'difference': current_score - baseline_score,
                'percentage_change': ((current_score - baseline_score) / baseline_score * 100) if baseline_score != 0 else 0
            }
            
            # Key metrics comparisons
            key_metrics = [
                ('missing_values', 'missing_percentage'),
                ('duplicates', 'duplicate_percentage'),
                ('completeness', 'overall_completeness')
            ]
            
            for category, metric in key_metrics:
                current_value = current_metrics.get(category, {}).get(metric, 0)
                baseline_value = baseline_data['metrics'].get(category, {}).get(metric, 0)
                
                comparisons[f"{category}_{metric}"] = {
                    'current': current_value,
                    'baseline': baseline_value,
                    'difference': current_value - baseline_value,
                    'percentage_change': ((current_value - baseline_value) / baseline_value * 100) if baseline_value != 0 else 0
                }
            
            return {
                'baseline_type': baseline_type,
                'comparisons': comparisons,
                'baseline_timestamp': baseline_data.get('timestamp')
            }
            
        except Exception as e:
            logger.error(f"Baseline comparison failed: {e}")
            return {'error': str(e)}
    
    def _generate_quality_alerts(self,
                               current_metrics: Dict[str, Any],
                               dataset_info: Dict[str, Any],
                               config: MonitoringConfig,
                               trends: Dict[str, Any]) -> List[QualityAlert]:
        """Generate quality alerts based on thresholds and trends"""
        alerts = []
        
        try:
            dataset_name = dataset_info.get('name', 'unknown')
            timestamp = datetime.now()
            
            # Missing values alert
            missing_pct = current_metrics.get('missing_values', {}).get('missing_percentage', 0)
            if missing_pct > config.alert_thresholds.get('missing_percentage', 10):
                alert = QualityAlert(
                    alert_id=f"missing_{dataset_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}",
                    alert_type="missing_values",
                    severity="high" if missing_pct > 20 else "medium",
                    message=f"High missing values detected: {missing_pct:.2f}% (threshold: {config.alert_thresholds['missing_percentage']}%)",
                    metric_name="missing_percentage",
                    current_value=missing_pct,
                    threshold_value=config.alert_thresholds['missing_percentage'],
                    timestamp=timestamp,
                    dataset_info=dataset_info
                )
                alerts.append(alert)
            
            # Duplicate values alert
            dup_pct = current_metrics.get('duplicates', {}).get('duplicate_percentage', 0)
            if dup_pct > config.alert_thresholds.get('duplicate_percentage', 5):
                alert = QualityAlert(
                    alert_id=f"duplicates_{dataset_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}",
                    alert_type="duplicates",
                    severity="medium" if dup_pct < 15 else "high",
                    message=f"High duplicate records detected: {dup_pct:.2f}% (threshold: {config.alert_thresholds['duplicate_percentage']}%)",
                    metric_name="duplicate_percentage",
                    current_value=dup_pct,
                    threshold_value=config.alert_thresholds['duplicate_percentage'],
                    timestamp=timestamp,
                    dataset_info=dataset_info
                )
                alerts.append(alert)
            
            # Quality score drop alert
            current_score = current_metrics.get('overall_quality_score', 0)
            if trends and 'baseline_comparison' in trends:
                baseline_comparison = trends['baseline_comparison']
                if 'comparisons' in baseline_comparison:
                    score_comparison = baseline_comparison['comparisons'].get('overall_quality_score', {})
                    score_drop = -score_comparison.get('difference', 0)  # Negative difference means drop
                    
                    if score_drop > config.alert_thresholds.get('quality_score_drop', 0.1):
                        alert = QualityAlert(
                            alert_id=f"quality_drop_{dataset_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}",
                            alert_type="quality_degradation",
                            severity="critical" if score_drop > 0.2 else "high",
                            message=f"Quality score dropped significantly: {score_drop:.3f} (threshold: {config.alert_thresholds['quality_score_drop']})",
                            metric_name="overall_quality_score",
                            current_value=current_score,
                            threshold_value=config.alert_thresholds['quality_score_drop'],
                            timestamp=timestamp,
                            dataset_info=dataset_info
                        )
                        alerts.append(alert)
            
            # Trend-based alerts
            if trends and 'trends' in trends:
                for metric_name, trend_info in trends['trends'].items():
                    if trend_info.get('trend') == 'declining':
                        percentage_change = trend_info.get('percentage_change', 0)
                        if abs(percentage_change) > 15:  # More than 15% decline
                            alert = QualityAlert(
                                alert_id=f"trend_{metric_name}_{dataset_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}",
                                alert_type="declining_trend",
                                severity="medium",
                                message=f"Declining trend detected in {metric_name}: {percentage_change:.1f}% change",
                                metric_name=metric_name,
                                current_value=trend_info.get('current_value', 0),
                                threshold_value=15.0,
                                timestamp=timestamp,
                                dataset_info=dataset_info
                            )
                            alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Alert generation failed: {e}")
            return []
    
    def _check_compliance_status(self,
                               current_metrics: Dict[str, Any],
                               dataset_info: Dict[str, Any],
                               config: MonitoringConfig) -> Dict[str, Any]:
        """Check compliance against quality standards"""
        try:
            compliance_checks = {
                'missing_values_compliant': True,
                'duplicate_compliance': True,
                'overall_quality_compliant': True,
                'completeness_compliant': True
            }
            
            compliance_details = {}
            
            # Missing values compliance
            missing_pct = current_metrics.get('missing_values', {}).get('missing_percentage', 0)
            missing_threshold = config.alert_thresholds.get('missing_percentage', 10)
            compliance_checks['missing_values_compliant'] = missing_pct <= missing_threshold
            compliance_details['missing_values'] = {
                'current': missing_pct,
                'threshold': missing_threshold,
                'compliant': compliance_checks['missing_values_compliant']
            }
            
            # Duplicates compliance
            dup_pct = current_metrics.get('duplicates', {}).get('duplicate_percentage', 0)
            dup_threshold = config.alert_thresholds.get('duplicate_percentage', 5)
            compliance_checks['duplicate_compliance'] = dup_pct <= dup_threshold
            compliance_details['duplicates'] = {
                'current': dup_pct,
                'threshold': dup_threshold,
                'compliant': compliance_checks['duplicate_compliance']
            }
            
            # Overall quality compliance
            quality_score = current_metrics.get('overall_quality_score', 0)
            quality_threshold = 0.7  # 70% minimum quality
            compliance_checks['overall_quality_compliant'] = quality_score >= quality_threshold
            compliance_details['overall_quality'] = {
                'current': quality_score,
                'threshold': quality_threshold,
                'compliant': compliance_checks['overall_quality_compliant']
            }
            
            # Completeness compliance
            completeness = current_metrics.get('completeness', {}).get('overall_completeness', 0)
            completeness_threshold = 80  # 80% minimum completeness
            compliance_checks['completeness_compliant'] = completeness >= completeness_threshold
            compliance_details['completeness'] = {
                'current': completeness,
                'threshold': completeness_threshold,
                'compliant': compliance_checks['completeness_compliant']
            }
            
            # Overall compliance status
            overall_compliant = all(compliance_checks.values())
            
            return {
                'overall_compliant': overall_compliant,
                'individual_checks': compliance_checks,
                'compliance_details': compliance_details,
                'compliance_score': sum(compliance_checks.values()) / len(compliance_checks),
                'non_compliant_areas': [
                    area for area, compliant in compliance_checks.items() 
                    if not compliant
                ]
            }
            
        except Exception as e:
            logger.error(f"Compliance check failed: {e}")
            return {'error': str(e)}
    
    def _generate_monitoring_recommendations(self,
                                           current_metrics: Dict[str, Any],
                                           trends: Dict[str, Any],
                                           alerts: List[QualityAlert],
                                           compliance: Dict[str, Any]) -> List[str]:
        """Generate monitoring-based recommendations"""
        recommendations = []
        
        try:
            # Alert-based recommendations
            if alerts:
                high_severity_alerts = [a for a in alerts if a.severity in ['high', 'critical']]
                if high_severity_alerts:
                    recommendations.append("Address critical data quality issues immediately")
                    recommendations.append("Implement automated data quality checks at ingestion")
                
                missing_alerts = [a for a in alerts if a.alert_type == 'missing_values']
                if missing_alerts:
                    recommendations.append("Review data collection processes to reduce missing values")
                
                duplicate_alerts = [a for a in alerts if a.alert_type == 'duplicates']
                if duplicate_alerts:
                    recommendations.append("Implement deduplication processes in data pipeline")
            
            # Trend-based recommendations
            if trends and 'trends' in trends:
                declining_trends = [
                    metric for metric, trend_info in trends['trends'].items()
                    if trend_info.get('trend') == 'declining'
                ]
                if declining_trends:
                    recommendations.append("Monitor declining quality trends closely")
                    recommendations.append("Consider implementing quality improvement measures")
            
            # Compliance-based recommendations
            if compliance and not compliance.get('overall_compliant', True):
                non_compliant_areas = compliance.get('non_compliant_areas', [])
                if 'missing_values_compliant' in non_compliant_areas:
                    recommendations.append("Improve data collection to meet missing values compliance")
                if 'duplicate_compliance' in non_compliant_areas:
                    recommendations.append("Implement duplicate detection and removal processes")
                if 'overall_quality_compliant' in non_compliant_areas:
                    recommendations.append("Comprehensive quality improvement program needed")
            
            # Quality score based recommendations
            quality_score = current_metrics.get('overall_quality_score', 0)
            if quality_score < 0.5:
                recommendations.append("Critical: Data quality is below acceptable standards")
                recommendations.append("Consider data quality remediation project")
            elif quality_score < 0.7:
                recommendations.append("Data quality improvement initiatives recommended")
            
            # General monitoring recommendations
            if len(self.quality_history) < 10:
                recommendations.append("Continue monitoring to establish quality baselines")
            
            recommendations.append("Schedule regular quality reviews with data stakeholders")
            
            # Remove duplicates and limit to top recommendations
            unique_recommendations = list(dict.fromkeys(recommendations))
            return unique_recommendations[:10]  # Top 10 recommendations
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            return ["Monitor data quality regularly", "Implement quality improvement processes"]
    
    def _load_historical_data(self):
        """Load historical quality data from storage"""
        try:
            # Load recent history files
            for history_file in self.storage_path.glob("quality_history_*.json"):
                try:
                    with open(history_file, 'r') as f:
                        file_history = json.load(f)
                        self.quality_history.extend(file_history)
                except Exception as e:
                    logger.warning(f"Could not load history file {history_file}: {e}")
            
            # Sort by timestamp
            self.quality_history.sort(key=lambda x: x['timestamp'])
            
            logger.info(f"Loaded {len(self.quality_history)} historical quality records")
            
        except Exception as e:
            logger.warning(f"Could not load historical data: {e}")
    
    def _cleanup_old_history(self, retention_days: int):
        """Clean up old history records"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # Filter in-memory history
            self.quality_history = [
                record for record in self.quality_history
                if datetime.fromisoformat(record['timestamp']) > cutoff_date
            ]
            
            # Clean up old files
            for history_file in self.storage_path.glob("quality_history_*.json"):
                file_month = history_file.stem.split('_')[-1]
                try:
                    file_date = datetime.strptime(file_month, '%Y%m')
                    if file_date < cutoff_date:
                        history_file.unlink()
                        logger.info(f"Removed old history file: {history_file}")
                except Exception as e:
                    logger.warning(f"Could not process history file {history_file}: {e}")
            
        except Exception as e:
            logger.error(f"History cleanup failed: {e}")
    
    def get_quality_dashboard_data(self, dataset_name: Optional[str] = None) -> Dict[str, Any]:
        """Get data for quality monitoring dashboard"""
        try:
            # Filter by dataset if specified
            if dataset_name:
                history_data = [
                    record for record in self.quality_history
                    if record['dataset_name'] == dataset_name
                ]
            else:
                history_data = self.quality_history
            
            if not history_data:
                return {'message': 'No monitoring data available'}
            
            # Get recent alerts
            recent_alerts = [
                alert for alert in self.alert_history
                if (datetime.now() - alert.timestamp).days <= 7
            ]
            
            # Calculate summary statistics
            latest_records = {}
            for record in history_data:
                dataset = record['dataset_name']
                if dataset not in latest_records or record['timestamp'] > latest_records[dataset]['timestamp']:
                    latest_records[dataset] = record
            
            dashboard_data = {
                'summary': {
                    'total_datasets_monitored': len(latest_records),
                    'recent_alerts': len(recent_alerts),
                    'monitoring_period': f"{history_data[0]['timestamp']} to {history_data[-1]['timestamp']}" if history_data else None
                },
                'latest_quality_scores': {
                    dataset: record['metrics'].get('overall_quality_score', 0)
                    for dataset, record in latest_records.items()
                },
                'recent_alerts': [
                    {
                        'alert_type': alert.alert_type,
                        'severity': alert.severity,
                        'message': alert.message,
                        'dataset': alert.dataset_info.get('name', 'unknown'),
                        'timestamp': alert.timestamp.isoformat()
                    }
                    for alert in recent_alerts[-10:]  # Last 10 alerts
                ],
                'quality_trends': self._calculate_dashboard_trends(history_data),
                'compliance_summary': self._calculate_compliance_summary(latest_records)
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Dashboard data generation failed: {e}")
            return {'error': str(e)}
    
    def _calculate_dashboard_trends(self, history_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trends for dashboard display"""
        try:
            if len(history_data) < 2:
                return {'insufficient_data': True}
            
            # Group by dataset
            dataset_trends = {}
            
            for dataset_name in set(record['dataset_name'] for record in history_data):
                dataset_records = [
                    record for record in history_data
                    if record['dataset_name'] == dataset_name
                ]
                
                if len(dataset_records) >= 2:
                    # Sort by timestamp
                    dataset_records.sort(key=lambda x: x['timestamp'])
                    
                    # Calculate quality score trend
                    quality_scores = [
                        record['metrics'].get('overall_quality_score', 0)
                        for record in dataset_records
                    ]
                    
                    recent_avg = np.mean(quality_scores[-3:]) if len(quality_scores) >= 3 else quality_scores[-1]
                    older_avg = np.mean(quality_scores[:3]) if len(quality_scores) >= 3 else quality_scores[0]
                    
                    trend_direction = 'stable'
                    if recent_avg > older_avg * 1.05:
                        trend_direction = 'improving'
                    elif recent_avg < older_avg * 0.95:
                        trend_direction = 'declining'
                    
                    dataset_trends[dataset_name] = {
                        'trend_direction': trend_direction,
                        'current_score': quality_scores[-1],
                        'score_change': recent_avg - older_avg,
                        'data_points': len(dataset_records)
                    }
            
            return dataset_trends
            
        except Exception as e:
            logger.error(f"Dashboard trends calculation failed: {e}")
            return {}
    
    def _calculate_compliance_summary(self, latest_records: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate compliance summary for dashboard"""
        try:
            compliant_datasets = 0
            total_datasets = len(latest_records)
            
            if total_datasets == 0:
                return {'no_data': True}
            
            compliance_details = {}
            
            for dataset_name, record in latest_records.items():
                metrics = record['metrics']
                
                # Simple compliance check
                missing_pct = metrics.get('missing_values', {}).get('missing_percentage', 0)
                quality_score = metrics.get('overall_quality_score', 0)
                
                is_compliant = missing_pct <= 10 and quality_score >= 0.7
                
                if is_compliant:
                    compliant_datasets += 1
                
                compliance_details[dataset_name] = {
                    'compliant': is_compliant,
                    'quality_score': quality_score,
                    'missing_percentage': missing_pct
                }
            
            return {
                'compliance_rate': (compliant_datasets / total_datasets) * 100,
                'compliant_datasets': compliant_datasets,
                'total_datasets': total_datasets,
                'details': compliance_details
            }
            
        except Exception as e:
            logger.error(f"Compliance summary calculation failed: {e}")
            return {}
    
    def _finalize_monitoring_result(self,
                                  result: MonitoringResult,
                                  start_time: datetime) -> MonitoringResult:
        """Finalize monitoring result with timing and stats"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Update performance metrics
        result.performance_metrics['monitoring_duration_seconds'] = duration
        result.performance_metrics['end_time'] = end_time
        result.performance_metrics['alerts_generated'] = len(result.alerts_generated)
        
        # Update execution stats
        self.execution_stats['total_monitoring_operations'] += 1
        if result.success:
            self.execution_stats['successful_monitoring_operations'] += 1
            self.execution_stats['total_alerts_generated'] += len(result.alerts_generated)
        else:
            self.execution_stats['failed_monitoring_operations'] += 1
        
        # Update average duration
        total = self.execution_stats['total_monitoring_operations']
        old_avg = self.execution_stats['average_monitoring_time']
        self.execution_stats['average_monitoring_time'] = (old_avg * (total - 1) + duration) / total
        
        logger.info(f"Quality monitoring completed: success={result.success}, duration={duration:.2f}s, alerts={len(result.alerts_generated)}")
        return result
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get service execution statistics"""
        return {
            **self.execution_stats,
            'success_rate': (
                self.execution_stats['successful_monitoring_operations'] / 
                max(1, self.execution_stats['total_monitoring_operations'])
            ),
            'average_alerts_per_operation': (
                self.execution_stats['total_alerts_generated'] / 
                max(1, self.execution_stats['successful_monitoring_operations'])
            )
        }