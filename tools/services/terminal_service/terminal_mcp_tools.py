#!/usr/bin/env python3
"""
Terminal MCP Tools - Secure terminal operations for MCP integration
Based on existing terminal service but with proper MCP @tool decorators
"""

import json
import asyncio
from typing import Optional, Dict, Any, List
from mcp.server.fastmcp import FastMCP
from tools.base_tool import BaseTool
from tools.services.terminal_service.services.terminal_service import TerminalService
from core.logging import get_logger

logger = get_logger(__name__)


class TerminalMCPTool(BaseTool):
    """Terminal tool for MCP server integration with secure command execution"""
    
    def __init__(self):
        super().__init__()
        self.terminal_service = TerminalService()
    
    async def safe_execute_command(
        self,
        command: str,
        session_id: Optional[str] = None,
        timeout: int = 30
    ) -> str:
        """
        Execute a terminal command with security validation
        
        Args:
            command: The command to execute
            session_id: Optional session ID for command isolation
            timeout: Command timeout in seconds (default: 30)
        """
        try:
            result = await self.terminal_service.execute_command(
                command=command,
                session_id=session_id,
                timeout=timeout,
                require_confirmation=False
            )
            
            return self.create_response(
                status="success" if result.success else "error",
                action="execute_command",
                data={
                    "command": command,
                    "exit_code": result.exit_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "execution_time": result.execution_time,
                    "session_id": result.session_id
                },
                error_message=result.stderr if not result.success else None
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="execute_command",
                data={},
                error_message=f"Command execution failed: {str(e)}"
            )
    
    async def get_directory_info(self, session_id: Optional[str] = None) -> str:
        """Get current directory information"""
        try:
            session = self.terminal_service.sessions.get(
                session_id or self.terminal_service.default_session_id
            )
            
            if not session:
                return self.create_response(
                    status="error",
                    action="get_directory_info",
                    data={},
                    error_message="Session not found"
                )
            
            return self.create_response(
                status="success",
                action="get_directory_info",
                data={
                    "current_directory": session.current_directory,
                    "session_id": session.session_id
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="get_directory_info",
                data={},
                error_message=str(e)
            )
    
    async def list_directory_contents(
        self, 
        path: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """List directory contents"""
        try:
            # Use ls command to list directory
            command = f"ls -la {path}" if path else "ls -la"
            result = await self.terminal_service.execute_command(
                command=command,
                session_id=session_id,
                timeout=10
            )
            
            return self.create_response(
                status="success" if result.success else "error",
                action="list_directory_contents",
                data={
                    "path": path or "current directory",
                    "contents": result.stdout,
                    "session_id": result.session_id
                },
                error_message=result.stderr if not result.success else None
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="list_directory_contents",
                data={},
                error_message=str(e)
            )
    
    async def get_system_information(self) -> str:
        """Get system information"""
        try:
            system_info = self.terminal_service.get_system_info()
            
            return self.create_response(
                status="success",
                action="get_system_information",
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
                action="get_system_information",
                data={},
                error_message=str(e)
            )
    
    async def manage_session(
        self,
        action: str,
        session_id: Optional[str] = None
    ) -> str:
        """Manage terminal sessions (create, list, delete)"""
        try:
            if action == "list":
                sessions = list(self.terminal_service.sessions.keys())
                return self.create_response(
                    status="success",
                    action="manage_session",
                    data={
                        "action": "list",
                        "sessions": sessions,
                        "total_sessions": len(sessions)
                    }
                )
            
            elif action == "create":
                new_session = self.terminal_service.create_session(session_id)
                return self.create_response(
                    status="success",
                    action="manage_session",
                    data={
                        "action": "create",
                        "session_id": new_session.session_id,
                        "current_directory": new_session.current_directory
                    }
                )
            
            elif action == "delete" and session_id:
                if session_id == self.terminal_service.default_session_id:
                    return self.create_response(
                        status="error",
                        action="manage_session",
                        data={},
                        error_message="Cannot delete default session"
                    )
                
                if session_id in self.terminal_service.sessions:
                    del self.terminal_service.sessions[session_id]
                    return self.create_response(
                        status="success",
                        action="manage_session",
                        data={
                            "action": "delete",
                            "session_id": session_id
                        }
                    )
                else:
                    return self.create_response(
                        status="error",
                        action="manage_session",
                        data={},
                        error_message="Session not found"
                    )
            
            else:
                return self.create_response(
                    status="error",
                    action="manage_session",
                    data={},
                    error_message="Invalid action or missing session_id for delete"
                )
                
        except Exception as e:
            return self.create_response(
                status="error",
                action="manage_session",
                data={},
                error_message=str(e)
            )


def register_terminal_mcp_tools(mcp: FastMCP):
    """Register terminal tools using FastMCP decorators"""
    terminal_tool = TerminalMCPTool()
    
    @mcp.tool()
    async def execute_terminal_command(
        command: str,
        session_id: Optional[str] = None,
        timeout: int = 30
    ) -> str:
        """
        Execute a terminal command with security validation
        
        Keywords: terminal, command, execute, shell, bash, run
        Category: system
        
        Args:
            command: The command to execute (e.g., 'ls -la', 'pwd', 'echo hello')
            session_id: Optional session ID for command isolation
            timeout: Command timeout in seconds (default: 30)
        """
        return await terminal_tool.safe_execute_command(command, session_id, timeout)
    
    @mcp.tool()
    async def get_current_directory(session_id: Optional[str] = None) -> str:
        """
        Get current working directory information
        
        Keywords: directory, pwd, current, path, location
        Category: system
        
        Args:
            session_id: Optional session ID (uses default if not provided)
        """
        return await terminal_tool.get_directory_info(session_id)
    
    @mcp.tool()
    async def list_files(
        path: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        List files and directories in the specified path
        
        Keywords: list, files, directory, ls, contents
        Category: system
        
        Args:
            path: Directory path to list (current directory if not provided)
            session_id: Optional session ID
        """
        return await terminal_tool.list_directory_contents(path, session_id)
    
    @mcp.tool()
    async def get_system_info() -> str:
        """
        Get system information (OS, platform, hostname, etc.)
        
        Keywords: system, info, platform, os, hostname
        Category: system
        """
        return await terminal_tool.get_system_information()
    
    @mcp.tool()
    async def manage_terminal_sessions(
        action: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        Manage terminal sessions (create, list, delete)
        
        Keywords: session, terminal, manage, create, delete, list
        Category: system
        
        Args:
            action: Action to perform ('create', 'list', 'delete')
            session_id: Session ID (required for 'delete', optional for 'create')
        """
        return await terminal_tool.manage_session(action, session_id)
    
    @mcp.tool()
    async def change_directory(
        path: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        Change current working directory
        
        Keywords: cd, change, directory, navigate, path
        Category: system
        
        Args:
            path: Directory path to change to
            session_id: Optional session ID
        """
        return await terminal_tool.safe_execute_command(f"cd {path} && pwd", session_id)


# Legacy compatibility with existing registration pattern
def register_terminal_tools(mcp):
    """Legacy function name for compatibility"""
    register_terminal_mcp_tools(mcp)