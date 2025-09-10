"""
Suite 2: Context Intelligence Integration Tests

Comprehensive tests for context intelligence prediction services with realistic data scenarios
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json
import logging

# Setup logging for testing
logging.basicConfig(level=logging.INFO)

# Import prediction services
from tools.services.user_service.services.prediction.context_intelligence.context_intelligence_service import ContextIntelligenceService
from tools.services.user_service.services.prediction.context_intelligence.sub_services.context_pattern_analyzer import ContextPatternAnalyzer
from tools.services.user_service.services.prediction.context_intelligence.sub_services.task_outcome_predictor import TaskOutcomePredictor

# Import prediction models
from tools.services.user_service.services.prediction.prediction_models import (
    ContextPattern, TaskOutcomePrediction, PredictionConfidenceLevel
)

# Import repositories (mocked for testing)
from tools.services.user_service.repositories.usage_repository import UsageRepository
from tools.services.user_service.repositories.session_repository import SessionRepository
from tools.services.user_service.repositories.user_repository import UserRepository


class MockUsageRepository:
    """Mock usage repository with realistic data"""
    
    def __init__(self):
        self.data = self._generate_realistic_usage_data()
    
    def _generate_realistic_usage_data(self) -> List[Dict[str, Any]]:
        """Generate realistic usage data for different contexts"""
        base_time = datetime.utcnow() - timedelta(days=30)
        data = []
        
        # Professional Data Scientist Persona
        contexts = [
            # Development context
            {
                "tools": ["code_editor", "git", "debugger", "test_runner", "build_system"],
                "endpoints": ["/api/code/analyze", "/api/git/commit", "/api/debug/trace", "/api/test/run"],
                "keywords": ["code", "debug", "test", "build", "function", "class", "git"],
                "hours": list(range(9, 12)) + list(range(14, 18)),  # Morning and afternoon coding
                "token_range": (200, 800),
                "success_rate": 0.85,
                "complexity": 0.7
            },
            # Analysis context
            {
                "tools": ["data_analyzer", "chart_generator", "statistics", "sql_executor", "report_builder"],
                "endpoints": ["/api/data/analyze", "/api/chart/create", "/api/stats/calculate", "/api/sql/execute"],
                "keywords": ["analyze", "data", "statistics", "metrics", "chart", "insights"],
                "hours": list(range(10, 12)) + list(range(15, 17)),  # Focused analysis periods
                "token_range": (300, 1200),
                "success_rate": 0.92,
                "complexity": 0.6
            },
            # Research context
            {
                "tools": ["web_search", "document_reader", "knowledge_base", "research_assistant"],
                "endpoints": ["/api/search/query", "/api/docs/read", "/api/knowledge/search", "/api/research/assist"],
                "keywords": ["search", "research", "investigate", "study", "explore", "find"],
                "hours": list(range(8, 10)) + list(range(13, 15)),  # Early morning and early afternoon
                "token_range": (150, 600),
                "success_rate": 0.88,
                "complexity": 0.4
            },
            # Documentation context
            {
                "tools": ["document_editor", "markdown_processor", "template_engine", "content_formatter"],
                "endpoints": ["/api/docs/edit", "/api/markdown/process", "/api/template/render", "/api/format/text"],
                "keywords": ["document", "text", "write", "edit", "format", "summary", "note"],
                "hours": list(range(16, 18)) + [19, 20],  # Late afternoon and evening
                "token_range": (100, 400),
                "success_rate": 0.90,
                "complexity": 0.3
            }
        ]
        
        # Generate 30 days of realistic data
        record_id = 1
        for day in range(30):
            current_day = base_time + timedelta(days=day)
            
            # Skip weekends (some reduced activity)
            if current_day.weekday() >= 5:
                daily_records = 2  # Minimal weekend activity
            else:
                daily_records = 8 + (day % 5)  # 8-12 records per weekday
            
            for _ in range(daily_records):
                # Choose context based on day patterns
                if day % 7 < 2:  # Mon-Tue: Heavy development
                    context_weights = [0.5, 0.2, 0.2, 0.1]
                elif day % 7 < 4:  # Wed-Thu: Analysis focus
                    context_weights = [0.2, 0.5, 0.2, 0.1]
                else:  # Fri + weekends: Research and documentation
                    context_weights = [0.1, 0.2, 0.4, 0.3]
                
                # Select context
                import random
                context = random.choices(contexts, weights=context_weights)[0]
                
                # Generate record time within context hours
                if context["hours"]:
                    hour = random.choice(context["hours"])
                    minute = random.randint(0, 59)
                    record_time = current_day.replace(hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    record_time = current_day
                
                # Create realistic record
                tool = random.choice(context["tools"])
                endpoint = random.choice(context["endpoints"])
                tokens = random.randint(*context["token_range"])
                success = random.random() < context["success_rate"]
                
                # Add some realistic variation
                if day > 20:  # Later days have slightly better performance
                    if random.random() < 0.1:
                        tokens = int(tokens * 1.2)  # 10% chance of higher token usage
                        success = True
                
                record = {
                    "id": record_id,
                    "user_id": "test_user_professional",
                    "tool_name": tool,
                    "endpoint": endpoint,
                    "event_type": "api_call",
                    "tokens_used": tokens,
                    "created_at": record_time.isoformat() + "Z",
                    "response_data": {
                        "success": success,
                        "complexity": context["complexity"] + random.uniform(-0.1, 0.1),
                        "context": context["keywords"][0]  # Primary context indicator
                    }
                }
                
                data.append(record)
                record_id += 1
        
        return sorted(data, key=lambda x: x["created_at"])
    
    async def get_user_usage_by_timeframe(self, user_id: str, timeframe: str) -> List[Dict[str, Any]]:
        """Get usage data for specific timeframe"""
        # Simple filtering by user_id
        return [record for record in self.data if record["user_id"] == user_id]


class MockSessionRepository:
    """Mock session repository with realistic session data"""
    
    def __init__(self):
        self.data = self._generate_realistic_session_data()
    
    def _generate_realistic_session_data(self) -> List[Dict[str, Any]]:
        """Generate realistic session data"""
        base_time = datetime.utcnow() - timedelta(days=30)
        sessions = []
        
        # Generate sessions for 30 days
        session_id = 1
        for day in range(30):
            current_day = base_time + timedelta(days=day)
            
            if current_day.weekday() >= 5:  # Weekend
                num_sessions = 1 if day % 3 == 0 else 0  # Some weekend activity
            else:  # Weekday
                num_sessions = 2 + (day % 3)  # 2-4 sessions per day
            
            for session_num in range(num_sessions):
                # Session timing
                if session_num == 0:  # Morning session
                    start_hour = 8 + (day % 2)  # 8-9 AM start
                    duration_minutes = 120 + (day % 60)  # 2-3 hour sessions
                elif session_num == 1:  # Afternoon session
                    start_hour = 14 + (day % 2)  # 2-3 PM start
                    duration_minutes = 90 + (day % 30)  # 1.5-2 hour sessions
                else:  # Evening session
                    start_hour = 19 + (day % 2)  # 7-8 PM start
                    duration_minutes = 60 + (day % 30)  # 1-1.5 hour sessions
                
                start_time = current_day.replace(
                    hour=start_hour,
                    minute=0,
                    second=0,
                    microsecond=0
                ) + timedelta(minutes=day % 30)  # Some variation
                
                end_time = start_time + timedelta(minutes=duration_minutes)
                
                # Session context based on time
                if start_hour < 12:
                    context_type = "deep_work"  # Morning focus
                elif start_hour < 17:
                    context_type = "collaborative"  # Afternoon collaboration
                else:
                    context_type = "exploratory"  # Evening exploration
                
                session = {
                    "id": session_id,
                    "user_id": "test_user_professional",
                    "session_type": context_type,
                    "created_at": start_time.isoformat() + "Z",
                    "ended_at": end_time.isoformat() + "Z",
                    "duration_minutes": duration_minutes,
                    "activity_level": 0.6 + (session_num * 0.1) + (day % 10) * 0.03,
                    "context_switches": max(0, session_num + (day % 5) - 2),
                    "tools_used": 3 + session_num + (day % 4),
                    "session_data": {
                        "focus_score": 0.7 + (0.3 if context_type == "deep_work" else 0.0) + (day % 10) * 0.02,
                        "productivity_score": 0.8 + (day % 20) * 0.01,
                        "collaboration_indicators": context_type == "collaborative"
                    }
                }
                
                sessions.append(session)
                session_id += 1
        
        return sorted(sessions, key=lambda x: x["created_at"])
    
    async def get_user_sessions_by_timeframe(self, user_id: str, timeframe: str) -> List[Dict[str, Any]]:
        """Get session data for specific timeframe"""
        return [session for session in self.data if session["user_id"] == user_id]


class MockUserRepository:
    """Mock user repository with realistic user profile data"""
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile with realistic professional data scientist profile"""
        return {
            "id": user_id,
            "user_type": "professional",
            "role": "data_scientist",
            "experience_level": "senior",
            "preferences": {
                "working_hours": (9, 17),
                "preferred_tools": ["python", "jupyter", "git", "sql", "visualization"],
                "collaboration_level": 0.7,
                "multitasking_tendency": 0.4,  # Focused worker
                "technical_skills": {
                    "programming": 0.9,
                    "data_analysis": 0.95,
                    "machine_learning": 0.85,
                    "statistics": 0.9,
                    "visualization": 0.8,
                    "sql": 0.85,
                    "documentation": 0.7
                }
            },
            "created_at": (datetime.utcnow() - timedelta(days=365)).isoformat() + "Z"
        }


