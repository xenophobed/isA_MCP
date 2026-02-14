"""
Search Tools - File and content search operations.

Provides:
- glob_files: Fast file pattern matching (like find with glob patterns)
- grep_search: Content search using regex (ripgrep-style)
- ls_directory: List files and directories

Keywords: search, find, glob, grep, list, directory, files, pattern
"""

import os
import re
import fnmatch
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Maximum results to return
MAX_RESULTS = 1000
# Maximum file size to search (for grep)
MAX_SEARCH_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def register_search_tools(mcp: FastMCP):
    """Register search tools with the MCP server."""

    @mcp.tool()
    async def glob_files(
        pattern: str,
        path: Optional[str] = None,
        include_hidden: bool = False,
        max_results: int = 500,
    ) -> Dict[str, Any]:
        """
        Fast file pattern matching tool that works with any codebase size.

        Supports glob patterns like "**/*.py" or "src/**/*.ts".
        Returns matching file paths sorted by modification time (newest first).

        Args:
            pattern: The glob pattern to match files against.
                Examples:
                - "*.py" - Python files in current directory
                - "**/*.py" - Python files recursively
                - "src/**/*.ts" - TypeScript files in src/
                - "test_*.py" - Files starting with test_
                - "**/*config*" - Files containing 'config' in name
            path: Directory to search in. Defaults to current working directory.
            include_hidden: Include hidden files/directories (starting with .). Default: False.
            max_results: Maximum number of results to return. Default: 500.

        Returns:
            {
                "status": "success",
                "pattern": "**/*.py",
                "path": "/project",
                "matches": ["/project/main.py", "/project/src/utils.py", ...],
                "total_matches": 42,
                "truncated": false
            }

        Keywords: glob, find, files, pattern, search, match, locate
        """
        try:
            # Default to current directory
            search_path = Path(path) if path else Path.cwd()

            if not search_path.exists():
                return {
                    "status": "error",
                    "action": "glob_files",
                    "error": f"Path not found: {path}",
                    "error_code": "PATH_NOT_FOUND",
                    "timestamp": datetime.now().isoformat(),
                }

            if not search_path.is_dir():
                return {
                    "status": "error",
                    "action": "glob_files",
                    "error": f"Path is not a directory: {path}",
                    "error_code": "NOT_A_DIRECTORY",
                    "timestamp": datetime.now().isoformat(),
                }

            # Collect matches
            matches = []
            limit = min(max_results, MAX_RESULTS)

            # Use pathlib glob
            for match in search_path.glob(pattern):
                # Skip hidden files/dirs if not included
                if not include_hidden:
                    parts = match.relative_to(search_path).parts
                    if any(part.startswith(".") for part in parts):
                        continue

                matches.append(match)

                if len(matches) >= limit:
                    break

            # Sort by modification time (newest first)
            matches.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)

            # Convert to strings
            match_paths = [str(m.absolute()) for m in matches]
            truncated = len(matches) >= limit

            logger.info(f"glob_files: pattern='{pattern}' found {len(matches)} matches")

            return {
                "status": "success",
                "action": "glob_files",
                "data": {
                    "pattern": pattern,
                    "path": str(search_path.absolute()),
                    "matches": match_paths,
                    "total_matches": len(match_paths),
                    "truncated": truncated,
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"glob_files failed: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "glob_files",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    @mcp.tool()
    async def grep_search(
        pattern: str,
        path: Optional[str] = None,
        file_pattern: Optional[str] = None,
        case_insensitive: bool = False,
        max_results: int = 100,
        context_lines: int = 0,
        include_line_numbers: bool = True,
    ) -> Dict[str, Any]:
        """
        Fast content search tool using regex patterns (ripgrep-style).

        Searches file contents for text or regex patterns.

        Args:
            pattern: The regex pattern to search for in file contents.
                Examples:
                - "def main" - Literal search
                - "class\\s+\\w+" - Regex: class definitions
                - "TODO|FIXME" - Multiple patterns with OR
            path: File or directory to search in. Defaults to current directory.
            file_pattern: Glob pattern to filter files (e.g., "*.py", "*.{ts,tsx}").
            case_insensitive: Ignore case when matching. Default: False.
            max_results: Maximum number of matches to return. Default: 100.
            context_lines: Number of lines to show before and after match. Default: 0.
            include_line_numbers: Include line numbers in output. Default: True.

        Returns:
            {
                "status": "success",
                "pattern": "def main",
                "matches": [
                    {
                        "file": "/path/to/file.py",
                        "line": 42,
                        "content": "def main():",
                        "context_before": ["", "# Main entry point"],
                        "context_after": ["    parser = argparse.ArgumentParser()"]
                    }
                ],
                "total_matches": 5,
                "files_searched": 100,
                "files_matched": 3
            }

        Keywords: grep, search, find, content, regex, pattern, code, text
        """
        try:
            search_path = Path(path) if path else Path.cwd()

            if not search_path.exists():
                return {
                    "status": "error",
                    "action": "grep_search",
                    "error": f"Path not found: {path}",
                    "error_code": "PATH_NOT_FOUND",
                    "timestamp": datetime.now().isoformat(),
                }

            # Compile regex
            flags = re.IGNORECASE if case_insensitive else 0
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return {
                    "status": "error",
                    "action": "grep_search",
                    "error": f"Invalid regex pattern: {e}",
                    "error_code": "INVALID_REGEX",
                    "timestamp": datetime.now().isoformat(),
                }

            matches = []
            files_searched = 0
            files_matched = set()
            limit = min(max_results, MAX_RESULTS)

            # Get files to search
            if search_path.is_file():
                files_to_search = [search_path]
            else:
                if file_pattern:
                    files_to_search = list(search_path.glob(f"**/{file_pattern}"))
                else:
                    # Search all text files
                    files_to_search = [
                        f
                        for f in search_path.rglob("*")
                        if f.is_file() and not any(p.startswith(".") for p in f.parts)
                    ]

            for file_path in files_to_search:
                if len(matches) >= limit:
                    break

                # Skip large files
                try:
                    if file_path.stat().st_size > MAX_SEARCH_FILE_SIZE:
                        continue
                except OSError:
                    continue

                # Skip binary files
                if not _is_searchable_file(file_path):
                    continue

                files_searched += 1

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    for line_num, line in enumerate(lines, 1):
                        if regex.search(line):
                            files_matched.add(str(file_path))

                            match_entry = {
                                "file": str(file_path.absolute()),
                                "content": line.rstrip(),
                            }

                            if include_line_numbers:
                                match_entry["line"] = line_num

                            # Add context if requested
                            if context_lines > 0:
                                start = max(0, line_num - 1 - context_lines)
                                end = min(len(lines), line_num + context_lines)
                                match_entry["context_before"] = [
                                    l.rstrip() for l in lines[start : line_num - 1]
                                ]
                                match_entry["context_after"] = [
                                    l.rstrip() for l in lines[line_num:end]
                                ]

                            matches.append(match_entry)

                            if len(matches) >= limit:
                                break

                except Exception as e:
                    logger.debug(f"Error searching {file_path}: {e}")
                    continue

            truncated = len(matches) >= limit

            logger.info(
                f"grep_search: pattern='{pattern}' found {len(matches)} matches in {len(files_matched)} files"
            )

            return {
                "status": "success",
                "action": "grep_search",
                "data": {
                    "pattern": pattern,
                    "path": str(search_path.absolute()),
                    "matches": matches,
                    "total_matches": len(matches),
                    "files_searched": files_searched,
                    "files_matched": len(files_matched),
                    "truncated": truncated,
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"grep_search failed: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "grep_search",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    @mcp.tool()
    async def ls_directory(
        path: Optional[str] = None,
        include_hidden: bool = False,
        recursive: bool = False,
        max_depth: int = 3,
        file_pattern: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List files and directories in a given path.

        Returns directory contents with file metadata.

        Args:
            path: Directory path to list. Defaults to current directory.
            include_hidden: Include hidden files (starting with .). Default: False.
            recursive: List recursively. Default: False.
            max_depth: Maximum depth for recursive listing. Default: 3.
            file_pattern: Optional glob pattern to filter results.

        Returns:
            {
                "status": "success",
                "path": "/project",
                "entries": [
                    {
                        "name": "src",
                        "path": "/project/src",
                        "type": "directory",
                        "size": null
                    },
                    {
                        "name": "main.py",
                        "path": "/project/main.py",
                        "type": "file",
                        "size": 1234,
                        "modified": "2024-01-15T10:30:00"
                    }
                ],
                "total_entries": 15,
                "directories": 3,
                "files": 12
            }

        Keywords: ls, list, directory, files, folders, contents, dir
        """
        try:
            list_path = Path(path) if path else Path.cwd()

            if not list_path.exists():
                return {
                    "status": "error",
                    "action": "ls_directory",
                    "error": f"Path not found: {path}",
                    "error_code": "PATH_NOT_FOUND",
                    "timestamp": datetime.now().isoformat(),
                }

            if not list_path.is_dir():
                return {
                    "status": "error",
                    "action": "ls_directory",
                    "error": f"Path is not a directory: {path}",
                    "error_code": "NOT_A_DIRECTORY",
                    "timestamp": datetime.now().isoformat(),
                }

            entries = []
            dir_count = 0
            file_count = 0

            def process_entry(entry_path: Path, depth: int = 0):
                nonlocal dir_count, file_count

                # Skip hidden if not included
                if not include_hidden and entry_path.name.startswith("."):
                    return

                # Apply file pattern filter
                if file_pattern and not fnmatch.fnmatch(entry_path.name, file_pattern):
                    if not entry_path.is_dir():
                        return

                try:
                    stat = entry_path.stat()
                    is_dir = entry_path.is_dir()

                    entry = {
                        "name": entry_path.name,
                        "path": str(entry_path.absolute()),
                        "type": "directory" if is_dir else "file",
                    }

                    if is_dir:
                        dir_count += 1
                        entry["size"] = None
                    else:
                        file_count += 1
                        entry["size"] = stat.st_size
                        entry["modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()

                    entries.append(entry)

                    # Recurse if directory and recursive mode
                    if is_dir and recursive and depth < max_depth:
                        try:
                            for child in sorted(entry_path.iterdir()):
                                process_entry(child, depth + 1)
                        except PermissionError:
                            pass

                except (PermissionError, OSError) as e:
                    logger.debug(f"Cannot access {entry_path}: {e}")

            # Process top-level entries
            try:
                for entry in sorted(list_path.iterdir()):
                    process_entry(entry)
            except PermissionError:
                return {
                    "status": "error",
                    "action": "ls_directory",
                    "error": f"Permission denied: {path}",
                    "error_code": "PERMISSION_DENIED",
                    "timestamp": datetime.now().isoformat(),
                }

            logger.info(f"ls_directory: {path} ({len(entries)} entries)")

            return {
                "status": "success",
                "action": "ls_directory",
                "data": {
                    "path": str(list_path.absolute()),
                    "entries": entries,
                    "total_entries": len(entries),
                    "directories": dir_count,
                    "files": file_count,
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"ls_directory failed: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "ls_directory",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    logger.debug("Registered search tools: glob_files, grep_search, ls_directory")


def _is_searchable_file(path: Path) -> bool:
    """Check if a file is searchable (text-based)."""
    # Skip known binary extensions
    binary_extensions = {
        ".pyc",
        ".pyo",
        ".so",
        ".dylib",
        ".dll",
        ".exe",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".ico",
        ".bmp",
        ".webp",
        ".mp3",
        ".mp4",
        ".wav",
        ".avi",
        ".mov",
        ".mkv",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".7z",
        ".rar",
        ".bin",
        ".dat",
        ".db",
        ".sqlite",
        ".sqlite3",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".eot",
        ".class",
        ".jar",
        ".war",
        ".o",
        ".a",
        ".lib",
        ".node",
        ".wasm",
    }

    if path.suffix.lower() in binary_extensions:
        return False

    # Try to read first few bytes
    try:
        with open(path, "rb") as f:
            sample = f.read(512)
            # Binary files often have null bytes
            if b"\x00" in sample:
                return False
    except OSError:
        return False

    return True
