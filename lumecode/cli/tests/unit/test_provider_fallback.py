"""
Tests for LLM Provider Fallback System
Tests the automatic fallback from Groq → OpenRouter → Mock
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from lumecode.cli.core.llm import (
    get_provider,
    get_provider_with_fallback,
    list_available_providers,
    GroqProvider,
    OpenRouterProvider,
    MockProvider
)


class TestProviderAttributes:
    """Test that all providers have the provider_name attribute"""
    
    def test_groq_provider_name(self):
        """Test Groq provider has provider_name attribute"""
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test-key'}):
            provider = GroqProvider()
            assert hasattr(provider, 'provider_name')
            assert provider.provider_name == 'groq'
    
    def test_openrouter_provider_name(self):
        """Test OpenRouter provider has provider_name attribute"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}):
            provider = OpenRouterProvider()
            assert hasattr(provider, 'provider_name')
            assert provider.provider_name == 'openrouter'
    
    def test_mock_provider_name(self):
        """Test Mock provider has provider_name attribute"""
        provider = MockProvider()
        assert hasattr(provider, 'provider_name')
        assert provider.provider_name == 'mock'


class TestProviderFallback:
    """Test the provider fallback chain"""
    
    def test_fallback_no_keys_uses_mock(self):
        """When no API keys are set, should fall back to mock provider"""
        with patch.dict(os.environ, {}, clear=True):
            provider = get_provider_with_fallback('groq', verbose=False)
            assert isinstance(provider, MockProvider)
            assert provider.provider_name == 'mock'
    
    def test_fallback_groq_available(self):
        """When Groq key is available, should use Groq"""
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test-key'}):
            provider = get_provider_with_fallback('groq', verbose=False)
            assert isinstance(provider, GroqProvider)
            assert provider.provider_name == 'groq'
    
    def test_fallback_openrouter_available(self):
        """When OpenRouter key is available, should use OpenRouter"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}):
            provider = get_provider_with_fallback('openrouter', verbose=False)
            assert isinstance(provider, OpenRouterProvider)
            assert provider.provider_name == 'openrouter'
    
    def test_fallback_groq_to_openrouter(self):
        """When requesting Groq but only OpenRouter available, should fall back"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}, clear=True):
            provider = get_provider_with_fallback('groq', verbose=False)
            assert isinstance(provider, OpenRouterProvider)
            assert provider.provider_name == 'openrouter'
    
    def test_fallback_openrouter_to_groq(self):
        """When requesting OpenRouter but only Groq available, should fall back"""
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test-key'}, clear=True):
            provider = get_provider_with_fallback('openrouter', verbose=False)
            assert isinstance(provider, GroqProvider)
            assert provider.provider_name == 'groq'
    
    def test_fallback_mock_always_works(self):
        """Mock provider should always work without API keys"""
        with patch.dict(os.environ, {}, clear=True):
            provider = get_provider_with_fallback('mock', verbose=False)
            assert isinstance(provider, MockProvider)
            assert provider.provider_name == 'mock'
    
    def test_fallback_preserves_model(self):
        """Fallback should preserve model preference when possible"""
        with patch.dict(os.environ, {}, clear=True):
            provider = get_provider_with_fallback('groq', model='llama-70b', verbose=False)
            # Should fall back to mock, but model parameter should be handled
            assert isinstance(provider, MockProvider)
            assert provider.model == 'llama-70b'  # Model should be preserved


class TestListAvailableProviders:
    """Test the list_available_providers function"""
    
    def test_no_keys_only_mock(self):
        """With no API keys, only mock should be available"""
        with patch.dict(os.environ, {}, clear=True):
            providers = list_available_providers()
            assert 'mock' in providers
            assert 'groq' not in providers
            assert 'openrouter' not in providers
    
    def test_groq_key_available(self):
        """With Groq key, Groq and mock should be available"""
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test-key'}, clear=True):
            providers = list_available_providers()
            assert 'groq' in providers
            assert 'mock' in providers
            assert 'openrouter' not in providers
    
    def test_openrouter_key_available(self):
        """With OpenRouter key, OpenRouter and mock should be available"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}, clear=True):
            providers = list_available_providers()
            assert 'openrouter' in providers
            assert 'mock' in providers
            assert 'groq' not in providers
    
    def test_all_keys_available(self):
        """With all keys, all providers should be available"""
        with patch.dict(os.environ, {
            'GROQ_API_KEY': 'test-key',
            'OPENROUTER_API_KEY': 'test-key'
        }):
            providers = list_available_providers()
            assert 'groq' in providers
            assert 'openrouter' in providers
            assert 'mock' in providers


class TestProviderDetection:
    """Test that commands can detect when fallback occurred"""
    
    def test_detect_fallback_in_command(self):
        """Test detection pattern used in commands"""
        with patch.dict(os.environ, {}, clear=True):
            requested_provider = 'groq'
            llm = get_provider_with_fallback(requested_provider, verbose=False)
            actual_provider = getattr(llm, 'provider_name', requested_provider)
            
            # Should detect that fallback occurred
            assert actual_provider != requested_provider
            assert actual_provider == 'mock'
    
    def test_no_fallback_detection(self):
        """Test when no fallback occurs"""
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test-key'}):
            requested_provider = 'groq'
            llm = get_provider_with_fallback(requested_provider, verbose=False)
            actual_provider = getattr(llm, 'provider_name', requested_provider)
            
            # Should detect that no fallback occurred
            assert actual_provider == requested_provider
            assert actual_provider == 'groq'


class TestProviderBasicFunctionality:
    """Test that providers still work correctly with new provider_name attribute"""
    
    def test_mock_provider_completion(self):
        """Test mock provider still generates completions"""
        provider = MockProvider()
        assert provider.provider_name == 'mock'
        
        response = provider.complete("test prompt")
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_mock_provider_streaming(self):
        """Test mock provider still streams"""
        provider = MockProvider()
        assert provider.provider_name == 'mock'
        
        chunks = list(provider.stream_complete("test prompt"))
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)


class TestProviderErrorMessages:
    """Test that error messages are still helpful"""
    
    def test_groq_error_message_helpful(self):
        """Test Groq error message guides users"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as excinfo:
                GroqProvider()
            
            error_msg = str(excinfo.value)
            assert 'Groq API key required' in error_msg
            assert 'https://console.groq.com' in error_msg
            assert 'GROQ_API_KEY' in error_msg
    
    def test_openrouter_error_message_helpful(self):
        """Test OpenRouter error message guides users"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as excinfo:
                OpenRouterProvider()
            
            error_msg = str(excinfo.value)
            assert 'OpenRouter API key required' in error_msg
            assert 'https://openrouter.ai' in error_msg
            assert 'OPENROUTER_API_KEY' in error_msg


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
