"""Command modules for the Lumecode CLI.

This package contains the command groups and commands for the Lumecode CLI.
Each module in this package should define a command group that can be registered
with the main CLI application.
"""

# Import command groups for easier access
from .docs import docs_group

__all__ = [
    'docs_group',
]