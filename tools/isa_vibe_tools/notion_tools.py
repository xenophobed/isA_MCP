#!/usr/bin/env python3
"""
Notion Tools for MCP Server

Provides Notion workspace access for agents via Notion API.
This allows agents to read/write PRDs, manage skills templates, and sync documentation.

Migrated from isA_Vibe/src/agents/mcp_servers/notion_mcp.py

Environment:
    NOTION_TOKEN or NOTION_API_KEY: Notion integration token (required)
    NOTION_VERSION: API version (default: 2022-06-28)
"""

import json
import os
import re
from typing import Any, Optional, Dict, List

from mcp.server.fastmcp import FastMCP
from core.logging import get_logger
from tools.base_tool import BaseTool

# Optional notion-client import
try:
    from notion_client import AsyncClient
    from notion_client.errors import APIResponseError
    NOTION_CLIENT_AVAILABLE = True
except ImportError:
    NOTION_CLIENT_AVAILABLE = False
    AsyncClient = None
    APIResponseError = Exception

logger = get_logger(__name__)
tools = BaseTool()

# Configuration - supports both NOTION_TOKEN and NOTION_API_KEY
NOTION_API_KEY = os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_KEY", "")
NOTION_VERSION = os.getenv("NOTION_VERSION", "2022-06-28")


def get_notion_client() -> AsyncClient:
    """Get Notion async client."""
    if not NOTION_CLIENT_AVAILABLE:
        raise ImportError("notion-client not installed. Install with: pip install notion-client")
    if not NOTION_API_KEY:
        raise ValueError("NOTION_TOKEN or NOTION_API_KEY environment variable is required")
    return AsyncClient(auth=NOTION_API_KEY)


def extract_text_from_rich_text(rich_text: List[Dict]) -> str:
    """Extract plain text from Notion rich text array."""
    return "".join(item.get("plain_text", "") for item in rich_text)


def extract_page_properties(properties: Dict) -> Dict:
    """Extract readable values from Notion page properties."""
    result = {}
    for prop_name, prop_value in properties.items():
        prop_type = prop_value.get("type")

        if prop_type == "title":
            result[prop_name] = extract_text_from_rich_text(prop_value.get("title", []))
        elif prop_type == "rich_text":
            result[prop_name] = extract_text_from_rich_text(prop_value.get("rich_text", []))
        elif prop_type == "number":
            result[prop_name] = prop_value.get("number")
        elif prop_type == "select":
            select = prop_value.get("select")
            result[prop_name] = select.get("name") if select else None
        elif prop_type == "multi_select":
            result[prop_name] = [item.get("name") for item in prop_value.get("multi_select", [])]
        elif prop_type == "date":
            date = prop_value.get("date")
            result[prop_name] = date.get("start") if date else None
        elif prop_type == "checkbox":
            result[prop_name] = prop_value.get("checkbox")
        elif prop_type == "url":
            result[prop_name] = prop_value.get("url")
        elif prop_type == "email":
            result[prop_name] = prop_value.get("email")
        elif prop_type == "phone_number":
            result[prop_name] = prop_value.get("phone_number")
        elif prop_type == "status":
            status = prop_value.get("status")
            result[prop_name] = status.get("name") if status else None
        elif prop_type == "relation":
            result[prop_name] = [rel.get("id") for rel in prop_value.get("relation", [])]
        elif prop_type == "formula":
            formula = prop_value.get("formula", {})
            result[prop_name] = formula.get(formula.get("type"))
        elif prop_type == "rollup":
            rollup = prop_value.get("rollup", {})
            result[prop_name] = rollup.get(rollup.get("type"))
        elif prop_type == "created_time":
            result[prop_name] = prop_value.get("created_time")
        elif prop_type == "last_edited_time":
            result[prop_name] = prop_value.get("last_edited_time")
        elif prop_type == "created_by":
            result[prop_name] = prop_value.get("created_by", {}).get("id")
        elif prop_type == "last_edited_by":
            result[prop_name] = prop_value.get("last_edited_by", {}).get("id")
        else:
            result[prop_name] = f"<{prop_type}>"

    return result


