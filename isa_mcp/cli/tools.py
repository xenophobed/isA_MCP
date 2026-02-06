"""
Tool discovery and execution commands for isA MCP CLI.

Commands:
    isa_mcp tools discover <query>   Search for tools
    isa_mcp tools list               List all tools
    isa_mcp tools defaults           List default tools (meta-tools)
    isa_mcp tools schema <name>      Get tool schema
    isa_mcp tools execute <name>     Execute a tool
    isa_mcp tools aggregated         List tools from external MCP servers
"""
import asyncio
import json
import sys
from typing import Optional

import click


def run_async(coro):
    """Run async coroutine in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# =========================================================================
# Tools Command Group
# =========================================================================

@click.group()
def tools():
    """Discover and manage MCP tools."""
    pass


@tools.command("discover")
@click.argument("query")
@click.option("--type", "-t", "item_type",
              type=click.Choice(["all", "tools", "prompts", "resources", "skills"]),
              default="all", help="Item type to search")
@click.option("--limit", "-n", default=10, help="Maximum results")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def tools_discover(query: str, item_type: str, limit: int, as_json: bool):
    """
    Search for tools, prompts, resources, or skills.

    Uses semantic search to find relevant items across all MCP entities.

    \b
    Examples:
      isa_mcp tools discover "video creation"
      isa_mcp tools discover "calendar" --type tools
      isa_mcp tools discover "authentication" --limit 20
    """
    click.echo(f"Searching for: {click.style(query, fg='cyan')}\n")

    async def do_discover():
        try:
            from services.search_service.hierarchical_search_service import HierarchicalSearchService
            service = HierarchicalSearchService()
            return await service.search(
                query=query,
                item_type=None if item_type == "all" else item_type,
                limit=limit
            )
        except ImportError:
            # Fallback to basic tool listing
            from tools.meta_tools.discovery_tools import discover
            return await discover(query=query, item_type=item_type, limit=limit)

    try:
        results = run_async(do_discover())

        if as_json:
            click.echo(json.dumps(results, indent=2, default=str))
            return

        if not results or not results.get("items"):
            click.echo(click.style("No results found.", fg="yellow"))
            return

        items = results.get("items", [])
        click.echo(click.style(f"Found {len(items)} results:\n", fg="green"))

        for item in items:
            item_type_str = item.get("type", "unknown")
            name = item.get("name", "unnamed")
            desc = item.get("description", "No description")
            score = item.get("score", 0)

            type_color = {
                "tool": "green",
                "prompt": "blue",
                "resource": "magenta",
                "skill": "cyan",
            }.get(item_type_str, "white")

            click.echo(f"  [{click.style(item_type_str, fg=type_color)}] {click.style(name, bold=True)}")
            click.echo(f"    {desc[:70]}{'...' if len(desc) > 70 else ''}")
            if score:
                click.echo(f"    Score: {score:.2f}")
            click.echo()

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)


@tools.command("list")
@click.option("--category", "-c", default=None, help="Filter by skill category")
@click.option("--limit", "-n", default=50, help="Maximum results")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def tools_list(category: Optional[str], limit: int, as_json: bool):
    """
    List all available tools.

    \b
    Examples:
      isa_mcp tools list
      isa_mcp tools list --category calendar-events
      isa_mcp tools list --json
    """
    async def do_list():
        try:
            from services.tool_service.tool_repository import ToolRepository
            repo = ToolRepository()
            return await repo.list_tools(
                category=category,
                limit=limit
            )
        except ImportError:
            # Fallback to meta-tools
            from tools.meta_tools.discovery_tools import discover
            result = await discover(query="", item_type="tools", limit=limit)
            return result.get("items", [])

    try:
        tools_list = run_async(do_list())

        if as_json:
            click.echo(json.dumps(tools_list, indent=2, default=str))
            return

        if not tools_list:
            click.echo(click.style("No tools found.", fg="yellow"))
            return

        click.echo(click.style(f"Available tools ({len(tools_list)}):\n", fg="cyan", bold=True))

        # Group by category if available
        by_category = {}
        for t in tools_list:
            cat = t.get("primary_skill", "uncategorized")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(t)

        for cat, cat_tools in sorted(by_category.items()):
            click.echo(click.style(f"  [{cat}]", fg="blue", bold=True))
            for t in cat_tools[:10]:  # Limit per category
                name = t.get("name", "unnamed")
                desc = t.get("description", "")[:50]
                click.echo(f"    {click.style(name, fg='green')}: {desc}")
            if len(cat_tools) > 10:
                click.echo(f"    ... and {len(cat_tools) - 10} more")
            click.echo()

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)


@tools.command("schema")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def tools_schema(name: str, as_json: bool):
    """
    Get the full schema for a tool.

    \b
    Example:
      isa_mcp tools schema create_calendar_event
    """
    async def do_get_schema():
        try:
            from tools.meta_tools.discovery_tools import get_tool_schema
            return await get_tool_schema(tool_name=name)
        except ImportError:
            from services.tool_service.tool_repository import ToolRepository
            repo = ToolRepository()
            return await repo.get_tool_schema(name)

    try:
        schema = run_async(do_get_schema())

        if not schema:
            click.echo(click.style(f"Tool '{name}' not found.", fg="yellow"))
            click.echo(f"\nSearch for it: isa_mcp tools discover {name}")
            return

        if as_json:
            click.echo(json.dumps(schema, indent=2))
            return

        click.echo(click.style(f"Tool: {name}", fg="cyan", bold=True))
        click.echo("─" * 50)
        click.echo(f"Description: {schema.get('description', 'No description')}")
        click.echo()

        # Input schema
        input_schema = schema.get("inputSchema", schema.get("input_schema", {}))
        if input_schema:
            click.echo(click.style("Parameters:", fg="blue", bold=True))
            properties = input_schema.get("properties", {})
            required = input_schema.get("required", [])

            for prop_name, prop_def in properties.items():
                req_str = click.style("*", fg="red") if prop_name in required else " "
                prop_type = prop_def.get("type", "any")
                prop_desc = prop_def.get("description", "")
                click.echo(f"  {req_str} {click.style(prop_name, fg='green')} ({prop_type})")
                if prop_desc:
                    click.echo(f"      {prop_desc[:60]}")

        click.echo()
        click.echo(click.style("Execute with:", fg="blue"))
        click.echo(f"  isa_mcp tools execute {name} --params '{{\"key\": \"value\"}}'")

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)


@tools.command("execute")
@click.argument("name")
@click.option("--params", "-p", default="{}", help="Tool parameters as JSON")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def tools_execute(name: str, params: str, as_json: bool):
    """
    Execute a tool by name.

    \b
    Examples:
      isa_mcp tools execute list_calendar_events
      isa_mcp tools execute create_calendar_event --params '{"title": "Meeting"}'
    """
    # Parse params
    try:
        params_dict = json.loads(params)
    except json.JSONDecodeError as e:
        click.echo(click.style(f"Invalid JSON parameters: {e}", fg="red"))
        sys.exit(1)

    click.echo(f"Executing: {click.style(name, fg='cyan')}")
    if params_dict:
        click.echo(f"Parameters: {json.dumps(params_dict)}")
    click.echo()

    async def do_execute():
        try:
            from tools.meta_tools.discovery_tools import execute
            return await execute(tool_name=name, params=params_dict)
        except ImportError:
            click.echo(click.style("Error: Tool execution requires full MCP environment", fg="red"))
            sys.exit(1)

    try:
        result = run_async(do_execute())

        if as_json:
            click.echo(json.dumps(result, indent=2, default=str))
            return

        if isinstance(result, dict):
            if result.get("error"):
                click.echo(click.style(f"✗ Error: {result['error']}", fg="red"))
                sys.exit(1)
            else:
                click.echo(click.style("✓ Execution successful!", fg="green"))
                click.echo()
                click.echo(json.dumps(result, indent=2, default=str))
        else:
            click.echo(click.style("✓ Execution successful!", fg="green"))
            click.echo()
            click.echo(str(result))

    except Exception as e:
        click.echo(click.style(f"✗ Execution failed: {e}", fg="red"))
        sys.exit(1)


@tools.command("defaults")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def tools_defaults(as_json: bool):
    """
    List default tools (meta-tools always available).

    Default tools are gateway tools for accessing all other capabilities:
    - discover, get_tool_schema, execute
    - list_skills, list_prompts, get_prompt, list_resources, read_resource

    \b
    Example:
      isa_mcp tools defaults
    """
    async def do_list():
        try:
            from services.tool_service.tool_service import ToolService
            service = ToolService()
            return await service.get_default_tools()
        except ImportError:
            # Fallback to HTTP API
            from isa_mcp.mcp_client import AsyncMCPClient
            async with AsyncMCPClient() as client:
                return await client.get_default_tools()

    try:
        default_tools = run_async(do_list())

        if as_json:
            click.echo(json.dumps(default_tools, indent=2, default=str))
            return

        if not default_tools:
            click.echo(click.style("No default tools found.", fg="yellow"))
            click.echo("\nRun migration and sync to populate default tools.")
            return

        click.echo(click.style(f"Default tools ({len(default_tools)}):\n", fg="cyan", bold=True))

        for t in default_tools:
            name = t.get("name", "unnamed")
            desc = t.get("description", "")[:60]
            click.echo(f"  {click.style(name, fg='green', bold=True)}")
            click.echo(f"    {desc}")
            click.echo()

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)


@tools.command("aggregated")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def tools_aggregated(as_json: bool):
    """
    List tools from all aggregated external MCP servers.

    Example:
      isa_mcp tools aggregated
    """
    async def do_list():
        try:
            from services.aggregator_service.aggregator_service import AggregatorService
            service = AggregatorService()
            return await service.list_all_aggregated_tools()
        except ImportError:
            return []

    try:
        tools_list = run_async(do_list())

        if as_json:
            click.echo(json.dumps(tools_list, indent=2))
            return

        if not tools_list:
            click.echo(click.style("No aggregated tools found.", fg="yellow"))
            click.echo("\nAdd external MCP servers with:")
            click.echo("  isa_mcp server add my-server --url http://localhost:8082")
            return

        click.echo(click.style(f"Aggregated tools ({len(tools_list)}):\n", fg="cyan", bold=True))

        # Group by server
        by_server = {}
        for t in tools_list:
            server = t.get("server_name", "unknown")
            if server not in by_server:
                by_server[server] = []
            by_server[server].append(t)

        for server, server_tools in sorted(by_server.items()):
            click.echo(click.style(f"  [{server}]", fg="blue", bold=True))
            for t in server_tools:
                name = t.get("name", "unnamed")
                desc = t.get("description", "")[:50]
                click.echo(f"    {click.style(name, fg='green')}: {desc}")
            click.echo()

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)
