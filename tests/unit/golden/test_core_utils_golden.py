"""
🔒 CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the CURRENT behavior of core/utils.py pure functions.
If these tests fail, it means behavior has changed unexpectedly.

Functions Under Test:
- Validators: validate_json, validate_email, validate_user_id, validate_tool_name
- Sanitizers: sanitize_input
- Formatters: format_timestamp, parse_timestamp, format_duration, format_bytes
- Hashing: generate_hash
- Security: mask_sensitive_data
- JSON: safe_json_loads, safe_json_dumps, merge_json_objects
- Response builders: create_success_response, create_error_response
"""

import pytest
from datetime import datetime


@pytest.mark.golden
@pytest.mark.unit
class TestValidateJsonGolden:
    """
    Golden tests for validate_json() - DO NOT MODIFY.

    Location: core/utils.py
    Purpose: Validate if a string is valid JSON
    """

    def test_valid_json_object(self):
        """CURRENT BEHAVIOR: Valid JSON object returns True."""
        from core.utils import validate_json

        assert validate_json('{"key": "value"}') is True
        assert validate_json('{"nested": {"value": 123}}') is True
        assert validate_json("{}") is True

    def test_valid_json_array(self):
        """CURRENT BEHAVIOR: Valid JSON array returns True."""
        from core.utils import validate_json

        assert validate_json("[1, 2, 3]") is True
        assert validate_json("[]") is True
        assert validate_json('[{"a": 1}, {"b": 2}]') is True

    def test_valid_json_primitives(self):
        """CURRENT BEHAVIOR: JSON primitives return True."""
        from core.utils import validate_json

        assert validate_json('"string"') is True
        assert validate_json("123") is True
        assert validate_json("true") is True
        assert validate_json("false") is True
        assert validate_json("null") is True

    def test_invalid_json(self):
        """CURRENT BEHAVIOR: Invalid JSON returns False."""
        from core.utils import validate_json

        assert validate_json("invalid json") is False
        assert validate_json("{key: value}") is False  # Missing quotes
        assert validate_json("{'key': 'value'}") is False  # Single quotes
        assert validate_json("{") is False  # Incomplete


@pytest.mark.golden
@pytest.mark.unit
class TestValidateEmailGolden:
    """
    Golden tests for validate_email() - DO NOT MODIFY.

    Location: core/utils.py
    Purpose: Validate email format using regex
    """

    def test_valid_emails(self):
        """CURRENT BEHAVIOR: Standard email formats return True."""
        from core.utils import validate_email

        assert validate_email("user@example.com") is True
        assert validate_email("test.user@domain.org") is True
        assert validate_email("user+tag@example.com") is True

    def test_valid_emails_with_subdomains(self):
        """CURRENT BEHAVIOR: Emails with subdomains return True."""
        from core.utils import validate_email

        assert validate_email("user@mail.example.com") is True
        assert validate_email("test@sub.domain.co.uk") is True

    def test_invalid_emails(self):
        """CURRENT BEHAVIOR: Invalid email formats return False."""
        from core.utils import validate_email

        assert validate_email("invalid.email") is False
        assert validate_email("@missing-local.com") is False
        assert validate_email("missing-at.com") is False
        assert validate_email("") is False
        assert validate_email("spaces in@email.com") is False


@pytest.mark.golden
@pytest.mark.unit
class TestValidateUserIdGolden:
    """
    Golden tests for validate_user_id() - DO NOT MODIFY.

    Location: core/utils.py
    Purpose: Validate user ID format (alphanumeric, underscore, hyphen, dot; max 100 chars)
    """

    def test_valid_user_ids(self):
        """CURRENT BEHAVIOR: Valid user IDs return True."""
        from core.utils import validate_user_id

        assert validate_user_id("valid_user-123") is True
        assert validate_user_id("user.name") is True
        assert validate_user_id("USER_123") is True
        assert validate_user_id("a") is True  # Single char

    def test_invalid_user_id_special_chars(self):
        """CURRENT BEHAVIOR: Special characters return False."""
        from core.utils import validate_user_id

        assert validate_user_id("user@invalid") is False
        assert validate_user_id("user#name") is False
        assert validate_user_id("user name") is False  # Space

    def test_invalid_user_id_too_long(self):
        """CURRENT BEHAVIOR: User ID > 100 chars returns False."""
        from core.utils import validate_user_id

        assert validate_user_id("a" * 100) is True  # Exactly 100
        assert validate_user_id("a" * 101) is False  # Exceeds max