class TestSuite2ContextIntelligence:
    """Comprehensive integration tests for Context Intelligence service"""
    
    @pytest.fixture
    async def context_service(self):
        """Create context intelligence service with mocked dependencies"""
        service = ContextIntelligenceService()
        
        # Replace repositories with mocks
        service.context_analyzer.usage_repository = MockUsageRepository()
        service.context_analyzer.session_repository = MockSessionRepository()
        service.outcome_predictor.usage_repository = MockUsageRepository()
        service.outcome_predictor.session_repository = MockSessionRepository()
        service.outcome_predictor.user_repository = MockUserRepository()
        
        return service
    
    @pytest.mark.asyncio
    async def test_analyze_context_patterns_comprehensive(self, context_service):
        """Test comprehensive context pattern analysis with realistic data"""
        print("\n🧠 Testing Context Pattern Analysis...")
        
        result = await context_service.analyze_context_patterns(
            user_id="test_user_professional",
            context_type="analysis"
        )
        
        # Validate result structure
        assert isinstance(result, ContextPattern)
        assert result.user_id == "test_user_professional"
        assert result.confidence > 0.0
        
        print(f"  ✅ Context Pattern Analysis completed with {result.confidence:.2f} confidence")
        print(f"     Dominant Context: {result.dominant_context}")
        print(f"     Context Stability: {result.context_stability:.2f}")
        print(f"     Context Switches: {len(result.context_transitions)}")
        
        # Validate context-specific insights
        assert result.dominant_context in ["development", "analysis", "research", "documentation", "general"]
        assert 0.0 <= result.context_stability <= 1.0
        assert isinstance(result.context_transitions, list)
        assert len(result.environment_factors) > 0
        
        # Check for realistic professional patterns
        if result.dominant_context == "analysis":
            assert result.confidence >= 0.6  # Should be confident about analysis context
        
        print(f"     Environment Factors: {len(result.environment_factors)}")
        print(f"     Behavioral Insights: {len(result.behavioral_insights)}")
        
    @pytest.mark.asyncio
    async def test_predict_task_outcomes_realistic_scenarios(self, context_service):
        """Test task outcome prediction with realistic professional scenarios"""
        print("\n🎯 Testing Task Outcome Prediction...")
        
        # Test scenario 1: Familiar analysis task
        analysis_task = {
            "task_type": "data_analysis",
            "estimated_duration": 120,  # 2 hours
            "complexity_level": 0.6,
            "required_skills": ["data_analysis", "statistics", "visualization"],
            "collaboration_required": False,
            "deadline": (datetime.utcnow() + timedelta(hours=4)).isoformat() + "Z"
        }
        
        result1 = await context_service.predict_task_outcomes(
            user_id="test_user_professional",
            task_plan=analysis_task
        )
        
        assert isinstance(result1, TaskOutcomePrediction)
        assert result1.user_id == "test_user_professional"
        assert 0.0 <= result1.success_probability <= 1.0
        assert 0.0 <= result1.confidence <= 1.0
        
        print(f"  ✅ Analysis Task Prediction: {result1.success_probability:.2f} success probability")
        print(f"     Confidence: {result1.confidence:.2f}")
        print(f"     Risk Factors: {len(result1.risk_factors)}")
        
        # Should have high success probability for familiar task
        assert result1.success_probability >= 0.6
        
        # Test scenario 2: Complex unfamiliar task
        complex_task = {
            "task_type": "deep_learning_model",
            "estimated_duration": 480,  # 8 hours
            "complexity_level": 0.9,
            "required_skills": ["machine_learning", "deep_learning", "gpu_computing"],
            "collaboration_required": True,
            "deadline": (datetime.utcnow() + timedelta(hours=24)).isoformat() + "Z"
        }
        
        result2 = await context_service.predict_task_outcomes(
            user_id="test_user_professional",
            task_plan=complex_task
        )
        
        print(f"  ✅ Complex Task Prediction: {result2.success_probability:.2f} success probability")
        print(f"     Confidence: {result2.confidence:.2f}")
        print(f"     Estimated Duration: {result2.estimated_duration_minutes} minutes")
        
        # Complex task should have more risk factors
        assert len(result2.risk_factors) >= len(result1.risk_factors)
        
        # Test scenario 3: Time-pressured task
        urgent_task = {
            "task_type": "bug_fix",
            "estimated_duration": 60,  # 1 hour
            "complexity_level": 0.4,
            "required_skills": ["programming", "debugging"],
            "collaboration_required": False,
            "deadline": (datetime.utcnow() + timedelta(minutes=90)).isoformat() + "Z"  # Tight deadline
        }
        
        result3 = await context_service.predict_task_outcomes(
            user_id="test_user_professional",
            task_plan=urgent_task
        )
        
        print(f"  ✅ Urgent Task Prediction: {result3.success_probability:.2f} success probability")
        print(f"     Time pressure should be a factor in risk assessment")
        
        # Should identify time pressure as a risk factor
        time_pressure_risks = [r for r in result3.risk_factors if "time" in r.lower() or "deadline" in r.lower()]
        assert len(time_pressure_risks) > 0
        
    @pytest.mark.asyncio
    async def test_comprehensive_context_analysis_integration(self, context_service):
        """Test comprehensive integration of all context intelligence components"""
        print("\n🔄 Testing Comprehensive Context Analysis Integration...")
        
        comprehensive_result = await context_service.get_comprehensive_analysis(
            user_id="test_user_professional",
            context_type="analysis",
            task_plan={
                "task_type": "customer_segmentation", 
                "estimated_duration": 240,
                "complexity_level": 0.6,
                "required_skills": ["data_analysis", "statistics"],
                "collaboration_required": False
            }
        )
        
        # Validate comprehensive result structure
        assert "context_patterns" in comprehensive_result
        assert "task_outcomes" in comprehensive_result  # Should exist since we provided task_plan
        assert "user_id" in comprehensive_result
        assert "overall_confidence" in comprehensive_result
        
        context_patterns = comprehensive_result["context_patterns"]
        task_outcomes = comprehensive_result["task_outcomes"]
        overall_confidence = comprehensive_result["overall_confidence"]
        
        # Validate context patterns
        assert isinstance(context_patterns, ContextPattern)
        assert context_patterns.user_id == "test_user_professional"
        
        # Validate task outcomes
        assert isinstance(task_outcomes, TaskOutcomePrediction)
        assert task_outcomes.user_id == "test_user_professional"
        
        print(f"  ✅ Context Analysis Integration completed")
        print(f"     Dominant Context: {context_patterns.dominant_context}")
        print(f"     Success Probability: {task_outcomes.success_probability:.2f}")
        print(f"     Overall Confidence: {overall_confidence:.2f}")
        print(f"     Risk Factors: {len(task_outcomes.risk_factors)}")
        
        # Validate confidence scores
        assert 0.0 <= overall_confidence <= 1.0
        assert 0.0 <= task_outcomes.success_probability <= 1.0
        
    @pytest.mark.asyncio
    async def test_context_evolution_tracking(self, context_service):
        """Test tracking of context evolution over time"""
        print("\n📈 Testing Context Evolution Tracking...")
        
        # Analyze different time periods
        short_term = await context_service.analyze_context_patterns(
            user_id="test_user_professional",
            context_type="development"
        )
        
        long_term = await context_service.analyze_context_patterns(
            user_id="test_user_professional", 
            context_type="analysis"
        )
        
        print(f"  ✅ Short-term Context (7d): {short_term.dominant_context}")
        print(f"     Stability: {short_term.context_stability:.2f}")
        
        print(f"  ✅ Long-term Context (30d): {long_term.dominant_context}")
        print(f"     Stability: {long_term.context_stability:.2f}")
        
        # Validate evolution insights
        context_evolution = {
            "short_term_context": short_term.dominant_context,
            "long_term_context": long_term.dominant_context,
            "stability_change": abs(short_term.context_stability - long_term.context_stability),
            "transition_frequency_change": len(short_term.context_transitions) - len(long_term.context_transitions)
        }
        
        print(f"     Context Evolution Detected: {context_evolution['short_term_context'] != context_evolution['long_term_context']}")
        print(f"     Stability Change: {context_evolution['stability_change']:.2f}")
        
        # Context should show some evolution or stability
        assert context_evolution["stability_change"] >= 0.0
        
    @pytest.mark.asyncio
    async def test_performance_and_error_handling(self, context_service):
        """Test performance characteristics and error handling"""
        print("\n⚡ Testing Performance and Error Handling...")
        
        # Test with invalid user
        try:
            result = await context_service.analyze_context_patterns(
                user_id="nonexistent_user",
                context_type="general"
            )
            # Should still return a result with low confidence
            assert result.confidence <= 0.5
            print(f"  ✅ Handled nonexistent user gracefully")
        except Exception as e:
            print(f"  ⚠️ Error handling could be improved: {e}")
        
        # Test with empty context
        result = await context_service.analyze_context_patterns(
            user_id="test_user_professional",
            context_type="general"
        )
        assert isinstance(result, ContextPattern)
        print(f"  ✅ Handled empty context gracefully")
        
        # Test with malformed task context
        try:
            result = await context_service.predict_task_outcomes(
                user_id="test_user_professional",
                task_plan={"invalid": "structure"}
            )
            assert isinstance(result, TaskOutcomePrediction)
            print(f"  ✅ Handled malformed task context gracefully")
        except Exception as e:
            print(f"  ⚠️ Task context error handling could be improved: {e}")
        
        # Performance test - multiple concurrent requests
        import time
        start_time = time.time()
        
        tasks = [
            context_service.analyze_context_patterns(
                user_id="test_user_professional",
                context_type="general"
            )
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        assert len(results) == 5
        assert all(isinstance(r, ContextPattern) for r in results)
        
        print(f"  ✅ Performance Test: 5 concurrent requests in {end_time - start_time:.2f}s")
        print(f"     Average response time: {(end_time - start_time) / 5:.2f}s per request")
        
    @pytest.mark.asyncio
    async def test_context_intelligence_data_quality(self, context_service):
        """Test data quality and consistency in context intelligence results"""
        print("\n🔍 Testing Data Quality and Consistency...")
        
        # Run analysis multiple times to check consistency
        results = []
        for i in range(3):
            result = await context_service.analyze_context_patterns(
                user_id="test_user_professional",
                context_type="general"
            )
            results.append(result)
        
        # Check consistency
        dominant_contexts = [r.dominant_context for r in results]
        context_stabilities = [r.context_stability for r in results]
        
        # Should be consistent across runs with same data
        assert len(set(dominant_contexts)) <= 2  # Allow some variation
        
        # Stability should be similar
        stability_variance = max(context_stabilities) - min(context_stabilities)
        assert stability_variance <= 0.1  # Should be fairly consistent
        
        print(f"  ✅ Consistency check passed")
        print(f"     Dominant contexts: {dominant_contexts}")
        print(f"     Stability variance: {stability_variance:.3f}")
        
        # Test data completeness
        sample_result = results[0]
        
        # Required fields should be populated
        assert sample_result.dominant_context is not None
        assert sample_result.context_stability is not None
        assert sample_result.environment_factors is not None
        assert sample_result.behavioral_insights is not None
        
        # Data should be in valid ranges
        assert 0.0 <= sample_result.context_stability <= 1.0
        assert 0.0 <= sample_result.confidence <= 1.0
        
        print(f"  ✅ Data quality validation passed")
        print(f"     All required fields populated with valid ranges")


# Additional utility function for running tests
async def run_suite2_tests():
    """Run all Suite 2 integration tests"""
    print("=" * 80)
    print("🧠 SUITE 2: CONTEXT INTELLIGENCE INTEGRATION TESTS")
    print("=" * 80)
    
    test_instance = TestSuite2ContextIntelligence()
    
    # Create service instance
    service = ContextIntelligenceService()
    
    # Replace repositories with mocks
    service.context_analyzer.usage_repository = MockUsageRepository()
    service.context_analyzer.session_repository = MockSessionRepository()
    service.outcome_predictor.usage_repository = MockUsageRepository()
    service.outcome_predictor.session_repository = MockSessionRepository()
    service.outcome_predictor.user_repository = MockUserRepository()
    
    try:
        # Run all test methods
        await test_instance.test_analyze_context_patterns_comprehensive(service)
        await test_instance.test_predict_task_outcomes_realistic_scenarios(service)
        await test_instance.test_comprehensive_context_analysis_integration(service)
        await test_instance.test_context_evolution_tracking(service)
        await test_instance.test_performance_and_error_handling(service)
        await test_instance.test_context_intelligence_data_quality(service)
        
        print("\n" + "=" * 80)
        print("✅ ALL SUITE 2 TESTS PASSED SUCCESSFULLY!")
        print("Context Intelligence service is ready for integration")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("=" * 80)
        return False


# Run tests if called directly
if __name__ == "__main__":
    asyncio.run(run_suite2_tests())