#!/usr/bin/env python3

import logging
import os
import sys
from pathlib import Path

import click

# Get version
try:
    from lumecode.__version__ import __version__
except ImportError:
    __version__ = "1.0.0"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("lumecode")

# Add parent directories to path for imports
cli_dir = Path(__file__).parent
project_root = cli_dir.parent.parent
sys.path.insert(0, str(project_root))

from lumecode.cli.commands.ask import ask
from lumecode.cli.commands.batch import batch_group
from lumecode.cli.commands.cache import cache_group
from lumecode.cli.commands.chat import chat  # NEW: Interactive REPL
from lumecode.cli.commands.commit import commit_group
from lumecode.cli.commands.config import config_group

# Import command groups
from lumecode.cli.commands.docs import docs_group
from lumecode.cli.commands.explain import explain_group
from lumecode.cli.commands.file import file  # NEW: File operations
from lumecode.cli.commands.provider import provider_group  # NEW: Provider management
from lumecode.cli.commands.refactor import refactor_group
from lumecode.cli.commands.review import review_group
from lumecode.cli.commands.test import test_group


def _check_api_keys():
    """Check for API keys and display setup guidance if missing."""
    groq_key = os.getenv("GROQ_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    # If at least one key is configured, we're good
    if groq_key or openrouter_key:
        return

    # No API keys configured - show friendly setup message
    click.echo()
    click.secho("⚠️  No API keys configured!", fg="yellow", bold=True)
    click.echo()
    click.echo("Lumecode requires at least one API key to function.")
    click.echo("You can use FREE tiers from:")
    click.echo()
    click.secho("  • Groq (recommended)", fg="green", bold=True)
    click.echo("    - Fast, high-quality models")
    click.echo("    - Sign up: https://console.groq.com")
    click.echo("    - Set: export GROQ_API_KEY='your-key-here'")
    click.echo()
    click.secho("  • OpenRouter", fg="cyan", bold=True)
    click.echo("    - Access to multiple model providers")
    click.echo("    - Sign up: https://openrouter.ai")
    click.echo("    - Set: export OPENROUTER_API_KEY='your-key-here'")
    click.echo()
    click.echo("To persist your API key, add it to your shell profile:")
    click.echo("  echo 'export GROQ_API_KEY=\"your-key-here\"' >> ~/.zshrc")
    click.echo("  source ~/.zshrc")
    click.echo()
    click.echo("Or create a .env file in your project directory:")
    click.echo("  GROQ_API_KEY=your-key-here")
    click.echo()
    click.secho("💡 Tip:", fg="blue", bold=True)
    click.echo("  Run 'lumecode config' to see all configuration options")
    click.echo()


@click.group()
@click.version_option(version=__version__)
@click.option("--debug", "-d", is_flag=True, help="Enable debug logging")
@click.option("--config", "-c", type=click.Path(exists=True), help="Path to config file")
def cli(debug, config):
    """Lumecode - AI-powered developer CLI assistant.

    FREE, open-source tool for intelligent code assistance, documentation,
    testing, review, and more - powered by AI models from Groq and OpenRouter.
    """
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    if config:
        # Load custom config file
        from backend.config import ConfigManager

        config_manager = ConfigManager()
        config_manager.load_config(config)
        logger.debug(f"Loaded config from {config}")

    # Check for API keys and show setup guidance
    _check_api_keys()


# Register command groups
cli.add_command(docs_group)
cli.add_command(ask)
cli.add_command(commit_group)
cli.add_command(explain_group)
cli.add_command(review_group)
cli.add_command(refactor_group)
cli.add_command(test_group)
cli.add_command(cache_group)
cli.add_command(config_group)
cli.add_command(batch_group)

# NEW: Interactive & AI-powered features
cli.add_command(chat)  # Interactive REPL mode
cli.add_command(file)  # AI-powered file operations
cli.add_command(provider_group)  # Provider management

# Add more command groups here as they are implemented
# cli.add_command(analyze_group)
# cli.add_command(agent_group)
# cli.add_command(plugin_group)


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except Exception as e:
        logger.error(f"Error: {e}")
        if logging.getLogger().level == logging.DEBUG:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
