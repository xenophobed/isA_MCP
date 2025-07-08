# Developer Guide

Welcome to the isA_MCP Developer Guide! This comprehensive resource will help you understand, extend, and contribute to the Smart MCP Server.

## 🎯 Development Overview

isA_MCP is built with modern Python architecture focusing on:
- **Modular Design**: Clean separation between services, tools, and core components
- **AI Integration**: Seamless integration with LLM APIs and AI services
- **Enterprise Features**: Security, monitoring, and production-ready deployment
- **Extensibility**: Easy addition of new services and tools

## 🏗️ Project Structure

```
isA_MCP/
├── 📁 core/                          # Core framework components
│   ├── auto_discovery.py             # Tool and service discovery
│   ├── config.py                     # Centralized configuration
│   ├── isa_client.py                 # AI service integration
│   ├── security.py                   # Authentication & authorization
│   └── database/                     # Database management
├── 📁 tools/                         # MCP tools and services
│   ├── base_tool.py                  # Base tool class
│   ├── base_service.py               # Base service class
│   ├── services/                     # Service implementations
│   │   ├── data_analytics_service/   # Data analytics pipeline
│   │   ├── graph_analytics_service/  # Graph analytics & Neo4j
│   │   ├── web_services/             # Web scraping platform
│   │   └── ...                       # Other services
│   └── *.py                         # Individual tool files
├── 📁 deployment/                    # Deployment configurations
│   ├── dev/                         # Development environment
│   ├── production/                  # Production Docker setup
│   └── scripts/                     # Deployment scripts
├── 📁 docs/                         # Documentation (GitBook format)
├── 📁 tests/                        # Comprehensive test suite
└── smart_mcp_server.py              # Main server entry point
```

## 🔧 Development Setup

### 1. Environment Setup
```bash
# Clone repository
git clone <repository_url>
cd isA_MCP

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup pre-commit hooks
pre-commit install
```

### 2. Configuration
```bash
# Copy development environment
cp deployment/dev/.env.example .env

# Edit configuration
nano .env

# Essential settings for development
ENV=development
DEBUG=true
MCP_PORT=4321
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
```

### 3. Database Setup
```bash
# Start PostgreSQL with Docker
docker-compose up -d postgres

# Run migrations
python -c "
from core.database.migration_manager import MigrationManager
manager = MigrationManager()
manager.run_migrations()
"
```

### 4. Development Server
```bash
# Start development server
python smart_mcp_server.py

# Or with auto-reload
python -m uvicorn smart_mcp_server:app --reload --port 4321
```

## 🧩 Core Architecture

### Base Classes Hierarchy

```python
# Tool Development
class BaseTool:
    """Base class for all MCP tools"""
    def __init__(self):
        self.isa_client = get_isa_client()
        self.security_manager = get_security_manager()
        self.billing_info = []
    
    async def call_isa_with_billing(self, ...):
        """Unified ISA API calling with cost tracking"""
    
    def create_response(self, ...):
        """Standardized response format"""

# Service Development  
class BaseService:
    """Base class for complex services"""
    def __init__(self, service_name: str):
        super().__init__(service_name)
        self.operation_history = []
    
    async def call_isa_with_billing(self, ...):
        """Service-level ISA integration"""
    
    def create_service_response(self, ...):
        """Service response with billing"""
```

### Configuration System
```python
# Centralized configuration management
from core.config import get_settings

settings = get_settings()

# Access service configurations
data_config = settings.data_analytics
graph_config = settings.graph_analytics
web_config = settings.web_services

# Environment-based loading
# deployment/dev/.env -> core/config.py -> services
```

### Auto Discovery System
```python
class AutoDiscovery:
    """Automatic tool and service discovery"""
    
    async def discover_tools(self) -> Dict[str, ToolMetadata]:
        """Scan codebase for MCP tools"""
        # 1. Scan tools/ directory
        # 2. Extract metadata from docstrings
        # 3. Generate embeddings for semantic search
        # 4. Register with MCP server
    
    async def discover_services(self) -> Dict[str, ServiceMetadata]:
        """Discover available services"""
        # 1. Find service classes
        # 2. Extract capabilities
        # 3. Build service registry
```

