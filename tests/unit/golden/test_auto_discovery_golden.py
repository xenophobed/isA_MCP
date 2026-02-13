"""
CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the current behavior of the AutoDiscoverySystem.
If these tests fail, it means the auto-discovery interface has changed.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import os


@pytest.mark.golden
class TestAutoDiscoverySystemInitGolden:
    """Golden tests for AutoDiscoverySystem initialization - DO NOT MODIFY."""

    def test_init_sets_base_dir(self):
        """AutoDiscoverySystem sets base_dir from constructor."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem(base_dir="/test/path")

        assert system.base_dir == Path("/test/path").resolve()

    def test_init_default_base_dir(self):
        """AutoDiscoverySystem defaults to current directory."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()

        assert system.base_dir == Path(".").resolve()

    def test_init_sets_tools_dir(self):
        """AutoDiscoverySystem sets tools_dir."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem(base_dir="/test")

        assert system.tools_dir == Path("/test").resolve() / "tools"

    def test_init_sets_prompts_dir(self):
        """AutoDiscoverySystem sets prompts_dir."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem(base_dir="/test")

        assert system.prompts_dir == Path("/test").resolve() / "prompts"

    def test_init_sets_resources_dir(self):
        """AutoDiscoverySystem sets resources_dir."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem(base_dir="/test")

        assert system.resources_dir == Path("/test").resolve() / "resources"

    def test_init_empty_discovered_dicts(self):
        """AutoDiscoverySystem initializes with empty discovery dicts."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()

        assert system.discovered_tools == {}
        assert system.discovered_prompts == {}
        assert system.discovered_resources == {}


@pytest.mark.golden
class TestAutoDiscoveryDocstringExtractionGolden:
    """Golden tests for docstring metadata extraction - DO NOT MODIFY."""

    def test_extract_empty_docstring(self):
        """extract_docstring_metadata handles empty docstring."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()
        result = system.extract_docstring_metadata("")

        assert result["description"] == ""
        assert result["keywords"] == []
        assert result["usage"] == ""

    def test_extract_none_docstring(self):
        """extract_docstring_metadata handles None docstring."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()
        result = system.extract_docstring_metadata(None)

        assert result["description"] == ""
        assert result["keywords"] == []

    def test_extract_simple_docstring(self):
        """extract_docstring_metadata extracts first line as description."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()
        result = system.extract_docstring_metadata("This is a test function")

        assert result["description"] == "This is a test function"

    def test_extract_keywords_from_docstring(self):
        """extract_docstring_metadata extracts Keywords: field."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()
        docstring = """Test function description

        Keywords: search, query, find
        """
        result = system.extract_docstring_metadata(docstring)

        assert "search" in result["keywords"]
        assert "query" in result["keywords"]
        assert "find" in result["keywords"]

    def test_extract_usage_from_docstring(self):
        """extract_docstring_metadata extracts Usage: field."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()
        docstring = """Test function description

        Usage: example_usage()
        """
        result = system.extract_docstring_metadata(docstring)

        assert result["usage"] == "example_usage()"

    def test_auto_extract_keywords_from_description(self):
        """extract_docstring_metadata auto-extracts keywords if not provided."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()
        docstring = "Search function for finding documents in database"
        result = system.extract_docstring_metadata(docstring)

        # Should extract meaningful words (length > 3, not common words)
        assert len(result["keywords"]) > 0
        assert "search" in result["keywords"] or "function" in result["keywords"]


@pytest.mark.golden
class TestAutoDiscoveryModulePathGolden:
    """Golden tests for module path conversion - DO NOT MODIFY."""

    def test_get_module_path_simple(self):
        """_get_module_path converts simple file path."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem(base_dir="/test")
        file_path = Path("/test/tools/memory_tools.py")

        result = system._get_module_path(file_path)

        assert result == "tools.memory_tools"

    def test_get_module_path_nested(self):
        """_get_module_path converts nested file path."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem(base_dir="/test")
        file_path = Path("/test/tools/services/web_service.py")

        result = system._get_module_path(file_path)

        assert result == "tools.services.web_service"

    def test_get_module_path_removes_py_extension(self):
        """_get_module_path removes .py extension."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem(base_dir="/test")
        file_path = Path("/test/tools/test_tool.py")

        result = system._get_module_path(file_path)

        assert not result.endswith(".py")


@pytest.mark.golden
class TestAutoDiscoveryInterfaceGolden:
    """Golden tests for AutoDiscoverySystem public interface - DO NOT MODIFY."""

    def test_has_discover_tools_method(self):
        """AutoDiscoverySystem has discover_tools method."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()

        assert hasattr(system, "discover_tools")
        assert callable(system.discover_tools)

    def test_has_discover_prompts_method(self):
        """AutoDiscoverySystem has discover_prompts method."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()

        assert hasattr(system, "discover_prompts")
        assert callable(system.discover_prompts)

    def test_has_discover_resources_method(self):
        """AutoDiscoverySystem has discover_resources method."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()

        assert hasattr(system, "discover_resources")
        assert callable(system.discover_resources)

    def test_has_auto_register_with_mcp_method(self):
        """AutoDiscoverySystem has auto_register_with_mcp method."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()

        assert hasattr(system, "auto_register_with_mcp")
        assert callable(system.auto_register_with_mcp)

    def test_has_get_all_metadata_method(self):
        """AutoDiscoverySystem has get_all_metadata method."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()

        assert hasattr(system, "get_all_metadata")
        assert callable(system.get_all_metadata)

    def test_has_discover_functions_in_file_method(self):
        """AutoDiscoverySystem has discover_functions_in_file method."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()

        assert hasattr(system, "discover_functions_in_file")
        assert callable(system.discover_functions_in_file)


@pytest.mark.golden
class TestAutoDiscoveryGetAllMetadataGolden:
    """Golden tests for get_all_metadata - DO NOT MODIFY."""

    def test_get_all_metadata_returns_dict(self):
        """get_all_metadata returns a dictionary."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()
        result = system.get_all_metadata()

        assert isinstance(result, dict)

    def test_get_all_metadata_has_tools_key(self):
        """get_all_metadata includes 'tools' key."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()
        result = system.get_all_metadata()

        assert "tools" in result

    def test_get_all_metadata_has_prompts_key(self):
        """get_all_metadata includes 'prompts' key."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()
        result = system.get_all_metadata()

        assert "prompts" in result

    def test_get_all_metadata_has_resources_key(self):
        """get_all_metadata includes 'resources' key."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()
        result = system.get_all_metadata()

        assert "resources" in result


@pytest.mark.golden
class TestAutoDiscoveryToolDetectionGolden:
    """Golden tests for MCP tool detection - DO NOT MODIFY."""

    def test_check_for_mcp_tools_returns_bool(self):
        """_check_for_mcp_tools returns boolean."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()

        # Create temp file with @mcp.tool
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("@mcp.tool()\ndef test(): pass")
            temp_path = f.name

        try:
            result = system._check_for_mcp_tools(Path(temp_path))
            assert isinstance(result, bool)
            assert result is True
        finally:
            os.unlink(temp_path)

    def test_check_for_mcp_tools_false_for_no_decorator(self):
        """_check_for_mcp_tools returns False when no @mcp.tool."""
        from core.auto_discovery import AutoDiscoverySystem

        system = AutoDiscoverySystem()

        # Create temp file without @mcp.tool
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def regular_function(): pass")
            temp_path = f.name

        try:
            result = system._check_for_mcp_tools(Path(temp_path))
            assert result is False
        finally:
            os.unlink(temp_path)
