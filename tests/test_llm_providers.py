"""
Test suite for LLM providers.
Tests provider instantiation, factory registration, API compatibility,
and reasoning model detection / parameter handling.
"""
import pytest
import sys
import os
import logging
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from llm import (
    LLMProviderFactory,
    LLMConfig,
    OpenAIProvider,
    VLLMProvider,
    OllamaProvider,
    LMStudioProvider,
)
from llm.base import LLMProvider


class TestProviderFactory:
    """Test LLMProviderFactory functionality."""

    def test_list_providers_includes_all(self):
        """All four providers should be registered."""
        providers = LLMProviderFactory.list_providers()
        assert 'openai' in providers
        assert 'vllm' in providers
        assert 'ollama' in providers
        assert 'lmstudio' in providers

    @patch("llm.ollama_provider.OpenAI")
    def test_create_ollama_provider(self, mock_openai):
        """Factory should create OllamaProvider for 'ollama' type."""
        provider = LLMProviderFactory.create('ollama', 'llama2')
        assert isinstance(provider, OllamaProvider)
        assert provider.model_name == 'llama2'

    @patch("llm.lmstudio_provider.OpenAI")
    def test_create_lmstudio_provider(self, mock_openai):
        """Factory should create LMStudioProvider for 'lmstudio' type."""
        provider = LLMProviderFactory.create('lmstudio', 'test-model')
        assert isinstance(provider, LMStudioProvider)
        assert provider.model_name == 'test-model'

    @patch("llm.lmstudio_provider.OpenAI")
    def test_create_with_custom_api_base(self, mock_openai):
        """Custom api_base should be respected."""
        custom_base = 'http://custom-server:9999/v1'
        provider = LLMProviderFactory.create(
            'lmstudio',
            'model',
            api_base=custom_base
        )
        assert provider.api_base == custom_base

    def test_unknown_provider_raises_error(self):
        """Unknown provider type should raise ValueError."""
        with pytest.raises(ValueError) as excinfo:
            LLMProviderFactory.create('unknown_provider', 'model')
        assert 'Unknown provider type' in str(excinfo.value)

    def test_legacy_format_ollama(self):
        """Legacy 'ollama/model' format should work."""
        # This tests the from_config path with legacy format
        # We can't easily test from_config without a full config object,
        # but we verify the provider is registered correctly
        providers = LLMProviderFactory.PROVIDERS
        assert 'ollama' in providers
        assert providers['ollama'] == OllamaProvider


class TestOllamaProvider:
    """Test OllamaProvider functionality."""

    def test_default_api_base(self):
        """Default API base should be localhost:11434."""
        assert OllamaProvider.DEFAULT_API_BASE == 'http://localhost:11434/v1'

    @patch("llm.ollama_provider.OpenAI")
    def test_initialization(self, mock_openai):
        """Provider should initialize with correct settings."""
        config = LLMConfig(model_name='llama2')
        provider = OllamaProvider(config)

        assert provider.model_name == 'llama2'
        assert provider.api_base == OllamaProvider.DEFAULT_API_BASE

    @patch("llm.ollama_provider.OpenAI")
    def test_custom_api_base_from_config(self, mock_openai):
        """Custom api_base from config should be used."""
        config = LLMConfig(
            model_name='llama2',
            api_base='http://custom:8080/v1'
        )
        provider = OllamaProvider(config)

        assert provider.api_base == 'http://custom:8080/v1'


class TestLMStudioProvider:
    """Test LMStudioProvider functionality."""

    def test_default_api_base(self):
        """Default API base should be localhost:1234."""
        assert LMStudioProvider.DEFAULT_API_BASE == 'http://localhost:1234/v1'

    @patch("llm.lmstudio_provider.OpenAI")
    def test_initialization(self, mock_openai):
        """Provider should initialize with correct settings."""
        config = LLMConfig(model_name='local-model')
        provider = LMStudioProvider(config)

        assert provider.model_name == 'local-model'
        assert provider.api_base == LMStudioProvider.DEFAULT_API_BASE

    @patch("llm.lmstudio_provider.OpenAI")
    def test_custom_api_base_from_config(self, mock_openai):
        """Custom api_base from config should be used."""
        config = LLMConfig(
            model_name='model',
            api_base='http://10.254.90.90:1234/v1'
        )
        provider = LMStudioProvider(config)

        assert provider.api_base == 'http://10.254.90.90:1234/v1'


