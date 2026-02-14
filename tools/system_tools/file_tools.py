"""
File Tools - Core file operations for reading, writing, and editing files.

Provides:
- read_file: Read file contents with line offset/limit support
- write_file: Create or overwrite files
- edit_file: Exact string replacement in files
- multi_edit_file: Multiple edits in one atomic operation

Keywords: file, read, write, edit, content, text, code, modify
"""

import os
import base64
import mimetypes
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Maximum file size to read (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024
# Maximum lines to read by default
DEFAULT_MAX_LINES = 2000
# Maximum line length before truncation
MAX_LINE_LENGTH = 2000


def register_file_tools(mcp: FastMCP):
    """Register file operation tools with the MCP server."""

    @mcp.tool()
    async def read_file(
        file_path: str,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        encoding: str = "utf-8",
    ) -> Dict[str, Any]:
        """
        Read a file from the local filesystem.

        Reads file contents with support for:
        - Text files (code, configs, logs, etc.)
        - Binary files (returned as base64)
        - Images (PNG, JPG, etc. - returned as base64 with mime type)
        - PDFs (returned as base64)
        - Line offset and limit for large files

        Args:
            file_path: Absolute path to the file to read.
            offset: Line number to start reading from (1-indexed). Optional.
            limit: Maximum number of lines to read. Defaults to 2000.
            encoding: Text encoding to use. Defaults to 'utf-8'.

        Returns:
            {
                "status": "success",
                "file_path": "/path/to/file",
                "content": "file contents or base64 data",
                "content_type": "text" | "image" | "binary",
                "mime_type": "text/plain" | "image/png" | etc.,
                "total_lines": 100,
                "lines_read": 50,
                "offset": 1,
                "truncated": false,
                "encoding": "utf-8"
            }

        Keywords: read, file, content, text, code, view, open, cat
        """
        try:
            path = Path(file_path)

            # Validate file exists
            if not path.exists():
                return {
                    "status": "error",
                    "action": "read_file",
                    "error": f"File not found: {file_path}",
                    "error_code": "FILE_NOT_FOUND",
                    "timestamp": datetime.now().isoformat(),
                }

            # Validate it's a file, not a directory
            if path.is_dir():
                return {
                    "status": "error",
                    "action": "read_file",
                    "error": f"Path is a directory, not a file: {file_path}. Use ls_directory instead.",
                    "error_code": "IS_DIRECTORY",
                    "timestamp": datetime.now().isoformat(),
                }

            # Check file size
            file_size = path.stat().st_size
            if file_size > MAX_FILE_SIZE:
                return {
                    "status": "error",
                    "action": "read_file",
                    "error": f"File too large ({file_size} bytes). Maximum: {MAX_FILE_SIZE} bytes.",
                    "error_code": "FILE_TOO_LARGE",
                    "timestamp": datetime.now().isoformat(),
                }

            # Determine file type
            mime_type, _ = mimetypes.guess_type(str(path))
            mime_type = mime_type or "application/octet-stream"

            # Handle binary/image files
            if (
                mime_type.startswith("image/")
                or mime_type in ["application/pdf", "application/octet-stream"]
                or not _is_text_file(path)
            ):
                with open(path, "rb") as f:
                    content = base64.b64encode(f.read()).decode("ascii")

                content_type = "image" if mime_type.startswith("image/") else "binary"

                return {
                    "status": "success",
                    "action": "read_file",
                    "data": {
                        "file_path": str(path.absolute()),
                        "content": content,
                        "content_type": content_type,
                        "mime_type": mime_type,
                        "file_size": file_size,
                        "encoding": "base64",
                    },
                    "timestamp": datetime.now().isoformat(),
                }

            # Handle text files
            with open(path, "r", encoding=encoding, errors="replace") as f:
                all_lines = f.readlines()

            total_lines = len(all_lines)

            # Apply offset and limit
            start_line = (offset - 1) if offset and offset > 0 else 0
            max_lines = limit if limit else DEFAULT_MAX_LINES
            end_line = min(start_line + max_lines, total_lines)

            selected_lines = all_lines[start_line:end_line]

            # Format with line numbers (like cat -n)
            formatted_lines = []
            for i, line in enumerate(selected_lines, start=start_line + 1):
                # Truncate long lines
                if len(line) > MAX_LINE_LENGTH:
                    line = line[:MAX_LINE_LENGTH] + "... [truncated]\n"
                # Format: "    5\t<content>"
                formatted_lines.append(f"{i:6}\t{line.rstrip()}")

            content = "\n".join(formatted_lines)
            truncated = end_line < total_lines or start_line > 0

            logger.info(f"read_file: {file_path} ({end_line - start_line} lines)")

            return {
                "status": "success",
                "action": "read_file",
                "data": {
                    "file_path": str(path.absolute()),
                    "content": content,
                    "content_type": "text",
                    "mime_type": mime_type,
                    "total_lines": total_lines,
                    "lines_read": end_line - start_line,
                    "offset": start_line + 1,
                    "truncated": truncated,
                    "encoding": encoding,
                },
                "timestamp": datetime.now().isoformat(),
            }

        except PermissionError:
            return {
                "status": "error",
                "action": "read_file",
                "error": f"Permission denied: {file_path}",
                "error_code": "PERMISSION_DENIED",
                "timestamp": datetime.now().isoformat(),
            }
        except UnicodeDecodeError as e:
            return {
                "status": "error",
                "action": "read_file",
                "error": f"Encoding error: {e}. Try specifying a different encoding.",
                "error_code": "ENCODING_ERROR",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"read_file failed: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "read_file",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    @mcp.tool()
    async def write_file(
        file_path: str, content: str, create_directories: bool = True, encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """
        Write content to a file on the local filesystem.

        Creates a new file or overwrites an existing one. Use edit_file
        for making targeted changes to existing files.

        Args:
            file_path: Absolute path to the file to write.
            content: The content to write to the file.
            create_directories: Create parent directories if they don't exist. Default: True.
            encoding: Text encoding to use. Defaults to 'utf-8'.

        Returns:
            {
                "status": "success",
                "file_path": "/path/to/file",
                "bytes_written": 1234,
                "lines_written": 50,
                "created": true | false (whether file was newly created)
            }

        Keywords: write, file, create, save, output, new
        """
        try:
            path = Path(file_path)

            # Security check: prevent writing to sensitive locations
            # Resolve symlinks to prevent traversal bypasses
            resolved = path.resolve()
            sensitive_paths = ["/etc", "/usr", "/bin", "/sbin", "/var", "/root"]
            for sensitive in sensitive_paths:
                if str(resolved) == sensitive or str(resolved).startswith(sensitive + "/"):
                    return {
                        "status": "error",
                        "action": "write_file",
                        "error": f"Cannot write to sensitive system path: {sensitive}",
                        "error_code": "SENSITIVE_PATH",
                        "timestamp": datetime.now().isoformat(),
                    }

            # Check if file exists (for created flag)
            file_existed = path.exists()

            # Create parent directories if needed
            if create_directories:
                path.parent.mkdir(parents=True, exist_ok=True)
            elif not path.parent.exists():
                return {
                    "status": "error",
                    "action": "write_file",
                    "error": f"Parent directory does not exist: {path.parent}",
                    "error_code": "DIRECTORY_NOT_FOUND",
                    "timestamp": datetime.now().isoformat(),
                }

            # Write the file
            with open(path, "w", encoding=encoding) as f:
                f.write(content)

            bytes_written = path.stat().st_size
            lines_written = content.count("\n") + (
                1 if content and not content.endswith("\n") else 0
            )

            logger.info(f"write_file: {file_path} ({bytes_written} bytes)")

            return {
                "status": "success",
                "action": "write_file",
                "data": {
                    "file_path": str(path.absolute()),
                    "bytes_written": bytes_written,
                    "lines_written": lines_written,
                    "created": not file_existed,
                },
                "timestamp": datetime.now().isoformat(),
            }

        except PermissionError:
            return {
                "status": "error",
                "action": "write_file",
                "error": f"Permission denied: {file_path}",
                "error_code": "PERMISSION_DENIED",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"write_file failed: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "write_file",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    @mcp.tool()
    async def edit_file(
        file_path: str, old_string: str, new_string: str, replace_all: bool = False
    ) -> Dict[str, Any]:
        """
        Perform exact string replacement in a file.

        Makes targeted edits to existing files by replacing specific text.
        The old_string must match exactly (including whitespace/indentation).

        Args:
            file_path: Absolute path to the file to edit.
            old_string: The exact text to find and replace.
            new_string: The text to replace it with (must be different from old_string).
            replace_all: If True, replace all occurrences. If False, replace only first. Default: False.

        Returns:
            {
                "status": "success",
                "file_path": "/path/to/file",
                "replacements": 1,
                "old_string_preview": "first 100 chars...",
                "new_string_preview": "first 100 chars..."
            }

        Keywords: edit, modify, replace, change, update, fix, refactor
        """
        try:
            path = Path(file_path)

            # Validate file exists
            if not path.exists():
                return {
                    "status": "error",
                    "action": "edit_file",
                    "error": f"File not found: {file_path}",
                    "error_code": "FILE_NOT_FOUND",
                    "timestamp": datetime.now().isoformat(),
                }

            # Validate old_string != new_string
            if old_string == new_string:
                return {
                    "status": "error",
                    "action": "edit_file",
                    "error": "old_string and new_string must be different",
                    "error_code": "SAME_STRING",
                    "timestamp": datetime.now().isoformat(),
                }

            # Read current content
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check if old_string exists
            if old_string not in content:
                return {
                    "status": "error",
                    "action": "edit_file",
                    "error": "old_string not found in file. Ensure exact match including whitespace.",
                    "error_code": "STRING_NOT_FOUND",
                    "data": {
                        "file_path": str(path.absolute()),
                        "old_string_preview": old_string[:200]
                        + ("..." if len(old_string) > 200 else ""),
                    },
                    "timestamp": datetime.now().isoformat(),
                }

            # Check for uniqueness if not replace_all
            if not replace_all:
                occurrences = content.count(old_string)
                if occurrences > 1:
                    return {
                        "status": "error",
                        "action": "edit_file",
                        "error": f"old_string found {occurrences} times. Use replace_all=True or provide more context for unique match.",
                        "error_code": "MULTIPLE_MATCHES",
                        "data": {"occurrences": occurrences},
                        "timestamp": datetime.now().isoformat(),
                    }

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_string, new_string)
                replacements = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                replacements = 1

            # Write back
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

            logger.info(f"edit_file: {file_path} ({replacements} replacements)")

            return {
                "status": "success",
                "action": "edit_file",
                "data": {
                    "file_path": str(path.absolute()),
                    "replacements": replacements,
                    "old_string_preview": old_string[:100]
                    + ("..." if len(old_string) > 100 else ""),
                    "new_string_preview": new_string[:100]
                    + ("..." if len(new_string) > 100 else ""),
                },
                "timestamp": datetime.now().isoformat(),
            }

        except PermissionError:
            return {
                "status": "error",
                "action": "edit_file",
                "error": f"Permission denied: {file_path}",
                "error_code": "PERMISSION_DENIED",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"edit_file failed: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "edit_file",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    @mcp.tool()
    async def multi_edit_file(file_path: str, edits: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Make multiple edits to a single file in one atomic operation.

        All edits are validated before any changes are made. If any edit
        fails validation, no changes are applied.

        Args:
            file_path: Absolute path to the file to edit.
            edits: List of edit operations, each with:
                - old_string: The exact text to find
                - new_string: The replacement text

        Returns:
            {
                "status": "success",
                "file_path": "/path/to/file",
                "total_edits": 3,
                "successful_edits": 3
            }

        Example:
            edits = [
                {"old_string": "def foo():", "new_string": "def bar():"},
                {"old_string": "return None", "new_string": "return result"}
            ]

        Keywords: multi, edit, batch, replace, refactor, multiple
        """
        try:
            path = Path(file_path)

            # Validate file exists
            if not path.exists():
                return {
                    "status": "error",
                    "action": "multi_edit_file",
                    "error": f"File not found: {file_path}",
                    "error_code": "FILE_NOT_FOUND",
                    "timestamp": datetime.now().isoformat(),
                }

            # Validate edits format
            if not edits or not isinstance(edits, list):
                return {
                    "status": "error",
                    "action": "multi_edit_file",
                    "error": "edits must be a non-empty list of {old_string, new_string} objects",
                    "error_code": "INVALID_EDITS",
                    "timestamp": datetime.now().isoformat(),
                }

            # Read current content
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Validate all edits first
            validation_errors = []
            for i, edit in enumerate(edits):
                if not isinstance(edit, dict):
                    validation_errors.append(f"Edit {i}: must be a dictionary")
                    continue
                if "old_string" not in edit or "new_string" not in edit:
                    validation_errors.append(f"Edit {i}: missing old_string or new_string")
                    continue
                if edit["old_string"] == edit["new_string"]:
                    validation_errors.append(f"Edit {i}: old_string and new_string are identical")
                    continue
                if edit["old_string"] not in content:
                    validation_errors.append(f"Edit {i}: old_string not found in file")
                    continue

            if validation_errors:
                return {
                    "status": "error",
                    "action": "multi_edit_file",
                    "error": "Validation failed for one or more edits",
                    "error_code": "VALIDATION_FAILED",
                    "data": {"errors": validation_errors},
                    "timestamp": datetime.now().isoformat(),
                }

            # Apply all edits
            new_content = content
            for edit in edits:
                new_content = new_content.replace(edit["old_string"], edit["new_string"], 1)

            # Write back
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

            logger.info(f"multi_edit_file: {file_path} ({len(edits)} edits)")

            return {
                "status": "success",
                "action": "multi_edit_file",
                "data": {
                    "file_path": str(path.absolute()),
                    "total_edits": len(edits),
                    "successful_edits": len(edits),
                },
                "timestamp": datetime.now().isoformat(),
            }

        except PermissionError:
            return {
                "status": "error",
                "action": "multi_edit_file",
                "error": f"Permission denied: {file_path}",
                "error_code": "PERMISSION_DENIED",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"multi_edit_file failed: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "multi_edit_file",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    logger.debug("Registered file tools: read_file, write_file, edit_file, multi_edit_file")


def _is_text_file(path: Path, sample_size: int = 8192) -> bool:
    """
    Check if a file is likely a text file by reading a sample.

    Returns True if the file appears to be text, False if binary.
    """
    try:
        with open(path, "rb") as f:
            sample = f.read(sample_size)

        # Check for null bytes (common in binary files)
        if b"\x00" in sample:
            return False

        # Try to decode as UTF-8
        try:
            sample.decode("utf-8")
            return True
        except UnicodeDecodeError:
            pass

        # Try Latin-1 (almost always succeeds for text)
        try:
            sample.decode("latin-1")
            # Check for high ratio of printable characters
            text = sample.decode("latin-1")
            printable_ratio = sum(1 for c in text if c.isprintable() or c.isspace()) / len(text)
            return printable_ratio > 0.85
        except Exception:
            return False

    except Exception:
        return False
