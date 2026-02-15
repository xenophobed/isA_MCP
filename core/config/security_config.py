"""
Security configuration for command execution.

This module provides security hardening for bash command execution:
- Command allowlist validation
- Dangerous pattern blocking
- Environment variable configuration
- Audit logging of blocked commands

Configuration via environment variables:
- BASH_COMMAND_ALLOWLIST: Comma-separated list of additional allowed commands
- BASH_COMMAND_ALLOWLIST_MODE: "strict" (only allowlist) or "permissive" (allowlist + block dangerous)
- BASH_AUDIT_BLOCKED_COMMANDS: "true"/"false" to enable/disable audit logging

Security Model:
- In STRICT mode: Only commands in the allowlist can be executed
- In PERMISSIVE mode: Any command is allowed unless it matches a dangerous pattern
- Dangerous patterns are ALWAYS blocked regardless of mode

Usage:
    from core.config.security_config import validate_command, SecurityConfig

    # Quick validation
    is_allowed, reason = validate_command("ls -la")

    # Or use the config object
    config = SecurityConfig.from_env()
    is_allowed, reason = config.validate("git status")
"""

import os
import re
import logging
from dataclasses import dataclass, field
from typing import Tuple, Set, List, FrozenSet

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Maximum allowed command length (8KB default)
MAX_COMMAND_LENGTH: int = 8192

# Default allowed commands - common safe development tools
DEFAULT_ALLOWED_COMMANDS: FrozenSet[str] = frozenset(
    {
        # File system navigation
        "ls",
        "pwd",
        "cd",
        "find",
        "tree",
        "du",
        "df",
        # File reading (non-destructive)
        "cat",
        "head",
        "tail",
        "less",
        "more",
        "wc",
        "file",
        # Text processing
        "grep",
        "awk",
        "sed",
        "sort",
        "uniq",
        "cut",
        "tr",
        "diff",
        # Version control
        "git",
        "gh",
        "svn",
        # Python
        "python",
        "python3",
        "pip",
        "pip3",
        "pytest",
        "poetry",
        "pdm",
        "uv",
        "ruff",
        "black",
        "isort",
        "mypy",
        "pylint",
        "flake8",
        # Node.js
        "node",
        "npm",
        "npx",
        "yarn",
        "pnpm",
        "bun",
        # Build tools
        "make",
        "cmake",
        "cargo",
        "go",
        "rustc",
        "gcc",
        "g++",
        "clang",
        # Container tools
        "docker",
        "docker-compose",
        "podman",
        "kubectl",
        "helm",
        # System info (read-only)
        "whoami",
        "id",
        "uname",
        "date",
        "uptime",
        "env",
        "printenv",
        "hostname",
        "which",
        "whereis",
        "type",
        # Text output
        "echo",
        "printf",
        # Network tools (read-only)
        "ping",
        "curl",
        "wget",
        "ssh",
        "scp",
        "rsync",
        # Archive tools
        "tar",
        "zip",
        "unzip",
        "gzip",
        "gunzip",
        # Shell utilities
        "sh",
        "bash",
        "zsh",
        "test",
        "true",
        "false",
        "sleep",
        "time",
        "timeout",
        "xargs",
        # File manipulation (careful - these can modify)
        "touch",
        "mkdir",
        "cp",
        "mv",
        "ln",
        # Text editors (non-interactive)
        "ed",
    }
)

