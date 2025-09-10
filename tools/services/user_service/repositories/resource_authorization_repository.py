"""
资源授权管理 Repository

处理用户和组织的资源权限数据库操作
"""


import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from core.database.supabase_client import get_supabase_client
from models.schemas.user_models import (
    ResourceType, AccessLevel, SubscriptionStatus,
    ResourcePermission, UserResourceAccess, OrganizationResourcePermission, 
    OrganizationResourceAccess, ResourceAccessCheck, UserResourceSummary
)

logger = logging.getLogger(__name__)


class ResourceAuthorizationRepository:
    """资源授权管理数据库操作类"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    # ====================
    # 资源权限配置管理
    # ====================
    
    async def create_resource_permission(self, permission: ResourcePermission) -> Optional[ResourcePermission]:
        """创建资源权限配置"""
        try:
            data = {
                "resource_type": permission.resource_type,
                "resource_name": permission.resource_name,
                "resource_category": permission.resource_category,
                "subscription_level": permission.subscription_level,
                "access_level": permission.access_level,
                "is_enabled": permission.is_enabled,
                "description": permission.description,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = self.supabase.table("resource_permissions").insert(data).execute()
            
            if result.data:
                return ResourcePermission(**result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to create resource permission: {e}")
            return None
    
    async def get_resource_permission(self, resource_type: ResourceType, resource_name: str) -> Optional[ResourcePermission]:
        """获取资源权限配置"""
        try:
            result = self.supabase.table("resource_permissions")\
                .select("*")\
                .eq("resource_type", resource_type)\
                .eq("resource_name", resource_name)\
                .eq("is_enabled", True)\
                .single()\
                .execute()
            
            if result.data:
                return ResourcePermission(**result.data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get resource permission: {e}")
            return None
    
    async def list_resource_permissions(self, resource_type: Optional[ResourceType] = None) -> List[ResourcePermission]:
        """列出资源权限配置"""
        try:
            query = self.supabase.table("resource_permissions").select("*").eq("is_enabled", True)
            
            if resource_type:
                query = query.eq("resource_type", resource_type)
            
            result = query.execute()
            
            if result.data:
                return [ResourcePermission(**item) for item in result.data]
            return []
            
        except Exception as e:
            logger.error(f"Failed to list resource permissions: {e}")
            return []
    
    # ====================
    # 用户资源访问管理
    # ====================
    
    async def grant_user_resource_access(self, access: UserResourceAccess) -> Optional[UserResourceAccess]:
        """授予用户资源访问权限"""
        try:
            data = {
                "user_id": access.user_id,
                "organization_id": access.organization_id,
                "resource_type": access.resource_type,
                "resource_name": access.resource_name,
                "access_level": access.access_level,
                "granted_by_subscription": access.granted_by_subscription,
                "granted_by_organization": access.granted_by_organization,
                "granted_by_admin": access.granted_by_admin,
                "expires_at": access.expires_at,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # 使用 upsert 避免重复记录
            result = self.supabase.table("user_resource_access")\
                .upsert(data, on_conflict="user_id,resource_type,resource_name")\
                .execute()
            
            if result.data:
                return UserResourceAccess(**result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to grant user resource access: {e}")
            return None
    
    async def get_user_resource_access(self, user_id: str, resource_type: ResourceType, 
                                     resource_name: str) -> Optional[UserResourceAccess]:
        """获取用户资源访问权限"""
        try:
            result = self.supabase.table("user_resource_access")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("resource_type", resource_type)\
                .eq("resource_name", resource_name)\
                .or_("expires_at.is.null,expires_at.gt.now()")\
                .single()\
                .execute()
            
            if result.data:
                return UserResourceAccess(**result.data)
            return None
            
        except Exception as e:
            logger.debug(f"User resource access not found: {e}")
            return None
    
    async def list_user_resource_access(self, user_id: str, 
                                       resource_type: Optional[ResourceType] = None,
                                       organization_id: Optional[str] = None) -> List[UserResourceAccess]:
        """列出用户的资源访问权限"""
        try:
            query = self.supabase.table("user_resource_access")\
                .select("*")\
                .eq("user_id", user_id)\
                .or_("expires_at.is.null,expires_at.gt.now()")
            
            if resource_type:
                query = query.eq("resource_type", resource_type)
            
            if organization_id:
                query = query.eq("organization_id", organization_id)
            
            result = query.execute()
            
            if result.data:
                return [UserResourceAccess(**item) for item in result.data]
            return []
            
        except Exception as e:
            logger.error(f"Failed to list user resource access: {e}")
            return []
    
    async def revoke_user_resource_access(self, user_id: str, resource_type: ResourceType, 
                                        resource_name: str) -> bool:
        """撤销用户资源访问权限"""
        try:
            result = self.supabase.table("user_resource_access")\
                .delete()\
                .eq("user_id", user_id)\
                .eq("resource_type", resource_type)\
                .eq("resource_name", resource_name)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to revoke user resource access: {e}")
            return False
    
    # ====================
    # 组织资源权限管理
    # ====================
    
    async def create_organization_resource_permission(self, permission: OrganizationResourcePermission) -> Optional[OrganizationResourcePermission]:
        """创建组织资源权限配置"""
        try:
            data = {
                "organization_id": permission.organization_id,
                "resource_type": permission.resource_type,
                "resource_name": permission.resource_name,
                "resource_category": permission.resource_category,
                "organization_plan_required": permission.organization_plan_required,
                "access_level": permission.access_level,
                "is_enabled": permission.is_enabled,
                "description": permission.description,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = self.supabase.table("organization_resource_permissions").insert(data).execute()
            
            if result.data:
                return OrganizationResourcePermission(**result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to create organization resource permission: {e}")
            return None
    
    async def get_organization_resource_permission(self, organization_id: str, resource_type: ResourceType, 
                                                 resource_name: str) -> Optional[OrganizationResourcePermission]:
        """获取组织资源权限配置"""
        try:
            result = self.supabase.table("organization_resource_permissions")\
                .select("*")\
                .eq("organization_id", organization_id)\
                .eq("resource_type", resource_type)\
                .eq("resource_name", resource_name)\
                .eq("is_enabled", True)\
                .single()\
                .execute()
            
            if result.data:
                return OrganizationResourcePermission(**result.data)
            return None
            
        except Exception as e:
            logger.debug(f"Organization resource permission not found: {e}")
            return None
    
    async def grant_organization_member_access(self, access: OrganizationResourceAccess) -> Optional[OrganizationResourceAccess]:
        """授予组织成员资源访问权限"""
        try:
            data = {
                "organization_id": access.organization_id,
                "user_id": access.user_id,
                "resource_type": access.resource_type,
                "resource_name": access.resource_name,
                "access_level": access.access_level,
                "granted_by_role": access.granted_by_role,
                "granted_by_admin": access.granted_by_admin,
                "expires_at": access.expires_at,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = self.supabase.table("organization_resource_access")\
                .upsert(data, on_conflict="organization_id,user_id,resource_type,resource_name")\
                .execute()
            
            if result.data:
                return OrganizationResourceAccess(**result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to grant organization member access: {e}")
            return None
    
    async def get_organization_member_access(self, organization_id: str, user_id: str, 
                                           resource_type: ResourceType, resource_name: str) -> Optional[OrganizationResourceAccess]:
        """获取组织成员资源访问权限"""
        try:
            result = self.supabase.table("organization_resource_access")\
                .select("*")\
                .eq("organization_id", organization_id)\
                .eq("user_id", user_id)\
                .eq("resource_type", resource_type)\
                .eq("resource_name", resource_name)\
                .or_("expires_at.is.null,expires_at.gt.now()")\
                .single()\
                .execute()
            
            if result.data:
                return OrganizationResourceAccess(**result.data)
            return None
            
        except Exception as e:
            logger.debug(f"Organization member access not found: {e}")
            return None
    
    # ====================
    # 权限检查辅助方法
    # ====================
    
    async def get_user_subscription_status(self, user_id: str) -> Optional[str]:
        """获取用户订阅状态"""
        try:
            result = self.supabase.table("users")\
                .select("subscription_status")\
                .eq("user_id", user_id)\
                .single()\
                .execute()
            
            if result.data:
                return result.data["subscription_status"]
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user subscription status: {e}")
            return None
    
    async def get_organization_plan(self, organization_id: str) -> Optional[str]:
        """获取组织计划级别"""
        try:
            result = self.supabase.table("organizations")\
                .select("plan")\
                .eq("organization_id", organization_id)\
                .single()\
                .execute()
            
            if result.data:
                return result.data["plan"]
            return None
            
        except Exception as e:
            logger.error(f"Failed to get organization plan: {e}")
            return None
    
    async def is_user_organization_member(self, user_id: str, organization_id: str) -> bool:
        """检查用户是否是组织成员"""
        try:
            result = self.supabase.table("organization_members")\
                .select("id")\
                .eq("user_id", user_id)\
                .eq("organization_id", organization_id)\
                .eq("status", "active")\
                .single()\
                .execute()
            
            return result.data is not None
            
        except Exception as e:
            logger.debug(f"User is not organization member: {e}")
            return False
    
    # ====================
    # 统计和汇总
    # ====================
    
    async def get_user_resource_summary(self, user_id: str) -> Optional[UserResourceSummary]:
        """获取用户资源访问汇总"""
        try:
            # 获取用户订阅状态
            subscription_status = await self.get_user_subscription_status(user_id)
            if not subscription_status:
                return None
            
            # 获取用户组织信息
            org_result = self.supabase.table("organization_members")\
                .select("organization_id, organizations(plan)")\
                .eq("user_id", user_id)\
                .eq("status", "active")\
                .limit(1)\
                .execute()
            
            organization_id = None
            organization_plan = None
            if org_result.data:
                organization_id = org_result.data[0]["organization_id"]
                organization_plan = org_result.data[0]["organizations"]["plan"]
            
            # 统计各类资源数量
            access_list = await self.list_user_resource_access(user_id)
            
            mcp_tools_count = len([a for a in access_list if a.resource_type == ResourceType.MCP_TOOL])
            prompts_count = len([a for a in access_list if a.resource_type == ResourceType.PROMPT])
            resources_count = len([a for a in access_list if a.resource_type == ResourceType.RESOURCE])
            
            personal_granted_count = len([a for a in access_list if a.granted_by_subscription])
            organization_granted_count = len([a for a in access_list if a.granted_by_organization])
            admin_granted_count = len([a for a in access_list if a.granted_by_admin])
            
            # 统计即将过期的权限
            soon_expire = datetime.utcnow() + timedelta(days=7)
            expires_soon_count = len([a for a in access_list if a.expires_at and a.expires_at <= soon_expire])
            
            return UserResourceSummary(
                user_id=user_id,
                subscription_level=subscription_status,
                organization_id=organization_id,
                organization_plan=organization_plan,
                total_accessible_resources=len(access_list),
                mcp_tools_count=mcp_tools_count,
                prompts_count=prompts_count,
                resources_count=resources_count,
                personal_granted_count=personal_granted_count,
                organization_granted_count=organization_granted_count,
                admin_granted_count=admin_granted_count,
                expires_soon_count=expires_soon_count
            )
            
        except Exception as e:
            logger.error(f"Failed to get user resource summary: {e}")
            return None
    
    async def cleanup_expired_access(self) -> int:
        """清理过期的访问权限"""
        try:
            # 删除过期的用户资源访问权限
            user_result = self.supabase.table("user_resource_access")\
                .delete()\
                .lt("expires_at", datetime.utcnow().isoformat())\
                .execute()
            
            # 删除过期的组织成员资源访问权限
            org_result = self.supabase.table("organization_resource_access")\
                .delete()\
                .lt("expires_at", datetime.utcnow().isoformat())\
                .execute()
            
            cleaned_count = len(user_result.data or []) + len(org_result.data or [])
            logger.info(f"Cleaned up {cleaned_count} expired access records")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired access: {e}")
            return 0