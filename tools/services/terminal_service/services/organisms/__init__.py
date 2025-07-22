"""
组织服务层 (Organisms)
分子服务的编排，实现完整的业务流程

组织服务通过编排多个分子服务来完成复杂的端到端业务流程
例如：完整的应用部署流程、CI/CD管道、监控系统等
"""

from .deployment_organisms import DeploymentOrganism
from .quick_app_organism import QuickAppOrganism

__all__ = [
    'DeploymentOrganism',
    'QuickAppOrganism'
] 