## 🛠️ Creating New Tools

### 1. Simple Tool Example
```python
# tools/weather_tools.py
from tools.base_tool import BaseTool

class WeatherTools(BaseTool):
    def __init__(self):
        super().__init__()
    
    def register_all_tools(self, mcp):
        """Register tools with MCP server"""
        
        @mcp.tool()
        async def get_weather(city: str) -> str:
            """
            Get current weather for a city
            
            Args:
                city: City name to get weather for
                
            Returns:
                Weather information in JSON format
            """
            try:
                # Tool implementation
                weather_data = await self._fetch_weather(city)
                
                return self.create_response(
                    status="success",
                    action="get_weather",
                    data={"weather": weather_data, "city": city}
                )
                
            except Exception as e:
                return self.create_response(
                    status="error", 
                    action="get_weather",
                    data={},
                    error_message=str(e)
                )
    
    async def _fetch_weather(self, city: str) -> dict:
        """Implementation details"""
        # Actual weather API integration
        pass
```

### 2. Advanced Tool with AI Integration
```python
# tools/analysis_tools.py
from tools.base_tool import BaseTool

class AnalysisTools(BaseTool):
    def register_all_tools(self, mcp):
        
        @mcp.tool()
        async def analyze_sentiment(text: str, detailed: bool = False) -> str:
            """
            Analyze sentiment of text using AI
            
            Args:
                text: Text to analyze
                detailed: Return detailed analysis
                
            Returns:
                Sentiment analysis results
            """
            try:
                # Use ISA client for AI processing
                result, billing = await self.call_isa_with_billing(
                    input_data=f"Analyze the sentiment of this text: {text}",
                    task="chat",
                    service_type="text",
                    parameters={
                        "max_tokens": 500,
                        "temperature": 0.1
                    }
                )
                
                return self.create_response(
                    status="success",
                    action="analyze_sentiment", 
                    data={
                        "text": text,
                        "sentiment": result,
                        "detailed": detailed
                    }
                )
                
            except Exception as e:
                return self.create_response(
                    status="error",
                    action="analyze_sentiment",
                    data={},
                    error_message=str(e)
                )
```

### 3. Tool Registration
```python
# smart_mcp_server.py
from tools.weather_tools import WeatherTools
from tools.analysis_tools import AnalysisTools

# Register tools
weather = WeatherTools()
weather.register_all_tools(mcp)

analysis = AnalysisTools() 
analysis.register_all_tools(mcp)
```

## 🔧 Creating New Services

### 1. Service Structure
```python
# tools/services/my_service/
├── __init__.py
├── core/                    # Core service logic
│   ├── __init__.py
│   ├── processor.py         # Main processing logic
│   └── validator.py         # Input validation
├── services/                # Sub-services
│   ├── __init__.py
│   ├── api_client.py        # External API integration
│   └── data_manager.py      # Data management
├── utils/                   # Utilities
│   ├── __init__.py
│   ├── helpers.py           # Helper functions
│   └── constants.py         # Service constants
└── adapters/                # External integrations
    ├── __init__.py
    └── database_adapter.py   # Database integration
```

