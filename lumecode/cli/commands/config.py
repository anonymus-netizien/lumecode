"""
Configuration Management Command
Manage user preferences and settings
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from ..core.config import Config, get_config_manager

console = Console()


@click.group(name="config")
def config_group():
    """⚙️  Manage configuration settings"""
    pass


@config_group.command(name="show")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def show(as_json):
    """
    Show current configuration.

    Examples:
        # Show all settings
        lume config show

        # Show as JSON
        lume config show --json
    """
    try:
        manager = get_config_manager()
        config_dict = manager.show()

        if as_json:
            import json

            console.print(json.dumps(config_dict, indent=2))
            return

        # Create sections
        sections = {
            "LLM Settings": [
                ("default_provider", config_dict["default_provider"]),
                ("default_model", config_dict["default_model"] or "(auto)"),
                ("temperature", config_dict["temperature"]),
                ("max_tokens", config_dict["max_tokens"]),
            ],
            "Cache Settings": [
                ("cache_enabled", "✅" if config_dict["cache_enabled"] else "❌"),
                ("cache_ttl_hours", config_dict["cache_ttl_hours"]),
                ("cache_dir", config_dict["cache_dir"] or "(default)"),
            ],
            "UI Settings": [
                ("streaming_enabled", "✅" if config_dict["streaming_enabled"] else "❌"),
                ("show_provider_info", "✅" if config_dict["show_provider_info"] else "❌"),
                ("color_theme", config_dict["color_theme"]),
            ],
            "Git Settings": [
                ("conventional_commits", "✅" if config_dict["conventional_commits"] else "❌"),
                ("auto_stage", "✅" if config_dict["auto_stage"] else "❌"),
                ("sign_commits", "✅" if config_dict["sign_commits"] else "❌"),
            ],
            "Test Settings": [
                ("default_test_framework", config_dict["default_test_framework"]),
                ("test_coverage_threshold", f"{config_dict['test_coverage_threshold']}%"),
            ],
            "Advanced Settings": [
                ("verbose_logging", "✅" if config_dict["verbose_logging"] else "❌"),
                ("telemetry_enabled", "✅" if config_dict["telemetry_enabled"] else "❌"),
                ("check_for_updates", "✅" if config_dict["check_for_updates"] else "❌"),
            ],
        }

        console.print()
        for section_name, settings in sections.items():
            table = Table(title=f"⚙️  {section_name}", show_header=False)
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="green")

            for key, value in settings:
                table.add_row(key, str(value))

            console.print(table)
            console.print()

        # Show config file location
        console.print(
            Panel(f"📁 Config file: [cyan]{manager.config_path}[/cyan]", border_style="blue")
        )

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise


@config_group.command(name="set")
@click.argument("key")
@click.argument("value")
def set_config(key, value):
    """
    Set configuration value.

    Examples:
        # Set default provider
        lume config set default_provider groq

        # Set temperature
        lume config set temperature 0.8

        # Enable/disable cache
        lume config set cache_enabled true

        # Set max tokens
        lume config set max_tokens 2000
    """
    try:
        manager = get_config_manager()

        # Convert value to appropriate type
        current_value = manager.get(key)
        if current_value is None:
            console.print(f"[red]❌ Unknown configuration key: {key}[/red]")
            console.print("\n💡 Use 'lume config show' to see all available settings")
            return

        # Type conversion
        if isinstance(current_value, bool):
            value = value.lower() in ("true", "1", "yes", "on")
        elif isinstance(current_value, int):
            value = int(value)
        elif isinstance(current_value, float):
            value = float(value)

        # Set and validate
        manager.set(key, value)
        manager.validate()

        console.print(f"\n✅ Set [cyan]{key}[/cyan] = [green]{value}[/green]")

    except ValueError as e:
        console.print(f"[red]❌ Invalid value: {e}[/red]")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise


@config_group.command(name="get")
@click.argument("key")
def get_config(key):
    """
    Get configuration value.

    Examples:
        # Get default provider
        lume config get default_provider

        # Get temperature
        lume config get temperature
    """
    try:
        manager = get_config_manager()
        value = manager.get(key)

        if value is None:
            console.print(f"[red]❌ Unknown configuration key: {key}[/red]")
            return

        console.print(f"\n[cyan]{key}[/cyan] = [green]{value}[/green]")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise


@config_group.command(name="reset")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def reset(force):
    """
    Reset configuration to defaults.

    Examples:
        # Reset all settings
        lume config reset

        # Skip confirmation
        lume config reset --force
    """
    try:
        if not force:
            if not click.confirm("Reset all configuration to defaults?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

        manager = get_config_manager()
        manager.reset()

        console.print("\n✅ Configuration reset to defaults")
        console.print("\n💡 Use 'lume config show' to see current settings")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise


@config_group.command(name="edit")
def edit():
    """
    Open configuration file in editor.

    Examples:
        # Edit config file
        lume config edit
    """
    try:
        import os
        import subprocess

        manager = get_config_manager()
        config_path = str(manager.config_path)

        # Get editor from environment or use default
        editor = os.environ.get("EDITOR", "nano")

        console.print(f"\n📝 Opening config file in {editor}...")
        console.print(f"📁 {config_path}\n")

        # Open editor
        subprocess.run([editor, config_path])

        # Reload config
        manager.load()
        manager.validate()

        console.print("\n✅ Configuration reloaded")

    except FileNotFoundError:
        console.print(f"[red]❌ Editor not found: {editor}[/red]")
        console.print("\n💡 Set EDITOR environment variable or use 'lume config set' instead")
    except ValueError as e:
        console.print(f"[red]❌ Invalid configuration: {e}[/red]")
        console.print("\n💡 Use 'lume config reset' to restore defaults")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise


@config_group.command(name="path")
def path():
    """
    Show configuration file path.

    Examples:
        # Show config file location
        lume config path
    """
    try:
        manager = get_config_manager()
        console.print(f"\n📁 {manager.config_path}")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise


if __name__ == "__main__":
    config_group()
