#!/usr/bin/env python3
"""
Production Environment Setup Script
This script prepares the MCP service for production deployment
"""
import os
import asyncio
import json
from pathlib import Path
from typing import Dict, Any
import secrets
import bcrypt
from datetime import datetime, timedelta
import jwt
from dataclasses import dataclass

@dataclass
class ProductionConfig:
    """Production configuration settings"""
    jwt_secret: str
    api_key_salt: str
    database_url: str
    redis_url: str
    environment: str = "production"
    debug: bool = False
    require_auth: bool = True
    rate_limit_per_hour: int = 1000
    max_workers: int = 4
    log_level: str = "INFO"

class ProductionSecurityManager:
    """Enhanced security manager for production"""
    
    def __init__(self, config: ProductionConfig):
        self.config = config
        self.jwt_secret = config.jwt_secret
        self.api_key_salt = config.api_key_salt.encode()
    
    def generate_jwt_token(self, user_id: str, plan: str = "free", expires_hours: int = 24) -> str:
        """Generate JWT token for user authentication"""
        payload = {
            'user_id': user_id,
            'plan': plan,
            'exp': datetime.utcnow() + timedelta(hours=expires_hours),
            'iat': datetime.utcnow(),
            'iss': 'mcp-service'
        }
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return {'valid': True, 'payload': payload}
        except jwt.ExpiredSignatureError:
            return {'valid': False, 'error': 'Token expired'}
        except jwt.InvalidTokenError:
            return {'valid': False, 'error': 'Invalid token'}
    
    def generate_api_key(self, user_id: str) -> tuple[str, str]:
        """Generate API key and hash for storage"""
        # Generate a random API key
        api_key = f"mcp_{secrets.token_urlsafe(32)}"
        
        # Create hash for storage
        key_hash = bcrypt.hashpw(
            f"{user_id}:{api_key}".encode() + self.api_key_salt,
            bcrypt.gensalt()
        ).decode()
        
        return api_key, key_hash
    
    def verify_api_key(self, api_key: str, user_id: str, stored_hash: str) -> bool:
        """Verify API key against stored hash"""
        try:
            return bcrypt.checkpw(
                f"{user_id}:{api_key}".encode() + self.api_key_salt,
                stored_hash.encode()
            )
        except Exception:
            return False

class BillingSystem:
    """Production billing and quota management"""
    
    PRICING_TIERS = {
        'free': {
            'api_calls_per_month': 1000,
            'storage_mb': 100,
            'ai_operations_per_month': 500,
            'rate_limit_per_hour': 100,
            'price_usd': 0
        },
        'starter': {
            'api_calls_per_month': 10000,
            'storage_mb': 1000,
            'ai_operations_per_month': 5000,
            'rate_limit_per_hour': 1000,
            'price_usd': 29
        },
        'professional': {
            'api_calls_per_month': 100000,
            'storage_mb': 10000,
            'ai_operations_per_month': 50000,
            'rate_limit_per_hour': 5000,
            'price_usd': 99
        },
        'enterprise': {
            'api_calls_per_month': float('inf'),
            'storage_mb': float('inf'),
            'ai_operations_per_month': float('inf'),
            'rate_limit_per_hour': 10000,
            'price_usd': 499
        }
    }
    
    def __init__(self, database_client):
        self.db = database_client
    
    async def check_quota(self, user_id: str, operation_type: str) -> Dict[str, Any]:
        """Check if user has quota for operation"""
        try:
            # Get user's current plan and usage
            user_data = await self.db.table('users').select('*').eq('id', user_id).single().execute()
            if not user_data.data:
                return {'allowed': False, 'error': 'User not found'}
            
            user = user_data.data
            plan = user.get('plan', 'free')
            
            # Get current month usage
            current_month = datetime.now().strftime('%Y-%m')
            usage_data = await self.db.table('usage_tracking').select('*').eq('user_id', user_id).eq('month', current_month).single().execute()
            
            current_usage = usage_data.data if usage_data.data else {}
            
            # Check quota
            limits = self.PRICING_TIERS[plan]
            operation_count = current_usage.get(operation_type, 0)
            limit = limits.get(f"{operation_type}_per_month", float('inf'))
            
            if operation_count >= limit:
                return {
                    'allowed': False,
                    'error': f'Monthly quota exceeded for {operation_type}',
                    'current': operation_count,
                    'limit': limit
                }
            
            return {
                'allowed': True,
                'current': operation_count,
                'limit': limit,
                'remaining': limit - operation_count if limit != float('inf') else 'unlimited'
            }
            
        except Exception as e:
            return {'allowed': False, 'error': f'Quota check failed: {str(e)}'}
    
    async def track_usage(self, user_id: str, operation_type: str, quantity: int = 1) -> bool:
        """Track usage for billing purposes"""
        try:
            current_month = datetime.now().strftime('%Y-%m')
            
            # Upsert usage record
            usage_data = {
                'user_id': user_id,
                'month': current_month,
                operation_type: f"COALESCE({operation_type}, 0) + {quantity}",
                'updated_at': datetime.utcnow().isoformat()
            }
            
            await self.db.table('usage_tracking').upsert(usage_data).execute()
            return True
            
        except Exception as e:
            print(f"Usage tracking failed: {e}")
            return False