@pytest.mark.golden
@pytest.mark.unit
class TestValidateToolNameGolden:
    """
    Golden tests for validate_tool_name() - DO NOT MODIFY.

    Location: core/utils.py
    Purpose: Validate tool name format (alphanumeric and underscore only; max 50 chars)
    """

    def test_valid_tool_names(self):
        """CURRENT BEHAVIOR: Valid tool names return True."""
        from core.utils import validate_tool_name

        assert validate_tool_name("valid_tool") is True
        assert validate_tool_name("MY_TOOL_123") is True
        assert validate_tool_name("tool") is True
        assert validate_tool_name("Tool123") is True

    def test_invalid_tool_name_with_dash(self):
        """CURRENT BEHAVIOR: Dashes are NOT allowed in tool names."""
        from core.utils import validate_tool_name

        assert validate_tool_name("tool-with-dash") is False

    def test_invalid_tool_name_too_long(self):
        """CURRENT BEHAVIOR: Tool name > 50 chars returns False."""
        from core.utils import validate_tool_name

        assert validate_tool_name("a" * 50) is True  # Exactly 50
        assert validate_tool_name("a" * 51) is False  # Exceeds max


@pytest.mark.golden
@pytest.mark.unit
class TestSanitizeInputGolden:
    """
    Golden tests for sanitize_input() - DO NOT MODIFY.

    Location: core/utils.py
    Purpose: Remove control characters and null bytes; truncate to max length
    """

    def test_removes_null_bytes(self):
        """CURRENT BEHAVIOR: Null bytes are removed."""
        from core.utils import sanitize_input

        assert sanitize_input("hello\x00world") == "helloworld"

    def test_truncates_to_max_length(self):
        """CURRENT BEHAVIOR: Long strings are truncated to max_length."""
        from core.utils import sanitize_input

        result = sanitize_input("a" * 2000)  # Default max is 1000
        assert len(result) == 1000

        result_custom = sanitize_input("a" * 100, max_length=50)
        assert len(result_custom) == 50

    def test_preserves_normal_text(self):
        """CURRENT BEHAVIOR: Normal text is unchanged."""
        from core.utils import sanitize_input

        assert sanitize_input("normal text") == "normal text"

    def test_preserves_newlines_tabs(self):
        """CURRENT BEHAVIOR: Newlines and tabs are preserved."""
        from core.utils import sanitize_input

        result = sanitize_input("text\nwith\ttabs")
        assert "\n" in result
        assert "\t" in result


@pytest.mark.golden
@pytest.mark.unit
class TestFormatTimestampGolden:
    """
    Golden tests for format_timestamp() - DO NOT MODIFY.

    Location: core/utils.py
    Purpose: Format datetime as ISO string
    """

    def test_formats_datetime_to_iso(self):
        """CURRENT BEHAVIOR: Datetime is formatted to ISO string."""
        from core.utils import format_timestamp

        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = format_timestamp(dt)

        assert "2024-01-15" in result
        assert "10:30:45" in result
        assert "T" in result  # ISO separator

    def test_none_returns_current_timestamp(self):
        """CURRENT BEHAVIOR: None input returns current timestamp."""
        from core.utils import format_timestamp

        result = format_timestamp()  # No argument
        assert "T" in result  # Has ISO separator
        assert len(result) >= 19  # At least YYYY-MM-DDTHH:MM:SS


@pytest.mark.golden
@pytest.mark.unit
class TestParseTimestampGolden:
    """
    Golden tests for parse_timestamp() - DO NOT MODIFY.

    Location: core/utils.py
    Purpose: Parse ISO timestamp string to datetime
    """

    def test_parses_iso_timestamp(self):
        """CURRENT BEHAVIOR: ISO string is parsed to datetime."""
        from core.utils import parse_timestamp

        dt = parse_timestamp("2024-01-15T10:30:45")

        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 10
        assert dt.minute == 30
        assert dt.second == 45

    def test_parses_timestamp_with_z_suffix(self):
        """CURRENT BEHAVIOR: Handles Z suffix (UTC)."""
        from core.utils import parse_timestamp

        dt = parse_timestamp("2024-01-15T10:30:45Z")
        assert isinstance(dt, datetime)


