"""
Bash Tools - Command execution with persistent shell sessions.

Provides:
- bash_execute: Execute shell commands with timeout and background support
- bash_output: Retrieve output from background shell sessions
- kill_shell: Terminate running background shells

Keywords: bash, shell, command, execute, terminal, run, script
"""

import os
import asyncio
import uuid
import signal
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Maximum command output size (1MB)
MAX_OUTPUT_SIZE = 1024 * 1024
# Default timeout (2 minutes)
DEFAULT_TIMEOUT = 120
# Maximum timeout (10 minutes)
MAX_TIMEOUT = 600

# Store for background shells
_background_shells: Dict[str, "BackgroundShell"] = {}


@dataclass
class BackgroundShell:
    """Represents a background shell process."""

    shell_id: str
    process: asyncio.subprocess.Process
    command: str
    started_at: datetime
    output_buffer: List[str] = field(default_factory=list)
    error_buffer: List[str] = field(default_factory=list)
    completed: bool = False
    exit_code: Optional[int] = None
    task: Optional[asyncio.Task] = None


def register_bash_tools(mcp: FastMCP):
    """Register bash execution tools with the MCP server."""

    @mcp.tool()
    async def bash_execute(
        command: str,
        timeout: int = DEFAULT_TIMEOUT,
        working_directory: Optional[str] = None,
        run_in_background: bool = False,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a bash command in a shell session.

        Executes commands with proper timeout handling and security measures.
        Can run commands in the background for long-running operations.

        Args:
            command: The bash command to execute.
            timeout: Timeout in seconds (max 600). Default: 120.
            working_directory: Directory to run the command in. Defaults to current directory.
            run_in_background: Run command in background, returning immediately. Default: False.
            env: Additional environment variables to set.

        Returns:
            For foreground commands:
            {
                "status": "success",
                "command": "ls -la",
                "stdout": "...",
                "stderr": "...",
                "exit_code": 0,
                "duration_ms": 150
            }

            For background commands:
            {
                "status": "success",
                "shell_id": "abc-123",
                "command": "npm install",
                "message": "Command running in background. Use bash_output to check status."
            }

        Security:
            - Commands are executed in a subprocess, not directly in the system shell
            - Dangerous commands (rm -rf /, sudo, etc.) should be blocked by policy
            - Output is limited to prevent memory issues

        Keywords: bash, shell, command, execute, run, terminal, script, cli
        """
        try:
            # Validate timeout
            timeout = min(timeout, MAX_TIMEOUT)

            # Security checks for dangerous patterns (regex-based to resist encoding bypasses)
            import re as _re
            dangerous_patterns = [
                (r"rm\s+(-[^\s]*\s+)*-[^\s]*r[^\s]*\s+/(\s|$|\*)", "rm -rf /"),
                (r">\s*/dev/sd[a-z]", "> /dev/sda"),
                (r"mkfs\.", "mkfs"),
                (r":\(\)\s*\{.*\|.*&\s*\}\s*;", "fork bomb"),
                (r"dd\s+.*if=/dev/zero", "dd if=/dev/zero"),
                (r"chmod\s+(-[^\s]*\s+)*777\s+/(\s|$)", "chmod 777 /"),
            ]

            for pattern, label in dangerous_patterns:
                if _re.search(pattern, command):
                    return {
                        "status": "error",
                        "action": "bash_execute",
                        "error": f"Potentially dangerous command blocked: {label}",
                        "error_code": "DANGEROUS_COMMAND",
                        "timestamp": datetime.now().isoformat(),
                    }

            # Set working directory
            cwd = working_directory if working_directory else os.getcwd()
            if not Path(cwd).exists():
                return {
                    "status": "error",
                    "action": "bash_execute",
                    "error": f"Working directory not found: {cwd}",
                    "error_code": "DIRECTORY_NOT_FOUND",
                    "timestamp": datetime.now().isoformat(),
                }

            # Prepare environment
            process_env = os.environ.copy()
            if env:
                process_env.update(env)

            # SECURITY NOTE: This tool executes shell commands WITH shell interpretation.
            # Shell features (pipes, redirects, variables) are intentional functionality.
            # Security relies on:
            #   1. Pattern-based blocking of dangerous commands (above)
            #   2. HIGH security level requiring explicit authorization (core/security.py)
            #   3. Audit logging of all commands
            # This is NOT safe for untrusted input - authorization required.
            start_time = datetime.now()
            process = await asyncio.create_subprocess_exec(
                "/bin/sh", "-c", command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=process_env,
            )

            if run_in_background:
                # Background execution
                shell_id = str(uuid.uuid4())[:8]
                shell = BackgroundShell(
                    shell_id=shell_id, process=process, command=command, started_at=start_time
                )

                # Start background task to collect output
                async def collect_output():
                    try:
                        stdout, stderr = await process.communicate()
                        shell.output_buffer.append(stdout.decode("utf-8", errors="replace"))
                        shell.error_buffer.append(stderr.decode("utf-8", errors="replace"))
                        shell.exit_code = process.returncode
                        shell.completed = True
                    except Exception as e:
                        shell.error_buffer.append(str(e))
                        shell.completed = True

                shell.task = asyncio.create_task(collect_output())
                _background_shells[shell_id] = shell

                logger.info(f"bash_execute: Started background shell {shell_id}: {command[:50]}...")

                return {
                    "status": "success",
                    "action": "bash_execute",
                    "data": {
                        "shell_id": shell_id,
                        "command": command,
                        "working_directory": cwd,
                        "message": "Command running in background. Use bash_output to check status.",
                    },
                    "timestamp": datetime.now().isoformat(),
                }

            # Foreground execution with timeout
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                # Kill the process on timeout
                try:
                    process.kill()
                    await process.wait()
                except ProcessLookupError:
                    pass

                return {
                    "status": "error",
                    "action": "bash_execute",
                    "error": f"Command timed out after {timeout} seconds",
                    "error_code": "TIMEOUT",
                    "data": {"command": command, "timeout": timeout},
                    "timestamp": datetime.now().isoformat(),
                }

            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Decode output
            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")

            # Truncate if too large
            truncated = False
            if len(stdout_text) > MAX_OUTPUT_SIZE:
                stdout_text = stdout_text[:MAX_OUTPUT_SIZE] + "\n... [output truncated]"
                truncated = True
            if len(stderr_text) > MAX_OUTPUT_SIZE:
                stderr_text = stderr_text[:MAX_OUTPUT_SIZE] + "\n... [output truncated]"
                truncated = True

            exit_code = process.returncode
            status = "success" if exit_code == 0 else "error"

            logger.info(
                f"bash_execute: '{command[:50]}...' exit_code={exit_code} duration={duration_ms}ms"
            )

            result = {
                "status": status,
                "action": "bash_execute",
                "data": {
                    "command": command,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "exit_code": exit_code,
                    "duration_ms": duration_ms,
                    "working_directory": cwd,
                    "truncated": truncated,
                },
                "timestamp": datetime.now().isoformat(),
            }

            if exit_code != 0:
                result["error"] = f"Command exited with code {exit_code}"
                result["error_code"] = "NON_ZERO_EXIT"

            return result

        except Exception as e:
            logger.error(f"bash_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "bash_execute",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    @mcp.tool()
    async def bash_output(shell_id: str, wait: bool = False, timeout: int = 30) -> Dict[str, Any]:
        """
        Retrieve output from a background shell session.

        Gets the current output from a command started with run_in_background=True.

        Args:
            shell_id: The shell ID returned from bash_execute with run_in_background=True.
            wait: If True, wait for the command to complete. Default: False.
            timeout: Maximum time to wait if wait=True. Default: 30 seconds.

        Returns:
            {
                "status": "success",
                "shell_id": "abc-123",
                "command": "npm install",
                "completed": true,
                "exit_code": 0,
                "stdout": "...",
                "stderr": "...",
                "running_time_ms": 5000
            }

        Keywords: bash, output, background, shell, status, result
        """
        try:
            if shell_id not in _background_shells:
                return {
                    "status": "error",
                    "action": "bash_output",
                    "error": f"Shell not found: {shell_id}",
                    "error_code": "SHELL_NOT_FOUND",
                    "data": {"active_shells": list(_background_shells.keys())},
                    "timestamp": datetime.now().isoformat(),
                }

            shell = _background_shells[shell_id]

            # Wait for completion if requested
            if wait and not shell.completed and shell.task:
                try:
                    await asyncio.wait_for(shell.task, timeout=timeout)
                except asyncio.TimeoutError:
                    pass

            # Calculate running time
            running_time_ms = int((datetime.now() - shell.started_at).total_seconds() * 1000)

            result = {
                "status": "success",
                "action": "bash_output",
                "data": {
                    "shell_id": shell_id,
                    "command": shell.command,
                    "completed": shell.completed,
                    "exit_code": shell.exit_code,
                    "stdout": "".join(shell.output_buffer),
                    "stderr": "".join(shell.error_buffer),
                    "running_time_ms": running_time_ms,
                },
                "timestamp": datetime.now().isoformat(),
            }

            # Clean up completed shells
            if shell.completed:
                # Keep for a while but could clean up old ones
                pass

            logger.info(f"bash_output: shell={shell_id} completed={shell.completed}")

            return result

        except Exception as e:
            logger.error(f"bash_output failed: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "bash_output",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    @mcp.tool()
    async def kill_shell(shell_id: str) -> Dict[str, Any]:
        """
        Terminate a running background shell.

        Kills a background command that was started with run_in_background=True.

        Args:
            shell_id: The shell ID to terminate.

        Returns:
            {
                "status": "success",
                "shell_id": "abc-123",
                "message": "Shell terminated"
            }

        Keywords: kill, terminate, stop, shell, background, cancel
        """
        try:
            if shell_id not in _background_shells:
                return {
                    "status": "error",
                    "action": "kill_shell",
                    "error": f"Shell not found: {shell_id}",
                    "error_code": "SHELL_NOT_FOUND",
                    "data": {"active_shells": list(_background_shells.keys())},
                    "timestamp": datetime.now().isoformat(),
                }

            shell = _background_shells[shell_id]

            if shell.completed:
                return {
                    "status": "success",
                    "action": "kill_shell",
                    "data": {
                        "shell_id": shell_id,
                        "message": "Shell already completed",
                        "exit_code": shell.exit_code,
                    },
                    "timestamp": datetime.now().isoformat(),
                }

            # Kill the process
            try:
                shell.process.terminate()
                await asyncio.sleep(0.5)

                if shell.process.returncode is None:
                    shell.process.kill()
                    await shell.process.wait()

            except ProcessLookupError:
                pass  # Already dead

            shell.completed = True
            shell.exit_code = -signal.SIGTERM

            # Cancel the task
            if shell.task and not shell.task.done():
                shell.task.cancel()

            logger.info(f"kill_shell: Terminated shell {shell_id}")

            return {
                "status": "success",
                "action": "kill_shell",
                "data": {
                    "shell_id": shell_id,
                    "command": shell.command,
                    "message": "Shell terminated",
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"kill_shell failed: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "kill_shell",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    @mcp.tool()
    async def list_shells() -> Dict[str, Any]:
        """
        List all active background shells.

        Returns information about all background shell sessions.

        Returns:
            {
                "status": "success",
                "shells": [
                    {
                        "shell_id": "abc-123",
                        "command": "npm install",
                        "completed": false,
                        "running_time_ms": 5000
                    }
                ],
                "total": 2
            }

        Keywords: list, shells, background, active, running
        """
        try:
            shells = []
            for shell_id, shell in _background_shells.items():
                running_time_ms = int((datetime.now() - shell.started_at).total_seconds() * 1000)
                shells.append(
                    {
                        "shell_id": shell_id,
                        "command": shell.command[:100]
                        + ("..." if len(shell.command) > 100 else ""),
                        "completed": shell.completed,
                        "exit_code": shell.exit_code,
                        "running_time_ms": running_time_ms,
                        "started_at": shell.started_at.isoformat(),
                    }
                )

            return {
                "status": "success",
                "action": "list_shells",
                "data": {"shells": shells, "total": len(shells)},
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"list_shells failed: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "list_shells",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    logger.debug("Registered bash tools: bash_execute, bash_output, kill_shell, list_shells")
