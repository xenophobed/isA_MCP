"""
Terminal Service Data Models
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class CommandResult:
    """Result of a terminal command execution"""
    success: bool
    stdout: str
    stderr: str
    return_code: int
    execution_time: float
    current_directory: str
    command: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TerminalSession:
    """Terminal session state"""
    session_id: str
    current_directory: str
    environment_variables: Dict[str, str]
    command_history: List[CommandResult] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)


@dataclass
class SecurityPolicy:
    """Security policy for command execution"""
    allowed_commands: List[str] = field(default_factory=list)
    forbidden_commands: List[str] = field(default_factory=list)
    allowed_directories: List[str] = field(default_factory=list)
    forbidden_directories: List[str] = field(default_factory=list)
    max_execution_time: int = 30
    require_confirmation: List[str] = field(default_factory=list)


@dataclass
class SystemInfo:
    """System information structure"""
    hostname: str
    username: str
    platform: str
    architecture: str
    kernel_version: str
    current_directory: str
    environment_variables: Dict[str, str] = field(default_factory=dict)