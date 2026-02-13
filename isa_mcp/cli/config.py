"""
Configuration management commands for isA MCP CLI.

Commands:
    isa_mcp config show          Show current configuration
    isa_mcp config get <key>     Get a configuration value
    isa_mcp config set <k> <v>   Set a configuration value
    isa_mcp config env           Show environment info
"""

import json
import os
import sys
from pathlib import Path

import click

# =========================================================================
# Config Command Group
# =========================================================================


@click.group()
def config():
    """Manage isA MCP configuration."""
    pass


@config.command("show")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--secrets/--no-secrets", default=False, help="Show secret values")
def config_show(as_json: bool, secrets: bool):
    """
    Show current configuration.

    \b
    Examples:
      isa_mcp config show
      isa_mcp config show --json
      isa_mcp config show --secrets
    """
    try:
        from core.config import get_settings

        settings = get_settings()

        config_dict = {
            "environment": os.getenv("ENVIRONMENT", "development"),
            "server": {
                "host": getattr(settings, "host", "0.0.0.0"),
                "port": getattr(settings, "port", 8081),
            },
            "infrastructure": {
                "postgres": {
                    "host": getattr(settings.infra, "postgres_grpc_host", "N/A"),
                    "port": getattr(settings.infra, "postgres_grpc_port", "N/A"),
                },
                "redis": {
                    "host": getattr(settings.infra, "redis_grpc_host", "N/A"),
                    "port": getattr(settings.infra, "redis_grpc_port", "N/A"),
                },
                "qdrant": {
                    "host": getattr(settings.infra, "qdrant_grpc_host", "N/A"),
                    "port": getattr(settings.infra, "qdrant_grpc_port", "N/A"),
                },
            },
            "services": {
                "model_service_url": getattr(settings.service, "model_service_url", "N/A"),
                "calendar_service_url": getattr(settings.service, "calendar_service_url", "N/A"),
            },
        }

        # Mask secrets unless explicitly requested
        if not secrets:

            def mask_secrets(d):
                for k, v in d.items():
                    if isinstance(v, dict):
                        mask_secrets(v)
                    elif isinstance(v, str) and any(
                        s in k.lower() for s in ["password", "secret", "key", "token"]
                    ):
                        d[k] = "***" if v else None

            mask_secrets(config_dict)

    except ImportError:
        config_dict = {
            "error": "Could not load settings. Running outside isA MCP environment.",
            "environment": os.getenv("ENVIRONMENT", "unknown"),
        }

    if as_json:
        click.echo(json.dumps(config_dict, indent=2, default=str))
        return

    click.echo(click.style("isA MCP Configuration", fg="cyan", bold=True))
    click.echo("─" * 50)

    def print_config(d, indent=0):
        for k, v in d.items():
            prefix = "  " * indent
            if isinstance(v, dict):
                click.echo(f"{prefix}{click.style(k, fg='blue')}:")
                print_config(v, indent + 1)
            else:
                click.echo(f"{prefix}{k}: {click.style(str(v), fg='green')}")

    print_config(config_dict)


@config.command("get")
@click.argument("key")
def config_get(key: str):
    """
    Get a specific configuration value.

    Key can use dot notation: infra.postgres.host

    \b
    Examples:
      isa_mcp config get port
      isa_mcp config get infra.postgres.host
      isa_mcp config get service.model_service_url
    """
    try:
        from core.config import get_settings

        settings = get_settings()

        # Navigate nested keys
        parts = key.split(".")
        value = settings

        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict) and part in value:
                value = value[part]
            else:
                click.echo(click.style(f"Key '{key}' not found", fg="yellow"))
                return

        click.echo(f"{key} = {click.style(str(value), fg='green')}")

    except ImportError:
        # Fallback to environment variables
        env_key = key.upper().replace(".", "_")
        value = os.getenv(env_key)
        if value:
            click.echo(f"{key} = {click.style(value, fg='green')}")
        else:
            click.echo(click.style(f"Key '{key}' not found", fg="yellow"))