class TestProviderInterface:
    """Test that all providers implement the required interface."""

    @pytest.fixture(params=['ollama', 'lmstudio'])
    def provider(self, request):
        """Create provider instance for each type."""
        patch_target = f"llm.{request.param}_provider.OpenAI"
        with patch(patch_target):
            return LLMProviderFactory.create(request.param, 'test-model')

    def test_has_chat_completion_method(self, provider):
        """Provider should have chat_completion method."""
        assert hasattr(provider, 'chat_completion')
        assert callable(provider.chat_completion)

    def test_has_select_action_method(self, provider):
        """Provider should have select_action method."""
        assert hasattr(provider, 'select_action')
        assert callable(provider.select_action)

    def test_has_model_name(self, provider):
        """Provider should have model_name attribute."""
        assert hasattr(provider, 'model_name')
        assert provider.model_name == 'test-model'


# ===== Phase 2: Reasoning Model Detection Tests (US4) T002-T006 =====


class TestReasoningModelDetection:
    """Test centralized is_reasoning_model() on the base class."""

    def _make_provider(self, model_name, **config_kwargs):
        """Helper: create an OllamaProvider (lightest, no API key needed) for detection tests."""
        config = LLMConfig(model_name=model_name, **config_kwargs)
        with patch("llm.ollama_provider.OpenAI"):
            return OllamaProvider(config)

    # T002
    def test_is_reasoning_model_gpt5_variants(self):
        """gpt-5.2, gpt-5-mini, gpt-5-nano should be detected as reasoning models."""
        for name in ("gpt-5.2", "gpt-5-mini", "gpt-5-nano"):
            provider = self._make_provider(name)
            assert provider.is_reasoning_model() is True, f"{name} should be a reasoning model"

    # T003
    def test_is_reasoning_model_open_source(self):
        """qwen3.5, glm-5, kimi-k2.5 should be detected as reasoning models."""
        for name in ("qwen3.5", "glm-5", "kimi-k2.5"):
            provider = self._make_provider(name)
            assert provider.is_reasoning_model() is True, f"{name} should be a reasoning model"

    # T004
    def test_is_reasoning_model_false_for_standard(self):
        """gpt-4, gpt-3.5-turbo, llama3, mistral should NOT be reasoning models."""
        for name in ("gpt-4", "gpt-3.5-turbo", "llama3", "mistral"):
            provider = self._make_provider(name)
            assert provider.is_reasoning_model() is False, f"{name} should NOT be a reasoning model"

    # T005
    def test_custom_reasoning_prefixes_override(self):
        """Custom reasoning_model_prefixes in LLMConfig should override defaults."""
        config = LLMConfig(
            model_name="my-custom-reasoning-v1",
            reasoning_model_prefixes=("my-custom-",)
        )
        with patch("llm.ollama_provider.OpenAI"):
            provider = OllamaProvider(config)
        assert provider.is_reasoning_model() is True

        # Default prefixes should no longer match
        config2 = LLMConfig(
            model_name="gpt-5.2",
            reasoning_model_prefixes=("my-custom-",)
        )
        with patch("llm.ollama_provider.OpenAI"):
            provider2 = OllamaProvider(config2)
        assert provider2.is_reasoning_model() is False

    # T006
    def test_factory_passes_reasoning_prefixes(self):
        """Factory.create() should pass reasoning_model_prefixes to LLMConfig."""
        custom = ("test-prefix",)
        with patch("llm.ollama_provider.OpenAI"):
            provider = LLMProviderFactory.create(
                "ollama", "test-prefix-model",
                reasoning_model_prefixes=custom,
            )
        assert provider.config.reasoning_model_prefixes == custom
        assert provider.is_reasoning_model() is True


# ===== Phase 3: OpenAI Reasoning Parameter Tests (US1) T014-T016 =====


