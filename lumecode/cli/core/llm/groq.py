"""
Groq LLM Provider
Ultra-fast inference with FREE tier (30 req/min, 500+ tokens/sec)
Models: llama-70b, mixtral-8x7b, llama-8b
"""

import os
import httpx
from typing import Iterator, Optional
from .base import BaseLLMProvider, ModelInfo, RateLimitInfo, ProviderType


class GroqProvider(BaseLLMProvider):
    """
    Groq provider using their FREE API.
    
    FREE Tier:
    - 30 requests/minute
    - 500+ tokens/second (ultra-fast!)
    - Models: llama-3.1-70b-versatile, mixtral-8x7b-32768, llama-3.1-8b-instant
    """
    
    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    
    # Available models on FREE tier
    MODELS = {
        "llama-70b": "llama-3.3-70b-versatile",
        "mixtral": "mixtral-8x7b-32768", 
        "llama-8b": "llama-3.1-8b-instant",
        "gemma": "gemma2-9b-it"
    }
    
    def __init__(self, model: str = "llama-70b", api_key: Optional[str] = None):
        """
        Initialize Groq provider.
        
        Args:
            model: Model shorthand (llama-70b, mixtral, llama-8b)
            api_key: Groq API key (or set GROQ_API_KEY env var)
        """
        super().__init__(model, api_key)
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        
        if not self.api_key:
            raise ValueError("Groq API key required. Set GROQ_API_KEY env var or pass api_key parameter")
        
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
        Get completion from Groq.
        
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
        # Check cache first
        cache = self._get_cache()
        if cache:
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            cached_response = cache.get(
                prompt=full_prompt,
                provider="groq",
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            if cached_response:
                return cached_response
        
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
            "Content-Type": "application/json"
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(self.API_URL, json=payload, headers=headers)
            response.raise_for_status()
            
            # Store rate limit info
            self._parse_rate_limit_headers(response.headers)
            
            data = response.json()
            completion = data["choices"][0]["message"]["content"]
            
            # Cache the response
            if cache:
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                cache.set(
                    prompt=full_prompt,
                    provider="groq",
                    model=self.model,
                    response=completion,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            
            return completion
            return data["choices"][0]["message"]["content"]
    
    def stream_complete(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> Iterator[str]:
        """
        Get streaming completion from Groq.
        
        Args:
            prompt: User prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            system_prompt: Optional system prompt
            
        Yields:
            Text chunks as they arrive (VERY FAST on Groq!)
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
            "Content-Type": "application/json"
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
        """Get Groq model information"""
        context_windows = {
            "llama-3.3-70b-versatile": 128000,
            "mixtral-8x7b-32768": 32768,
            "llama-3.1-8b-instant": 128000,
            "gemma2-9b-it": 8192
        }
        
        return ModelInfo(
            provider="groq",
            model=self.model,
            max_tokens=8000,
            supports_streaming=True,
            context_window=context_windows.get(self.model, 32000)
        )
    
    def check_rate_limit(self) -> RateLimitInfo:
        """Get current rate limit status"""
        return self.last_rate_limit or RateLimitInfo()
    
    def _parse_rate_limit_headers(self, headers: httpx.Headers):
        """Parse rate limit info from response headers"""
        self.last_rate_limit = RateLimitInfo(
            requests_remaining=int(headers.get("x-ratelimit-remaining-requests", 0)),
            requests_limit=int(headers.get("x-ratelimit-limit-requests", 0)),
            tokens_remaining=int(headers.get("x-ratelimit-remaining-tokens", 0)),
            tokens_limit=int(headers.get("x-ratelimit-limit-tokens", 0)),
            reset_at=headers.get("x-ratelimit-reset-requests", "unknown")
        )