# Blocked patterns - these are ALWAYS blocked regardless of mode
# Each tuple is (regex_pattern, human_readable_label)
BLOCKED_PATTERNS: List[Tuple[str, str]] = [
    # Command chaining/injection
    (r"[;&|]", "command chaining operators (; & |)"),
    (r"\$\(", "command substitution $()"),
    (r"`", "backtick command execution"),
    (r"\$\{[^}]*\}", "variable expansion with braces"),
    (r"\n|\r", "newline injection"),
    (r"\x00", "null byte injection"),
    # Dangerous file operations
    (r"rm\s+(-[^\s]*\s+)*-[^\s]*r[^\s]*\s+/(\s|$|\*)", "rm -rf /"),
    (r"rm\s+(-[^\s]*\s+)*/(\s|$|\*)", "rm /"),
    (r">\s*/dev/sd[a-z]", "write to block device"),
    (r">\s*/dev/null\s*[;&|]", "redirect to /dev/null with chaining"),
    (r"mkfs\.", "filesystem format"),
    (r":\(\)\s*\{", "fork bomb pattern"),
    (r"\|\s*:\s*&", "fork bomb variant"),
    (r"dd\s+.*if=/dev/(zero|random|urandom)", "dd from special device"),
    (r"dd\s+.*of=/dev/", "dd to device"),
    (r"chmod\s+(-[^\s]*\s+)*777\s+/(\s|$)", "chmod 777 /"),
    (r"chmod\s+(-[^\s]*\s+)*-R\s+777", "recursive chmod 777"),
    (r"chown\s+(-[^\s]*\s+)*-R\s+\S+\s+/(\s|$)", "recursive chown /"),
    # System modification
    (r"sudo\s", "sudo command"),
    (r"su\s+-", "su - command"),
    (r"passwd", "password change"),
    (r"useradd|userdel|usermod", "user management"),
    (r"groupadd|groupdel|groupmod", "group management"),
    # Sensitive file access
    (r"/etc/passwd", "access to /etc/passwd"),
    (r"/etc/shadow", "access to /etc/shadow"),
    (r"/etc/sudoers", "access to sudoers"),
    (r"~/.ssh/", "SSH directory access"),
    (r"/root/", "root directory access"),
    # Network attacks
    (r"nc\s+-[^\s]*l", "netcat listener"),
    (r"ncat\s+-[^\s]*l", "ncat listener"),
    (r"/dev/tcp/", "bash TCP redirect"),
    (r"/dev/udp/", "bash UDP redirect"),
    # Code execution
    (r"eval\s", "eval command"),
    (r"exec\s", "exec command"),
    (r"source\s", "source command"),
    (r"\.\s+/", "dot sourcing"),
    # Output redirection to sensitive locations
    (r">\s*/etc/", "redirect to /etc/"),
    (r">>\s*/etc/", "append to /etc/"),
    (r">\s*/var/", "redirect to /var/"),
    (r">\s*/usr/", "redirect to /usr/"),
    (r">\s*/boot/", "redirect to /boot/"),
    (r">\s*/sys/", "redirect to /sys/"),
    (r">\s*/proc/", "redirect to /proc/"),
    # History/credential exposure
    (r"history", "shell history"),
    (r"\.bash_history", "bash history file"),
    (r"\.zsh_history", "zsh history file"),
    # Cron/scheduled tasks
    (r"crontab\s+-[er]", "crontab edit/remove"),
    (r"/etc/cron", "cron directory"),
    # Init system
    (r"systemctl\s+(start|stop|restart|enable|disable|mask)", "systemd control"),
    (r"service\s+\S+\s+(start|stop|restart)", "service control"),
]

# Compiled patterns for efficiency
_COMPILED_PATTERNS: List[Tuple[re.Pattern, str]] = []


def _compile_patterns() -> List[Tuple[re.Pattern, str]]:
    """Compile regex patterns for efficient matching."""
    global _COMPILED_PATTERNS
    if not _COMPILED_PATTERNS:
        _COMPILED_PATTERNS = [
            (re.compile(pattern, re.IGNORECASE), label) for pattern, label in BLOCKED_PATTERNS
        ]
    return _COMPILED_PATTERNS


# =============================================================================
# Helper Functions
# =============================================================================


def _extract_base_command(command: str) -> str:
    """
    Extract the base command name from a full command string.

    Handles:
    - Simple commands: "ls -la" -> "ls"
    - Full paths: "/usr/bin/ls -la" -> "ls"
    - Environment prefix: handled as "env"

    Args:
        command: The full command string

    Returns:
        The base command name (without path or arguments)
    """
    if not command or not command.strip():
        return ""

    # Split on whitespace and get first part
    parts = command.strip().split()
    if not parts:
        return ""

    first_part = parts[0]

    # If it's a path, extract the basename
    if "/" in first_part:
        first_part = first_part.split("/")[-1]

    return first_part


def _bool(val: str) -> bool:
    """Convert string to boolean."""
    return val.lower() in ("true", "1", "yes", "on")


# =============================================================================
# SecurityConfig Class
# =============================================================================


