# Terminal Service Documentation

## Overview

The Terminal Service provides secure terminal command execution capabilities for macOS/Linux systems through MCP (Model Context Protocol) integration. It allows controlled execution of shell commands with comprehensive security validation, session management, and audit logging.

## Features

### 🔐 Security-First Design
- **Command Validation**: Whitelist-based command filtering
- **Path Protection**: Prevents access to sensitive system directories
- **Injection Prevention**: Blocks command injection and dangerous patterns
- **Confirmation Requirements**: Prompts for destructive operations
- **Resource Limits**: Timeouts and resource constraints

### 🗂️ Session Management
- **Persistent Sessions**: Maintain command history and working directories
- **Session Isolation**: Multiple independent terminal sessions
- **State Tracking**: Directory, environment variables, and command history

### 📊 Comprehensive Logging
- **Command History**: Full audit trail of executed commands
- **Performance Metrics**: Execution times and success rates
- **Billing Integration**: Cost tracking for ISA model usage

## Architecture

```
terminal_service/
├── models/                 # Data structures
│   └── terminal_models.py  # CommandResult, TerminalSession, etc.
├── services/               # Core business logic
│   ├── terminal_service.py      # Main service implementation
│   └── security_validator.py    # Security validation
├── tools/                  # MCP tool registration
│   └── terminal_tools.py   # MCP tool definitions
├── tests/                  # Test suite
│   ├── test_security_validator.py
│   ├── test_terminal_service.py
│   └── test_terminal_tools.py
└── docs/
    └── terminal_service.md # This documentation
```

## Available Tools

### Command Execution

#### `execute_command`
Execute a terminal command with security validation.

**Parameters:**
- `command` (string): The command to execute
- `session_id` (optional string): Session identifier for command isolation
- `timeout` (optional int): Command timeout in seconds (default: 30)
- `require_confirmation` (optional bool): Bypass confirmation for dangerous commands

**Example:**
```json
{
  "command": "ls -la /Users/username/Documents",
  "session_id": "main_session",
  "timeout": 10
}
```

#### `list_files`
List files and directories with formatting options.

**Parameters:**
- `directory` (optional string): Target directory (current if None)
- `show_hidden` (optional bool): Show hidden files
- `long_format` (optional bool): Use detailed format
- `session_id` (optional string): Session identifier

#### `change_directory`
Change the current working directory for a session.

**Parameters:**
- `directory` (string): Target directory path
- `session_id` (optional string): Session identifier

### System Information

#### `get_system_info`
Retrieve comprehensive system information.

**Returns:**
- Hostname, username, platform, architecture
- Kernel version, current directory

#### `get_current_directory`
Get the current working directory for a session.

### Session Management

#### `create_session`
Create a new terminal session.

**Parameters:**
- `session_id` (string): Unique session identifier

#### `list_sessions`
List all active terminal sessions with details.

#### `delete_session`
Delete a terminal session (except default).

**Parameters:**
- `session_id` (string): Session to delete

#### `get_command_history`
Retrieve command execution history.

**Parameters:**
- `session_id` (optional string): Target session
- `limit` (optional int): Maximum commands to return

## Security Model

### Command Classification

#### ✅ **Allowed Commands (LOW Risk)**
- File operations: `ls`, `pwd`, `cat`, `head`, `tail`, `grep`, `find`
- System info: `whoami`, `uname`, `hostname`, `ps`, `top`, `df`
- Development tools: `git`, `npm`, `pip`, `python`, `node`
- macOS specific: `open`, `say`, `pbcopy`, `pbpaste`

#### ⚠️ **Confirmation Required (MEDIUM Risk)**
- File modifications: `rm`, `mv`, `cp -r`, `chmod`, `chown`
- Repository operations: `git push`, `git reset --hard`
- Package installations: `npm install -g`, `pip install`
- Container operations: `docker run`, `docker-compose up`

