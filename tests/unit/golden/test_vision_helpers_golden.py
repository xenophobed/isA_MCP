"""
🔒 CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the CURRENT behavior of vision helper pure functions.
If these tests fail, it means behavior has changed unexpectedly.

Functions Under Test:
- extract_input_text (ui_helpers.py)
- analyze_task_requirements (ui_helpers.py)
"""

import pytest


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.vision
class TestExtractInputTextGolden:
    """
    Golden tests for extract_input_text() - DO NOT MODIFY.

    Location: tools/services/intelligence_service/vision/helper/ui_helpers.py
    Purpose: Extract text input from task descriptions using regex patterns
    """

    def test_extracts_quoted_text_double_quotes(self):
        """CURRENT BEHAVIOR: Extracts text within double quotes."""
        from tools.intelligent_tools.vision.helper.ui_helpers import extract_input_text

        result = extract_input_text('search for "python tutorials"')
        assert result == "python tutorials"

    def test_extracts_quoted_text_single_quotes(self):
        """CURRENT BEHAVIOR: Extracts text within single quotes."""
        from tools.intelligent_tools.vision.helper.ui_helpers import extract_input_text

        result = extract_input_text("find 'machine learning'")
        assert result == "machine learning"

    def test_extracts_text_after_type_keyword(self):
        """CURRENT BEHAVIOR: Extracts text after 'type' keyword."""
        from tools.intelligent_tools.vision.helper.ui_helpers import extract_input_text

        result = extract_input_text("type password123")
        assert result == "password123"

    def test_extracts_text_after_enter_keyword(self):
        """CURRENT BEHAVIOR: Extracts text after 'enter' keyword."""
        from tools.intelligent_tools.vision.helper.ui_helpers import extract_input_text

        result = extract_input_text("enter john@email.com")
        assert result == "john@email.com"

    def test_fallback_to_last_word(self):
        """CURRENT BEHAVIOR: Falls back to last word if no pattern matches."""
        from tools.intelligent_tools.vision.helper.ui_helpers import extract_input_text

        result = extract_input_text("random words here")
        assert result == "here"


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.vision
class TestAnalyzeTaskRequirementsGolden:
    """
    Golden tests for analyze_task_requirements() - DO NOT MODIFY.

    Location: tools/services/intelligence_service/vision/helper/ui_helpers.py
    Purpose: Analyze task to determine interaction type and fallback UI elements
    """

    def test_search_task_detection(self):
        """CURRENT BEHAVIOR: 'search' keyword sets task_type to 'search'."""
        from tools.intelligent_tools.vision.helper.ui_helpers import analyze_task_requirements

        result = analyze_task_requirements("search for products")

        assert result["task_type"] == "search"
        assert "input_text" in result["interactions"]

    def test_click_task_detection(self):
        """CURRENT BEHAVIOR: 'click' keyword sets task_type to 'click'."""
        from tools.intelligent_tools.vision.helper.ui_helpers import analyze_task_requirements

        result = analyze_task_requirements("click the button")

        assert result["task_type"] == "click"
        assert "click" in result["interactions"]

    def test_form_task_detection(self):
        """CURRENT BEHAVIOR: 'fill' keyword sets task_type to 'form'."""
        from tools.intelligent_tools.vision.helper.ui_helpers import analyze_task_requirements

        result = analyze_task_requirements("fill the form")

        assert result["task_type"] == "form"

    def test_returns_required_keys(self):
        """CURRENT BEHAVIOR: Result contains task_type, interactions, fallback_elements."""
        from tools.intelligent_tools.vision.helper.ui_helpers import analyze_task_requirements

        result = analyze_task_requirements("any task")

        assert "task_type" in result
        assert "interactions" in result
        assert "fallback_elements" in result

    def test_login_task_detection(self):
        """CURRENT BEHAVIOR: 'login' keyword returns 'generic' task type (no special handling)."""
        from tools.intelligent_tools.vision.helper.ui_helpers import analyze_task_requirements

        result = analyze_task_requirements("login to the website")

        # Note: Current behavior does NOT have special handling for 'login'
        # It falls through to 'generic' task type
        assert result["task_type"] == "generic"