def blocks_to_markdown(blocks: List[Dict], indent: int = 0) -> str:
    """Convert Notion blocks to markdown."""
    lines = []
    prefix = "  " * indent

    for block in blocks:
        block_type = block.get("type")

        if block_type == "paragraph":
            text = extract_text_from_rich_text(block.get("paragraph", {}).get("rich_text", []))
            lines.append(f"{prefix}{text}")

        elif block_type == "heading_1":
            text = extract_text_from_rich_text(block.get("heading_1", {}).get("rich_text", []))
            lines.append(f"{prefix}# {text}")

        elif block_type == "heading_2":
            text = extract_text_from_rich_text(block.get("heading_2", {}).get("rich_text", []))
            lines.append(f"{prefix}## {text}")

        elif block_type == "heading_3":
            text = extract_text_from_rich_text(block.get("heading_3", {}).get("rich_text", []))
            lines.append(f"{prefix}### {text}")

        elif block_type == "bulleted_list_item":
            text = extract_text_from_rich_text(block.get("bulleted_list_item", {}).get("rich_text", []))
            lines.append(f"{prefix}- {text}")

        elif block_type == "numbered_list_item":
            text = extract_text_from_rich_text(block.get("numbered_list_item", {}).get("rich_text", []))
            lines.append(f"{prefix}1. {text}")

        elif block_type == "to_do":
            todo = block.get("to_do", {})
            text = extract_text_from_rich_text(todo.get("rich_text", []))
            checked = "x" if todo.get("checked") else " "
            lines.append(f"{prefix}- [{checked}] {text}")

        elif block_type == "toggle":
            text = extract_text_from_rich_text(block.get("toggle", {}).get("rich_text", []))
            lines.append(f"{prefix}<details><summary>{text}</summary>")

        elif block_type == "code":
            code = block.get("code", {})
            text = extract_text_from_rich_text(code.get("rich_text", []))
            lang = code.get("language", "")
            lines.append(f"{prefix}```{lang}")
            lines.append(text)
            lines.append(f"{prefix}```")

        elif block_type == "quote":
            text = extract_text_from_rich_text(block.get("quote", {}).get("rich_text", []))
            lines.append(f"{prefix}> {text}")

        elif block_type == "callout":
            callout = block.get("callout", {})
            text = extract_text_from_rich_text(callout.get("rich_text", []))
            icon = callout.get("icon", {}).get("emoji", "")
            lines.append(f"{prefix}> {icon} {text}")

        elif block_type == "divider":
            lines.append(f"{prefix}---")

        elif block_type == "table":
            lines.append(f"{prefix}<table>")

        elif block_type == "child_page":
            title = block.get("child_page", {}).get("title", "Untitled")
            lines.append(f"{prefix}[{title}](page:{block.get('id')})")

        elif block_type == "child_database":
            title = block.get("child_database", {}).get("title", "Untitled")
            lines.append(f"{prefix}[{title}](database:{block.get('id')})")

        else:
            lines.append(f"{prefix}[{block_type}]")

    return "\n".join(lines)


def parse_id(id_or_url: str) -> str:
    """Extract Notion ID from URL or return as-is if already an ID."""
    if "/" in id_or_url:
        # URL format: https://www.notion.so/workspace/Page-Title-abc123def456
        parts = id_or_url.rstrip("/").split("/")
        last_part = parts[-1]
        # Handle ?v= query params for database views
        if "?" in last_part:
            last_part = last_part.split("?")[0]
        # Extract 32-char hex ID from end of string
        match = re.search(r'([a-f0-9]{32})$', last_part.replace("-", ""))
        if match:
            return match.group(1)
        # Fallback: return last part without dashes
        return last_part.replace("-", "")
    # Remove dashes if present (standardize format)
    return id_or_url.replace("-", "")