@config.command("set")
@click.argument("key")
@click.argument("value")
@click.option("--persist/--no-persist", default=False, help="Persist to .env file")
def config_set(key: str, value: str, persist: bool):
    """
    Set a configuration value.

    By default, sets environment variable for current session.
    Use --persist to save to .env file.

    \b
    Examples:
      isa_mcp config set PORT 8082
      isa_mcp config set DEBUG true --persist
    """
    # Set environment variable
    env_key = key.upper().replace(".", "_")
    os.environ[env_key] = value

    click.echo(f"Set {env_key} = {click.style(value, fg='green')}")

    if persist:
        # Find .env file
        env_file = Path.cwd() / ".env"
        if not env_file.exists():
            env_file = Path.cwd() / "deployment" / "development" / "config" / ".env"

        if env_file.exists():
            # Read existing content
            content = env_file.read_text()
            lines = content.splitlines()

            # Update or add the key
            found = False
            for i, line in enumerate(lines):
                if line.startswith(f"{env_key}="):
                    lines[i] = f"{env_key}={value}"
                    found = True
                    break

            if not found:
                lines.append(f"{env_key}={value}")

            # Write back
            env_file.write_text("\n".join(lines) + "\n")
            click.echo(click.style(f"  Persisted to {env_file}", fg="cyan"))
        else:
            click.echo(click.style("  Warning: .env file not found, not persisted", fg="yellow"))


@config.command("env")
def config_env():
    """
    Show environment information.

    Displays Python version, working directory, and environment variables
    related to isA MCP.
    """
    import platform

    click.echo(click.style("Environment Information", fg="cyan", bold=True))
    click.echo("─" * 50)

    click.echo(f"Python:      {platform.python_version()}")
    click.echo(f"Platform:    {platform.system()} {platform.release()}")
    click.echo(f"Working Dir: {os.getcwd()}")
    click.echo(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    click.echo()

    click.echo(click.style("Relevant Environment Variables:", fg="blue", bold=True))

    relevant_prefixes = ["ISA_", "MCP_", "POSTGRES_", "REDIS_", "QDRANT_", "MODEL_", "DEBUG"]
    env_vars = {
        k: v for k, v in os.environ.items() if any(k.startswith(p) for p in relevant_prefixes)
    }

    if env_vars:
        for k, v in sorted(env_vars.items()):
            # Mask sensitive values
            if any(s in k.lower() for s in ["password", "secret", "key", "token"]):
                v = "***"
            click.echo(f"  {k}={v}")
    else:
        click.echo("  (none set)")


@config.command("init")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing config")
def config_init(force: bool):
    """
    Initialize configuration files.

    Creates default .env and configuration files if they don't exist.

    Example:
      isa_mcp config init
    """
    env_file = Path.cwd() / ".env"

    if env_file.exists() and not force:
        click.echo(click.style(".env file already exists. Use --force to overwrite.", fg="yellow"))
        return

    default_config = """# isA MCP Configuration
ENVIRONMENT=development

# Server
PORT=8081
HOST=0.0.0.0

# Infrastructure (gRPC endpoints)
POSTGRES_GRPC_HOST=localhost
POSTGRES_GRPC_PORT=50051
REDIS_GRPC_HOST=localhost
REDIS_GRPC_PORT=50052
QDRANT_GRPC_HOST=localhost
QDRANT_GRPC_PORT=6334

# Services
MODEL_SERVICE_URL=http://localhost:8080
CALENDAR_SERVICE_URL=http://localhost:8083

# Logging
LOG_LEVEL=INFO
DEBUG=false
"""

    env_file.write_text(default_config)
    click.echo(click.style(f"✓ Created {env_file}", fg="green"))
    click.echo("\nEdit this file to configure your isA MCP instance.")


@config.command("paths")
def config_paths():
    """
    Show important file paths.

    Displays paths to skills, resources, and other important directories.
    """
    from pathlib import Path

    project_root = Path(__file__).parent.parent.parent

    paths = {
        "Project Root": project_root,
        "Skills (Vibe)": project_root / "resources" / "skills" / "vibe",
        "Skills (External)": project_root / "resources" / "skills" / "external",
        "Tools": project_root / "tools",
        "Prompts": project_root / "prompts",
        "Resources": project_root / "resources",
        "Services": project_root / "services",
        "Config": project_root / "deployment",
    }

    click.echo(click.style("isA MCP Paths", fg="cyan", bold=True))
    click.echo("─" * 50)

    for name, path in paths.items():
        exists = path.exists()
        status = click.style("✓", fg="green") if exists else click.style("✗", fg="red")
        click.echo(f"  {status} {name}: {path}")
