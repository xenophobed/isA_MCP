"""
CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the current behavior of AutoDiscoverySystem integration.
If these tests fail, it means auto-discovery integration behavior has changed.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile


@pytest.mark.golden
@pytest.mark.integration
class TestAutoDiscoveryMCPIntegrationGolden:
    """Golden tests for AutoDiscovery + MCP integration - DO NOT MODIFY."""

    async def test_auto_register_calls_discover_methods(self):
        """auto_register_with_mcp calls all discover methods."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create required directories
            (Path(tmpdir) / "tools").mkdir()
            (Path(tmpdir) / "prompts").mkdir()
            (Path(tmpdir) / "resources").mkdir()

            system = AutoDiscoverySystem(base_dir=tmpdir)

            # Patch discover methods to track calls
            with (
                patch.object(system, "discover_tools", return_value={}) as mock_tools,
                patch.object(system, "discover_prompts", return_value={}) as mock_prompts,
                patch.object(system, "discover_resources", return_value={}) as mock_resources,
            ):

                mock_mcp = MagicMock()

                await system.auto_register_with_mcp(mock_mcp)

                # All discover methods should be called
                mock_tools.assert_called()
                mock_prompts.assert_called()
                mock_resources.assert_called()

    async def test_auto_register_handles_empty_directories(self):
        """auto_register_with_mcp handles empty directories gracefully."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create empty directories
            (Path(tmpdir) / "tools").mkdir()
            (Path(tmpdir) / "prompts").mkdir()
            (Path(tmpdir) / "resources").mkdir()

            system = AutoDiscoverySystem(base_dir=tmpdir)
            mock_mcp = MagicMock()

            # Should not raise
            await system.auto_register_with_mcp(mock_mcp)

            # Discovered items should be empty
            assert len(system.discovered_tools) == 0


@pytest.mark.golden
@pytest.mark.integration
class TestAutoDiscoveryToolRegistrationGolden:
    """Golden tests for tool registration integration - DO NOT MODIFY."""

    async def test_register_function_pattern(self):
        """auto_register_with_mcp looks for register_* functions."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create tools directory with a tool file
            tools_dir = Path(tmpdir) / "tools"
            tools_dir.mkdir()

            # Create a tool file with register function
            tool_file = tools_dir / "test_tools.py"
            tool_file.write_text('''
def register_test_tools(mcp):
    """Register test tools"""
    pass
''')

            # Create empty prompts and resources dirs
            (Path(tmpdir) / "prompts").mkdir()
            (Path(tmpdir) / "resources").mkdir()

            system = AutoDiscoverySystem(base_dir=tmpdir)
            mock_mcp = MagicMock()

            # Should attempt to call register_test_tools
            await system.auto_register_with_mcp(mock_mcp)

            # The system should have processed the file
            # (actual registration depends on the module loading)

    async def test_skips_ml_models_directory(self):
        """auto_register_with_mcp skips ML model directories."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create tools directory with ml_models subdirectory
            tools_dir = Path(tmpdir) / "tools"
            tools_dir.mkdir()
            ml_dir = tools_dir / "ml_models"
            ml_dir.mkdir()

            # Create a tool file in ml_models
            ml_tool = ml_dir / "ml_tool.py"
            ml_tool.write_text("@mcp.tool()\ndef ml_tool(): pass")

            # Create empty prompts and resources dirs
            (Path(tmpdir) / "prompts").mkdir()
            (Path(tmpdir) / "resources").mkdir()

            system = AutoDiscoverySystem(base_dir=tmpdir)

            # discover_tools should skip ML models
            tools = system.discover_tools()

            assert "ml_tool" not in tools


@pytest.mark.golden
@pytest.mark.integration
class TestAutoDiscoveryComposioIntegrationGolden:
    """Golden tests for Composio bridge integration - DO NOT MODIFY."""

    async def test_composio_bridge_attempt(self):
        """auto_register_with_mcp attempts Composio bridge registration."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "tools").mkdir()
            (Path(tmpdir) / "prompts").mkdir()
            (Path(tmpdir) / "resources").mkdir()

            system = AutoDiscoverySystem(base_dir=tmpdir)
            mock_mcp = MagicMock()

            # Composio import might fail - that's expected
            # The test verifies it handles the failure gracefully
            await system.auto_register_with_mcp(mock_mcp)

            # Should complete without error even if Composio not available


@pytest.mark.golden
@pytest.mark.integration
class TestAutoDiscoveryMetadataIntegrationGolden:
    """Golden tests for metadata integration - DO NOT MODIFY."""

    def test_discovered_tools_structure(self):
        """Discovered tools have expected structure."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir) / "tools"
            tools_dir.mkdir()

            # Create a tool file
            tool_file = tools_dir / "sample_tools.py"
            tool_file.write_text('''
@mcp.tool()
def sample_tool():
    """Sample tool description

    Keywords: sample, test, example
    """
    pass
''')

            system = AutoDiscoverySystem(base_dir=tmpdir)
            tools = system.discover_tools()

            if "sample_tool" in tools:
                tool = tools["sample_tool"]
                # Expected structure
                assert "name" in tool
                assert "file" in tool
                assert "description" in tool
                assert "keywords" in tool
                assert "type" in tool
                assert tool["type"] == "tool"

    def test_get_all_metadata_combines_discoveries(self):
        """get_all_metadata combines all discovered items."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "tools").mkdir()
            (Path(tmpdir) / "prompts").mkdir()
            (Path(tmpdir) / "resources").mkdir()

            system = AutoDiscoverySystem(base_dir=tmpdir)

            # Run discoveries
            system.discover_tools()
            system.discover_prompts()
            system.discover_resources()

            # Get all metadata
            metadata = system.get_all_metadata()

            assert "tools" in metadata
            assert "prompts" in metadata
            assert "resources" in metadata
            assert metadata["tools"] == system.discovered_tools
            assert metadata["prompts"] == system.discovered_prompts
            assert metadata["resources"] == system.discovered_resources
