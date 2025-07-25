"""
User ID Utilities
用户ID处理工具类

解决系统中 user_id 格式验证和类型转换问题
确保 Auth0 ID 在整个系统中的一致性处理
"""

import re
import uuid
from typing import Optional, Union
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class UserIdValidationResult:
    """用户ID验证结果"""
    is_valid: bool
    user_id: Optional[str] = None
    error_message: Optional[str] = None
    id_type: Optional[str] = None  # 'auth0', 'uuid', 'test', 'dev'


class UserIdValidator:
    """
    用户ID验证器
    
    支持的ID格式：
    1. Auth0 ID: auth0|{uuid} 或 {uuid} 格式
    2. 标准UUID: 36位带连字符的UUID
    3. 测试ID: test-user-{数字} 格式
    4. 开发ID: dev_user, dev-user 等
    """
    
    # Auth0 ID 模式 - 支持多种登录格式
    # 包括: 社交登录、邮箱登录、自定义格式等
    # 格式: {provider}|{identifier}
    # - provider: 登录提供商标识
    # - identifier: 用户标识符 (可以是UUID、数字ID、邮箱等)
    AUTH0_PATTERN = re.compile(r'^[a-zA-Z0-9\-_]+\|[\w\-\.@+]+$', re.IGNORECASE)
    
    # 标准UUID模式 (36位，包含连字符)
    UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    
    # 测试用户ID模式
    TEST_PATTERN = re.compile(r'^test-user-\d+$', re.IGNORECASE)
    
    # 开发用户ID模式
    DEV_PATTERN = re.compile(r'^dev[-_]?user$', re.IGNORECASE)
    
    @classmethod
    def validate(cls, user_id: Union[str, None]) -> UserIdValidationResult:
        """
        验证用户ID格式
        
        Args:
            user_id: 待验证的用户ID
            
        Returns:
            UserIdValidationResult: 验证结果
        """
        if not user_id:
            return UserIdValidationResult(
                is_valid=False,
                error_message="User ID cannot be empty or None"
            )
        
        if not isinstance(user_id, str):
            return UserIdValidationResult(
                is_valid=False,
                error_message=f"User ID must be string, got {type(user_id)}"
            )
        
        user_id = user_id.strip()
        
        if not user_id:
            return UserIdValidationResult(
                is_valid=False,
                error_message="User ID cannot be empty string"
            )
        
        # 检查长度限制（数据库字段为varchar(255)）
        if len(user_id) > 255:
            return UserIdValidationResult(
                is_valid=False,
                error_message=f"User ID too long: {len(user_id)} characters (max 255)"
            )
        
        # 按优先级检查不同格式
        
        # 1. 外部提供商格式 (Auth0、自建系统等)
        if cls.AUTH0_PATTERN.match(user_id):
            # 检测具体的提供商类型
            provider = user_id.split('|')[0].lower()
            if provider.startswith('auth0') or provider in ['google-oauth2', 'github', 'facebook', 'twitter', 'linkedin', 'microsoft-oauth2']:
                id_type = "auth0"
            else:
                id_type = "external"  # 自建或其他外部系统
            
            return UserIdValidationResult(
                is_valid=True,
                user_id=user_id,
                id_type=id_type
            )
        
        # 2. 标准UUID格式
        if cls.UUID_PATTERN.match(user_id):
            return UserIdValidationResult(
                is_valid=True,
                user_id=user_id,
                id_type="uuid"
            )
        
        # 3. 测试用户ID格式
        if cls.TEST_PATTERN.match(user_id):
            return UserIdValidationResult(
                is_valid=True,
                user_id=user_id,
                id_type="test"
            )
        
        # 4. 开发用户ID格式
        if cls.DEV_PATTERN.match(user_id):
            return UserIdValidationResult(
                is_valid=True,
                user_id=user_id,
                id_type="dev"
            )
        
        # 不支持的格式
        return UserIdValidationResult(
            is_valid=False,
            user_id=user_id,
            error_message=f"Unsupported user ID format: {user_id}",
        )
    
    @classmethod
    def normalize(cls, user_id: str) -> str:
        """
        标准化用户ID格式
        
        Args:
            user_id: 原始用户ID
            
        Returns:
            str: 标准化后的用户ID
        """
        if not user_id:
            return user_id
        
        # 移除首尾空格
        normalized = user_id.strip()
        
        # Auth0 ID: 保持原格式
        if cls.AUTH0_PATTERN.match(normalized):
            return normalized
        
        # UUID: 转换为小写
        if cls.UUID_PATTERN.match(normalized):
            return normalized.lower()
        
        # 测试和开发ID: 转换为小写
        if cls.TEST_PATTERN.match(normalized) or cls.DEV_PATTERN.match(normalized):
            return normalized.lower()
        
        return normalized
    
    @classmethod
    def is_auth0_id(cls, user_id: str) -> bool:
        """检查是否为Auth0 ID格式"""
        return bool(user_id and cls.AUTH0_PATTERN.match(user_id.strip()))
    
    @classmethod
    def is_uuid(cls, user_id: str) -> bool:
        """检查是否为UUID格式"""
        return bool(user_id and cls.UUID_PATTERN.match(user_id.strip()))
    
    @classmethod
    def is_test_id(cls, user_id: str) -> bool:
        """检查是否为测试ID格式"""
        return bool(user_id and cls.TEST_PATTERN.match(user_id.strip()))
    
    @classmethod
    def is_dev_id(cls, user_id: str) -> bool:
        """检查是否为开发ID格式"""
        return bool(user_id and cls.DEV_PATTERN.match(user_id.strip()))


