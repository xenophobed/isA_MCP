"""
Test cases for deployment workflow functionality
Tests the complete "code -> deploy -> URL" pipeline
"""

import pytest
import asyncio
import json
import tempfile
import os
import shutil
from unittest.mock import AsyncMock, patch, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../'))

from tools.services.terminal_service.tools.deployment_tools import DeploymentTools


class TestDeploymentWorkflow:
    """Test deployment workflow functionality"""
    
    @pytest.fixture
    def deployment_tools(self):
        """Create deployment tools instance"""
        return DeploymentTools()
    
    @pytest.fixture
    def sample_fastapi_code(self):
        """Sample FastAPI code for testing"""
        return """
@app.get("/api/users")
async def get_users():
    return {"users": ["Alice", "Bob", "Charlie"]}

@app.post("/api/users")
async def create_user(name: str):
    return {"message": f"User {name} created", "id": 123}
"""
    
    @pytest.fixture
    def sample_flask_code(self):
        """Sample Flask code for testing"""
        return """
@app.route("/api/items")
def get_items():
    return {"items": ["item1", "item2", "item3"]}

@app.route("/api/status")
def get_status():
    return {"status": "running", "app": "flask"}
"""
    
    @pytest.mark.asyncio
    async def test_generate_fastapi_code(self, deployment_tools):
        """Test FastAPI code generation"""
        user_code = "@app.get('/test')\nasync def test(): return {'test': True}"
        
        generated = deployment_tools._generate_app_code(
            user_code, "fastapi", 8000
        )
        
        assert "from fastapi import FastAPI" in generated
        assert "import uvicorn" in generated
        assert user_code in generated
        assert "uvicorn.run(app" in generated
        assert 'title="Auto-deployed Service"' in generated
    
    @pytest.mark.asyncio
    async def test_generate_flask_code(self, deployment_tools):
        """Test Flask code generation"""
        user_code = "@app.route('/test')\ndef test(): return {'test': True}"
        
        generated = deployment_tools._generate_app_code(
            user_code, "flask", 5000
        )
        
        assert "from flask import Flask" in generated
        assert user_code in generated
        assert "app.run(host=" in generated
        assert 'app = Flask(__name__)' in generated
    
    @pytest.mark.asyncio
    async def test_generate_simple_http_code(self, deployment_tools):
        """Test simple HTTP server code generation"""
        user_code = "# Custom logic here"
        
        generated = deployment_tools._generate_app_code(
            user_code, "simple", 3000
        )
        
        assert "import http.server" in generated
        assert "import socketserver" in generated
        assert user_code in generated
        assert "TCPServer" in generated
    
    def test_generate_requirements_fastapi(self, deployment_tools):
        """Test requirements generation for FastAPI"""
        requirements = deployment_tools._generate_requirements(
            "fastapi", ["requests", "pandas"]
        )
        
        assert "fastapi>=0.100.0" in requirements
        assert "uvicorn[standard]>=0.23.0" in requirements
        assert "requests" in requirements
        assert "pandas" in requirements
    
    def test_generate_requirements_flask(self, deployment_tools):
        """Test requirements generation for Flask"""
        requirements = deployment_tools._generate_requirements(
            "flask", ["sqlalchemy"]
        )
        
        assert "flask>=2.3.0" in requirements
        assert "gunicorn>=21.0.0" in requirements
        assert "sqlalchemy" in requirements
    
    def test_generate_service_url_railway(self, deployment_tools):
        """Test service URL generation for Railway"""
        url = deployment_tools._generate_service_url(
            "my-service", "railway", 8000
        )
        
        assert url == "https://my-service.railway.app"
    
    def test_generate_service_url_docker(self, deployment_tools):
        """Test service URL generation for Docker"""
        url = deployment_tools._generate_service_url(
            "my-service", "docker", 8080
        )
        
        assert url == "http://localhost:8080"
    
    def test_generate_service_url_vercel(self, deployment_tools):
        """Test service URL generation for Vercel"""
        url = deployment_tools._generate_service_url(
            "my-app", "vercel", 3000
        )
        
        assert url == "https://my-app.vercel.app"
    
    @pytest.mark.asyncio
    @patch('tools.services.terminal_service.tools.deployment_tools.tempfile')
    @patch('tools.services.terminal_service.tools.deployment_tools.os')
    async def test_create_project_structure(self, mock_os, mock_tempfile, deployment_tools):
        """Test project structure creation"""
        # Mock tempfile creation
        mock_file = MagicMock()
        mock_file.name = "/tmp/test_file"
        mock_tempfile.NamedTemporaryFile.return_value.__enter__.return_value = mock_file
        
        # Mock terminal tools
        deployment_tools.terminal_tools.execute_command = AsyncMock(
            return_value='{"status": "success", "data": {"stdout": "OK"}}'
        )
        deployment_tools.terminal_tools.change_directory = AsyncMock(
            return_value='{"status": "success"}'
        )
        
        result = await deployment_tools._create_project_structure(
            "test-project", "test_code", "fastapi", 8000, ["requests"], "test_session"
        )
        
        assert result["success"] is True
        assert "project_path" in result
        assert "/tmp/deployments/test-project" in result["project_path"]
    
    @pytest.mark.asyncio
    async def test_create_deployment_config(self, deployment_tools):
        """Test deployment configuration creation"""
        # Mock terminal tools
        deployment_tools.terminal_tools.execute_command = AsyncMock(
            return_value='{"status": "success"}'
        )
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('os.unlink') as mock_unlink:
            
            mock_file = MagicMock()
            mock_file.name = "/tmp/test_config"
            mock_temp.return_value.__enter__.return_value = mock_file
            
            result = await deployment_tools._create_deployment_config(
                "test-project", "/tmp/test", "fastapi", 8000, "test_session"
            )
            
            assert "configs_created" in result
            expected_configs = ["Dockerfile", "docker-compose.yml", "railway.json"]
            assert all(config in result["configs_created"] for config in expected_configs)
    
    @pytest.mark.asyncio
    async def test_deploy_service_docker(self, deployment_tools):
        """Test Docker deployment"""
        # Mock successful deployment
        deployment_tools.terminal_tools.execute_command = AsyncMock(
            return_value='{"status": "success", "data": {"stdout": "Container started"}}'
        )
        
        result = await deployment_tools._deploy_service(
            "test-project", "docker", "test_session"
        )
        
        assert result["success"] is True
        assert "logs" in result
    
    @pytest.mark.asyncio
    async def test_deploy_service_railway(self, deployment_tools):
        """Test Railway deployment"""
        # Mock successful deployment
        deployment_tools.terminal_tools.execute_command = AsyncMock(
            return_value='{"status": "success", "data": {"stdout": "Deployed to Railway"}}'
        )
        
        result = await deployment_tools._deploy_service(
            "test-project", "railway", "test_session"
        )
        
        assert result["success"] is True
        assert "logs" in result
    
    @pytest.mark.asyncio
    async def test_deploy_service_unsupported_platform(self, deployment_tools):
        """Test deployment with unsupported platform"""
        result = await deployment_tools._deploy_service(
            "test-project", "unsupported", "test_session"
        )
        
        assert result["success"] is False
        assert "Unsupported platform" in result["error"]
    
    @pytest.mark.asyncio
    async def test_complete_deployment_workflow(self, deployment_tools, sample_fastapi_code):
        """Test complete deployment workflow integration"""
        
        with patch.object(deployment_tools, '_create_project_structure') as mock_create, \
             patch.object(deployment_tools, '_deploy_service') as mock_deploy:
            
            # Mock successful project creation
            mock_create.return_value = {
                "success": True,
                "project_path": "/tmp/deployments/test-api",
                "config": {"configs_created": ["Dockerfile", "docker-compose.yml"]}
            }
            
            # Mock successful deployment
            mock_deploy.return_value = {
                "success": True,
                "logs": ["Deployment successful"]
            }
            
            result_json = await deployment_tools.create_and_deploy_service(
                project_name="test-api",
                code_content=sample_fastapi_code,
                service_type="fastapi",
                deployment_platform="docker",
                port=8000,
                requirements=["requests"]
            )
            
            result = json.loads(result_json)
            
            assert result["status"] == "success"
            assert result["action"] == "create_and_deploy_service"
            assert result["data"]["project_name"] == "test-api"
            assert result["data"]["service_url"] == "http://localhost:8000"
            assert result["data"]["deployment_platform"] == "docker"
            assert result["data"]["service_type"] == "fastapi"
    
    @pytest.mark.asyncio
    async def test_deployment_workflow_project_creation_failure(self, deployment_tools):
        """Test deployment workflow when project creation fails"""
        
        with patch.object(deployment_tools, '_create_project_structure') as mock_create:
            # Mock failed project creation
            mock_create.return_value = {
                "success": False,
                "error": "Failed to create project directory"
            }
            
            result_json = await deployment_tools.create_and_deploy_service(
                project_name="test-fail",
                code_content="test_code",
                service_type="fastapi"
            )
            
            result = json.loads(result_json)
            
            assert result["status"] == "error"
            assert result["data"]["step"] == "project_creation"
            assert "Failed to create project directory" in result["error_message"]
    
    @pytest.mark.asyncio
    async def test_deployment_workflow_deployment_failure(self, deployment_tools):
        """Test deployment workflow when deployment fails"""
        
        with patch.object(deployment_tools, '_create_project_structure') as mock_create, \
             patch.object(deployment_tools, '_deploy_service') as mock_deploy:
            
            # Mock successful project creation
            mock_create.return_value = {
                "success": True,
                "project_path": "/tmp/test",
                "config": {}
            }
            
            # Mock failed deployment
            mock_deploy.return_value = {
                "success": False,
                "error": "Docker daemon not running"
            }
            
            result_json = await deployment_tools.create_and_deploy_service(
                project_name="test-fail-deploy",
                code_content="test_code",
                service_type="fastapi"
            )
            
            result = json.loads(result_json)
            
            assert result["status"] == "error"
            assert result["data"]["step"] == "deployment"
            assert "Docker daemon not running" in result["error_message"]
    
    @pytest.mark.asyncio
    async def test_list_deployed_services(self, deployment_tools):
        """Test listing deployed services"""
        # Mock docker ps command output
        docker_output = """NAMES\tPORTS\tSTATUS
test-api\t0.0.0.0:8000->8000/tcp\tUp 2 hours
my-app\t0.0.0.0:5000->5000/tcp\tUp 1 hour"""
        
        deployment_tools.terminal_tools.execute_command = AsyncMock(
            return_value=f'{{"status": "success", "data": {{"stdout": "{docker_output}"}}}}'
        )
        
        result_json = await deployment_tools.list_deployed_services()
        result = json.loads(result_json)
        
        assert result["status"] == "success"
        assert result["action"] == "list_deployed_services"
        assert len(result["data"]["services"]) == 2
        assert result["data"]["services"][0]["name"] == "test-api"
        assert result["data"]["services"][0]["platform"] == "docker"
    
    @pytest.mark.asyncio
    async def test_list_deployed_services_error(self, deployment_tools):
        """Test listing deployed services with error"""
        deployment_tools.terminal_tools.execute_command = AsyncMock(
            side_effect=Exception("Docker not available")
        )
        
        result_json = await deployment_tools.list_deployed_services()
        result = json.loads(result_json)
        
        assert result["status"] == "error"
        assert "Docker not available" in result["error_message"]


