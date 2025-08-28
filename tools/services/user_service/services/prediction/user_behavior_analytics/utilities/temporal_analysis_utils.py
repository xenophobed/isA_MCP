"""
Temporal Analysis Utilities

Common utilities for time-based analysis and pattern detection
"""

from typing import Tuple, Dict, Any, List
from datetime import datetime, timedelta
import re


class TemporalAnalysisUtils:
    """Utilities for temporal analysis and time parsing"""
    
    @staticmethod
    def parse_timeframe(timeframe: str) -> Tuple[datetime, datetime]:
        """
        Parse timeframe string into start and end dates
        
        Args:
            timeframe: Time period (e.g., "30d", "7d", "1d", "24h")
            
        Returns:
            Tuple of (start_date, end_date)
        """
        now = datetime.utcnow()
        
        # Parse different timeframe formats
        if timeframe.endswith('d'):
            days = int(timeframe[:-1])
            start_date = now - timedelta(days=days)
        elif timeframe.endswith('h'):
            hours = int(timeframe[:-1])
            start_date = now - timedelta(hours=hours)
        elif timeframe.endswith('w'):
            weeks = int(timeframe[:-1])
            start_date = now - timedelta(weeks=weeks)
        elif timeframe.endswith('m'):
            months = int(timeframe[:-1])
            start_date = now - timedelta(days=months * 30)  # Approximate
        else:
            # Default to 30 days if format not recognized
            start_date = now - timedelta(days=30)
        
        return start_date, now
    
    @staticmethod
    def categorize_time_period(dt: datetime) -> str:
        """
        Categorize datetime into time period
        
        Args:
            dt: Datetime to categorize
            
        Returns:
            Time period category
        """
        hour = dt.hour
        
        if 0 <= hour < 6:
            return "early_morning"
        elif 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        else:
            return "evening"
    
    @staticmethod
    def is_weekend(dt: datetime) -> bool:
        """Check if datetime falls on weekend"""
        return dt.weekday() >= 5  # Saturday = 5, Sunday = 6
    
    @staticmethod
    def get_week_of_month(dt: datetime) -> int:
        """Get week number within the month (1-5)"""
        first_day = dt.replace(day=1)
        first_week_day = first_day.weekday()
        day_of_month = dt.day
        
        return (day_of_month + first_week_day - 1) // 7 + 1
    
    @staticmethod
    def calculate_time_consistency(timestamps: List[datetime]) -> float:
        """
        Calculate consistency of timing patterns
        
        Args:
            timestamps: List of timestamps to analyze
            
        Returns:
            Consistency score (0.0 to 1.0, higher = more consistent)
        """
        if len(timestamps) < 2:
            return 0.0
        
        # Extract hours from timestamps
        hours = [dt.hour + dt.minute/60.0 for dt in timestamps]
        
        # Calculate standard deviation
        mean_hour = sum(hours) / len(hours)
        variance = sum((h - mean_hour) ** 2 for h in hours) / len(hours)
        std_dev = variance ** 0.5
        
        # Normalize by 12 hours (half day) and invert
        consistency = 1.0 - min(std_dev / 12.0, 1.0)
        
        return max(0.0, consistency)
    
    @staticmethod
    def detect_cyclical_pattern(
        timestamps: List[datetime], 
        cycle_type: str = "weekly"
    ) -> Dict[str, float]:
        """
        Detect cyclical patterns in timestamps
        
        Args:
            timestamps: List of timestamps
            cycle_type: Type of cycle ("weekly", "monthly", "daily")
            
        Returns:
            Dictionary with pattern strength and characteristics
        """
        if not timestamps:
            return {"pattern_strength": 0.0}
        
        if cycle_type == "weekly":
            # Group by day of week
            dow_counts = {}
            for ts in timestamps:
                dow = ts.strftime('%A')
                dow_counts[dow] = dow_counts.get(dow, 0) + 1
            
            # Calculate pattern strength (how uneven the distribution is)
            total = sum(dow_counts.values())
            if total == 0:
                return {"pattern_strength": 0.0}
            
            # Calculate entropy as a measure of pattern strength
            probs = [count/total for count in dow_counts.values()]
            entropy = -sum(p * (p.bit_length() - 1) for p in probs if p > 0)
            max_entropy = len(dow_counts).bit_length() - 1 if dow_counts else 1
            
            pattern_strength = 1.0 - (entropy / max_entropy if max_entropy > 0 else 0)
            
            return {
                "pattern_strength": pattern_strength,
                "distribution": dow_counts,
                "most_active_day": max(dow_counts, key=dow_counts.get) if dow_counts else None
            }
        
        elif cycle_type == "monthly":
            # Group by day of month
            dom_counts = {}
            for ts in timestamps:
                dom = ts.day
                dom_counts[dom] = dom_counts.get(dom, 0) + 1
            
            total = sum(dom_counts.values())
            if total == 0:
                return {"pattern_strength": 0.0}
            
            # Simple variance-based pattern detection
            values = list(dom_counts.values())
            mean_val = sum(values) / len(values)
            variance = sum((v - mean_val) ** 2 for v in values) / len(values)
            
            # Normalize pattern strength
            pattern_strength = min(variance / (mean_val ** 2), 1.0) if mean_val > 0 else 0.0
            
            return {
                "pattern_strength": pattern_strength,
                "distribution": dom_counts,
                "peak_days": [day for day, count in dom_counts.items() 
                             if count > mean_val * 1.5]
            }
        
        return {"pattern_strength": 0.0}
    
    @staticmethod
    def normalize_timestamp_to_utc(timestamp_str: str) -> datetime:
        """
        Normalize various timestamp formats to UTC datetime
        
        Args:
            timestamp_str: Timestamp string in various formats
            
        Returns:
            UTC datetime object
        """
        # Handle ISO format with Z
        if timestamp_str.endswith('Z'):
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        
        # Handle ISO format with timezone
        if '+' in timestamp_str or timestamp_str.endswith('+00:00'):
            return datetime.fromisoformat(timestamp_str)
        
        # Assume UTC if no timezone info
        try:
            dt = datetime.fromisoformat(timestamp_str)
            return dt.replace(tzinfo=None)  # Remove timezone info, assume UTC
        except ValueError:
            # Fallback to current time if parsing fails
            return datetime.utcnow()