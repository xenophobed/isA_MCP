#!/usr/bin/env python3
"""
HIL Example Tools - Test all 4 core HIL methods

This module provides example tools to test the 4 core Human-in-Loop interaction methods:
1. request_authorization() - Authorization for operations
2. request_input() - Collect user input
3. request_review() - Review and edit content
4. request_input_with_authorization() - Combined input + authorization
"""

from typing import Dict, Any, Optional, Annotated
from pydantic import Field
from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from tools.base_tool import BaseTool
from core.security import SecurityLevel
from core.logging import get_logger

logger = get_logger(__name__)


class HILExampleTool(BaseTool):
    """Example tool demonstrating all 4 HIL methods"""

    def __init__(self):
        super().__init__()

    def register_tools(self, mcp):
        """Register all HIL example tools"""

        # =====================================================================
        # Scenario 1: Authorization - Approve/Reject operations
        # =====================================================================

        self.register_tool(
            mcp,
            self.test_authorization_low_risk,
            name="test_authorization_low_risk",
            description="Test authorization HIL low-risk operation cache configuration approve reject",
            security_level=SecurityLevel.LOW,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        self.register_tool(
            mcp,
            self.test_authorization_high_risk,
            name="test_authorization_high_risk",
            description="Test authorization HIL high-risk payment transaction approve reject",
            security_level=SecurityLevel.LOW,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        self.register_tool(
            mcp,
            self.test_authorization_critical_risk,
            name="test_authorization_critical_risk",
            description="Test authorization HIL critical-risk database deletion approve reject destructive",
            security_level=SecurityLevel.LOW,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        # =====================================================================
        # Scenario 2: Input - Collect user information
        # =====================================================================

        self.register_tool(
            mcp,
            self.test_input_credentials,
            name="test_input_credentials",
            description="Test input HIL credentials collection API key submit skip cancel",
            security_level=SecurityLevel.LOW,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        self.register_tool(
            mcp,
            self.test_input_selection,
            name="test_input_selection",
            description="Test input HIL selection deployment environment choose options",
            security_level=SecurityLevel.LOW,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        self.register_tool(
            mcp,
            self.test_input_augmentation,
            name="test_input_augmentation",
            description="Test input HIL augmentation requirements enhancement user provide additional",
            security_level=SecurityLevel.LOW,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        # =====================================================================
        # Scenario 3: Review - Review and optionally edit content
        # =====================================================================

        self.register_tool(
            mcp,
            self.test_review_execution_plan,
            name="test_review_execution_plan",
            description="Test review HIL execution plan editable approve edit reject deployment",
            security_level=SecurityLevel.LOW,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        self.register_tool(
            mcp,
            self.test_review_generated_code,
            name="test_review_generated_code",
            description="Test review HIL generated code editable approve edit reject security",
            security_level=SecurityLevel.LOW,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        self.register_tool(
            mcp,
            self.test_review_config_readonly,
            name="test_review_config_readonly",
            description="Test review HIL configuration readonly approve reject production",
            security_level=SecurityLevel.LOW,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        # =====================================================================
        # Scenario 4: Input + Authorization - Combined flow
        # =====================================================================

        self.register_tool(
            mcp,
            self.test_input_with_auth_payment,
            name="test_input_with_auth_payment",
            description="Test input-authorization HIL payment amount enter approve combined flow",
            security_level=SecurityLevel.LOW,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        self.register_tool(
            mcp,
            self.test_input_with_auth_deployment,
            name="test_input_with_auth_deployment",
            description="Test input-authorization HIL deployment configuration critical approve combined",
            security_level=SecurityLevel.LOW,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        # =====================================================================
        # Utility
        # =====================================================================

        self.register_tool(
            mcp,
            self.test_all_hil_scenarios,
            name="test_all_hil_scenarios",
            description="List all available HIL test scenarios methods tools information",
            security_level=SecurityLevel.LOW,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        logger.info(f"Registered {len(self.registered_tools)} HIL example tools")

    # =========================================================================
    # Scenario 1: Authorization implementations
    # =========================================================================

    async def test_authorization_low_risk(
        self,
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Test authorization HIL with LOW risk operation"""
        await self.log_info(ctx, "Testing LOW risk authorization")

        return self.request_authorization(
            action="Update cache TTL configuration",
            reason="Increase cache duration from 5 minutes to 10 minutes to improve performance",
            risk_level="low",
            context={
                "setting": "cache_ttl",
                "old_value": 300,
                "new_value": 600,
                "affected_services": ["api-gateway", "web-frontend"]
            }
        )

    async def test_authorization_high_risk(
        self,
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Test authorization HIL with HIGH risk operation"""
        await self.log_info(ctx, "Testing HIGH risk authorization")

        return self.request_authorization(
            action="Process $5000 payment to vendor",
            reason="Complete payment for invoice INV-2024-001 to Acme Corp for cloud infrastructure services",
            risk_level="high",
            context={
                "amount": 5000.00,
                "currency": "USD",
                "vendor": "Acme Corp",
                "invoice_id": "INV-2024-001",
                "payment_method": "Stripe",
                "account_balance": 25000.00
            }
        )

    async def test_authorization_critical_risk(
        self,
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Test authorization HIL with CRITICAL risk operation"""
        await self.log_info(ctx, "Testing CRITICAL risk authorization")

        return self.request_authorization(
            action="Delete production database table",
            reason="Remove deprecated 'legacy_customers' table that has been migrated to new schema",
            risk_level="critical",
            context={
                "database": "production_db",
                "table": "legacy_customers",
                "row_count": 50000,
                "size_mb": 250,
                "last_accessed": "2024-01-15",
                "backup_created": True,
                "irreversible": True
            }
        )

    # =========================================================================
    # Scenario 2: Input implementations
    # =========================================================================

    async def test_input_credentials(
        self,
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Test input HIL for credentials collection"""
        await self.log_info(ctx, "Testing credentials input")

        return self.request_input(
            input_type="credentials",
            prompt="Enter OpenAI API Key",
            description=(
                "Provide your OpenAI API key to enable AI-powered features in the system.\n\n"
                "The key should start with 'sk-' and be 51 characters long.\n"
                "Your key will be securely stored and never logged."
            ),
            schema={
                "type": "string",
                "pattern": "^sk-[A-Za-z0-9]{48}$",
                "minLength": 51,
                "maxLength": 51
            },
            default_value="sk-..."
        )

    async def test_input_selection(
        self,
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Test input HIL for selection from options"""
        await self.log_info(ctx, "Testing selection input")

        return self.request_input(
            input_type="selection",
            prompt="Choose deployment environment",
            description=(
                "Select the target environment for deploying the application.\n\n"
                "• development - For local testing\n"
                "• staging - For QA and integration testing\n"
                "• production - For live users (requires additional authorization)"
            ),
            suggestions=["development", "staging", "production"]
        )

    async def test_input_augmentation(
        self,
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Test input HIL for data augmentation"""
        await self.log_info(ctx, "Testing augmentation input")

        return self.request_input(
            input_type="augmentation",
            prompt="Add more requirements",
            description=(
                "The AI has generated initial project requirements based on your description.\n"
                "Please review and add any missing details, edge cases, or additional requirements.\n\n"
                "Current requirements cover basic functionality, but you may want to add:\n"
                "• Non-functional requirements (performance, security, scalability)\n"
                "• Edge cases and error handling\n"
                "• Integration requirements\n"
                "• Compliance and regulatory needs"
            ),
            current_data={
                "requirements": [
                    "User authentication and authorization",
                    "CRUD operations for customer data",
                    "RESTful API endpoints"
                ]
            },
            suggestions=[
                "Add performance requirements (response time, throughput)",
                "Define security requirements (encryption, authentication)",
                "Specify error handling and logging requirements",
                "Include monitoring and alerting requirements"
            ]
        )

    # =========================================================================
    # Scenario 3: Review implementations
    # =========================================================================

    async def test_review_execution_plan(
        self,
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Test review HIL for execution plan (editable)"""
        await self.log_info(ctx, "Testing execution plan review")

        sample_plan = {
            "plan_id": "plan_test_123",
            "plan_title": "E-commerce Website Deployment Plan",
            "solution_hypothesis": "Deploy using blue-green strategy to minimize downtime",
            "execution_mode": "sequential",
            "total_tasks": 4,
            "tasks": [
                {
                    "id": 1,
                    "title": "Prepare deployment environment",
                    "description": "Set up new production environment with required infrastructure",
                    "tools": ["terraform", "kubectl"],
                    "priority": "high",
                    "status": "pending"
                },
                {
                    "id": 2,
                    "title": "Deploy application to staging",
                    "description": "Deploy new version to staging environment for final validation",
                    "tools": ["docker", "kubernetes"],
                    "priority": "high",
                    "status": "pending"
                },
                {
                    "id": 3,
                    "title": "Run smoke tests",
                    "description": "Execute automated smoke tests to verify deployment",
                    "tools": ["pytest", "selenium"],
                    "priority": "high",
                    "status": "pending"
                },
                {
                    "id": 4,
                    "title": "Switch traffic to new deployment",
                    "description": "Update load balancer to route traffic to new version",
                    "tools": ["kubectl", "monitoring"],
                    "priority": "critical",
                    "status": "pending"
                }
            ]
        }

        return self.request_review(
            content=sample_plan,
            content_type="execution_plan",
            instructions=(
                "Review this deployment execution plan before starting autonomous execution.\n\n"
                f"Plan contains {len(sample_plan['tasks'])} tasks in {sample_plan['execution_mode']} mode.\n"
                f"Solution hypothesis: {sample_plan['solution_hypothesis']}\n\n"
                "You can:\n"
                "• Approve - Start execution immediately\n"
                "• Edit - Modify tasks, reorder, add/remove steps\n"
                "• Reject - Cancel and create a different plan"
            ),
            editable=True,
            timeout=600
        )

    async def test_review_generated_code(
        self,
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Test review HIL for generated code (editable)"""
        await self.log_info(ctx, "Testing generated code review")

        sample_code = '''def process_payment(amount: float, customer_id: str) -> Dict[str, Any]:
    """Process a payment transaction for a customer"""
    # Validate input
    if amount <= 0:
        raise ValueError("Amount must be positive")

    if not customer_id:
        raise ValueError("Customer ID is required")

    # Process payment through Stripe
    try:
        charge = stripe.Charge.create(
            amount=int(amount * 100),
            currency="usd",
            customer=customer_id,
            description="Payment transaction"
        )

        return {
            "status": "success",
            "transaction_id": charge.id,
            "amount": amount,
            "currency": "usd"
        }
    except stripe.error.CardError as e:
        return {
            "status": "failed",
            "error": str(e)
        }'''

        return self.request_review(
            content=sample_code,
            content_type="code",
            instructions=(
                "Review the generated payment processing code.\n\n"
                "Please check for:\n"
                "• Security vulnerabilities (input validation, error handling)\n"
                "• Best practices (error messages, logging)\n"
                "• Edge cases (negative amounts, empty customer ID)\n"
                "• Code quality (naming, comments, structure)\n\n"
                "You can edit the code directly or approve/reject as is."
            ),
            editable=True
        )

    async def test_review_config_readonly(
        self,
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Test review HIL for configuration (read-only)"""
        await self.log_info(ctx, "Testing config review (readonly)")

        sample_config = {
            "database": {
                "host": "prod-db.example.com",
                "port": 5432,
                "name": "production_db",
                "ssl": True,
                "max_connections": 100
            },
            "cache": {
                "host": "redis.example.com",
                "port": 6379,
                "ttl": 600
            },
            "api": {
                "rate_limit": 1000,
                "timeout": 30,
                "retry_attempts": 3
            }
        }

        return self.request_review(
            content=sample_config,
            content_type="config",
            instructions=(
                "Review the current production configuration before applying changes.\n\n"
                "This is a read-only review - you can approve or reject but not edit.\n"
                "If changes are needed, reject and modify the configuration separately."
            ),
            editable=False
        )

    # =========================================================================
    # Scenario 4: Input + Authorization implementations
    # =========================================================================

    async def test_input_with_auth_payment(
        self,
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Test input + authorization HIL for payment"""
        await self.log_info(ctx, "Testing input with authorization (payment)")

        return self.request_input_with_authorization(
            input_prompt="Enter payment amount",
            input_description=(
                "Specify the amount (in USD) to pay vendor Acme Corp.\n\n"
                "Invoice: INV-2024-001\n"
                "Current balance: $25,000.00\n"
                "Maximum single payment: $10,000.00"
            ),
            authorization_reason=(
                "After entering the amount, you will be asked to authorize the payment transaction.\n"
                "This is a high-risk operation that will be executed immediately upon approval."
            ),
            input_type="number",
            risk_level="high",
            schema={
                "type": "number",
                "minimum": 0.01,
                "maximum": 10000.00
            },
            context={
                "vendor": "Acme Corp",
                "invoice_id": "INV-2024-001",
                "payment_method": "Stripe",
                "account_balance": 25000.00
            }
        )

    async def test_input_with_auth_deployment(
        self,
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Test input + authorization HIL for deployment configuration"""
        await self.log_info(ctx, "Testing input with authorization (deployment)")

        return self.request_input_with_authorization(
            input_prompt="Enter production deployment configuration",
            input_description=(
                "Provide the environment variables and configuration settings for production deployment.\n\n"
                "Required variables:\n"
                "• DATABASE_URL\n"
                "• API_KEY\n"
                "• REDIS_URL\n"
                "• LOG_LEVEL\n\n"
                "Format: JSON object with key-value pairs"
            ),
            authorization_reason=(
                "After providing the configuration, you must authorize the production deployment.\n\n"
                "⚠️ CRITICAL OPERATION ⚠️\n"
                "This will deploy to production and affect live users.\n"
                "Ensure all configuration values are correct before approving."
            ),
            input_type="text",
            risk_level="critical",
            schema={
                "type": "object",
                "required": ["DATABASE_URL", "API_KEY", "REDIS_URL", "LOG_LEVEL"]
            },
            context={
                "environment": "production",
                "service": "api-gateway",
                "current_version": "v1.2.3",
                "target_version": "v1.3.0"
            }
        )

    # =========================================================================
    # Utility
    # =========================================================================

    async def test_all_hil_scenarios(
        self,
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """List all available HIL test scenarios"""
        await self.log_info(ctx, "Listing all HIL test scenarios")

        return self.create_response(
            "success",
            "test_all_hil_scenarios",
            {
                "hil_methods": [
                    {
                        "method": "request_authorization()",
                        "description": "工具授权运行 - Approve/reject operations",
                        "test_tools": [
                            "test_authorization_low_risk",
                            "test_authorization_high_risk",
                            "test_authorization_critical_risk"
                        ],
                        "options": ["approve", "reject"]
                    },
                    {
                        "method": "request_input()",
                        "description": "让用户提供信息 - Collect user input or augment data",
                        "test_tools": [
                            "test_input_credentials",
                            "test_input_selection",
                            "test_input_augmentation"
                        ],
                        "options": ["submit", "skip", "cancel"]
                    },
                    {
                        "method": "request_review()",
                        "description": "让用户 edit - Review and optionally edit content",
                        "test_tools": [
                            "test_review_execution_plan",
                            "test_review_generated_code",
                            "test_review_config_readonly"
                        ],
                        "options": ["approve", "edit", "reject"]
                    },
                    {
                        "method": "request_input_with_authorization()",
                        "description": "提供信息并授权 - Input data and authorize action",
                        "test_tools": [
                            "test_input_with_auth_payment",
                            "test_input_with_auth_deployment"
                        ],
                        "options": ["approve_with_input", "cancel"]
                    }
                ],
                "total_test_tools": 12,
                "usage": "Call any of the test tools above to trigger the corresponding HIL scenario"
            }
        )


# ============================================================================
# Registration - Auto-discovery
# ============================================================================

def register_hil_example_tools(mcp):
    """
    Register HIL example tools

    IMPORTANT: Function name must match pattern: register_{filename}(mcp)
    For hil_example_tools.py, function must be: register_hil_example_tools(mcp)

    This allows auto-discovery system to find and register tools
    """
    tool = HILExampleTool()
    tool.register_tools(mcp)
    return tool