#### 🚫 **Forbidden Commands (HIGH Risk)**
- System administration: `sudo`, `su`, `passwd`, `usermod`
- Destructive operations: `rm -rf /`, `dd`, `mkfs`, `shutdown`
- Permission changes: `chmod 777`, `chown -R`
- Process killing: `killall`, `pkill -9`

### Directory Access Control

#### ✅ **Allowed Directories**
- User home directory: `/Users/*`
- Temporary directories: `/tmp`, `/var/tmp`
- Application directories: `/Applications`, `/opt/homebrew`

#### 🚫 **Forbidden Directories**
- System configuration: `/etc`, `/private/etc`
- Root directory: `/var/root`
- System libraries: `/System/Library`
- Launch services: `/Library/LaunchDaemons`

### Protection Mechanisms

1. **Input Validation**: Command syntax and parameter validation
2. **Pattern Matching**: Detection of dangerous command patterns
3. **Path Traversal Prevention**: Blocks `../` and similar attempts
4. **Command Injection Protection**: Prevents chaining and substitution
5. **Resource Limits**: Execution timeouts and memory constraints

## Usage Examples

### Basic Command Execution

```python
# Execute a simple command
result = await terminal_tools.execute_command("ls -la")

# Execute in specific session
result = await terminal_tools.execute_command(
    "pwd", 
    session_id="development"
)

# Execute with custom timeout
result = await terminal_tools.execute_command(
    "find /Users -name '*.txt'", 
    timeout=60
)
```

### Session Management

```python
# Create a new session for project work
await terminal_tools.create_session("project_alpha")

# Change directory in that session
await terminal_tools.change_directory(
    "/Users/username/projects/alpha",
    session_id="project_alpha"
)

# Execute commands in the session
await terminal_tools.execute_command(
    "git status",
    session_id="project_alpha"
)

# View session history
history = await terminal_tools.get_command_history(
    session_id="project_alpha",
    limit=10
)
```

### File Operations

```python
# List files with details
result = await terminal_tools.list_files(
    directory="/Users/username/Documents",
    show_hidden=True,
    long_format=True
)

# Navigate directories safely
await terminal_tools.change_directory("../projects")
current_dir = await terminal_tools.get_current_directory()
```

## Response Format

All tools return JSON responses with this structure:

```json
{
  "status": "success|error",
  "action": "tool_name",
  "data": {
    // Tool-specific response data
  },
  "billing_info": {
    "total_cost": 0.0,
    "operations": []
  },
  "error_message": "Error details if status is error"
}
```

### Command Execution Response

```json
{
  "status": "success",
  "action": "execute_command",
  "data": {
    "command": "ls -la",
    "success": true,
    "return_code": 0,
    "execution_time": 0.045,
    "current_directory": "/Users/username",
    "timestamp": "2025-07-21T10:30:45.123456",
    "stdout": "total 16\ndrwxr-xr-x  4 username staff  128 Jul 21 10:30 .\n...",
    "stderr": ""
  },
  "billing_info": {
    "total_cost": 0.0,
    "operations": []
  }
}
```

## Configuration

### Environment Variables

- `TERMINAL_MAX_TIMEOUT`: Maximum command timeout (default: 300 seconds)
- `TERMINAL_MAX_SESSIONS`: Maximum concurrent sessions (default: 50)
- `TERMINAL_LOG_LEVEL`: Logging verbosity level

### Security Policy Customization

The security validator can be customized by modifying:

```python
from terminal_service.services.security_validator import SecurityValidator

validator = SecurityValidator()
# Add custom allowed commands
validator.policy.allowed_commands.extend(['custom_tool', 'special_cmd'])
# Add restricted directories
validator.policy.forbidden_directories.append('/custom/restricted')
```

## Error Handling

### Common Error Types

1. **Security Validation Errors**
   - Forbidden commands
   - Dangerous patterns detected
   - Unauthorized directory access