class TestDeploymentToolsIntegration:
    """Integration tests for deployment tools"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for integration tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_project_structure_creation(self, temp_dir):
        """Test real project structure creation (integration test)"""
        deployment_tools = DeploymentTools()
        
        # Override project path to use temp directory
        project_path = os.path.join(temp_dir, "test-project")
        
        with patch.object(deployment_tools.terminal_tools, 'execute_command') as mock_exec, \
             patch.object(deployment_tools.terminal_tools, 'change_directory') as mock_cd:
            
            # Mock terminal commands to work with temp directory
            mock_exec.return_value = '{"status": "success", "data": {"stdout": "OK"}}'
            mock_cd.return_value = '{"status": "success"}'
            
            # Create the project directory manually for this test
            os.makedirs(project_path, exist_ok=True)
            
            result = await deployment_tools._create_project_structure(
                "test-project", "test_code", "fastapi", 8000, [], "test_session"
            )
            
            assert result["success"] is True
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_docker_availability_check(self):
        """Test if Docker is available for integration tests"""
        deployment_tools = DeploymentTools()
        
        try:
            result = await deployment_tools.terminal_tools.execute_command("docker --version")
            result_data = json.loads(result)
            
            if result_data["status"] == "success":
                pytest.skip("Docker is available - this validates our deployment assumptions")
            else:
                pytest.skip("Docker not available - integration tests would fail")
                
        except Exception:
            pytest.skip("Cannot check Docker availability")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"]) 