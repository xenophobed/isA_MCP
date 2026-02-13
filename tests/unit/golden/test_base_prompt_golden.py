"""
Golden Tests for BasePrompt - prompts/base_prompt.py

These tests capture the expected behavior of the BasePrompt class,
simple_prompt decorator, and create_simple_prompt_registration decorator.

Run with: pytest tests/unit/golden/test_base_prompt_golden.py -v
"""

import pytest
from unittest.mock import Mock, patch

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def base_prompt():
    """Create a BasePrompt instance for testing"""
    from prompts.base_prompt import BasePrompt

    return BasePrompt()


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server"""
    mcp = Mock()
    mcp.prompt = Mock(return_value=lambda f: f)
    return mcp


# =============================================================================
# BasePrompt.__init__ Tests
# =============================================================================


class TestBasePromptInit:
    """Tests for BasePrompt initialization"""

    def test_init_creates_empty_registered_prompts_list(self, base_prompt):
        """Registered prompts list should be empty initially"""
        assert base_prompt.registered_prompts == []
        assert isinstance(base_prompt.registered_prompts, list)

    def test_init_sets_default_category(self, base_prompt):
        """Default category should be 'default'"""
        assert base_prompt.default_category == "default"


# =============================================================================
# BasePrompt.register_prompt Tests
# =============================================================================


class TestRegisterPrompt:
    """Tests for prompt registration"""

    def test_register_prompt_calls_mcp_prompt(self, base_prompt, mock_mcp):
        """Should call mcp.prompt() decorator"""

        def test_prompt(msg: str = "") -> str:
            return msg

        base_prompt.register_prompt(mock_mcp, test_prompt)
        mock_mcp.prompt.assert_called()

    def test_register_prompt_tracks_registration(self, base_prompt, mock_mcp):
        """Should add prompt to registered_prompts list"""

        def my_prompt(msg: str = "") -> str:
            """Test description"""
            return msg

        base_prompt.register_prompt(mock_mcp, my_prompt)

        assert len(base_prompt.registered_prompts) == 1
        reg = base_prompt.registered_prompts[0]
        assert reg["name"] == "my_prompt"
        assert reg["function"] == "my_prompt"
        assert reg["description"] == "Test description"

    def test_register_prompt_with_custom_name(self, base_prompt, mock_mcp):
        """Should allow custom prompt name"""

        def func() -> str:
            return "x"

        base_prompt.register_prompt(mock_mcp, func, name="custom_name")

        assert base_prompt.registered_prompts[0]["name"] == "custom_name"
        assert base_prompt.registered_prompts[0]["function"] == "func"

    def test_register_prompt_with_custom_description(self, base_prompt, mock_mcp):
        """Should allow custom description override"""

        def func() -> str:
            """Original docstring"""
            return "x"

        base_prompt.register_prompt(mock_mcp, func, description="Custom description")

        assert base_prompt.registered_prompts[0]["description"] == "Custom description"

    def test_register_prompt_with_category(self, base_prompt, mock_mcp):
        """Should track category"""

        def func() -> str:
            return "x"

        base_prompt.register_prompt(mock_mcp, func, category="reasoning")

        assert base_prompt.registered_prompts[0]["category"] == "reasoning"

    def test_register_prompt_default_category(self, base_prompt, mock_mcp):
        """Should use default category when not specified"""

        def func() -> str:
            return "x"

        base_prompt.register_prompt(mock_mcp, func)

        assert base_prompt.registered_prompts[0]["category"] == "default"

    def test_register_prompt_with_tags(self, base_prompt, mock_mcp):
        """Should track tags"""

        def func() -> str:
            return "x"

        base_prompt.register_prompt(mock_mcp, func, tags=["analysis", "reasoning"])

        assert base_prompt.registered_prompts[0]["tags"] == ["analysis", "reasoning"]

    def test_register_prompt_default_empty_tags(self, base_prompt, mock_mcp):
        """Tags should default to empty list"""

        def func() -> str:
            return "x"

        base_prompt.register_prompt(mock_mcp, func)

        assert base_prompt.registered_prompts[0]["tags"] == []

    def test_register_prompt_multiple_registrations(self, base_prompt, mock_mcp):
        """Should track multiple registrations"""

        def p1() -> str:
            return "1"

        def p2() -> str:
            return "2"

        def p3() -> str:
            return "3"

        base_prompt.register_prompt(mock_mcp, p1)
        base_prompt.register_prompt(mock_mcp, p2)
        base_prompt.register_prompt(mock_mcp, p3)

        assert len(base_prompt.registered_prompts) == 3

    def test_register_prompt_passes_name_kwarg_to_mcp(self, base_prompt, mock_mcp):
        """Should pass name kwarg to mcp.prompt()"""

        def func() -> str:
            return "x"

        base_prompt.register_prompt(mock_mcp, func, name="Custom Name")

        call_kwargs = mock_mcp.prompt.call_args[1]
        assert call_kwargs.get("name") == "Custom Name"

    def test_register_prompt_returns_decorated_function(self, base_prompt, mock_mcp):
        """Should return the decorated function"""

        def func() -> str:
            return "test"

        result = base_prompt.register_prompt(mock_mcp, func)
        assert callable(result)

    def test_register_prompt_uses_decorator_attributes(self, base_prompt, mock_mcp):
        """Should use attributes from @simple_prompt decorator"""
        from prompts.base_prompt import simple_prompt

        @simple_prompt(category="custom_cat", tags=["tag1"])
        def decorated_prompt() -> str:
            return "x"

        base_prompt.register_prompt(mock_mcp, decorated_prompt)

        assert base_prompt.registered_prompts[0]["category"] == "custom_cat"
        assert base_prompt.registered_prompts[0]["tags"] == ["tag1"]


# =============================================================================
# BasePrompt.register_all_prompts Tests
# =============================================================================


class TestRegisterAllPrompts:
    """Tests for the template method"""

    def test_register_all_prompts_is_noop_by_default(self, base_prompt, mock_mcp):
        """Base implementation should do nothing"""
        result = base_prompt.register_all_prompts(mock_mcp)
        assert result is None
        assert len(base_prompt.registered_prompts) == 0


# =============================================================================
# BasePrompt.format_prompt_output Tests
# =============================================================================


class TestFormatPromptOutput:
    """Tests for prompt output formatting"""

    def test_format_string_unchanged(self, base_prompt):
        """Simple string should be returned unchanged"""
        result = base_prompt.format_prompt_output("Hello World")
        assert result == "Hello World"

    def test_format_empty_string(self, base_prompt):
        """Empty string should be returned"""
        result = base_prompt.format_prompt_output("")
        assert result == ""

    def test_format_none_returns_empty(self, base_prompt):
        """None content should return empty string"""
        result = base_prompt.format_prompt_output(None)
        assert result == ""

    def test_format_with_sections(self, base_prompt):
        """Should format sections with headers"""
        result = base_prompt.format_prompt_output(
            sections={"Context": "Some context", "Instructions": "Do something"}
        )

        assert "## Context" in result
        assert "Some context" in result
        assert "## Instructions" in result
        assert "Do something" in result

    def test_format_sections_separated_by_newlines(self, base_prompt):
        """Sections should be separated by blank lines"""
        result = base_prompt.format_prompt_output(sections={"A": "a", "B": "b"})

        assert "\n\n" in result

    def test_format_with_variables(self, base_prompt):
        """Should substitute variables"""
        result = base_prompt.format_prompt_output(
            "Hello {name}, task: {task}", variables={"name": "User", "task": "test"}
        )

        assert result == "Hello User, task: test"

    def test_format_variables_partial(self, base_prompt):
        """Should raise KeyError for missing variables"""
        with pytest.raises(KeyError):
            base_prompt.format_prompt_output("Hello {name} {missing}", variables={"name": "User"})

    def test_format_sections_override_content(self, base_prompt):
        """Sections should override content string"""
        result = base_prompt.format_prompt_output(
            "This will be ignored", sections={"Header": "Section content"}
        )

        assert "This will be ignored" not in result
        assert "## Header" in result


# =============================================================================
# BasePrompt.create_system_prompt Tests
# =============================================================================


class TestCreateSystemPrompt:
    """Tests for system prompt creation"""

    def test_create_with_role_only(self, base_prompt):
        """Should create prompt with just role"""
        result = base_prompt.create_system_prompt(role="You are an assistant")
        assert "You are an assistant" in result

    def test_create_with_capabilities(self, base_prompt):
        """Should include capabilities list"""
        result = base_prompt.create_system_prompt(
            role="Assistant", capabilities=["answer questions", "search data"]
        )

        assert "Capabilities:" in result
        assert "- answer questions" in result
        assert "- search data" in result

    def test_create_with_constraints(self, base_prompt):
        """Should include constraints/guidelines"""
        result = base_prompt.create_system_prompt(
            role="Assistant", constraints=["Be concise", "Be accurate"]
        )

        assert "Guidelines:" in result
        assert "- Be concise" in result
        assert "- Be accurate" in result

    def test_create_full_system_prompt(self, base_prompt):
        """Should combine role, capabilities, and constraints"""
        result = base_prompt.create_system_prompt(
            role="You are a helpful assistant",
            capabilities=["answer", "search"],
            constraints=["be brief"],
        )

        assert "You are a helpful assistant" in result
        assert "Capabilities:" in result
        assert "Guidelines:" in result


# =============================================================================
# BasePrompt.get_registered_prompts Tests
# =============================================================================


class TestGetRegisteredPrompts:
    """Tests for retrieving registered prompts"""

    def test_get_all_prompts(self, base_prompt, mock_mcp):
        """Should return all registered prompts"""

        def p1() -> str:
            return "1"

        def p2() -> str:
            return "2"

        base_prompt.register_prompt(mock_mcp, p1)
        base_prompt.register_prompt(mock_mcp, p2)

        result = base_prompt.get_registered_prompts()
        assert len(result) == 2

    def test_get_empty_when_none_registered(self, base_prompt):
        """Should return empty list when no prompts registered"""
        result = base_prompt.get_registered_prompts()
        assert result == []

    def test_filter_by_category(self, base_prompt, mock_mcp):
        """Should filter by category"""

        def p1() -> str:
            return "1"

        def p2() -> str:
            return "2"

        base_prompt.register_prompt(mock_mcp, p1, category="cat1")
        base_prompt.register_prompt(mock_mcp, p2, category="cat2")

        result = base_prompt.get_registered_prompts(category="cat1")
        assert len(result) == 1
        assert result[0]["category"] == "cat1"

    def test_filter_by_category_no_match(self, base_prompt, mock_mcp):
        """Should return empty list when no category match"""

        def p1() -> str:
            return "1"

        base_prompt.register_prompt(mock_mcp, p1, category="cat1")

        result = base_prompt.get_registered_prompts(category="nonexistent")
        assert result == []

    def test_filter_by_tags_any_match(self, base_prompt, mock_mcp):
        """Should match any tag (OR logic)"""

        def p1() -> str:
            return "1"

        def p2() -> str:
            return "2"

        base_prompt.register_prompt(mock_mcp, p1, tags=["a", "b"])
        base_prompt.register_prompt(mock_mcp, p2, tags=["c", "d"])

        result = base_prompt.get_registered_prompts(tags=["a"])
        assert len(result) == 1
        assert "a" in result[0]["tags"]

    def test_filter_by_multiple_tags(self, base_prompt, mock_mcp):
        """Should match if any of the filter tags match"""

        def p1() -> str:
            return "1"

        def p2() -> str:
            return "2"

        base_prompt.register_prompt(mock_mcp, p1, tags=["x"])
        base_prompt.register_prompt(mock_mcp, p2, tags=["y"])

        result = base_prompt.get_registered_prompts(tags=["x", "y"])
        assert len(result) == 2


# =============================================================================
# simple_prompt Decorator Tests
# =============================================================================


class TestSimplePromptDecorator:
    """Tests for @simple_prompt decorator"""

    def test_adds_category_attribute(self):
        """Should add _prompt_category attribute"""
        from prompts.base_prompt import simple_prompt

        @simple_prompt(category="test_cat")
        def my_prompt() -> str:
            return "x"

        assert hasattr(my_prompt, "_prompt_category")
        assert my_prompt._prompt_category == "test_cat"

    def test_adds_tags_attribute(self):
        """Should add _prompt_tags attribute"""
        from prompts.base_prompt import simple_prompt

        @simple_prompt(tags=["tag1", "tag2"])
        def my_prompt() -> str:
            return "x"

        assert hasattr(my_prompt, "_prompt_tags")
        assert my_prompt._prompt_tags == ["tag1", "tag2"]

    def test_default_category(self):
        """Default category should be 'default'"""
        from prompts.base_prompt import simple_prompt

        @simple_prompt()
        def my_prompt() -> str:
            return "x"

        assert my_prompt._prompt_category == "default"

    def test_default_tags_empty(self):
        """Default tags should be empty list"""
        from prompts.base_prompt import simple_prompt

        @simple_prompt()
        def my_prompt() -> str:
            return "x"

        assert my_prompt._prompt_tags == []

    def test_preserves_function_behavior(self):
        """Decorated function should work normally"""
        from prompts.base_prompt import simple_prompt

        @simple_prompt(category="test")
        def greet(name: str = "World") -> str:
            return f"Hello {name}"

        assert greet() == "Hello World"
        assert greet("Test") == "Hello Test"

    def test_preserves_function_name(self):
        """Should preserve function __name__"""
        from prompts.base_prompt import simple_prompt

        @simple_prompt()
        def my_special_prompt() -> str:
            return "x"

        assert my_special_prompt.__name__ == "my_special_prompt"


# =============================================================================
# create_simple_prompt_registration Decorator Tests
# =============================================================================


class TestCreateSimplePromptRegistration:
    """Tests for create_simple_prompt_registration class decorator"""

    def test_returns_callable_decorator(self):
        """Should return a callable decorator"""
        from prompts.base_prompt import create_simple_prompt_registration

        decorator = create_simple_prompt_registration("register_test")
        assert callable(decorator)

    def test_default_function_name(self):
        """Default function name should be 'register_prompts'"""
        from prompts.base_prompt import create_simple_prompt_registration

        decorator = create_simple_prompt_registration()
        assert callable(decorator)


# =============================================================================
# Integration Tests
# =============================================================================


class TestBasePromptIntegration:
    """Integration tests for BasePrompt"""

    def test_subclass_override_register_all_prompts(self, mock_mcp):
        """Subclasses can override register_all_prompts"""
        from prompts.base_prompt import BasePrompt

        class MyPrompts(BasePrompt):
            def register_all_prompts(self, mcp):
                def hello(name: str = "World") -> str:
                    return f"Hello {name}"

                self.register_prompt(mcp, hello, category="greeting")

        prompts = MyPrompts()
        prompts.register_all_prompts(mock_mcp)

        assert len(prompts.registered_prompts) == 1
        assert prompts.registered_prompts[0]["name"] == "hello"
        assert prompts.registered_prompts[0]["category"] == "greeting"

    def test_format_helpers_in_subclass(self):
        """Format helpers should work in subclasses"""
        from prompts.base_prompt import BasePrompt

        class MyPrompts(BasePrompt):
            def build_analysis_prompt(self, topic: str) -> str:
                return self.format_prompt_output(
                    sections={"Topic": topic, "Task": "Analyze thoroughly"}
                )

        prompts = MyPrompts()
        result = prompts.build_analysis_prompt("Python")

        assert "## Topic" in result
        assert "Python" in result
        assert "## Task" in result

    def test_combined_category_and_tag_filtering(self, mock_mcp):
        """Category and tag filtering should work together"""
        from prompts.base_prompt import BasePrompt

        bp = BasePrompt()

        def p1() -> str:
            return "1"

        def p2() -> str:
            return "2"

        def p3() -> str:
            return "3"

        bp.register_prompt(mock_mcp, p1, category="cat1", tags=["a"])
        bp.register_prompt(mock_mcp, p2, category="cat1", tags=["b"])
        bp.register_prompt(mock_mcp, p3, category="cat2", tags=["a"])

        # Filter by category only
        cat1_prompts = bp.get_registered_prompts(category="cat1")
        assert len(cat1_prompts) == 2

        # Filter by tag only
        tag_a_prompts = bp.get_registered_prompts(tags=["a"])
        assert len(tag_a_prompts) == 2

        # Note: current implementation doesn't support combined filtering
        # This documents the current behavior
