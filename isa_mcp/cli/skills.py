"""
Skill management commands for isA MCP CLI.

Commands:
    isa_mcp skill install <name>    Install skill from npm/GitHub
    isa_mcp skill uninstall <name>  Uninstall a skill
    isa_mcp skill list              List installed skills
    isa_mcp skill search <query>    Search for skills
    isa_mcp skill info <name>       Show skill details
    isa_mcp skill create            Create a new skill category
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click


def get_installer():
    """Get ExternalSkillInstaller instance."""
    try:
        from services.skill_service.external_skill_installer import (
            ExternalSkillInstaller,
            SkillSource,
            search_npm_skills,
            search_github_skills,
        )

        return ExternalSkillInstaller(), SkillSource, search_npm_skills, search_github_skills
    except ImportError as e:
        click.echo(click.style(f"Error: Could not import skill installer: {e}", fg="red"))
        click.echo("Make sure you're running from the isA MCP project directory.")
        sys.exit(1)


def run_async(coro):
    """Run async coroutine in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def do_sync_skills(verbose: bool = False):
    """Sync skills to database and generate embeddings."""
    try:
        from services.sync_service.sync_service import SyncService
    except ImportError:
        if verbose:
            click.echo(click.style("  Sync skipped: SyncService not available", fg="yellow"))
        return None

    async def _sync():
        service = SyncService()
        return await service.sync_skills()

    try:
        result = run_async(_sync())
        return result
    except Exception as e:
        if verbose:
            click.echo(click.style(f"  Sync warning: {e}", fg="yellow"))
        return None


# =========================================================================
# Skill Command Group
# =========================================================================


@click.group()
def skill():
    """Manage external skills for Claude Code."""
    pass


@skill.command("install")
@click.argument("name")
@click.option("--version", "-v", default=None, help="Specific version to install")
@click.option(
    "--source",
    "-s",
    type=click.Choice(["npm", "github", "auto"], case_sensitive=False),
    default="auto",
    help="Source registry (auto-detect by default)",
)
@click.option("--force", "-f", is_flag=True, help="Force reinstall if already exists")
@click.option("--sync/--no-sync", default=True, help="Auto-sync after install (default: sync)")
def skill_install(name: str, version: Optional[str], source: str, force: bool, sync: bool):
    """
    Install a skill from npm or GitHub.

    \b
    NAME can be:
      - npm package: claude-skill-video, @org/skill-name
      - GitHub repo: owner/repo, remotion-dev/skills

    \b
    Examples:
      isa_mcp skill install remotion-dev/skills
      isa_mcp skill install claude-skill-tdd --source npm
      isa_mcp skill install @anthropic/claude-skills -v 2.0.0
      isa_mcp skill install my-skill --no-sync  # Skip auto-sync
    """
    installer, SkillSource, _, _ = get_installer()

    click.echo(f"Installing skill: {click.style(name, fg='cyan')}")

    # Determine source
    skill_source = None
    if source != "auto":
        skill_source = SkillSource.NPM if source == "npm" else SkillSource.GITHUB

    # Check if already installed
    installed = installer.list_installed()
    sanitized_name = name.lstrip("@").replace("/", "-").lower()

    for s in installed:
        if s["name"] == sanitized_name:
            if not force:
                click.echo(click.style(f"Skill '{name}' is already installed.", fg="yellow"))
                click.echo("Use --force to reinstall.")
                return
            else:
                click.echo(f"Reinstalling {name}...")
                run_async(installer.uninstall(name))

    # Install
    async def do_install():
        result = await installer.install(name, version=version, source=skill_source)
        await installer.close()
        return result

    with click.progressbar(length=100, label="Downloading") as bar:
        bar.update(30)
        result = run_async(do_install())
        bar.update(70)

    if result.success:
        click.echo(click.style("\n✓ Installation successful!", fg="green"))
        click.echo(f"  Name:      {result.skill_name}")
        click.echo(f"  Version:   {result.version}")
        click.echo(f"  Source:    {result.source.value if result.source else 'unknown'}")
        click.echo(f"  Path:      {result.install_path}")
        click.echo(f"  Guides:    {result.guides_count}")
        click.echo(f"  Templates: {result.templates_count}")

        # Auto-sync if enabled
        if sync:
            click.echo(f"\n{click.style('Syncing...', fg='cyan')}")
            sync_result = do_sync_skills(verbose=True)
            if sync_result:
                click.echo(click.style("✓ Synced to database", fg="green"))
    else:
        click.echo(click.style(f"\n✗ Installation failed: {result.error}", fg="red"))
        sys.exit(1)


