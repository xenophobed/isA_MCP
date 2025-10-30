#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Automation Progress Context Module

Universal progress tracking for web automation 5-step workflow.
Provides standardized progress reporting for browser automation operations.

5-Step Workflow Stages:
1. Capturing (20%) - Take initial screenshot
2. Understanding (40%) - Analyze page with Vision Model
3. Detecting (60%) - Detect UI elements and coordinates
4. Planning (80%) - Generate action sequence
5. Executing (100%) - Execute actions and verify results

Supported Operations: Basic automation, HIL authentication, Multi-step workflows
"""

from typing import Dict, Any, Optional
from mcp.server.fastmcp import Context
from tools.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class WebAutomationProgressReporter:
    """
    Universal progress reporting for web automation operations
    
    Provides standardized 5-step workflow progress tracking:
    1. Capturing (20%) - Screenshot capture
    2. Understanding (40%) - Screen understanding (Step 2)
    3. Detecting (60%) - UI detection (Step 3)
    4. Planning (80%) - Action reasoning (Step 4)
    5. Executing (100%) - Action execution (Step 5)
    
    Supports: Basic automation, HIL authentication, Multi-step workflows
    
    Example:
        reporter = WebAutomationProgressReporter(base_tool)
        
        # Step 1: Capturing
        await reporter.report_stage(ctx, "capturing", "automation", "taking screenshot")
        
        # Step 2: Understanding
        await reporter.report_stage(ctx, "understanding", "automation", "analyzing page")
        
        # Step 3: Detecting
        await reporter.report_stage(ctx, "detecting", "automation", "finding elements")
        
        # Step 4: Planning
        await reporter.report_stage(ctx, "planning", "automation", "generating actions")
        
        # Step 5: Executing with granular progress
        for i in range(1, total_actions + 1):
            await reporter.report_action_progress(ctx, i, total_actions, "click")
    """
    
    # 5-Step Automation Workflow Stages
    AUTOMATION_STAGES = {
        "capturing": {"step": 1, "weight": 20, "label": "Capturing"},
        "understanding": {"step": 2, "weight": 40, "label": "Understanding"},
        "detecting": {"step": 3, "weight": 60, "label": "Detecting"},
        "planning": {"step": 4, "weight": 80, "label": "Planning"},
        "executing": {"step": 5, "weight": 100, "label": "Executing"}
    }
    
    # HIL workflow stages (when human intervention is needed)
    HIL_STAGES = {
        "detecting_hil": {"step": 1, "weight": 33, "label": "Detecting HIL"},
        "checking_vault": {"step": 2, "weight": 67, "label": "Checking Vault"},
        "waiting_user": {"step": 3, "weight": 100, "label": "Waiting User"}
    }
    
    # Operation type display names
    OPERATION_NAMES = {
        "automation": "Web Automation",
        "hil": "HIL Authentication",
        "click": "Click Action",
        "type": "Type Action",
        "navigate": "Navigation",
        "form": "Form Filling"
    }
    
    # Stage-specific prefixes for logging
    STAGE_PREFIXES = {
        "capturing": "[📸 CAPTURE]",
        "understanding": "[🧠 UNDERSTAND]",
        "detecting": "[🎯 DETECT]",
        "planning": "[🤖 PLAN]",
        "executing": "[⚡ EXECUTE]",
        "detecting_hil": "[🤚 HIL-DETECT]",
        "checking_vault": "[🔐 VAULT-CHECK]",
        "waiting_user": "[⏳ WAIT-USER]"
    }
    
    def __init__(self, base_tool: BaseTool):
        """
        Initialize progress reporter
        
        Args:
            base_tool: BaseTool instance for accessing Context methods
        """
        self.base_tool = base_tool
    
    async def report_stage(
        self,
        ctx: Optional[Context],
        stage: str,
        operation_type: str,
        sub_progress: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        workflow_type: str = "automation"
    ):
        """
        Report progress for a workflow stage
        
        Args:
            ctx: MCP Context for progress reporting
            stage: Workflow stage name
            operation_type: Operation type - "automation", "hil"
            sub_progress: Optional granular progress within stage
            details: Optional additional details for logging
            workflow_type: Type of workflow - "automation" or "hil"
        
        Workflow Types & Stages:
            automation: capturing -> understanding -> detecting -> planning -> executing (5 stages)
            hil: detecting_hil -> checking_vault -> waiting_user (3 stages)
        
        Examples:
            # Normal automation
            await reporter.report_stage(ctx, "capturing", "automation", "screenshot.png")
            -> "Step 1/5 (20%): Capturing - screenshot.png"
            
            # Understanding page
            await reporter.report_stage(ctx, "understanding", "automation", "analyzing page type")
            -> "Step 2/5 (40%): Understanding - analyzing page type"
            
            # HIL detection
            await reporter.report_stage(ctx, "detecting_hil", "hil", "login page", workflow_type="hil")
            -> "Step 1/3 (33%): Detecting HIL - login page"
        """
        # Select the appropriate stage dictionary
        if workflow_type == "hil":
            stages = self.HIL_STAGES
            total_stages = 3
        else:
            stages = self.AUTOMATION_STAGES
            total_stages = 5
        
        if stage not in stages:
            logger.warning(f"Unknown stage '{stage}' for workflow type '{workflow_type}', skipping progress report")
            return
        
        stage_info = stages[stage]
        operation_name = self.OPERATION_NAMES.get(operation_type, operation_type.upper())
        
        # Build progress message
        message = f"{stage_info['label']}"
        
        # Add operation type if meaningful (skip redundant "automation")
        if operation_type not in ["automation"]:
            message += f" {operation_name}"
        
        if sub_progress:
            message += f" - {sub_progress}"
        
        # Report to Context
        await self.base_tool.report_progress(
            ctx,
            progress=stage_info["step"],
            total=total_stages,
            message=message
        )
        
        # Also log for debugging and HTTP mode fallback
        prefix = self.STAGE_PREFIXES.get(stage, "[INFO]")
        
        log_msg = f"{prefix} Stage {stage_info['step']}/{total_stages} ({stage_info['weight']}%): {message}"
        if details:
            log_msg += f" | {details}"
        
        await self.base_tool.log_info(ctx, log_msg)
    
    async def report_action_progress(
        self,
        ctx: Optional[Context],
        current: int,
        total: int,
        action_type: str = "action"
    ):
        """
        Report progress for individual action execution
        
        This is useful for tracking progress within Step 5 (Executing) when
        multiple actions are being performed sequentially.
        
        Args:
            ctx: MCP Context
            current: Current action number (1-indexed)
            total: Total number of actions
            action_type: Type of action being executed (click, type, scroll, etc.)
        
        Examples:
            # Executing click action
            await reporter.report_action_progress(ctx, 1, 5, "click")
            -> "Step 5/5 (100%): Executing - action 1/5 (click)"
            
            # Executing type action
            await reporter.report_action_progress(ctx, 2, 5, "type")
            -> "Step 5/5 (100%): Executing - action 2/5 (type)"
        """
        sub_progress = f"action {current}/{total} ({action_type})"
        await self.report_stage(ctx, "executing", "automation", sub_progress)
    
    async def report_hil_detection(
        self,
        ctx: Optional[Context],
        intervention_type: str,
        provider: str,
        details: Optional[str] = None
    ):
        """
        Report HIL detection progress
        
        Called when the system detects that human intervention is needed
        (login, CAPTCHA, payment, wallet connection, etc.)
        
        Args:
            ctx: MCP Context
            intervention_type: Type of intervention (login, captcha, payment, wallet, verification)
            provider: Provider name (google, facebook, metamask, stripe, etc.)
            details: Optional additional details about the detection
        
        Examples:
            # Login detected
            await reporter.report_hil_detection(ctx, "login", "google")
            -> "Step 1/3 (33%): Detecting HIL - login (google)"
            
            # CAPTCHA detected
            await reporter.report_hil_detection(ctx, "captcha", "recaptcha", "reCAPTCHA v2")
            -> "Step 1/3 (33%): Detecting HIL - captcha (recaptcha)"
        """
        sub_progress = f"{intervention_type} ({provider})"
        if details:
            sub_progress += f" - {details}"
        
        await self.report_stage(
            ctx, "detecting_hil", "hil", sub_progress,
            workflow_type="hil"
        )
    
    async def report_vault_check(
        self,
        ctx: Optional[Context],
        provider: str,
        has_credentials: bool,
        credential_type: str = "credentials"
    ):
        """
        Report Vault credential check progress
        
        Called after checking the Vault Service for stored credentials.
        
        Args:
            ctx: MCP Context
            provider: Provider name (google, stripe, metamask, etc.)
            has_credentials: Whether credentials were found in Vault
            credential_type: Type of credentials (credentials, payment, wallet)
        
        Examples:
            # Credentials found
            await reporter.report_vault_check(ctx, "google", True)
            -> "Step 2/3 (67%): Checking Vault - google (found in Vault)"
            
            # Credentials not found
            await reporter.report_vault_check(ctx, "stripe", False, "payment")
            -> "Step 2/3 (67%): Checking Vault - stripe (not found, need to add)"
        """
        if has_credentials:
            status = f"found in Vault"
        else:
            status = f"not found, need to add {credential_type}"
        
        sub_progress = f"{provider} ({status})"
        await self.report_stage(
            ctx, "checking_vault", "hil", sub_progress,
            workflow_type="hil"
        )
    
    async def report_screenshot(
        self,
        ctx: Optional[Context],
        screenshot_path: str,
        stage: str = "initial"
    ):
        """
        Report screenshot capture progress
        
        Args:
            ctx: MCP Context
            screenshot_path: Path to screenshot file
            stage: Screenshot stage ("initial" for Step 1, "final" for Step 5)
        
        Examples:
            # Initial screenshot (Step 1)
            await reporter.report_screenshot(ctx, "/tmp/screenshot_001.png", "initial")
            -> "Step 1/5 (20%): Capturing - initial screenshot"
            
            # Final screenshot (Step 5)
            await reporter.report_screenshot(ctx, "/tmp/screenshot_002.png", "final")
            -> "Step 5/5 (100%): Executing - final screenshot"
        """
        sub_progress = f"{stage} screenshot"
        
        if stage == "initial":
            await self.report_stage(ctx, "capturing", "automation", sub_progress)
        else:
            # Final screenshot is part of execution
            await self.report_stage(ctx, "executing", "automation", sub_progress)
    
    async def report_page_analysis(
        self,
        ctx: Optional[Context],
        page_type: str,
        elements_found: int
    ):
        """
        Report page analysis progress (Step 2: Understanding)
        
        Args:
            ctx: MCP Context
            page_type: Type of page detected (search_page, form, login, ecommerce, etc.)
            elements_found: Number of required elements identified
        
        Example:
            await reporter.report_page_analysis(ctx, "search_page", 2)
            -> "Step 2/5 (40%): Understanding - search_page (2 elements required)"
        """
        sub_progress = f"{page_type} ({elements_found} elements required)"
        await self.report_stage(ctx, "understanding", "automation", sub_progress)
    
    async def report_ui_detection(
        self,
        ctx: Optional[Context],
        elements_mapped: int,
        detection_success: bool = True
    ):
        """
        Report UI detection progress (Step 3: Detecting)
        
        Args:
            ctx: MCP Context
            elements_mapped: Number of UI elements successfully mapped
            detection_success: Whether detection was successful
        
        Examples:
            # Successful detection
            await reporter.report_ui_detection(ctx, 3, True)
            -> "Step 3/5 (60%): Detecting - 3 elements mapped"
            
            # Failed detection
            await reporter.report_ui_detection(ctx, 0, False)
            -> "Step 3/5 (60%): Detecting - detection failed, using fallback"
        """
        if detection_success:
            sub_progress = f"{elements_mapped} elements mapped"
        else:
            sub_progress = "detection failed, using fallback"
        
        await self.report_stage(ctx, "detecting", "automation", sub_progress)
    
    async def report_action_generation(
        self,
        ctx: Optional[Context],
        actions_generated: int,
        generation_method: str = "llm"
    ):
        """
        Report action generation progress (Step 4: Planning)
        
        Args:
            ctx: MCP Context
            actions_generated: Number of actions generated
            generation_method: Method used ("llm", "fallback", "template")
        
        Examples:
            await reporter.report_action_generation(ctx, 5, "llm")
            -> "Step 4/5 (80%): Planning - 5 actions generated (llm)"
        """
        sub_progress = f"{actions_generated} actions generated ({generation_method})"
        await self.report_stage(ctx, "planning", "automation", sub_progress)
    
    async def report_execution_summary(
        self,
        ctx: Optional[Context],
        executed: int,
        successful: int,
        failed: int
    ):
        """
        Report execution summary (Step 5: Executing completion)
        
        Args:
            ctx: MCP Context
            executed: Number of actions executed
            successful: Number of successful actions
            failed: Number of failed actions
        
        Example:
            await reporter.report_execution_summary(ctx, 5, 5, 0)
            -> "Step 5/5 (100%): Executing - completed: 5/5 successful, 0 failed"
        """
        sub_progress = f"completed: {successful}/{executed} successful, {failed} failed"
        await self.report_stage(ctx, "executing", "automation", sub_progress)
    
    async def report_complete(
        self,
        ctx: Optional[Context],
        operation_type: str,
        summary: Optional[Dict[str, Any]] = None
    ):
        """
        Report completion of entire workflow
        
        Args:
            ctx: MCP Context
            operation_type: Operation type ("automation", "hil")
            summary: Optional summary statistics
        
        Examples:
            # Successful automation
            await reporter.report_complete(ctx, "automation", {
                "actions_executed": 5,
                "actions_successful": 5,
                "task_completed": True,
                "final_url": "https://example.com/results"
            })
            -> "[✅ DONE] Web Automation complete | {'actions_executed': 5, ...}"
            
            # HIL required
            await reporter.report_complete(ctx, "hil", {
                "intervention_type": "login",
                "provider": "google",
                "action": "request_authorization"
            })
            -> "[🤚 DONE] HIL Authentication complete | {'intervention_type': 'login', ...}"
        """
        operation_name = self.OPERATION_NAMES.get(operation_type, operation_type.upper())
        
        # Choose appropriate emoji
        if operation_type == "hil":
            prefix = "[🤚 DONE]"
        elif summary and summary.get("task_completed"):
            prefix = "[✅ DONE]"
        elif summary and not summary.get("task_completed"):
            prefix = "[⚠️ DONE]"
        else:
            prefix = "[DONE]"
        
        message = f"{prefix} {operation_name} complete"
        
        if summary:
            # Format summary for readability
            summary_str = ", ".join([f"{k}={v}" for k, v in summary.items()])
            message += f" | {summary_str}"
        
        await self.base_tool.log_info(ctx, message)


class AutomationOperationDetector:
    """
    Utility class to detect and categorize automation operations
    """
    
    @classmethod
    def detect_operation_type(cls, task: str, url: str) -> str:
        """
        Detect operation type from task and URL
        
        Args:
            task: Task description
            url: Target URL
        
        Returns:
            Operation type: "search", "form", "navigation", "extraction"
        
        Examples:
            detect_operation_type("search for airpods", "https://google.com") -> "search"
            detect_operation_type("fill form", "https://example.com/register") -> "form"
        """
        task_lower = task.lower()
        
        if any(word in task_lower for word in ['search', 'find', 'look for']):
            return "search"
        elif any(word in task_lower for word in ['fill', 'submit', 'register', 'sign up']):
            return "form"
        elif any(word in task_lower for word in ['login', 'sign in', 'authenticate']):
            return "authentication"
        elif any(word in task_lower for word in ['click', 'select', 'choose']):
            return "navigation"
        else:
            return "automation"
    
    @classmethod
    def estimate_action_count(cls, task: str) -> int:
        """
        Estimate number of actions from task description
        
        Args:
            task: Task description
        
        Returns:
            Estimated number of actions (minimum 1)
        
        Example:
            estimate_action_count("search for python") -> 3 (click input, type, press enter)
            estimate_action_count("fill name and email") -> 4 (click name, type, click email, type)
        """
        task_lower = task.lower()
        
        # Count action keywords
        action_count = 0
        action_keywords = ['click', 'type', 'fill', 'select', 'submit', 'press', 'search']
        
        for keyword in action_keywords:
            action_count += task_lower.count(keyword)
        
        # Count conjunctions as indicators of multiple actions
        action_count += task_lower.count(' and ')
        action_count += task_lower.count(',')
        
        # Default to at least 1 action, max reasonable estimate is 10
        return min(max(action_count, 1), 10)


