"""
CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the current behavior of AutoDiscoverySystem component interactions.
If these tests fail, it means auto-discovery component behavior has changed.
"""

import pytest
from pathlib import Path
import tempfile
import os


@pytest.mark.golden
@pytest.mark.component
class TestAutoDiscoveryToolsComponentGolden:
    """Golden tests for discover_tools component behavior - DO NOT MODIFY."""

    def test_discover_tools_returns_dict(self):
        """discover_tools returns a dictionary."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir) / "tools"
            tools_dir.mkdir()

            system = AutoDiscoverySystem(base_dir=tmpdir)
            result = system.discover_tools()

            assert isinstance(result, dict)

    def test_discover_tools_skips_init_files(self):
        """discover_tools skips __init__.py files."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir) / "tools"
            tools_dir.mkdir()

            # Create __init__.py with tool decorator
            init_file = tools_dir / "__init__.py"
            init_file.write_text("@mcp.tool()\ndef init_tool(): pass")

            system = AutoDiscoverySystem(base_dir=tmpdir)
            result = system.discover_tools()

            # Should not discover tools from __init__.py
            assert "init_tool" not in result

    def test_discover_tools_handles_missing_dir(self):
        """discover_tools handles missing tools directory gracefully."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.TemporaryDirectory() as tmpdir:
            # Don't create tools directory
            system = AutoDiscoverySystem(base_dir=tmpdir)
            result = system.discover_tools()

            assert result == {}

    def test_discover_tools_populates_discovered_tools(self):
        """discover_tools populates self.discovered_tools."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir) / "tools"
            tools_dir.mkdir()

            system = AutoDiscoverySystem(base_dir=tmpdir)
            system.discover_tools()

            assert system.discovered_tools is not None
            assert isinstance(system.discovered_tools, dict)


@pytest.mark.golden
@pytest.mark.component
class TestAutoDiscoveryPromptsComponentGolden:
    """Golden tests for discover_prompts component behavior - DO NOT MODIFY."""

    def test_discover_prompts_returns_dict(self):
        """discover_prompts returns a dictionary."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = Path(tmpdir) / "prompts"
            prompts_dir.mkdir()

            system = AutoDiscoverySystem(base_dir=tmpdir)
            result = system.discover_prompts()

            assert isinstance(result, dict)

    def test_discover_prompts_finds_prompt_variables(self):
        """discover_prompts finds variables ending with _prompt."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = Path(tmpdir) / "prompts"
            prompts_dir.mkdir()

            # Create a prompt file with _prompt variable
            prompt_file = prompts_dir / "test_prompts.py"
            prompt_file.write_text('test_prompt = "This is a test prompt"')

            system = AutoDiscoverySystem(base_dir=tmpdir)
            result = system.discover_prompts()

            # Should discover the prompt
            assert "test_prompt" in result

    def test_discover_prompts_handles_missing_dir(self):
        """discover_prompts handles missing prompts directory gracefully."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.TemporaryDirectory() as tmpdir:
            # Don't create prompts directory
            system = AutoDiscoverySystem(base_dir=tmpdir)
            result = system.discover_prompts()

            assert result == {}


@pytest.mark.golden
@pytest.mark.component
class TestAutoDiscoveryResourcesComponentGolden:
    """Golden tests for discover_resources component behavior - DO NOT MODIFY."""

    def test_discover_resources_returns_dict(self):
        """discover_resources returns a dictionary."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = Path(tmpdir) / "resources"
            resources_dir.mkdir()

            system = AutoDiscoverySystem(base_dir=tmpdir)
            result = system.discover_resources()

            assert isinstance(result, dict)

    def test_discover_resources_handles_missing_dir(self):
        """discover_resources handles missing resources directory gracefully."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.TemporaryDirectory() as tmpdir:
            # Don't create resources directory
            system = AutoDiscoverySystem(base_dir=tmpdir)
            result = system.discover_resources()

            assert result == {}


@pytest.mark.golden
@pytest.mark.component
class TestAutoDiscoveryFunctionParsingGolden:
    """Golden tests for discover_functions_in_file - DO NOT MODIFY."""

    def test_discover_functions_returns_list(self):
        """discover_functions_in_file returns a list."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def test(): pass")
            temp_path = f.name

        try:
            system = AutoDiscoverySystem()
            result = system.discover_functions_in_file(Path(temp_path))

            assert isinstance(result, list)
        finally:
            os.unlink(temp_path)

    def test_discover_functions_finds_mcp_tool_decorator(self):
        """discover_functions_in_file finds @mcp.tool() decorated functions."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('''
@mcp.tool()
def my_tool():
    """This is my tool description"""
    pass
''')
            temp_path = f.name

        try:
            system = AutoDiscoverySystem()
            result = system.discover_functions_in_file(Path(temp_path))

            assert len(result) == 1
            assert result[0]["name"] == "my_tool"
            assert result[0]["type"] == "tool"
        finally:
            os.unlink(temp_path)

    def test_discover_functions_extracts_docstring(self):
        """discover_functions_in_file extracts function docstring."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('''
@mcp.tool()
def documented_tool():
    """This is the tool description"""
    pass
''')
            temp_path = f.name

        try:
            system = AutoDiscoverySystem()
            result = system.discover_functions_in_file(Path(temp_path))

            assert len(result) == 1
            assert result[0]["docstring"] == "This is the tool description"
            assert result[0]["description"] == "This is the tool description"
        finally:
            os.unlink(temp_path)

    def test_discover_functions_ignores_non_tool_functions(self):
        """discover_functions_in_file ignores functions without @mcp.tool()."""
        from core.auto_discovery import AutoDiscoverySystem

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
def regular_function():
    pass

@mcp.tool()
def tool_function():
    pass
""")
            temp_path = f.name

        try:
            system = AutoDiscoverySystem()
            result = system.discover_functions_in_file(Path(temp_path))

            assert len(result) == 1
            assert result[0]["name"] == "tool_function"
        finally:
            os.unlink(temp_path)


@pytest.mark.golden
@pytest.mark.component
class TestAutoDiscoveryRegistrationGolden:
    """Golden tests for auto_register_with_mcp - DO NOT MODIFY."""

    async def test_auto_register_is_async(self):
        """auto_register_with_mcp is an async method."""
        from core.auto_discovery import AutoDiscoverySystem
        import asyncio

        system = AutoDiscoverySystem()

        # Should be a coroutine function
        assert asyncio.iscoroutinefunction(system.auto_register_with_mcp)

    async def test_auto_register_accepts_mcp_and_config(self):
        """auto_register_with_mcp accepts mcp and optional config."""
        from core.auto_discovery import AutoDiscoverySystem
        import inspect

        system = AutoDiscoverySystem()
        sig = inspect.signature(system.auto_register_with_mcp)

        params = list(sig.parameters.keys())
        assert "mcp" in params
        assert "config" in params
