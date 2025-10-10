#!/usr/bin/env python3
"""
Comprehensive Terminal MCP Tools - Complete terminal service for MCP integration
Production-ready terminal tools with enhanced security and session management
"""

import json
import asyncio
from typing import Optional, Dict, Any, List
from mcp.server.fastmcp import FastMCP
from tools.base_tool import BaseTool
from tools.services.terminal_service.enhanced_terminal_service import EnhancedTerminalService
from core.logging import get_logger

logger = get_logger(__name__)


class ComprehensiveTerminalTool(BaseTool):
    """Comprehensive terminal tool for MCP server integration"""
    
    def __init__(self):
        super().__init__()
        self.terminal_service = EnhancedTerminalService()
        logger.info("Comprehensive Terminal Tool initialized")
    
    async def execute_command_safely(
        self,
        command: str,
        session_id: Optional[str] = None,
        timeout: int = 30,
        require_confirmation: bool = False
    ) -> str:
        """Execute terminal command with enhanced security"""
        try:
            result = await self.terminal_service.execute_command(
                command=command,
                session_id=session_id,
                timeout=timeout,
                require_confirmation=require_confirmation
            )
            
            return self.create_response(
                status="success" if result.success else "error",
                action="execute_command",
                data={
                    "command": result.command,
                    "exit_code": result.exit_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "execution_time": result.execution_time,
                    "session_id": result.session_id,
                    "timestamp": result.timestamp.isoformat()
                },
                error_message=result.stderr if not result.success else None
            )
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return self.create_response(
                status="error",
                action="execute_command",
                data={},
                error_message=f"Command execution failed: {str(e)}"
            )
    
    async def get_working_directory(self, session_id: Optional[str] = None) -> str:
        """Get current working directory"""
        try:
            session = self.terminal_service.get_session(session_id)
            
            if not session:
                return self.create_response(
                    status="error",
                    action="get_working_directory",
                    data={},
                    error_message="Session not found"
                )
            
            return self.create_response(
                status="success",
                action="get_working_directory",
                data={
                    "current_directory": session.current_directory,
                    "session_id": session.session_id,
                    "last_used": session.last_used.isoformat()
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="get_working_directory",
                data={},
                error_message=str(e)
            )
    
    async def list_directory(
        self, 
        path: Optional[str] = None,
        session_id: Optional[str] = None,
        show_hidden: bool = False,
        detailed: bool = True
    ) -> str:
        """List directory contents with options"""
        try:
            # Build ls command with options
            ls_options = "-l" if detailed else ""
            if show_hidden:
                ls_options += "a"
            
            command = f"ls {ls_options} {path}" if path else f"ls {ls_options}"
            
            result = await self.terminal_service.execute_command(
                command=command.strip(),
                session_id=session_id,
                timeout=10
            )
            
            return self.create_response(
                status="success" if result.success else "error",
                action="list_directory",
                data={
                    "path": path or "current directory",
                    "contents": result.stdout,
                    "session_id": result.session_id,
                    "detailed": detailed,
                    "show_hidden": show_hidden
                },
                error_message=result.stderr if not result.success else None
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="list_directory",
                data={},
                error_message=str(e)
            )
    
    async def change_working_directory(
        self,
        path: str,
        session_id: Optional[str] = None
    ) -> str:
        """Change working directory"""
        try:
            # Use cd command and verify the change
            result = await self.terminal_service.execute_command(
                command=f"cd {path} && pwd",
                session_id=session_id,
                timeout=5
            )
            
            return self.create_response(
                status="success" if result.success else "error",
                action="change_working_directory",
                data={
                    "requested_path": path,
                    "new_directory": result.stdout.strip() if result.success else None,
                    "session_id": result.session_id
                },
                error_message=result.stderr if not result.success else None
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="change_working_directory",
                data={},
                error_message=str(e)
            )
    
    async def get_system_info(self) -> str:
        """Get comprehensive system information"""
        try:
            system_info = self.terminal_service.get_system_info()
            
            return self.create_response(
                status="success",
                action="get_system_info",
                data={
                    "platform": system_info.platform,
                    "system": system_info.system,
                    "release": system_info.release,
                    "version": system_info.version,
                    "machine": system_info.machine,
                    "processor": system_info.processor,
                    "hostname": system_info.hostname,
                    "user": system_info.user
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="get_system_info",
                data={},
                error_message=str(e)
            )
    
    async def manage_sessions(
        self,
        action: str,
        session_id: Optional[str] = None
    ) -> str:
        """Comprehensive session management"""
        try:
            if action == "list":
                stats = self.terminal_service.get_session_stats()
                return self.create_response(
                    status="success",
                    action="manage_sessions",
                    data={
                        "action": "list",
                        "session_stats": stats
                    }
                )
            
            elif action == "create":
                new_session = self.terminal_service.create_session(session_id)
                return self.create_response(
                    status="success",
                    action="manage_sessions",
                    data={
                        "action": "create",
                        "session_id": new_session.session_id,
                        "current_directory": new_session.current_directory,
                        "created_at": new_session.created_at.isoformat()
                    }
                )
            
            elif action == "delete" and session_id:
                success = self.terminal_service.cleanup_session(session_id)
                if success:
                    return self.create_response(
                        status="success",
                        action="manage_sessions",
                        data={
                            "action": "delete",
                            "session_id": session_id,
                            "deleted": True
                        }
                    )
                else:
                    return self.create_response(
                        status="error",
                        action="manage_sessions",
                        data={},
                        error_message="Cannot delete session (not found or default session)"
                    )
            
            elif action == "info" and session_id:
                session = self.terminal_service.get_session(session_id)
                if session:
                    return self.create_response(
                        status="success",
                        action="manage_sessions",
                        data={
                            "action": "info",
                            "session_info": {
                                "session_id": session.session_id,
                                "current_directory": session.current_directory,
                                "created_at": session.created_at.isoformat(),
                                "last_used": session.last_used.isoformat(),
                                "command_history_count": len(session.command_history),
                                "recent_commands": session.command_history[-5:] if session.command_history else []
                            }
                        }
                    )
                else:
                    return self.create_response(
                        status="error",
                        action="manage_sessions",
                        data={},
                        error_message="Session not found"
                    )
            
            else:
                return self.create_response(
                    status="error",
                    action="manage_sessions",
                    data={},
                    error_message="Invalid action or missing session_id"
                )
                
        except Exception as e:
            return self.create_response(
                status="error",
                action="manage_sessions",
                data={},
                error_message=str(e)
            )
    
    async def get_command_history(
        self,
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> str:
        """Get command history for a session"""
        try:
            session = self.terminal_service.get_session(session_id)
            
            if not session:
                return self.create_response(
                    status="error",
                    action="get_command_history",
                    data={},
                    error_message="Session not found"
                )
            
            history = session.command_history[-limit:] if session.command_history else []
            
            return self.create_response(
                status="success",
                action="get_command_history",
                data={
                    "session_id": session.session_id,
                    "total_commands": len(session.command_history),
                    "returned_commands": len(history),
                    "history": history,
                    "limit": limit
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="get_command_history",
                data={},
                error_message=str(e)
            )
    
    async def validate_command_safety(self, command: str) -> str:
        """Validate command safety without executing"""
        try:
            validation = self.terminal_service.security_validator.validate_command(command)
            
            return self.create_response(
                status="success",
                action="validate_command_safety",
                data={
                    "command": command,
                    "allowed": validation['allowed'],
                    "reason": validation['reason'],
                    "risk_level": validation['risk_level']
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="validate_command_safety",
                data={},
                error_message=str(e)
            )


def register_comprehensive_terminal_tools(mcp: FastMCP):
    """Register comprehensive terminal tools with MCP"""
    terminal_tool = ComprehensiveTerminalTool()
    logger.info("Registering comprehensive terminal tools with MCP")
    
    @mcp.tool()
    async def execute_terminal_command(
        command: str,
        session_id: Optional[str] = None,
        timeout: int = 30,
        require_confirmation: bool = False
    ) -> str:
        """
        Execute a terminal command with enhanced security validation
        
        Keywords: terminal, command, execute, shell, bash, run, cli
        Category: system
        
        Args:
            command: Command to execute (e.g., 'ls -la', 'pwd', 'echo hello')
            session_id: Optional session ID for command isolation
            timeout: Command timeout in seconds (default: 30)
            require_confirmation: Bypass safety checks for dangerous commands
        """
        return await terminal_tool.execute_command_safely(
            command, session_id, timeout, require_confirmation
        )
    
    @mcp.tool()
    async def get_current_directory(session_id: Optional[str] = None) -> str:
        """
        Get current working directory for the session
        
        Keywords: directory, pwd, current, path, location, working
        Category: system
        
        Args:
            session_id: Optional session ID (uses default if not provided)
        """
        return await terminal_tool.get_working_directory(session_id)
    
    @mcp.tool()
    async def list_files(
        path: Optional[str] = None,
        session_id: Optional[str] = None,
        show_hidden: bool = False,
        detailed: bool = True
    ) -> str:
        """
        List files and directories with customizable options
        
        Keywords: list, files, directory, ls, contents, browse
        Category: system
        
        Args:
            path: Directory path to list (current directory if not provided)
            session_id: Optional session ID
            show_hidden: Show hidden files (default: False)
            detailed: Show detailed information (default: True)
        """
        return await terminal_tool.list_directory(path, session_id, show_hidden, detailed)
    
    @mcp.tool()
    async def change_directory(
        path: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        Change current working directory
        
        Keywords: cd, change, directory, navigate, path, move
        Category: system
        
        Args:
            path: Directory path to change to
            session_id: Optional session ID
        """
        return await terminal_tool.change_working_directory(path, session_id)
    
    @mcp.tool()
    async def get_system_info() -> str:
        """
        Get comprehensive system information
        
        Keywords: system, info, platform, os, hostname, machine
        Category: system
        """
        return await terminal_tool.get_system_info()
    
    @mcp.tool()
    async def manage_terminal_sessions(
        action: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        Manage terminal sessions (create, list, delete, info)
        
        Keywords: session, terminal, manage, create, delete, list, info
        Category: system
        
        Args:
            action: Action to perform ('create', 'list', 'delete', 'info')
            session_id: Session ID (required for 'delete' and 'info')
        """
        return await terminal_tool.manage_sessions(action, session_id)
    
    @mcp.tool()
    async def get_command_history(
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> str:
        """
        Get command history for a session
        
        Keywords: history, commands, recent, log, session
        Category: system
        
        Args:
            session_id: Optional session ID (uses default if not provided)
            limit: Maximum number of commands to return (default: 10)
        """
        return await terminal_tool.get_command_history(session_id, limit)
    
    @mcp.tool()
    async def validate_command_safety(command: str) -> str:
        """
        Validate command safety without executing it
        
        Keywords: validate, safety, security, check, command, risk
        Category: system
        
        Args:
            command: Command to validate for safety
        """
        return await terminal_tool.validate_command_safety(command)


# Aliases for compatibility
def register_terminal_tools(mcp):
    """Compatibility alias for existing code"""
    register_comprehensive_terminal_tools(mcp)


def register_terminal_mcp_tools(mcp):
    """Compatibility alias for existing code"""
    register_comprehensive_terminal_tools(mcp)