#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Automation Tools - Clean MCP Tool Wrapper

Thin MCP wrapper for web automation functionality.
All business logic is in WebAutomationService.

Core Function:
- web_automation: 5-step atomic workflow for browser automation with HIL support

Architecture:
- This file: MCP tool interface + progress tracking
- web_automation_service.py: Business logic for 5-step workflow
- automation_progress_context.py: Progress reporting for 5 steps
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP, Context
from tools.base_tool import BaseTool
from tools.services.web_services.services.web_automation_service import WebAutomationService
from tools.services.web_services.tools.context.automation_progress_context import (
    WebAutomationProgressReporter,
    AutomationOperationDetector
)
from core.security import SecurityLevel, get_security_manager
from core.logging import get_logger

logger = get_logger(__name__)


class WebAutomationTool(BaseTool):
    """Web automation tool with progress tracking"""
    
    def __init__(self):
        super().__init__()
        self.automation_service = None
        self.progress_reporter = WebAutomationProgressReporter(self)
    
    def _get_automation_service(self):
        """Lazy initialize automation service"""
        if self.automation_service is None:
            self.automation_service = WebAutomationService()
        return self.automation_service
    
    async def cleanup(self):
        """Cleanup automation service"""
        if self.automation_service:
            await self.automation_service.close()
            self.automation_service = None


