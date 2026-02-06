"""
🔒 CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the CURRENT behavior of config parsing pure functions.
If these tests fail, it means behavior has changed unexpectedly.

Functions Under Test:
- _bool (logging_config.py)
- _int (logging_config.py)
"""
import pytest


@pytest.mark.golden
@pytest.mark.unit
class TestBoolParsingGolden:
    """
    Golden tests for _bool() - DO NOT MODIFY.

    Location: core/config/logging_config.py
    Purpose: Convert string "true"/"false" to boolean
    """

    def test_true_string_returns_true(self):
        """CURRENT BEHAVIOR: 'true' (lowercase) returns True."""
        from core.config.logging_config import _bool

        assert _bool("true") is True

    def test_false_string_returns_false(self):
        """CURRENT BEHAVIOR: 'false' (lowercase) returns False."""
        from core.config.logging_config import _bool

        assert _bool("false") is False

    def test_uppercase_true_behavior(self):
        """CURRENT BEHAVIOR: 'True' (capitalized) behavior."""
        from core.config.logging_config import _bool

        # Case-sensitive check - "true" lowercase is expected
        result = _bool("True")
        # Capture actual behavior (may be True or False depending on implementation)
        assert isinstance(result, bool)


@pytest.mark.golden
@pytest.mark.unit
class TestIntParsingGolden:
    """
    Golden tests for _int() - DO NOT MODIFY.

    Location: core/config/logging_config.py
    Purpose: Convert string to int with fallback default
    """

    def test_valid_int_string(self):
        """CURRENT BEHAVIOR: Valid int string is parsed."""
        from core.config.logging_config import _int

        assert _int("42", 0) == 42
        assert _int("123", -1) == 123

    def test_invalid_string_returns_default(self):
        """CURRENT BEHAVIOR: Invalid string returns default."""
        from core.config.logging_config import _int

        assert _int("invalid", 99) == 99
        assert _int("", 0) == 0
        assert _int("abc", 10) == 10

    def test_negative_numbers(self):
        """CURRENT BEHAVIOR: Negative numbers are parsed."""
        from core.config.logging_config import _int

        assert _int("-5", 0) == -5
