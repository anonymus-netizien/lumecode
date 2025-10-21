"""
Mock LLM Provider
Provides canned responses for offline testing and demos.
No API key required - perfect for testing the CLI flow.
"""

from typing import Iterator, Optional
from .base import BaseLLMProvider, ModelInfo, RateLimitInfo, ProviderType


class MockProvider(BaseLLMProvider):
    """
    Mock LLM provider that returns canned responses.
    Use this for offline testing and demo preparation.
    """
    
    # Canned responses for common prompts
    RESPONSES = {
        "commit": "feat: implement user authentication with JWT tokens\n\nAdded secure login endpoint with password hashing and token generation.",
        "explain": "This code implements a user authentication system using JWT tokens. The login endpoint validates credentials and returns a secure token.",
        "ask": "Based on the code context, this appears to be a REST API built with FastAPI. I recommend adding input validation and error handling.",
        "default": "I'm a mock LLM provider. In production, I would analyze your code and provide intelligent responses using real AI models."
    }
    
    def __init__(self, model: str = "mock-v1", api_key: Optional[str] = None):
        """Initialize mock provider"""
        super().__init__(model, api_key)
        self.provider_name = "mock"
        self.model = model
    
    def complete(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Return a canned response based on prompt keywords.
        
        Args:
            prompt: The user prompt
            max_tokens: Ignored (mock always returns full response)
            temperature: Ignored (mock is deterministic)
            system_prompt: Ignored
            
        Returns:
            A canned response string
        """
        prompt_lower = prompt.lower()
        
        # Match response based on keywords
        if "commit" in prompt_lower or "message" in prompt_lower:
            return self.RESPONSES["commit"]
        elif "explain" in prompt_lower or "what" in prompt_lower:
            return self.RESPONSES["explain"]
        elif "ask" in prompt_lower or "recommend" in prompt_lower:
            return self.RESPONSES["ask"]
        else:
            return self.RESPONSES["default"]
    
    def stream_complete(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> Iterator[str]:
        """
        Stream the response word by word.
        
        Args:
            prompt: The user prompt
            max_tokens: Ignored
            temperature: Ignored
            system_prompt: Ignored
            
        Yields:
            Words from the canned response
        """
        response = self.complete(prompt, max_tokens, temperature, system_prompt)
        
        # Simulate streaming by yielding word by word
        words = response.split()
        for word in words:
            yield word + " "
    
    def get_model_info(self) -> ModelInfo:
        """
        Return mock model information.
        
        Returns:
            ModelInfo for the mock provider
        """
        return ModelInfo(
            provider="mock",
            model=self.model,
            max_tokens=2000,
            supports_streaming=True,
            context_window=4000
        )
    
    def check_rate_limit(self) -> RateLimitInfo:
        """
        Mock has unlimited rate limits.
        
        Returns:
            RateLimitInfo with unlimited values
        """
        return RateLimitInfo(
            requests_remaining=999999,
            requests_limit=999999,
            tokens_remaining=999999,
            tokens_limit=999999,
            reset_at="never"
        )
