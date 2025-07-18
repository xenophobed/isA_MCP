#!/usr/bin/env python3
"""
Tests for Working Memory Engine with Intelligent Dialog Processing
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from tools.services.memory_service.engines.working_engine import WorkingMemoryEngine
from tools.services.memory_service.models import MemoryOperationResult, WorkingMemory


class TestWorkingMemoryEngine:
    """Test suite for intelligent working memory processing"""

    @pytest.fixture
    def engine(self):
        """Create a mock working engine for testing"""
        with patch('tools.services.memory_service.engines.base_engine.get_supabase_client') as mock_db, \
             patch('tools.services.memory_service.engines.base_engine.EmbeddingGenerator') as mock_embedder, \
             patch('tools.services.intelligence_service.language.text_extractor.TextExtractor') as mock_extractor:
            
            # Mock database
            mock_db.return_value = MagicMock()
            
            # Mock embedder
            mock_embedder_instance = AsyncMock()
            mock_embedder.return_value = mock_embedder_instance
            mock_embedder_instance.embed_single.return_value = [0.1, 0.2, 0.3]
            
            # Mock text extractor
            mock_extractor_instance = AsyncMock()
            mock_extractor.return_value = mock_extractor_instance
            
            engine = WorkingMemoryEngine()
            engine.db = mock_db.return_value
            engine.embedder = mock_embedder_instance
            engine.text_extractor = mock_extractor_instance
            
            return engine

    @pytest.mark.asyncio
    async def test_store_working_memory_successful_extraction(self, engine):
        """Test successful working memory storage with intelligent extraction"""
        
        # Mock dialog content with task information
        dialog_content = """
        Human: I'm working on analyzing customer data for our Q4 report. I've imported the data and cleaned it, now I need to run statistical analysis and create visualizations.
        
        AI: Great! For your Q4 customer data analysis, I can help you with the statistical analysis and visualizations. What specific metrics are you looking to analyze?
        
        Human: I need to analyze customer acquisition trends, retention rates, and revenue patterns. This is a high priority project due next week.
        """
        
        # Mock extraction results
        mock_extraction_result = {
            'success': True,
            'data': {
                'task_id': 'q4_customer_analysis',
                'clean_content': 'Analyzing customer data for Q4 report including acquisition trends, retention rates, and revenue patterns',
                'task_context': {
                    'data_status': 'imported_and_cleaned',
                    'analysis_types': ['customer_acquisition', 'retention_rates', 'revenue_patterns'],
                    'deliverable': 'Q4_report',
                    'deadline': 'next_week'
                },
                'priority': 4,
                'importance_score': 0.9,
                'current_step': 'statistical_analysis_and_visualization',
                'next_actions': ['run statistical analysis', 'create visualizations', 'compile report'],
                'interim_results': ['data imported and cleaned'],
                'blocking_issues': [],
                'time_sensitivity': 'high'
            },
            'confidence': 0.9
        }
        
        # Configure text extractor mock
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        
        # Mock store_memory to return the expected result
        engine.store_memory = AsyncMock(return_value=MemoryOperationResult(
            success=True,
            memory_id="working_memory_id",
            operation="store_working_memory",
            message="Working memory stored successfully"
        ))
        
        # Test the store_working_memory method
        result = await engine.store_working_memory(
            user_id="user123",
            dialog_content=dialog_content,
            ttl_seconds=7200  # 2 hours
        )
        
        # Assertions
        assert result.success == True
        assert result.operation == "store_working_memory"
        assert result.memory_id == "working_memory_id"
        
        # Verify text extractor was called
        engine.text_extractor.extract_key_information.assert_called_once()
        
        # Verify store_memory was called
        engine.store_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_working_memory_extraction_failure(self, engine):
        """Test working memory storage when extraction fails"""
        
        dialog_content = "Brief task"
        
        # Mock failed extraction
        mock_extraction_result = {
            'success': False,
            'error': 'Text too short for meaningful working memory extraction',
            'data': {},
            'confidence': 0.0
        }
        
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        
        # Test the store_working_memory method
        result = await engine.store_working_memory(
            user_id="user123",
            dialog_content=dialog_content
        )
        
        # Assertions
        assert result.success == False
        assert "Failed to extract working memory information" in result.message
        assert result.operation == "store_working_memory"

    @pytest.mark.asyncio
    async def test_search_active_working_memories(self, engine):
        """Test searching active working memories"""
        
        # Mock database response
        mock_memories_data = [
            {
                'id': 'memory1',
                'user_id': 'user123',
                'content': 'Q4 customer analysis project',
                'memory_type': 'working',
                'task_id': 'q4_analysis',
                'task_context': '{"current_step": "data_analysis", "priority": "high"}',
                'ttl_seconds': 7200,
                'priority': 4,
                'expires_at': (datetime.now() + timedelta(hours=2)).isoformat(),
                'importance_score': 0.9,
                'access_count': 3,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            },
            {
                'id': 'memory2',
                'user_id': 'user123',
                'content': 'Bug fix for authentication issue',
                'memory_type': 'working',
                'task_id': 'auth_bug_fix',
                'task_context': '{"current_step": "testing", "priority": "urgent"}',
                'ttl_seconds': 3600,
                'priority': 5,
                'expires_at': (datetime.now() + timedelta(hours=1)).isoformat(),
                'importance_score': 0.95,
                'access_count': 1,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.2, 0.3, 0.4]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.gt.return_value.order.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_memories_data
        )
        
        # Test search
        memories = await engine.search_active_working_memories(
            user_id="user123",
            limit=10
        )
        
        # Assertions
        assert len(memories) == 2
        assert all(memory.user_id == "user123" for memory in memories)

    @pytest.mark.asyncio
    async def test_search_working_memories_by_task(self, engine):
        """Test searching working memories by task"""
        
        # Mock database response
        mock_memories_data = [
            {
                'id': 'memory1',
                'user_id': 'user123',
                'content': 'Q4 analysis progress update',
                'memory_type': 'working',
                'task_id': 'q4_customer_analysis',
                'task_context': '{"current_step": "visualization"}',
                'ttl_seconds': 7200,
                'priority': 3,
                'expires_at': (datetime.now() + timedelta(hours=2)).isoformat(),
                'importance_score': 0.8,
                'access_count': 2,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.ilike.return_value.gt.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_memories_data
        )
        
        # Test search
        memories = await engine.search_working_memories_by_task(
            user_id="user123",
            task_id="q4_customer_analysis",
            limit=5
        )
        
        # Assertions
        assert len(memories) == 1
        assert "q4_customer_analysis" in memories[0].task_id

    @pytest.mark.asyncio
    async def test_search_working_memories_by_priority(self, engine):
        """Test searching working memories by priority level"""
        
        # Mock database response
        mock_memories_data = [
            {
                'id': 'urgent_memory',
                'user_id': 'user123',
                'content': 'Critical production issue',
                'memory_type': 'working',
                'task_id': 'prod_issue_fix',
                'task_context': '{"severity": "critical"}',
                'ttl_seconds': 1800,
                'priority': 5,
                'expires_at': (datetime.now() + timedelta(minutes=30)).isoformat(),
                'importance_score': 1.0,
                'access_count': 1,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.gte.return_value.gt.return_value.order.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_memories_data
        )
        
        # Test search for high-priority memories
        memories = await engine.search_working_memories_by_priority(
            user_id="user123",
            min_priority=4,
            limit=5
        )
        
        # Assertions
        assert len(memories) == 1
        assert memories[0].priority >= 4

    @pytest.mark.asyncio
    async def test_search_working_memories_by_time_remaining(self, engine):
        """Test searching working memories that expire soon"""
        
        # Mock database response with memory expiring soon
        expires_soon = datetime.now() + timedelta(minutes=30)
        mock_memories_data = [
            {
                'id': 'expiring_memory',
                'user_id': 'user123',
                'content': 'Task expiring soon',
                'memory_type': 'working',
                'task_id': 'urgent_task',
                'task_context': '{"deadline": "soon"}',
                'ttl_seconds': 1800,
                'priority': 3,
                'expires_at': expires_soon.isoformat(),
                'importance_score': 0.8,
                'access_count': 1,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.gt.return_value.lt.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_memories_data
        )
        
        # Test search
        memories = await engine.search_working_memories_by_time_remaining(
            user_id="user123",
            max_hours_remaining=1.0,
            limit=5
        )
        
        # Assertions
        assert len(memories) == 1
        assert memories[0].expires_at <= datetime.now() + timedelta(hours=1)

    @pytest.mark.asyncio
    async def test_search_working_memories_by_context_key(self, engine):
        """Test searching working memories by context key"""
        
        # Mock database response
        mock_memories_data = [
            {
                'id': 'memory1',
                'user_id': 'user123',
                'content': 'Project with specific context',
                'memory_type': 'working',
                'task_id': 'special_project',
                'task_context': '{"project_type": "data_analysis", "phase": "modeling"}',
                'ttl_seconds': 3600,
                'priority': 3,
                'expires_at': (datetime.now() + timedelta(hours=1)).isoformat(),
                'importance_score': 0.7,
                'access_count': 2,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            },
            {
                'id': 'memory2',
                'user_id': 'user123',
                'content': 'Different project',
                'memory_type': 'working',
                'task_id': 'other_project',
                'task_context': '{"project_type": "web_development", "phase": "testing"}',
                'ttl_seconds': 3600,
                'priority': 2,
                'expires_at': (datetime.now() + timedelta(hours=1)).isoformat(),
                'importance_score': 0.6,
                'access_count': 1,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.2, 0.3, 0.4]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.gt.return_value.order.return_value.execute.return_value = MagicMock(
            data=mock_memories_data
        )
        
        # Test search
        memories = await engine.search_working_memories_by_context_key(
            user_id="user123",
            context_key="project_type",
            limit=5
        )
        
        # Assertions
        assert len(memories) == 2
        assert all("project_type" in memory.task_context for memory in memories)

    @pytest.mark.asyncio
    async def test_extend_memory_ttl(self, engine):
        """Test extending TTL of a working memory"""
        
        # Mock existing working memory
        existing_memory = WorkingMemory(
            id="memory_id",
            user_id="user123",
            content="Task in progress",
            memory_type="working",
            task_id="ongoing_task",
            task_context={"step": "analysis"},
            ttl_seconds=3600,
            priority=3,
            expires_at=datetime.now() + timedelta(hours=1),
            importance_score=0.7,
            access_count=2,
            source="user_dialog",
            verification_status="unverified",
            embedding=[0.1, 0.2, 0.3]
        )
        
        # Mock get_memory to return existing memory
        engine.get_memory = AsyncMock(return_value=existing_memory)
        
        # Mock update_memory
        engine.update_memory = AsyncMock(return_value=MemoryOperationResult(
            success=True,
            memory_id="memory_id",
            operation="extend_ttl",
            message="TTL extended successfully"
        ))
        
        # Test extending TTL
        result = await engine.extend_memory_ttl("memory_id", 1800)  # Add 30 minutes
        
        # Assertions
        assert result.success == True
        assert result.operation == "extend_ttl"
        
        # Verify update_memory was called
        engine.update_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_context(self, engine):
        """Test updating task context"""
        
        # Mock existing working memory
        existing_memory = WorkingMemory(
            id="memory_id",
            user_id="user123",
            content="Task with context",
            memory_type="working",
            task_id="context_task",
            task_context={"step": "initial", "progress": 25},
            ttl_seconds=3600,
            priority=2,
            expires_at=datetime.now() + timedelta(hours=1),
            importance_score=0.6,
            access_count=1,
            source="user_dialog",
            verification_status="unverified",
            embedding=[0.1, 0.2, 0.3]
        )
        
        # Mock get_memory to return existing memory
        engine.get_memory = AsyncMock(return_value=existing_memory)
        
        # Mock update_memory
        engine.update_memory = AsyncMock(return_value=MemoryOperationResult(
            success=True,
            memory_id="memory_id",
            operation="update_context",
            message="Context updated successfully"
        ))
        
        # Test updating context
        context_updates = {"step": "advanced", "progress": 75, "notes": "Making good progress"}
        result = await engine.update_task_context("memory_id", context_updates)
        
        # Assertions
        assert result.success == True
        assert result.operation == "update_context"
        
        # Verify update_memory was called
        engine.update_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_progress(self, engine):
        """Test updating task progress"""
        
        # Mock existing working memory
        existing_memory = WorkingMemory(
            id="memory_id",
            user_id="user123",
            content="Task with progress tracking",
            memory_type="working",
            task_id="progress_task",
            task_context={"step": "starting"},
            ttl_seconds=3600,
            priority=3,
            expires_at=datetime.now() + timedelta(hours=1),
            importance_score=0.7,
            access_count=1,
            source="user_dialog",
            verification_status="unverified",
            embedding=[0.1, 0.2, 0.3]
        )
        
        # Mock get_memory to return existing memory
        engine.get_memory = AsyncMock(return_value=existing_memory)
        
        # Mock update_memory
        engine.update_memory = AsyncMock(return_value=MemoryOperationResult(
            success=True,
            memory_id="memory_id",
            operation="update_context",
            message="Context updated successfully"
        ))
        
        # Test updating progress
        result = await engine.update_task_progress(
            "memory_id",
            current_step="analysis_complete",
            progress_percentage=60.0,
            next_actions=["create_visualizations", "write_report"]
        )
        
        # Assertions
        assert result.success == True
        
        # Verify update_memory was called
        engine.update_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_expired_memories(self, engine):
        """Test cleaning up expired memories"""
        
        # Mock database delete operation
        engine.db.table.return_value.delete.return_value.lt.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{'id': 'deleted1'}, {'id': 'deleted2'}]
        )
        
        # Test cleanup
        result = await engine.cleanup_expired_memories(user_id="user123")
        
        # Assertions
        assert result.success == True
        assert result.operation == "cleanup_expired"
        assert "2 expired working memories" in result.message
        assert result.affected_count == 2

    @pytest.mark.asyncio
    async def test_get_task_summary(self, engine):
        """Test getting task summary"""
        
        # Mock working memories for a task
        memory1 = WorkingMemory(
            id="memory1",
            user_id="user123",
            content="Task progress 1",
            memory_type="working",
            task_id="summary_task",
            task_context={
                "current_step": "data_collection",
                "next_actions": ["clean_data", "analyze"],
                "progress_percentage": 30
            },
            ttl_seconds=3600,
            priority=3,
            expires_at=datetime.now() + timedelta(hours=1),
            importance_score=0.7,
            access_count=2,
            source="user_dialog",
            verification_status="unverified",
            embedding=[0.1, 0.2, 0.3]
        )
        
        memory2 = WorkingMemory(
            id="memory2",
            user_id="user123",
            content="Task progress 2",
            memory_type="working",
            task_id="summary_task",
            task_context={
                "current_step": "data_analysis",
                "next_actions": ["create_report"],
                "blocking_issues": ["missing_data_source"]
            },
            ttl_seconds=3600,
            priority=4,
            expires_at=datetime.now() + timedelta(hours=1),
            importance_score=0.8,
            access_count=1,
            source="user_dialog",
            verification_status="unverified",
            embedding=[0.2, 0.3, 0.4]
        )
        
        # Mock search_working_memories_by_task
        engine.search_working_memories_by_task = AsyncMock(return_value=[memory1, memory2])
        
        # Test get task summary
        summary = await engine.get_task_summary("user123", "summary_task")
        
        # Assertions
        assert summary['task_id'] == "summary_task"
        assert summary['total_memories'] == 2
        assert summary['highest_priority'] == 4
        assert summary['status'] == 'active'
        assert 'data_collection' in summary['current_steps']
        assert 'data_analysis' in summary['current_steps']
        assert 'clean_data' in summary['next_actions']
        assert 'missing_data_source' in summary['blocking_issues']

    @pytest.mark.asyncio
    async def test_process_working_memory_data_validation(self, engine):
        """Test working memory data processing and validation"""
        
        # Test data with various edge cases
        raw_data = {
            'task_id': 'Complex Task Name',  # Should be normalized
            'clean_content': 'Working on data analysis project',
            'priority': '3.5',  # Should be converted and clamped
            'importance_score': 1.2,  # Should be clamped
            'current_step': 'data_preprocessing',
            'next_actions': ['feature_engineering', 'model_training'],
            'interim_results': ['data_loaded', 'cleaned_80_percent'],
            'blocking_issues': [],
            'time_sensitivity': 'medium'
        }
        
        original_content = "This is the original dialog content for fallback task ID generation."
        
        # Test the processing method directly
        processed = await engine._process_working_memory_data(raw_data, original_content)
        
        # Assertions
        assert processed['task_id'] == 'complex_task_name'  # Normalized
        assert processed['priority'] == 3  # Converted and clamped (3.5 -> 3 when int(), max 5)
        assert processed['importance_score'] == 1.0  # Clamped
        assert processed['task_context']['current_step'] == 'data_preprocessing'
        assert processed['task_context']['next_actions'] == ['feature_engineering', 'model_training']
        assert 'extraction_timestamp' in processed['task_context']

    @pytest.mark.asyncio
    async def test_search_methods_error_handling(self, engine):
        """Test error handling in search methods"""
        
        # Mock database error
        engine.db.table.return_value.select.side_effect = Exception("Database error")
        
        # Test all search methods handle errors gracefully
        result1 = await engine.search_active_working_memories("user123")
        assert result1 == []
        
        result2 = await engine.search_working_memories_by_task("user123", "task1")
        assert result2 == []
        
        result3 = await engine.search_working_memories_by_priority("user123", 3)
        assert result3 == []
        
        result4 = await engine.search_working_memories_by_time_remaining("user123", 1.0)
        assert result4 == []
        
        result5 = await engine.search_working_memories_by_context_key("user123", "key")
        assert result5 == []

    def test_engine_properties(self, engine):
        """Test engine basic properties"""
        assert engine.table_name == "working_memories"
        assert engine.memory_type == "working"

    @pytest.mark.asyncio
    async def test_extraction_with_complex_task_context(self, engine):
        """Test extraction of complex task with detailed context"""
        
        dialog_content = """
        Human: I'm debugging a critical production issue with our authentication service. The service is experiencing 30% failure rate for login attempts. I've already checked the database connections and they're stable. 
        
        AI: That's a serious issue. Let's systematically debug this. Have you checked the authentication service logs for any error patterns?
        
        Human: Yes, I see timeout errors from the OAuth provider. I suspect it's a network latency issue. Next I need to check the load balancer configuration and maybe implement retry logic. This needs to be fixed within the next 2 hours before peak traffic.
        """
        
        # Mock complex extraction result
        mock_extraction_result = {
            'success': True,
            'data': {
                'task_id': 'auth_service_debug',
                'clean_content': 'Debugging critical production authentication service with 30% failure rate due to OAuth timeout issues',
                'task_context': {
                    'service': 'authentication_service',
                    'issue_type': 'timeout_errors',
                    'failure_rate': '30_percent',
                    'root_cause_suspect': 'oauth_provider_network_latency',
                    'verified_working': ['database_connections'],
                    'environment': 'production'
                },
                'priority': 5,
                'importance_score': 1.0,
                'current_step': 'investigating_oauth_timeouts',
                'next_actions': [
                    'check_load_balancer_configuration',
                    'implement_retry_logic',
                    'monitor_oauth_provider_response_times'
                ],
                'interim_results': [
                    'database_connections_stable',
                    'timeout_errors_identified_in_logs',
                    'oauth_provider_suspected'
                ],
                'blocking_issues': ['oauth_provider_network_latency'],
                'time_sensitivity': 'urgent'
            },
            'confidence': 0.95
        }
        
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        engine.store_memory = AsyncMock(return_value=MemoryOperationResult(
            success=True,
            memory_id="complex_working_memory_id",
            operation="store_working_memory",
            message="Complex working memory stored successfully"
        ))
        
        # Test
        result = await engine.store_working_memory(
            user_id="user123",
            dialog_content=dialog_content,
            ttl_seconds=7200  # 2 hours for urgent task
        )
        
        # Assertions
        assert result.success == True
        assert result.memory_id == "complex_working_memory_id"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])