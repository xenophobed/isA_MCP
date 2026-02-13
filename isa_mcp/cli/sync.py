"""
Sync and resync commands for isA MCP CLI.

Commands:
    isa_mcp sync              Full sync of tools/prompts/resources to DB
    isa_mcp sync tools        Sync only tools
    isa_mcp sync prompts      Sync only prompts
    isa_mcp sync resources    Sync only resources
    isa_mcp sync skills       Sync skill categories
"""

import asyncio
import os
import sys
from typing import Optional

import click
import httpx


def run_async(coro):
    """Run async coroutine in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def get_mcp_server_url():
    """Get the MCP server URL from environment or default."""
    host = os.getenv("MCP_HOST", "localhost")
    port = os.getenv("MCP_PORT", "8081")
    return f"http://{host}:{port}"


async def call_sync_endpoint(url: str):
    """Call the /sync endpoint on the running MCP server."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(f"{url}/sync")
        response.raise_for_status()
        return response.json()


# =========================================================================
# Sync Command Group
# =========================================================================


@click.command()
@click.option("--url", "-u", default=None, help="MCP server URL (default: http://localhost:8081)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def sync(url: Optional[str], verbose: bool):
    """
    Sync tools, prompts, resources, and skills to PostgreSQL + Qdrant.

    This command calls the /sync endpoint on the running MCP server to
    synchronize all discovered MCP items to the database and generate
    vector embeddings for semantic search.

    The sync is INCREMENTAL - it only updates new/changed items.

    \b
    Examples:
      isa_mcp sync                              # Sync via localhost:8081
      isa_mcp sync --url http://localhost:8082  # Custom server URL
    """
    server_url = url or get_mcp_server_url()

    click.echo(click.style("Starting synchronization...", fg="cyan", bold=True))
    click.echo(f"  Server: {server_url}")
    click.echo(f"  Mode:   Incremental (only new/changed items)")
    click.echo()

    async def do_sync():
        return await call_sync_endpoint(server_url)

    try:
        click.echo("  Calling /sync endpoint...")
        result = run_async(do_sync())

        if result.get("status") == "success":
            click.echo()
            click.echo(click.style("✓ Synchronization complete!", fg="green"))

            # Show results
            if verbose:
                click.echo(f"\n  Results:")
                click.echo(f"    Total synced: {result.get('total_synced', 0)}")
                click.echo(f"    Total failed: {result.get('total_failed', 0)}")

                if result.get("tools"):
                    t = result["tools"]
                    click.echo(
                        f"    Tools:     {t.get('total', 0)} total, {t.get('synced', 0)} synced"
                    )

                if result.get("prompts"):
                    p = result["prompts"]
                    click.echo(
                        f"    Prompts:   {p.get('total', 0)} total, {p.get('synced', 0)} synced"
                    )

                if result.get("resources"):
                    r = result["resources"]
                    click.echo(
                        f"    Resources: {r.get('total', 0)} total, {r.get('synced', 0)} synced"
                    )

                if result.get("skills"):
                    s = result["skills"]
                    click.echo(f"    Skills:    {s.get('total', 0)} categories")
            else:
                click.echo(f"  Synced: {result.get('total_synced', 0)} items")
        else:
            click.echo(
                click.style(f"✗ Sync failed: {result.get('message', 'Unknown error')}", fg="red")
            )
            sys.exit(1)

    except httpx.ConnectError:
        click.echo(click.style(f"\n✗ Cannot connect to MCP server at {server_url}", fg="red"))
        click.echo("  Make sure the MCP server is running:")
        click.echo(f"    cd /path/to/isA_MCP && python main.py --port 8081")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        click.echo(click.style(f"\n✗ HTTP error: {e.response.status_code}", fg="red"))
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"\n✗ Sync failed: {e}", fg="red"))
        if verbose:
            import traceback

            click.echo(traceback.format_exc())
        sys.exit(1)


# Note: Selective resync commands removed - use `isa_mcp sync` which calls
# the running MCP server's /sync endpoint for incremental sync.
