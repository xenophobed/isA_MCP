"""
Base Service Classes and Utilities

定义Service层的基础类和通用功能
统一错误处理、响应格式和业务逻辑模式
"""

from typing import Dict, Any, Optional, Generic, TypeVar, Union
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 泛型类型变量
T = TypeVar('T')


class ServiceStatus(str, Enum):
    """服务操作状态"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    NOT_FOUND = "not_found"
    VALIDATION_ERROR = "validation_error"
    PERMISSION_DENIED = "permission_denied"


@dataclass
class ServiceResult(Generic[T]):
    """统一的服务返回结果"""
    status: ServiceStatus
    data: Optional[T] = None
    message: str = ""
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    @classmethod
    def success(cls, data: T = None, message: str = "Operation completed successfully") -> 'ServiceResult[T]':
        """创建成功结果"""
        return cls(
            status=ServiceStatus.SUCCESS,
            data=data,
            message=message
        )
    
    @classmethod
    def error(cls, message: str, error_code: str = None, error_details: Dict[str, Any] = None) -> 'ServiceResult[T]':
        """创建错误结果"""
        return cls(
            status=ServiceStatus.ERROR,
            message=message,
            error_code=error_code,
            error_details=error_details
        )
    
    @classmethod
    def not_found(cls, message: str = "Resource not found") -> 'ServiceResult[T]':
        """创建未找到结果"""
        return cls(
            status=ServiceStatus.NOT_FOUND,
            message=message
        )
    
    @classmethod
    def validation_error(cls, message: str, error_details: Dict[str, Any] = None) -> 'ServiceResult[T]':
        """创建验证错误结果"""
        return cls(
            status=ServiceStatus.VALIDATION_ERROR,
            message=message,
            error_details=error_details
        )
    
    @classmethod
    def permission_denied(cls, message: str = "Permission denied") -> 'ServiceResult[T]':
        """创建权限拒绝结果"""
        return cls(
            status=ServiceStatus.PERMISSION_DENIED,
            message=message
        )
    
    @property
    def is_success(self) -> bool:
        """是否操作成功"""
        return self.status == ServiceStatus.SUCCESS
    
    @property
    def is_error(self) -> bool:
        """是否操作失败"""
        return self.status == ServiceStatus.ERROR
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于API响应"""
        result = {
            "success": self.is_success,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
        
        if self.data is not None:
            # 如果data是Pydantic模型，使用model_dump()
            if hasattr(self.data, 'model_dump'):
                result["data"] = self.data.model_dump()
            # 如果data有dict()方法（旧版Pydantic）
            elif hasattr(self.data, 'dict'):
                result["data"] = self.data.dict()
            # 如果是字典或列表，直接使用
            elif isinstance(self.data, (dict, list)):
                result["data"] = self.data
            else:
                result["data"] = self.data
        
        if self.error_code:
            result["error_code"] = self.error_code
        
        if self.error_details:
            result["error_details"] = self.error_details
        
        return result


class BaseService:
    """Service层基础类"""
    
    def __init__(self, service_name: str):
        """
        初始化基础Service
        
        Args:
            service_name: 服务名称，用于日志记录
        """
        self.service_name = service_name
        self.logger = logging.getLogger(f"{__name__}.{service_name}")
    
    def _log_operation(self, operation: str, details: str = "", level: str = "info"):
        """
        记录操作日志
        
        Args:
            operation: 操作名称
            details: 操作详情
            level: 日志级别
        """
        log_message = f"[{self.service_name}] {operation}"
        if details:
            log_message += f" - {details}"
        
        getattr(self.logger, level)(log_message)
    
    def _handle_exception(self, e: Exception, operation: str) -> ServiceResult:
        """
        统一异常处理
        
        Args:
            e: 异常对象
            operation: 操作名称
            
        Returns:
            错误结果
        """
        error_message = f"Failed to {operation}: {str(e)}"
        self.logger.error(error_message, exc_info=True)
        
        return ServiceResult.error(
            message=error_message,
            error_code=type(e).__name__,
            error_details={"operation": operation, "exception": str(e)}
        )
    
    def _validate_required_fields(self, data: Dict[str, Any], required_fields: list) -> Optional[ServiceResult]:
        """
        验证必填字段
        
        Args:
            data: 数据字典
            required_fields: 必填字段列表
            
        Returns:
            验证错误结果或None（验证通过）
        """
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                missing_fields.append(field)
        
        if missing_fields:
            return ServiceResult.validation_error(
                message=f"Missing required fields: {', '.join(missing_fields)}",
                error_details={"missing_fields": missing_fields}
            )
        
        return None
    
    def _validate_email(self, email: str) -> bool:
        """
        简单的邮箱格式验证
        
        Args:
            email: 邮箱地址
            
        Returns:
            是否有效
        """
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email) is not None