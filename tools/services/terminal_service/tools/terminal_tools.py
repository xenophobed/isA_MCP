"""
Terminal Tools for MCP Integration
"""

import sys
import os
import json
from typing import Optional, Dict, Any, List

# Add parent directories to path for imports
# /Users/.../tools/services/terminal_service/tools/terminal_tools.py -> /Users/.../
# 需要向上5级到项目根目录
current_file = __file__  # terminal_tools.py
tools_dir = os.path.dirname(current_file)  # tools/
terminal_service_dir = os.path.dirname(tools_dir)  # terminal_service/
services_dir = os.path.dirname(terminal_service_dir)  # services/
tools_root = os.path.dirname(services_dir)  # tools/
project_root = os.path.dirname(tools_root)  # project root/
sys.path.insert(0, project_root)

from tools.base_tool import BaseTool
from tools.services.terminal_service.services.terminal_service import TerminalService
from tools.services.terminal_service.models.terminal_models import CommandResult, TerminalSession


class TerminalTools(BaseTool):
    """Terminal tools for MCP server integration"""
    
    def __init__(self):
        super().__init__()
        self.terminal_service = TerminalService()
    
    async def execute_command(
        self,
        command: str,
        session_id: Optional[str] = None,
        timeout: int = 30,
        require_confirmation: bool = False
    ) -> str:
        """
        Execute a terminal command with security validation
        
        Keywords: terminal, command, execute, shell, bash, zsh
        Category: system
        
        Args:
            command: The command to execute
            session_id: Optional session ID for command isolation
            timeout: Command timeout in seconds (default: 30)
            require_confirmation: Bypass confirmation for dangerous commands
        """
        try:
            result = await self.terminal_service.execute_command(
                command=command,
                session_id=session_id,
                timeout=timeout,
                require_confirmation=require_confirmation
            )
            
            response_data = {
                "command": result.command,
                "success": result.success,
                "return_code": result.return_code,
                "execution_time": result.execution_time,
                "current_directory": result.current_directory,
                "timestamp": result.timestamp.isoformat() if hasattr(result, 'timestamp') else None
            }
            
            if result.stdout:
                response_data["stdout"] = result.stdout
            
            if result.stderr:
                response_data["stderr"] = result.stderr
            
            status = "success" if result.success else "error"
            error_message = result.stderr if not result.success else None
            
            return self.create_response(
                status=status,
                action="execute_command",
                data=response_data,
                error_message=error_message
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="execute_command",
                data={"command": command},
                error_message=str(e)
            )
    
    async def get_current_directory(self, session_id: Optional[str] = None) -> str:
        """
        Get current working directory for session
        
        Keywords: pwd, directory, current, working, path
        Category: system
        
        Args:
            session_id: Optional session ID
        """
        try:
            session = self.terminal_service.get_session_info(session_id)
            if not session:
                return self.create_response(
                    status="error",
                    action="get_current_directory",
                    data={},
                    error_message="Session not found"
                )
            
            return self.create_response(
                status="success",
                action="get_current_directory",
                data={
                    "current_directory": session.current_directory,
                    "session_id": session.session_id
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="get_current_directory",
                data={},
                error_message=str(e)
            )
    
    async def list_files(
        self,
        directory: Optional[str] = None,
        show_hidden: bool = False,
        long_format: bool = True,
        session_id: Optional[str] = None
    ) -> str:
        """
        List files and directories
        
        Keywords: ls, list, files, directory, folder
        Category: file_system
        
        Args:
            directory: Directory to list (current directory if None)
            show_hidden: Show hidden files (starting with .)
            long_format: Use long format with details
            session_id: Optional session ID
        """
        try:
            # Build ls command
            cmd_parts = ["ls"]
            
            if long_format:
                cmd_parts.append("-l")
            
            if show_hidden:
                cmd_parts.append("-a")
            
            if directory:
                cmd_parts.append(directory)
            
            command = " ".join(cmd_parts)
            
            return await self.execute_command(
                command=command,
                session_id=session_id
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="list_files",
                data={"directory": directory},
                error_message=str(e)
            )
    
    async def change_directory(self, directory: str, session_id: Optional[str] = None) -> str:
        """
        Change current directory
        
        Keywords: cd, change, directory, navigate, path
        Category: file_system
        
        Args:
            directory: Target directory path
            session_id: Optional session ID
        """
        try:
            return await self.execute_command(
                command=f"cd {directory}",
                session_id=session_id
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="change_directory",
                data={"directory": directory},
                error_message=str(e)
            )
    
    async def get_system_info(self) -> str:
        """
        Get system information
        
        Keywords: system, info, uname, hostname, platform
        Category: system
        """
        try:
            system_info = self.terminal_service.get_system_info()
            
            return self.create_response(
                status="success",
                action="get_system_info",
                data={
                    "hostname": system_info.hostname,
                    "username": system_info.username,
                    "platform": system_info.platform,
                    "architecture": system_info.architecture,
                    "kernel_version": system_info.kernel_version,
                    "current_directory": system_info.current_directory
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="get_system_info",
                data={},
                error_message=str(e)
            )
    
    async def get_command_history(
        self,
        session_id: Optional[str] = None,
        limit: int = 20
    ) -> str:
        """
        Get command execution history for session
        
        Keywords: history, commands, log, past, executed
        Category: system
        
        Args:
            session_id: Optional session ID
            limit: Maximum number of commands to return
        """
        try:
            history = self.terminal_service.get_command_history(session_id, limit)
            
            history_data = []
            for cmd_result in history:
                history_data.append({
                    "command": cmd_result.command,
                    "success": cmd_result.success,
                    "return_code": cmd_result.return_code,
                    "execution_time": cmd_result.execution_time,
                    "timestamp": cmd_result.timestamp.isoformat() if hasattr(cmd_result, 'timestamp') else None
                })
            
            return self.create_response(
                status="success",
                action="get_command_history",
                data={
                    "history": history_data,
                    "count": len(history_data)
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="get_command_history",
                data={},
                error_message=str(e)
            )
    
    async def list_sessions(self) -> str:
        """
        List all active terminal sessions
        
        Keywords: sessions, active, terminal, list
        Category: session
        """
        try:
            sessions = self.terminal_service.list_sessions()
            
            session_details = []
            for session_id in sessions:
                session = self.terminal_service.get_session_info(session_id)
                if session:
                    session_details.append({
                        "session_id": session.session_id,
                        "current_directory": session.current_directory,
                        "created_at": session.created_at.isoformat(),
                        "last_accessed": session.last_accessed.isoformat(),
                        "command_count": len(session.command_history)
                    })
            
            return self.create_response(
                status="success",
                action="list_sessions",
                data={
                    "sessions": session_details,
                    "count": len(session_details)
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="list_sessions",
                data={},
                error_message=str(e)
            )
    
    async def create_session(self, session_id: str) -> str:
        """
        Create a new terminal session
        
        Keywords: session, create, new, terminal
        Category: session
        
        Args:
            session_id: Unique identifier for the new session
        """
        try:
            # Creating session happens automatically when accessed
            session = self.terminal_service._get_or_create_session(session_id)
            
            return self.create_response(
                status="success",
                action="create_session",
                data={
                    "session_id": session.session_id,
                    "current_directory": session.current_directory,
                    "created_at": session.created_at.isoformat()
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="create_session",
                data={"session_id": session_id},
                error_message=str(e)
            )
    
    async def delete_session(self, session_id: str) -> str:
        """
        Delete a terminal session
        
        Keywords: session, delete, remove, close
        Category: session
        
        Args:
            session_id: Session ID to delete
        """
        try:
            success = self.terminal_service.delete_session(session_id)
            
            if success:
                return self.create_response(
                    status="success",
                    action="delete_session",
                    data={"session_id": session_id}
                )
            else:
                return self.create_response(
                    status="error",
                    action="delete_session",
                    data={"session_id": session_id},
                    error_message="Session not found or cannot be deleted"
                )
                
        except Exception as e:
            return self.create_response(
                status="error",
                action="delete_session",
                data={"session_id": session_id},
                error_message=str(e)
            )
    
    def register_all_tools(self, mcp):
        """Register all terminal tools with MCP server"""
        self.register_tool(mcp, self.execute_command)
        self.register_tool(mcp, self.get_current_directory)
        self.register_tool(mcp, self.list_files)
        self.register_tool(mcp, self.change_directory)
        self.register_tool(mcp, self.get_system_info)
        self.register_tool(mcp, self.get_command_history)
        self.register_tool(mcp, self.list_sessions)
        self.register_tool(mcp, self.create_session)
        self.register_tool(mcp, self.delete_session)


def register_terminal_tools(mcp):
    """Register terminal tools with MCP server"""
    terminal_tools = TerminalTools()
    terminal_tools.register_all_tools(mcp)