### 2. Service Implementation
```python
# tools/services/my_service/core/processor.py
from tools.base_service import BaseService
from core.config import get_settings

class MyServiceProcessor(BaseService):
    """Main service processor"""
    
    def __init__(self):
        super().__init__("my_service")
        self.settings = get_settings()
        
    async def process_data(self, input_data: dict) -> dict:
        """Main processing method"""
        try:
            # Validate input
            validated_data = self._validate_input(input_data)
            
            # Process with AI if needed
            if self._needs_ai_processing(validated_data):
                result, billing = await self.call_isa_with_billing(
                    input_data=validated_data,
                    task="chat",
                    service_type="text",
                    operation_name="data_processing"
                )
            else:
                result = self._process_locally(validated_data)
            
            return self.create_service_response(
                status="success",
                operation="process_data",
                data={"result": result}
            )
            
        except Exception as e:
            return self.create_service_response(
                status="error",
                operation="process_data", 
                data={},
                error_message=str(e)
            )
    
    def _validate_input(self, data: dict) -> dict:
        """Input validation logic"""
        pass
    
    def _needs_ai_processing(self, data: dict) -> bool:
        """Determine if AI processing is needed"""
        pass
    
    def _process_locally(self, data: dict) -> dict:
        """Local processing without AI"""
        pass
```

### 3. Service Tools Integration
```python
# tools/my_service_tools.py
from tools.base_tool import BaseTool
from tools.services.my_service.core.processor import MyServiceProcessor

class MyServiceTools(BaseTool):
    def __init__(self):
        super().__init__()
        self.processor = MyServiceProcessor()
    
    def register_all_tools(self, mcp):
        
        @mcp.tool()
        async def process_my_data(data: dict, options: dict = None) -> str:
            """
            Process data using MyService
            
            Args:
                data: Input data to process
                options: Processing options
                
            Returns:
                Processing results
            """
            try:
                result = await self.processor.process_data({
                    "data": data,
                    "options": options or {}
                })
                
                return result
                
            except Exception as e:
                return self.create_response(
                    status="error",
                    action="process_my_data",
                    data={},
                    error_message=str(e)
                )
```

## 🔐 Security Implementation

### Authentication & Authorization
```python
# core/security.py extension
class SecurityManager:
    def __init__(self):
        self.authorization_cache = {}
        self.audit_logger = AuditLogger()
    
    async def authorize_tool(self, tool_name: str, user_context: dict) -> bool:
        """Tool-level authorization"""
        security_level = self.get_tool_security_level(tool_name)
        
        if security_level == "LOW":
            return True
        elif security_level == "MEDIUM":
            return await self._request_user_approval(tool_name, user_context)
        elif security_level == "HIGH":
            return await self._require_admin_approval(tool_name, user_context)
    
    async def _request_user_approval(self, tool_name: str, context: dict) -> bool:
        """Request user approval for medium security tools"""
        # Implementation for user approval workflow
        pass
```

### Audit Logging
```python
# core/monitoring.py
class AuditLogger:
    async def log_tool_execution(self, 
                                tool_name: str,
                                user_id: str, 
                                parameters: dict,
                                result: dict,
                                duration: float):
        """Log tool execution for audit purposes"""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "user_id": user_id,
            "parameters": self._sanitize_parameters(parameters),
            "success": result.get("status") == "success",
            "duration_ms": duration * 1000,
            "cost_usd": result.get("billing", {}).get("total_cost_usd", 0)
        }
        
        await self._store_audit_entry(audit_entry)
```

## 🧪 Testing Strategy

### 1. Unit Tests
```python
# tests/unit/test_my_service.py
import pytest
from unittest.mock import Mock, patch
from tools.services.my_service.core.processor import MyServiceProcessor

class TestMyServiceProcessor:
    @pytest.fixture
    def processor(self):
        return MyServiceProcessor()
    
    @pytest.mark.asyncio
    async def test_process_data_success(self, processor):
        """Test successful data processing"""
        input_data = {"text": "test input", "type": "analysis"}
        
        with patch.object(processor, 'call_isa_with_billing') as mock_isa:
            mock_isa.return_value = ("processed result", {"cost_usd": 0.01})
            
            result = await processor.process_data(input_data)
            
            assert result["status"] == "success"
            assert "result" in result["data"]
            mock_isa.assert_called_once()
    
    def test_validate_input(self, processor):
        """Test input validation"""
        valid_input = {"text": "test", "type": "analysis"}
        result = processor._validate_input(valid_input)
        assert result == valid_input
        
        invalid_input = {"invalid": "data"}
        with pytest.raises(ValueError):
            processor._validate_input(invalid_input)
```

