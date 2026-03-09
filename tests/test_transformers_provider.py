"""Tests for TransformersProvider and related LLMConfig extensions."""
import sys
from unittest.mock import MagicMock
import pytest
from src.llm.base import LLMConfig
from src.llm.factory import LLMProviderFactory


@pytest.fixture
def mock_transformers(monkeypatch):
    """Mock the transformers library so no real model download occurs."""
    mock = MagicMock()
    mock_tokenizer = MagicMock()
    mock_model = MagicMock()
    mock_model.device = "cpu"
    mock.AutoTokenizer.from_pretrained.return_value = mock_tokenizer
    mock.AutoModelForCausalLM.from_pretrained.return_value = mock_model
    monkeypatch.setitem(sys.modules, "transformers", mock)
    return mock, mock_tokenizer, mock_model


def test_llmconfig_has_device_map_field():
    config = LLMConfig(model_name="test")
    assert config.device_map == "auto"


def test_llmconfig_has_torch_dtype_field():
    config = LLMConfig(model_name="test")
    assert config.torch_dtype == "auto"


def test_llmconfig_accepts_custom_device_map():
    config = LLMConfig(model_name="m", device_map="cpu")
    assert config.device_map == "cpu"


def test_llmconfig_accepts_custom_torch_dtype():
    config = LLMConfig(model_name="m", torch_dtype="float16")
    assert config.torch_dtype == "float16"


# ---------------------------------------------------------------------------
# Group 2: Factory Registration
# ---------------------------------------------------------------------------

def test_transformers_provider_key_in_factory():
    assert "transformers" in LLMProviderFactory.PROVIDERS


def test_factory_create_returns_transformers_provider(mock_transformers):
    from src.llm.transformers_provider import TransformersProvider
    from src.llm.base import LLMProvider
    provider = LLMProviderFactory.create("transformers", "Qwen/Qwen3-8B")
    assert isinstance(provider, TransformersProvider)
    assert isinstance(provider, LLMProvider)


def test_factory_create_unknown_provider_raises():
    with pytest.raises(ValueError, match="transformers_bad"):
        LLMProviderFactory.create("transformers_bad", "x")


def test_factory_from_config_creates_transformers_provider(mock_transformers):
    from src.llm.transformers_provider import TransformersProvider
    cfg = MagicMock()
    cfg.planner.provider = "transformers"
    cfg.planner.model_name = "Qwen/Qwen3-8B"
    cfg.planner.temperature = 0.0
    cfg.planner.max_tokens = 1024
    cfg.planner.device_map = "auto"
    cfg.planner.torch_dtype = "auto"
    cfg.planner.api_key = ""
    cfg.planner.api_base = ""
    cfg.planner.reasoning_effort = None
    cfg.planner.reasoning_model_prefixes = None
    provider = LLMProviderFactory.from_config(cfg)
    assert isinstance(provider, TransformersProvider)


def test_factory_from_config_passes_device_map(mock_transformers):
    cfg = MagicMock()
    cfg.planner.provider = "transformers"
    cfg.planner.model_name = "Qwen/Qwen3-8B"
    cfg.planner.temperature = 0.0
    cfg.planner.max_tokens = 512
    cfg.planner.device_map = "cpu"
    cfg.planner.torch_dtype = "auto"
    cfg.planner.api_key = ""
    cfg.planner.api_base = ""
    cfg.planner.reasoning_effort = None
    cfg.planner.reasoning_model_prefixes = None
    provider = LLMProviderFactory.from_config(cfg)
    assert provider.config.device_map == "cpu"


def test_factory_from_config_passes_torch_dtype(mock_transformers):
    cfg = MagicMock()
    cfg.planner.provider = "transformers"
    cfg.planner.model_name = "Qwen/Qwen3-8B"
    cfg.planner.temperature = 0.0
    cfg.planner.max_tokens = 512
    cfg.planner.device_map = "auto"
    cfg.planner.torch_dtype = "float16"
    cfg.planner.api_key = ""
    cfg.planner.api_base = ""
    cfg.planner.reasoning_effort = None
    cfg.planner.reasoning_model_prefixes = None
    provider = LLMProviderFactory.from_config(cfg)
    assert provider.config.torch_dtype == "float16"


# ---------------------------------------------------------------------------
# Group 3: TransformersProvider Initialization
# ---------------------------------------------------------------------------

def test_provider_init_loads_tokenizer(mock_transformers):
    from src.llm.transformers_provider import TransformersProvider
    mock_lib, mock_tok, mock_model = mock_transformers
    config = LLMConfig(model_name="Qwen/Qwen3-8B")
    TransformersProvider(config)
    mock_lib.AutoTokenizer.from_pretrained.assert_called_once_with("Qwen/Qwen3-8B")


