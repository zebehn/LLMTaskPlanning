# Contract: LLM Provider Interface

**Version**: 2.0 (expanded for reasoning models)

## Base Provider Interface

All LLM providers MUST implement these methods:

### `chat_completion(messages, temperature?, max_tokens?) -> str`

Generate a chat completion response. Reasoning-aware providers adapt parameter handling based on `is_reasoning_model()`.

**Input**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `messages` | `list[dict[str, str]]` | Yes | Chat messages with `role` and `content` |
| `temperature` | `float` or `None` | No | Sampling temperature (default from config) |
| `max_tokens` | `int` or `None` | No | Max tokens to generate (default from config) |

**Output**: `str` — generated text response, stripped of whitespace.

**Error handling**:
- Raises `ConnectionError` if server is unreachable (Ollama, LM Studio)
- Raises `ValueError` for invalid API key (OpenAI)
- Local providers: on reasoning parameter error, falls back to standard params and logs warning

### `select_action(prompt, candidates) -> str`

Select best action from candidates. Uses `chat_completion` internally.

### `is_reasoning_model() -> bool`

Check if the configured model is a reasoning model by matching `model_name` against `config.reasoning_model_prefixes`.

**Logic**: `any(self.model_name.startswith(p) for p in self.config.reasoning_model_prefixes)`

## Provider-Specific Contracts

### OpenAI Provider

| Condition | Parameter Used | Value |
|-----------|---------------|-------|
| Reasoning model | `max_completion_tokens` | from `max_tokens` config |
| Reasoning model + effort configured | `reasoning_effort` | `"low"` / `"medium"` / `"high"` |
| Non-reasoning model | `max_tokens` + `temperature` | from config |

### Ollama Provider

| Condition | Parameter Used | Notes |
|-----------|---------------|-------|
| Any model | `max_tokens` + `temperature` | Always use standard params |
| Reasoning model detection | For logging only | Log that model is recognized as reasoning |

Ollama does NOT support `max_completion_tokens` or `reasoning_effort` reliably. Always use `max_tokens`.

### LM Studio Provider

| Condition | Parameter Used | Notes |
|-----------|---------------|-------|
| Any model | `max_tokens` + `temperature` | Always use standard params |
| Unknown params | Silently ignored | LM Studio is permissive |

### vLLM Provider

| Condition | Parameter Used | Notes |
|-----------|---------------|-------|
| Reasoning model | Try `max_completion_tokens` + `reasoning_effort` | Fallback to standard on error |
| Non-reasoning model | `max_tokens` + `temperature` | Standard params |

## Factory Contract

### `LLMProviderFactory.create(provider_type, model_name, ..., reasoning_model_prefixes?) -> LLMProvider`

Extended with optional `reasoning_model_prefixes` parameter.

### `LLMProviderFactory.from_config(cfg) -> LLMProvider`

Reads `cfg.planner.reasoning_model_prefixes` (list of strings) from Hydra config. Converts to tuple and passes to `LLMConfig`.

## Configuration Contract

### Hydra YAML Schema

```yaml
planner:
  provider: str          # "openai" | "ollama" | "lmstudio" | "vllm"
  model_name: str        # Model identifier
  api_key: str           # API key (empty = use env var)
  api_base: str          # Custom endpoint URL (empty = use default)
  temperature: float     # 0.0 - 2.0
  max_tokens: int        # 1 - 128000
  reasoning_effort: str  # "low" | "medium" | "high" | null
  reasoning_model_prefixes:  # list of str prefixes
    - "gpt-5"
    - "o1"
    - "o3"
    - "o4"
    - "qwen3"
    - "glm-"
    - "kimi-k"
```
