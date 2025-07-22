"""
Tests for Security Validator
"""

import unittest
import os
from ..services.security_validator import SecurityValidator


class TestSecurityValidator(unittest.TestCase):
    def setUp(self):
        self.validator = SecurityValidator()
    
    def test_allowed_commands(self):
        """Test that allowed commands pass validation"""
        safe_commands = [
            "ls -la",
            "pwd",
            "whoami",
            "cat file.txt",
            "grep pattern file.txt",
            "git status",
            "npm --version",
            "python3 --version"
        ]
        
        for command in safe_commands:
            is_valid, error = self.validator.validate_command(command)
            self.assertTrue(is_valid, f"Command '{command}' should be allowed: {error}")
    
    def test_forbidden_commands(self):
        """Test that dangerous commands are blocked"""
        dangerous_commands = [
            "sudo rm -rf /",
            "rm -rf *",
            "dd if=/dev/zero of=/dev/sda",
            "shutdown now",
            "chmod 777 /etc/passwd",
            "killall -9"
        ]
        
        for command in dangerous_commands:
            is_valid, error = self.validator.validate_command(command)
            self.assertFalse(is_valid, f"Command '{command}' should be blocked")
            self.assertIsNotNone(error)
    
    def test_command_injection(self):
        """Test that command injection attempts are blocked"""
        injection_attempts = [
            "ls; rm -rf /",
            "cat file.txt | sudo rm",
            "echo hello && sudo shutdown",
            "ls `rm file.txt`",
            "pwd $(rm file.txt)"
        ]
        
        for command in injection_attempts:
            is_valid, error = self.validator.validate_command(command)
            self.assertFalse(is_valid, f"Injection attempt '{command}' should be blocked")
    
    def test_path_traversal(self):
        """Test that path traversal attempts are blocked"""
        traversal_attempts = [
            "cat ../../etc/passwd",
            "ls ../../../root",
            "cat /etc/../etc/passwd",
            "ls %2e%2e%2fpasswd"
        ]
        
        for command in traversal_attempts:
            is_valid, error = self.validator.validate_command(command)
            self.assertFalse(is_valid, f"Path traversal '{command}' should be blocked")
    
    def test_confirmation_required(self):
        """Test that certain commands require confirmation"""
        confirmation_commands = [
            "rm important_file.txt",
            "git reset --hard",
            "npm install -g package",
            "docker run -it ubuntu"
        ]
        
        for command in confirmation_commands:
            requires_confirmation = self.validator.requires_confirmation(command)
            self.assertTrue(requires_confirmation, f"Command '{command}' should require confirmation")
    
    def test_empty_command(self):
        """Test that empty commands are rejected"""
        is_valid, error = self.validator.validate_command("")
        self.assertFalse(is_valid)
        self.assertIn("Empty command", error)
    
    def test_directory_validation(self):
        """Test directory access validation"""
        # Test with user directory (should be allowed)
        user_dir = os.path.expanduser("~/Documents")
        is_valid, error = self.validator.validate_command("ls", user_dir)
        self.assertTrue(is_valid or not os.path.exists(user_dir))  # Allow if directory exists
        
        # Test with system directory (should be blocked)
        is_valid, error = self.validator.validate_command("ls", "/etc")
        self.assertFalse(is_valid)


if __name__ == "__main__":
    unittest.main()