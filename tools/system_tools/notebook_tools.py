"""
Notebook Tools - Jupyter notebook operations.

Provides:
- notebook_read: Read Jupyter notebook cells and outputs
- notebook_edit: Replace, insert, or delete notebook cells

Keywords: notebook, jupyter, ipynb, cell, code, markdown
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_notebook_tools(mcp: FastMCP):
    """Register Jupyter notebook tools with the MCP server."""

    @mcp.tool()
    async def notebook_read(
        notebook_path: str,
        include_outputs: bool = True,
        cell_range: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Read a Jupyter notebook (.ipynb file) and return all cells.

        Returns all cells with their source code, cell type, and optionally outputs.

        Args:
            notebook_path: Absolute path to the Jupyter notebook file.
            include_outputs: Include cell outputs in the response. Default: True.
            cell_range: Optional range of cells to read (e.g., "0-5", "3-10"). Default: all cells.

        Returns:
            {
                "status": "success",
                "notebook_path": "/path/to/notebook.ipynb",
                "metadata": {
                    "kernel": "python3",
                    "language": "python"
                },
                "cells": [
                    {
                        "index": 0,
                        "cell_id": "abc123",
                        "cell_type": "code",
                        "source": "import pandas as pd",
                        "outputs": [...],
                        "execution_count": 1
                    },
                    {
                        "index": 1,
                        "cell_id": "def456",
                        "cell_type": "markdown",
                        "source": "# Analysis"
                    }
                ],
                "total_cells": 10
            }

        Keywords: notebook, read, jupyter, ipynb, cells, view
        """
        try:
            path = Path(notebook_path)

            # Validate file exists
            if not path.exists():
                return {
                    "status": "error",
                    "action": "notebook_read",
                    "error": f"Notebook not found: {notebook_path}",
                    "error_code": "FILE_NOT_FOUND",
                    "timestamp": datetime.now().isoformat()
                }

            # Validate it's a notebook
            if path.suffix.lower() != '.ipynb':
                return {
                    "status": "error",
                    "action": "notebook_read",
                    "error": f"Not a Jupyter notebook (expected .ipynb): {notebook_path}",
                    "error_code": "INVALID_FILE_TYPE",
                    "timestamp": datetime.now().isoformat()
                }

            # Read notebook
            with open(path, 'r', encoding='utf-8') as f:
                notebook = json.load(f)

            # Extract metadata
            metadata = {}
            if 'metadata' in notebook:
                nb_meta = notebook['metadata']
                if 'kernelspec' in nb_meta:
                    metadata['kernel'] = nb_meta['kernelspec'].get('name', 'unknown')
                    metadata['language'] = nb_meta['kernelspec'].get('language', 'unknown')
                elif 'language_info' in nb_meta:
                    metadata['language'] = nb_meta['language_info'].get('name', 'unknown')

            # Parse cell range
            start_idx, end_idx = 0, len(notebook.get('cells', []))
            if cell_range:
                try:
                    parts = cell_range.split('-')
                    start_idx = int(parts[0])
                    end_idx = int(parts[1]) + 1 if len(parts) > 1 else start_idx + 1
                except ValueError:
                    return {
                        "status": "error",
                        "action": "notebook_read",
                        "error": f"Invalid cell_range format: {cell_range}. Use 'start-end' (e.g., '0-5')",
                        "error_code": "INVALID_RANGE",
                        "timestamp": datetime.now().isoformat()
                    }

            # Process cells
            cells = []
            for idx, cell in enumerate(notebook.get('cells', [])):
                if idx < start_idx or idx >= end_idx:
                    continue

                cell_data = {
                    "index": idx,
                    "cell_type": cell.get('cell_type', 'unknown'),
                    "source": _join_source(cell.get('source', []))
                }

                # Add cell ID if available (nbformat 4.5+)
                if 'id' in cell:
                    cell_data['cell_id'] = cell['id']

                # Add execution count for code cells
                if cell.get('cell_type') == 'code':
                    cell_data['execution_count'] = cell.get('execution_count')

                # Add outputs if requested
                if include_outputs and cell.get('cell_type') == 'code':
                    cell_data['outputs'] = _process_outputs(cell.get('outputs', []))

                cells.append(cell_data)

            logger.info(f"notebook_read: {notebook_path} ({len(cells)} cells)")

            return {
                "status": "success",
                "action": "notebook_read",
                "data": {
                    "notebook_path": str(path.absolute()),
                    "metadata": metadata,
                    "cells": cells,
                    "total_cells": len(notebook.get('cells', []))
                },
                "timestamp": datetime.now().isoformat()
            }

        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "action": "notebook_read",
                "error": f"Invalid notebook JSON: {e}",
                "error_code": "INVALID_JSON",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"notebook_read failed: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "notebook_read",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    @mcp.tool()
    async def notebook_edit(
        notebook_path: str,
        new_source: str,
        cell_index: Optional[int] = None,
        cell_id: Optional[str] = None,
        cell_type: Optional[str] = None,
        edit_mode: str = "replace"
    ) -> Dict[str, Any]:
        """
        Edit a Jupyter notebook cell.

        Supports replacing, inserting, or deleting cells.

        Args:
            notebook_path: Absolute path to the Jupyter notebook file.
            new_source: The new source content for the cell.
            cell_index: The 0-indexed position of the cell to edit.
            cell_id: The ID of the cell to edit (alternative to cell_index).
            cell_type: Cell type for new/replaced cells: "code" or "markdown".
                       Required for insert mode, optional for replace.
            edit_mode: The type of edit: "replace", "insert", or "delete".
                       - replace: Replace the cell's content (default)
                       - insert: Insert a new cell at the position
                       - delete: Delete the cell (new_source is ignored)

        Returns:
            {
                "status": "success",
                "notebook_path": "/path/to/notebook.ipynb",
                "edit_mode": "replace",
                "cell_index": 3,
                "cell_type": "code"
            }

        Keywords: notebook, edit, jupyter, ipynb, cell, modify, insert, delete
        """
        try:
            path = Path(notebook_path)

            # Validate file exists
            if not path.exists():
                return {
                    "status": "error",
                    "action": "notebook_edit",
                    "error": f"Notebook not found: {notebook_path}",
                    "error_code": "FILE_NOT_FOUND",
                    "timestamp": datetime.now().isoformat()
                }

            # Validate edit_mode
            if edit_mode not in ["replace", "insert", "delete"]:
                return {
                    "status": "error",
                    "action": "notebook_edit",
                    "error": f"Invalid edit_mode: {edit_mode}. Must be 'replace', 'insert', or 'delete'",
                    "error_code": "INVALID_MODE",
                    "timestamp": datetime.now().isoformat()
                }

            # Validate cell_type for insert mode
            if edit_mode == "insert" and cell_type not in ["code", "markdown"]:
                return {
                    "status": "error",
                    "action": "notebook_edit",
                    "error": "cell_type is required for insert mode: 'code' or 'markdown'",
                    "error_code": "MISSING_CELL_TYPE",
                    "timestamp": datetime.now().isoformat()
                }

            # Read notebook
            with open(path, 'r', encoding='utf-8') as f:
                notebook = json.load(f)

            cells = notebook.get('cells', [])

            # Find target cell
            target_index = None

            if cell_index is not None:
                if cell_index < 0 or cell_index > len(cells):
                    return {
                        "status": "error",
                        "action": "notebook_edit",
                        "error": f"cell_index {cell_index} out of range (0-{len(cells)-1})",
                        "error_code": "INDEX_OUT_OF_RANGE",
                        "timestamp": datetime.now().isoformat()
                    }
                target_index = cell_index

            elif cell_id is not None:
                for idx, cell in enumerate(cells):
                    if cell.get('id') == cell_id:
                        target_index = idx
                        break

                if target_index is None:
                    return {
                        "status": "error",
                        "action": "notebook_edit",
                        "error": f"Cell with id '{cell_id}' not found",
                        "error_code": "CELL_NOT_FOUND",
                        "timestamp": datetime.now().isoformat()
                    }
            else:
                return {
                    "status": "error",
                    "action": "notebook_edit",
                    "error": "Either cell_index or cell_id must be provided",
                    "error_code": "MISSING_CELL_IDENTIFIER",
                    "timestamp": datetime.now().isoformat()
                }

            # Perform edit
            if edit_mode == "delete":
                if target_index >= len(cells):
                    return {
                        "status": "error",
                        "action": "notebook_edit",
                        "error": f"Cannot delete cell at index {target_index}: only {len(cells)} cells exist",
                        "error_code": "INDEX_OUT_OF_RANGE",
                        "timestamp": datetime.now().isoformat()
                    }
                deleted_cell = cells.pop(target_index)
                result_cell_type = deleted_cell.get('cell_type', 'unknown')

            elif edit_mode == "insert":
                new_cell = _create_cell(
                    cell_type=cell_type,
                    source=new_source
                )
                cells.insert(target_index, new_cell)
                result_cell_type = cell_type

            else:  # replace
                if target_index >= len(cells):
                    return {
                        "status": "error",
                        "action": "notebook_edit",
                        "error": f"Cannot replace cell at index {target_index}: only {len(cells)} cells exist",
                        "error_code": "INDEX_OUT_OF_RANGE",
                        "timestamp": datetime.now().isoformat()
                    }

                existing_cell = cells[target_index]
                result_cell_type = cell_type or existing_cell.get('cell_type', 'code')

                # Update the cell
                existing_cell['source'] = new_source.split('\n')
                if cell_type:
                    existing_cell['cell_type'] = cell_type

                # Clear outputs and execution count for code cells
                if existing_cell.get('cell_type') == 'code':
                    existing_cell['outputs'] = []
                    existing_cell['execution_count'] = None

            # Write back
            notebook['cells'] = cells
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(notebook, f, indent=1, ensure_ascii=False)

            logger.info(f"notebook_edit: {notebook_path} mode={edit_mode} index={target_index}")

            return {
                "status": "success",
                "action": "notebook_edit",
                "data": {
                    "notebook_path": str(path.absolute()),
                    "edit_mode": edit_mode,
                    "cell_index": target_index,
                    "cell_type": result_cell_type,
                    "total_cells": len(cells)
                },
                "timestamp": datetime.now().isoformat()
            }

        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "action": "notebook_edit",
                "error": f"Invalid notebook JSON: {e}",
                "error_code": "INVALID_JSON",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"notebook_edit failed: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "notebook_edit",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    logger.debug("Registered notebook tools: notebook_read, notebook_edit")