class UserIdConverter:
    """
    用户ID转换器
    处理不同系统间的ID格式转换
    """
    
    @staticmethod
    def extract_uuid_from_auth0(auth0_id: str) -> Optional[str]:
        """
        从Auth0 ID中提取UUID部分
        
        Args:
            auth0_id: Auth0格式的ID (如: auth0|550e8400-e29b-41d4-a716-446655440000)
            
        Returns:
            str: UUID部分，如果无法提取则返回None
        """
        if not auth0_id or not isinstance(auth0_id, str):
            return None
        
        if auth0_id.startswith('auth0|'):
            uuid_part = auth0_id[6:]  # 移除 'auth0|' 前缀
            if UserIdValidator.UUID_PATTERN.match(uuid_part):
                return uuid_part.lower()
        
        return None
    
    @staticmethod
    def create_auth0_id_from_uuid(uuid_str: str) -> Optional[str]:
        """
        从UUID创建Auth0 ID格式
        
        Args:
            uuid_str: UUID字符串
            
        Returns:
            str: Auth0格式的ID，如果输入无效则返回None
        """
        if not uuid_str or not isinstance(uuid_str, str):
            return None
        
        uuid_str = uuid_str.strip().lower()
        
        if UserIdValidator.UUID_PATTERN.match(uuid_str):
            return f"auth0|{uuid_str}"
        
        return None
    
    @staticmethod
    def generate_test_user_id(user_number: int = None) -> str:
        """
        生成测试用户ID
        
        Args:
            user_number: 用户编号，如果不提供则使用随机数
            
        Returns:
            str: 测试用户ID
        """
        if user_number is None:
            import random
            user_number = random.randint(1000, 9999)
        
        return f"test-user-{user_number:03d}"
    
    @staticmethod
    def generate_uuid_user_id() -> str:
        """
        生成UUID格式的用户ID
        
        Returns:
            str: UUID格式的用户ID
        """
        return str(uuid.uuid4())


def validate_user_id(user_id: Union[str, None], raise_on_invalid: bool = False) -> UserIdValidationResult:
    """
    便捷的用户ID验证函数
    
    Args:
        user_id: 待验证的用户ID
        raise_on_invalid: 是否在验证失败时抛出异常
        
    Returns:
        UserIdValidationResult: 验证结果
        
    Raises:
        ValueError: 当 raise_on_invalid=True 且验证失败时抛出
    """
    result = UserIdValidator.validate(user_id)
    
    if not result.is_valid and raise_on_invalid:
        raise ValueError(f"Invalid user ID: {result.error_message}")
    
    return result


def normalize_user_id(user_id: str) -> str:
    """
    便捷的用户ID标准化函数
    
    Args:
        user_id: 原始用户ID
        
    Returns:
        str: 标准化后的用户ID
    """
    return UserIdValidator.normalize(user_id)


def safe_user_id(user_id: Union[str, None], default: str = "anonymous") -> str:
    """
    安全获取用户ID，如果无效则返回默认值
    
    Args:
        user_id: 原始用户ID
        default: 默认值
        
    Returns:
        str: 有效的用户ID或默认值
    """
    if not user_id:
        return default
    
    result = UserIdValidator.validate(user_id)
    return result.user_id if result.is_valid else default


# 导出主要功能
__all__ = [
    'UserIdValidator',
    'UserIdConverter', 
    'UserIdValidationResult',
    'validate_user_id',
    'normalize_user_id',
    'safe_user_id'
]


if __name__ == "__main__":
    # 测试代码
    test_ids = [
        "auth0|550e8400-e29b-41d4-a716-446655440000",
        "550e8400-e29b-41d4-a716-446655440000",
        "test-user-001",
        "dev_user",
        "invalid-id",
        None,
        "",
        "   "
    ]
    
    print("User ID Validation Tests:")
    print("=" * 50)
    
    for test_id in test_ids:
        result = validate_user_id(test_id)
        print(f"ID: {test_id!r}")
        print(f"  Valid: {result.is_valid}")
        if result.is_valid:
            print(f"  Type: {result.id_type}")
            print(f"  Normalized: {normalize_user_id(result.user_id)}")
        else:
            print(f"  Error: {result.error_message}")
        print()