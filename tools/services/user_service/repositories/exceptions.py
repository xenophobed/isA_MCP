"""
Repository Layer Exceptions

定义Repository层的异常类型
"""

class RepositoryException(Exception):
    """Repository层基础异常"""
    pass


class UserNotFoundException(RepositoryException):
    """用户未找到异常"""
    pass


class SubscriptionNotFoundException(RepositoryException):
    """订阅未找到异常"""
    pass


class DatabaseConnectionException(RepositoryException):
    """数据库连接异常"""
    pass


class DataIntegrityException(RepositoryException):
    """数据完整性异常"""
    pass


class DuplicateEntryException(RepositoryException):
    """重复数据异常"""
    pass