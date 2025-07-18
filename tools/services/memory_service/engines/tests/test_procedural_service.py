#!/usr/bin/env python3
"""
Tests for Procedural Memory Engine with Intelligent Dialog Processing
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from tools.services.memory_service.engines.procedural_engine import ProceduralMemoryEngine
from tools.services.memory_service.models import MemoryOperationResult, ProceduralMemory


class TestProceduralMemoryEngine:
    """Test suite for intelligent procedural memory processing"""

    @pytest.fixture
    def engine(self):
        """Create a mock procedural engine for testing"""
        with patch('tools.services.memory_service.engines.base_engine.get_supabase_client') as mock_db, \
             patch('tools.services.memory_service.engines.base_engine.EmbeddingGenerator') as mock_embedder, \
             patch('tools.services.memory_service.engines.procedural_engine.TextExtractor') as mock_extractor:
            
            # Mock database
            mock_db.return_value = MagicMock()
            
            # Mock embedder
            mock_embedder_instance = AsyncMock()
            mock_embedder.return_value = mock_embedder_instance
            mock_embedder_instance.embed_single.return_value = [0.1, 0.2, 0.3]
            
            # Mock text extractor
            mock_extractor_instance = AsyncMock()
            mock_extractor.return_value = mock_extractor_instance
            
            engine = ProceduralMemoryEngine()
            engine.db = mock_db.return_value
            engine.embedder = mock_embedder_instance
            engine.text_extractor = mock_extractor_instance
            
            return engine

    @pytest.mark.asyncio
    async def test_store_procedural_memory_successful_extraction(self, engine):
        """Test successful procedural memory storage with intelligent extraction"""
        
        # Mock dialog content with procedural information
        dialog_content = """
        Human: Can you help me understand how to deploy a web application using Docker?
        
        AI: I'll walk you through the process step by step:

        First, you need to create a Dockerfile in your project root. This file defines how to build your application container. Start with a base image like node:16 for Node.js apps.

        Next, copy your application files into the container and install dependencies using npm install or similar commands.

        Then build the Docker image using 'docker build -t myapp .' command in your terminal.

        After that, run the container with 'docker run -p 3000:3000 myapp' to expose port 3000.

        Finally, test your application by visiting localhost:3000 in your browser.

        This process requires Docker installed on your machine and basic knowledge of command line operations.
        """
        
        # Mock extraction results
        mock_extraction_result = {
            'success': True,
            'data': {
                'skill_type': 'web_deployment',
                'clean_content': 'How to deploy a web application using Docker containers with step-by-step instructions',
                'steps': [
                    {
                        'step_number': 1,
                        'description': 'Create a Dockerfile in your project root with base image',
                        'importance': 'critical',
                        'estimated_time': '5 minutes',
                        'tools_needed': ['text editor']
                    },
                    {
                        'step_number': 2,
                        'description': 'Copy application files and install dependencies',
                        'importance': 'critical',
                        'estimated_time': '2 minutes',
                        'tools_needed': ['docker']
                    },
                    {
                        'step_number': 3,
                        'description': 'Build Docker image using docker build command',
                        'importance': 'critical',
                        'estimated_time': '1-5 minutes',
                        'tools_needed': ['docker', 'terminal']
                    },
                    {
                        'step_number': 4,
                        'description': 'Run container with port mapping',
                        'importance': 'critical',
                        'estimated_time': '30 seconds',
                        'tools_needed': ['docker', 'terminal']
                    },
                    {
                        'step_number': 5,
                        'description': 'Test application by visiting localhost:3000',
                        'importance': 'important',
                        'estimated_time': '1 minute',
                        'tools_needed': ['web browser']
                    }
                ],
                'prerequisites': ['Docker installed', 'command line knowledge', 'web application source code'],
                'difficulty_level': 'intermediate',
                'domain': 'technology',
                'importance_score': 0.8,
                'tools_required': ['Docker', 'terminal', 'text editor'],
                'success_indicators': ['Application accessible on localhost:3000', 'No error messages in docker logs'],
                'common_mistakes': ['Forgetting to expose ports', 'Not copying files correctly']
            },
            'confidence': 0.9
        }
        
        # Configure text extractor mock
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        
        # Mock store_memory to return the expected result
        engine.store_memory = AsyncMock(return_value=MemoryOperationResult(
            success=True,
            memory_id="procedure_memory_id",
            operation="store_procedural_memory",
            message="Procedural memory stored successfully"
        ))
        
        # Test the store_procedural_memory method
        result = await engine.store_procedural_memory(
            user_id="user123",
            dialog_content=dialog_content
        )
        
        # Assertions
        assert result.success == True
        assert result.operation == "store_procedural_memory"
        assert result.memory_id == "procedure_memory_id"
        
        # Verify text extractor was called
        engine.text_extractor.extract_key_information.assert_called_once()
        
        # Verify store_memory was called
        engine.store_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_procedural_memory_extraction_failure(self, engine):
        """Test procedural memory storage when extraction fails"""
        
        dialog_content = "Short content"
        
        # Mock failed extraction
        mock_extraction_result = {
            'success': False,
            'error': 'Text too short for meaningful procedural extraction',
            'data': {},
            'confidence': 0.0
        }
        
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        
        # Test the store_procedural_memory method
        result = await engine.store_procedural_memory(
            user_id="user123",
            dialog_content=dialog_content
        )
        
        # Assertions
        assert result.success == False
        assert "Failed to extract procedural information" in result.message
        assert result.operation == "store_procedural_memory"

    @pytest.mark.asyncio
    async def test_search_procedures_by_domain(self, engine):
        """Test searching procedures by domain"""
        
        # Mock database response
        mock_procedures_data = [
            {
                'id': 'proc1',
                'user_id': 'user123',
                'content': 'How to deploy web applications using Docker',
                'memory_type': 'procedural',
                'skill_type': 'web_deployment',
                'steps': '[{"step_number": 1, "description": "Create Dockerfile"}]',
                'prerequisites': '["Docker knowledge"]',
                'difficulty_level': 'intermediate',
                'success_rate': 0.9,
                'domain': 'technology',
                'importance_score': 0.8,
                'access_count': 5,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            },
            {
                'id': 'proc2',
                'user_id': 'user123',
                'content': 'How to set up CI/CD pipeline',
                'memory_type': 'procedural',
                'skill_type': 'devops',
                'steps': '[{"step_number": 1, "description": "Configure GitHub Actions"}]',
                'prerequisites': '["Git knowledge"]',
                'difficulty_level': 'advanced',
                'success_rate': 0.85,
                'domain': 'technology',
                'importance_score': 0.9,
                'access_count': 3,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.2, 0.3, 0.4]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.ilike.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_procedures_data
        )
        
        # Test search
        procedures = await engine.search_procedures_by_domain(
            user_id="user123",
            domain="technology",
            limit=5
        )
        
        # Assertions
        assert len(procedures) == 2
        assert all(proc.domain == "technology" for proc in procedures)

    @pytest.mark.asyncio
    async def test_search_procedures_by_skill_type(self, engine):
        """Test searching procedures by skill type"""
        
        # Mock database response
        mock_procedures_data = [
            {
                'id': 'proc1',
                'user_id': 'user123',
                'content': 'How to deploy web applications',
                'memory_type': 'procedural',
                'skill_type': 'web_deployment',
                'steps': '[{"step_number": 1, "description": "Create Dockerfile"}]',
                'prerequisites': '[]',
                'difficulty_level': 'intermediate',
                'success_rate': 0.9,
                'domain': 'technology',
                'importance_score': 0.8,
                'access_count': 5,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.ilike.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_procedures_data
        )
        
        # Test search
        procedures = await engine.search_procedures_by_skill_type(
            user_id="user123",
            skill_type="web_deployment",
            limit=5
        )
        
        # Assertions
        assert len(procedures) == 1
        assert procedures[0].skill_type == "web_deployment"

    @pytest.mark.asyncio
    async def test_search_procedures_by_difficulty(self, engine):
        """Test searching procedures by difficulty level"""
        
        # Mock database response
        mock_procedures_data = [
            {
                'id': 'proc1',
                'user_id': 'user123',
                'content': 'Advanced Docker deployment',
                'memory_type': 'procedural',
                'skill_type': 'deployment',
                'steps': '[{"step_number": 1, "description": "Configure orchestration"}]',
                'prerequisites': '["Docker", "Kubernetes"]',
                'difficulty_level': 'advanced',
                'success_rate': 0.75,
                'domain': 'technology',
                'importance_score': 0.9,
                'access_count': 2,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_procedures_data
        )
        
        # Test search
        procedures = await engine.search_procedures_by_difficulty(
            user_id="user123",
            difficulty_level="advanced",
            limit=5
        )
        
        # Assertions
        assert len(procedures) == 1
        assert procedures[0].difficulty_level == "advanced"

    @pytest.mark.asyncio
    async def test_search_procedures_by_success_rate(self, engine):
        """Test searching procedures by success rate"""
        
        # Mock database response
        mock_procedures_data = [
            {
                'id': 'high_success_proc',
                'user_id': 'user123',
                'content': 'Reliable deployment procedure',
                'memory_type': 'procedural',
                'skill_type': 'deployment',
                'steps': '[{"step_number": 1, "description": "Follow tested steps"}]',
                'prerequisites': '[]',
                'difficulty_level': 'intermediate',
                'success_rate': 0.95,
                'domain': 'technology',
                'importance_score': 0.8,
                'access_count': 10,
                'source': 'user_dialog',
                'verification_status': 'verified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_procedures_data
        )
        
        # Test search for high-success procedures
        procedures = await engine.search_procedures_by_success_rate(
            user_id="user123",
            min_success_rate=0.9,
            limit=5
        )
        
        # Assertions
        assert len(procedures) == 1
        assert procedures[0].success_rate >= 0.9

    @pytest.mark.asyncio
    async def test_search_procedures_by_prerequisites(self, engine):
        """Test searching procedures by prerequisites"""
        
        # Mock database response
        mock_procedures_data = [
            {
                'id': 'proc1',
                'user_id': 'user123',
                'content': 'Advanced Docker orchestration',
                'memory_type': 'procedural',
                'skill_type': 'orchestration',
                'steps': '[{"step_number": 1, "description": "Set up cluster"}]',
                'prerequisites': '["Docker", "Kubernetes", "Linux"]',
                'difficulty_level': 'expert',
                'success_rate': 0.8,
                'domain': 'technology',
                'importance_score': 0.9,
                'access_count': 1,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.1, 0.2, 0.3]',
                'context': '{}',
                'tags': '[]'
            },
            {
                'id': 'proc2',
                'user_id': 'user123',
                'content': 'Basic web deployment',
                'memory_type': 'procedural',
                'skill_type': 'deployment',
                'steps': '[{"step_number": 1, "description": "Upload files"}]',
                'prerequisites': '["FTP knowledge"]',
                'difficulty_level': 'beginner',
                'success_rate': 0.9,
                'domain': 'technology',
                'importance_score': 0.5,
                'access_count': 5,
                'source': 'user_dialog',
                'verification_status': 'unverified',
                'embedding': '[0.2, 0.3, 0.4]',
                'context': '{}',
                'tags': '[]'
            }
        ]
        
        # Mock database query
        engine.db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=mock_procedures_data
        )
        
        # Test search
        procedures = await engine.search_procedures_by_prerequisites(
            user_id="user123",
            prerequisite="Docker",
            limit=5
        )
        
        # Assertions
        assert len(procedures) == 1
        assert "Docker" in procedures[0].prerequisites

    @pytest.mark.asyncio
    async def test_update_success_rate(self, engine):
        """Test updating procedure success rate"""
        
        # Mock existing procedure
        existing_procedure = ProceduralMemory(
            id="existing_proc_id",
            user_id="user123",
            content="How to deploy applications",
            memory_type="procedural",
            skill_type="deployment",
            steps=[{"step_number": 1, "description": "Deploy app"}],
            prerequisites=[],
            difficulty_level="intermediate",
            success_rate=0.7,
            domain="technology",
            importance_score=0.8,
            access_count=5,
            source="user_dialog",
            verification_status="unverified",
            embedding=[0.1, 0.2, 0.3]
        )
        
        # Mock get_memory to return existing procedure
        engine.get_memory = AsyncMock(return_value=existing_procedure)
        
        # Mock update_memory
        engine.update_memory = AsyncMock(return_value=MemoryOperationResult(
            success=True,
            memory_id="existing_proc_id",
            operation="update_success_rate",
            message="Success rate updated successfully"
        ))
        
        # Test successful execution
        result = await engine.update_success_rate("existing_proc_id", True)
        
        # Assertions
        assert result.success == True
        assert result.operation == "update_success_rate"
        
        # Verify update_memory was called with correct parameters
        engine.update_memory.assert_called_once()
        args = engine.update_memory.call_args[0]
        updates = args[1]
        assert updates['access_count'] == 6  # Incremented
        assert updates['success_rate'] > 0.7  # Increased due to success

    @pytest.mark.asyncio
    async def test_process_procedural_data_validation(self, engine):
        """Test procedural data processing and validation"""
        
        # Test data with various edge cases
        raw_data = {
            'skill_type': 'Web Development',  # Should be normalized
            'clean_content': 'How to build web applications',
            'steps': 'Step 1: Set up environment\nStep 2: Write code\nStep 3: Deploy',  # String format
            'prerequisites': 'HTML, CSS, JavaScript',  # Comma-separated string
            'difficulty_level': 'INTERMEDIATE',  # Wrong case
            'domain': 'Technology',  # Wrong case
            'importance_score': 1.5,  # Should be clamped
            'tools_required': ['VS Code', 'Node.js'],
            'success_indicators': ['App runs successfully'],
            'common_mistakes': ['Forgetting to save files']
        }
        
        original_content = "This is the original dialog content for fallback."
        
        # Test the processing method directly
        processed = await engine._process_procedural_data(raw_data, original_content)
        
        # Assertions
        assert processed['skill_type'] == 'web_development'  # Normalized
        assert len(processed['steps']) == 3  # Parsed from string
        assert len(processed['prerequisites']) == 3  # Parsed from comma-separated
        assert processed['difficulty_level'] == 'intermediate'  # Normalized to valid value
        assert processed['domain'] == 'technology'  # Normalized
        assert processed['importance_score'] == 1.0  # Clamped

    @pytest.mark.asyncio
    async def test_search_methods_error_handling(self, engine):
        """Test error handling in search methods"""
        
        # Mock database error
        engine.db.table.return_value.select.side_effect = Exception("Database error")
        
        # Test all search methods handle errors gracefully
        result1 = await engine.search_procedures_by_domain("user123", "technology")
        assert result1 == []
        
        result2 = await engine.search_procedures_by_skill_type("user123", "deployment")
        assert result2 == []
        
        result3 = await engine.search_procedures_by_difficulty("user123", "advanced")
        assert result3 == []
        
        result4 = await engine.search_procedures_by_success_rate("user123", 0.8)
        assert result4 == []
        
        result5 = await engine.search_procedures_by_prerequisites("user123", "Docker")
        assert result5 == []

    def test_engine_properties(self, engine):
        """Test engine basic properties"""
        assert engine.table_name == "procedural_memories"
        assert engine.memory_type == "procedural"

    @pytest.mark.asyncio
    async def test_extraction_with_complex_steps(self, engine):
        """Test extraction of complex multi-step procedures"""
        
        dialog_content = """
        Human: How do I set up a complete CI/CD pipeline for my React application?
        
        AI: Here's a comprehensive guide:
        
        1. First, set up your Git repository with proper branching strategy
        2. Configure GitHub Actions workflow file in .github/workflows/
        3. Set up testing pipeline with Jest and React Testing Library
        4. Configure build process with webpack optimization
        5. Set up staging environment deployment
        6. Configure production deployment with proper secrets
        7. Add monitoring and rollback capabilities
        
        You'll need Docker, AWS CLI, and knowledge of YAML configuration files.
        """
        
        # Mock complex extraction result
        mock_extraction_result = {
            'success': True,
            'data': {
                'skill_type': 'cicd_setup',
                'clean_content': 'Complete CI/CD pipeline setup for React applications',
                'steps': [
                    {
                        'step_number': 1,
                        'description': 'Set up Git repository with branching strategy',
                        'importance': 'critical',
                        'estimated_time': '30 minutes',
                        'tools_needed': ['Git', 'GitHub']
                    },
                    {
                        'step_number': 2,
                        'description': 'Configure GitHub Actions workflow file',
                        'importance': 'critical',
                        'estimated_time': '45 minutes',
                        'tools_needed': ['YAML editor', 'GitHub']
                    }
                ],
                'prerequisites': ['Git knowledge', 'Docker basics', 'AWS CLI', 'YAML configuration'],
                'difficulty_level': 'advanced',
                'domain': 'technology',
                'importance_score': 0.9,
                'tools_required': ['Docker', 'AWS CLI', 'Git', 'GitHub Actions'],
                'success_indicators': ['Pipeline runs successfully', 'Automated deployments work'],
                'common_mistakes': ['Exposing secrets in workflow files', 'Not testing pipeline thoroughly']
            },
            'confidence': 0.85
        }
        
        engine.text_extractor.extract_key_information.return_value = mock_extraction_result
        engine.store_memory = AsyncMock(return_value=MemoryOperationResult(
            success=True,
            memory_id="complex_proc_id",
            operation="store_procedural_memory",
            message="Complex procedural memory stored successfully"
        ))
        
        # Test
        result = await engine.store_procedural_memory(
            user_id="user123",
            dialog_content=dialog_content
        )
        
        # Assertions
        assert result.success == True
        assert result.memory_id == "complex_proc_id"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])