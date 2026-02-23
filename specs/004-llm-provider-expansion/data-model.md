# Data Model: LLM Provider Expansion for Reasoning Models

**Date**: 2026-02-23 | **Branch**: `004-llm-provider-expansion`

## Entities

### LLMConfig (modified)

Configuration dataclass for LLM providers. Extended with reasoning model prefixes.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `model_name` | `str` | (required) | Model identifier (e.g., "gpt-5-mini", "qwen3.5") |
| `api_key` | `Optional[str]` | `None` | API key for authentication |
| `api_base` | `Optional[str]` | `None` | Custom API endpoint URL |
| `temperature` | `float` | `0.0` | Sampling temperature |
| `max_tokens` | `int` | `500` | Max tokens for generation |
| `reasoning_effort` | `Optional[str]` | `None` | "low", "medium", "high" for reasoning models |
| `reasoning_model_prefixes` | `tuple[str, ...]` | `("gpt-5", "o1", "o3", "o4", "qwen3", "glm-", "kimi-k")` | Model name prefixes that indicate reasoning models |

### Reasoning Model Registry (new concept, embedded in LLMConfig)

A tuple of string prefixes used to detect reasoning models. Checked via `model_name.startswith(prefix)` for any prefix in the tuple.

**Default prefixes**:

| Prefix | Models Covered |
|--------|---------------|
| `gpt-5` | gpt-5.2, gpt-5-mini, gpt-5-nano |
| `o1` | o1, o1-mini, o1-preview |
| `o3` | o3, o3-mini |
| `o4` | o4-mini |
| `qwen3` | qwen3.5, qwen3-8B, etc. |
| `glm-` | glm-5, glm-4.5, etc. |
| `kimi-k` | kimi-k2.5, kimi-k1.5, etc. |

### Provider Parameter Handling (behavioral model)

Each provider adapts its `chat_completion()` call based on whether the model is a reasoning model:

| Provider | Reasoning Model | Non-Reasoning Model |
|----------|----------------|---------------------|
| **OpenAI** | `max_completion_tokens` + `reasoning_effort` | `temperature` + `max_tokens` |
| **Ollama** | `max_tokens` only (fallback; no `reasoning_effort`) | `temperature` + `max_tokens` |
| **LM Studio** | `max_tokens` only (params silently ignored) | `temperature` + `max_tokens` |
| **vLLM** | `max_completion_tokens` + `reasoning_effort` (try/except fallback) | `temperature` + `max_tokens` |

### Hydra Configuration Schema (modified)

```yaml
planner:
  provider: "openai"          # openai | ollama | lmstudio | vllm
  model_name: "gpt-5-mini"
  api_key: ''
  api_base: ''
  temperature: 0.0
  max_tokens: 1024
  reasoning_effort: "low"     # low | medium | high (for reasoning models)
  reasoning_model_prefixes:   # configurable prefix list
    - "gpt-5"
    - "o1"
    - "o3"
    - "o4"
    - "qwen3"
    - "glm-"
    - "kimi-k"
```

## Relationships

```
LLMConfig ──has──> reasoning_model_prefixes (tuple of str)
LLMProvider ──uses──> LLMConfig.reasoning_model_prefixes
LLMProvider.is_reasoning_model() ──checks──> model_name against prefixes
OpenAIProvider ──inherits──> LLMProvider (removes local _is_reasoning_model)
OllamaProvider ──inherits──> LLMProvider (gains reasoning detection + fallback)
LMStudioProvider ──inherits──> LLMProvider (gains reasoning detection)
VLLMProvider ──inherits──> LLMProvider (gains reasoning detection + fallback)
LLMProviderFactory.from_config() ──reads──> cfg.planner.reasoning_model_prefixes
```

## State Transitions

No state transitions — all entities are stateless configuration and request/response patterns.

## Validation Rules

- `reasoning_effort` must be one of: `None`, `"low"`, `"medium"`, `"high"`
- `reasoning_model_prefixes` must be a sequence of non-empty strings
- `provider` must be one of the registered provider types
- `api_base` must be a valid URL if provided
