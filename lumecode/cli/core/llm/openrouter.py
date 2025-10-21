"""
OpenRouter LLM Provider
Access to multiple models via OpenRouter

SETUP REQUIRED:
1. Get API key from https://openrouter.ai/keys
2. Configure privacy settings at https://openrouter.ai/settings/privacy
   - Enable "Allow Training" to use free models
3. Set OPENROUTER_API_KEY environment variable

Free models available after setup: deepseek-v3.1, qwen3-coder, kimi-k2, etc.
"""

import os
import httpx
from typing import Iterator, Optional
from .base import BaseLLMProvider, ModelInfo, RateLimitInfo, ProviderType


class OpenRouterProvider(BaseLLMProvider):
    """
    OpenRouter provider using their FREE API.
    
    FREE Tier:
    - 20 requests/minute
    - Access to multiple free models
    - Models: deepseek-v3.1, qwen3-coder, kimi-k2, gemma-3n, nemotron-nano-9b
    """
    
    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    # Available FREE models (verified working)
    MODELS = {
        "deepseek": "deepseek/deepseek-chat-v3.1:free",
        "qwen": "qwen/qwen3-coder:free",
        "kimi": "moonshotai/kimi-k2:free",
        "gemma": "google/gemma-3n-e2b-it:free",
        "nemotron": "nvidia/nemotron-nano-9b-v2:free"
    }
    
    def __init__(self, model: str = "deepseek", api_key: Optional[str] = None):
        """
        Initialize OpenRouter provider.
        
        Args:
            model: Model shorthand (deepseek, qwen, kimi, gemma, nemotron)
            api_key: OpenRouter API key (or set OPENROUTER_API_KEY env var)
        """
        super().__init__(model, api_key)
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        
        if not self.api_key:
            raise ValueError("OpenRouter API key required. Set OPENROUTER_API_KEY env var or pass api_key parameter")
        
        # Map shorthand to full model name
        self.model = self.MODELS.get(model, model)
        self.last_rate_limit = None
    
    def complete(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Get completion from OpenRouter.
        
        Args:
            prompt: User prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            system_prompt: Optional system prompt
            
        Returns:
            Completion text
            
        Raises:
            httpx.HTTPError: If API request fails
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/yourusername/lumecode",  # Required by OpenRouter
            "X-Title": "Lumecode CLI",  # Optional, helps with monitoring
            "X-Data-Policy": "allow_training"  # Required for free models
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(self.API_URL, json=payload, headers=headers)
            
            # Better error handling for common issues
            if response.status_code == 404:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                
                if 'data policy' in error_msg.lower():
                    raise ValueError(
                        "❌ OpenRouter account not configured for free models.\n\n"
                        "To use free models:\n"
                        "1. Visit https://openrouter.ai/settings/privacy\n"
                        "2. Enable 'Allow Training' option\n"
                        "3. Try again\n\n"
                        "Or use Groq provider instead: lume ask query 'your question' --provider groq"
                    )
                raise ValueError(f"OpenRouter error: {error_msg}")
            
            response.raise_for_status()
            
            # Store rate limit info
            self._parse_rate_limit_headers(response.headers)
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    def stream_complete(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> Iterator[str]:
        """
        Get streaming completion from OpenRouter.
        
        Args:
            prompt: User prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            system_prompt: Optional system prompt
            
        Yields:
            Text chunks as they arrive
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/yourusername/lumecode",
            "X-Title": "Lumecode CLI",
            "X-Data-Policy": "allow_training"  # Required for free models
        }
        
        with httpx.Client(timeout=30.0) as client:
            with client.stream("POST", self.API_URL, json=payload, headers=headers) as response:
                response.raise_for_status()
                
                # Parse SSE stream
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        
                        if data_str.strip() == "[DONE]":
                            break
                        
                        try:
                            import json
                            data = json.loads(data_str)
                            
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
    
    def get_model_info(self) -> ModelInfo:
        """Get OpenRouter model information"""
        context_windows = {
            "deepseek/deepseek-chat-v3.1:free": 64000,
            "qwen/qwen3-coder:free": 32768,
            "moonshotai/kimi-k2:free": 128000,
            "google/gemma-3n-e2b-it:free": 8192,
            "nvidia/nemotron-nano-9b-v2:free": 32768
        }
        
        return ModelInfo(
            provider="openrouter",
            model=self.model,
            max_tokens=4000,
            supports_streaming=True,
            context_window=context_windows.get(self.model, 32000)
        )
    
    def check_rate_limit(self) -> RateLimitInfo:
        """Get current rate limit status"""
        return self.last_rate_limit or RateLimitInfo()
    
    def _parse_rate_limit_headers(self, headers: httpx.Headers):
        """Parse rate limit info from response headers"""
        self.last_rate_limit = RateLimitInfo(
            requests_remaining=int(headers.get("x-ratelimit-remaining", 0)) if headers.get("x-ratelimit-remaining") else None,
            requests_limit=int(headers.get("x-ratelimit-limit", 0)) if headers.get("x-ratelimit-limit") else None,
            reset_at=headers.get("x-ratelimit-reset", "unknown")
        )
