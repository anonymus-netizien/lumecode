"""
Base LLM Provider Interface
Defines the abstract interface that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Iterator, Optional


class ProviderType(Enum):
    """Supported LLM provider types"""

    OPENROUTER = "openrouter"
    GROQ = "groq"
    OLLAMA = "ollama"
    MOCK = "mock"


@dataclass
class ModelInfo:
    """Information about the LLM model being used"""

    provider: str
    model: str
    max_tokens: int
    supports_streaming: bool
    context_window: int


@dataclass
class RateLimitInfo:
    """Rate limit information from provider"""

    requests_remaining: Optional[int] = None
    requests_limit: Optional[int] = None
    tokens_remaining: Optional[int] = None
    tokens_limit: Optional[int] = None
    reset_at: Optional[str] = None


class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers.

    All providers must implement:
    - complete(): Get a completion from the LLM
    - stream_complete(): Get a streaming completion
    - get_model_info(): Return model information
    - check_rate_limit(): Check current rate limit status
    """

    def __init__(
        self, model: Optional[str] = None, api_key: Optional[str] = None, use_cache: bool = True
    ):
        """
        Initialize the provider.

        Args:
            model: Model name to use (provider-specific)
            api_key: API key for the provider (optional, can use env var)
            use_cache: Whether to use response caching (default: True)
        """
        self.model = model
        self.api_key = api_key
        self.use_cache = use_cache
        self._cache = None

    def _get_cache(self):
        """Get cache instance (lazy loading)"""
        if self._cache is None and self.use_cache:
            from ..cache import get_cache

            self._cache = get_cache()
        return self._cache

    @abstractmethod
    def complete(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Get a completion from the LLM.

        Args:
            prompt: The user prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            system_prompt: Optional system prompt

        Returns:
            The completion text
        """
        pass

    @abstractmethod
    def stream_complete(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> Iterator[str]:
        """
        Get a streaming completion from the LLM.

        Args:
            prompt: The user prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            system_prompt: Optional system prompt

        Yields:
            Text chunks as they arrive
        """
        pass

    @abstractmethod
    def get_model_info(self) -> ModelInfo:
        """
        Get information about the model being used.

        Returns:
            ModelInfo dataclass with model details
        """
        pass

    @abstractmethod
    def check_rate_limit(self) -> RateLimitInfo:
        """
        Check the current rate limit status.

        Returns:
            RateLimitInfo with current rate limit details
        """
        pass

    def __str__(self) -> str:
        """String representation of the provider"""
        info = self.get_model_info()
        return f"{info.provider}:{info.model}"