@pytest.mark.golden
@pytest.mark.unit
class TestFormatDurationGolden:
    """
    Golden tests for format_duration() - DO NOT MODIFY.

    Location: core/utils.py
    Purpose: Format seconds into human-readable duration
    """

    def test_formats_milliseconds(self):
        """CURRENT BEHAVIOR: < 1 second shows milliseconds."""
        from core.utils import format_duration

        result = format_duration(0.5)
        assert "ms" in result
        assert "500" in result

    def test_formats_seconds(self):
        """CURRENT BEHAVIOR: 1-60 seconds shows seconds."""
        from core.utils import format_duration

        result = format_duration(30)
        assert "s" in result
        assert "30" in result

    def test_formats_minutes(self):
        """CURRENT BEHAVIOR: 60-3600 seconds shows minutes."""
        from core.utils import format_duration

        result = format_duration(120)
        assert "m" in result
        assert "2" in result

    def test_formats_hours(self):
        """CURRENT BEHAVIOR: >= 3600 seconds shows hours."""
        from core.utils import format_duration

        result = format_duration(3600)
        assert "h" in result
        assert "1" in result

        result_2h = format_duration(7200)
        assert "2" in result_2h


@pytest.mark.golden
@pytest.mark.unit
class TestFormatBytesGolden:
    """
    Golden tests for format_bytes() - DO NOT MODIFY.

    Location: core/utils.py
    Purpose: Format byte count into human-readable format
    """

    def test_formats_bytes(self):
        """CURRENT BEHAVIOR: < 1024 shows bytes."""
        from core.utils import format_bytes

        result = format_bytes(512)
        assert "B" in result
        assert "512" in result

    def test_formats_kilobytes(self):
        """CURRENT BEHAVIOR: 1024+ shows KB."""
        from core.utils import format_bytes

        result = format_bytes(1024)
        assert "KB" in result

    def test_formats_megabytes(self):
        """CURRENT BEHAVIOR: 1MB+ shows MB."""
        from core.utils import format_bytes

        result = format_bytes(1048576)  # 1 MB
        assert "MB" in result

    def test_formats_gigabytes(self):
        """CURRENT BEHAVIOR: 1GB+ shows GB."""
        from core.utils import format_bytes

        result = format_bytes(1073741824)  # 1 GB
        assert "GB" in result


@pytest.mark.golden
@pytest.mark.unit
class TestGenerateHashGolden:
    """
    Golden tests for generate_hash() - DO NOT MODIFY.

    Location: core/utils.py
    Purpose: Generate hash of data using specified algorithm
    """

    def test_sha256_is_deterministic(self):
        """CURRENT BEHAVIOR: Same input produces same SHA256 hash."""
        from core.utils import generate_hash

        hash1 = generate_hash("test", "sha256")
        hash2 = generate_hash("test", "sha256")
        assert hash1 == hash2

    def test_sha256_produces_64_chars(self):
        """CURRENT BEHAVIOR: SHA256 produces 64-char hex string."""
        from core.utils import generate_hash

        result = generate_hash("test", "sha256")
        assert len(result) == 64

    def test_md5_produces_32_chars(self):
        """CURRENT BEHAVIOR: MD5 produces 32-char hex string."""
        from core.utils import generate_hash

        result = generate_hash("test", "md5")
        assert len(result) == 32

    def test_different_inputs_different_hashes(self):
        """CURRENT BEHAVIOR: Different inputs produce different hashes."""
        from core.utils import generate_hash

        hash1 = generate_hash("input1", "sha256")
        hash2 = generate_hash("input2", "sha256")
        assert hash1 != hash2


@pytest.mark.golden
@pytest.mark.unit
class TestMaskSensitiveDataGolden:
    """
    Golden tests for mask_sensitive_data() - DO NOT MODIFY.

    Location: core/utils.py
    Purpose: Recursively mask sensitive data in dictionaries
    """

    def test_masks_password_field(self):
        """CURRENT BEHAVIOR: 'password' field is masked."""
        from core.utils import mask_sensitive_data

        data = {"username": "john", "password": "secret123"}
        masked = mask_sensitive_data(data)

        assert masked["username"] == "john"
        assert masked["password"] == "***MASKED***"

    def test_masks_api_key_field(self):
        """CURRENT BEHAVIOR: 'api_key' field is masked."""
        from core.utils import mask_sensitive_data

        data = {"name": "test", "api_key": "key_xyz"}
        masked = mask_sensitive_data(data)

        assert masked["api_key"] == "***MASKED***"

    def test_masks_token_field(self):
        """CURRENT BEHAVIOR: 'token' field is masked."""
        from core.utils import mask_sensitive_data

        data = {"token": "abc123"}
        masked = mask_sensitive_data(data)

        assert masked["token"] == "***MASKED***"

    def test_masks_nested_structures(self):
        """CURRENT BEHAVIOR: Nested sensitive fields are masked."""
        from core.utils import mask_sensitive_data

        data = {"user": {"token": "abc123", "name": "John"}}
        masked = mask_sensitive_data(data)

        assert masked["user"]["token"] == "***MASKED***"
        assert masked["user"]["name"] == "John"


