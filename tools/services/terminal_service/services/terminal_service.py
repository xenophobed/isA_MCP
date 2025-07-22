"""
Terminal Service Implementation
"""

import subprocess
import os
import uuid
import platform
import socket
from datetime import datetime
from typing import Dict, Optional, List, Any
import asyncio
import shlex

from ..models.terminal_models import CommandResult, TerminalSession, SystemInfo
from .security_validator import SecurityValidator


class TerminalService:
    """Core terminal service for command execution"""
    
    def __init__(self):
        self.sessions: Dict[str, TerminalSession] = {}
        self.security_validator = SecurityValidator()
        self.default_session_id = "default"
        self._initialize_default_session()
    
    def _initialize_default_session(self):
        """Initialize default terminal session"""
        self.sessions[self.default_session_id] = TerminalSession(
            session_id=self.default_session_id,
            current_directory=os.getcwd(),
            environment_variables=dict(os.environ)
        )
    
    async def execute_command(
        self, 
        command: str, 
        session_id: Optional[str] = None,
        timeout: int = 30,
        require_confirmation: bool = False
    ) -> CommandResult:
        """
        Execute a terminal command with security validation
        
        Args:
            command: Command to execute
            session_id: Session ID (uses default if None)
            timeout: Command timeout in seconds
            require_confirmation: Whether to bypass confirmation requirements
            
        Returns:
            CommandResult with execution details
        """
        if not session_id:
            session_id = self.default_session_id
        
        session = self._get_or_create_session(session_id)
        
        # Security validation
        is_valid, error_message = self.security_validator.validate_command(
            command, session.current_directory
        )
        
        if not is_valid:
            return CommandResult(
                success=False,
                stdout="",
                stderr=f"Security validation failed: {error_message}",
                return_code=-1,
                execution_time=0.0,
                current_directory=session.current_directory,
                command=command
            )
        
        # Check if confirmation is required
        if not require_confirmation and self.security_validator.requires_confirmation(command):
            return CommandResult(
                success=False,
                stdout="",
                stderr="Command requires confirmation. Use require_confirmation=true parameter.",
                return_code=-1,
                execution_time=0.0,
                current_directory=session.current_directory,
                command=command
            )
        
        # Execute command
        try:
            start_time = datetime.now()
            
            # Handle cd command specially
            if command.strip().startswith('cd '):
                result = await self._handle_cd_command(command, session)
            else:
                result = await self._execute_subprocess(command, session, timeout)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time
            result.timestamp = start_time
            
            # Update session
            session.command_history.append(result)
            session.last_accessed = datetime.now()
            
            return result
            
        except Exception as e:
            return CommandResult(
                success=False,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                return_code=-1,
                execution_time=0.0,
                current_directory=session.current_directory,
                command=command
            )
    
    async def _execute_subprocess(
        self, 
        command: str, 
        session: TerminalSession, 
        timeout: int
    ) -> CommandResult:
        """Execute command using subprocess"""
        try:
            # Use shell=True for complex commands, but validate first
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=session.current_directory,
                env=session.environment_variables
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            return CommandResult(
                success=process.returncode == 0,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                return_code=process.returncode,
                execution_time=0.0,  # Will be set by caller
                current_directory=session.current_directory,
                command=command
            )
            
        except asyncio.TimeoutError:
            return CommandResult(
                success=False,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                return_code=-1,
                execution_time=float(timeout),
                current_directory=session.current_directory,
                command=command
            )
    
    async def _handle_cd_command(self, command: str, session: TerminalSession) -> CommandResult:
        """Handle cd command specially to update session directory"""
        parts = shlex.split(command)
        if len(parts) < 2:
            # cd with no args goes to home
            new_dir = os.path.expanduser("~")
        else:
            new_dir = parts[1]
        
        # Resolve path
        if not os.path.isabs(new_dir):
            new_dir = os.path.join(session.current_directory, new_dir)
        
        new_dir = os.path.abspath(new_dir)
        
        # Check if directory exists and is accessible
        if not os.path.exists(new_dir):
            return CommandResult(
                success=False,
                stdout="",
                stderr=f"cd: {new_dir}: No such file or directory",
                return_code=1,
                execution_time=0.0,
                current_directory=session.current_directory,
                command=command
            )
        
        if not os.path.isdir(new_dir):
            return CommandResult(
                success=False,
                stdout="",
                stderr=f"cd: {new_dir}: Not a directory",
                return_code=1,
                execution_time=0.0,
                current_directory=session.current_directory,
                command=command
            )
        
        # Update session directory
        session.current_directory = new_dir
        
        return CommandResult(
            success=True,
            stdout="",
            stderr="",
            return_code=0,
            execution_time=0.0,
            current_directory=new_dir,
            command=command
        )
    
    def _get_or_create_session(self, session_id: str) -> TerminalSession:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = TerminalSession(
                session_id=session_id,
                current_directory=os.getcwd(),
                environment_variables=dict(os.environ)
            )
        return self.sessions[session_id]
    
    def get_session_info(self, session_id: Optional[str] = None) -> Optional[TerminalSession]:
        """Get session information"""
        if not session_id:
            session_id = self.default_session_id
        return self.sessions.get(session_id)
    
    def list_sessions(self) -> List[str]:
        """List all active session IDs"""
        return list(self.sessions.keys())
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id == self.default_session_id:
            return False  # Can't delete default session
        
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def get_system_info(self) -> SystemInfo:
        """Get current system information"""
        return SystemInfo(
            hostname=socket.gethostname(),
            username=os.getenv('USER', 'unknown'),
            platform=platform.system(),
            architecture=platform.machine(),
            kernel_version=platform.release(),
            current_directory=os.getcwd(),
            environment_variables=dict(os.environ)
        )
    
    def get_command_history(self, session_id: Optional[str] = None, limit: int = 50) -> List[CommandResult]:
        """Get command history for session"""
        session = self.get_session_info(session_id)
        if not session:
            return []
        
        return session.command_history[-limit:] if limit > 0 else session.command_history