class TestOpenAIReasoningParams:
    """Test OpenAI provider parameter handling for reasoning vs standard models."""

    def _make_openai_provider(self, model_name, reasoning_effort=None):
        """Helper: create OpenAI provider with a mocked client."""
        config = LLMConfig(
            model_name=model_name,
            api_key="test-key",
            reasoning_effort=reasoning_effort,
        )
        with patch("llm.openai_provider.OpenAI"):
            provider = OpenAIProvider(config)
        provider.client = MagicMock()
        # Mock the response chain
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "test response"
        provider.client.chat.completions.create.return_value = mock_response
        return provider

    # T014
    def test_openai_reasoning_model_uses_max_completion_tokens(self):
        """Reasoning model should use max_completion_tokens, not max_tokens."""
        provider = self._make_openai_provider("gpt-5-mini")
        provider.chat_completion([{"role": "user", "content": "test"}])

        call_kwargs = provider.client.chat.completions.create.call_args[1]
        assert "max_completion_tokens" in call_kwargs
        assert "max_tokens" not in call_kwargs

    # T015
    def test_openai_reasoning_model_passes_reasoning_effort(self):
        """Reasoning model with effort configured should pass reasoning_effort."""
        provider = self._make_openai_provider("gpt-5.2", reasoning_effort="low")
        provider.chat_completion([{"role": "user", "content": "test"}])

        call_kwargs = provider.client.chat.completions.create.call_args[1]
        assert call_kwargs["reasoning_effort"] == "low"
        assert "max_completion_tokens" in call_kwargs

    # T016
    def test_openai_non_reasoning_model_uses_max_tokens(self):
        """Non-reasoning model should use max_tokens + temperature."""
        provider = self._make_openai_provider("gpt-4")
        provider.chat_completion([{"role": "user", "content": "test"}])

        call_kwargs = provider.client.chat.completions.create.call_args[1]
        assert "max_tokens" in call_kwargs
        assert "temperature" in call_kwargs
        assert "max_completion_tokens" not in call_kwargs
        assert "reasoning_effort" not in call_kwargs


# ===== Phase 4: Ollama Reasoning Parameter Tests (US2) T019-T021 =====


class TestOllamaReasoningParams:
    """Test Ollama provider always uses standard params for reasoning models."""

    def _make_ollama_provider(self, model_name, reasoning_effort=None):
        """Helper: create Ollama provider with a mocked client."""
        config = LLMConfig(
            model_name=model_name,
            reasoning_effort=reasoning_effort,
        )
        with patch("llm.ollama_provider.OpenAI"):
            provider = OllamaProvider(config)
        provider.client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "test response"
        provider.client.chat.completions.create.return_value = mock_response
        return provider

    # T019
    def test_ollama_reasoning_model_uses_standard_params(self):
        """Ollama should always use max_tokens + temperature even for reasoning models."""
        provider = self._make_ollama_provider("qwen3.5")
        provider.chat_completion([{"role": "user", "content": "test"}])

        call_kwargs = provider.client.chat.completions.create.call_args[1]
        assert "max_tokens" in call_kwargs
        assert "temperature" in call_kwargs
        assert "max_completion_tokens" not in call_kwargs

    # T020
    def test_ollama_does_not_pass_reasoning_effort(self):
        """Ollama should NOT pass reasoning_effort even when configured."""
        provider = self._make_ollama_provider("qwen3.5", reasoning_effort="medium")
        provider.chat_completion([{"role": "user", "content": "test"}])

        call_kwargs = provider.client.chat.completions.create.call_args[1]
        assert "reasoning_effort" not in call_kwargs

    # T021
    def test_ollama_reasoning_model_logs_detection(self, caplog):
        """Ollama should log when it detects a reasoning model."""
        provider = self._make_ollama_provider("glm-5")
        with caplog.at_level(logging.INFO, logger="llm.ollama_provider"):
            provider.chat_completion([{"role": "user", "content": "test"}])
        assert "Reasoning model" in caplog.text
        assert "glm-5" in caplog.text


# ===== Phase 5: LM Studio Reasoning Parameter Tests (US3) T024-T025 =====


