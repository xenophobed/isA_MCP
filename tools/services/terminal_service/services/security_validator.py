"""
Security Validator for Terminal Commands
"""

import os
import re
from typing import List, Tuple
from ..models.terminal_models import SecurityPolicy


class SecurityValidator:
    """Validates terminal commands for security compliance"""
    
    def __init__(self):
        self.policy = self._create_default_policy()
    
    def _create_default_policy(self) -> SecurityPolicy:
        """Create default security policy for macOS"""
        return SecurityPolicy(
            # Safe read-only commands
            allowed_commands=[
                'ls', 'pwd', 'whoami', 'id', 'date', 'uname', 'hostname',
                'cat', 'head', 'tail', 'grep', 'find', 'locate', 'which',
                'ps', 'top', 'df', 'du', 'free', 'uptime', 'w', 'who',
                'history', 'env', 'printenv', 'echo', 'wc', 'sort', 'uniq',
                'diff', 'file', 'stat', 'lsof', 'netstat', 'ping', 'curl',
                'wget', 'git', 'npm', 'pip', 'brew', 'python', 'python3',
                'node', 'java', 'javac', 'gcc', 'make', 'cmake',
                'docker', 'kubectl', 'helm', 'terraform',
                'open', 'say', 'pbcopy', 'pbpaste', 'osascript'
            ],
            
            # Dangerous commands that should be blocked
            forbidden_commands=[
                'sudo', 'su', 'doas',
                'rm -rf /', 'rm -rf *', 'rmdir *',
                'dd', 'mkfs', 'fdisk', 'parted',
                'shutdown', 'reboot', 'halt', 'poweroff',
                'passwd', 'chpasswd', 'usermod', 'userdel',
                'chmod 777', 'chown -R', 'chgrp -R',
                'killall', 'pkill -9', 'kill -9',
                'crontab -r', 'crontab -e',
                'launchctl load', 'launchctl unload',
                'systemctl', 'service'
            ],
            
            # Safe directories
            allowed_directories=[
                '/Users',
                '/tmp',
                '/var/tmp',
                '/opt/homebrew',
                '/usr/local',
                '/Applications',
                '/System/Applications'
            ],
            
            # Forbidden directories
            forbidden_directories=[
                '/etc',
                '/var/root',
                '/private/etc',
                '/System/Library',
                '/Library/LaunchDaemons',
                '/Library/LaunchAgents'
            ],
            
            # Commands requiring confirmation
            require_confirmation=[
                'rm', 'rmdir', 'mv', 'cp -r', 'chmod', 'chown',
                'git push', 'git reset --hard', 'git clean -fd',
                'npm install -g', 'pip install', 'brew install',
                'docker run', 'docker-compose up'
            ]
        )
    
    def validate_command(self, command: str, current_dir: str = None) -> Tuple[bool, str]:
        """
        Validate if a command is safe to execute
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        command = command.strip()
        
        # Check for empty command
        if not command:
            return False, "Empty command not allowed"
        
        # Extract base command
        base_command = command.split()[0]
        
        # Check forbidden commands
        if self._is_forbidden_command(command):
            return False, f"Command '{base_command}' is forbidden for security reasons"
        
        # Check if command is in allowed list (for strict mode)
        if not self._is_allowed_command(base_command):
            return False, f"Command '{base_command}' is not in the allowed commands list"
        
        # Check for dangerous patterns
        dangerous_pattern = self._check_dangerous_patterns(command)
        if dangerous_pattern:
            return False, f"Dangerous pattern detected: {dangerous_pattern}"
        
        # Check directory access
        if current_dir and not self._is_allowed_directory(current_dir):
            return False, f"Directory '{current_dir}' is not accessible"
        
        # Check for path traversal in command arguments
        if self._has_path_traversal(command):
            return False, "Path traversal detected in command"
        
        return True, ""
    
    def _is_forbidden_command(self, command: str) -> bool:
        """Check if command contains forbidden patterns"""
        command_lower = command.lower()
        
        for forbidden in self.policy.forbidden_commands:
            if forbidden.lower() in command_lower:
                return True
        
        # Additional dangerous patterns
        dangerous_patterns = [
            r'rm\s+-rf\s+/',
            r'rm\s+-rf\s+\*',
            r'>\s*/dev/sd[a-z]',
            r'mkfs\.',
            r'dd\s+if=.*of=/dev/',
            r'chmod\s+777',
            r'chown\s+-R.*/',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command_lower):
                return True
        
        return False
    
    def _is_allowed_command(self, base_command: str) -> bool:
        """Check if base command is allowed"""
        return base_command in self.policy.allowed_commands
    
    def _check_dangerous_patterns(self, command: str) -> str:
        """Check for dangerous patterns in command"""
        patterns = {
            r';\s*(rm|sudo|su)': 'Command chaining with dangerous commands',
            r'\|\s*(rm|sudo|su)': 'Piping to dangerous commands',
            r'&&\s*(rm|sudo|su)': 'Command concatenation with dangerous commands',
            r'`.*`': 'Command substitution detected',
            r'\$\(.*\)': 'Command substitution detected',
            r'eval\s+': 'eval command detected',
            r'exec\s+': 'exec command detected'
        }
        
        for pattern, message in patterns.items():
            if re.search(pattern, command, re.IGNORECASE):
                return message
        
        return ""
    
    def _is_allowed_directory(self, directory: str) -> bool:
        """Check if directory is allowed for access"""
        directory = os.path.abspath(directory)
        
        # Check forbidden directories
        for forbidden in self.policy.forbidden_directories:
            if directory.startswith(forbidden):
                return False
        
        # Check allowed directories
        for allowed in self.policy.allowed_directories:
            if directory.startswith(allowed):
                return True
        
        return False
    
    def _has_path_traversal(self, command: str) -> bool:
        """Check for path traversal attempts"""
        traversal_patterns = [
            r'\.\./.*\.\.',
            r'/\.\./\.\.',
            r'\\\.\.\\\.\.', 
            r'%2e%2e%2f',
            r'%2e%2e/',
            r'\.\.%2f'
        ]
        
        for pattern in traversal_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return True
        
        return False
    
    def requires_confirmation(self, command: str) -> bool:
        """Check if command requires user confirmation"""
        command_lower = command.lower()
        
        for confirm_cmd in self.policy.require_confirmation:
            if command_lower.startswith(confirm_cmd.lower()):
                return True
        
        return False