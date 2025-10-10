#!/usr/bin/env python3
"""
Enhanced Terminal Service - Improved security and reliability
"""

import subprocess
import os
import uuid
import platform
import socket
import shlex
import asyncio
from datetime import datetime
from typing import Dict, Optional, List, Any, Set
from dataclasses import dataclass, field

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CommandResult:
    """Result of command execution"""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    session_id: str
    command: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TerminalSession:
    """Terminal session information"""
    session_id: str
    current_directory: str
    environment_variables: Dict[str, str]
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    command_history: List[str] = field(default_factory=list)


@dataclass
class SystemInfo:
    """System information"""
    platform: str
    system: str
    release: str
    version: str
    machine: str
    processor: str
    hostname: str
    user: str


class SecurityValidator:
    """Enhanced security validation for terminal commands"""
    
    def __init__(self):
        # Dangerous commands that require confirmation
        self.dangerous_commands: Set[str] = {
            'rm', 'rmdir', 'del', 'delete', 'format', 'fdisk',
            'mkfs', 'dd', 'sudo', 'su', 'chmod', 'chown',
            'systemctl', 'service', 'kill', 'killall', 'pkill',
            'shutdown', 'reboot', 'halt', 'poweroff'
        }
        
        # Completely blocked commands
        self.blocked_commands: Set[str] = {
            'rm -rf /', 'format c:', ':(){ :|:& };:', 'dd if=/dev/zero'
        }
        
        # Safe commands that can run without validation
        self.safe_commands: Set[str] = {
            'ls', 'dir', 'pwd', 'echo', 'cat', 'head', 'tail',
            'grep', 'find', 'which', 'whoami', 'date', 'uptime',
            'ps', 'top', 'df', 'du', 'free', 'uname', 'hostname'
        }
    
    def validate_command(self, command: str) -> Dict[str, Any]:
        """
        Validate command safety
        
        Returns:
            Dict with validation result
        """
        command = command.strip()
        
        # Check for blocked commands
        for blocked in self.blocked_commands:
            if blocked in command.lower():
                return {
                    'allowed': False,
                    'reason': 'Command is completely blocked for safety',
                    'risk_level': 'CRITICAL'
                }
        
        # Parse command to get the main command
        try:
            parts = shlex.split(command)
            if not parts:
                return {
                    'allowed': False,
                    'reason': 'Empty command',
                    'risk_level': 'LOW'
                }
            
            main_command = parts[0].split('/')[-1]  # Get basename for full paths
            
            # Check if it's a safe command
            if main_command in self.safe_commands:
                return {
                    'allowed': True,
                    'reason': 'Command is in safe list',
                    'risk_level': 'LOW'
                }
            
            # Check if it's a dangerous command
            if main_command in self.dangerous_commands:
                return {
                    'allowed': False,
                    'reason': 'Command requires confirmation due to potential risk',
                    'risk_level': 'HIGH'
                }
            
            # Check for suspicious patterns
            suspicious_patterns = ['>', '>>', '|', '&', ';', '$(', '`']
            for pattern in suspicious_patterns:
                if pattern in command:
                    return {
                        'allowed': True,  # Allow but warn
                        'reason': f'Command contains potentially risky pattern: {pattern}',
                        'risk_level': 'MEDIUM'
                    }
            
            # Default: allow with caution
            return {
                'allowed': True,
                'reason': 'Command appears safe',
                'risk_level': 'LOW'
            }
            
        except ValueError as e:
            return {
                'allowed': False,
                'reason': f'Command parsing failed: {e}',
                'risk_level': 'MEDIUM'
            }


