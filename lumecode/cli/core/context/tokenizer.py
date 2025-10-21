"""Token counting utilities using tiktoken.

This module provides utilities for counting tokens in text, managing token limits,
and truncating text to fit within token budgets.
"""

from typing import Optional
import tiktoken


# Model token limits (context window sizes)
MODEL_TOKEN_LIMITS = {
    'gpt-3.5-turbo': 4096,
    'gpt-4': 8192,
    'gpt-4-turbo': 128000,
    'gpt-4-32k': 32768,
    'groq': 8192,  # llama-3.3-70b-versatile
    'openrouter': 8192,  # Default
    'mock': 4096,
}

# Default model for encoding
DEFAULT_MODEL = 'gpt-3.5-turbo'

# Token buffer (reserve for response)
RESPONSE_TOKEN_BUFFER = 0.25  # 25% reserved for response


def count_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    """Count tokens in text for a specific model.
    
    Args:
        text: The text to count tokens in
        model: The model name (e.g., 'gpt-3.5-turbo', 'groq')
        
    Returns:
        Number of tokens in the text
        
    Example:
        >>> count_tokens("Hello, world!")
        4
    """
    if not text:
        return 0
        
    try:
        # Get encoding for model
        encoding = _get_encoding_for_model(model)
        
        # Count tokens
        tokens = encoding.encode(text)
        return len(tokens)
    except Exception as e:
        # Fallback: rough estimate (1 token ≈ 4 chars)
        return len(text) // 4


def get_max_tokens(model: str) -> int:
    """Get maximum token limit for a model.
    
    Args:
        model: The model name
        
    Returns:
        Maximum tokens allowed for the model
        
    Example:
        >>> get_max_tokens('gpt-4')
        8192
    """
    return MODEL_TOKEN_LIMITS.get(model, MODEL_TOKEN_LIMITS[DEFAULT_MODEL])


def get_context_budget(model: str) -> int:
    """Get token budget for context (excluding response buffer).
    
    Reserves RESPONSE_TOKEN_BUFFER (25%) for AI response and user query.
    
    Args:
        model: The model name
        
    Returns:
        Maximum tokens available for context
        
    Example:
        >>> get_context_budget('gpt-3.5-turbo')
        3072  # 75% of 4096
    """
    max_tokens = get_max_tokens(model)
    return int(max_tokens * (1 - RESPONSE_TOKEN_BUFFER))


def truncate_to_tokens(
    text: str,
    max_tokens: int,
    model: str = DEFAULT_MODEL,
    preserve_start: bool = True
) -> str:
    """Truncate text to fit within token limit.
    
    Args:
        text: The text to truncate
        max_tokens: Maximum tokens allowed
        model: The model name
        preserve_start: If True, keep start of text; if False, keep end
        
    Returns:
        Truncated text that fits within max_tokens
        
    Example:
        >>> truncate_to_tokens("Hello world this is a test", 3)
        "Hello world this..."
    """
    if not text:
        return ""
        
    # Check if already within limit
    current_tokens = count_tokens(text, model)
    if current_tokens <= max_tokens:
        return text
        
    try:
        encoding = _get_encoding_for_model(model)
        tokens = encoding.encode(text)
        
        if preserve_start:
            # Keep start, truncate end
            truncated_tokens = tokens[:max_tokens]
            truncated_text = encoding.decode(truncated_tokens)
            return truncated_text + "\n\n... [truncated]"
        else:
            # Keep end, truncate start
            truncated_tokens = tokens[-max_tokens:]
            truncated_text = encoding.decode(truncated_tokens)
            return "... [truncated]\n\n" + truncated_text
    except Exception:
        # Fallback: character-based truncation
        chars_per_token = 4
        max_chars = max_tokens * chars_per_token
        
        if preserve_start:
            return text[:max_chars] + "\n\n... [truncated]"
        else:
            return "... [truncated]\n\n" + text[-max_chars:]


def estimate_tokens_from_chars(char_count: int) -> int:
    """Estimate token count from character count.
    
    Quick estimation without actual tokenization.
    Rough approximation: 1 token ≈ 4 characters.
    
    Args:
        char_count: Number of characters
        
    Returns:
        Estimated token count
        
    Example:
        >>> estimate_tokens_from_chars(100)
        25
    """
    return char_count // 4


def _get_encoding_for_model(model: str) -> tiktoken.Encoding:
    """Get tiktoken encoding for a model.
    
    Args:
        model: The model name
        
    Returns:
        tiktoken.Encoding instance
        
    Raises:
        ValueError: If encoding not found
    """
    # Map our model names to tiktoken encoding names
    encoding_map = {
        'gpt-3.5-turbo': 'cl100k_base',
        'gpt-4': 'cl100k_base',
        'gpt-4-turbo': 'cl100k_base',
        'gpt-4-32k': 'cl100k_base',
        'groq': 'cl100k_base',  # Use GPT-4 encoding for Groq
        'openrouter': 'cl100k_base',
        'mock': 'cl100k_base',
    }
    
    encoding_name = encoding_map.get(model, 'cl100k_base')
    return tiktoken.get_encoding(encoding_name)


def get_token_breakdown(text: str, model: str = DEFAULT_MODEL) -> dict:
    """Get detailed token breakdown for debugging.
    
    Args:
        text: The text to analyze
        model: The model name
        
    Returns:
        Dict with token statistics
        
    Example:
        >>> get_token_breakdown("Hello world")
        {
            'text_length': 11,
            'token_count': 2,
            'chars_per_token': 5.5,
            'model': 'gpt-3.5-turbo'
        }
    """
    token_count = count_tokens(text, model)
    text_length = len(text)
    
    return {
        'text_length': text_length,
        'token_count': token_count,
        'chars_per_token': text_length / token_count if token_count > 0 else 0,
        'model': model,
        'max_tokens': get_max_tokens(model),
        'context_budget': get_context_budget(model),
    }
