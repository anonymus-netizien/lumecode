"""
LLM Provider Factory
Automatically selects and creates providers with fallback chain.
Order: Groq → OpenRouter → Mock (never fails!)
"""

import os
from typing import Optional, List
from .base import BaseLLMProvider, ProviderType
from .mock import MockProvider
from .groq import GroqProvider
from .openrouter import OpenRouterProvider


def get_provider(
    provider_name: str = "groq", model: Optional[str] = None, api_key: Optional[str] = None
) -> BaseLLMProvider:
    """
    Get a specific LLM provider.

    Args:
        provider_name: Provider name (groq, openrouter, mock)
        model: Optional model override
        api_key: Optional API key override

    Returns:
        Configured LLM provider instance

    Raises:
        ValueError: If provider name is invalid
    """
    provider_name = provider_name.lower()

    if provider_name == "groq":
        return GroqProvider(model=model or "llama-70b", api_key=api_key)

    elif provider_name == "openrouter":
        return OpenRouterProvider(model=model or "deepseek", api_key=api_key)

    elif provider_name == "mock":
        return MockProvider(model=model or "mock-v1")

    else:
        raise ValueError(f"Unknown provider: {provider_name}. Choose from: groq, openrouter, mock")


def get_provider_with_fallback(
    preferred_provider: str = "groq", model: Optional[str] = None, verbose: bool = False
) -> BaseLLMProvider:
    """
    Get a provider with automatic fallback if the preferred one fails.

    Fallback order:
    1. Groq (if API key available) - fastest, best FREE tier
    2. OpenRouter (if API key available) - more models
    3. Mock - always works, for offline testing

    Args:
        preferred_provider: Preferred provider name
        model: Optional model override
        verbose: Print fallback messages

    Returns:
        Working LLM provider (never fails!)
    """
    # Determine fallback order based on preference
    if preferred_provider == "groq":
        fallback_order = ["groq", "openrouter", "mock"]
    elif preferred_provider == "openrouter":
        fallback_order = ["openrouter", "groq", "mock"]
    elif preferred_provider == "mock":
        fallback_order = ["mock"]
    else:
        # Unknown provider, use default order
        fallback_order = ["groq", "openrouter", "mock"]

    last_error = None

    for provider_name in fallback_order:
        try:
            # Check if API key is available (skip if not, except for mock)
            if provider_name == "groq":
                if not os.getenv("GROQ_API_KEY"):
                    if verbose:
                        print(f"⚠️  Groq API key not found, trying next provider...")
                    continue

            elif provider_name == "openrouter":
                if not os.getenv("OPENROUTER_API_KEY"):
                    if verbose:
                        print(f"⚠️  OpenRouter API key not found, trying next provider...")
                    continue

            # Try to create provider
            provider = get_provider(provider_name, model)

            if verbose and provider_name != preferred_provider:
                print(f"✅ Using fallback provider: {provider_name}")

            return provider

        except Exception as e:
            last_error = e
            if verbose:
                print(f"⚠️  {provider_name} failed: {e}")
            continue

    # If we get here, something went very wrong (mock should always work)
    raise RuntimeError(f"All providers failed! Last error: {last_error}")


def list_available_providers() -> List[str]:
    """
    List all providers that have API keys configured.

    Returns:
        List of available provider names
    """
    available = []

    if os.getenv("GROQ_API_KEY"):
        available.append("groq")

    if os.getenv("OPENROUTER_API_KEY"):
        available.append("openrouter")

    # Mock is always available
    available.append("mock")

    return available


def check_provider_health(provider: BaseLLMProvider) -> bool:
    """
    Check if a provider is working by making a test request.

    Args:
        provider: Provider to test

    Returns:
        True if provider works, False otherwise
    """
    try:
        response = provider.complete("Say 'ok' in one word", max_tokens=10)
        return len(response) > 0
    except Exception:
        return False


# Convenience exports
__all__ = [
    "BaseLLMProvider",
    "MockProvider",
    "GroqProvider",
    "OpenRouterProvider",
    "get_provider",
    "get_provider_with_fallback",
    "list_available_providers",
    "check_provider_health",
]