class EnhancedTerminalService:
    """Enhanced terminal service with improved security and session management"""
    
    def __init__(self):
        self.sessions: Dict[str, TerminalSession] = {}
        self.security_validator = SecurityValidator()
        self.default_session_id = "default"
        self.max_sessions = 10
        self.max_command_history = 100
        self._initialize_default_session()
    
    def _initialize_default_session(self):
        """Initialize default terminal session"""
        self.sessions[self.default_session_id] = TerminalSession(
            session_id=self.default_session_id,
            current_directory=os.getcwd(),
            environment_variables=dict(os.environ)
        )
    
    def create_session(self, session_id: Optional[str] = None) -> TerminalSession:
        """Create a new terminal session"""
        if len(self.sessions) >= self.max_sessions:
            # Remove oldest session (except default)
            oldest_session = min(
                (s for s in self.sessions.values() if s.session_id != self.default_session_id),
                key=lambda x: x.last_used,
                default=None
            )
            if oldest_session:
                del self.sessions[oldest_session.session_id]
        
        if session_id is None:
            session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        session = TerminalSession(
            session_id=session_id,
            current_directory=os.getcwd(),
            environment_variables=dict(os.environ)
        )
        
        self.sessions[session_id] = session
        logger.info(f"Created new terminal session: {session_id}")
        return session
    
    def get_session(self, session_id: Optional[str] = None) -> Optional[TerminalSession]:
        """Get session by ID"""
        session_id = session_id or self.default_session_id
        session = self.sessions.get(session_id)
        if session:
            session.last_used = datetime.now()
        return session
    
    async def execute_command(
        self,
        command: str,
        session_id: Optional[str] = None,
        timeout: int = 30,
        require_confirmation: bool = False
    ) -> CommandResult:
        """
        Execute a terminal command with enhanced security
        
        Args:
            command: Command to execute
            session_id: Session ID
            timeout: Timeout in seconds
            require_confirmation: Whether to bypass confirmation for dangerous commands
        """
        start_time = datetime.now()
        session = self.get_session(session_id)
        
        if not session:
            return CommandResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="Session not found",
                execution_time=0,
                session_id=session_id or "unknown",
                command=command
            )
        
        # Validate command security
        validation = self.security_validator.validate_command(command)
        
        if not validation['allowed'] and not require_confirmation:
            return CommandResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Command blocked: {validation['reason']}",
                execution_time=0,
                session_id=session.session_id,
                command=command
            )
        
        # Add command to history
        session.command_history.append(command)
        if len(session.command_history) > self.max_command_history:
            session.command_history = session.command_history[-self.max_command_history:]
        
        try:
            # Execute command in session's directory
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=session.current_directory,
                env=session.environment_variables
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Update session directory if command was 'cd'
                if command.strip().startswith('cd '):
                    try:
                        # Get the new directory
                        new_dir_process = await asyncio.create_subprocess_shell(
                            'pwd',
                            stdout=asyncio.subprocess.PIPE,
                            cwd=session.current_directory,
                            env=session.environment_variables
                        )
                        new_dir_stdout, _ = await new_dir_process.communicate()
                        if new_dir_process.returncode == 0:
                            session.current_directory = new_dir_stdout.decode().strip()
                    except Exception as e:
                        logger.warning(f"Failed to update session directory: {e}")
                
                return CommandResult(
                    success=process.returncode == 0,
                    exit_code=process.returncode,
                    stdout=stdout.decode() if stdout else "",
                    stderr=stderr.decode() if stderr else "",
                    execution_time=execution_time,
                    session_id=session.session_id,
                    command=command
                )
                
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                
                return CommandResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=f"Command timed out after {timeout} seconds",
                    execution_time=timeout,
                    session_id=session.session_id,
                    command=command
                )
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return CommandResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                execution_time=execution_time,
                session_id=session.session_id,
                command=command
            )
    
    def get_system_info(self) -> SystemInfo:
        """Get comprehensive system information"""
        try:
            return SystemInfo(
                platform=platform.platform(),
                system=platform.system(),
                release=platform.release(),
                version=platform.version(),
                machine=platform.machine(),
                processor=platform.processor() or "Unknown",
                hostname=socket.gethostname(),
                user=os.environ.get('USER', os.environ.get('USERNAME', 'Unknown'))
            )
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return SystemInfo(
                platform="Unknown",
                system="Unknown", 
                release="Unknown",
                version="Unknown",
                machine="Unknown",
                processor="Unknown",
                hostname="Unknown",
                user="Unknown"
            )
    
    def cleanup_session(self, session_id: str) -> bool:
        """Clean up a session"""
        if session_id == self.default_session_id:
            return False  # Cannot delete default session
        
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Cleaned up session: {session_id}")
            return True
        
        return False
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about sessions"""
        return {
            'total_sessions': len(self.sessions),
            'default_session': self.default_session_id,
            'max_sessions': self.max_sessions,
            'sessions': [
                {
                    'session_id': s.session_id,
                    'created_at': s.created_at.isoformat(),
                    'last_used': s.last_used.isoformat(),
                    'current_directory': s.current_directory,
                    'command_count': len(s.command_history)
                }
                for s in self.sessions.values()
            ]
        }