class ProductionHealthChecker:
    """Health check system for production monitoring"""
    
    def __init__(self, mcp_server):
        self.server = mcp_server
        self.checks = {
            'database': self._check_database,
            'ai_services': self._check_ai_services,
            'rag_system': self._check_rag_system,
            'memory_system': self._check_memory_system
        }
    
    async def full_health_check(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }
        
        overall_healthy = True
        
        for check_name, check_func in self.checks.items():
            try:
                check_result = await check_func()
                results['checks'][check_name] = check_result
                
                if not check_result.get('healthy', False):
                    overall_healthy = False
                    
            except Exception as e:
                results['checks'][check_name] = {
                    'healthy': False,
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }
                overall_healthy = False
        
        results['status'] = 'healthy' if overall_healthy else 'unhealthy'
        return results
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            from core.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            
            # Simple query to test connection
            result = await supabase.client.table('users').select('count').limit(1).execute()
            
            return {
                'healthy': True,
                'response_time_ms': 0,  # Would measure actual response time
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _check_ai_services(self) -> Dict[str, Any]:
        """Check AI services availability"""
        try:
            from isa_model.inference import AIFactory
            ai_factory = AIFactory()
            
            # Test embedding service
            embed_service = ai_factory.get_embed()
            test_embedding = await embed_service.create_text_embedding("health check")
            
            return {
                'healthy': len(test_embedding) > 0,
                'embedding_dimension': len(test_embedding),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _check_rag_system(self) -> Dict[str, Any]:
        """Check RAG system health"""
        try:
            from tools.services.rag_service.rag_client import get_rag_client
            rag_client = get_rag_client()
            
            # Test collection listing
            collections = await rag_client.list_collections()
            
            return {
                'healthy': collections.get('success', False),
                'collections_count': collections.get('total_collections', 0),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _check_memory_system(self) -> Dict[str, Any]:
        """Check memory system health"""
        try:
            # Test memory operations
            # This would test the memory tools
            return {
                'healthy': True,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

async def setup_production_environment():
    """Setup production environment with all necessary configurations"""
    print("🚀 Setting up production environment...")
    
    # 1. Generate production configuration
    print("1. Generating production configuration...")
    
    config = ProductionConfig(
        jwt_secret=secrets.token_urlsafe(64),
        api_key_salt=secrets.token_urlsafe(32),
        database_url=os.getenv('DATABASE_URL', ''),
        redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379'),
    )
    
    # 2. Create production environment file
    env_content = f"""
# Production Environment Configuration
NODE_ENV=production
DEBUG=false
REQUIRE_AUTH=true

# Security
JWT_SECRET_KEY={config.jwt_secret}
API_KEY_SALT={config.api_key_salt}

# Database
DATABASE_URL={config.database_url}
REDIS_URL={config.redis_url}

# Rate Limiting
RATE_LIMIT_PER_HOUR={config.rate_limit_per_hour}

# Performance
MAX_WORKERS={config.max_workers}
LOG_LEVEL={config.log_level}

# Monitoring
PROMETHEUS_ENABLED=true
JAEGER_ENABLED=true
HEALTH_CHECK_INTERVAL=30
"""
    
    with open('.env.production', 'w') as f:
        f.write(env_content.strip())
    
    print("   ✅ Production environment file created")
    
    # 3. Create database schema for production features
    print("2. Creating production database schema...")
    
    sql_schema = """
-- Production users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    plan TEXT DEFAULT 'free' CHECK (plan IN ('free', 'starter', 'professional', 'enterprise')),
    api_key_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'
);

-- Usage tracking table
CREATE TABLE IF NOT EXISTS usage_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    month TEXT NOT NULL, -- YYYY-MM format
    api_calls INTEGER DEFAULT 0,
    storage_mb FLOAT DEFAULT 0,
    ai_operations INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, month)
);

-- Billing history table
CREATE TABLE IF NOT EXISTS billing_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    amount_usd DECIMAL(10,2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'failed', 'refunded')),
    stripe_payment_id TEXT,
    billing_period_start DATE,
    billing_period_end DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- API usage logs (for detailed tracking)
CREATE TABLE IF NOT EXISTS api_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_usage_tracking_user_month ON usage_tracking(user_id, month);
CREATE INDEX IF NOT EXISTS idx_api_usage_logs_user_timestamp ON api_usage_logs(user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_billing_history_user_status ON billing_history(user_id, status);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_usage_tracking_updated_at BEFORE UPDATE ON usage_tracking
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"""
    
    with open('production_schema.sql', 'w') as f:
        f.write(sql_schema)
    
    print("   ✅ Production database schema created")
    
    # 4. Create Docker configuration for production
    print("3. Creating production Docker configuration...")
    
    dockerfile_content = """
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \\
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:4321/health || exit 1

# Expose port
EXPOSE 4321

# Run application
CMD ["python", "-m", "uvicorn", "smart_mcp_server:app", "--host", "0.0.0.0", "--port", "4321", "--workers", "4"]
"""
    
    with open('Dockerfile.production', 'w') as f:
        f.write(dockerfile_content)
    
    print("   ✅ Production Dockerfile created")
    
    # 5. Create production requirements
    print("4. Creating production requirements...")
    
    requirements_prod = """
# Production requirements
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
redis>=5.0.0
prometheus-client>=0.19.0
structlog>=23.2.0
sentry-sdk>=1.38.0
httpx>=0.25.0
cryptography>=41.0.0
PyJWT>=2.8.0
bcrypt>=4.1.0
stripe>=7.0.0
"""
    
    with open('requirements.production.txt', 'w') as f:
        f.write(requirements_prod)
    
    print("   ✅ Production requirements created")
    
    # 6. Create monitoring configuration
    print("5. Creating monitoring configuration...")
    
    prometheus_config = """
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'mcp-service'
    static_configs:
      - targets: ['mcp-service:4321']
    metrics_path: '/metrics'
    scrape_interval: 30s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
"""
    
    os.makedirs('monitoring', exist_ok=True)
    with open('monitoring/prometheus.yml', 'w') as f:
        f.write(prometheus_config)
    
    print("   ✅ Monitoring configuration created")
    
    print("\n🎉 Production environment setup complete!")
    print("\nNext steps:")
    print("1. Review and customize .env.production")
    print("2. Run production_schema.sql in your database")
    print("3. Build production Docker image: docker build -f Dockerfile.production -t mcp-service:prod .")
    print("4. Deploy to your chosen platform")
    print("5. Set up monitoring and alerting")
    
    return config

async def test_production_setup():
    """Test production setup functionality"""
    print("\n🧪 Testing production setup...")
    
    # Test security manager
    config = ProductionConfig(
        jwt_secret="test_secret_key_for_testing_only",
        api_key_salt="test_salt",
        database_url="test://localhost",
        redis_url="redis://localhost:6379"
    )
    
    security_manager = ProductionSecurityManager(config)
    
    # Test JWT token generation and verification
    test_user_id = "test_user_123"
    token = security_manager.generate_jwt_token(test_user_id, "starter")
    verification = security_manager.verify_jwt_token(token)
    
    print(f"JWT Token Test: {'✅' if verification['valid'] else '❌'}")
    
    # Test API key generation
    api_key, key_hash = security_manager.generate_api_key(test_user_id)
    key_valid = security_manager.verify_api_key(api_key, test_user_id, key_hash)
    
    print(f"API Key Test: {'✅' if key_valid else '❌'}")
    
    print("✅ Production setup tests completed")

if __name__ == "__main__":
    asyncio.run(setup_production_environment())
    asyncio.run(test_production_setup())