@skill.command("uninstall")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def skill_uninstall(name: str, yes: bool):
    """
    Uninstall a skill.

    Example:
      isa_mcp skill uninstall remotion-dev-skills
    """
    installer, _, _, _ = get_installer()

    # Check if installed
    installed = installer.list_installed()
    sanitized_name = name.lstrip("@").replace("/", "-").lower()

    found = None
    for s in installed:
        if s["name"] == sanitized_name or s["name"] == name:
            found = s
            break

    if not found:
        click.echo(click.style(f"Skill '{name}' is not installed.", fg="yellow"))
        return

    if not yes:
        click.confirm(f"Uninstall skill '{found['name']}'?", abort=True)

    async def do_uninstall():
        result = await installer.uninstall(found["name"])
        await installer.close()
        return result

    success = run_async(do_uninstall())

    if success:
        click.echo(click.style(f"✓ Uninstalled '{found['name']}'", fg="green"))
    else:
        click.echo(click.style(f"✗ Failed to uninstall '{name}'", fg="red"))
        sys.exit(1)


@skill.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def skill_list(as_json: bool):
    """
    List installed skills.

    Example:
      isa_mcp skill list
      isa_mcp skill list --json
    """
    installer, _, _, _ = get_installer()

    skills = installer.list_installed()

    if as_json:
        click.echo(json.dumps(skills, indent=2))
        return

    if not skills:
        click.echo(click.style("No external skills installed.", fg="yellow"))
        click.echo("\nInstall skills with:")
        click.echo("  isa_mcp skill install remotion-dev/skills")
        click.echo("  isa_mcp skill search video")
        return

    click.echo(click.style(f"Installed skills ({len(skills)}):\n", fg="cyan", bold=True))

    for s in skills:
        click.echo(f"  {click.style(s['name'], fg='green', bold=True)}")
        click.echo(f"    Version:     {s.get('version', 'unknown')}")
        desc = s.get("description", "No description")
        click.echo(f"    Description: {desc[:60]}{'...' if len(desc) > 60 else ''}")
        click.echo(f"    Guides:      {'Yes' if s.get('has_guides') else 'No'}")
        click.echo(f"    Templates:   {'Yes' if s.get('has_templates') else 'No'}")
        click.echo()


@skill.command("search")
@click.argument("query")
@click.option(
    "--source",
    "-s",
    type=click.Choice(["all", "npm", "github"], case_sensitive=False),
    default="all",
    help="Search source",
)
@click.option("--limit", "-n", default=10, help="Maximum results per source")
def skill_search(query: str, source: str, limit: int):
    """
    Search for skills on npm and GitHub.

    \b
    Examples:
      isa_mcp skill search video
      isa_mcp skill search "code generation" --source npm
      isa_mcp skill search remotion --limit 5
    """
    _, _, search_npm, search_github = get_installer()

    click.echo(f"Searching for: {click.style(query, fg='cyan')}\n")

    async def do_search():
        results = []

        if source in ["all", "npm"]:
            npm_results = await search_npm(query, limit=limit)
            results.extend(npm_results)

        if source in ["all", "github"]:
            gh_results = await search_github(query, limit=limit)
            results.extend(gh_results)

        return results

    results = run_async(do_search())

    if not results:
        click.echo(click.style("No skills found.", fg="yellow"))
        click.echo("\nTry different keywords or check:")
        click.echo("  - npm: packages with 'claude-skill' keyword")
        click.echo("  - GitHub: repos with 'claude-skill' topic")
        return

    # Group by source
    npm_skills = [r for r in results if r.get("source") == "npm"]
    gh_skills = [r for r in results if r.get("source") == "github"]

    if npm_skills:
        click.echo(click.style("npm packages:", fg="blue", bold=True))
        for s in npm_skills:
            click.echo(f"  {click.style(s['name'], fg='green')}")
            desc = s.get("description", "No description")
            click.echo(f"    {desc[:70]}{'...' if len(desc) > 70 else ''}")
            click.echo(f"    Install: isa_mcp skill install {s['name']}")
            click.echo()

    if gh_skills:
        click.echo(click.style("GitHub repositories:", fg="blue", bold=True))
        for s in gh_skills:
            stars = s.get("stars", 0)
            star_str = f"★ {stars}" if stars else ""
            click.echo(
                f"  {click.style(s['name'], fg='green')} {click.style(star_str, fg='yellow')}"
            )
            desc = s.get("description", "No description")
            click.echo(f"    {desc[:70]}{'...' if len(desc) > 70 else ''}")
            click.echo(f"    Install: isa_mcp skill install {s['name']}")
            click.echo()


