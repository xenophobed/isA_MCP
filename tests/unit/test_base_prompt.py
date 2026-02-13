"""
TDD Unit Tests for BasePrompt - prompts/base_prompt.py

These tests define the expected behavior BEFORE implementation.
Run these tests to drive the implementation of BasePrompt.

Run with: pytest tests/unit/test_base_prompt.py -v
"""

import pytest
from unittest.mock import Mock

# =============================================================================
# BasePrompt Core Tests
# =============================================================================


class TestBasePromptInit:
    """TDD: BasePrompt should initialize with empty state"""

    def test_init_creates_empty_registered_prompts_list(self):
        from prompts.base_prompt import BasePrompt

        bp = BasePrompt()
        assert bp.registered_prompts == []

    def test_init_has_default_category_attribute(self):
        from prompts.base_prompt import BasePrompt

        bp = BasePrompt()
        assert hasattr(bp, "default_category")


class TestRegisterPrompt:
    """TDD: BasePrompt.register_prompt() should register prompts to MCP"""

    def test_register_prompt_calls_mcp_decorator(self):
        from prompts.base_prompt import BasePrompt

        mcp = Mock()
        mcp.prompt = Mock(return_value=lambda f: f)
        bp = BasePrompt()

        def my_prompt(msg: str = "") -> str:
            return msg

        bp.register_prompt(mcp, my_prompt)
        mcp.prompt.assert_called()

    def test_register_prompt_tracks_in_list(self):
        from prompts.base_prompt import BasePrompt

        mcp = Mock()
        mcp.prompt = Mock(return_value=lambda f: f)
        bp = BasePrompt()

        def my_prompt(msg: str = "") -> str:
            return msg

        bp.register_prompt(mcp, my_prompt)

        assert len(bp.registered_prompts) == 1
        assert bp.registered_prompts[0]["name"] == "my_prompt"

    def test_register_prompt_with_custom_name(self):
        from prompts.base_prompt import BasePrompt

        mcp = Mock()
        mcp.prompt = Mock(return_value=lambda f: f)
        bp = BasePrompt()

        def func() -> str:
            return "x"

        bp.register_prompt(mcp, func, name="custom_name")
        assert bp.registered_prompts[0]["name"] == "custom_name"

    def test_register_prompt_with_category(self):
        from prompts.base_prompt import BasePrompt

        mcp = Mock()
        mcp.prompt = Mock(return_value=lambda f: f)
        bp = BasePrompt()

        def func() -> str:
            return "x"

        bp.register_prompt(mcp, func, category="reasoning")
        assert bp.registered_prompts[0]["category"] == "reasoning"

    def test_register_prompt_with_tags(self):
        from prompts.base_prompt import BasePrompt

        mcp = Mock()
        mcp.prompt = Mock(return_value=lambda f: f)
        bp = BasePrompt()

        def func() -> str:
            return "x"

        bp.register_prompt(mcp, func, tags=["a", "b"])
        assert bp.registered_prompts[0]["tags"] == ["a", "b"]


class TestRegisterAllPrompts:
    """TDD: BasePrompt.register_all_prompts() template method"""

    def test_register_all_prompts_is_noop(self):
        from prompts.base_prompt import BasePrompt

        mcp = Mock()
        bp = BasePrompt()
        result = bp.register_all_prompts(mcp)

        assert result is None
        assert len(bp.registered_prompts) == 0


class TestFormatPromptOutput:
    """TDD: BasePrompt.format_prompt_output() helper"""

    def test_format_string_unchanged(self):
        from prompts.base_prompt import BasePrompt

        bp = BasePrompt()

        result = bp.format_prompt_output("Hello")
        assert result == "Hello"

    def test_format_with_sections(self):
        from prompts.base_prompt import BasePrompt

        bp = BasePrompt()

        result = bp.format_prompt_output(sections={"Context": "ctx", "Task": "do it"})

        assert "## Context" in result
        assert "ctx" in result
        assert "## Task" in result

    def test_format_with_variables(self):
        from prompts.base_prompt import BasePrompt

        bp = BasePrompt()

        result = bp.format_prompt_output("Hello {name}", variables={"name": "World"})
        assert result == "Hello World"


class TestGetRegisteredPrompts:
    """TDD: BasePrompt.get_registered_prompts() query method"""

    def test_get_all_prompts(self):
        from prompts.base_prompt import BasePrompt

        mcp = Mock()
        mcp.prompt = Mock(return_value=lambda f: f)
        bp = BasePrompt()

        def p1() -> str:
            return "1"

        def p2() -> str:
            return "2"

        bp.register_prompt(mcp, p1)
        bp.register_prompt(mcp, p2)

        assert len(bp.get_registered_prompts()) == 2

    def test_filter_by_category(self):
        from prompts.base_prompt import BasePrompt

        mcp = Mock()
        mcp.prompt = Mock(return_value=lambda f: f)
        bp = BasePrompt()

        def p1() -> str:
            return "1"

        def p2() -> str:
            return "2"

        bp.register_prompt(mcp, p1, category="cat1")
        bp.register_prompt(mcp, p2, category="cat2")

        result = bp.get_registered_prompts(category="cat1")
        assert len(result) == 1
        assert result[0]["category"] == "cat1"


# =============================================================================
# simple_prompt Decorator Tests
# =============================================================================


class TestSimplePromptDecorator:
    """TDD: @simple_prompt decorator for quick prompt definition"""

    def test_adds_category_attribute(self):
        from prompts.base_prompt import simple_prompt

        @simple_prompt(category="test")
        def my_prompt() -> str:
            return "x"

        assert my_prompt._prompt_category == "test"

    def test_adds_tags_attribute(self):
        from prompts.base_prompt import simple_prompt

        @simple_prompt(tags=["a", "b"])
        def my_prompt() -> str:
            return "x"

        assert my_prompt._prompt_tags == ["a", "b"]

    def test_preserves_function_behavior(self):
        from prompts.base_prompt import simple_prompt

        @simple_prompt()
        def my_prompt(name: str = "X") -> str:
            return f"Hi {name}"

        assert my_prompt("Test") == "Hi Test"

    def test_default_category_is_default(self):
        from prompts.base_prompt import simple_prompt

        @simple_prompt()
        def my_prompt() -> str:
            return "x"

        assert my_prompt._prompt_category == "default"
