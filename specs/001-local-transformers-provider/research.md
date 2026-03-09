# Research: Local Transformers Provider for ReAct Experiments

**Feature**: 001-local-transformers-provider
**Date**: 2026-03-05

## Existing Provider Architecture

### Decision: Extend LLMProvider ABC
- **Decision**: Implement `TransformersProvider(LLMProvider)` following the existing Strategy Pattern
- **Rationale**: All providers implement `chat_completion()` and `select_action()`. The factory
  maps string keys to classes via `PROVIDERS` dict. Adding `"transformers"` requires only one
  line in the factory dict and one new file.
- **Alternatives considered**: Subclassing `LLMConfig` for local-specific fields — rejected
  because it breaks the factory's uniform `config = LLMConfig(**kwargs)` construction pattern.

### Decision: Extend LLMConfig with optional device fields
- **Decision**: Add two optional fields to `LLMConfig`: `device_map: str = "auto"` and
  `torch_dtype: str = "auto"`. API-based providers ignore these fields.
- **Rationale**: Keeps a single config class; optional fields with defaults are backward-
  compatible. No existing provider reads `device_map` or `torch_dtype`, so no regressions.
- **Alternatives considered**: Separate `LocalModelConfig` dataclass — rejected because
  `LLMProviderFactory.from_config()` always creates `LLMConfig`, and diverging config types
  would require branching logic in the factory.

---

## Qwen3-8B Model Specifics

### Decision: Use chat template with `enable_thinking=False` by default
- **Decision**: Call `tokenizer.apply_chat_template(messages, tokenize=False,
  add_generation_prompt=True, enable_thinking=False)` to format the prompt.
- **Rationale**: Qwen3 has two modes: thinking (chain-of-thought inside `<think>` tags)
  and non-thinking. The existing `ReActTaskPlanner` sanitizer already strips `<think>` blocks,
  so thinking mode is compatible but wastes tokens. Non-thinking mode produces more concise
  JSON responses suited to the ReAct loop format.
- **Alternatives considered**: `enable_thinking=True` — possible and backward-compatible due
  to sanitizer, but produces larger outputs and slower inference. Deferred to configuration
  option if researchers want it.

### Decision: Qwen3-8B is already recognized as a reasoning model
- **Finding**: `LLMConfig.reasoning_model_prefixes` already contains `"qwen3"`. The
  `is_reasoning_model()` method will return `True` for `Qwen/Qwen3-8B`. The `TransformersProvider`
  can use this to conditionally enable thinking mode if desired.
- **Impact**: No changes needed to reasoning model detection logic.

---

## Device and Precision Management

### Decision: Use `device_map="auto"` as the default strategy
- **Decision**: Pass `device_map="auto"` to `AutoModelForCausalLM.from_pretrained()` by default.
- **Rationale**: `device_map="auto"` distributes the model across all available GPUs using
  `accelerate`, falling back to CPU if no GPU is available. This handles single-GPU, multi-GPU,
  and CPU-only scenarios with a single setting.
- **Alternatives considered**: Manual device placement (`.to("cuda:0")`) — rejected because it
  fails silently on CPU-only machines and doesn't leverage multi-GPU setups.

### Decision: Default to `torch_dtype="auto"` (resolved at load time)
- **Decision**: Pass `torch_dtype="auto"` to `from_pretrained()`, which loads in the model's
  native dtype (bfloat16 for Qwen3).
- **Rationale**: Avoids hardcoding precision in code; researchers can override via config.
  For Qwen3-8B, `bfloat16` is the native dtype and provides the best accuracy/speed trade-off.
- **Alternatives considered**: Always `bfloat16` — rejected because it fails on older GPUs
  that don't support bfloat16; `float32` — uses 2x memory unnecessarily.

---

## Generation Parameters

### Decision: Map `max_tokens` → `max_new_tokens`
- **Decision**: Pass `config.max_tokens` as `max_new_tokens` to `model.generate()`.
- **Rationale**: `max_tokens` is the established config field shared across all providers.
  `max_new_tokens` in `generate()` controls output length without counting input tokens,
  which matches the intent of the parameter.

### Decision: Map `temperature=0.0` → `do_sample=False`
- **Decision**: When `temperature <= 0.0`, use `do_sample=False` (greedy decoding).
  When `temperature > 0.0`, use `do_sample=True, temperature=temperature`.
- **Rationale**: Unlike the OpenAI API which accepts `temperature=0` for greedy decoding,
  `model.generate()` requires `do_sample=False` explicitly. Mixing `temperature` with
  `do_sample=False` raises a warning in transformers.

---

## Configuration

### Decision: New Hydra config `conf/config_alfred_react_local.yaml`
- **Decision**: Create a new config file inheriting from `config_alfred_react.yaml` with
  local provider settings, rather than modifying the existing config.
- **Rationale**: Preserves existing config for API-based runs; researchers switch between
  local and API modes by selecting config file.
- **Config additions needed**:
  ```yaml
  planner:
    provider: "transformers"
    model_name: "Qwen/Qwen3-8B"
    device_map: "auto"
    torch_dtype: "auto"
    temperature: 0.0
    max_tokens: 1024
  ```
- **Factory change**: `from_config()` must read `device_map` and `torch_dtype` from
  `planner_cfg` and pass them to `LLMProviderFactory.create()`.

---

## Testing Strategy

### Decision: Mock `AutoModelForCausalLM` and `AutoTokenizer` in unit tests
- **Decision**: Unit tests use `unittest.mock.patch` to mock HuggingFace model loading.
  No actual model download required for tests.
- **Rationale**: Tests must be fast enough to run frequently (constitution requirement).
  Downloading Qwen3-8B (~16GB) during CI/testing is not feasible.
- **Test file**: `tests/test_transformers_provider.py`

---

## Dependencies

| Package | Version | Reason |
|---------|---------|--------|
| `transformers` | `>=4.51.0` | Qwen3 chat template support (`enable_thinking` param) |
| `torch` | `>=2.0.0` | Model inference backend |
| `accelerate` | `>=0.26.0` | Required for `device_map="auto"` |

All three are already commonly installed in ML research environments. `transformers` and
`torch` may already be present as transitive dependencies; `accelerate` is needed for
multi-GPU/auto device mapping.
