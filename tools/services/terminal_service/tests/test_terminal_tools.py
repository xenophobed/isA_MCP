"""
Tests for Terminal Tools MCP Integration
"""

import unittest
import asyncio
import json
import sys
import os

# Add the parent directories to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from ..tools.terminal_tools import TerminalTools


class TestTerminalTools(unittest.TestCase):
    def setUp(self):
        self.tools = TerminalTools()
    
    def test_initialization(self):
        """Test that tools initialize correctly"""
        self.assertIsNotNone(self.tools.terminal_service)
        self.assertIsNotNone(self.tools.billing_info)
    
    async def async_test_execute_command(self):
        """Test execute_command tool"""
        response = await self.tools.execute_command("echo 'Hello from MCP'")
        
        # Parse response
        response_data = json.loads(response)
        
        self.assertEqual(response_data["status"], "success")
        self.assertEqual(response_data["action"], "execute_command")
        self.assertIn("data", response_data)
        self.assertIn("Hello from MCP", response_data["data"]["stdout"])
    
    def test_execute_command(self):
        """Wrapper for async test"""
        asyncio.run(self.async_test_execute_command())
    
    async def async_test_dangerous_command_blocked(self):
        """Test that dangerous commands are blocked"""
        response = await self.tools.execute_command("sudo rm -rf /")
        
        response_data = json.loads(response)
        
        self.assertEqual(response_data["status"], "error")
        self.assertIn("Security validation failed", response_data["error_message"])
    
    def test_dangerous_command_blocked(self):
        """Wrapper for async test"""
        asyncio.run(self.async_test_dangerous_command_blocked())
    
    async def async_test_get_current_directory(self):
        """Test get_current_directory tool"""
        response = await self.tools.get_current_directory()
        
        response_data = json.loads(response)
        
        self.assertEqual(response_data["status"], "success")
        self.assertIn("current_directory", response_data["data"])
        self.assertIn("session_id", response_data["data"])
    
    def test_get_current_directory(self):
        """Wrapper for async test"""
        asyncio.run(self.async_test_get_current_directory())
    
    async def async_test_list_files(self):
        """Test list_files tool"""
        response = await self.tools.list_files()
        
        response_data = json.loads(response)
        
        # Should be successful (ls command should work)
        self.assertEqual(response_data["status"], "success")
        self.assertIn("data", response_data)
    
    def test_list_files(self):
        """Wrapper for async test"""
        asyncio.run(self.async_test_list_files())
    
    async def async_test_get_system_info(self):
        """Test get_system_info tool"""
        response = await self.tools.get_system_info()
        
        response_data = json.loads(response)
        
        self.assertEqual(response_data["status"], "success")
        self.assertIn("hostname", response_data["data"])
        self.assertIn("username", response_data["data"])
        self.assertIn("platform", response_data["data"])
    
    def test_get_system_info(self):
        """Wrapper for async test"""
        asyncio.run(self.async_test_get_system_info())
    
    async def async_test_session_management(self):
        """Test session management tools"""
        # Create a session
        response = await self.tools.create_session("test_session_123")
        response_data = json.loads(response)
        self.assertEqual(response_data["status"], "success")
        
        # List sessions
        response = await self.tools.list_sessions()
        response_data = json.loads(response)
        self.assertEqual(response_data["status"], "success")
        
        session_ids = [s["session_id"] for s in response_data["data"]["sessions"]]
        self.assertIn("test_session_123", session_ids)
        self.assertIn("default", session_ids)
        
        # Delete session
        response = await self.tools.delete_session("test_session_123")
        response_data = json.loads(response)
        self.assertEqual(response_data["status"], "success")
        
        # Try to delete default session (should fail)
        response = await self.tools.delete_session("default")
        response_data = json.loads(response)
        self.assertEqual(response_data["status"], "error")
    
    def test_session_management(self):
        """Wrapper for async test"""
        asyncio.run(self.async_test_session_management())
    
    async def async_test_command_history(self):
        """Test command history tool"""
        # Execute a few commands first
        await self.tools.execute_command("echo 'history test 1'")
        await self.tools.execute_command("echo 'history test 2'")
        await self.tools.execute_command("pwd")
        
        # Get history
        response = await self.tools.get_command_history()
        response_data = json.loads(response)
        
        self.assertEqual(response_data["status"], "success")
        self.assertIn("history", response_data["data"])
        self.assertGreater(response_data["data"]["count"], 0)
        
        # Check that our commands are in history
        commands = [h["command"] for h in response_data["data"]["history"]]
        self.assertTrue(any("history test 1" in cmd for cmd in commands))
    
    def test_command_history(self):
        """Wrapper for async test"""
        asyncio.run(self.async_test_command_history())
    
    async def async_test_change_directory(self):
        """Test change_directory tool"""
        # Get current directory first
        response = await self.tools.get_current_directory()
        original_data = json.loads(response)
        original_dir = original_data["data"]["current_directory"]
        
        # Try to change to home directory
        home_dir = os.path.expanduser("~")
        response = await self.tools.change_directory(home_dir)
        response_data = json.loads(response)
        
        if response_data["status"] == "success":
            # Verify directory changed
            response = await self.tools.get_current_directory()
            new_data = json.loads(response)
            self.assertEqual(new_data["data"]["current_directory"], home_dir)
        
        # Test changing to non-existent directory
        response = await self.tools.change_directory("/non/existent/path")
        response_data = json.loads(response)
        self.assertEqual(response_data["status"], "error")
    
    def test_change_directory(self):
        """Wrapper for async test"""
        asyncio.run(self.async_test_change_directory())
    
    def test_response_format(self):
        """Test that all responses follow the expected format"""
        async def check_response_format():
            response = await self.tools.get_system_info()
            response_data = json.loads(response)
            
            # Check required fields
            self.assertIn("status", response_data)
            self.assertIn("action", response_data)
            self.assertIn("data", response_data)
            self.assertIn("billing_info", response_data)
            
            # Check billing info structure
            billing = response_data["billing_info"]
            self.assertIn("total_cost", billing)
            self.assertIn("operations", billing)
            
        asyncio.run(check_response_format())


if __name__ == "__main__":
    unittest.main()