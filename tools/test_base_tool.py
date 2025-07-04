#!/usr/bin/env python
"""
Test Tool for Base Tool Implementation
测试base_tool的功能，包括billing信息返回
"""
import json
from datetime import datetime
from typing import Dict, Any
from tools.base_tool import BaseTool

class TestTool(BaseTool):
    """测试工具类，继承自BaseTool"""
    
    def __init__(self):
        super().__init__()
    
    async def test_simple_response(self, message: str, user_id: str = "default") -> str:
        """
        测试简单响应，不使用ISA客户端
        
        Args:
            message: 测试消息
            user_id: 用户ID
            
        Returns:
            JSON格式的响应
        """
        response = {
            "status": "success",
            "action": "test_simple_response",
            "data": {
                "message": f"Hello {message}!",
                "user_id": user_id,
                "test_type": "simple"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(response, ensure_ascii=False)
    
    async def test_isa_client_call(self, message: str, user_id: str = "default") -> str:
        """
        测试ISA客户端调用和billing信息
        
        Args:
            message: 要处理的消息
            user_id: 用户ID
            
        Returns:
            JSON格式的响应，包含billing信息
        """
        try:
            # 使用ISA客户端处理消息
            result_data, billing_info = await self.call_isa_with_billing(
                input_data=[{"role": "user", "content": message}],
                task="chat",
                service_type="text"
            )
            
            response = {
                "status": "success",
                "action": "test_isa_client_call",
                "data": {
                    "isa_response": result_data,
                    "user_id": user_id,
                    "test_type": "isa_client"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            return json.dumps(response, ensure_ascii=False)
            
        except Exception as e:
            error_response = {
                "status": "error",
                "action": "test_isa_client_call",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            return json.dumps(error_response, ensure_ascii=False)
    
    async def test_embedding_call(self, text: str, user_id: str = "default") -> str:
        """
        测试embedding调用和billing信息
        
        Args:
            text: 要生成embedding的文本
            user_id: 用户ID
            
        Returns:
            JSON格式的响应，包含billing信息
        """
        try:
            # 使用ISA客户端生成embedding
            embedding_data, billing_info = await self.call_isa_with_billing(
                input_data=text,
                task="embed",
                service_type="embedding"
            )
            
            response = {
                "status": "success",
                "action": "test_embedding_call",
                "data": {
                    "embedding_length": len(embedding_data) if embedding_data else 0,
                    "text": text,
                    "user_id": user_id,
                    "test_type": "embedding"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            return json.dumps(response, ensure_ascii=False)
            
        except Exception as e:
            error_response = {
                "status": "error",
                "action": "test_embedding_call",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            return json.dumps(error_response, ensure_ascii=False)
    
    def register_all_tools(self, mcp):
        """注册所有测试工具"""
        
        # 注册简单响应测试
        self.register_tool(
            mcp,
            self.test_simple_response,
            name="test_simple_response"
        )
        
        # 注册ISA客户端测试
        self.register_tool(
            mcp,
            self.test_isa_client_call,
            name="test_isa_client_call"
        )
        
        # 注册embedding测试
        self.register_tool(
            mcp,
            self.test_embedding_call,
            name="test_embedding_call"
        )

# 创建全局实例
test_tool = TestTool()

def register_test_base_tool(mcp):
    """注册测试工具到MCP服务器"""
    test_tool.register_all_tools(mcp)