@dataclass
class SecurityConfig:
    """
    Security configuration for bash command execution.

    Attributes:
        mode: "strict" or "permissive"
            - strict: Only commands in allowlist are permitted
            - permissive: All commands permitted except those matching blocked patterns
        allowed_commands: Set of allowed base command names
        audit_blocked_commands: Whether to log blocked command attempts
        max_command_length: Maximum allowed command string length
    """

    mode: str = "permissive"
    allowed_commands: Set[str] = field(default_factory=lambda: set(DEFAULT_ALLOWED_COMMANDS))
    audit_blocked_commands: bool = True
    max_command_length: int = MAX_COMMAND_LENGTH

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.mode not in ("strict", "permissive"):
            logger.warning(f"Invalid mode '{self.mode}', defaulting to 'permissive'")
            self.mode = "permissive"

    @classmethod
    def from_env(cls) -> "SecurityConfig":
        """
        Create SecurityConfig from environment variables.

        Environment variables:
            BASH_COMMAND_ALLOWLIST: Comma-separated additional commands
            BASH_COMMAND_ALLOWLIST_MODE: "strict" or "permissive"
            BASH_AUDIT_BLOCKED_COMMANDS: "true" or "false"
        """
        # Start with default allowed commands
        allowed = set(DEFAULT_ALLOWED_COMMANDS)

        # Add custom commands from environment
        custom_allowlist = os.getenv("BASH_COMMAND_ALLOWLIST", "")
        if custom_allowlist:
            for cmd in custom_allowlist.split(","):
                cmd = cmd.strip()
                if cmd:
                    allowed.add(cmd)

        # Get mode
        mode = os.getenv("BASH_COMMAND_ALLOWLIST_MODE", "permissive").lower()
        if mode not in ("strict", "permissive"):
            mode = "permissive"

        # Get audit setting
        audit = _bool(os.getenv("BASH_AUDIT_BLOCKED_COMMANDS", "true"))

        # Get max length
        try:
            max_length = int(os.getenv("BASH_MAX_COMMAND_LENGTH", str(MAX_COMMAND_LENGTH)))
        except ValueError:
            max_length = MAX_COMMAND_LENGTH

        return cls(
            mode=mode,
            allowed_commands=allowed,
            audit_blocked_commands=audit,
            max_command_length=max_length,
        )

    def validate(self, command: str) -> Tuple[bool, str]:
        """
        Validate a command against security rules.

        Args:
            command: The command string to validate

        Returns:
            Tuple of (is_allowed, reason)
            - is_allowed: True if command is allowed, False otherwise
            - reason: Empty string if allowed, explanation if blocked
        """
        return _validate_command_impl(
            command=command,
            mode=self.mode,
            allowed_commands=self.allowed_commands,
            audit=self.audit_blocked_commands,
            max_length=self.max_command_length,
        )


# =============================================================================
# Validation Implementation
# =============================================================================


def _validate_command_impl(
    command: str,
    mode: str,
    allowed_commands: Set[str],
    audit: bool,
    max_length: int,
) -> Tuple[bool, str]:
    """
    Internal implementation of command validation.

    Args:
        command: Command to validate
        mode: "strict" or "permissive"
        allowed_commands: Set of allowed base commands
        audit: Whether to log blocked commands
        max_length: Maximum command length

    Returns:
        Tuple of (is_allowed, reason)
    """
    # Check for empty command
    if not command or not command.strip():
        reason = "Command is empty"
        if audit:
            logger.warning(f"Blocked command: {reason}")
        return False, reason

    command = command.strip()

    # Check command length
    if len(command) > max_length:
        reason = f"Command too long ({len(command)} > {max_length})"
        if audit:
            logger.warning(f"Blocked command: {reason}")
        return False, reason

    # Check against dangerous patterns (ALWAYS checked, regardless of mode)
    compiled_patterns = _compile_patterns()
    for pattern, label in compiled_patterns:
        if pattern.search(command):
            reason = f"Blocked: dangerous pattern detected ({label})"
            if audit:
                logger.warning(f"Blocked command attempt: {label} - command: {command[:100]}...")
            return False, reason

    # In strict mode, check allowlist
    if mode == "strict":
        base_cmd = _extract_base_command(command)
        if base_cmd not in allowed_commands:
            reason = f"Command '{base_cmd}' not in allowlist (strict mode)"
            if audit:
                logger.warning(f"Blocked command: {reason}")
            return False, reason

    # Command is allowed
    return True, ""


# =============================================================================
# Module-level convenience function
# =============================================================================

# Singleton config instance (lazy loaded)
_config_instance: SecurityConfig = None


def _get_config() -> SecurityConfig:
    """Get or create the singleton SecurityConfig instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = SecurityConfig.from_env()
    return _config_instance


def validate_command(command: str) -> Tuple[bool, str]:
    """
    Validate a command against security rules.

    This is a convenience function that uses the global SecurityConfig.
    For custom configuration, use SecurityConfig directly.

    Args:
        command: The command string to validate

    Returns:
        Tuple of (is_allowed, reason)
        - is_allowed: True if command is allowed, False otherwise
        - reason: Empty string if allowed, explanation if blocked

    Example:
        >>> is_allowed, reason = validate_command("ls -la")
        >>> if not is_allowed:
        ...     print(f"Blocked: {reason}")
    """
    # Always reload config to pick up environment changes during tests
    config = SecurityConfig.from_env()
    return config.validate(command)


def reset_config() -> None:
    """Reset the cached config instance. Useful for testing."""
    global _config_instance
    _config_instance = None


# Export the allowed commands set for external access
ALLOWED_COMMANDS: FrozenSet[str] = DEFAULT_ALLOWED_COMMANDS