2. **Execution Errors**
   - Command not found
   - Permission denied
   - Timeout exceeded

3. **Session Errors**
   - Session not found
   - Cannot delete default session

### Error Response Example

```json
{
  "status": "error",
  "action": "execute_command",
  "data": {
    "command": "sudo rm -rf /"
  },
  "error_message": "Security validation failed: Command 'sudo' is forbidden for security reasons",
  "billing_info": {
    "total_cost": 0.0,
    "operations": []
  }
}
```

## Performance Considerations

### Optimization Strategies

1. **Session Reuse**: Maintain persistent sessions to avoid repeated initialization
2. **Command Batching**: Group related operations in single sessions
3. **Timeout Tuning**: Adjust timeouts based on expected command duration
4. **History Limits**: Configure appropriate command history retention

### Resource Limits

- **Memory**: Commands are executed in isolated processes
- **CPU**: System-level process controls apply
- **Network**: Network commands respect system firewall rules
- **Disk**: Write operations are limited to allowed directories

## Testing

### Running Tests

```bash
# Run all tests
python -m pytest tools/services/terminal_service/tests/

# Run specific test file
python -m pytest tools/services/terminal_service/tests/test_security_validator.py

# Run with coverage
python -m pytest --cov=terminal_service tools/services/terminal_service/tests/
```

### Test Coverage

- Security validator: Command validation, pattern detection, directory access
- Terminal service: Command execution, session management, error handling
- MCP tools: Response formatting, parameter validation, integration testing

## Troubleshooting

### Common Issues

#### Permission Denied Errors
- **Cause**: Attempting to access restricted directories or execute forbidden commands
- **Solution**: Use allowed commands and directories, or adjust security policy

#### Command Timeout
- **Cause**: Long-running commands exceeding timeout limits
- **Solution**: Increase timeout parameter or optimize command

#### Session Not Found
- **Cause**: Using invalid or deleted session ID
- **Solution**: Create session or use default session

#### Path Not Found
- **Cause**: Incorrect directory paths or navigation
- **Solution**: Use absolute paths or verify directory existence

### Debugging

Enable detailed logging:

```python
import logging
logging.getLogger('terminal_service').setLevel(logging.DEBUG)
```

Check command history for troubleshooting:

```python
history = await terminal_tools.get_command_history(limit=50)
# Review failed commands and error patterns
```

## Integration Guide

### MCP Server Registration

```python
from tools.services.terminal_service.tools.terminal_tools import register_terminal_tools

# Register with MCP server
register_terminal_tools(mcp_server)
```

### Custom Tool Development

Extend the terminal service with custom tools:

```python
from tools.services.terminal_service.tools.terminal_tools import TerminalTools

class CustomTerminalTools(TerminalTools):
    async def custom_operation(self, param: str) -> str:
        # Custom logic here
        return await self.execute_command(f"custom_cmd {param}")
```

## Security Best Practices

1. **Principle of Least Privilege**: Only allow necessary commands
2. **Input Validation**: Always validate command parameters
3. **Audit Logging**: Monitor all command executions
4. **Regular Updates**: Keep security policies current
5. **Session Cleanup**: Regularly clean up unused sessions
6. **Resource Monitoring**: Monitor system resource usage
7. **Error Handling**: Implement comprehensive error handling

## Limitations

1. **Platform Support**: Optimized for macOS, basic Linux support
2. **Interactive Commands**: No support for interactive/TUI applications
3. **Real-time Output**: Commands must complete before output is returned
4. **File Transfer**: No built-in file upload/download capabilities
5. **Root Access**: No sudo or root command execution

## Future Enhancements

- **Interactive Shell Support**: Support for interactive applications
- **Real-time Streaming**: Live command output streaming
- **File Transfer**: Secure file upload/download capabilities
- **Container Integration**: Enhanced Docker/container support
- **Advanced Analytics**: Command usage analytics and optimization
- **Multi-platform**: Enhanced Linux and Windows support