class TestLMStudioReasoningParams:
    """Test LM Studio provider always uses standard params for reasoning models."""

    def _make_lmstudio_provider(self, model_name, reasoning_effort=None):
        """Helper: create LM Studio provider with a mocked client."""
        config = LLMConfig(
            model_name=model_name,
            reasoning_effort=reasoning_effort,
        )
        with patch("llm.lmstudio_provider.OpenAI"):
            provider = LMStudioProvider(config)
        provider.client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "test response"
        provider.client.chat.completions.create.return_value = mock_response
        return provider

    # T024
    def test_lmstudio_reasoning_model_uses_standard_params(self):
        """LM Studio should always use max_tokens + temperature for reasoning models."""
        provider = self._make_lmstudio_provider("kimi-k2.5")
        provider.chat_completion([{"role": "user", "content": "test"}])

        call_kwargs = provider.client.chat.completions.create.call_args[1]
        assert "max_tokens" in call_kwargs
        assert "temperature" in call_kwargs
        assert "max_completion_tokens" not in call_kwargs

    # T025
    def test_lmstudio_reasoning_model_logs_detection(self, caplog):
        """LM Studio should log when it detects a reasoning model."""
        provider = self._make_lmstudio_provider("kimi-k2.5")
        with caplog.at_level(logging.INFO, logger="llm.lmstudio_provider"):
            provider.chat_completion([{"role": "user", "content": "test"}])
        assert "Reasoning model" in caplog.text
        assert "kimi-k2.5" in caplog.text


# ===== Phase 6: vLLM Reasoning Parameter Tests T028-T029 =====


class TestVLLMReasoningParams:
    """Test vLLM provider reasoning-aware parameter handling with fallback."""

    def _make_vllm_provider(self, model_name, reasoning_effort=None):
        """Helper: create vLLM provider with a mocked client."""
        config = LLMConfig(
            model_name=model_name,
            reasoning_effort=reasoning_effort,
        )
        with patch("llm.vllm_provider.OpenAI"):
            provider = VLLMProvider(config)
        provider.client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "test response"
        provider.client.chat.completions.create.return_value = mock_response
        return provider

    # T028
    def test_vllm_reasoning_model_with_fallback(self):
        """vLLM should fallback to standard params when reasoning params fail."""
        provider = self._make_vllm_provider("qwen3.5", reasoning_effort="high")

        # First call (reasoning params) raises error, second call (fallback) succeeds
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "fallback response"
        provider.client.chat.completions.create.side_effect = [
            Exception("max_completion_tokens not supported"),
            mock_response,
        ]

        result = provider.chat_completion([{"role": "user", "content": "test"}])
        assert result == "fallback response"
        assert provider.client.chat.completions.create.call_count == 2

        # Second call should use standard params
        fallback_kwargs = provider.client.chat.completions.create.call_args_list[1][1]
        assert "max_tokens" in fallback_kwargs
        assert "temperature" in fallback_kwargs

    # T029
    def test_vllm_non_reasoning_uses_standard_params(self):
        """Non-reasoning model on vLLM should use standard params."""
        provider = self._make_vllm_provider("llama3")
        provider.chat_completion([{"role": "user", "content": "test"}])

        call_kwargs = provider.client.chat.completions.create.call_args[1]
        assert "max_tokens" in call_kwargs
        assert "temperature" in call_kwargs
        assert "max_completion_tokens" not in call_kwargs


# Integration tests (require running server)
@pytest.mark.integration
class TestLMStudioIntegration:
    """Integration tests requiring a running LM Studio server."""

    @pytest.fixture
    def lmstudio_provider(self):
        """Create LM Studio provider with test server."""
        # Skip if LMSTUDIO_TEST_BASE not set
        test_base = os.getenv('LMSTUDIO_TEST_BASE')
        test_model = os.getenv('LMSTUDIO_TEST_MODEL', 'test-model')

        if not test_base:
            pytest.skip("LMSTUDIO_TEST_BASE not set")

        return LLMProviderFactory.create(
            'lmstudio',
            test_model,
            api_base=test_base
        )

    def test_chat_completion(self, lmstudio_provider):
        """Test actual chat completion."""
        messages = [
            {'role': 'user', 'content': 'Say "hello" and nothing else.'}
        ]
        response = lmstudio_provider.chat_completion(messages, max_tokens=50)
        assert len(response) > 0

    def test_select_action(self, lmstudio_provider):
        """Test action selection."""
        prompt = "I need to pick up a cup from the table."
        candidates = ["PickupObject cup", "GoToObject table", "OpenObject door"]

        action = lmstudio_provider.select_action(prompt, candidates)
        assert action in candidates or any(c in action for c in candidates)


if __name__ == '__main__':
    # Run unit tests only (not integration tests)
    pytest.main([__file__, '-v', '-m', 'not integration'])
