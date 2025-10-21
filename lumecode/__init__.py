"""
Lumecode - AI-powered developer CLI tool for intelligent code assistance.
"""

try:
    from lumecode.__version__ import __version__
except ImportError:
    __version__ = "1.0.0"

__all__ = ["__version__"]