def register_web_automation_tools(mcp: FastMCP):
    """Register web automation tool with MCP"""
    web_tool = WebAutomationTool()
    security_manager = get_security_manager()
    
    @mcp.tool()
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def web_automation(
        url: str,
        task: str,
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Automate web browser interactions using 5-step atomic workflow
        
        This tool provides intelligent browser automation with human-in-loop support.
        It uses a 5-step workflow combining Vision Models and Playwright for reliable
        web interaction.
        
        5-Step Workflow:
        1. 📸 Capturing (20%) - Take initial screenshot of the page
        2. 🧠 Understanding (40%) - Analyze page with Vision Model to understand structure
        3. 🎯 Detecting (60%) - Detect UI elements and map coordinates
        4. 🤖 Planning (80%) - Generate optimal action sequence for the task
        5. ⚡ Executing (100%) - Execute actions and verify results
        
        Human-in-Loop (HIL) Support:
        Automatically detects when human intervention is needed for:
        - 🔐 Login/Authentication (OAuth, username/password)
        - 💳 Payment authorization (Stripe, PayPal, Apple Pay)
        - 🦊 Wallet connections (MetaMask, Coinbase, WalletConnect)
        - 🤖 CAPTCHA solving (reCAPTCHA, hCaptcha)
        - ✅ Age verification and cookie consent
        
        HIL Actions:
        - request_authorization: Credentials found in Vault, asks user permission to use
        - ask_human: Credentials not found, asks user to provide or complete manually
        
        Supported Actions (15+):
        - Basic: click, type, scroll, hover, navigate
        - Forms: select dropdown, checkbox, radio buttons
        - Advanced: iframe handling, file upload/download, drag-and-drop
        - Wait strategies: selector, text, URL, timeout
        
        Keywords: automation, browser, interact, task, web, hil, login, auth, 
                  click, type, form, submit, search, fill, playwright, selenium
        Category: web
        
        Args:
            url: Target web page URL (must start with http:// or https://)
            task: Natural language task description
                  Examples:
                  - "search for python programming"
                  - "fill name 'John Doe', email 'john@example.com', submit form"
                  - "login with my Google account"
                  - "add item to cart and checkout"
            user_id: User identifier for credential lookup in Vault (default: "default")
        
        Returns:
            Dict with status, data, and results
            
            Success response:
            {
                "status": "success",
                "action": "web_automation",
                "data": {
                    "success": true,
                    "initial_url": "https://...",
                    "final_url": "https://...",
                    "task": "search for airpods",
                    "workflow_results": {
                        "step1_screenshot": "/tmp/xxx.png",
                        "step2_analysis": {...},
                        "step3_ui_detection": 3,
                        "step4_actions": [...],
                        "step5_execution": {...}
                    },
                    "result_description": "Task completed successfully"
                }
            }
            
            HIL response (request_authorization):
            {
                "status": "authorization_required",
                "action": "request_authorization",
                "message": "Found stored credentials for Google. Do you authorize using them?",
                "data": {
                    "intervention_type": "login",
                    "provider": "google",
                    "credential_preview": {
                        "vault_id": "vault_xxx",
                        "provider": "google"
                    },
                    "screenshot": "/tmp/xxx.png"
                }
            }
            
            HIL response (ask_human):
            {
                "status": "credential_required",
                "action": "ask_human",
                "message": "CAPTCHA detected. Please solve the CAPTCHA manually.",
                "data": {
                    "intervention_type": "captcha",
                    "screenshot": "/tmp/xxx.png",
                    "instructions": "Please solve the CAPTCHA and notify when complete"
                }
            }
        
        Examples:
            # Basic search
            web_automation(
                url="https://www.google.com",
                task="search for python programming"
            )
            
            # E-commerce interaction
            web_automation(
                url="https://www.amazon.com",
                task="search for wireless headphones, filter by prime, click first result"
            )
            
            # Form filling
            web_automation(
                url="https://example.com/register",
                task="fill name 'John Doe', email 'john@example.com', select country 'USA', check terms, submit"
            )
            
            # Login (triggers HIL if credentials needed)
            web_automation(
                url="https://accounts.google.com",
                task="login to gmail",
                user_id="user123"
            )
            
            # Multi-step workflow
            web_automation(
                url="https://github.com",
                task="go to search, type 'python async', press enter, click first repo"
            )

        Notes:
            - The tool takes screenshots at key stages for debugging and verification
            - All actions are logged with detailed progress reporting
            - Failed actions don't stop execution by default (configurable in service)
            - Session state is not persisted between calls (use Agent layer for session management)
            - Credentials are securely stored in Vault Service and require explicit user authorization
        """
        # Create progress operation at start (NEW WAY)
        operation_id = await web_tool.create_progress_operation(
            metadata={
                "user_id": user_id,
                "url": url[:100],
                "task": task[:100],
                "operation": "web_automation"
            }
        )

        try:
            # Detect operation type for better logging
            operation_type = AutomationOperationDetector.detect_operation_type(task, url)

            await web_tool.log_info(
                ctx,
                f"🚀 Starting web automation: '{task}' on {url} (type: {operation_type})"
            )

            # Step 1: Capturing - Report initial progress
            await web_tool.progress_reporter.report_stage(
                operation_id, "capturing", "automation", f"loading {url[:50]}..."
            )
            
            # Get automation service (lazy initialization)
            service = web_tool._get_automation_service()
            
            # Execute automation task
            result = await service.execute_task(
                url=url,
                task=task,
                user_id=user_id
            )
            
            # Check if HIL is required
            if result.get("hil_required"):
                intervention_type = result.get("data", {}).get("intervention_type", "unknown")
                provider = result.get("data", {}).get("provider", "unknown")
                details = result.get("data", {}).get("details", "")
                
                # Report HIL detection (Step 1 of HIL workflow)
                await web_tool.progress_reporter.report_hil_detection(
                    operation_id, intervention_type, provider, details
                )

                # Check Vault status (Step 2 of HIL workflow)
                has_credentials = result.get("action") == "request_authorization"
                credential_type = {
                    "login": "credentials",
                    "payment": "payment method",
                    "wallet": "wallet"
                }.get(intervention_type, "credentials")

                await web_tool.progress_reporter.report_vault_check(
                    operation_id, provider, has_credentials, credential_type
                )
                
                # Log HIL message
                await web_tool.log_info(
                    ctx,
                    f"🤚 HIL required: {result.get('message')}"
                )
                
                # Report completion for HIL workflow
                await web_tool.progress_reporter.report_complete(
                    "hil",
                    {
                        "intervention_type": intervention_type,
                        "provider": provider,
                        "action": result.get("action"),
                        "has_credentials": has_credentials
                    }
                )
                
                # Extract context info
                context_info = web_tool.extract_context_info(ctx, user_id)
                
                # Return HIL response
                return web_tool.create_response(
                    status=result.get("status", "human_required"),
                    action=result.get("action", "ask_human"),
                    data={
                        **result.get("data", {}),
                        "context": context_info
                    },
                    error_message=result.get("message")
                )
            
            # Normal automation workflow completed
            if result.get("success"):
                workflow = result.get("workflow_results", {})
                
                # Report Step 2: Understanding
                step2 = workflow.get("step2_analysis", {})
                page_type = step2.get("page_type", "unknown")
                elements_required = len(step2.get("required_elements", []))

                await web_tool.progress_reporter.report_page_analysis(
                    operation_id, page_type, elements_required
                )

                # Report Step 3: Detecting
                elements_mapped = workflow.get("step3_ui_detection", 0)
                await web_tool.progress_reporter.report_ui_detection(
                    operation_id, elements_mapped, elements_mapped > 0
                )

                # Report Step 4: Planning
                actions = workflow.get("step4_actions", [])
                await web_tool.progress_reporter.report_action_generation(
                    operation_id, len(actions), "llm"
                )
                
                # Report Step 5: Executing (with action-by-action progress)
                execution = workflow.get("step5_execution", {})
                executed = execution.get("actions_executed", 0)
                successful = execution.get("actions_successful", 0)
                failed = execution.get("actions_failed", 0)
                
                # Report individual actions if available
                execution_details = execution.get("execution_details", {})
                action_results = execution_details.get("results", [])
                
                for i, action_result in enumerate(action_results, 1):
                    action_type = action_result.get("action_type", "unknown")
                    await web_tool.progress_reporter.report_action_progress(
                        operation_id, i, len(action_results), action_type
                    )

                # Report execution summary
                await web_tool.progress_reporter.report_execution_summary(
                    operation_id, executed, successful, failed
                )
                
                # Final logging
                task_completed = execution.get("task_completed", False)
                await web_tool.log_info(
                    ctx,
                    f"✅ Automation complete: {executed} actions executed, "
                    f"{successful} successful, {failed} failed, "
                    f"task_completed: {task_completed}"
                )
                
                # Report completion
                await web_tool.progress_reporter.report_complete(
                    "automation",
                    {
                        "actions_executed": executed,
                        "actions_successful": successful,
                        "actions_failed": failed,
                        "task_completed": task_completed,
                        "initial_url": result.get("initial_url"),
                        "final_url": result.get("final_url")
                    }
                )

                # Complete progress operation
                await web_tool.complete_progress_operation(
                    operation_id,
                    result={
                        "actions_executed": executed,
                        "task_completed": task_completed
                    }
                )
            else:
                # Automation failed
                await web_tool.log_error(
                    ctx,
                    f"❌ Automation failed: {result.get('error', 'Unknown error')}"
                )
            
            # Extract context info
            context_info = web_tool.extract_context_info(ctx, user_id)
            
            # Return response
            if result.get("success"):
                return web_tool.create_response(
                    "success",
                    "web_automation",
                    {
                        **result,
                        "operation_id": operation_id,  # ✅ Return operation_id for SSE monitoring
                        "context": context_info
                    }
                )
            else:
                return web_tool.create_response(
                    "error",
                    "web_automation",
                    {
                        "url": url,
                        "task": task,
                        "error_details": result.get("error"),
                        "context": context_info
                    },
                    result.get("error", "Unknown error")
                )
        
        except Exception as e:
            # Fail progress operation on error
            if 'operation_id' in locals():
                await web_tool.fail_progress_operation(operation_id, str(e))

            logger.exception(f"Web automation failed: {e}")
            await web_tool.log_error(ctx, f"❌ Web automation failed: {str(e)}")

            # Extract context even in error case
            context_info = web_tool.extract_context_info(ctx, user_id)
            
            return web_tool.create_response(
                "error",
                "web_automation",
                {
                    "url": url,
                    "task": task,
                    "context": context_info
                },
                f"Automation failed: {str(e)}"
            )
        finally:
            # Cleanup service
            await web_tool.cleanup()
    
    print("✅ Web Automation Tools registered: 1 enhanced function")
    print("🤖 web_automation: 5-step workflow + HIL support + progress tracking")
    print("📊 Features:")
    print("   - 5-step atomic workflow with Vision Model")
    print("   - HIL authentication (login, payment, wallet, CAPTCHA)")
    print("   - 15+ action types (click, type, select, scroll, iframe, upload, etc.)")
    print("   - Real-time progress reporting for all 5 steps")
    print("   - Vault integration for secure credential storage")


