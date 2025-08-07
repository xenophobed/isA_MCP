"""
Organization Invitation Repository

邀请系统的数据访问层
处理组织邀请的CRUD操作
"""

import asyncpg
import json
import secrets
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from .base import BaseRepository
from ..models import OrganizationInvitation, InvitationStatus


class InvitationRepository(BaseRepository[OrganizationInvitation]):
    """邀请数据仓库"""
    
    def __init__(self):
        super().__init__("organization_invitations")
        self._db_pool = None
    
    async def _get_connection(self):
        """获取数据库连接"""
        if self._db_pool is None:
            self._db_pool = await asyncpg.create_pool(
                host='127.0.0.1',
                port=54322,
                database='postgres',
                user='postgres',
                password='postgres',
                min_size=1,
                max_size=10
            )
        return self._db_pool
    
    def _parse_json_field(self, value: Any) -> Any:
        """解析JSON字段"""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value
    
    async def create(self, data: Dict[str, Any]) -> Optional[OrganizationInvitation]:
        """创建邀请"""
        try:
            pool = await self._get_connection()
            
            # 生成邀请ID和令牌
            invitation_id = str(uuid.uuid4())
            invitation_token = secrets.token_urlsafe(32)
            
            # 设置过期时间（7天）
            expires_at = datetime.utcnow() + timedelta(days=7)
            
            query = """
            INSERT INTO organization_invitations 
            (invitation_id, organization_id, email, role, invited_by, invitation_token, status, expires_at, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING *
            """
            
            now = datetime.utcnow()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    query,
                    invitation_id,
                    data['organization_id'],
                    data['email'],
                    data['role'],
                    data['invited_by'],
                    invitation_token,
                    InvitationStatus.PENDING.value,
                    expires_at,
                    now,
                    now
                )
                
                if row:
                    return OrganizationInvitation(**dict(row))
                return None
                
        except Exception as e:
            print(f"Error creating invitation: {e}")
            return None
    
    async def get_by_id(self, invitation_id: str) -> Optional[OrganizationInvitation]:
        """根据ID获取邀请"""
        try:
            pool = await self._get_connection()
            
            query = "SELECT * FROM organization_invitations WHERE invitation_id = $1"
            
            async with pool.acquire() as conn:
                row = await conn.fetchrow(query, invitation_id)
                
                if row:
                    return OrganizationInvitation(**dict(row))
                return None
                
        except Exception as e:
            print(f"Error getting invitation by id: {e}")
            return None
    
    async def get_by_token(self, token: str) -> Optional[OrganizationInvitation]:
        """根据令牌获取邀请"""
        try:
            pool = await self._get_connection()
            
            query = "SELECT * FROM organization_invitations WHERE invitation_token = $1"
            
            async with pool.acquire() as conn:
                row = await conn.fetchrow(query, token)
                
                if row:
                    return OrganizationInvitation(**dict(row))
                return None
                
        except Exception as e:
            print(f"Error getting invitation by token: {e}")
            return None
    
    async def get_by_email_and_organization(self, email: str, organization_id: str) -> Optional[OrganizationInvitation]:
        """根据邮箱和组织ID获取邀请"""
        try:
            pool = await self._get_connection()
            
            query = """
            SELECT * FROM organization_invitations 
            WHERE email = $1 AND organization_id = $2 AND status = $3
            ORDER BY created_at DESC
            LIMIT 1
            """
            
            async with pool.acquire() as conn:
                row = await conn.fetchrow(query, email, organization_id, InvitationStatus.PENDING.value)
                
                if row:
                    return OrganizationInvitation(**dict(row))
                return None
                
        except Exception as e:
            print(f"Error getting invitation by email and organization: {e}")
            return None
    
    async def get_by_organization(self, organization_id: str) -> List[OrganizationInvitation]:
        """获取组织的所有邀请"""
        try:
            pool = await self._get_connection()
            
            query = """
            SELECT * FROM organization_invitations 
            WHERE organization_id = $1
            ORDER BY created_at DESC
            """
            
            async with pool.acquire() as conn:
                rows = await conn.fetch(query, organization_id)
                
                return [OrganizationInvitation(**dict(row)) for row in rows]
                
        except Exception as e:
            print(f"Error getting invitations by organization: {e}")
            return []
    
    async def get_pending_by_organization(self, organization_id: str) -> List[OrganizationInvitation]:
        """获取组织的待处理邀请"""
        try:
            pool = await self._get_connection()
            
            query = """
            SELECT * FROM organization_invitations 
            WHERE organization_id = $1 AND status = $2
            ORDER BY created_at DESC
            """
            
            async with pool.acquire() as conn:
                rows = await conn.fetch(query, organization_id, InvitationStatus.PENDING.value)
                
                return [OrganizationInvitation(**dict(row)) for row in rows]
                
        except Exception as e:
            print(f"Error getting pending invitations by organization: {e}")
            return []
    
    async def update(self, invitation_id: str, data: Dict[str, Any]) -> bool:
        """更新邀请"""
        try:
            pool = await self._get_connection()
            
            # 构建更新字段
            set_fields = []
            values = []
            param_count = 1
            
            for field, value in data.items():
                if field not in ['id', 'invitation_id', 'created_at']:
                    set_fields.append(f"{field} = ${param_count}")
                    values.append(value)
                    param_count += 1
            
            if not set_fields:
                return False
            
            # 添加updated_at
            set_fields.append(f"updated_at = ${param_count}")
            values.append(datetime.utcnow())
            param_count += 1
            
            # 添加where条件
            values.append(invitation_id)
            
            query = f"""
            UPDATE organization_invitations 
            SET {', '.join(set_fields)}
            WHERE invitation_id = ${param_count}
            """
            
            async with pool.acquire() as conn:
                result = await conn.execute(query, *values)
                return result.split()[-1] == '1'  # 检查是否更新了一行
                
        except Exception as e:
            print(f"Error updating invitation: {e}")
            return False
    
    async def accept_invitation(self, invitation_token: str) -> bool:
        """接受邀请"""
        try:
            pool = await self._get_connection()
            
            query = """
            UPDATE organization_invitations 
            SET status = $1, accepted_at = $2, updated_at = $3
            WHERE invitation_token = $4 AND status = $5 AND expires_at > $6
            """
            
            now = datetime.utcnow()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    query,
                    InvitationStatus.ACCEPTED.value,
                    now,
                    now,
                    invitation_token,
                    InvitationStatus.PENDING.value,
                    now
                )
                return result.split()[-1] == '1'
                
        except Exception as e:
            print(f"Error accepting invitation: {e}")
            return False
    
    async def cancel_invitation(self, invitation_id: str) -> bool:
        """取消邀请"""
        return await self.update(invitation_id, {
            'status': InvitationStatus.CANCELLED.value
        })
    
    async def expire_old_invitations(self) -> int:
        """过期旧邀请"""
        try:
            pool = await self._get_connection()
            
            query = """
            UPDATE organization_invitations 
            SET status = $1, updated_at = $2
            WHERE status = $3 AND expires_at < $4
            """
            
            now = datetime.utcnow()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    query,
                    InvitationStatus.EXPIRED.value,
                    now,
                    InvitationStatus.PENDING.value,
                    now
                )
                return int(result.split()[-1])
                
        except Exception as e:
            print(f"Error expiring old invitations: {e}")
            return 0
    
    async def delete(self, invitation_id: str) -> bool:
        """删除邀请"""
        try:
            pool = await self._get_connection()
            
            query = "DELETE FROM organization_invitations WHERE invitation_id = $1"
            
            async with pool.acquire() as conn:
                result = await conn.execute(query, invitation_id)
                return result.split()[-1] == '1'
                
        except Exception as e:
            print(f"Error deleting invitation: {e}")
            return False
    
    async def get_invitation_with_organization_info(self, invitation_token: str) -> Optional[Dict[str, Any]]:
        """获取邀请及组织信息"""
        try:
            pool = await self._get_connection()
            
            query = """
            SELECT 
                inv.*,
                org.name as organization_name,
                org.domain as organization_domain,
                u.name as inviter_name,
                u.email as inviter_email
            FROM organization_invitations inv
            JOIN organizations org ON inv.organization_id = org.organization_id
            LEFT JOIN users u ON inv.invited_by = u.user_id
            WHERE inv.invitation_token = $1
            """
            
            async with pool.acquire() as conn:
                row = await conn.fetchrow(query, invitation_token)
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            print(f"Error getting invitation with organization info: {e}")
            return None