def markdown_to_blocks(markdown: str) -> List[Dict]:
    """Convert simple markdown to Notion blocks."""
    blocks = []
    lines = markdown.split("\n")

    for line in lines:
        line = line.rstrip()
        if not line:
            continue

        if line.startswith("### "):
            blocks.append({
                "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:]}}]}
            })
        elif line.startswith("## "):
            blocks.append({
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]}
            })
        elif line.startswith("# "):
            blocks.append({
                "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}
            })
        elif line.startswith("- [ ] "):
            blocks.append({
                "type": "to_do",
                "to_do": {"rich_text": [{"type": "text", "text": {"content": line[6:]}}], "checked": False}
            })
        elif line.startswith("- [x] "):
            blocks.append({
                "type": "to_do",
                "to_do": {"rich_text": [{"type": "text", "text": {"content": line[6:]}}], "checked": True}
            })
        elif line.startswith("- "):
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}
            })
        elif line.startswith("> "):
            blocks.append({
                "type": "quote",
                "quote": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}
            })
        elif line.startswith("---"):
            blocks.append({"type": "divider", "divider": {}})
        elif line.startswith("1. ") or (len(line) > 2 and line[0].isdigit() and line[1:3] == ". "):
            text = line.split(". ", 1)[1] if ". " in line else line
            blocks.append({
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]}
            })
        else:
            blocks.append({
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}
            })

    return blocks