### 2. Integration Tests
```python
# tests/integration/test_my_service_integration.py
import pytest
from tests.integration.base import IntegrationTestBase

class TestMyServiceIntegration(IntegrationTestBase):
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete service workflow"""
        # Test data
        input_data = {"text": "Complex text to process"}
        
        # Call tool through MCP client
        result = await self.mcp_client.call_tool("process_my_data", input_data)
        
        # Validate response
        assert result["status"] == "success"
        assert "billing" in result
        assert result["billing"]["total_cost_usd"] > 0
        
        # Verify audit logging
        audit_logs = await self.get_audit_logs(tool_name="process_my_data")
        assert len(audit_logs) == 1
        assert audit_logs[0]["success"] is True
```

### 3. Performance Tests
```python
# tests/performance/test_my_service_performance.py
import pytest
import asyncio
from time import time

class TestMyServicePerformance:
    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """Test service under concurrent load"""
        input_data = {"text": "test input"}
        
        start_time = time()
        
        # Run 10 concurrent requests
        tasks = [
            self.client.call_tool("process_my_data", input_data)
            for _ in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time()
        duration = end_time - start_time
        
        # Validate all requests succeeded
        assert all(r["status"] == "success" for r in results)
        
        # Validate performance (should complete within 5 seconds)
        assert duration < 5.0
        
        # Calculate throughput
        throughput = len(results) / duration
        assert throughput > 2.0  # At least 2 requests per second
```

## 📊 Performance Optimization

### 1. Caching Strategy
```python
# core/cache.py
from typing import Any, Optional
import redis
import json
from datetime import timedelta

class CacheManager:
    def __init__(self):
        self.redis_client = redis.Redis.from_url(settings.redis_url)
    
    async def get_cached_result(self, key: str) -> Optional[Any]:
        """Get cached result"""
        try:
            cached = self.redis_client.get(key)
            return json.loads(cached) if cached else None
        except Exception:
            return None
    
    async def cache_result(self, key: str, result: Any, ttl: int = 3600):
        """Cache result with TTL"""
        try:
            self.redis_client.setex(
                key, 
                ttl, 
                json.dumps(result, default=str)
            )
        except Exception:
            pass  # Fail silently for cache errors

# Usage in services
class OptimizedService(BaseService):
    def __init__(self):
        super().__init__()
        self.cache = CacheManager()
    
    async def expensive_operation(self, input_data: dict) -> dict:
        """Expensive operation with caching"""
        cache_key = f"expensive_op:{hash(str(input_data))}"
        
        # Try cache first
        cached_result = await self.cache.get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Perform operation
        result = await self._perform_expensive_operation(input_data)
        
        # Cache result
        await self.cache.cache_result(cache_key, result, ttl=3600)
        
        return result
```

### 2. Async Optimization
```python
# Efficient concurrent processing
import asyncio
from asyncio import Semaphore

class AsyncOptimizedService:
    def __init__(self, max_concurrent: int = 5):
        self.semaphore = Semaphore(max_concurrent)
    
    async def process_batch(self, items: List[dict]) -> List[dict]:
        """Process multiple items concurrently"""
        async def process_item(item: dict) -> dict:
            async with self.semaphore:
                return await self._process_single_item(item)
        
        # Process all items concurrently with rate limiting
        tasks = [process_item(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        successful_results = []
        for result in results:
            if isinstance(result, Exception):
                # Log error but continue processing
                logger.error(f"Processing failed: {result}")
            else:
                successful_results.append(result)
        
        return successful_results
```