@skill.command("info")
@click.argument("name")
def skill_info(name: str):
    """
    Show detailed information about an installed skill.

    Example:
      isa_mcp skill info remotion-dev-skills
    """
    installer, _, _, _ = get_installer()

    installed = installer.list_installed()
    sanitized_name = name.lstrip("@").replace("/", "-").lower()

    found = None
    for s in installed:
        if s["name"] == sanitized_name or s["name"] == name:
            found = s
            break

    if not found:
        click.echo(click.style(f"Skill '{name}' is not installed.", fg="yellow"))
        click.echo(f"\nSearch for it: isa_mcp skill search {name}")
        return

    click.echo(click.style(f"Skill: {found['name']}", fg="cyan", bold=True))
    click.echo(f"{'─' * 50}")
    click.echo(f"Version:       {found.get('version', 'unknown')}")
    click.echo(f"Description:   {found.get('description', 'No description')}")
    click.echo(f"Path:          {found.get('path')}")
    click.echo(f"Has guides:    {'Yes' if found.get('has_guides') else 'No'}")
    click.echo(f"Has templates: {'Yes' if found.get('has_templates') else 'No'}")

    # Show SKILL.md content preview
    skill_path = Path(found.get("path"))
    skill_md = skill_path / "SKILL.md"

    if skill_md.exists():
        click.echo(f"\n{click.style('SKILL.md preview:', fg='blue', bold=True)}")
        click.echo("─" * 50)
        content = skill_md.read_text()
        # Show first 500 chars
        preview = content[:500]
        if len(content) > 500:
            preview += "\n..."
        click.echo(preview)

    # List guides if present
    guides_dir = skill_path / "guides"
    if guides_dir.exists():
        guides = list(guides_dir.rglob("*.md"))
        if guides:
            click.echo(f"\n{click.style('Available guides:', fg='blue', bold=True)}")
            for g in guides[:10]:
                click.echo(f"  - {g.relative_to(guides_dir)}")
            if len(guides) > 10:
                click.echo(f"  ... and {len(guides) - 10} more")


@skill.command("create")
@click.option("--id", "skill_id", required=True, help="Skill ID (e.g., video-creation)")
@click.option("--name", "skill_name", required=True, help="Display name")
@click.option("--description", required=True, help="Skill description")
@click.option("--domain", default="specialized", help="Parent domain")
@click.option("--keywords", default="", help="Comma-separated keywords")
def skill_create(skill_id: str, skill_name: str, description: str, domain: str, keywords: str):
    """
    Create a new skill category in the database.

    \b
    Example:
      isa_mcp skill create \\
        --id video-creation \\
        --name "Video Creation" \\
        --description "Tools for creating and editing videos" \\
        --domain content \\
        --keywords "video,render,animation"
    """
    try:
        from services.skill_service.skill_service import SkillService
    except ImportError:
        click.echo(click.style("Error: Could not import SkillService", fg="red"))
        click.echo("This command requires the full isA MCP environment.")
        sys.exit(1)

    click.echo(f"Creating skill category: {click.style(skill_id, fg='cyan')}")

    async def do_create():
        service = SkillService()
        skill_data = {
            "id": skill_id,
            "name": skill_name,
            "description": description,
            "parent_domain": domain,
            "keywords": [k.strip() for k in keywords.split(",") if k.strip()],
        }
        return await service.create_skill_category(skill_data)

    try:
        result = run_async(do_create())
        click.echo(click.style("✓ Skill category created!", fg="green"))
        click.echo(f"  ID:     {result.get('id')}")
        click.echo(f"  Name:   {result.get('name')}")
        click.echo(f"  Domain: {result.get('parent_domain')}")
    except Exception as e:
        click.echo(click.style(f"✗ Failed to create skill: {e}", fg="red"))
        sys.exit(1)