def _join_source(source) -> str:
    """Join notebook cell source (can be string or list of strings)."""
    if isinstance(source, list):
        return ''.join(source)
    return source


def _process_outputs(outputs: List[Dict]) -> List[Dict[str, Any]]:
    """Process notebook cell outputs for readable format."""
    processed = []

    for output in outputs:
        output_type = output.get('output_type', 'unknown')
        processed_output = {"type": output_type}

        if output_type == 'stream':
            processed_output['name'] = output.get('name', 'stdout')
            processed_output['text'] = _join_source(output.get('text', []))

        elif output_type == 'execute_result':
            processed_output['execution_count'] = output.get('execution_count')
            data = output.get('data', {})
            if 'text/plain' in data:
                processed_output['text'] = _join_source(data['text/plain'])
            if 'text/html' in data:
                processed_output['html'] = _join_source(data['text/html'])[:500] + "..."

        elif output_type == 'display_data':
            data = output.get('data', {})
            if 'text/plain' in data:
                processed_output['text'] = _join_source(data['text/plain'])
            if 'image/png' in data:
                processed_output['has_image'] = True

        elif output_type == 'error':
            processed_output['ename'] = output.get('ename', 'Error')
            processed_output['evalue'] = output.get('evalue', '')
            traceback = output.get('traceback', [])
            # Clean ANSI escape codes
            clean_tb = [_strip_ansi(line) for line in traceback]
            processed_output['traceback'] = '\n'.join(clean_tb)

        processed.append(processed_output)

    return processed


def _create_cell(cell_type: str, source: str) -> Dict[str, Any]:
    """Create a new notebook cell."""
    import uuid

    cell = {
        "cell_type": cell_type,
        "source": source.split('\n'),
        "metadata": {},
        "id": str(uuid.uuid4())[:8]
    }

    if cell_type == "code":
        cell["execution_count"] = None
        cell["outputs"] = []

    return cell


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)
