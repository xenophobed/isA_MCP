"""
Base Tool Class for ISA MCP Tools
统一处理ISA客户端调用、billing信息返回和工具注册
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Callable
import logging
from isa_model.client import ISAModelClient

logger = logging.getLogger(__name__)

class BaseTool:
    """基础工具类，提供统一的ISA客户端调用和billing信息处理"""
    
    def __init__(self):
        self._isa_client = None
        self.billing_info = []
        self._security_manager = None
        self.registered_tools = []
    
    @property
    def isa_client(self):
        """延迟初始化ISA客户端"""
        if self._isa_client is None:
            from core.isa_client_factory import get_isa_client
            self._isa_client = get_isa_client()
        return self._isa_client
    
    @property 
    def security_manager(self):
        """Simple security manager placeholder"""
        if self._security_manager is None:
            class SimpleSecurityManager:
                def security_check(self, func):
                    return func
            self._security_manager = SimpleSecurityManager()
        return self._security_manager
    
    async def call_isa_with_billing(
        self,
        input_data: Union[str, List[Dict], Dict],
        task: str,
        service_type: str,
        parameters: Optional[Dict] = None
    ) -> tuple[Any, Dict]:
        """
        调用ISA客户端并返回结果和billing信息
        
        Args:
            input_data: 输入数据
            task: 任务类型 ("chat", "embed", "generate_image", "image_to_image")
            service_type: 服务类型 ("text", "embedding", "image")
            parameters: 额外参数
            
        Returns:
            tuple: (result_data, billing_info)
        """
        try:
            # 调用ISA客户端
            isa_response = await self.isa_client.invoke(
                input_data=input_data,
                task=task,
                service_type=service_type,
                parameters=parameters or {}
            )
            
            # 提取结果和billing信息
            result_data = isa_response.get('result', {})
            billing_info = isa_response.get('billing', {})
            
            # 记录billing信息
            if billing_info:
                self.billing_info.append(billing_info)
                logger.info(f"💰 ISA API cost: ${billing_info.get('cost_usd', 0.0):.6f}")
            
            if not isa_response.get('success'):
                raise Exception(f"ISA API call failed: {isa_response.get('error', 'Unknown error')}")
            
            return result_data, billing_info
            
        except Exception as e:
            logger.error(f"ISA API call failed: {e}")
            raise
    
    def create_response(
        self,
        status: str,
        action: str,
        data: Dict[str, Any],
        error_message: Optional[str] = None
    ) -> str:
        """
        创建统一格式的响应，包含billing信息
        
        Args:
            status: 状态 ("success" or "error")
            action: 操作名称
            data: 响应数据
            error_message: 错误消息（可选）
            
        Returns:
            str: JSON格式的响应
        """
        response = {
            "status": status,
            "action": action,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # 添加billing信息
        if self.billing_info:
            # 计算总费用
            total_cost = sum(b.get('cost_usd', 0.0) for b in self.billing_info)
            
            response["billing"] = {
                "total_cost_usd": total_cost,
                "operations": self.billing_info,
                "currency": "USD"
            }
        
        # 添加错误信息
        if error_message:
            response["error"] = error_message
        
        return json.dumps(response, ensure_ascii=False)
    
    def reset_billing(self):
        """重置billing信息"""
        self.billing_info = []
    
    def register_tool(self, mcp, func: Callable, **kwargs):
        """
        注册工具到MCP服务器，自动应用安全检查和billing处理
        
        Args:
            mcp: MCP服务器实例
            func: 工具函数
            **kwargs: 传递给@mcp.tool()的额外参数
        """
        # 包装函数以添加billing处理
        async def wrapped_func(*args, **kwargs):
            # 重置billing信息
            self.reset_billing()
            
            try:
                # 调用原始函数
                result = await func(*args, **kwargs)
                
                # 如果返回的是字符串，尝试解析为JSON并添加billing
                if isinstance(result, str):
                    try:
                        result_dict = json.loads(result)
                        # 添加billing信息
                        if self.billing_info:
                            total_cost = sum(b.get('cost_usd', 0.0) for b in self.billing_info)
                            result_dict["billing"] = {
                                "total_cost_usd": total_cost,
                                "operations": self.billing_info,
                                "currency": "USD"
                            }
                        return json.dumps(result_dict, ensure_ascii=False)
                    except json.JSONDecodeError:
                        # 如果不是JSON，直接返回
                        return result
                else:
                    return result
                    
            except Exception as e:
                # 创建错误响应
                error_response = {
                    "status": "error",
                    "action": func.__name__,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                
                # 添加billing信息（即使出错也要记录已产生的费用）
                if self.billing_info:
                    total_cost = sum(b.get('cost_usd', 0.0) for b in self.billing_info)
                    error_response["billing"] = {
                        "total_cost_usd": total_cost,
                        "operations": self.billing_info,
                        "currency": "USD"
                    }
                
                return json.dumps(error_response, ensure_ascii=False)
        
        # 应用装饰器
        decorated_func = self.security_manager.security_check(wrapped_func)
        tool_func = mcp.tool(**kwargs)(decorated_func)
        
        # 记录注册的工具
        self.registered_tools.append(func.__name__)
        
        return tool_func
    
    def register_all_tools(self, mcp):
        """
        注册所有工具的模板方法
        子类应该重写这个方法来注册具体的工具
        """
        pass