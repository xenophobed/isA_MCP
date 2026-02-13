"""
Unit layer test configuration and fixtures.

Layer 4: Unit Tests
- Tests pure functions and models
- No I/O operations
- Maximum isolation with everything mocked
"""

import pytest
from typing import Any
from dataclasses import dataclass
from decimal import Decimal

# ═══════════════════════════════════════════════════════════════
# Sample Data Structures
# ═══════════════════════════════════════════════════════════════


@dataclass
class SampleToolMetadata:
    """Sample tool metadata for testing."""

    name: str
    description: str
    input_schema: dict
    output_type: str = "string"


@dataclass
class SamplePromptMetadata:
    """Sample prompt metadata for testing."""

    name: str
    description: str
    template: str
    arguments: list


@dataclass
class SampleDocstringResult:
    """Sample docstring parsing result."""

    description: str
    args: dict
    returns: str


# ═══════════════════════════════════════════════════════════════
# Test Data Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def valid_tool_schema():
    """Provide a valid tool schema."""
    return {
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "Input text"},
            "max_length": {
                "type": "integer",
                "description": "Maximum output length",
                "default": 100,
            },
        },
        "required": ["input"],
    }


@pytest.fixture
def invalid_tool_schemas():
    """Provide various invalid tool schemas for testing."""
    return [
        {},  # Empty schema
        {"type": "string"},  # Wrong type
        {"type": "object"},  # Missing properties
        {"type": "object", "properties": {}},  # Empty properties
        {"type": "object", "properties": {"x": {}}},  # Property without type
    ]


@pytest.fixture
def sample_docstrings():
    """Provide sample docstrings for parsing tests."""
    return {
        "simple": """
        A simple description.
        """,
        "with_args": """
        A function that does something.

        Args:
            arg1: First argument
            arg2: Second argument
        """,
        "with_returns": """
        A function that returns something.

        Args:
            input: The input value

        Returns:
            The processed result
        """,
        "complex": """
        A complex function with multiple features.

        This function performs various operations on the input
        and returns a structured result.

        Args:
            input_text: The text to process
            max_tokens: Maximum tokens (default: 100)
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            dict: A dictionary containing:
                - result: The processed text
                - metadata: Processing metadata

        Raises:
            ValueError: If input is invalid
        """,
        "google_style": """
        Short description.

        Longer description that spans
        multiple lines.

        Args:
            param1 (str): First parameter.
            param2 (int, optional): Second parameter. Defaults to 10.

        Returns:
            str: The result string.
        """,
        "numpy_style": """
        Short description.

        Parameters
        ----------
        param1 : str
            First parameter.
        param2 : int, optional
            Second parameter (default is 10).

        Returns
        -------
        str
            The result string.
        """,
    }


@pytest.fixture
def sample_decorator_sources():
    """Provide sample decorator source code for parsing tests."""
    return {
        "simple_tool": '''
@mcp.tool()
async def simple_tool(input: str) -> str:
    """A simple tool."""
    return input
''',
        "tool_with_args": '''
@mcp.tool()
async def tool_with_args(
    required_arg: str,
    optional_arg: int = 10,
    flag: bool = False
) -> dict:
    """A tool with multiple arguments.

    Args:
        required_arg: A required string argument
        optional_arg: An optional integer argument
        flag: A boolean flag
    """
    return {"result": required_arg}
''',
        "prompt_simple": '''
@mcp.prompt()
def simple_prompt(topic: str) -> str:
    """A simple prompt."""
    return f"Write about {topic}"
''',
        "resource_simple": '''
@mcp.resource("resource://data/{id}")
async def simple_resource(id: str) -> dict:
    """A simple resource."""
    return {"id": id}
''',
    }


# ═══════════════════════════════════════════════════════════════
# Type Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def python_type_mappings():
    """Provide Python to JSON Schema type mappings."""
    return {
        "str": "string",
        "int": "integer",
        "float": "number",
        "bool": "boolean",
        "list": "array",
        "dict": "object",
        "None": "null",
        "Any": "any",
    }


@pytest.fixture
def sample_function_signatures():
    """Provide sample function signatures for schema generation."""

    def func_simple(arg: str) -> str:
        pass

    def func_with_defaults(arg1: str, arg2: int = 10) -> dict:
        pass

    def func_with_optional(arg1: str, arg2: int | None = None) -> str:
        pass

    def func_complex(
        required: str, optional: int = 10, nullable: str | None = None, flag: bool = False
    ) -> dict:
        pass

    return {
        "simple": func_simple,
        "with_defaults": func_with_defaults,
        "with_optional": func_with_optional,
        "complex": func_complex,
    }


# ═══════════════════════════════════════════════════════════════
# Validation Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def valid_jwt_tokens():
    """Provide valid JWT token structures."""
    return [
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature",
    ]


@pytest.fixture
def invalid_jwt_tokens():
    """Provide invalid JWT token structures."""
    return [
        "",  # Empty
        "not.a.token",  # Missing parts
        "a.b.c.d",  # Too many parts
        "invalid",  # Not base64
        "a.b",  # Only two parts
    ]


@pytest.fixture
def valid_tool_names():
    """Provide valid tool names."""
    return ["simple_tool", "tool123", "my_awesome_tool", "CamelCaseTool", "tool_with_numbers_123"]


@pytest.fixture
def invalid_tool_names():
    """Provide invalid tool names."""
    return [
        "",  # Empty
        "tool with spaces",  # Spaces
        "tool-with-dashes",  # Dashes (depending on rules)
        "../malicious",  # Path traversal
        "tool; rm -rf /",  # Command injection
        "a" * 256,  # Too long
    ]


# ═══════════════════════════════════════════════════════════════
# Pure Function Test Helpers
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def assert_schema_valid():
    """Provide schema validation helper."""

    def _validate(schema: dict) -> bool:
        required_keys = ["type"]
        if not all(k in schema for k in required_keys):
            return False
        if schema["type"] == "object":
            if "properties" not in schema:
                return False
        return True

    return _validate


@pytest.fixture
def assert_docstring_parsed():
    """Provide docstring parsing assertion helper."""

    def _assert(result: SampleDocstringResult, expected_args: list):
        assert result.description is not None
        assert len(result.description) > 0
        for arg in expected_args:
            assert arg in result.args

    return _assert


# ═══════════════════════════════════════════════════════════════
# Edge Case Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def edge_case_inputs():
    """Provide edge case inputs for testing."""
    return {
        "empty_string": "",
        "whitespace": "   ",
        "newlines": "\n\n\n",
        "unicode": "Hello \u4e16\u754c \ud83c\udf0d",
        "special_chars": "!@#$%^&*()[]{}",
        "very_long": "x" * 10000,
        "null_bytes": "hello\x00world",
        "mixed": "  \n\tHello\r\n  ",
    }


@pytest.fixture
def numeric_edge_cases():
    """Provide numeric edge cases."""
    return {
        "zero": 0,
        "negative": -1,
        "max_int": 2**31 - 1,
        "min_int": -(2**31),
        "float_precision": 0.1 + 0.2,  # ~0.30000000000000004
        "infinity": float("inf"),
        "neg_infinity": float("-inf"),
        "nan": float("nan"),
        "decimal": Decimal("0.1"),
    }
