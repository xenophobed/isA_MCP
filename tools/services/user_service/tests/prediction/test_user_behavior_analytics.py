"""
Test Suite for User Behavior Analytics Service

Tests the complete Suite 1 functionality with real data patterns
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from services.prediction.user_behavior_analytics.user_behavior_analytics_service import (
    UserBehaviorAnalyticsService
)
from services.prediction.prediction_models import (
    TemporalPattern,
    UserBehaviorPattern, 
    UserNeedsPrediction,
    PredictionConfidenceLevel
)


class TestUserBehaviorAnalyticsService:
    """Test suite for user behavior analytics service"""
    
    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        return UserBehaviorAnalyticsService()
    
    @pytest.fixture
    def mock_usage_data(self):
        """Mock usage data for testing"""
        base_time = datetime.utcnow() - timedelta(days=30)
        
        return [
            {
                "id": i,
                "user_id": "test_user_123",
                "endpoint": "/api/chat" if i % 3 == 0 else "/api/memory",
                "event_type": "api_call",
                "tokens_used": 100 + (i * 10),
                "cost_usd": 0.01 + (i * 0.001),
                "tool_name": "chat_tool" if i % 2 == 0 else "memory_tool",
                "provider": "openai",
                "created_at": (base_time + timedelta(hours=i * 2)).isoformat(),
                "response_data": {"success": True}
            }
            for i in range(20)
        ]
    
    @pytest.fixture
    def mock_session_data(self):
        """Mock session data for testing"""
        base_time = datetime.utcnow() - timedelta(days=30)
        
        return [
            {
                "id": i,
                "session_id": f"session_{i}",
                "user_id": "test_user_123",
                "status": "active",
                "message_count": i + 5,
                "total_tokens": (i + 1) * 150,
                "total_cost": (i + 1) * 0.05,
                "created_at": (base_time + timedelta(days=i * 2)).isoformat(),
                "last_activity": (base_time + timedelta(days=i * 2, hours=2)).isoformat()
            }
            for i in range(10)
        ]
    
    @pytest.mark.asyncio
    async def test_analyze_temporal_patterns_success(self, service, mock_usage_data, mock_session_data):
        """Test successful temporal pattern analysis"""
        
        # Mock repository calls
        with patch.object(service.temporal_analyzer.usage_repo, 'get_user_usage_history', 
                         new_callable=AsyncMock) as mock_usage, \
             patch.object(service.temporal_analyzer.session_repo, 'get_user_sessions', 
                         new_callable=AsyncMock) as mock_sessions:
            
            mock_usage.return_value = mock_usage_data
            mock_sessions.return_value = mock_session_data
            
            # Test temporal pattern analysis
            result = await service.analyze_temporal_patterns("test_user_123", "30d")
            
            # Assertions
            assert isinstance(result, TemporalPattern)
            assert result.user_id == "test_user_123"
            assert result.data_period == "30d"
            assert result.sample_size == len(mock_usage_data)
            assert isinstance(result.confidence, float)
            assert 0.0 <= result.confidence <= 1.0
            assert isinstance(result.confidence_level, PredictionConfidenceLevel)
            
            # Check that patterns are extracted
            assert isinstance(result.time_periods, dict)
            assert isinstance(result.peak_hours, list)
            assert isinstance(result.session_frequency, dict)
            assert isinstance(result.cyclical_patterns, dict)
            
            # Verify repository calls
            mock_usage.assert_called_once()
            mock_sessions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_temporal_patterns_empty_data(self, service):
        """Test temporal pattern analysis with empty data"""
        
        with patch.object(service.temporal_analyzer.usage_repo, 'get_user_usage_history', 
                         new_callable=AsyncMock) as mock_usage, \
             patch.object(service.temporal_analyzer.session_repo, 'get_user_sessions', 
                         new_callable=AsyncMock) as mock_sessions:
            
            mock_usage.return_value = []
            mock_sessions.return_value = []
            
            result = await service.analyze_temporal_patterns("test_user_123", "30d")
            
            # Should return low confidence pattern
            assert result.confidence < 0.3
            assert result.confidence_level == PredictionConfidenceLevel.LOW
            assert result.sample_size == 0
    
    @pytest.mark.asyncio
    async def test_analyze_user_patterns_success(self, service, mock_usage_data):
        """Test successful user pattern analysis"""
        
        with patch.object(service.user_pattern_analyzer, 'analyze_patterns', 
                         new_callable=AsyncMock) as mock_analyze:
            
            expected_pattern = UserBehaviorPattern(
                user_id="test_user_123",
                confidence=0.8,
                confidence_level=PredictionConfidenceLevel.VERY_HIGH,
                task_preferences=["chat", "memory_search"],
                tool_preferences=["chat_tool", "memory_tool"],
                interaction_style={"verbose": True, "technical": True},
                success_patterns={"chat": 0.95, "memory": 0.90},
                failure_patterns=[]
            )
            
            mock_analyze.return_value = expected_pattern
            
            result = await service.analyze_user_patterns("test_user_123", {"recent": True})
            
            assert isinstance(result, UserBehaviorPattern)
            assert result.user_id == "test_user_123"
            assert result.confidence == 0.8
            assert result.task_preferences == ["chat", "memory_search"]
            
            mock_analyze.assert_called_once_with("test_user_123", {"recent": True})
    
    @pytest.mark.asyncio
    async def test_predict_user_needs_success(self, service):
        """Test successful user needs prediction"""
        
        with patch.object(service.user_needs_predictor, 'predict_needs', 
                         new_callable=AsyncMock) as mock_predict:
            
            expected_prediction = UserNeedsPrediction(
                user_id="test_user_123",
                confidence=0.75,
                confidence_level=PredictionConfidenceLevel.HIGH,
                anticipated_tasks=["document_analysis", "data_query"],
                required_tools=["text_analyzer", "query_tool"],
                context_needs={"session_id": "current_session"},
                based_on_patterns=["pattern_1", "pattern_2"]
            )
            
            mock_predict.return_value = expected_prediction
            
            context = {"session_id": "current_session", "query": "analyze document"}
            result = await service.predict_user_needs("test_user_123", context, "analyze document")
            
            assert isinstance(result, UserNeedsPrediction)
            assert result.user_id == "test_user_123"
            assert result.anticipated_tasks == ["document_analysis", "data_query"]
            assert result.required_tools == ["text_analyzer", "query_tool"]
            
            mock_predict.assert_called_once_with("test_user_123", context, "analyze document")
    
    @pytest.mark.asyncio 
    async def test_comprehensive_analysis(self, service, mock_usage_data, mock_session_data):
        """Test comprehensive analysis combining all sub-services"""
        
        # Mock all sub-service methods
        temporal_pattern = TemporalPattern(
            user_id="test_user_123",
            confidence=0.7,
            confidence_level=PredictionConfidenceLevel.HIGH,
            time_periods={"morning": 0.6, "afternoon": 0.4},
            peak_hours=[9, 10, 14],
            session_frequency={"daily_average": 2.5},
            cyclical_patterns={},
            data_period="30d",
            sample_size=20
        )
        
        user_pattern = UserBehaviorPattern(
            user_id="test_user_123", 
            confidence=0.8,
            confidence_level=PredictionConfidenceLevel.VERY_HIGH,
            task_preferences=["chat"],
            tool_preferences=["chat_tool"],
            interaction_style={},
            success_patterns={},
            failure_patterns=[]
        )
        
        user_needs = UserNeedsPrediction(
            user_id="test_user_123",
            confidence=0.6,
            confidence_level=PredictionConfidenceLevel.MEDIUM,
            anticipated_tasks=["analysis"],
            required_tools=["analyzer"],
            context_needs={},
            based_on_patterns=[]
        )
        
        with patch.object(service, 'analyze_temporal_patterns', 
                         new_callable=AsyncMock) as mock_temporal, \
             patch.object(service, 'analyze_user_patterns', 
                         new_callable=AsyncMock) as mock_patterns, \
             patch.object(service, 'predict_user_needs', 
                         new_callable=AsyncMock) as mock_needs:
            
            mock_temporal.return_value = temporal_pattern
            mock_patterns.return_value = user_pattern  
            mock_needs.return_value = user_needs
            
            result = await service.get_comprehensive_analysis("test_user_123", {"test": True})
            
            # Check result structure
            assert result["user_id"] == "test_user_123"
            assert "temporal_patterns" in result
            assert "user_patterns" in result
            assert "user_needs" in result
            assert "overall_confidence" in result
            assert "analysis_timestamp" in result
            
            # Check overall confidence calculation
            expected_confidence = (0.7 + 0.8 + 0.6) / 3
            assert abs(result["overall_confidence"] - expected_confidence) < 0.01
            
            # Verify all methods were called
            mock_temporal.assert_called_once()
            mock_patterns.assert_called_once()
            mock_needs.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_service_health_check(self, service):
        """Test service health check"""
        
        # Mock sub-service health checks
        with patch.object(service.temporal_analyzer, 'health_check', 
                         new_callable=AsyncMock) as mock_temporal_health, \
             patch.object(service.user_pattern_analyzer, 'health_check', 
                         new_callable=AsyncMock) as mock_pattern_health, \
             patch.object(service.user_needs_predictor, 'health_check', 
                         new_callable=AsyncMock) as mock_needs_health:
            
            mock_temporal_health.return_value = {"status": "healthy"}
            mock_pattern_health.return_value = {"status": "healthy"}
            mock_needs_health.return_value = {"status": "healthy"}
            
            result = await service.get_service_health()
            
            assert result["service"] == "user_behavior_analytics"
            assert result["status"] == "healthy"
            assert "sub_services" in result
            assert "last_check" in result
            
            # Check sub-service health
            sub_services = result["sub_services"]
            assert sub_services["temporal_analyzer"]["status"] == "healthy"
            assert sub_services["user_pattern_analyzer"]["status"] == "healthy"
            assert sub_services["user_needs_predictor"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, service):
        """Test error handling in service methods"""
        
        # Test temporal patterns error handling
        with patch.object(service.temporal_analyzer, 'analyze_patterns', 
                         side_effect=Exception("Database error")):
            
            result = await service.analyze_temporal_patterns("test_user_123", "30d")
            
            # Should return low confidence pattern with error info
            assert result.confidence == 0.1
            assert result.confidence_level == PredictionConfidenceLevel.LOW
            assert "error" in result.metadata
        
        # Test comprehensive analysis error handling
        with patch.object(service, 'analyze_temporal_patterns', side_effect=Exception("Error")):
            
            result = await service.get_comprehensive_analysis("test_user_123")
            
            assert "error" in result
            assert result["overall_confidence"] == 0.0


# Integration test with real data patterns
class TestUserBehaviorAnalyticsIntegration:
    """Integration tests with realistic data scenarios"""
    
    @pytest.mark.asyncio
    async def test_realistic_temporal_analysis(self):
        """Test with realistic temporal usage patterns"""
        service = UserBehaviorAnalyticsService()
        
        # Create realistic usage pattern (work hours, weekdays)
        mock_data = []
        base_time = datetime.utcnow() - timedelta(days=30)
        
        for day in range(30):
            current_day = base_time + timedelta(days=day)
            
            # Skip weekends for this user
            if current_day.weekday() >= 5:
                continue
            
            # Add usage during work hours (9 AM - 5 PM)
            for hour in [9, 10, 14, 16]:
                mock_data.append({
                    "id": len(mock_data),
                    "user_id": "professional_user",
                    "endpoint": "/api/chat",
                    "created_at": current_day.replace(hour=hour).isoformat(),
                    "tokens_used": 150,
                    "cost_usd": 0.02
                })
        
        with patch.object(service.temporal_analyzer.usage_repo, 'get_user_usage_history',
                         new_callable=AsyncMock, return_value=mock_data), \
             patch.object(service.temporal_analyzer.session_repo, 'get_user_sessions',
                         new_callable=AsyncMock, return_value=[]):
            
            result = await service.analyze_temporal_patterns("professional_user", "30d")
            
            # Should detect weekday preference
            assert result.time_periods["weekday"] > result.time_periods["weekend"]
            
            # Should detect work hours as peak times
            work_hours = [9, 10, 14, 16]
            detected_peaks = set(result.peak_hours)
            work_hour_overlap = len(detected_peaks.intersection(work_hours))
            
            # Should detect at least half of the work hours as peaks
            assert work_hour_overlap >= 2
            
            # Should have reasonable confidence
            assert result.confidence > 0.5


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])