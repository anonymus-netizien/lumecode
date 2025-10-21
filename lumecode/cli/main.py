#!/usr/bin/env python3

import os
import sys
import click
import logging
from pathlib import Path

# Get version
try:
    from lumecode.__version__ import __version__
except ImportError:
    __version__ = "1.0.0"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("lumecode")

# Add parent directories to path for imports
cli_dir = Path(__file__).parent
project_root = cli_dir.parent.parent
sys.path.insert(0, str(project_root))

# Import command groups
from lumecode.cli.commands.docs import docs_group
from lumecode.cli.commands.ask import ask
from lumecode.cli.commands.commit import commit_group
from lumecode.cli.commands.explain import explain_group
from lumecode.cli.commands.review import review_group
from lumecode.cli.commands.refactor import refactor_group
from lumecode.cli.commands.test import test_group
from lumecode.cli.commands.cache import cache_group
from lumecode.cli.commands.config import config_group
from lumecode.cli.commands.batch import batch_group
from lumecode.cli.commands.chat import chat  # NEW: Interactive REPL
from lumecode.cli.commands.file import file  # NEW: File operations
from lumecode.cli.commands.provider import provider_group  # NEW: Provider management


@click.group()
@click.version_option(version=__version__)
@click.option(
    "--debug", "-d",
    is_flag=True,
    help="Enable debug logging"
)
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Path to config file"
)
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
cli.add_command(chat)    # Interactive REPL mode
cli.add_command(file)    # AI-powered file operations
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