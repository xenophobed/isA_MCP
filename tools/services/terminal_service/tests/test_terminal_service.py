"""
Tests for Terminal Service
"""

import unittest
import asyncio
import os
import tempfile
from unittest.mock import patch, MagicMock
from ..services.terminal_service import TerminalService
from ..models.terminal_models import CommandResult


class TestTerminalService(unittest.TestCase):
    def setUp(self):
        self.service = TerminalService()
    
    def test_initialization(self):
        """Test that service initializes correctly"""
        self.assertIsNotNone(self.service.sessions)
        self.assertIn(self.service.default_session_id, self.service.sessions)
        self.assertIsNotNone(self.service.security_validator)
    
    def test_session_management(self):
        """Test session creation and management"""
        # Test default session exists
        default_session = self.service.get_session_info()
        self.assertIsNotNone(default_session)
        self.assertEqual(default_session.session_id, "default")
        
        # Test creating new session
        new_session = self.service._get_or_create_session("test_session")
        self.assertEqual(new_session.session_id, "test_session")
        
        # Test listing sessions
        sessions = self.service.list_sessions()
        self.assertIn("default", sessions)
        self.assertIn("test_session", sessions)
        
        # Test deleting session
        success = self.service.delete_session("test_session")
        self.assertTrue(success)
        
        # Test cannot delete default session
        success = self.service.delete_session("default")
        self.assertFalse(success)
    
    def test_system_info(self):
        """Test system information retrieval"""
        system_info = self.service.get_system_info()
        
        self.assertIsNotNone(system_info.hostname)
        self.assertIsNotNone(system_info.username)
        self.assertIsNotNone(system_info.platform)
        self.assertIsNotNone(system_info.architecture)
    
    async def async_test_safe_command_execution(self):
        """Test execution of safe commands"""
        # Test simple echo command
        result = await self.service.execute_command("echo 'Hello World'")
        
        self.assertIsInstance(result, CommandResult)
        self.assertTrue(result.success)
        self.assertEqual(result.return_code, 0)
        self.assertIn("Hello World", result.stdout)
        self.assertEqual(result.command, "echo 'Hello World'")
    
    def test_safe_command_execution(self):
        """Wrapper for async test"""
        asyncio.run(self.async_test_safe_command_execution())
    
    async def async_test_dangerous_command_blocked(self):
        """Test that dangerous commands are blocked"""
        result = await self.service.execute_command("sudo rm -rf /")
        
        self.assertIsInstance(result, CommandResult)
        self.assertFalse(result.success)
        self.assertIn("Security validation failed", result.stderr)
    
    def test_dangerous_command_blocked(self):
        """Wrapper for async test"""
        asyncio.run(self.async_test_dangerous_command_blocked())
    
    async def async_test_cd_command(self):
        """Test cd command handling"""
        # Get current directory
        original_dir = self.service.get_session_info().current_directory
        
        # Try to change to a safe directory (home)
        home_dir = os.path.expanduser("~")
        result = await self.service.execute_command(f"cd {home_dir}")
        
        if result.success:
            # Check that session directory was updated
            updated_session = self.service.get_session_info()
            self.assertEqual(updated_session.current_directory, home_dir)
        
        # Test cd to non-existent directory
        result = await self.service.execute_command("cd /non/existent/directory")
        self.assertFalse(result.success)
        self.assertIn("No such file or directory", result.stderr)
    
    def test_cd_command(self):
        """Wrapper for async test"""
        asyncio.run(self.async_test_cd_command())
    
    async def async_test_command_timeout(self):
        """Test command timeout handling"""
        # Test with a command that would timeout (sleep)
        result = await self.service.execute_command("sleep 5", timeout=1)
        
        self.assertFalse(result.success)
        self.assertIn("timed out", result.stderr)
    
    def test_command_timeout(self):
        """Wrapper for async test"""
        asyncio.run(self.async_test_command_timeout())
    
    def test_command_history(self):
        """Test command history tracking"""
        # Execute a few commands
        async def run_commands():
            await self.service.execute_command("echo 'test1'")
            await self.service.execute_command("echo 'test2'")
            await self.service.execute_command("pwd")
        
        asyncio.run(run_commands())
        
        # Check history
        history = self.service.get_command_history(limit=10)
        self.assertGreaterEqual(len(history), 3)
        
        # Check that commands are in history
        command_texts = [cmd.command for cmd in history]
        self.assertIn("echo 'test1'", command_texts)
        self.assertIn("echo 'test2'", command_texts)
        self.assertIn("pwd", command_texts)
    
    async def async_test_confirmation_required(self):
        """Test that dangerous commands require confirmation"""
        result = await self.service.execute_command("rm important_file.txt")
        
        self.assertFalse(result.success)
        self.assertIn("requires confirmation", result.stderr)
        
        # Test that same command works with confirmation
        result = await self.service.execute_command(
            "rm /tmp/non_existent_file.txt", 
            require_confirmation=True
        )
        # Should still fail because file doesn't exist, but not due to confirmation
        self.assertFalse(result.success)
        self.assertNotIn("requires confirmation", result.stderr)
    
    def test_confirmation_required(self):
        """Wrapper for async test"""
        asyncio.run(self.async_test_confirmation_required())


if __name__ == "__main__":
    unittest.main()