### 3. Memory Management
```python
# Memory-efficient processing for large datasets
import gc
from typing import Generator

class MemoryEfficientProcessor:
    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size
    
    def process_large_dataset(self, data_source) -> Generator[dict, None, None]:
        """Process large datasets in chunks"""
        chunk = []
        
        for item in data_source:
            chunk.append(item)
            
            if len(chunk) >= self.chunk_size:
                # Process chunk
                yield self._process_chunk(chunk)
                
                # Clear chunk and force garbage collection
                chunk.clear()
                gc.collect()
        
        # Process remaining items
        if chunk:
            yield self._process_chunk(chunk)
    
    def _process_chunk(self, chunk: List[dict]) -> dict:
        """Process a single chunk of data"""
        # Implementation
        pass
```

## 🔧 Configuration Management

### 1. Environment-Specific Configuration
```python
# core/config.py extensions
@dataclass
class MyServiceSettings:
    """Configuration for MyService"""
    api_key: Optional[str] = None
    endpoint_url: str = "https://api.example.com"
    timeout_seconds: int = 30
    max_retries: int = 3
    cache_ttl: int = 3600
    debug_mode: bool = False

# Add to main MCPSettings
@dataclass 
class MCPSettings:
    # ... existing settings ...
    my_service: MyServiceSettings = field(default_factory=MyServiceSettings)
    
    def load_from_env(self):
        # ... existing loading ...
        
        # Load MyService settings
        self.my_service.api_key = os.getenv("MY_SERVICE_API_KEY")
        self.my_service.endpoint_url = os.getenv("MY_SERVICE_ENDPOINT", self.my_service.endpoint_url)
        self.my_service.timeout_seconds = int(os.getenv("MY_SERVICE_TIMEOUT", str(self.my_service.timeout_seconds)))
        
        return self
```

### 2. Service Configuration Access
```python
# In your service
from core.config import get_settings

class MyService(BaseService):
    def __init__(self):
        super().__init__("my_service")
        self.config = get_settings().my_service
        
    async def make_api_call(self, data: dict) -> dict:
        """Make API call using configured settings"""
        timeout = self.config.timeout_seconds
        endpoint = self.config.endpoint_url
        api_key = self.config.api_key
        
        # Use configuration in API call
        pass
```

## 📚 Documentation Standards

### 1. Docstring Format
```python
def my_function(param1: str, param2: int = 10) -> dict:
    """
    Brief description of the function.
    
    Longer description if needed. Explain the purpose,
    algorithm, or any important details.
    
    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2 with default value
        
    Returns:
        Description of return value and its structure
        
    Raises:
        ValueError: When param1 is empty
        ConnectionError: When API call fails
        
    Example:
        >>> result = my_function("test", 20)
        >>> print(result["status"])
        success
    """
```

### 2. Service Documentation
```python
class MyService(BaseService):
    """
    MyService provides advanced data processing capabilities.
    
    This service integrates with external APIs to process data
    and provides caching, error handling, and performance optimization.
    
    Configuration:
        - MY_SERVICE_API_KEY: Required API key
        - MY_SERVICE_ENDPOINT: API endpoint URL  
        - MY_SERVICE_TIMEOUT: Request timeout in seconds
        
    Features:
        - Async processing with rate limiting
        - Automatic retry with exponential backoff
        - Result caching with configurable TTL
        - Comprehensive error handling
        
    Example:
        service = MyService()
        result = await service.process_data({"text": "input"})
    """
```

## 🚀 Deployment Best Practices

### 1. Docker Integration
```dockerfile
# Custom service Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install service-specific dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy service code
COPY tools/services/my_service/ ./tools/services/my_service/

# Expose ports if needed
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "tools.services.my_service"]
```

### 2. Environment Configuration
```yaml
# docker-compose.yml extension
services:
  my-service:
    build: .
    environment:
      - MY_SERVICE_API_KEY=${MY_SERVICE_API_KEY}
      - MY_SERVICE_ENDPOINT=${MY_SERVICE_ENDPOINT}
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - postgres
      - redis
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

---

**Next Sections:**
- [Project Structure](project-structure.md) - Detailed codebase organization
- [Code Standards](code-standards.md) - Coding conventions and style guide
- [Testing](testing.md) - Comprehensive testing strategies
- [Contributing](contributing.md) - Contribution guidelines and processes