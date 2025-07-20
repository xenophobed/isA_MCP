"""
Base Service Class for ISA MCP Services
统一处理ISA客户端调用、billing信息返回和服务管理
专门为复杂的服务类设计，区别于简单的工具类
"""
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
import logging
from isa_model.client import ISAModelClient

logger = logging.getLogger(__name__)

class BaseService:
    """基础服务类，提供统一的ISA客户端调用和billing信息处理"""
    
    def __init__(self, service_name: str = None):
        self.service_name = service_name or self.__class__.__name__
        self._isa_client = None
        self.billing_info = []
        self._security_manager = None
        self.operation_history = []
    
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
        parameters: Optional[Dict] = None,
        operation_name: str = None
    ) -> tuple[Any, Dict]:
        """
        调用ISA客户端并返回结果和billing信息
        
        Args:
            input_data: 输入数据
            task: 任务类型 ("chat", "embed", "generate_image", "image_to_image")
            service_type: 服务类型 ("text", "embedding", "image")
            parameters: 额外参数
            operation_name: 操作名称（用于追踪）
            
        Returns:
            tuple: (result_data, billing_info)
        """
        try:
            operation_start = datetime.now()
            
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
                billing_info['operation_name'] = operation_name or task
                billing_info['service_name'] = self.service_name
                billing_info['timestamp'] = operation_start.isoformat()
                self.billing_info.append(billing_info)
                logger.info(f"💰 {self.service_name} - {operation_name or task}: ${billing_info.get('cost_usd', 0.0):.6f}")
            
            # 记录操作历史
            self.operation_history.append({
                'operation': operation_name or task,
                'timestamp': operation_start.isoformat(),
                'success': isa_response.get('success', False),
                'cost_usd': billing_info.get('cost_usd', 0.0) if billing_info else 0.0
            })
            
            if not isa_response.get('success'):
                raise Exception(f"ISA API call failed: {isa_response.get('error', 'Unknown error')}")
            
            return result_data, billing_info
            
        except Exception as e:
            logger.error(f"{self.service_name} ISA API call failed: {e}")
            # 记录失败的操作
            self.operation_history.append({
                'operation': operation_name or task,
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'error': str(e),
                'cost_usd': 0.0
            })
            raise
    
    def create_service_response(
        self,
        status: str,
        operation: str,
        data: Dict[str, Any],
        error_message: Optional[str] = None,
        include_history: bool = False
    ) -> str:
        """
        创建统一格式的服务响应，包含billing信息
        
        Args:
            status: 状态 ("success" or "error")
            operation: 操作名称
            data: 响应数据
            error_message: 错误消息（可选）
            include_history: 是否包含操作历史
            
        Returns:
            str: JSON格式的响应
        """
        response = {
            "status": status,
            "service": self.service_name,
            "operation": operation,
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
        
        # 添加操作历史（可选）
        if include_history and self.operation_history:
            response["operation_history"] = self.operation_history[-10:]  # 最近10次操作
        
        # 添加错误信息
        if error_message:
            response["error"] = error_message
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    def reset_billing(self):
        """重置billing信息"""
        self.billing_info = []
    
    def reset_history(self):
        """重置操作历史"""
        self.operation_history = []
    
    def get_billing_summary(self) -> Dict[str, Any]:
        """获取billing摘要"""
        if not self.billing_info:
            return {
                "total_cost_usd": 0.0,
                "operation_count": 0,
                "operations": []
            }
        
        total_cost = sum(b.get('cost_usd', 0.0) for b in self.billing_info)
        operation_counts = {}
        
        for billing in self.billing_info:
            op_name = billing.get('operation_name', 'unknown')
            operation_counts[op_name] = operation_counts.get(op_name, 0) + 1
        
        return {
            "total_cost_usd": total_cost,
            "operation_count": len(self.billing_info),
            "operation_counts": operation_counts,
            "operations": self.billing_info
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        if not self.operation_history:
            return {
                "total_operations": 0,
                "success_rate": 0.0,
                "total_cost": 0.0,
                "avg_cost_per_operation": 0.0
            }
        
        total_ops = len(self.operation_history)
        successful_ops = sum(1 for op in self.operation_history if op.get('success', False))
        total_cost = sum(op.get('cost_usd', 0.0) for op in self.operation_history)
        
        return {
            "total_operations": total_ops,
            "successful_operations": successful_ops,
            "success_rate": successful_ops / total_ops if total_ops > 0 else 0.0,
            "total_cost": total_cost,
            "avg_cost_per_operation": total_cost / total_ops if total_ops > 0 else 0.0,
            "service_name": self.service_name
        }
    
    async def batch_isa_operations(
        self,
        operations: List[Dict[str, Any]]
    ) -> List[tuple[Any, Dict]]:
        """
        批量执行ISA操作
        
        Args:
            operations: 操作列表，每个操作包含：
                - input_data: 输入数据
                - task: 任务类型
                - service_type: 服务类型
                - parameters: 参数（可选）
                - operation_name: 操作名称（可选）
        
        Returns:
            List[tuple]: 结果列表
        """
        results = []
        
        for i, operation in enumerate(operations):
            try:
                result = await self.call_isa_with_billing(
                    input_data=operation['input_data'],
                    task=operation['task'],
                    service_type=operation['service_type'],
                    parameters=operation.get('parameters'),
                    operation_name=operation.get('operation_name', f"batch_op_{i}")
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Batch operation {i} failed: {e}")
                results.append((None, {"error": str(e), "cost_usd": 0.0}))
        
        return results
    
    def create_batch_response(
        self,
        operation: str,
        results: List[Any],
        errors: List[str] = None
    ) -> str:
        """创建批量操作响应"""
        successful_results = [r for r in results if r is not None]
        
        data = {
            "total_operations": len(results),
            "successful_operations": len(successful_results),
            "results": results,
            "errors": errors or []
        }
        
        return self.create_service_response(
            status="success" if len(successful_results) > 0 else "error",
            operation=operation,
            data=data
        )