def register_notion_tools(mcp: FastMCP):
    """Register Notion tools with the MCP server."""

    @mcp.tool()
    async def notion_search(
        query: str,
        filter_type: Optional[str] = None,
        limit: int = 10
    ) -> dict:
        """Search for pages and databases in Notion workspace

        Args:
            query: Search query text
            filter_type: Filter by object type - "page" or "database" (optional)
            limit: Maximum results (default: 10, max: 100)

        Returns:
            Dict with query, results list, and count
        """
        try:
            client = get_notion_client()
            limit = min(limit, 100)

            search_params = {"query": query, "page_size": limit}
            if filter_type:
                search_params["filter"] = {"property": "object", "value": filter_type}

            results = await client.search(**search_params)

            items = []
            for item in results.get("results", []):
                obj_type = item.get("object")
                item_id = item.get("id")

                if obj_type == "page":
                    props = extract_page_properties(item.get("properties", {}))
                    title = props.get("title") or props.get("Name") or props.get("Title") or "Untitled"
                    items.append({
                        "type": "page",
                        "id": item_id,
                        "title": title,
                        "url": item.get("url"),
                        "last_edited": item.get("last_edited_time")
                    })
                elif obj_type == "database":
                    title = extract_text_from_rich_text(item.get("title", []))
                    items.append({
                        "type": "database",
                        "id": item_id,
                        "title": title or "Untitled Database",
                        "url": item.get("url")
                    })

            return tools.create_response(
                status="success",
                action="notion_search",
                data={"query": query, "results": items, "count": len(items)}
            )

        except APIResponseError as e:
            return tools.create_response(
                status="error",
                action="notion_search",
                data={"query": query},
                error_message=str(e),
                error_code=str(e.code) if hasattr(e, 'code') else None if hasattr(e, 'code') else None
            )
        except Exception as e:
            logger.error(f"Error in notion_search: {e}")
            return tools.create_response(
                status="error",
                action="notion_search",
                data={"query": query},
                error_message=str(e)
            )

    @mcp.tool()
    async def notion_get_page(page_id: str) -> dict:
        """Get a page's properties and metadata

        Args:
            page_id: Notion page ID or URL

        Returns:
            Dict with page info and extracted properties
        """
        try:
            client = get_notion_client()
            page_id = parse_id(page_id)
            page = await client.pages.retrieve(page_id=page_id)

            props = extract_page_properties(page.get("properties", {}))

            return tools.create_response(
                status="success",
                action="notion_get_page",
                data={
                    "id": page.get("id"),
                    "url": page.get("url"),
                    "created_time": page.get("created_time"),
                    "last_edited_time": page.get("last_edited_time"),
                    "archived": page.get("archived"),
                    "properties": props
                }
            )

        except APIResponseError as e:
            return tools.create_response(
                status="error",
                action="notion_get_page",
                data={"page_id": page_id},
                error_message=str(e),
                error_code=str(e.code) if hasattr(e, 'code') else None
            )
        except Exception as e:
            logger.error(f"Error in notion_get_page: {e}")
            return tools.create_response(
                status="error",
                action="notion_get_page",
                data={"page_id": page_id},
                error_message=str(e)
            )

    @mcp.tool()
    async def notion_get_page_content(page_id: str) -> dict:
        """Get a page's content as markdown

        Args:
            page_id: Notion page ID or URL

        Returns:
            Dict with page info and content as markdown
        """
        try:
            client = get_notion_client()
            page_id = parse_id(page_id)

            # Get page metadata first
            page = await client.pages.retrieve(page_id=page_id)
            props = extract_page_properties(page.get("properties", {}))
            title = props.get("title") or props.get("Name") or props.get("Title") or "Untitled"

            # Get blocks
            blocks_response = await client.blocks.children.list(block_id=page_id, page_size=100)
            blocks = blocks_response.get("results", [])

            # Convert to markdown
            markdown = blocks_to_markdown(blocks)

            return tools.create_response(
                status="success",
                action="notion_get_page_content",
                data={
                    "id": page_id,
                    "title": title,
                    "url": page.get("url"),
                    "content_markdown": markdown,
                    "block_count": len(blocks)
                }
            )

        except APIResponseError as e:
            return tools.create_response(
                status="error",
                action="notion_get_page_content",
                data={"page_id": page_id},
                error_message=str(e),
                error_code=str(e.code) if hasattr(e, 'code') else None
            )
        except Exception as e:
            logger.error(f"Error in notion_get_page_content: {e}")
            return tools.create_response(
                status="error",
                action="notion_get_page_content",
                data={"page_id": page_id},
                error_message=str(e)
            )

    @mcp.tool()
    async def notion_get_database(database_id: str) -> dict:
        """Get database schema and properties

        Args:
            database_id: Notion database ID or URL

        Returns:
            Dict with database info and schema
        """
        try:
            client = get_notion_client()
            db_id = parse_id(database_id)
            db = await client.databases.retrieve(database_id=db_id)

            title = extract_text_from_rich_text(db.get("title", []))

            # Extract schema
            schema = {}
            for prop_name, prop_def in db.get("properties", {}).items():
                prop_type = prop_def.get("type")
                schema[prop_name] = {"type": prop_type}

                if prop_type == "select":
                    schema[prop_name]["options"] = [
                        opt.get("name") for opt in prop_def.get("select", {}).get("options", [])
                    ]
                elif prop_type == "multi_select":
                    schema[prop_name]["options"] = [
                        opt.get("name") for opt in prop_def.get("multi_select", {}).get("options", [])
                    ]
                elif prop_type == "status":
                    schema[prop_name]["options"] = [
                        opt.get("name") for opt in prop_def.get("status", {}).get("options", [])
                    ]

            return tools.create_response(
                status="success",
                action="notion_get_database",
                data={
                    "id": db.get("id"),
                    "title": title or "Untitled Database",
                    "url": db.get("url"),
                    "schema": schema
                }
            )

        except APIResponseError as e:
            return tools.create_response(
                status="error",
                action="notion_get_database",
                data={"database_id": database_id},
                error_message=str(e),
                error_code=str(e.code) if hasattr(e, 'code') else None
            )
        except Exception as e:
            logger.error(f"Error in notion_get_database: {e}")
            return tools.create_response(
                status="error",
                action="notion_get_database",
                data={"database_id": database_id},
                error_message=str(e)
            )

    @mcp.tool()
    async def notion_query_database(
        database_id: str,
        filter_obj: Optional[dict] = None,
        sorts: Optional[list] = None,
        limit: int = 50
    ) -> dict:
        """Query a database with optional filters and sorts

        Args:
            database_id: Notion database ID
            filter_obj: Notion filter object (optional)
            sorts: Sort criteria array (optional)
            limit: Maximum results (default: 50, max: 100)

        Returns:
            Dict with database_id, results, count, has_more
        """
        try:
            client = get_notion_client()
            db_id = parse_id(database_id)
            limit = min(limit, 100)

            query_params = {"database_id": db_id, "page_size": limit}
            if filter_obj:
                query_params["filter"] = filter_obj
            if sorts:
                query_params["sorts"] = sorts

            results = await client.databases.query(**query_params)

            items = []
            for page in results.get("results", []):
                props = extract_page_properties(page.get("properties", {}))
                items.append({
                    "id": page.get("id"),
                    "url": page.get("url"),
                    "properties": props
                })

            return tools.create_response(
                status="success",
                action="notion_query_database",
                data={
                    "database_id": db_id,
                    "results": items,
                    "count": len(items),
                    "has_more": results.get("has_more", False)
                }
            )

        except APIResponseError as e:
            return tools.create_response(
                status="error",
                action="notion_query_database",
                data={"database_id": database_id},
                error_message=str(e),
                error_code=str(e.code) if hasattr(e, 'code') else None
            )
        except Exception as e:
            logger.error(f"Error in notion_query_database: {e}")
            return tools.create_response(
                status="error",
                action="notion_query_database",
                data={"database_id": database_id},
                error_message=str(e)
            )

    @mcp.tool()
    async def notion_create_page(
        parent_id: str,
        title: str,
        parent_type: str = "database",
        properties: Optional[dict] = None,
        content: Optional[str] = None
    ) -> dict:
        """Create a new page in a database or as child of another page

        Args:
            parent_id: Parent database ID or page ID
            title: Page title
            parent_type: Type of parent - "database" or "page" (default: database)
            properties: Page properties (for database items)
            content: Initial page content as markdown (optional)

        Returns:
            Dict with created, id, url
        """
        try:
            client = get_notion_client()
            parent_id = parse_id(parent_id)
            properties = properties or {}

            # Build parent reference
            if parent_type == "database":
                parent = {"database_id": parent_id}
                if "Name" not in properties and "title" not in properties:
                    properties["Name"] = {"title": [{"text": {"content": title}}]}
            else:
                parent = {"page_id": parent_id}

            # Build properties
            notion_props = {}
            for prop_name, prop_value in properties.items():
                if isinstance(prop_value, dict):
                    notion_props[prop_name] = prop_value
                elif isinstance(prop_value, str):
                    notion_props[prop_name] = {
                        "rich_text": [{"text": {"content": prop_value}}]
                    }

            if "Name" in properties and isinstance(properties["Name"], str):
                notion_props["Name"] = {"title": [{"text": {"content": properties["Name"]}}]}

            create_params = {"parent": parent, "properties": notion_props}

            if content:
                create_params["children"] = markdown_to_blocks(content)

            page = await client.pages.create(**create_params)

            return tools.create_response(
                status="success",
                action="notion_create_page",
                data={
                    "created": True,
                    "id": page.get("id"),
                    "url": page.get("url")
                }
            )

        except APIResponseError as e:
            return tools.create_response(
                status="error",
                action="notion_create_page",
                data={"parent_id": parent_id, "title": title},
                error_message=str(e),
                error_code=str(e.code) if hasattr(e, 'code') else None
            )
        except Exception as e:
            logger.error(f"Error in notion_create_page: {e}")
            return tools.create_response(
                status="error",
                action="notion_create_page",
                data={"parent_id": parent_id, "title": title},
                error_message=str(e)
            )

    @mcp.tool()
    async def notion_update_page(
        page_id: str,
        properties: Optional[dict] = None,
        archived: Optional[bool] = None
    ) -> dict:
        """Update page properties

        Args:
            page_id: Page ID to update
            properties: Properties to update
            archived: Archive/unarchive the page

        Returns:
            Dict with updated, id, url, archived
        """
        try:
            client = get_notion_client()
            page_id = parse_id(page_id)

            update_params = {"page_id": page_id}

            if properties:
                notion_props = {}
                for prop_name, prop_value in properties.items():
                    if isinstance(prop_value, dict):
                        notion_props[prop_name] = prop_value
                    elif isinstance(prop_value, str):
                        notion_props[prop_name] = {
                            "rich_text": [{"text": {"content": prop_value}}]
                        }
                update_params["properties"] = notion_props

            if archived is not None:
                update_params["archived"] = archived

            page = await client.pages.update(**update_params)

            return tools.create_response(
                status="success",
                action="notion_update_page",
                data={
                    "updated": True,
                    "id": page.get("id"),
                    "url": page.get("url"),
                    "archived": page.get("archived")
                }
            )

        except APIResponseError as e:
            return tools.create_response(
                status="error",
                action="notion_update_page",
                data={"page_id": page_id},
                error_message=str(e),
                error_code=str(e.code) if hasattr(e, 'code') else None
            )
        except Exception as e:
            logger.error(f"Error in notion_update_page: {e}")
            return tools.create_response(
                status="error",
                action="notion_update_page",
                data={"page_id": page_id},
                error_message=str(e)
            )

    @mcp.tool()
    async def notion_append_blocks(page_id: str, markdown: str) -> dict:
        """Append content blocks to a page

        Args:
            page_id: Page ID to append to
            markdown: Markdown content to append

        Returns:
            Dict with appended, page_id, blocks_added
        """
        try:
            client = get_notion_client()
            page_id = parse_id(page_id)
            blocks = markdown_to_blocks(markdown)

            await client.blocks.children.append(block_id=page_id, children=blocks)

            return tools.create_response(
                status="success",
                action="notion_append_blocks",
                data={
                    "appended": True,
                    "page_id": page_id,
                    "blocks_added": len(blocks)
                }
            )

        except APIResponseError as e:
            return tools.create_response(
                status="error",
                action="notion_append_blocks",
                data={"page_id": page_id},
                error_message=str(e),
                error_code=str(e.code) if hasattr(e, 'code') else None
            )
        except Exception as e:
            logger.error(f"Error in notion_append_blocks: {e}")
            return tools.create_response(
                status="error",
                action="notion_append_blocks",
                data={"page_id": page_id},
                error_message=str(e)
            )

    @mcp.tool()
    async def notion_replace_content(page_id: str, markdown: str) -> dict:
        """Replace all content blocks in a page (clears existing content first)

        Args:
            page_id: Page ID to replace content
            markdown: Markdown content to replace with

        Returns:
            Dict with replaced, page_id, blocks_deleted, blocks_added
        """
        try:
            client = get_notion_client()
            page_id = parse_id(page_id)

            # First, delete all existing blocks
            existing_blocks = await client.blocks.children.list(block_id=page_id)
            deleted_count = 0
            for block in existing_blocks.get("results", []):
                try:
                    await client.blocks.delete(block_id=block["id"])
                    deleted_count += 1
                except Exception:
                    pass  # Some blocks may not be deletable

            # Then add new content
            blocks = markdown_to_blocks(markdown)
            if blocks:
                await client.blocks.children.append(block_id=page_id, children=blocks)

            return tools.create_response(
                status="success",
                action="notion_replace_content",
                data={
                    "replaced": True,
                    "page_id": page_id,
                    "blocks_deleted": deleted_count,
                    "blocks_added": len(blocks)
                }
            )

        except APIResponseError as e:
            return tools.create_response(
                status="error",
                action="notion_replace_content",
                data={"page_id": page_id},
                error_message=str(e),
                error_code=str(e.code) if hasattr(e, 'code') else None
            )
        except Exception as e:
            logger.error(f"Error in notion_replace_content: {e}")
            return tools.create_response(
                status="error",
                action="notion_replace_content",
                data={"page_id": page_id},
                error_message=str(e)
            )

    @mcp.tool()
    async def notion_update_backlog_item(
        page_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        item_type: Optional[str] = None,
        project: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        latest_status: Optional[str] = None,
        content: Optional[str] = None
    ) -> dict:
        """Update a Product Backlog item with common fields (Status, Priority, Type, etc.)

        Args:
            page_id: Page ID to update
            status: Status field (Not Started, In Progress, In Review, Done, Blocked)
            priority: Priority field (Critical, High, Medium, Low)
            item_type: Type field (Epic, User Story, Task, Bug, Technical Debt)
            project: Project field
            name: Name/Title field
            description: Description field
            latest_status: Latest Status field (progress updates)
            content: Page body content (markdown). Replaces existing content.

        Returns:
            Dict with page_id, updated_properties, content_updated
        """
        try:
            client = get_notion_client()
            page_id = parse_id(page_id)

            # Build properties to update
            properties = {}

            if status:
                properties["Status"] = {"status": {"name": status}}
            if priority:
                properties["Priority"] = {"select": {"name": priority}}
            if item_type:
                properties["Type"] = {"select": {"name": item_type}}
            if project:
                properties["Project"] = {"select": {"name": project}}
            if name:
                properties["Name"] = {"title": [{"text": {"content": name}}]}
            if description:
                properties["Description"] = {"rich_text": [{"text": {"content": description}}]}
            if latest_status:
                properties["Latest Status"] = {"rich_text": [{"text": {"content": latest_status}}]}

            result = {"page_id": page_id, "updated_properties": [], "content_updated": False}

            # Update properties if any
            if properties:
                await client.pages.update(page_id=page_id, properties=properties)
                result["updated_properties"] = list(properties.keys())

            # Replace content if provided
            if content:
                # Delete existing blocks
                existing_blocks = await client.blocks.children.list(block_id=page_id)
                for block in existing_blocks.get("results", []):
                    try:
                        await client.blocks.delete(block_id=block["id"])
                    except Exception:
                        pass

                # Add new content
                blocks = markdown_to_blocks(content)
                if blocks:
                    await client.blocks.children.append(block_id=page_id, children=blocks)
                result["content_updated"] = True
                result["blocks_added"] = len(blocks)

            return tools.create_response(
                status="success",
                action="notion_update_backlog_item",
                data=result
            )

        except APIResponseError as e:
            return tools.create_response(
                status="error",
                action="notion_update_backlog_item",
                data={"page_id": page_id},
                error_message=str(e),
                error_code=str(e.code) if hasattr(e, 'code') else None
            )
        except Exception as e:
            logger.error(f"Error in notion_update_backlog_item: {e}")
            return tools.create_response(
                status="error",
                action="notion_update_backlog_item",
                data={"page_id": page_id},
                error_message=str(e)
            )

    @mcp.tool()
    async def notion_list_databases(limit: int = 20) -> dict:
        """List all databases the integration has access to

        Args:
            limit: Maximum results (default: 20)

        Returns:
            Dict with databases list and count
        """
        try:
            client = get_notion_client()
            limit = min(limit, 100)

            # Note: Notion API no longer supports filter by "database" type
            # Search all and filter client-side
            results = await client.search(page_size=100)

            databases = []
            for db in results.get("results", []):
                if db.get("object") != "database":
                    continue
                if len(databases) >= limit:
                    break
                title = extract_text_from_rich_text(db.get("title", []))
                databases.append({
                    "id": db.get("id"),
                    "title": title or "Untitled Database",
                    "url": db.get("url")
                })

            return tools.create_response(
                status="success",
                action="notion_list_databases",
                data={"databases": databases, "count": len(databases)}
            )

        except APIResponseError as e:
            return tools.create_response(
                status="error",
                action="notion_list_databases",
                data={},
                error_message=str(e),
                error_code=str(e.code) if hasattr(e, 'code') else None
            )
        except Exception as e:
            logger.error(f"Error in notion_list_databases: {e}")
            return tools.create_response(
                status="error",
                action="notion_list_databases",
                data={},
                error_message=str(e)
            )

    @mcp.tool()
    async def notion_create_database(
        parent_page_id: str,
        title: str,
        properties: dict
    ) -> dict:
        """Create a new database as a child of a page

        Args:
            parent_page_id: Parent page ID where database will be created
            title: Database title
            properties: Database schema properties definition

        Returns:
            Dict with created, id, title, url, properties
        """
        try:
            client = get_notion_client()
            parent_page_id = parse_id(parent_page_id)

            # Build Notion properties schema
            notion_properties = {
                "Name": {"title": {}}  # Title property is required
            }

            for prop_name, prop_def in properties.items():
                if prop_name == "Name":
                    continue  # Skip, already added as title

                prop_type = prop_def.get("type", "rich_text")

                if prop_type == "select":
                    options = prop_def.get("options", [])
                    notion_properties[prop_name] = {
                        "select": {
                            "options": [{"name": opt, "color": "default"} for opt in options]
                        }
                    }
                elif prop_type == "multi_select":
                    options = prop_def.get("options", [])
                    notion_properties[prop_name] = {
                        "multi_select": {
                            "options": [{"name": opt, "color": "default"} for opt in options]
                        }
                    }
                elif prop_type == "status":
                    options = prop_def.get("options", ["Not Started", "In Progress", "Done"])
                    notion_properties[prop_name] = {
                        "status": {
                            "options": [{"name": opt, "color": "default"} for opt in options]
                        }
                    }
                elif prop_type == "date":
                    notion_properties[prop_name] = {"date": {}}
                elif prop_type == "checkbox":
                    notion_properties[prop_name] = {"checkbox": {}}
                elif prop_type == "number":
                    notion_properties[prop_name] = {"number": {"format": prop_def.get("format", "number")}}
                elif prop_type == "url":
                    notion_properties[prop_name] = {"url": {}}
                elif prop_type == "email":
                    notion_properties[prop_name] = {"email": {}}
                elif prop_type == "relation":
                    notion_properties[prop_name] = {
                        "relation": {
                            "database_id": prop_def.get("database_id", ""),
                            "single_property": {}
                        }
                    }
                else:  # Default to rich_text
                    notion_properties[prop_name] = {"rich_text": {}}

            db = await client.databases.create(
                parent={"page_id": parent_page_id},
                title=[{"type": "text", "text": {"content": title}}],
                properties=notion_properties
            )

            return tools.create_response(
                status="success",
                action="notion_create_database",
                data={
                    "created": True,
                    "id": db.get("id"),
                    "title": title,
                    "url": db.get("url"),
                    "properties": list(notion_properties.keys())
                }
            )

        except APIResponseError as e:
            return tools.create_response(
                status="error",
                action="notion_create_database",
                data={"parent_page_id": parent_page_id, "title": title},
                error_message=str(e),
                error_code=str(e.code) if hasattr(e, 'code') else None
            )
        except Exception as e:
            logger.error(f"Error in notion_create_database: {e}")
            return tools.create_response(
                status="error",
                action="notion_create_database",
                data={"parent_page_id": parent_page_id, "title": title},
                error_message=str(e)
            )

    @mcp.tool()
    async def notion_list_users() -> dict:
        """List workspace users

        Returns:
            Dict with users list and count
        """
        try:
            client = get_notion_client()
            results = await client.users.list()

            users = []
            for user in results.get("results", []):
                users.append({
                    "id": user.get("id"),
                    "name": user.get("name"),
                    "type": user.get("type"),
                    "email": user.get("person", {}).get("email") if user.get("type") == "person" else None
                })

            return tools.create_response(
                status="success",
                action="notion_list_users",
                data={"users": users, "count": len(users)}
            )

        except APIResponseError as e:
            return tools.create_response(
                status="error",
                action="notion_list_users",
                data={},
                error_message=str(e),
                error_code=str(e.code) if hasattr(e, 'code') else None
            )
        except Exception as e:
            logger.error(f"Error in notion_list_users: {e}")
            return tools.create_response(
                status="error",
                action="notion_list_users",
                data={},
                error_message=str(e)
            )

    logger.debug("Registered 13 Notion tools")
