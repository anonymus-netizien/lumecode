"""Tests for tokenizer module."""

import pytest

from lumecode.cli.core.context.tokenizer import (
    MODEL_TOKEN_LIMITS,
    count_tokens,
    estimate_tokens_from_chars,
    get_context_budget,
    get_max_tokens,
    get_token_breakdown,
    truncate_to_tokens,
)


class TestCountTokens:
    """Test token counting."""

    def test_count_tokens_simple(self):
        """Test counting tokens in simple text."""
        text = "Hello, world!"
        tokens = count_tokens(text)
        assert tokens > 0
        assert tokens < 10  # Should be around 4 tokens

    def test_count_tokens_empty(self):
        """Test counting tokens in empty string."""
        assert count_tokens("") == 0

    def test_count_tokens_long_text(self):
        """Test counting tokens in longer text."""
        text = "This is a longer piece of text. " * 10
        tokens = count_tokens(text)
        assert tokens > 50

    def test_count_tokens_with_code(self):
        """Test counting tokens in Python code."""
        code = """
def hello():
    print("Hello, world!")
    return True
"""
        tokens = count_tokens(code)
        assert tokens > 10

    def test_count_tokens_different_models(self):
        """Test token counting for different models."""
        text = "Hello, world!"

        gpt35_tokens = count_tokens(text, "gpt-3.5-turbo")
        gpt4_tokens = count_tokens(text, "gpt-4")
        groq_tokens = count_tokens(text, "groq")

        # Should be same encoding (cl100k_base)
        assert gpt35_tokens == gpt4_tokens == groq_tokens


class TestGetMaxTokens:
    """Test getting max token limits."""

    def test_get_max_tokens_gpt35(self):
        """Test GPT-3.5 token limit."""
        assert get_max_tokens("gpt-3.5-turbo") == 4096

    def test_get_max_tokens_gpt4(self):
        """Test GPT-4 token limit."""
        assert get_max_tokens("gpt-4") == 8192

    def test_get_max_tokens_groq(self):
        """Test Groq token limit."""
        assert get_max_tokens("groq") == 8192

    def test_get_max_tokens_unknown_model(self):
        """Test unknown model falls back to default."""
        default_limit = MODEL_TOKEN_LIMITS["gpt-3.5-turbo"]
        assert get_max_tokens("unknown-model") == default_limit


class TestGetContextBudget:
    """Test context budget calculation."""

    def test_get_context_budget_reserves_tokens(self):
        """Test that context budget reserves 25% for response."""
        model = "gpt-3.5-turbo"
        max_tokens = get_max_tokens(model)
        budget = get_context_budget(model)

        # Budget should be 75% of max
        expected = int(max_tokens * 0.75)
        assert budget == expected

    def test_get_context_budget_gpt4(self):
        """Test GPT-4 context budget."""
        budget = get_context_budget("gpt-4")
        assert budget == int(8192 * 0.75)  # 6144


class TestTruncateToTokens:
    """Test text truncation."""

    def test_truncate_to_tokens_no_truncation_needed(self):
        """Test when text is already under limit."""
        text = "Short text"
        result = truncate_to_tokens(text, max_tokens=100)
        assert result == text
        assert "[truncated]" not in result

    def test_truncate_to_tokens_empty_string(self):
        """Test truncating empty string."""
        assert truncate_to_tokens("", max_tokens=10) == ""

    def test_truncate_to_tokens_preserve_start(self):
        """Test truncation preserves start of text."""
        text = "This is a long piece of text. " * 20
        result = truncate_to_tokens(text, max_tokens=50, preserve_start=True)

        assert len(result) < len(text)
        assert result.startswith("This")
        assert "[truncated]" in result

    def test_truncate_to_tokens_preserve_end(self):
        """Test truncation preserves end of text."""
        text = "Start. " + "Middle. " * 200 + "End."  # Much longer text
        result = truncate_to_tokens(text, max_tokens=50, preserve_start=False)

        assert len(result) < len(text)
        assert "End." in result
        assert "[truncated]" in result

    def test_truncate_to_tokens_different_models(self):
        """Test truncation works with different models."""
        text = "Long text. " * 100

        result_gpt35 = truncate_to_tokens(text, max_tokens=50, model="gpt-3.5-turbo")
        result_gpt4 = truncate_to_tokens(text, max_tokens=50, model="gpt-4")

        assert len(result_gpt35) < len(text)
        assert len(result_gpt4) < len(text)


class TestEstimateTokensFromChars:
    """Test token estimation."""

    def test_estimate_tokens_from_chars(self):
        """Test token estimation from character count."""
        # Rough estimate: 1 token ≈ 4 chars
        assert estimate_tokens_from_chars(100) == 25
        assert estimate_tokens_from_chars(400) == 100
        assert estimate_tokens_from_chars(0) == 0

    def test_estimate_is_close_to_actual(self):
        """Test that estimate is reasonable."""
        text = "Hello, world! " * 10
        actual_tokens = count_tokens(text)
        estimated_tokens = estimate_tokens_from_chars(len(text))

        # Guard against division by zero
        if actual_tokens == 0:
            assert estimated_tokens == 0
        else:
            # Should be within 50% of actual
            ratio = estimated_tokens / actual_tokens
            assert 0.5 <= ratio <= 1.5


class TestGetTokenBreakdown:
    """Test token breakdown."""

    def test_get_token_breakdown(self):
        """Test getting detailed token breakdown."""
        text = "Hello, world!"
        breakdown = get_token_breakdown(text, "gpt-4")

        assert "text_length" in breakdown
        assert "token_count" in breakdown
        assert "chars_per_token" in breakdown
        assert "model" in breakdown
        assert "max_tokens" in breakdown
        assert "context_budget" in breakdown

        assert breakdown["text_length"] == len(text)
        assert breakdown["token_count"] > 0
        assert breakdown["model"] == "gpt-4"
        assert breakdown["max_tokens"] == 8192

    def test_token_breakdown_empty_text(self):
        """Test breakdown with empty text."""
        breakdown = get_token_breakdown("", "gpt-3.5-turbo")
        assert breakdown["text_length"] == 0
        assert breakdown["token_count"] == 0


class TestTokenizerIntegration:
    """Integration tests for tokenizer."""

    def test_real_python_code(self):
        """Test with real Python code."""
        code = """
def calculate_sum(numbers):
    '''Calculate sum of numbers.'''
    total = 0
    for num in numbers:
        total += num
    return total

# Test
result = calculate_sum([1, 2, 3, 4, 5])
print(f'Sum: {result}')
"""
        tokens = count_tokens(code)
        assert tokens > 30  # Should have reasonable token count

        # Test truncation
        truncated = truncate_to_tokens(code, max_tokens=20)
        assert count_tokens(truncated) <= 25  # Some buffer for truncation marker

    def test_token_counting_consistency(self):
        """Test that token counting is consistent."""
        text = "The quick brown fox jumps over the lazy dog."

        count1 = count_tokens(text)
        count2 = count_tokens(text)
        count3 = count_tokens(text)

        assert count1 == count2 == count3

    def test_context_budget_math(self):
        """Test that context budget math is correct."""
        for model in ["gpt-3.5-turbo", "gpt-4", "groq"]:
            max_tokens = get_max_tokens(model)
            budget = get_context_budget(model)

            # Budget should be 75% of max
            expected_budget = int(max_tokens * 0.75)
            assert budget == expected_budget

            # Remaining 25% for response
            remaining = max_tokens - budget
            assert remaining == int(max_tokens * 0.25)
