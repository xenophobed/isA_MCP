#!/usr/bin/env python
"""
Client Interaction Tools for MCP Server
Handles human-in-the-loop interactions and response formatting
"""
import json
from datetime import datetime

from core.security import get_security_manager
from core.monitoring import monitor_manager
from core.logging import get_logger

logger = get_logger(__name__)

def register_client_interaction_tools(mcp):
    """Register all client interaction tools with the MCP server"""
    
    # Get security manager for applying decorators
    security_manager = get_security_manager()
    
    @mcp.tool()
    @security_manager.security_check
    async def ask_human(question: str, context: str = "", user_id: str = "default") -> str:
        """Ask the human for additional information or clarification
        
        This tool provides a standardized way for the system to request
        human input or clarification during operations.
        
        Keywords: human, interaction, input, question, clarification, communication
        Category: client
        """
        # This tool provides a standardized way for the client to request human input
        # The actual human interaction happens on the client side
        
        result = {
            "status": "human_input_requested",
            "action": "ask_human",
            "data": {
                "question": question,
                "context": context,
                "user_id": user_id,
                "instruction": "This request requires human input. The client should handle the interaction."
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Human input requested: '{question}' by {user_id}")
        return json.dumps(result)

    @mcp.tool()
    @security_manager.security_check
    async def request_authorization(tool_name: str, reason: str, user_id: str = "default", tool_args: dict | None = None) -> str:
        """Request human authorization before executing a tool
        
        This tool provides a standardized way to request authorization
        before executing potentially sensitive or high-impact operations.
        
        Keywords: authorization, security, approval, permission, human, verification
        Category: client
        """
        # This tool provides a standardized way for authorization requests
        # The actual authorization happens on the client side or through the security manager
        
        # Handle None tool_args
        if tool_args is None:
            tool_args = {}
        
        # Create authorization request through security manager
        auth_manager = security_manager.auth_manager
        from core.security import SecurityLevel
        
        # Determine security level based on tool name
        security_level = SecurityLevel.MEDIUM
        if "forget" in tool_name.lower() or "delete" in tool_name.lower():
            security_level = SecurityLevel.HIGH
        elif "admin" in tool_name.lower():
            security_level = SecurityLevel.CRITICAL
        
        auth_request = auth_manager.create_request(
            tool_name, tool_args, user_id, security_level, reason
        )
        
        result = {
            "status": "authorization_requested",
            "action": "request_authorization",
            "data": {
                "request_id": auth_request.id,
                "tool_name": tool_name,
                "tool_args": tool_args,
                "reason": reason,
                "security_level": security_level.name,
                "user_id": user_id,
                "expires_at": auth_request.expires_at.isoformat(),
                "instruction": "This request requires authorization. The client should handle the approval process."
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Authorization requested for {tool_name} by {user_id}")
        return json.dumps(result)

    @mcp.tool()
    @security_manager.security_check
    async def check_security_status(include_metrics: bool = False, user_id: str = "default") -> str:
        """Check the security and monitoring status of the system
        
        This tool provides an overview of system security status,
        including violations, rate limits, and overall health metrics.
        
        Keywords: security, status, monitoring, health, metrics, system
        Category: client
        """
        try:
            # Get monitoring metrics
            metrics = monitor_manager.get_metrics()
            
            # Get security manager status
            auth_manager = security_manager.auth_manager
            pending_requests = len([req for req in auth_manager.pending_requests.values() 
                                  if req.status.value == "pending"])
            
            # Calculate security indicators
            total_requests = metrics.get("total_requests", 0)
            security_violations = metrics.get("security_violations", 0)
            rate_limit_hits = metrics.get("rate_limit_hits", 0)
            
            security_score = "HIGH"
            if security_violations > 0 or rate_limit_hits > 10:
                security_score = "MEDIUM"
            if security_violations > 5 or rate_limit_hits > 50:
                security_score = "LOW"
            
            status_data = {
                "security_score": security_score,
                "pending_authorizations": pending_requests,
                "security_violations": security_violations,
                "rate_limit_hits": rate_limit_hits,
                "total_requests": total_requests,
                "uptime": metrics.get("uptime", 0)
            }
            
            if include_metrics:
                status_data["detailed_metrics"] = metrics
                status_data["recent_logs"] = monitor_manager.request_history[-10:]
            
            result = {
                "status": "success",
                "action": "check_security_status",
                "data": status_data,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Security status checked by {user_id}")
            return json.dumps(result)
            
        except Exception as e:
            error_result = {
                "status": "error",
                "action": "check_security_status",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error(f"Security status check failed: {e}")
            return json.dumps(error_result)

    @mcp.tool()
    @security_manager.security_check
    async def format_response(content: str, format_type: str = "structured", user_id: str = "default") -> str:
        """Format responses with enhanced structure and guardrails
        
        This tool formats and structures responses in various formats
        including JSON, markdown, and security summaries for better presentation.
        
        Keywords: format, response, structure, presentation, json, markdown
        Category: client
        """
        try:
            if format_type == "json":
                # Try to parse and reformat as JSON
                if content.startswith('{') or content.startswith('['):
                    try:
                        parsed = json.loads(content)
                        formatted_content = json.dumps(parsed, indent=2)
                    except json.JSONDecodeError:
                        formatted_content = json.dumps({
                            "raw_content": content,
                            "format_error": "Could not parse as JSON",
                            "formatted_at": datetime.now().isoformat()
                        })
                else:
                    formatted_content = json.dumps({
                        "content": content,
                        "formatted_at": datetime.now().isoformat()
                    })
            
            elif format_type == "security_summary":
                lines = content.split('\n')
                summary = "🔒 SECURITY SUMMARY\n" + "=" * 30 + "\n"
                for line in lines[:10]:  # Limit to first 10 lines
                    if line.strip():
                        summary += f"• {line.strip()}\n"
                if len(lines) > 10:
                    summary += f"... and {len(lines) - 10} more items\n"
                formatted_content = summary
            
            elif format_type == "markdown":
                # Basic markdown formatting
                formatted_content = f"## Response\n\n{content}\n\n---\n*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
            
            else:  # structured (default)
                formatted_content = f"📋 STRUCTURED RESPONSE\n{'=' * 25}\n{content}\n{'=' * 25}\nTimestamp: {datetime.now().isoformat()}"
            
            result = {
                "status": "success",
                "action": "format_response",
                "data": {
                    "original_content": content,
                    "formatted_content": formatted_content,
                    "format_type": format_type
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Response formatted ({format_type}) by {user_id}")
            return json.dumps(result)
            
        except Exception as e:
            error_result = {
                "status": "error",
                "action": "format_response",
                "error": str(e),
                "original_content": content,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error(f"Response formatting failed: {e}")
            return json.dumps(error_result)

    logger.info("Client interaction tools registered successfully") 