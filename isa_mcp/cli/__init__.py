"""
isA MCP CLI - Comprehensive command line interface for MCP management.

Usage:
    isa_mcp skill install <name>       Install a skill from npm or GitHub
    isa_mcp skill list                 List installed skills
    isa_mcp server add <name>          Add external MCP server
    isa_mcp server list                List connected servers
    isa_mcp sync                       Sync tools/prompts/resources
    isa_mcp tools discover <query>     Search for tools
    isa_mcp marketplace search <q>     Search MCP packages

Run 'isa_mcp --help' for full command list.
"""

import sys
from pathlib import Path

import click

# Add parent directories to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =========================================================================
# Main CLI Group
# =========================================================================


@click.group()
@click.version_option(version="1.0.0", prog_name="isa-mcp")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, verbose):
    """
    isA MCP - AI-powered Model Context Protocol management.

    Manage skills, external MCP servers, tools, and more.

    \b
    Quick Start:
      isa_mcp skill search video          Search for video skills
      isa_mcp skill install remotion-dev/skills
      isa_mcp server add my-server --url http://localhost:8082
      isa_mcp sync                        Sync all tools and resources
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["project_root"] = PROJECT_ROOT


# =========================================================================
# Import and Register Command Groups
# =========================================================================


def register_commands():
    """Register all command groups."""
    from isa_mcp.cli.skills import skill
    from isa_mcp.cli.servers import server
    from isa_mcp.cli.sync import sync
    from isa_mcp.cli.tools import tools
    from isa_mcp.cli.marketplace import marketplace
    from isa_mcp.cli.config import config

    cli.add_command(skill)
    cli.add_command(server)
    cli.add_command(sync)
    cli.add_command(tools)
    cli.add_command(marketplace)
    cli.add_command(config)


# =========================================================================
# Quick Shortcut Commands
# =========================================================================


@cli.command("install")
@click.argument("name")
@click.option("--version", "-v", default=None, help="Specific version")
@click.pass_context
def quick_install(ctx, name: str, version: str):
    """
    Quick install a skill (shortcut for 'skill install').

    Example:
      isa_mcp install remotion-dev/skills
    """
    from isa_mcp.cli.skills import skill_install

    ctx.invoke(skill_install, name=name, version=version, source="auto", force=False)


@cli.command("search")
@click.argument("query")
@click.pass_context
def quick_search(ctx, query: str):
    """
    Quick search for skills (shortcut for 'skill search').

    Example:
      isa_mcp search video
    """
    from isa_mcp.cli.skills import skill_search

    ctx.invoke(skill_search, query=query, source="all", limit=10)


# =========================================================================
# Entry Point
# =========================================================================


def main():
    """Main entry point for CLI."""
    register_commands()
    cli()


if __name__ == "__main__":
    main()
