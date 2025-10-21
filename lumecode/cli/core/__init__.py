"""Core functionality for the Lumecode CLI.

This package contains core functionality used by the Lumecode CLI,
including LLM providers, context extraction, and prompt management.
"""

from .llm import (
    get_provider,
    get_provider_with_fallback,
    list_available_providers,
    BaseLLMProvider,
)

__all__ = [
    "get_provider",
    "get_provider_with_fallback", 
    "list_available_providers",
    "BaseLLMProvider",
]