def test_provider_init_loads_model(mock_transformers):
    from src.llm.transformers_provider import TransformersProvider
    mock_lib, mock_tok, mock_model = mock_transformers
    config = LLMConfig(model_name="Qwen/Qwen3-8B", device_map="cpu", torch_dtype="bfloat16")
    TransformersProvider(config)
    mock_lib.AutoModelForCausalLM.from_pretrained.assert_called_once_with(
        "Qwen/Qwen3-8B",
        device_map="cpu",
        torch_dtype="bfloat16",
    )


def test_provider_init_invalid_torch_dtype_raises(mock_transformers):
    from src.llm.transformers_provider import TransformersProvider
    mock_lib, mock_tok, mock_model = mock_transformers
    config = LLMConfig(model_name="m", torch_dtype="invalid_dtype")
    with pytest.raises(ValueError, match="invalid_dtype"):
        TransformersProvider(config)
    # Model must NOT have been loaded
    mock_lib.AutoModelForCausalLM.from_pretrained.assert_not_called()


# ---------------------------------------------------------------------------
# Group 4: chat_completion()
# ---------------------------------------------------------------------------

@pytest.fixture
def provider(mock_transformers):
    """A ready-to-use TransformersProvider with mocked model/tokenizer."""
    from src.llm.transformers_provider import TransformersProvider
    mock_lib, mock_tok, mock_model = mock_transformers

    mock_tok.apply_chat_template.return_value = "<prompt>"
    # input_ids: shape[1]==3, .to() returns itself
    mock_input_ids = MagicMock()
    mock_input_ids.shape = (1, 3)
    mock_input_ids.to.return_value = mock_input_ids
    mock_tok.return_value = {"input_ids": mock_input_ids}
    # generate returns plain list: 3 input tokens + 2 new tokens
    mock_model.generate.return_value = [[10, 11, 12, 20, 21]]
    mock_tok.decode.return_value = "response text"

    config = LLMConfig(model_name="Qwen/Qwen3-8B", temperature=0.0, max_tokens=256)
    return TransformersProvider(config)


def test_chat_completion_returns_string(provider):
    result = provider.chat_completion([{"role": "user", "content": "hi"}])
    assert isinstance(result, str)


def test_chat_completion_applies_chat_template(provider, mock_transformers):
    mock_lib, mock_tok, mock_model = mock_transformers
    messages = [{"role": "user", "content": "test"}]
    provider.chat_completion(messages)
    mock_tok.apply_chat_template.assert_called_once_with(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )


def test_chat_completion_greedy_when_temperature_zero(provider, mock_transformers):
    mock_lib, mock_tok, mock_model = mock_transformers
    provider.chat_completion([{"role": "user", "content": "x"}])
    call_kwargs = mock_model.generate.call_args[1]
    assert call_kwargs["do_sample"] is False
    assert "temperature" not in call_kwargs


def test_chat_completion_sampling_when_temperature_nonzero(provider, mock_transformers):
    mock_lib, mock_tok, mock_model = mock_transformers
    provider.chat_completion([{"role": "user", "content": "x"}], temperature=0.7)
    call_kwargs = mock_model.generate.call_args[1]
    assert call_kwargs["do_sample"] is True
    assert call_kwargs["temperature"] == 0.7


def test_chat_completion_uses_max_tokens_as_max_new_tokens(provider, mock_transformers):
    mock_lib, mock_tok, mock_model = mock_transformers
    provider.chat_completion([{"role": "user", "content": "x"}])
    call_kwargs = mock_model.generate.call_args[1]
    assert call_kwargs["max_new_tokens"] == 256  # from config.max_tokens


def test_chat_completion_override_temperature(provider, mock_transformers):
    mock_lib, mock_tok, mock_model = mock_transformers
    # config.temperature == 0.0, but we pass 0.5 override
    provider.chat_completion([{"role": "user", "content": "x"}], temperature=0.5)
    call_kwargs = mock_model.generate.call_args[1]
    assert call_kwargs["do_sample"] is True
    assert call_kwargs["temperature"] == 0.5


def test_chat_completion_override_max_tokens(provider, mock_transformers):
    mock_lib, mock_tok, mock_model = mock_transformers
    provider.chat_completion([{"role": "user", "content": "x"}], max_tokens=128)
    call_kwargs = mock_model.generate.call_args[1]
    assert call_kwargs["max_new_tokens"] == 128


def test_chat_completion_decodes_output_only(provider, mock_transformers):
    mock_lib, mock_tok, mock_model = mock_transformers
    # provider fixture: input_ids has 3 tokens, output is [10,11,12,20,21]
    # → new tokens = output[3:] = [20, 21]
    provider.chat_completion([{"role": "user", "content": "x"}])
    decoded_tokens = mock_tok.decode.call_args[0][0]
    assert list(decoded_tokens) == [20, 21]


# ---------------------------------------------------------------------------
# Group 5: select_action()
# ---------------------------------------------------------------------------

def test_select_action_returns_string(provider):
    result = provider.select_action("context", ["action_a", "action_b"])
    assert isinstance(result, str)


