"""
Organization Repository

Handles database operations for organizations and organization members
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import uuid

from .base import BaseRepository
from ..models import (
    Organization, OrganizationCreate, OrganizationUpdate,
    OrganizationMember, OrganizationMemberCreate, OrganizationMemberUpdate,
    OrganizationUsage, OrganizationUsageCreate,
    OrganizationCreditTransaction,
    OrganizationStatus, OrganizationPlan, OrganizationRole, OrganizationMemberStatus
)
from ..services.base import ServiceResult

logger = logging.getLogger(__name__)


class OrganizationRepository(BaseRepository):
    """Repository for organization-related database operations"""
    
    def __init__(self):
        super().__init__("organizations")
        self._db_pool = None

    def _parse_json_field(self, value, default_list=False):
        """Parse JSON field from database"""
        import json
        logger.debug(f"Parsing JSON field: {value} (type: {type(value)})")
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                logger.debug(f"Parsed result: {parsed} (type: {type(parsed)})")
                return parsed
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse JSON: {value}, error: {e}")
                return [] if default_list else {}
        result = value or ([] if default_list else {})
        logger.debug(f"Returning default: {result}")
        return result

    async def _get_connection(self):
        """Get database connection"""
        import asyncpg
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

    async def execute(self, sql: str, *params):
        """Execute SQL statement"""
        pool = await self._get_connection()
        async with pool.acquire() as conn:
            await conn.execute('SET search_path TO dev')
            return await conn.execute(sql, *params)

    async def fetch_one(self, sql: str, *params):
        """Fetch single row"""
        pool = await self._get_connection()
        async with pool.acquire() as conn:
            await conn.execute('SET search_path TO dev')
            return await conn.fetchrow(sql, *params)

    async def fetch_all(self, sql: str, *params):
        """Fetch all rows"""
        pool = await self._get_connection()
        async with pool.acquire() as conn:
            await conn.execute('SET search_path TO dev')
            return await conn.fetch(sql, *params)

    async def create_organizations_table(self):
        """Create organizations table"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS organizations (
            id SERIAL PRIMARY KEY,
            organization_id VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            domain VARCHAR(255),
            plan VARCHAR(50) DEFAULT 'startup',
            billing_email VARCHAR(255) NOT NULL,
            status VARCHAR(50) DEFAULT 'active',
            settings JSONB DEFAULT '{}',
            credits_pool DECIMAL(12,2) DEFAULT 0.00,
            api_keys JSONB DEFAULT '[]',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_organizations_organization_id ON organizations(organization_id);
        CREATE INDEX IF NOT EXISTS idx_organizations_domain ON organizations(domain);
        CREATE INDEX IF NOT EXISTS idx_organizations_status ON organizations(status);
        """
        
        try:
            await self.execute(create_table_sql)
            logger.info("Organizations table created/verified successfully")
        except Exception as e:
            logger.error(f"Error creating organizations table: {str(e)}")
            raise

    async def create_organization_members_table(self):
        """Create organization_members table"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS organization_members (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            organization_id VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL DEFAULT 'member',
            permissions JSONB DEFAULT '[]',
            status VARCHAR(50) DEFAULT 'active',
            joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, organization_id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_org_members_user_id ON organization_members(user_id);
        CREATE INDEX IF NOT EXISTS idx_org_members_org_id ON organization_members(organization_id);
        CREATE INDEX IF NOT EXISTS idx_org_members_role ON organization_members(role);
        CREATE INDEX IF NOT EXISTS idx_org_members_status ON organization_members(status);
        """
        
        try:
            await self.execute(create_table_sql)
            logger.info("Organization members table created/verified successfully")
        except Exception as e:
            logger.error(f"Error creating organization members table: {str(e)}")
            raise

    async def create_organization_usage_table(self):
        """Create organization_usage table"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS organization_usage (
            id SERIAL PRIMARY KEY,
            organization_id VARCHAR(255) NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            session_id VARCHAR(255),
            trace_id VARCHAR(255),
            endpoint VARCHAR(255) NOT NULL,
            event_type VARCHAR(100) NOT NULL,
            credits_charged DECIMAL(12,4) DEFAULT 0.0000,
            cost_usd DECIMAL(12,4) DEFAULT 0.0000,
            calculation_method VARCHAR(100) DEFAULT 'unknown',
            tokens_used INTEGER DEFAULT 0,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            model_name VARCHAR(255),
            provider VARCHAR(100),
            tool_name VARCHAR(255),
            operation_name VARCHAR(255),
            department VARCHAR(255),
            project_id VARCHAR(255),
            billing_metadata JSONB DEFAULT '{}',
            request_data JSONB DEFAULT '{}',
            response_data JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_org_usage_org_id ON organization_usage(organization_id);
        CREATE INDEX IF NOT EXISTS idx_org_usage_user_id ON organization_usage(user_id);
        CREATE INDEX IF NOT EXISTS idx_org_usage_event_type ON organization_usage(event_type);
        CREATE INDEX IF NOT EXISTS idx_org_usage_created_at ON organization_usage(created_at);
        CREATE INDEX IF NOT EXISTS idx_org_usage_department ON organization_usage(department);
        CREATE INDEX IF NOT EXISTS idx_org_usage_project_id ON organization_usage(project_id);
        """
        
        try:
            await self.execute(create_table_sql)
            logger.info("Organization usage table created/verified successfully")
        except Exception as e:
            logger.error(f"Error creating organization usage table: {str(e)}")
            raise

    async def create_organization_credit_transactions_table(self):
        """Create organization_credit_transactions table"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS organization_credit_transactions (
            id SERIAL PRIMARY KEY,
            organization_id VARCHAR(255) NOT NULL,
            transaction_type VARCHAR(50) NOT NULL,
            credits_amount DECIMAL(12,4) NOT NULL,
            credits_before DECIMAL(12,4) NOT NULL,
            credits_after DECIMAL(12,4) NOT NULL,
            user_id VARCHAR(255),
            usage_record_id INTEGER,
            description TEXT,
            reference_id VARCHAR(255),
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_org_credit_trans_org_id ON organization_credit_transactions(organization_id);
        CREATE INDEX IF NOT EXISTS idx_org_credit_trans_type ON organization_credit_transactions(transaction_type);
        CREATE INDEX IF NOT EXISTS idx_org_credit_trans_user_id ON organization_credit_transactions(user_id);
        CREATE INDEX IF NOT EXISTS idx_org_credit_trans_created_at ON organization_credit_transactions(created_at);
        """
        
        try:
            await self.execute(create_table_sql)
            logger.info("Organization credit transactions table created/verified successfully")
        except Exception as e:
            logger.error(f"Error creating organization credit transactions table: {str(e)}")
            raise

    async def init_tables(self):
        """Initialize all organization-related tables"""
        await self.create_organizations_table()
        await self.create_organization_members_table()
        await self.create_organization_usage_table()
        await self.create_organization_credit_transactions_table()

    # ============ BaseRepository Abstract Method Implementations ============

    async def create(self, data: Dict[str, Any]) -> Optional[Organization]:
        """Create a new organization record"""
        try:
            org_create = OrganizationCreate(**data)
            result = await self.create_organization(org_create, data.get('owner_user_id', ''))
            return result.data if result.is_success else None
        except Exception as e:
            logger.error(f"Error in create method: {str(e)}")
            return None

    async def get_by_id(self, entity_id: str) -> Optional[Organization]:
        """Get organization by ID"""
        try:
            result = await self.get_organization(entity_id)
            return result.data if result.is_success else None
        except Exception as e:
            logger.error(f"Error in get_by_id method: {str(e)}")
            return None

    async def update(self, entity_id: str, data: Dict[str, Any]) -> bool:
        """Update organization record"""
        try:
            org_update = OrganizationUpdate(**data)
            result = await self.update_organization(entity_id, org_update)
            return result.is_success
        except Exception as e:
            logger.error(f"Error in update method: {str(e)}")
            return False

    async def delete(self, entity_id: str) -> bool:
        """Delete organization record"""
        try:
            result = await self.delete_organization(entity_id)
            return result.is_success
        except Exception as e:
            logger.error(f"Error in delete method: {str(e)}")
            return False

    # ============ Organization CRUD Operations ============

    async def create_organization(self, org_data: OrganizationCreate, owner_user_id: str) -> ServiceResult[Organization]:
        """Create a new organization"""
        try:
            # Generate unique organization ID
            org_id = f"org_{uuid.uuid4().hex[:12]}"
            
            # Insert organization
            insert_sql = """
            INSERT INTO organizations 
            (organization_id, name, domain, plan, billing_email, settings)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """
            
            import json
            row = await self.fetch_one(
                insert_sql,
                org_id,
                org_data.name,
                org_data.domain,
                org_data.plan.value,
                org_data.billing_email,
                json.dumps(org_data.settings or {})
            )
            
            if not row:
                return ServiceResult.error("Failed to create organization")
            
            # Convert row to Organization model
            org = Organization(
                id=row['id'],
                organization_id=row['organization_id'],
                name=row['name'],
                domain=row['domain'],
                plan=OrganizationPlan(row['plan']),
                billing_email=row['billing_email'],
                status=OrganizationStatus(row['status']),
                settings=self._parse_json_field(row['settings']),
                credits_pool=float(row['credits_pool']),
                api_keys=self._parse_json_field(row['api_keys']) if row['api_keys'] else [],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            
            # Add owner as organization member
            member_result = await self.add_organization_member(
                org_id, owner_user_id, OrganizationRole.OWNER
            )
            
            if not member_result.is_success:
                # Rollback organization creation if member addition fails
                await self.delete_organization(org_id)
                return ServiceResult.error(f"Failed to add owner to organization: {member_result.message}")
            
            return ServiceResult.success(org, "Organization created successfully")
            
        except Exception as e:
            logger.error(f"Error creating organization: {str(e)}")
            return ServiceResult.error(f"Failed to create organization: {str(e)}")

    async def get_organization(self, organization_id: str) -> ServiceResult[Organization]:
        """Get organization by ID"""
        try:
            sql = "SELECT * FROM organizations WHERE organization_id = $1"
            row = await self.fetch_one(sql, organization_id)
            
            if not row:
                return ServiceResult.error(f"Organization not found: {organization_id}")
            
            org = Organization(
                id=row['id'],
                organization_id=row['organization_id'],
                name=row['name'],
                domain=row['domain'],
                plan=OrganizationPlan(row['plan']),
                billing_email=row['billing_email'],
                status=OrganizationStatus(row['status']),
                settings=self._parse_json_field(row['settings']),
                credits_pool=float(row['credits_pool']),
                api_keys=self._parse_json_field(row['api_keys']) if row['api_keys'] else [],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            
            return ServiceResult.success(org, "Organization retrieved successfully")
            
        except Exception as e:
            logger.error(f"Error getting organization: {str(e)}")
            return ServiceResult.error(f"Failed to get organization: {str(e)}")

    async def update_organization(self, organization_id: str, update_data: OrganizationUpdate) -> ServiceResult[Organization]:
        """Update organization"""
        try:
            # Build dynamic update query
            update_fields = []
            params = []
            param_count = 1
            
            import json
            for field, value in update_data.dict(exclude_unset=True).items():
                if value is not None:
                    if field == 'plan':
                        update_fields.append(f"{field} = ${param_count}")
                        params.append(value.value)
                    elif field == 'status':
                        update_fields.append(f"{field} = ${param_count}")
                        params.append(value.value)
                    elif field in ['settings', 'api_keys']:
                        update_fields.append(f"{field} = ${param_count}")
                        params.append(json.dumps(value))
                    else:
                        update_fields.append(f"{field} = ${param_count}")
                        params.append(value)
                    param_count += 1
            
            if not update_fields:
                return ServiceResult.error("No fields to update")
            
            # Add updated_at
            update_fields.append(f"updated_at = ${param_count}")
            params.append(datetime.utcnow())
            param_count += 1
            
            # Add organization_id for WHERE clause
            params.append(organization_id)
            
            sql = f"""
            UPDATE organizations 
            SET {', '.join(update_fields)}
            WHERE organization_id = ${param_count}
            RETURNING *
            """
            
            row = await self.fetch_one(sql, *params)
            
            if not row:
                return ServiceResult.error(f"Organization not found: {organization_id}")
            
            org = Organization(
                id=row['id'],
                organization_id=row['organization_id'],
                name=row['name'],
                domain=row['domain'],
                plan=OrganizationPlan(row['plan']),
                billing_email=row['billing_email'],
                status=OrganizationStatus(row['status']),
                settings=self._parse_json_field(row['settings']),
                credits_pool=float(row['credits_pool']),
                api_keys=self._parse_json_field(row['api_keys']) if row['api_keys'] else [],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            
            return ServiceResult.success(org, "Organization updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating organization: {str(e)}")
            return ServiceResult.error(f"Failed to update organization: {str(e)}")

    async def delete_organization(self, organization_id: str) -> ServiceResult[bool]:
        """Delete organization"""
        try:
            # Delete organization members first
            await self.execute("DELETE FROM organization_members WHERE organization_id = $1", organization_id)
            
            # Delete organization usage records
            await self.execute("DELETE FROM organization_usage WHERE organization_id = $1", organization_id)
            
            # Delete organization credit transactions
            await self.execute("DELETE FROM organization_credit_transactions WHERE organization_id = $1", organization_id)
            
            # Delete organization
            sql = "DELETE FROM organizations WHERE organization_id = $1"
            result = await self.execute(sql, organization_id)
            
            return ServiceResult.success(True, "Organization deleted successfully")
            
        except Exception as e:
            logger.error(f"Error deleting organization: {str(e)}")
            return ServiceResult.error(f"Failed to delete organization: {str(e)}")

    async def get_user_organizations(self, user_id: str) -> ServiceResult[List[Dict[str, Any]]]:
        """Get all organizations for a user"""
        try:
            sql = """
            SELECT o.*, om.role, om.status as member_status, om.joined_at
            FROM organizations o
            JOIN organization_members om ON o.organization_id = om.organization_id
            WHERE om.user_id = $1 AND om.status = 'active'
            ORDER BY om.joined_at DESC
            """
            
            rows = await self.fetch_all(sql, user_id)
            
            organizations = []
            for row in rows:
                org_data = {
                    "id": row['id'],
                    "organization_id": row['organization_id'],
                    "name": row['name'],
                    "domain": row['domain'],
                    "plan": row['plan'],
                    "billing_email": row['billing_email'],
                    "status": row['status'],
                    "settings": row['settings'] or {},
                    "credits_pool": float(row['credits_pool']),
                    "api_keys": row['api_keys'] or [],
                    "created_at": row['created_at'],
                    "updated_at": row['updated_at'],
                    "user_role": row['role'],
                    "member_status": row['member_status'],
                    "joined_at": row['joined_at']
                }
                organizations.append(org_data)
            
            return ServiceResult.success(organizations, f"Retrieved {len(organizations)} organizations")
            
        except Exception as e:
            logger.error(f"Error getting user organizations: {str(e)}")
            return ServiceResult.error(f"Failed to get user organizations: {str(e)}")

    # ============ Organization Member Operations ============

    async def add_organization_member(self, organization_id: str, user_id: str, role: OrganizationRole, permissions: List[str] = None) -> ServiceResult[OrganizationMember]:
        """Add member to organization"""
        try:
            sql = """
            INSERT INTO organization_members 
            (user_id, organization_id, role, permissions)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id, organization_id) 
            DO UPDATE SET 
                role = EXCLUDED.role,
                permissions = EXCLUDED.permissions,
                status = 'active',
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
            """
            
            import json
            row = await self.fetch_one(
                sql,
                user_id,
                organization_id,
                role.value,
                json.dumps(permissions or [])
            )
            
            if not row:
                return ServiceResult.error("Failed to add organization member")
            
            member = OrganizationMember(
                id=row['id'],
                user_id=row['user_id'],
                organization_id=row['organization_id'],
                role=OrganizationRole(row['role']),
                permissions=self._parse_json_field(row['permissions'], default_list=True),
                status=OrganizationMemberStatus(row['status']),
                joined_at=row['joined_at'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            
            return ServiceResult.success(member, "Organization member added successfully")
            
        except Exception as e:
            logger.error(f"Error adding organization member: {str(e)}")
            return ServiceResult.error(f"Failed to add organization member: {str(e)}")

    async def get_organization_members(self, organization_id: str) -> ServiceResult[List[OrganizationMember]]:
        """Get all members of an organization"""
        try:
            sql = """
            SELECT * FROM organization_members 
            WHERE organization_id = $1 
            ORDER BY created_at ASC
            """
            
            rows = await self.fetch_all(sql, organization_id)
            
            members = []
            for row in rows:
                member = OrganizationMember(
                    id=row['id'],
                    user_id=row['user_id'],
                    organization_id=row['organization_id'],
                    role=OrganizationRole(row['role']),
                    permissions=self._parse_json_field(row['permissions'], default_list=True),
                    status=OrganizationMemberStatus(row['status']),
                    joined_at=row['joined_at'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                members.append(member)
            
            return ServiceResult.success(members, f"Retrieved {len(members)} organization members")
            
        except Exception as e:
            logger.error(f"Error getting organization members: {str(e)}")
            return ServiceResult.error(f"Failed to get organization members: {str(e)}")

    async def update_organization_member(self, organization_id: str, user_id: str, update_data: OrganizationMemberUpdate) -> ServiceResult[OrganizationMember]:
        """Update organization member"""
        try:
            # Build dynamic update query
            update_fields = []
            params = []
            param_count = 1
            
            import json
            for field, value in update_data.dict(exclude_unset=True).items():
                if value is not None:
                    if field in ['role', 'status']:
                        update_fields.append(f"{field} = ${param_count}")
                        params.append(value.value)
                    elif field == 'permissions':
                        update_fields.append(f"{field} = ${param_count}")
                        params.append(json.dumps(value))
                    else:
                        update_fields.append(f"{field} = ${param_count}")
                        params.append(value)
                    param_count += 1
            
            if not update_fields:
                return ServiceResult.error("No fields to update")
            
            # Add updated_at
            update_fields.append(f"updated_at = ${param_count}")
            params.append(datetime.utcnow())
            param_count += 1
            
            # Add WHERE clause parameters
            params.extend([organization_id, user_id])
            
            sql = f"""
            UPDATE organization_members 
            SET {', '.join(update_fields)}
            WHERE organization_id = ${param_count} AND user_id = ${param_count + 1}
            RETURNING *
            """
            
            row = await self.fetch_one(sql, *params)
            
            if not row:
                return ServiceResult.error(f"Organization member not found: {user_id}")
            
            member = OrganizationMember(
                id=row['id'],
                user_id=row['user_id'],
                organization_id=row['organization_id'],
                role=OrganizationRole(row['role']),
                permissions=self._parse_json_field(row['permissions'], default_list=True),
                status=OrganizationMemberStatus(row['status']),
                joined_at=row['joined_at'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            
            return ServiceResult.success(member, "Organization member updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating organization member: {str(e)}")
            return ServiceResult.error(f"Failed to update organization member: {str(e)}")

    async def remove_organization_member(self, organization_id: str, user_id: str) -> ServiceResult[bool]:
        """Remove member from organization"""
        try:
            sql = "DELETE FROM organization_members WHERE organization_id = $1 AND user_id = $2"
            result = await self.execute(sql, organization_id, user_id)
            
            return ServiceResult.success(True, "Organization member removed successfully")
            
        except Exception as e:
            logger.error(f"Error removing organization member: {str(e)}")
            return ServiceResult.error(f"Failed to remove organization member: {str(e)}")

    async def get_user_organization_role(self, organization_id: str, user_id: str) -> ServiceResult[Dict[str, Any]]:
        """Get user's role and permissions in organization"""
        try:
            sql = """
            SELECT role, permissions, status 
            FROM organization_members 
            WHERE organization_id = $1 AND user_id = $2
            """
            
            row = await self.fetch_one(sql, organization_id, user_id)
            
            if not row:
                return ServiceResult.error(f"User not found in organization: {user_id}")
            
            result = {
                "role": row['role'],
                "permissions": row['permissions'] or [],
                "status": row['status']
            }
            
            return ServiceResult.success(result, "User organization role retrieved successfully")
            
        except Exception as e:
            logger.error(f"Error getting user organization role: {str(e)}")
            return ServiceResult.error(f"Failed to get user organization role: {str(e)}")