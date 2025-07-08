"""
ISA Model Client Manager
Simple client manager using existing ISA Model config system
"""
import os
from typing import Optional
from isa_model.client import ISAModelClient
from core.logging import get_logger

logger = get_logger(__name__)

class ISAClientManager:
    """ISA Model客户端管理器 - Simple approach"""
    
    def __init__(self):
        self._client: Optional[ISAModelClient] = None
        self._initialized = False
    
    def get_client(self) -> ISAModelClient:
        """获取客户端实例，自动初始化"""
        if not self._initialized:
            self._initialize_client()
        return self._client
    
    def _initialize_client(self):
        """根据环境变量初始化客户端"""
        # Simple approach - just use ISAModelClient directly
        try:
            self._client = ISAModelClient()
            logger.info("✅ ISA Client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize ISA Client: {e}")
            raise
        
        self._initialized = True
    
    async def health_check(self):
        """健康检查"""
        client = self.get_client()
        return await client.health_check()
    
    def clear_cache(self):
        """清除缓存"""
        if self._client:
            self._client.clear_cache()
    
    async def invoke(self, input_data, task, service_type, model=None, provider=None, **kwargs):
        """Forward invoke calls to the wrapped ISAModelClient"""
        client = self.get_client()
        return await client.invoke(input_data, task, service_type, model, provider, **kwargs)
    
    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.close()

# 全局实例
_isa_manager = ISAClientManager()

def get_isa_client():
    """获取ISA Manager（支持HTTP fallback）"""
    return _isa_manager

async def isa_health_check():
    """ISA健康检查"""
    return await _isa_manager.health_check()

def clear_isa_cache():
    """清除ISA缓存"""
    _isa_manager.clear_cache()

def extract_isa_response_with_billing(isa_response):
    """
    从ISA响应中提取结果和billing信息
    返回格式: (result_data, billing_info)
    """
    if not isa_response:
        return None, None
    
    # 提取结果数据
    result_data = None
    if isa_response.get('success'):
        result_data = isa_response.get('result')
    
    # 提取billing信息
    billing_info = None
    metadata = isa_response.get('metadata', {})
    if 'billing' in metadata:
        billing_info = metadata['billing']
    
    return result_data, billing_info