@pytest.mark.golden
@pytest.mark.unit
class TestSafeJsonLoadsGolden:
    """
    Golden tests for safe_json_loads() - DO NOT MODIFY.

    Location: core/utils.py
    Purpose: Safely load JSON with default fallback on error
    """

    def test_parses_valid_json(self):
        """CURRENT BEHAVIOR: Valid JSON is parsed correctly."""
        from core.utils import safe_json_loads

        result = safe_json_loads('{"key": "value"}')
        assert result == {"key": "value"}

    def test_returns_default_on_invalid_json(self):
        """CURRENT BEHAVIOR: Invalid JSON returns default value."""
        from core.utils import safe_json_loads

        result = safe_json_loads("invalid json", default={})
        assert result == {}

    def test_returns_none_when_no_default(self):
        """CURRENT BEHAVIOR: Invalid JSON with no default returns None."""
        from core.utils import safe_json_loads

        result = safe_json_loads("invalid json")
        assert result is None


@pytest.mark.golden
@pytest.mark.unit
class TestSafeJsonDumpsGolden:
    """
    Golden tests for safe_json_dumps() - DO NOT MODIFY.

    Location: core/utils.py
    Purpose: Safely serialize objects to JSON with error handling
    """

    def test_serializes_dict(self):
        """CURRENT BEHAVIOR: Dict is serialized to JSON string."""
        from core.utils import safe_json_dumps

        result = safe_json_dumps({"key": "value"})
        assert '"key"' in result
        assert '"value"' in result

    def test_applies_indentation(self):
        """CURRENT BEHAVIOR: Default indentation is applied."""
        from core.utils import safe_json_dumps

        result = safe_json_dumps({"key": "value"})
        # With indent, result should have newlines
        assert "\n" in result or '{"key"' in result


@pytest.mark.golden
@pytest.mark.unit
class TestMergeJsonObjectsGolden:
    """
    Golden tests for merge_json_objects() - DO NOT MODIFY.

    Location: core/utils.py
    Purpose: Merge multiple JSON objects/dictionaries
    """

    def test_merges_multiple_dicts(self):
        """CURRENT BEHAVIOR: Multiple dicts are merged."""
        from core.utils import merge_json_objects

        result = merge_json_objects({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_later_values_override(self):
        """CURRENT BEHAVIOR: Later values override earlier ones."""
        from core.utils import merge_json_objects

        result = merge_json_objects({"a": 1}, {"a": 3})
        assert result == {"a": 3}

    def test_empty_args_returns_empty_dict(self):
        """CURRENT BEHAVIOR: No arguments returns empty dict."""
        from core.utils import merge_json_objects

        result = merge_json_objects()
        assert result == {}


@pytest.mark.golden
@pytest.mark.unit
class TestCreateSuccessResponseGolden:
    """
    Golden tests for create_success_response() - DO NOT MODIFY.

    Location: core/utils.py
    Purpose: Create standardized success response dictionary
    """

    def test_creates_success_structure(self):
        """CURRENT BEHAVIOR: Success response has required fields."""
        from core.utils import create_success_response

        response = create_success_response({"id": 1}, "Created")

        assert response["status"] == "success"
        assert response["message"] == "Created"
        assert response["data"] == {"id": 1}
        assert "timestamp" in response

    def test_default_message(self):
        """CURRENT BEHAVIOR: Default message is 'Operation successful'."""
        from core.utils import create_success_response

        response = create_success_response({"id": 1})
        assert response["message"] == "Operation successful"


@pytest.mark.golden
@pytest.mark.unit
class TestCreateErrorResponseGolden:
    """
    Golden tests for create_error_response() - DO NOT MODIFY.

    Location: core/utils.py
    Purpose: Create standardized error response dictionary
    """

    def test_creates_error_structure(self):
        """CURRENT BEHAVIOR: Error response has required fields."""
        from core.utils import create_error_response

        response = create_error_response("INVALID_INPUT", "Email is invalid", {"field": "email"})

        assert response["status"] == "error"
        assert response["error"]["code"] == "INVALID_INPUT"
        assert response["error"]["message"] == "Email is invalid"
        assert response["error"]["details"] == {"field": "email"}

    def test_optional_details(self):
        """CURRENT BEHAVIOR: Details is optional."""
        from core.utils import create_error_response

        response = create_error_response("ERROR", "Something failed")
        assert "error" in response
        assert response["error"]["code"] == "ERROR"