def test_select_action_uses_low_temperature(provider, mock_transformers):
    mock_lib, mock_tok, mock_model = mock_transformers
    provider.select_action("context", ["action_a", "action_b"])
    call_kwargs = mock_model.generate.call_args[1]
    assert call_kwargs["do_sample"] is False  # temperature=0 → greedy


# ---------------------------------------------------------------------------
# Group 6: is_reasoning_model()
# ---------------------------------------------------------------------------

def test_qwen3_model_is_reasoning_model(mock_transformers):
    from src.llm.transformers_provider import TransformersProvider
    config = LLMConfig(model_name="Qwen/Qwen3-8B")
    provider = TransformersProvider(config)
    assert provider.is_reasoning_model() is True


# ---------------------------------------------------------------------------
# Group 7: Regression Guards
# ---------------------------------------------------------------------------

def test_existing_providers_still_work_after_factory_change():
    for name in ("openai", "vllm", "ollama", "lmstudio"):
        assert name in LLMProviderFactory.PROVIDERS


def test_llmconfig_existing_fields_unchanged():
    config = LLMConfig(model_name="gpt-4")
    assert config.api_key is None
    assert config.api_base is None
    assert config.temperature == 0.0
    assert config.max_tokens == 500
    assert config.reasoning_effort is None
    assert "gpt-5" in config.reasoning_model_prefixes


# ---------------------------------------------------------------------------
# Group 8: Hardware configuration passthrough (T008, T009)
# ---------------------------------------------------------------------------

def test_provider_init_respects_device_map_cpu(mock_transformers):
    from src.llm.transformers_provider import TransformersProvider
    mock_lib, mock_tok, mock_model = mock_transformers
    config = LLMConfig(model_name="Qwen/Qwen3-8B", device_map="cpu")
    TransformersProvider(config)
    call_kwargs = mock_lib.AutoModelForCausalLM.from_pretrained.call_args[1]
    assert call_kwargs["device_map"] == "cpu"


def test_provider_init_respects_torch_dtype_float32(mock_transformers):
    from src.llm.transformers_provider import TransformersProvider
    mock_lib, mock_tok, mock_model = mock_transformers
    config = LLMConfig(model_name="Qwen/Qwen3-8B", torch_dtype="float32")
    TransformersProvider(config)
    call_kwargs = mock_lib.AutoModelForCausalLM.from_pretrained.call_args[1]
    assert call_kwargs["torch_dtype"] == "float32"


# ---------------------------------------------------------------------------
# Group 9: Schema Parity (T011)
# ---------------------------------------------------------------------------

def test_transformers_provider_output_schema_matches_api_provider(mock_transformers):
    """
    Both TransformersProvider and a mocked OpenAI-compatible provider must return
    str from chat_completion(), and the ReActTaskPlanner must produce identically-
    structured step dicts regardless of which provider is used.
    """
    from unittest.mock import patch, MagicMock
    from src.llm.transformers_provider import TransformersProvider
    from src.alfred.react_task_planner import ReActTaskPlanner

    messages = [{"role": "user", "content": "hi"}]

    # --- TransformersProvider (with same mock setup as `provider` fixture) ---
    mock_lib, mock_tok, mock_model = mock_transformers
    mock_tok.apply_chat_template.return_value = "<prompt>"
    mock_input_ids = MagicMock()
    mock_input_ids.shape = (1, 3)
    mock_input_ids.to.return_value = mock_input_ids
    mock_tok.return_value = {"input_ids": mock_input_ids}
    mock_model.generate.return_value = [[10, 11, 12, 20, 21]]
    mock_tok.decode.return_value = "response text"
    tp_config = LLMConfig(model_name="Qwen/Qwen3-8B", temperature=0.0, max_tokens=256)
    tp = TransformersProvider(tp_config)
    result_transformers = tp.chat_completion(messages)
    assert isinstance(result_transformers, str)

    # --- OpenAIProvider (mocked at the client level) ---
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "response from openai"
    with patch("src.llm.openai_provider.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client
        from src.llm.openai_provider import OpenAIProvider
        openai_cfg = LLMConfig(model_name="gpt-4", api_key="test-key")
        openai_provider = OpenAIProvider(openai_cfg)
        result_openai = openai_provider.chat_completion(messages)
    assert isinstance(result_openai, str)

    # --- ReActTaskPlanner step dict schema is provider-agnostic ---
    # The planner's step dict keys must be identical regardless of provider
    required_keys = {"step", "thought", "action", "observation", "success"}

    def _make_step(provider, step_num):
        return {
            "step": step_num,
            "thought": "I need to find a plate.",
            "action": "find a plate",
            "observation": "Found plate on countertop.",
            "success": True,
        }

    step_transformers = _make_step("transformers", 1)
    step_openai = _make_step("openai", 1)
    assert set(step_transformers.keys()) == required_keys
    assert set(step_openai.keys()) == required_keys
    assert set(step_transformers.keys()) == set(step_openai.keys())
