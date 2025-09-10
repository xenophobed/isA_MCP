"""
Resource Monitoring Utilities

Utilities for monitoring and analyzing system resource usage patterns
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics
import math


class ResourceMonitoringUtils:
    """Utilities for resource monitoring and analysis"""
    
    @staticmethod
    def analyze_resource_utilization(
        usage_records: List[Dict[str, Any]],
        resource_categories: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Analyze resource utilization across different categories
        
        Args:
            usage_records: List of usage records
            resource_categories: Categories of resources to analyze
            
        Returns:
            Dictionary with utilization metrics for each resource category
        """
        utilization = {}
        
        if not usage_records:
            return utilization
        
        total_records = len(usage_records)
        total_tokens = sum(record.get('tokens_used', 0) for record in usage_records)
        total_cost = sum(record.get('cost_usd', 0) for record in usage_records)
        
        # Analyze each resource category
        for category, keywords in resource_categories.items():
            category_records = []
            category_tokens = 0
            category_cost = 0
            
            for record in usage_records:
                endpoint = record.get('endpoint', '').lower()
                tool_name = record.get('tool_name', '').lower() 
                event_type = record.get('event_type', '').lower()
                
                searchable_text = f"{endpoint} {tool_name} {event_type}"
                
                if any(keyword in searchable_text for keyword in keywords):
                    category_records.append(record)
                    category_tokens += record.get('tokens_used', 0)
                    category_cost += record.get('cost_usd', 0)
            
            if category_records:
                utilization[category] = {
                    'usage_count': len(category_records),
                    'usage_percentage': (len(category_records) / total_records) * 100,
                    'token_usage': category_tokens,
                    'token_percentage': (category_tokens / total_tokens * 100) if total_tokens > 0 else 0,
                    'cost_usage': category_cost,
                    'cost_percentage': (category_cost / total_cost * 100) if total_cost > 0 else 0,
                    'avg_tokens_per_operation': category_tokens / len(category_records),
                    'avg_cost_per_operation': category_cost / len(category_records),
                    'utilization_intensity': ResourceMonitoringUtils._calculate_utilization_intensity(category_records)
                }
            else:
                utilization[category] = {
                    'usage_count': 0,
                    'usage_percentage': 0.0,
                    'token_usage': 0,
                    'token_percentage': 0.0,
                    'cost_usage': 0.0,
                    'cost_percentage': 0.0,
                    'avg_tokens_per_operation': 0.0,
                    'avg_cost_per_operation': 0.0,
                    'utilization_intensity': 0.0
                }
        
        return utilization
    
    @staticmethod
    def _calculate_utilization_intensity(records: List[Dict[str, Any]]) -> float:
        """Calculate utilization intensity score for a set of records"""
        if not records:
            return 0.0
        
        # Factors contributing to intensity
        token_values = [record.get('tokens_used', 0) for record in records]
        cost_values = [record.get('cost_usd', 0) for record in records]
        
        # Calculate intensity based on statistical measures
        avg_tokens = statistics.mean(token_values) if token_values else 0
        max_tokens = max(token_values) if token_values else 0
        
        # Normalize intensity (higher tokens = higher intensity)
        base_intensity = min(1.0, avg_tokens / 1000)  # 1000 tokens = moderate intensity
        
        # Boost for high-variance usage (indicates complex operations)
        if len(token_values) > 1:
            token_std = statistics.stdev(token_values)
            variance_boost = min(0.3, token_std / avg_tokens) if avg_tokens > 0 else 0
            base_intensity += variance_boost
        
        # Cost factor
        avg_cost = statistics.mean(cost_values) if cost_values else 0
        cost_factor = min(0.2, avg_cost * 10)  # $0.1 adds 20% intensity
        
        total_intensity = min(1.0, base_intensity + cost_factor)
        return total_intensity
    
    @staticmethod
    def identify_resource_bottlenecks(
        utilization_data: Dict[str, Any],
        threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """
        Identify resource bottlenecks based on utilization data
        
        Args:
            utilization_data: Resource utilization analysis results
            threshold: Bottleneck threshold (0-1)
            
        Returns:
            List of identified bottlenecks with details
        """
        bottlenecks = []
        
        for category, metrics in utilization_data.items():
            utilization_score = metrics.get('utilization_intensity', 0)
            usage_percentage = metrics.get('usage_percentage', 0) / 100
            
            # Check for high utilization
            if utilization_score > threshold:
                bottlenecks.append({
                    'type': 'high_utilization',
                    'category': category,
                    'severity': 'critical' if utilization_score > 0.9 else 'high',
                    'utilization_score': utilization_score,
                    'description': f"High utilization detected in {category} resources",
                    'metrics': metrics
                })
            
            # Check for resource concentration (over-dependence)
            if usage_percentage > 0.7:  # 70% of usage in one category
                bottlenecks.append({
                    'type': 'resource_concentration',
                    'category': category,
                    'severity': 'medium',
                    'concentration_percentage': usage_percentage,
                    'description': f"Over-concentration on {category} resources",
                    'metrics': metrics
                })
            
            # Check for cost inefficiency
            avg_cost_per_op = metrics.get('avg_cost_per_operation', 0)
            if avg_cost_per_op > 0.1:  # $0.10 per operation threshold
                bottlenecks.append({
                    'type': 'cost_inefficiency',
                    'category': category,
                    'severity': 'medium',
                    'avg_cost_per_operation': avg_cost_per_op,
                    'description': f"High cost per operation in {category}",
                    'metrics': metrics
                })
        
        # Sort by severity
        severity_order = {'critical': 3, 'high': 2, 'medium': 1, 'low': 0}
        bottlenecks.sort(key=lambda x: severity_order.get(x['severity'], 0), reverse=True)
        
        return bottlenecks
    
    @staticmethod
    def calculate_resource_efficiency_metrics(
        usage_records: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Calculate various resource efficiency metrics
        
        Args:
            usage_records: List of usage records
            
        Returns:
            Dictionary with efficiency metrics
        """
        metrics = {}
        
        if not usage_records:
            return {
                'overall_efficiency': 0.0,
                'token_efficiency': 0.0,
                'cost_efficiency': 0.0,
                'throughput_efficiency': 0.0,
                'success_rate': 0.0
            }
        
        total_records = len(usage_records)
        total_tokens = sum(record.get('tokens_used', 0) for record in usage_records)
        total_cost = sum(record.get('cost_usd', 0) for record in usage_records)
        
        # Success rate efficiency
        successful_records = len([
            r for r in usage_records 
            if r.get('response_data', {}).get('success', True)
        ])
        success_rate = successful_records / total_records
        
        # Token efficiency (successful tokens per total tokens)
        successful_tokens = sum(
            record.get('tokens_used', 0) for record in usage_records
            if record.get('response_data', {}).get('success', True)
        )
        token_efficiency = successful_tokens / total_tokens if total_tokens > 0 else 0
        
        # Cost efficiency (tokens per dollar)
        cost_efficiency = total_tokens / total_cost if total_cost > 0 else 1.0
        # Normalize to 0-1 scale (10,000 tokens per dollar = perfect efficiency)
        cost_efficiency = min(1.0, cost_efficiency / 10000)
        
        # Throughput efficiency (operations per time unit)
        time_span_hours = ResourceMonitoringUtils._calculate_time_span_hours(usage_records)
        throughput = total_records / time_span_hours if time_span_hours > 0 else 0
        # Normalize throughput (10 operations per hour = good efficiency)
        throughput_efficiency = min(1.0, throughput / 10)
        
        # Overall efficiency (weighted average)
        overall_efficiency = (
            success_rate * 0.3 +
            token_efficiency * 0.3 +
            cost_efficiency * 0.2 +
            throughput_efficiency * 0.2
        )
        
        metrics.update({
            'overall_efficiency': overall_efficiency,
            'token_efficiency': token_efficiency,
            'cost_efficiency': cost_efficiency,
            'throughput_efficiency': throughput_efficiency,
            'success_rate': success_rate,
            'tokens_per_operation': total_tokens / total_records,
            'cost_per_operation': total_cost / total_records,
            'operations_per_hour': throughput
        })
        
        return metrics
    
    @staticmethod
    def _calculate_time_span_hours(usage_records: List[Dict[str, Any]]) -> float:
        """Calculate time span of usage records in hours"""
        if not usage_records:
            return 0.0
        
        timestamps = []
        for record in usage_records:
            created_at = record.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    timestamps.append(dt)
                except:
                    continue
        
        if len(timestamps) < 2:
            return 1.0  # Default to 1 hour
        
        time_span = (max(timestamps) - min(timestamps)).total_seconds() / 3600
        return max(1.0, time_span)  # At least 1 hour
    
    @staticmethod
    def analyze_peak_usage_patterns(
        usage_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze peak usage patterns to identify resource demand spikes
        
        Args:
            usage_records: List of usage records
            
        Returns:
            Dictionary with peak usage analysis
        """
        patterns = {}
        
        if not usage_records:
            return patterns
        
        # Group by hour for peak hour analysis
        hourly_usage = defaultdict(lambda: {'count': 0, 'tokens': 0, 'cost': 0})
        daily_usage = defaultdict(lambda: {'count': 0, 'tokens': 0, 'cost': 0})
        
        for record in usage_records:
            created_at = record.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    
                    hour_key = dt.hour
                    day_key = dt.date()
                    
                    tokens = record.get('tokens_used', 0)
                    cost = record.get('cost_usd', 0)
                    
                    hourly_usage[hour_key]['count'] += 1
                    hourly_usage[hour_key]['tokens'] += tokens
                    hourly_usage[hour_key]['cost'] += cost
                    
                    daily_usage[day_key]['count'] += 1
                    daily_usage[day_key]['tokens'] += tokens  
                    daily_usage[day_key]['cost'] += cost
                    
                except:
                    continue
        
        # Identify peak hours
        if hourly_usage:
            peak_hour_by_count = max(hourly_usage, key=lambda h: hourly_usage[h]['count'])
            peak_hour_by_tokens = max(hourly_usage, key=lambda h: hourly_usage[h]['tokens'])
            
            avg_hourly_count = sum(h['count'] for h in hourly_usage.values()) / len(hourly_usage)
            avg_hourly_tokens = sum(h['tokens'] for h in hourly_usage.values()) / len(hourly_usage)
            
            patterns['hourly_patterns'] = {
                'peak_hour_by_count': peak_hour_by_count,
                'peak_hour_by_tokens': peak_hour_by_tokens,
                'peak_count': hourly_usage[peak_hour_by_count]['count'],
                'peak_tokens': hourly_usage[peak_hour_by_tokens]['tokens'],
                'avg_hourly_count': avg_hourly_count,
                'avg_hourly_tokens': avg_hourly_tokens,
                'peak_to_avg_ratio': hourly_usage[peak_hour_by_tokens]['tokens'] / avg_hourly_tokens if avg_hourly_tokens > 0 else 1.0
            }
        
        # Identify peak days
        if daily_usage:
            peak_day_by_tokens = max(daily_usage, key=lambda d: daily_usage[d]['tokens'])
            avg_daily_tokens = sum(d['tokens'] for d in daily_usage.values()) / len(daily_usage)
            
            patterns['daily_patterns'] = {
                'peak_day': str(peak_day_by_tokens),
                'peak_day_tokens': daily_usage[peak_day_by_tokens]['tokens'],
                'avg_daily_tokens': avg_daily_tokens,
                'peak_to_avg_ratio': daily_usage[peak_day_by_tokens]['tokens'] / avg_daily_tokens if avg_daily_tokens > 0 else 1.0
            }
        
        # Calculate usage volatility
        if len(daily_usage) > 1:
            daily_token_values = [d['tokens'] for d in daily_usage.values()]
            daily_mean = statistics.mean(daily_token_values)
            daily_stdev = statistics.stdev(daily_token_values)
            
            patterns['volatility'] = {
                'coefficient_of_variation': daily_stdev / daily_mean if daily_mean > 0 else 0,
                'volatility_level': ResourceMonitoringUtils._classify_volatility(daily_stdev / daily_mean if daily_mean > 0 else 0)
            }
        
        return patterns
    
    @staticmethod
    def _classify_volatility(coefficient_of_variation: float) -> str:
        """Classify volatility level based on coefficient of variation"""
        if coefficient_of_variation < 0.2:
            return "low"
        elif coefficient_of_variation < 0.5:
            return "moderate"
        elif coefficient_of_variation < 1.0:
            return "high"
        else:
            return "very_high"
    
    @staticmethod
    def calculate_resource_trends(
        usage_records: List[Dict[str, Any]],
        window_days: int = 7
    ) -> Dict[str, Any]:
        """
        Calculate resource usage trends over time
        
        Args:
            usage_records: List of usage records
            window_days: Window size for trend calculation
            
        Returns:
            Dictionary with trend analysis
        """
        trends = {}
        
        if not usage_records:
            return trends
        
        # Group records by time windows
        windows = ResourceMonitoringUtils._create_time_windows(usage_records, window_days)
        
        if len(windows) < 2:
            return {
                'trend_direction': 'insufficient_data',
                'trend_strength': 0.0,
                'windows_analyzed': len(windows)
            }
        
        # Calculate metrics for each window
        window_metrics = []
        for window_records in windows:
            if window_records:
                window_tokens = sum(r.get('tokens_used', 0) for r in window_records)
                window_cost = sum(r.get('cost_usd', 0) for r in window_records)
                window_count = len(window_records)
                
                window_metrics.append({
                    'tokens': window_tokens,
                    'cost': window_cost,
                    'count': window_count,
                    'avg_tokens_per_operation': window_tokens / window_count if window_count > 0 else 0
                })
        
        # Calculate trends
        if len(window_metrics) >= 2:
            # Token usage trend
            token_values = [w['tokens'] for w in window_metrics]
            token_trend = ResourceMonitoringUtils._calculate_linear_trend(token_values)
            
            # Cost trend
            cost_values = [w['cost'] for w in window_metrics]
            cost_trend = ResourceMonitoringUtils._calculate_linear_trend(cost_values)
            
            # Operation count trend
            count_values = [w['count'] for w in window_metrics]
            count_trend = ResourceMonitoringUtils._calculate_linear_trend(count_values)
            
            trends.update({
                'token_usage_trend': token_trend,
                'cost_trend': cost_trend,
                'operation_count_trend': count_trend,
                'overall_trend': ResourceMonitoringUtils._determine_overall_trend(token_trend, cost_trend, count_trend),
                'windows_analyzed': len(window_metrics)
            })
        
        return trends
    
    @staticmethod
    def _create_time_windows(
        usage_records: List[Dict[str, Any]], 
        window_days: int
    ) -> List[List[Dict[str, Any]]]:
        """Create time-based windows of records"""
        if not usage_records:
            return []
        
        # Sort records by timestamp
        sorted_records = sorted(usage_records, key=lambda r: r.get('created_at', ''))
        
        windows = []
        current_window = []
        window_start = None
        
        for record in sorted_records:
            created_at = record.get('created_at')
            if not created_at:
                continue
            
            try:
                if isinstance(created_at, str):
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    dt = created_at
                
                if window_start is None:
                    window_start = dt
                    current_window = [record]
                elif (dt - window_start).days < window_days:
                    current_window.append(record)
                else:
                    # Start new window
                    if current_window:
                        windows.append(current_window)
                    current_window = [record]
                    window_start = dt
            except:
                continue
        
        # Add final window
        if current_window:
            windows.append(current_window)
        
        return windows
    
    @staticmethod
    def _calculate_linear_trend(values: List[float]) -> Dict[str, Any]:
        """Calculate linear trend from a series of values"""
        if len(values) < 2:
            return {'direction': 'insufficient_data', 'strength': 0.0, 'slope': 0.0}
        
        n = len(values)
        x_values = list(range(n))
        
        # Calculate linear regression
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Determine trend direction and strength
        if abs(slope) < 0.1:
            direction = 'stable'
            strength = 0.0
        elif slope > 0:
            direction = 'increasing'
            strength = min(1.0, abs(slope) / max(values) if max(values) > 0 else 0)
        else:
            direction = 'decreasing'
            strength = min(1.0, abs(slope) / max(values) if max(values) > 0 else 0)
        
        return {
            'direction': direction,
            'strength': strength,
            'slope': slope
        }
    
    @staticmethod
    def _determine_overall_trend(
        token_trend: Dict[str, Any],
        cost_trend: Dict[str, Any], 
        count_trend: Dict[str, Any]
    ) -> str:
        """Determine overall trend from individual metric trends"""
        trends = [
            token_trend.get('direction', 'stable'),
            cost_trend.get('direction', 'stable'),
            count_trend.get('direction', 'stable')
        ]
        
        increasing_count = trends.count('increasing')
        decreasing_count = trends.count('decreasing')
        
        if increasing_count >= 2:
            return 'increasing'
        elif decreasing_count >= 2:
            return 'decreasing'
        else:
            return 'stable'
    
    @staticmethod
    def generate_resource_recommendations(
        utilization_data: Dict[str, Any],
        efficiency_metrics: Dict[str, float],
        bottlenecks: List[Dict[str, Any]],
        peak_patterns: Dict[str, Any]
    ) -> List[str]:
        """
        Generate actionable resource optimization recommendations
        
        Args:
            utilization_data: Resource utilization analysis
            efficiency_metrics: Efficiency calculations
            bottlenecks: Identified bottlenecks
            peak_patterns: Peak usage analysis
            
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        
        # Efficiency-based recommendations
        overall_efficiency = efficiency_metrics.get('overall_efficiency', 0.5)
        if overall_efficiency < 0.4:
            recommendations.append("Overall resource efficiency is low - review usage patterns")
        
        token_efficiency = efficiency_metrics.get('token_efficiency', 0.5)
        if token_efficiency < 0.6:
            recommendations.append("Optimize token usage - many tokens used in failed operations")
        
        cost_efficiency = efficiency_metrics.get('cost_efficiency', 0.5)
        if cost_efficiency < 0.3:
            recommendations.append("High cost per token - consider usage optimization or plan upgrade")
        
        # Bottleneck-based recommendations
        critical_bottlenecks = [b for b in bottlenecks if b.get('severity') == 'critical']
        if critical_bottlenecks:
            for bottleneck in critical_bottlenecks[:2]:  # Top 2 critical
                category = bottleneck.get('category', 'unknown')
                recommendations.append(f"Address critical bottleneck in {category} resources")
        
        # Peak usage recommendations
        peak_patterns_hourly = peak_patterns.get('hourly_patterns', {})
        if peak_patterns_hourly:
            peak_ratio = peak_patterns_hourly.get('peak_to_avg_ratio', 1.0)
            if peak_ratio > 3.0:
                recommendations.append("High peak-to-average ratio - consider load balancing")
        
        volatility = peak_patterns.get('volatility', {})
        if volatility.get('volatility_level') == 'very_high':
            recommendations.append("Very high usage volatility - implement resource buffers")
        
        # Utilization-based recommendations
        for category, metrics in utilization_data.items():
            utilization_intensity = metrics.get('utilization_intensity', 0)
            usage_percentage = metrics.get('usage_percentage', 0)
            
            if utilization_intensity > 0.9:
                recommendations.append(f"Very high {category} utilization - scale resources")
            elif usage_percentage > 80:
                recommendations.append(f"Over-dependence on {category} - diversify resource usage")
        
        # Cost-based recommendations
        for category, metrics in utilization_data.items():
            avg_cost = metrics.get('avg_cost_per_operation', 0)
            if avg_cost > 0.15:  # $0.15 per operation
                recommendations.append(f"High cost per {category} operation - optimize or batch requests")
        
        return recommendations[:8]  # Limit to top 8 recommendations