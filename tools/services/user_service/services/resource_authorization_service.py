"""
资源授权管理服务

提供用户和组织的资源权限管理功能，包括：
- 权限检查
- 权限授予和撤销
- 权限汇总统计
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta

from ..models import (
    ResourceType, AccessLevel, SubscriptionStatus,
    ResourcePermission, UserResourceAccess, OrganizationResourcePermission,
    OrganizationResourceAccess, ResourceAccessCheck, ResourceAccessResponse,
    UserResourceSummary, GrantResourceAccessRequest, RevokeResourceAccessRequest
)
from ..repositories.resource_authorization_repository import ResourceAuthorizationRepository

logger = logging.getLogger(__name__)


class ResourceAuthorizationService:
    """资源授权管理服务"""
    
    def __init__(self):
        self.repo = ResourceAuthorizationRepository()
        
        # 订阅级别权限映射
        self.subscription_hierarchy = {
            SubscriptionStatus.FREE: 0,
            SubscriptionStatus.PRO: 1, 
            SubscriptionStatus.ENTERPRISE: 2
        }
        
        # 访问级别权限映射
        self.access_level_hierarchy = {
            AccessLevel.NONE: 0,
            AccessLevel.READ_ONLY: 1,
            AccessLevel.READ_WRITE: 2,
            AccessLevel.ADMIN: 3
        }
    
    # ====================
    # 核心权限检查
    # ====================
    
    async def check_resource_access(self, check_request: ResourceAccessCheck) -> ResourceAccessResponse:
        """
        检查用户对资源的访问权限
        
        权限检查优先级：
        1. 管理员特别授权 (最高优先级)
        2. 组织权限
        3. 个人订阅权限
        4. 基础权限配置
        """
        try:
            user_id = check_request.user_id
            organization_id = check_request.organization_id
            resource_type = check_request.resource_type
            resource_name = check_request.resource_name
            required_level = check_request.required_access_level
            
            logger.debug(f"Checking access for user {user_id}, resource {resource_type}:{resource_name}")
            
            # 1. 检查管理员特别授权
            user_access = await self.repo.get_user_resource_access(user_id, resource_type, resource_name)
            if user_access and user_access.granted_by_admin:
                if self._has_sufficient_access(user_access.access_level, required_level):
                    return ResourceAccessResponse(
                        has_access=True,
                        user_access_level=user_access.access_level,
                        subscription_level=await self.repo.get_user_subscription_status(user_id) or "free",
                        organization_plan=await self.repo.get_organization_plan(organization_id) if organization_id else None,
                        access_source="admin",
                        reason=f"管理员授权访问 - {user_access.access_level}",
                        resource_info={"granted_by": "admin", "expires_at": user_access.expires_at}
                    )
            
            # 2. 检查组织权限
            if organization_id:
                org_access = await self._check_organization_access(
                    user_id, organization_id, resource_type, resource_name, required_level
                )
                if org_access.has_access:
                    return org_access
            
            # 3. 检查个人订阅权限  
            personal_access = await self._check_personal_subscription_access(
                user_id, resource_type, resource_name, required_level
            )
            if personal_access.has_access:
                return personal_access
            
            # 4. 无权限访问
            subscription_level = await self.repo.get_user_subscription_status(user_id) or "free"
            return ResourceAccessResponse(
                has_access=False,
                user_access_level=AccessLevel.NONE,
                subscription_level=subscription_level,
                organization_plan=await self.repo.get_organization_plan(organization_id) if organization_id else None,
                access_source="none",
                reason=f"用户订阅级别 ({subscription_level}) 不足以访问此资源，需要权限级别: {required_level}",
                resource_info=None
            )
            
        except Exception as e:
            logger.error(f"Error checking resource access: {e}")
            return ResourceAccessResponse(
                has_access=False,
                user_access_level=AccessLevel.NONE,
                subscription_level="unknown",
                organization_plan=None,
                access_source="error",
                reason=f"权限检查失败: {str(e)}",
                resource_info=None
            )
    
    async def _check_organization_access(self, user_id: str, organization_id: str, 
                                       resource_type: ResourceType, resource_name: str,
                                       required_level: AccessLevel) -> ResourceAccessResponse:
        """检查组织权限"""
        try:
            # 检查用户是否是组织成员
            if not await self.repo.is_user_organization_member(user_id, organization_id):
                subscription_level = await self.repo.get_user_subscription_status(user_id) or "free"
                return ResourceAccessResponse(
                    has_access=False,
                    user_access_level=AccessLevel.NONE,
                    subscription_level=subscription_level,
                    organization_plan=None,
                    access_source="none",
                    reason="用户不是该组织成员",
                    resource_info=None
                )
            
            # 检查组织成员资源访问权限
            org_member_access = await self.repo.get_organization_member_access(
                organization_id, user_id, resource_type, resource_name
            )
            if org_member_access and self._has_sufficient_access(org_member_access.access_level, required_level):
                subscription_level = await self.repo.get_user_subscription_status(user_id) or "free"
                org_plan = await self.repo.get_organization_plan(organization_id)
                return ResourceAccessResponse(
                    has_access=True,
                    user_access_level=org_member_access.access_level,
                    subscription_level=subscription_level,
                    organization_plan=org_plan,
                    access_source="organization",
                    reason=f"组织权限访问 - {org_member_access.access_level}",
                    resource_info={
                        "organization_id": organization_id,
                        "granted_by_role": org_member_access.granted_by_role,
                        "expires_at": org_member_access.expires_at
                    }
                )
            
            # 检查组织资源权限配置
            org_permission = await self.repo.get_organization_resource_permission(
                organization_id, resource_type, resource_name
            )
            if org_permission:
                org_plan = await self.repo.get_organization_plan(organization_id)
                if org_plan and self._organization_plan_sufficient(org_plan, org_permission.organization_plan_required):
                    if self._has_sufficient_access(org_permission.access_level, required_level):
                        subscription_level = await self.repo.get_user_subscription_status(user_id) or "free"
                        return ResourceAccessResponse(
                            has_access=True,
                            user_access_level=org_permission.access_level,
                            subscription_level=subscription_level,
                            organization_plan=org_plan,
                            access_source="organization",
                            reason=f"组织计划 ({org_plan}) 权限访问",
                            resource_info={
                                "organization_id": organization_id,
                                "plan_required": org_permission.organization_plan_required
                            }
                        )
            
            # 组织权限不足
            subscription_level = await self.repo.get_user_subscription_status(user_id) or "free"
            org_plan = await self.repo.get_organization_plan(organization_id)
            return ResourceAccessResponse(
                has_access=False,
                user_access_level=AccessLevel.NONE,
                subscription_level=subscription_level,
                organization_plan=org_plan,
                access_source="organization",
                reason=f"组织权限不足，需要权限级别: {required_level}",
                resource_info={"organization_id": organization_id}
            )
            
        except Exception as e:
            logger.error(f"Error checking organization access: {e}")
            subscription_level = await self.repo.get_user_subscription_status(user_id) or "free"
            return ResourceAccessResponse(
                has_access=False,
                user_access_level=AccessLevel.NONE,
                subscription_level=subscription_level,
                organization_plan=None,
                access_source="error",
                reason=f"组织权限检查失败: {str(e)}",
                resource_info=None
            )
    
    async def _check_personal_subscription_access(self, user_id: str, resource_type: ResourceType,
                                                resource_name: str, required_level: AccessLevel) -> ResourceAccessResponse:
        """检查个人订阅权限"""
        try:
            # 获取用户订阅状态
            subscription_level = await self.repo.get_user_subscription_status(user_id)
            if not subscription_level:
                return ResourceAccessResponse(
                    has_access=False,
                    user_access_level=AccessLevel.NONE,
                    subscription_level="unknown",
                    organization_plan=None,
                    access_source="none",
                    reason="无法获取用户订阅状态",
                    resource_info=None
                )
            
            # 检查用户特别授权
            user_access = await self.repo.get_user_resource_access(user_id, resource_type, resource_name)
            if user_access and user_access.granted_by_subscription:
                if self._has_sufficient_access(user_access.access_level, required_level):
                    return ResourceAccessResponse(
                        has_access=True,
                        user_access_level=user_access.access_level,
                        subscription_level=subscription_level,
                        organization_plan=None,
                        access_source="personal",
                        reason=f"个人订阅权限访问 - {user_access.access_level}",
                        resource_info={
                            "granted_by_subscription": True,
                            "expires_at": user_access.expires_at
                        }
                    )
            
            # 检查基础资源权限配置
            resource_permission = await self.repo.get_resource_permission(resource_type, resource_name)
            if resource_permission:
                if self._subscription_level_sufficient(subscription_level, resource_permission.subscription_level):
                    if self._has_sufficient_access(resource_permission.access_level, required_level):
                        return ResourceAccessResponse(
                            has_access=True,
                            user_access_level=resource_permission.access_level,
                            subscription_level=subscription_level,
                            organization_plan=None,
                            access_source="personal",
                            reason=f"订阅级别 ({subscription_level}) 权限访问",
                            resource_info={
                                "subscription_required": resource_permission.subscription_level,
                                "resource_category": resource_permission.resource_category
                            }
                        )
            
            # 个人权限不足
            return ResourceAccessResponse(
                has_access=False,
                user_access_level=AccessLevel.NONE,
                subscription_level=subscription_level,
                organization_plan=None,
                access_source="personal",
                reason=f"个人订阅级别 ({subscription_level}) 不足以访问此资源，需要权限级别: {required_level}",
                resource_info=None
            )
            
        except Exception as e:
            logger.error(f"Error checking personal subscription access: {e}")
            return ResourceAccessResponse(
                has_access=False,
                user_access_level=AccessLevel.NONE,
                subscription_level="error",
                organization_plan=None,
                access_source="error",
                reason=f"个人权限检查失败: {str(e)}",
                resource_info=None
            )
    
    # ====================
    # 权限管理操作
    # ====================
    
    async def grant_resource_access(self, request: GrantResourceAccessRequest) -> bool:
        """授予资源访问权限"""
        try:
            # 构建访问权限记录
            user_access = UserResourceAccess(
                user_id=request.user_id,
                organization_id=request.organization_id,
                resource_type=request.resource_type,
                resource_name=request.resource_name,
                access_level=request.access_level,
                granted_by_subscription=not request.granted_by_admin and not request.granted_by_organization,
                granted_by_organization=request.granted_by_organization,
                granted_by_admin=request.granted_by_admin,
                expires_at=request.expires_at
            )
            
            # 保存到数据库
            result = await self.repo.grant_user_resource_access(user_access)
            
            if result:
                logger.info(f"Granted resource access: user={request.user_id}, "
                          f"resource={request.resource_type}:{request.resource_name}, "
                          f"level={request.access_level}")
                return True
            
            logger.error(f"Failed to grant resource access for user {request.user_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error granting resource access: {e}")
            return False
    
    async def revoke_resource_access(self, request: RevokeResourceAccessRequest) -> bool:
        """撤销资源访问权限"""
        try:
            success = await self.repo.revoke_user_resource_access(
                request.user_id, request.resource_type, request.resource_name
            )
            
            if success:
                logger.info(f"Revoked resource access: user={request.user_id}, "
                          f"resource={request.resource_type}:{request.resource_name}")
            else:
                logger.warning(f"No access to revoke for user {request.user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error revoking resource access: {e}")
            return False
    
    # ====================
    # 批量权限初始化
    # ====================
    
    async def initialize_default_permissions(self) -> bool:
        """初始化默认资源权限配置"""
        try:
            logger.info("Initializing default resource permissions...")
            
            # 定义默认权限配置
            default_permissions = [
                # 免费用户的基础MCP工具
                ResourcePermission(
                    resource_type=ResourceType.MCP_TOOL,
                    resource_name="weather_get_weather",
                    resource_category="weather",
                    subscription_level=SubscriptionStatus.FREE,
                    access_level=AccessLevel.READ_ONLY,
                    description="获取天气信息（免费用户）"
                ),
                
                # 专业版用户的高级MCP工具
                ResourcePermission(
                    resource_type=ResourceType.MCP_TOOL,
                    resource_name="image_generate_image",
                    resource_category="image",
                    subscription_level=SubscriptionStatus.PRO,
                    access_level=AccessLevel.READ_WRITE,
                    description="AI图像生成（专业版用户）"
                ),
                
                # 企业版用户的管理工具
                ResourcePermission(
                    resource_type=ResourceType.MCP_TOOL,
                    resource_name="admin_manage_users",
                    resource_category="admin",
                    subscription_level=SubscriptionStatus.ENTERPRISE,
                    access_level=AccessLevel.ADMIN,
                    description="用户管理工具（企业版用户）"
                ),
                
                # 基础提示词（所有用户）
                ResourcePermission(
                    resource_type=ResourceType.PROMPT,
                    resource_name="user_assistance_prompt",
                    resource_category="assistance",
                    subscription_level=SubscriptionStatus.FREE,
                    access_level=AccessLevel.READ_ONLY,
                    description="基础用户协助提示词"
                ),
                
                # 高级提示词（专业版用户）
                ResourcePermission(
                    resource_type=ResourceType.PROMPT,
                    resource_name="security_analysis_prompt",
                    resource_category="security",
                    subscription_level=SubscriptionStatus.PRO,
                    access_level=AccessLevel.READ_WRITE,
                    description="安全分析提示词（专业版用户）"
                ),
                
                # 基础资源（免费用户）
                ResourcePermission(
                    resource_type=ResourceType.RESOURCE,
                    resource_name="memory://all",
                    resource_category="memory",
                    subscription_level=SubscriptionStatus.FREE,
                    access_level=AccessLevel.READ_ONLY,
                    description="基础内存资源访问"
                ),
                
                # 高级资源（企业版用户）
                ResourcePermission(
                    resource_type=ResourceType.RESOURCE,
                    resource_name="event://tasks",
                    resource_category="event",
                    subscription_level=SubscriptionStatus.ENTERPRISE,
                    access_level=AccessLevel.READ_WRITE,
                    description="事件系统任务资源（企业版用户）"
                )
            ]
            
            # 批量创建权限配置
            success_count = 0
            for permission in default_permissions:
                # 检查是否已存在
                existing = await self.repo.get_resource_permission(permission.resource_type, permission.resource_name)
                if not existing:
                    result = await self.repo.create_resource_permission(permission)
                    if result:
                        success_count += 1
                        logger.debug(f"Created permission: {permission.resource_type}:{permission.resource_name}")
                    else:
                        logger.warning(f"Failed to create permission: {permission.resource_type}:{permission.resource_name}")
                else:
                    logger.debug(f"Permission already exists: {permission.resource_type}:{permission.resource_name}")
            
            logger.info(f"Initialized {success_count} default resource permissions")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error initializing default permissions: {e}")
            return False
    
    # ====================
    # 统计和查询
    # ====================
    
    async def get_user_resource_summary(self, user_id: str) -> Optional[UserResourceSummary]:
        """获取用户资源访问汇总"""
        try:
            return await self.repo.get_user_resource_summary(user_id)
        except Exception as e:
            logger.error(f"Error getting user resource summary: {e}")
            return None
    
    async def list_user_accessible_resources(self, user_id: str, resource_type: Optional[ResourceType] = None) -> List[Dict[str, Any]]:
        """列出用户可访问的资源"""
        try:
            # 获取用户直接授权的资源
            user_access_list = await self.repo.list_user_resource_access(user_id, resource_type)
            
            # 获取基础权限配置（基于订阅级别）
            subscription_level = await self.repo.get_user_subscription_status(user_id)
            base_permissions = await self.repo.list_resource_permissions(resource_type)
            
            accessible_resources = []
            
            # 添加用户特别授权的资源
            for access in user_access_list:
                accessible_resources.append({
                    "resource_type": access.resource_type,
                    "resource_name": access.resource_name,
                    "access_level": access.access_level,
                    "access_source": "admin" if access.granted_by_admin else ("organization" if access.granted_by_organization else "personal"),
                    "expires_at": access.expires_at
                })
            
            # 添加基于订阅级别的基础权限
            if subscription_level:
                for permission in base_permissions:
                    if self._subscription_level_sufficient(subscription_level, permission.subscription_level):
                        # 检查是否已有特别授权（避免重复）
                        if not any(r["resource_name"] == permission.resource_name for r in accessible_resources):
                            accessible_resources.append({
                                "resource_type": permission.resource_type,
                                "resource_name": permission.resource_name,
                                "access_level": permission.access_level,
                                "access_source": "subscription",
                                "subscription_required": permission.subscription_level,
                                "expires_at": None
                            })
            
            return accessible_resources
            
        except Exception as e:
            logger.error(f"Error listing user accessible resources: {e}")
            return []
    
    # ====================
    # 辅助方法
    # ====================
    
    def _subscription_level_sufficient(self, user_level: str, required_level: str) -> bool:
        """检查订阅级别是否足够"""
        user_priority = self.subscription_hierarchy.get(user_level, -1)
        required_priority = self.subscription_hierarchy.get(required_level, 999)
        return user_priority >= required_priority
    
    def _organization_plan_sufficient(self, org_plan: str, required_plan: str) -> bool:
        """检查组织计划级别是否足够（这里简化处理，实际可能需要更复杂的映射）"""
        plan_hierarchy = {
            "startup": 0,
            "growth": 1,
            "enterprise": 2
        }
        org_priority = plan_hierarchy.get(org_plan.lower(), -1)
        required_priority = plan_hierarchy.get(required_plan.lower(), 999)
        return org_priority >= required_priority
    
    def _has_sufficient_access(self, user_level: AccessLevel, required_level: AccessLevel) -> bool:
        """检查访问级别是否足够"""
        user_priority = self.access_level_hierarchy.get(user_level, -1)
        required_priority = self.access_level_hierarchy.get(required_level, 999)
        return user_priority >= required_priority
    
    async def cleanup_expired_permissions(self) -> int:
        """清理过期的权限"""
        try:
            return await self.repo.cleanup_expired_access()
        except Exception as e:
            logger.error(f"Error cleaning up expired permissions: {e}")
            return 0