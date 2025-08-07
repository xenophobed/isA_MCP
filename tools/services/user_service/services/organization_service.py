"""
Organization Service

Business logic for organization management
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..repositories.organization_repository import OrganizationRepository
from ..models import (
    Organization, OrganizationCreate, OrganizationUpdate,
    OrganizationMember, OrganizationMemberCreate, OrganizationMemberUpdate,
    OrganizationRole, OrganizationMemberStatus
)
from .base import ServiceResult

logger = logging.getLogger(__name__)


class OrganizationService:
    """Service for organization management"""

    def __init__(self):
        self.org_repo = OrganizationRepository()

    async def initialize(self):
        """Initialize the service (create tables if needed)"""
        try:
            await self.org_repo.init_tables()
            logger.info("Organization service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize organization service: {str(e)}")
            raise

    # ============ Organization Operations ============

    async def create_organization(self, org_data: OrganizationCreate, owner_user_id: str) -> ServiceResult[Organization]:
        """Create a new organization with the user as owner"""
        try:
            # Validate organization data
            if not org_data.name.strip():
                return ServiceResult.error("Organization name cannot be empty")
            
            if not org_data.billing_email:
                return ServiceResult.error("Billing email is required")
            
            # Create organization
            result = await self.org_repo.create_organization(org_data, owner_user_id)
            
            if result.is_success:
                logger.info(f"Organization created: {result.data.organization_id} by user {owner_user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating organization: {str(e)}")
            return ServiceResult.error(f"Failed to create organization: {str(e)}")

    async def get_organization(self, organization_id: str) -> ServiceResult[Organization]:
        """Get organization by ID"""
        try:
            return await self.org_repo.get_organization(organization_id)
        except Exception as e:
            logger.error(f"Error getting organization: {str(e)}")
            return ServiceResult.error(f"Failed to get organization: {str(e)}")

    async def update_organization(self, organization_id: str, update_data: OrganizationUpdate, user_id: str) -> ServiceResult[Organization]:
        """Update organization (requires admin/owner permissions)"""
        try:
            # Check user permissions
            role_result = await self.org_repo.get_user_organization_role(organization_id, user_id)
            if not role_result.is_success:
                return ServiceResult.error("Access denied: User not found in organization")
            
            user_role = role_result.data['role']
            if user_role not in ['owner', 'admin']:
                return ServiceResult.error("Access denied: Only owners and admins can update organization")
            
            # Update organization
            result = await self.org_repo.update_organization(organization_id, update_data)
            
            if result.is_success:
                logger.info(f"Organization updated: {organization_id} by user {user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error updating organization: {str(e)}")
            return ServiceResult.error(f"Failed to update organization: {str(e)}")

    async def delete_organization(self, organization_id: str, user_id: str) -> ServiceResult[bool]:
        """Delete organization (requires owner permissions)"""
        try:
            # Check user permissions
            role_result = await self.org_repo.get_user_organization_role(organization_id, user_id)
            if not role_result.is_success:
                return ServiceResult.error("Access denied: User not found in organization")
            
            user_role = role_result.data['role']
            if user_role != 'owner':
                return ServiceResult.error("Access denied: Only owners can delete organization")
            
            # Delete organization
            result = await self.org_repo.delete_organization(organization_id)
            
            if result.is_success:
                logger.info(f"Organization deleted: {organization_id} by user {user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error deleting organization: {str(e)}")
            return ServiceResult.error(f"Failed to delete organization: {str(e)}")

    async def get_user_organizations(self, user_id: str) -> ServiceResult[List[Dict[str, Any]]]:
        """Get all organizations for a user"""
        try:
            return await self.org_repo.get_user_organizations(user_id)
        except Exception as e:
            logger.error(f"Error getting user organizations: {str(e)}")
            return ServiceResult.error(f"Failed to get user organizations: {str(e)}")

    # ============ Organization Member Operations ============

    async def add_organization_member(self, organization_id: str, member_data: OrganizationMemberCreate, requesting_user_id: str) -> ServiceResult[OrganizationMember]:
        """Add member to organization"""
        try:
            # Check requesting user permissions
            role_result = await self.org_repo.get_user_organization_role(organization_id, requesting_user_id)
            if not role_result.is_success:
                return ServiceResult.error("Access denied: User not found in organization")
            
            requesting_role = role_result.data['role']
            if requesting_role not in ['owner', 'admin']:
                return ServiceResult.error("Access denied: Only owners and admins can add members")
            
            # Validate member data
            if not member_data.user_id and not member_data.email:
                return ServiceResult.error("Either user_id or email must be provided")
            
            # If email is provided but no user_id, this would be an invitation
            # For now, we'll require user_id (existing user)
            if not member_data.user_id:
                return ServiceResult.error("User invitation not implemented yet. Please provide user_id of existing user.")
            
            # Check if user is already a member
            existing_member = await self.org_repo.get_user_organization_role(organization_id, member_data.user_id)
            if existing_member.is_success:
                return ServiceResult.error(f"User {member_data.user_id} is already a member of this organization")
            
            # Add member
            result = await self.org_repo.add_organization_member(
                organization_id, 
                member_data.user_id, 
                member_data.role, 
                member_data.permissions
            )
            
            if result.is_success:
                logger.info(f"Member added to organization {organization_id}: {member_data.user_id} with role {member_data.role.value}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error adding organization member: {str(e)}")
            return ServiceResult.error(f"Failed to add organization member: {str(e)}")

    async def get_organization_members(self, organization_id: str, requesting_user_id: str) -> ServiceResult[List[OrganizationMember]]:
        """Get all members of an organization"""
        try:
            # Check requesting user permissions
            role_result = await self.org_repo.get_user_organization_role(organization_id, requesting_user_id)
            if not role_result.is_success:
                return ServiceResult.error("Access denied: User not found in organization")
            
            # Any organization member can view the member list
            return await self.org_repo.get_organization_members(organization_id)
            
        except Exception as e:
            logger.error(f"Error getting organization members: {str(e)}")
            return ServiceResult.error(f"Failed to get organization members: {str(e)}")

    async def update_organization_member(self, organization_id: str, user_id: str, update_data: OrganizationMemberUpdate, requesting_user_id: str) -> ServiceResult[OrganizationMember]:
        """Update organization member"""
        try:
            # Check requesting user permissions
            role_result = await self.org_repo.get_user_organization_role(organization_id, requesting_user_id)
            if not role_result.is_success:
                return ServiceResult.error("Access denied: User not found in organization")
            
            requesting_role = role_result.data['role']
            
            # Get target user's current role
            target_role_result = await self.org_repo.get_user_organization_role(organization_id, user_id)
            if not target_role_result.is_success:
                return ServiceResult.error("Target user not found in organization")
            
            target_role = target_role_result.data['role']
            
            # Permission checks
            if requesting_role == 'admin':
                # Admins can update members and viewers, but not owners or other admins
                if target_role in ['owner', 'admin']:
                    return ServiceResult.error("Access denied: Admins cannot modify owners or other admins")
            elif requesting_role == 'owner':
                # Owners can update anyone except other owners (unless it's themselves)
                if target_role == 'owner' and requesting_user_id != user_id:
                    return ServiceResult.error("Access denied: Cannot modify other owners")
            else:
                return ServiceResult.error("Access denied: Only owners and admins can update members")
            
            # Update member
            result = await self.org_repo.update_organization_member(organization_id, user_id, update_data)
            
            if result.is_success:
                logger.info(f"Organization member updated: {user_id} in {organization_id} by {requesting_user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error updating organization member: {str(e)}")
            return ServiceResult.error(f"Failed to update organization member: {str(e)}")

    async def remove_organization_member(self, organization_id: str, user_id: str, requesting_user_id: str) -> ServiceResult[bool]:
        """Remove member from organization"""
        try:
            # Check requesting user permissions
            role_result = await self.org_repo.get_user_organization_role(organization_id, requesting_user_id)
            if not role_result.is_success:
                return ServiceResult.error("Access denied: User not found in organization")
            
            requesting_role = role_result.data['role']
            
            # Get target user's current role
            target_role_result = await self.org_repo.get_user_organization_role(organization_id, user_id)
            if not target_role_result.is_success:
                return ServiceResult.error("Target user not found in organization")
            
            target_role = target_role_result.data['role']
            
            # Permission checks
            if requesting_role == 'admin':
                # Admins can remove members and viewers, but not owners or other admins
                if target_role in ['owner', 'admin']:
                    return ServiceResult.error("Access denied: Admins cannot remove owners or other admins")
            elif requesting_role == 'owner':
                # Owners can remove anyone except other owners
                if target_role == 'owner' and requesting_user_id != user_id:
                    return ServiceResult.error("Access denied: Cannot remove other owners")
            else:
                # Members can only remove themselves
                if requesting_user_id != user_id:
                    return ServiceResult.error("Access denied: You can only remove yourself from the organization")
            
            # Special check: Don't allow removing the last owner
            if target_role == 'owner':
                members_result = await self.org_repo.get_organization_members(organization_id)
                if members_result.is_success:
                    owners = [m for m in members_result.data if m.role == OrganizationRole.OWNER and m.status == OrganizationMemberStatus.ACTIVE]
                    if len(owners) <= 1:
                        return ServiceResult.error("Cannot remove the last owner from organization")
            
            # Remove member
            result = await self.org_repo.remove_organization_member(organization_id, user_id)
            
            if result.is_success:
                logger.info(f"Organization member removed: {user_id} from {organization_id} by {requesting_user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error removing organization member: {str(e)}")
            return ServiceResult.error(f"Failed to remove organization member: {str(e)}")

    async def get_user_organization_role(self, organization_id: str, user_id: str) -> ServiceResult[Dict[str, Any]]:
        """Get user's role and permissions in organization"""
        try:
            return await self.org_repo.get_user_organization_role(organization_id, user_id)
        except Exception as e:
            logger.error(f"Error getting user organization role: {str(e)}")
            return ServiceResult.error(f"Failed to get user organization role: {str(e)}")

    async def switch_user_context(self, user_id: str, organization_id: Optional[str] = None) -> ServiceResult[Dict[str, Any]]:
        """Switch user context to organization or back to individual"""
        try:
            if organization_id:
                # Validate user is member of organization
                role_result = await self.org_repo.get_user_organization_role(organization_id, user_id)
                if not role_result.is_success:
                    return ServiceResult.error("User is not a member of this organization")
                
                # Get organization details
                org_result = await self.org_repo.get_organization(organization_id)
                if not org_result.is_success:
                    return ServiceResult.error("Organization not found")
                
                context = {
                    "type": "organization",
                    "organization_id": organization_id,
                    "organization_name": org_result.data.name,
                    "user_role": role_result.data['role'],
                    "permissions": role_result.data['permissions'],
                    "credits_available": org_result.data.credits_pool
                }
            else:
                # Switch back to individual context
                context = {
                    "type": "individual",
                    "organization_id": None,
                    "organization_name": None,
                    "user_role": None,
                    "permissions": [],
                    "credits_available": None  # Will be fetched from user's individual credits
                }
            
            return ServiceResult.success(context, "Context switched successfully")
            
        except Exception as e:
            logger.error(f"Error switching user context: {str(e)}")
            return ServiceResult.error(f"Failed to switch user context: {str(e)}")

    # ============ Utility Methods ============

    async def check_organization_access(self, organization_id: str, user_id: str, required_roles: List[str] = None) -> bool:
        """Check if user has access to organization with optional role requirements"""
        try:
            role_result = await self.org_repo.get_user_organization_role(organization_id, user_id)
            if not role_result.is_success:
                return False
            
            if role_result.data['status'] != 'active':
                return False
            
            if required_roles:
                return role_result.data['role'] in required_roles
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking organization access: {str(e)}")
            return False

    async def get_organization_stats(self, organization_id: str, user_id: str) -> ServiceResult[Dict[str, Any]]:
        """Get organization statistics"""
        try:
            # Check access
            if not await self.check_organization_access(organization_id, user_id):
                return ServiceResult.error("Access denied")
            
            # Get organization details
            org_result = await self.org_repo.get_organization(organization_id)
            if not org_result.is_success:
                return ServiceResult.error("Organization not found")
            
            # Get member count
            members_result = await self.org_repo.get_organization_members(organization_id)
            member_count = len(members_result.data) if members_result.is_success else 0
            
            # TODO: Add usage statistics, credit consumption, etc.
            
            stats = {
                "organization_id": organization_id,
                "name": org_result.data.name,
                "plan": org_result.data.plan.value,
                "status": org_result.data.status.value,
                "member_count": member_count,
                "credits_pool": org_result.data.credits_pool,
                "created_at": org_result.data.created_at,
                # TODO: Add more statistics
                "total_usage_this_month": 0,
                "total_cost_this_month": 0.0,
                "top_users": [],
                "usage_by_department": {}
            }
            
            return ServiceResult.success(stats, "Organization statistics retrieved successfully")
            
        except Exception as e:
            logger.error(f"Error getting organization stats: {str(e)}")
            return ServiceResult.error(f"Failed to get organization stats: {str(e)}")