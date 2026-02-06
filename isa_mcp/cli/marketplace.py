"""
Marketplace commands for isA MCP CLI.

Commands:
    isa_mcp marketplace search <query>    Search for MCP packages
    isa_mcp marketplace install <name>    Install MCP package
    isa_mcp marketplace list              List installed packages
    isa_mcp marketplace update <name>     Update a package
    isa_mcp marketplace uninstall <name>  Uninstall a package
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


def get_marketplace_service():
    """Get MarketplaceService instance."""
    try:
        from services.marketplace_service.marketplace_service import MarketplaceService
        return MarketplaceService()
    except ImportError as e:
        click.echo(click.style(f"Error: Could not import MarketplaceService: {e}", fg="red"))
        click.echo("This command requires the full isA MCP environment.")
        sys.exit(1)


def do_sync_all(verbose: bool = False):
    """Sync tools, prompts, resources to database and generate embeddings."""
    try:
        from services.sync_service.sync_service import SyncService
    except ImportError:
        if verbose:
            click.echo(click.style("  Sync skipped: SyncService not available", fg="yellow"))
        return None

    async def _sync():
        service = SyncService()
        results = {}
        results["tools"] = await service.sync_tools()
        results["skills"] = await service.sync_skills()
        return results

    try:
        result = run_async(_sync())
        return result
    except Exception as e:
        if verbose:
            click.echo(click.style(f"  Sync warning: {e}", fg="yellow"))
        return None


# =========================================================================
# Marketplace Command Group
# =========================================================================

@click.group()
def marketplace():
    """Browse and install MCP packages from the marketplace."""
    pass


@marketplace.command("search")
@click.argument("query")
@click.option("--source", "-s",
              type=click.Choice(["all", "npm", "isa-cloud"], case_sensitive=False),
              default="all", help="Search source")
@click.option("--limit", "-n", default=20, help="Maximum results")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def marketplace_search(query: str, source: str, limit: int, as_json: bool):
    """
    Search for MCP packages in the marketplace.

    Searches npm registry and isA Cloud for MCP-compatible packages.

    \b
    Examples:
      isa_mcp marketplace search video
      isa_mcp marketplace search "notion integration" --source npm
      isa_mcp marketplace search calendar --limit 5
    """
    click.echo(f"Searching marketplace for: {click.style(query, fg='cyan')}\n")

    async def do_search():
        service = get_marketplace_service()
        return await service.search_packages(
            query=query,
            source=None if source == "all" else source,
            limit=limit
        )

    try:
        results = run_async(do_search())

        if as_json:
            click.echo(json.dumps(results, indent=2, default=str))
            return

        if not results:
            click.echo(click.style("No packages found.", fg="yellow"))
            click.echo("\nTry different keywords or check:")
            click.echo("  - npm packages with 'mcp-server' or 'claude-skill' keywords")
            return

        click.echo(click.style(f"Found {len(results)} packages:\n", fg="green"))

        for pkg in results:
            name = pkg.get("name", "unnamed")
            desc = pkg.get("description", "No description")
            version = pkg.get("version", "")
            source_str = pkg.get("source", "unknown")
            downloads = pkg.get("downloads", 0)

            source_color = "blue" if source_str == "npm" else "magenta"

            click.echo(f"  {click.style(name, fg='green', bold=True)} {click.style(f'v{version}', fg='white')}")
            click.echo(f"    {desc[:70]}{'...' if len(desc) > 70 else ''}")
            click.echo(f"    Source: {click.style(source_str, fg=source_color)} | Downloads: {downloads:,}")
            click.echo(f"    Install: isa_mcp marketplace install {name}")
            click.echo()

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)


@marketplace.command("install")
@click.argument("name")
@click.option("--version", "-v", default=None, help="Specific version")
@click.option("--auto-configure/--no-auto-configure", default=True,
              help="Auto-configure as MCP server")
@click.option("--classify/--no-classify", default=True,
              help="Auto-classify tools into skills")
@click.option("--sync/--no-sync", default=True, help="Auto-sync after install (default: sync)")
def marketplace_install(name: str, version: Optional[str], auto_configure: bool,
                        classify: bool, sync: bool):
    """
    Install an MCP package from the marketplace.

    \b
    Examples:
      isa_mcp marketplace install @modelcontextprotocol/server-filesystem
      isa_mcp marketplace install mcp-server-notion --version 1.2.0
      isa_mcp marketplace install my-mcp-server --no-auto-configure
      isa_mcp marketplace install pkg1 --no-sync  # Skip auto-sync
    """
    click.echo(f"Installing package: {click.style(name, fg='cyan')}")
    if version:
        click.echo(f"Version: {version}")

    async def do_install():
        service = get_marketplace_service()
        return await service.install_package(
            name=name,
            version=version,
            auto_configure=auto_configure,
            auto_classify=classify
        )

    try:
        with click.progressbar(length=100, label="Installing") as bar:
            bar.update(20)
            result = run_async(do_install())
            bar.update(80)

        if result.get("success"):
            click.echo(click.style("\n✓ Package installed successfully!", fg="green"))
            click.echo(f"  Name:    {result.get('name')}")
            click.echo(f"  Version: {result.get('version')}")
            click.echo(f"  Path:    {result.get('install_path')}")

            if result.get("tools_count"):
                click.echo(f"  Tools:   {result.get('tools_count')} discovered")

            if auto_configure and result.get("server_configured"):
                click.echo(click.style("\n  Server auto-configured!", fg="cyan"))
                click.echo(f"  Run: isa_mcp server list")

            # Auto-sync if enabled
            if sync and result.get("tools_count", 0) > 0:
                click.echo(f"\n{click.style('Syncing to database...', fg='cyan')}")
                sync_result = do_sync_all(verbose=True)
                if sync_result:
                    tools_synced = sync_result.get("tools", {}).get("total", 0)
                    click.echo(click.style(f"✓ Synced ({tools_synced} tools)", fg="green"))
        else:
            click.echo(click.style(f"\n✗ Installation failed: {result.get('error')}", fg="red"))
            sys.exit(1)

    except Exception as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg="red"))
        sys.exit(1)


@marketplace.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def marketplace_list(as_json: bool):
    """
    List installed MCP packages.

    Example:
      isa_mcp marketplace list
    """
    async def do_list():
        service = get_marketplace_service()
        return await service.list_installed_packages()

    try:
        packages = run_async(do_list())

        if as_json:
            click.echo(json.dumps(packages, indent=2, default=str))
            return

        if not packages:
            click.echo(click.style("No packages installed.", fg="yellow"))
            click.echo("\nInstall packages with:")
            click.echo("  isa_mcp marketplace search notion")
            click.echo("  isa_mcp marketplace install <package-name>")
            return

        click.echo(click.style(f"Installed packages ({len(packages)}):\n", fg="cyan", bold=True))

        for pkg in packages:
            name = pkg.get("name", "unnamed")
            version = pkg.get("version", "unknown")
            status = pkg.get("status", "unknown")

            status_color = "green" if status == "active" else "yellow"

            click.echo(f"  {click.style(name, fg='green', bold=True)} v{version}")
            click.echo(f"    Status: {click.style(status, fg=status_color)}")
            click.echo(f"    Path:   {pkg.get('install_path', 'N/A')}")
            if pkg.get("tools_count"):
                click.echo(f"    Tools:  {pkg.get('tools_count')}")
            click.echo()

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)


@marketplace.command("update")
@click.argument("name")
@click.option("--version", "-v", default=None, help="Target version (default: latest)")
def marketplace_update(name: str, version: Optional[str]):
    """
    Update an installed MCP package.

    \b
    Examples:
      isa_mcp marketplace update mcp-server-notion
      isa_mcp marketplace update my-package --version 2.0.0
    """
    target = version or "latest"
    click.echo(f"Updating {click.style(name, fg='cyan')} to {target}...")

    async def do_update():
        service = get_marketplace_service()
        return await service.update_package(name=name, version=version)

    try:
        result = run_async(do_update())

        if result.get("success"):
            click.echo(click.style("✓ Package updated!", fg="green"))
            click.echo(f"  Previous: v{result.get('previous_version')}")
            click.echo(f"  Current:  v{result.get('current_version')}")
        else:
            click.echo(click.style(f"✗ Update failed: {result.get('error')}", fg="red"))
            sys.exit(1)

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)


@marketplace.command("uninstall")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def marketplace_uninstall(name: str, yes: bool):
    """
    Uninstall an MCP package.

    Example:
      isa_mcp marketplace uninstall mcp-server-notion
    """
    if not yes:
        click.confirm(f"Uninstall package '{name}'?", abort=True)

    async def do_uninstall():
        service = get_marketplace_service()
        return await service.uninstall_package(name)

    try:
        success = run_async(do_uninstall())

        if success:
            click.echo(click.style(f"✓ Package '{name}' uninstalled", fg="green"))
        else:
            click.echo(click.style(f"✗ Package '{name}' not found", fg="yellow"))

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)


@marketplace.command("info")
@click.argument("name")
def marketplace_info(name: str):
    """
    Show detailed information about a marketplace package.

    Example:
      isa_mcp marketplace info @modelcontextprotocol/server-filesystem
    """
    async def do_info():
        service = get_marketplace_service()
        return await service.get_package_info(name)

    try:
        info = run_async(do_info())

        if not info:
            click.echo(click.style(f"Package '{name}' not found.", fg="yellow"))
            return

        click.echo(click.style(f"Package: {info.get('name')}", fg="cyan", bold=True))
        click.echo("─" * 50)
        click.echo(f"Version:     {info.get('version', 'unknown')}")
        click.echo(f"Description: {info.get('description', 'No description')}")
        click.echo(f"Author:      {info.get('author', 'Unknown')}")
        click.echo(f"License:     {info.get('license', 'Unknown')}")
        click.echo(f"Source:      {info.get('source', 'unknown')}")
        click.echo(f"Downloads:   {info.get('downloads', 0):,}")

        if info.get("homepage"):
            click.echo(f"Homepage:    {info.get('homepage')}")

        if info.get("repository"):
            click.echo(f"Repository:  {info.get('repository')}")

        click.echo()
        click.echo(f"Install: isa_mcp marketplace install {name}")

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)
