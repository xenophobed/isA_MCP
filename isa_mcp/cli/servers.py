"""
External MCP server management commands for isA MCP CLI.

Commands:
    isa_mcp server add <name>       Add/register external MCP server
    isa_mcp server remove <name>    Remove external MCP server
    isa_mcp server list             List connected servers
    isa_mcp server health <name>    Check server health
    isa_mcp server tools <name>     List tools from a server
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


def get_aggregator_service():
    """Get AggregatorService instance."""
    try:
        from services.aggregator_service.aggregator_service import AggregatorService

        return AggregatorService()
    except ImportError as e:
        click.echo(click.style(f"Error: Could not import AggregatorService: {e}", fg="red"))
        click.echo("This command requires the full isA MCP environment.")
        sys.exit(1)


def do_sync_tools(verbose: bool = False):
    """Sync tools to database and generate embeddings."""
    try:
        from services.sync_service.sync_service import SyncService
    except ImportError:
        if verbose:
            click.echo(click.style("  Sync skipped: SyncService not available", fg="yellow"))
        return None

    async def _sync():
        service = SyncService()
        return await service.sync_tools()

    try:
        result = run_async(_sync())
        return result
    except Exception as e:
        if verbose:
            click.echo(click.style(f"  Sync warning: {e}", fg="yellow"))
        return None


# =========================================================================
# Server Command Group
# =========================================================================


@click.group()
def server():
    """Manage external MCP servers."""
    pass


@server.command("add")
@click.argument("name")
@click.option("--url", "-u", required=True, help="Server URL (e.g., http://localhost:8082)")
@click.option(
    "--transport",
    "-t",
    type=click.Choice(["sse", "stdio", "http"], case_sensitive=False),
    default="sse",
    help="Transport type (default: sse)",
)
@click.option("--command", "-c", default=None, help="Command for stdio transport")
@click.option("--args", "-a", default=None, help="Args for stdio transport (JSON array)")
@click.option("--env", "-e", multiple=True, help="Environment variables (KEY=VALUE)")
@click.option("--auto-connect/--no-auto-connect", default=True, help="Auto-connect after adding")
@click.option("--sync/--no-sync", default=True, help="Auto-sync tools after adding (default: sync)")
def server_add(
    name: str,
    url: str,
    transport: str,
    command: Optional[str],
    args: Optional[str],
    env: tuple,
    auto_connect: bool,
    sync: bool,
):
    """
    Add/register an external MCP server.

    \b
    Examples:
      # SSE transport (default)
      isa_mcp server add my-server --url http://localhost:8082

      # stdio transport
      isa_mcp server add local-tool \\
        --transport stdio \\
        --command python \\
        --args '["-m", "my_mcp_server"]'

      # With environment variables
      isa_mcp server add api-server \\
        --url http://api.example.com \\
        -e API_KEY=xxx -e DEBUG=true

      # Skip auto-sync for batch operations
      isa_mcp server add server1 --url http://localhost:8082 --no-sync
    """
    click.echo(f"Adding MCP server: {click.style(name, fg='cyan')}")

    # Build config
    config = {"url": url}

    if transport == "stdio":
        if not command:
            click.echo(click.style("Error: --command required for stdio transport", fg="red"))
            sys.exit(1)
        config["command"] = command
        if args:
            try:
                config["args"] = json.loads(args)
            except json.JSONDecodeError:
                click.echo(click.style("Error: --args must be valid JSON array", fg="red"))
                sys.exit(1)

    # Parse environment variables
    if env:
        config["env"] = {}
        for e in env:
            if "=" in e:
                key, value = e.split("=", 1)
                config["env"][key] = value

    async def do_add():
        service = get_aggregator_service()
        result = await service.register_server(
            name=name, transport_type=transport.upper(), config=config, auto_connect=auto_connect
        )
        return result

    try:
        result = run_async(do_add())

        if result.get("success"):
            click.echo(click.style("✓ Server added successfully!", fg="green"))
            click.echo(f"  Name:      {name}")
            click.echo(f"  URL:       {url}")
            click.echo(f"  Transport: {transport}")
            if auto_connect:
                click.echo(f"  Status:    Connected")
                tools = result.get("tools_count", 0)
                click.echo(f"  Tools:     {tools} discovered")

            # Auto-sync if enabled and tools were discovered
            if sync and auto_connect and result.get("tools_count", 0) > 0:
                click.echo(f"\n{click.style('Syncing tools...', fg='cyan')}")
                sync_result = do_sync_tools(verbose=True)
                if sync_result:
                    click.echo(click.style("✓ Tools synced to database", fg="green"))
        else:
            click.echo(click.style(f"✗ Failed to add server: {result.get('error')}", fg="red"))
            sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)


@server.command("remove")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def server_remove(name: str, yes: bool):
    """
    Remove an external MCP server.

    Example:
      isa_mcp server remove my-server
    """
    if not yes:
        click.confirm(f"Remove server '{name}'?", abort=True)

    async def do_remove():
        service = get_aggregator_service()
        return await service.deregister_server(name)

    try:
        success = run_async(do_remove())

        if success:
            click.echo(click.style(f"✓ Server '{name}' removed", fg="green"))
        else:
            click.echo(click.style(f"✗ Server '{name}' not found", fg="yellow"))
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)


@server.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed info")
def server_list(as_json: bool, verbose: bool):
    """
    List connected external MCP servers.

    Examples:
      isa_mcp server list
      isa_mcp server list --json
      isa_mcp server list -v
    """

    async def do_list():
        service = get_aggregator_service()
        return await service.list_servers()

    try:
        servers = run_async(do_list())

        if as_json:
            click.echo(json.dumps(servers, indent=2, default=str))
            return

        if not servers:
            click.echo(click.style("No external MCP servers registered.", fg="yellow"))
            click.echo("\nAdd a server with:")
            click.echo("  isa_mcp server add my-server --url http://localhost:8082")
            return

        click.echo(click.style(f"External MCP servers ({len(servers)}):\n", fg="cyan", bold=True))

        for s in servers:
            status_color = "green" if s.get("connected") else "red"
            status_text = "Connected" if s.get("connected") else "Disconnected"

            click.echo(f"  {click.style(s['name'], fg='green', bold=True)}")
            click.echo(f"    URL:       {s.get('url', 'N/A')}")
            click.echo(f"    Transport: {s.get('transport_type', 'unknown')}")
            click.echo(f"    Status:    {click.style(status_text, fg=status_color)}")
            click.echo(f"    Tools:     {s.get('tools_count', 0)}")

            if verbose:
                click.echo(f"    Added:     {s.get('registered_at', 'N/A')}")
                click.echo(f"    Last ping: {s.get('last_health_check', 'N/A')}")
                if s.get("failures"):
                    click.echo(f"    Failures:  {s.get('consecutive_failures', 0)}")
            click.echo()

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)


@server.command("health")
@click.argument("name")
def server_health(name: str):
    """
    Check health of an external MCP server.

    Example:
      isa_mcp server health my-server
    """

    async def do_health():
        service = get_aggregator_service()
        return await service.health_check(name)

    try:
        result = run_async(do_health())

        if result.get("healthy"):
            click.echo(click.style(f"✓ Server '{name}' is healthy", fg="green"))
            click.echo(f"  Response time: {result.get('response_time_ms', 'N/A')}ms")
            click.echo(f"  Tools:         {result.get('tools_count', 0)}")
        else:
            click.echo(click.style(f"✗ Server '{name}' is unhealthy", fg="red"))
            click.echo(f"  Error: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)


@server.command("tools")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def server_tools(name: str, as_json: bool):
    """
    List tools from a specific external MCP server.

    Example:
      isa_mcp server tools my-server
    """

    async def do_list_tools():
        service = get_aggregator_service()
        return await service.list_server_tools(name)

    try:
        tools = run_async(do_list_tools())

        if as_json:
            click.echo(json.dumps(tools, indent=2))
            return

        if not tools:
            click.echo(click.style(f"No tools found on server '{name}'", fg="yellow"))
            return

        click.echo(click.style(f"Tools from '{name}' ({len(tools)}):\n", fg="cyan", bold=True))

        for t in tools:
            click.echo(f"  {click.style(t['name'], fg='green')}")
            desc = t.get("description", "No description")
            click.echo(f"    {desc[:70]}{'...' if len(desc) > 70 else ''}")

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)


@server.command("connect")
@click.argument("name")
def server_connect(name: str):
    """
    Connect to a registered MCP server.

    Example:
      isa_mcp server connect my-server
    """

    async def do_connect():
        service = get_aggregator_service()
        return await service.connect_server(name)

    try:
        result = run_async(do_connect())

        if result.get("success"):
            click.echo(click.style(f"✓ Connected to '{name}'", fg="green"))
            click.echo(f"  Tools discovered: {result.get('tools_count', 0)}")
        else:
            click.echo(click.style(f"✗ Failed to connect: {result.get('error')}", fg="red"))
            sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)


@server.command("disconnect")
@click.argument("name")
def server_disconnect(name: str):
    """
    Disconnect from a registered MCP server.

    Example:
      isa_mcp server disconnect my-server
    """

    async def do_disconnect():
        service = get_aggregator_service()
        return await service.disconnect_server(name)

    try:
        success = run_async(do_disconnect())

        if success:
            click.echo(click.style(f"✓ Disconnected from '{name}'", fg="green"))
        else:
            click.echo(click.style(f"✗ Failed to disconnect", fg="red"))
            sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)
