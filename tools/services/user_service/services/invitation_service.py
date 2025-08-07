"""
Organization Invitation Service

组织邀请服务
处理邀请发送、接受、管理等业务逻辑
"""

import secrets
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .base import BaseService, ServiceResult
from .email_service import EmailService
from ..models import (
    OrganizationInvitation, OrganizationInvitationCreate, InvitationStatus,
    OrganizationRole, AcceptInvitationRequest
)
from ..repositories import (
    InvitationRepository, OrganizationRepository, 
    UserRepository
)


class InvitationService(BaseService):
    """邀请服务"""
    
    def __init__(self, 
                 invitation_repository: InvitationRepository = None,
                 organization_repository: OrganizationRepository = None,
                 user_repository: UserRepository = None,
                 email_service: EmailService = None):
        """
        初始化邀请服务
        
        Args:
            invitation_repository: 邀请数据仓库
            organization_repository: 组织数据仓库
            user_repository: 用户数据仓库
            email_service: 邮件服务
        """
        super().__init__("InvitationService")
        self.invitation_repo = invitation_repository or InvitationRepository()
        self.organization_repo = organization_repository or OrganizationRepository()
        self.user_repo = user_repository or UserRepository()
        self.email_service = email_service or EmailService()
        
        # 邀请链接基础URL（应该从配置中读取）
        self.invitation_base_url = "https://app.iapro.ai/accept-invitation"
    
    async def create_invitation(self, organization_id: str, inviter_user_id: str, 
                               invitation_data: OrganizationInvitationCreate) -> ServiceResult[Dict[str, Any]]:
        """
        创建组织邀请
        
        Args:
            organization_id: 组织ID
            inviter_user_id: 邀请人用户ID
            invitation_data: 邀请数据
            
        Returns:
            ServiceResult[Dict]: 创建结果
        """
        try:
            self._log_operation("create_invitation", f"org={organization_id}, email={invitation_data.email}")
            
            # 验证组织是否存在
            organization = await self.organization_repo.get_by_id(organization_id)
            if not organization:
                return ServiceResult.not_found("Organization not found")
            
            # 验证邀请人是否存在且有权限
            inviter = await self.user_repo.get_by_user_id(inviter_user_id)
            if not inviter:
                return ServiceResult.not_found("Inviter not found")
            
            # 检查邀请人是否是组织成员且有邀请权限
            is_member = await self._check_inviter_permissions(organization_id, inviter_user_id)
            if not is_member:
                return ServiceResult.permission_denied("You don't have permission to invite users to this organization")
            
            # 检查是否已经有待处理的邀请
            existing_invitation = await self.invitation_repo.get_by_email_and_organization(
                invitation_data.email, organization_id
            )
            if existing_invitation:
                return ServiceResult.validation_error(
                    "A pending invitation already exists for this email",
                    error_details={"existing_invitation_id": existing_invitation.invitation_id}
                )
            
            # 检查用户是否已经是组织成员
            existing_user = await self.user_repo.get_by_email(invitation_data.email)
            if existing_user:
                # 检查是否已经是成员
                is_already_member = await self._check_user_membership(organization_id, existing_user.user_id)
                if is_already_member:
                    return ServiceResult.validation_error("User is already a member of this organization")
            
            # 创建邀请记录
            invitation_create_data = {
                'organization_id': organization_id,
                'email': invitation_data.email,
                'role': invitation_data.role.value,
                'invited_by': inviter_user_id
            }
            
            invitation = await self.invitation_repo.create(invitation_create_data)
            if not invitation:
                return ServiceResult.error("Failed to create invitation")
            
            # 发送邀请邮件
            email_result = await self._send_invitation_email(invitation, organization, inviter, invitation_data.message)
            
            result_data = {
                "invitation_id": invitation.invitation_id,
                "email": invitation.email,
                "role": invitation.role,
                "organization_name": organization.name,
                "expires_at": invitation.expires_at,
                "email_sent": email_result.is_success,
                "email_error": email_result.message if not email_result.is_success else None
            }
            
            self._log_operation("invitation_created", f"invitation_id={invitation.invitation_id}")
            
            return ServiceResult.success(
                data=result_data,
                message="Invitation created and sent successfully"
            )
            
        except Exception as e:
            return self._handle_exception(e, "create invitation")
    
    async def get_invitation_by_token(self, invitation_token: str) -> ServiceResult[Dict[str, Any]]:
        """
        根据令牌获取邀请信息
        
        Args:
            invitation_token: 邀请令牌
            
        Returns:
            ServiceResult[Dict]: 邀请信息
        """
        try:
            self._log_operation("get_invitation_by_token", f"token={invitation_token[:10]}...")
            
            # 获取邀请及组织信息
            invitation_info = await self.invitation_repo.get_invitation_with_organization_info(invitation_token)
            if not invitation_info:
                return ServiceResult.not_found("Invitation not found")
            
            # 检查邀请状态
            if invitation_info['status'] != InvitationStatus.PENDING.value:
                return ServiceResult.validation_error(f"Invitation is {invitation_info['status']}")
            
            # 检查是否过期
            expires_at = invitation_info['expires_at']
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace('Z', ''))
            
            if expires_at < datetime.utcnow():
                # 更新状态为过期
                await self.invitation_repo.update(invitation_info['invitation_id'], {
                    'status': InvitationStatus.EXPIRED.value
                })
                return ServiceResult.validation_error("Invitation has expired")
            
            result_data = {
                "invitation_id": invitation_info['invitation_id'],
                "organization_id": invitation_info['organization_id'],
                "organization_name": invitation_info['organization_name'],
                "organization_domain": invitation_info.get('organization_domain'),
                "email": invitation_info['email'],
                "role": invitation_info['role'],
                "inviter_name": invitation_info.get('inviter_name'),
                "inviter_email": invitation_info.get('inviter_email'),
                "expires_at": expires_at.isoformat(),
                "created_at": invitation_info['created_at']
            }
            
            return ServiceResult.success(
                data=result_data,
                message="Invitation found"
            )
            
        except Exception as e:
            return self._handle_exception(e, "get invitation by token")
    
    async def accept_invitation(self, accept_request: AcceptInvitationRequest) -> ServiceResult[Dict[str, Any]]:
        """
        接受邀请
        
        Args:
            accept_request: 接受邀请请求
            
        Returns:
            ServiceResult[Dict]: 接受结果
        """
        try:
            self._log_operation("accept_invitation", f"token={accept_request.invitation_token[:10]}...")
            
            # 获取邀请信息
            invitation_result = await self.get_invitation_by_token(accept_request.invitation_token)
            if not invitation_result.is_success:
                return invitation_result
            
            invitation_info = invitation_result.data
            
            # 确定用户ID
            user_id = accept_request.user_id
            if not user_id:
                # 如果没有提供用户ID，尝试根据邮箱查找用户
                existing_user = await self.user_repo.get_by_email(invitation_info['email'])
                if existing_user:
                    user_id = existing_user.user_id
                else:
                    return ServiceResult.validation_error(
                        "User not found. Please provide user_id or user_data to create account"
                    )
            
            # 检查用户是否存在
            user = await self.user_repo.get_by_user_id(user_id)
            if not user:
                return ServiceResult.not_found("User not found")
            
            # 检查邮箱是否匹配
            if user.email != invitation_info['email']:
                return ServiceResult.validation_error("Email mismatch")
            
            # 接受邀请
            accept_success = await self.invitation_repo.accept_invitation(accept_request.invitation_token)
            if not accept_success:
                return ServiceResult.error("Failed to accept invitation")
            
            # 添加用户到组织
            from .organization_service import OrganizationService
            org_service = OrganizationService()
            
            add_member_result = await org_service.add_member(
                invitation_info['organization_id'],
                user_id,
                invitation_info['role']
            )
            
            if not add_member_result.is_success:
                # 如果添加成员失败，回滚邀请状态
                await self.invitation_repo.update(invitation_info['invitation_id'], {
                    'status': InvitationStatus.PENDING.value,
                    'accepted_at': None
                })
                return ServiceResult.error(f"Failed to add user to organization: {add_member_result.message}")
            
            result_data = {
                "invitation_id": invitation_info['invitation_id'],
                "organization_id": invitation_info['organization_id'],
                "organization_name": invitation_info['organization_name'],
                "user_id": user_id,
                "role": invitation_info['role'],
                "accepted_at": datetime.utcnow().isoformat()
            }
            
            self._log_operation("invitation_accepted", f"user_id={user_id}, org_id={invitation_info['organization_id']}")
            
            return ServiceResult.success(
                data=result_data,
                message="Invitation accepted successfully"
            )
            
        except Exception as e:
            return self._handle_exception(e, "accept invitation")
    
    async def get_organization_invitations(self, organization_id: str) -> ServiceResult[List[Dict[str, Any]]]:
        """
        获取组织的所有邀请
        
        Args:
            organization_id: 组织ID
            
        Returns:
            ServiceResult[List]: 邀请列表
        """
        try:
            self._log_operation("get_organization_invitations", f"org_id={organization_id}")
            
            invitations = await self.invitation_repo.get_by_organization(organization_id)
            
            result_data = []
            for invitation in invitations:
                # 获取邀请人信息
                inviter = await self.user_repo.get_by_user_id(invitation.invited_by)
                
                invitation_data = {
                    "invitation_id": invitation.invitation_id,
                    "email": invitation.email,
                    "role": invitation.role,
                    "status": invitation.status,
                    "inviter_name": inviter.name if inviter else "Unknown",
                    "inviter_email": inviter.email if inviter else "Unknown",
                    "expires_at": invitation.expires_at.isoformat() if invitation.expires_at else None,
                    "created_at": invitation.created_at.isoformat() if invitation.created_at else None,
                    "accepted_at": invitation.accepted_at.isoformat() if invitation.accepted_at else None
                }
                result_data.append(invitation_data)
            
            return ServiceResult.success(
                data=result_data,
                message=f"Found {len(result_data)} invitations"
            )
            
        except Exception as e:
            return self._handle_exception(e, "get organization invitations")
    
    async def cancel_invitation(self, invitation_id: str, user_id: str) -> ServiceResult[bool]:
        """
        取消邀请
        
        Args:
            invitation_id: 邀请ID
            user_id: 操作用户ID
            
        Returns:
            ServiceResult[bool]: 取消结果
        """
        try:
            self._log_operation("cancel_invitation", f"invitation_id={invitation_id}, user_id={user_id}")
            
            # 获取邀请信息
            invitation = await self.invitation_repo.get_by_id(invitation_id)
            if not invitation:
                return ServiceResult.not_found("Invitation not found")
            
            # 检查权限（只有邀请人或组织管理员可以取消）
            if invitation.invited_by != user_id:
                has_permission = await self._check_inviter_permissions(invitation.organization_id, user_id)
                if not has_permission:
                    return ServiceResult.permission_denied("You don't have permission to cancel this invitation")
            
            # 取消邀请
            success = await self.invitation_repo.cancel_invitation(invitation_id)
            
            if success:
                return ServiceResult.success(
                    data=True,
                    message="Invitation cancelled successfully"
                )
            else:
                return ServiceResult.error("Failed to cancel invitation")
                
        except Exception as e:
            return self._handle_exception(e, "cancel invitation")
    
    async def resend_invitation(self, invitation_id: str, user_id: str) -> ServiceResult[Dict[str, Any]]:
        """
        重新发送邀请
        
        Args:
            invitation_id: 邀请ID
            user_id: 操作用户ID
            
        Returns:
            ServiceResult[Dict]: 重发结果
        """
        try:
            self._log_operation("resend_invitation", f"invitation_id={invitation_id}, user_id={user_id}")
            
            # 获取邀请信息
            invitation = await self.invitation_repo.get_by_id(invitation_id)
            if not invitation:
                return ServiceResult.not_found("Invitation not found")
            
            # 检查权限
            if invitation.invited_by != user_id:
                has_permission = await self._check_inviter_permissions(invitation.organization_id, user_id)
                if not has_permission:
                    return ServiceResult.permission_denied("You don't have permission to resend this invitation")
            
            # 检查邀请状态
            if invitation.status != InvitationStatus.PENDING.value:
                return ServiceResult.validation_error(f"Cannot resend {invitation.status} invitation")
            
            # 延长过期时间
            new_expires_at = datetime.utcnow() + timedelta(days=7)
            await self.invitation_repo.update(invitation_id, {
                'expires_at': new_expires_at
            })
            
            # 重新获取完整信息
            invitation_info = await self.invitation_repo.get_invitation_with_organization_info(invitation.invitation_token)
            if not invitation_info:
                return ServiceResult.error("Failed to get invitation info")
            
            # 获取组织和邀请人信息
            organization = await self.organization_repo.get_by_id(invitation.organization_id)
            inviter = await self.user_repo.get_by_user_id(invitation.invited_by)
            
            # 重新发送邮件
            email_result = await self._send_invitation_email(invitation, organization, inviter)
            
            result_data = {
                "invitation_id": invitation_id,
                "email_sent": email_result.is_success,
                "email_error": email_result.message if not email_result.is_success else None,
                "new_expires_at": new_expires_at.isoformat()
            }
            
            return ServiceResult.success(
                data=result_data,
                message="Invitation resent successfully"
            )
            
        except Exception as e:
            return self._handle_exception(e, "resend invitation")
    
    async def _send_invitation_email(self, invitation: OrganizationInvitation, 
                                   organization: Any, inviter: Any, 
                                   personal_message: Optional[str] = None) -> ServiceResult:
        """发送邀请邮件"""
        try:
            invitation_link = f"{self.invitation_base_url}?token={invitation.invitation_token}"
            
            email_data = {
                'to_email': invitation.email,
                'organization_name': organization.name,
                'inviter_name': inviter.name if inviter else 'Unknown',
                'inviter_email': inviter.email if inviter else None,
                'role': invitation.role,
                'invitation_link': invitation_link,
                'expires_at': invitation.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC') if invitation.expires_at else 'N/A'
            }
            
            if personal_message:
                email_data['personal_message'] = personal_message
            
            return await self.email_service.send_organization_invitation(email_data)
            
        except Exception as e:
            return ServiceResult.error(f"Failed to send invitation email: {str(e)}")
    
    async def _check_inviter_permissions(self, organization_id: str, user_id: str) -> bool:
        """检查邀请人权限"""
        try:
            from .organization_service import OrganizationService
            org_service = OrganizationService()
            
            # 检查用户在组织中的角色
            member = await org_service.get_member(organization_id, user_id)
            if not member.is_success:
                return False
            
            member_data = member.data
            # 只有OWNER和ADMIN可以邀请用户
            return member_data.get('role') in ['owner', 'admin']
            
        except Exception:
            return False
    
    async def _check_user_membership(self, organization_id: str, user_id: str) -> bool:
        """检查用户是否已经是组织成员"""
        try:
            from .organization_service import OrganizationService
            org_service = OrganizationService()
            
            member = await org_service.get_member(organization_id, user_id)
            return member.is_success
            
        except Exception:
            return False
    
    async def expire_old_invitations(self) -> ServiceResult[int]:
        """过期旧邀请"""
        try:
            self._log_operation("expire_old_invitations")
            
            expired_count = await self.invitation_repo.expire_old_invitations()
            
            return ServiceResult.success(
                data=expired_count,
                message=f"Expired {expired_count} old invitations"
            )
            
        except Exception as e:
            return self._handle_exception(e, "expire old invitations")