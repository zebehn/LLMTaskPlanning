# Contract: LLMProvider Interface

**Feature**: 001-local-transformers-provider
**Date**: 2026-03-05

This document defines the interface contract that `TransformersProvider` MUST fulfill
to be a valid `LLMProvider` implementation. All existing providers satisfy this contract;
the new provider must not deviate.

---

## Interface: `LLMProvider.chat_completion()`

```python
def chat_completion(
    self,
    messages: List[Dict[str, str]],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> str
```

**Pre-conditions**:
- `messages` is a non-empty list of dicts with exactly the keys `"role"` and `"content"`
- `role` values are `"system"`, `"user"`, or `"assistant"`
- `temperature` is `None` (use config default) or a float in `[0.0, 2.0]`
- `max_tokens` is `None` (use config default) or a positive integer

**Post-conditions**:
- Returns a non-None `str` (may be empty if model generates empty output)
- Does NOT raise exceptions for normal generation (only for initialization failures)
- Response is the raw generated text; caller is responsible for parsing

**Behavior**:
- When `temperature` argument is provided, it overrides `config.temperature` for this call
- When `max_tokens` argument is provided, it overrides `config.max_tokens` for this call
- The response MUST NOT include the input prompt or system message — only the generated text

---

## Interface: `LLMProvider.select_action()`

```python
def select_action(
    self,
    prompt: str,
    candidates: List[str]
) -> str
```

**Pre-conditions**:
- `prompt` is a non-empty string describing the current task context
- `candidates` is a non-empty list of candidate action strings

**Post-conditions**:
- Returns one of the strings from `candidates` (or a string very close to one)
- Uses low temperature (0 or near-deterministic) for consistency

**Behavior**:
- SHOULD delegate to `chat_completion()` via `_build_selection_messages()`
- Response is expected to be brief (the selected action, not a long explanation)

---

## `LLMConfig` Contract for TransformersProvider

The following fields from `LLMConfig` MUST be respected:

| Field | Contract |
|-------|----------|
| `model_name` | Used as the HuggingFace model identifier for loading |
| `temperature` | Applied to generation; `0.0` MUST produce deterministic (greedy) output |
| `max_tokens` | Applied as `max_new_tokens`; controls output length only (not input) |
| `device_map` | Passed to `from_pretrained()` for device placement |
| `torch_dtype` | Passed to `from_pretrained()` for model precision |

Fields `api_key`, `api_base`, `reasoning_effort` are intentionally ignored by
`TransformersProvider` (they are API-provider-specific).

---

## Factory Contract

After registering `"transformers": TransformersProvider` in `PROVIDERS`:

```python
provider = LLMProviderFactory.create(
    provider_type="transformers",
    model_name="Qwen/Qwen3-8B",
    temperature=0.0,
    max_tokens=1024
)
# provider MUST be an instance of TransformersProvider and LLMProvider
assert isinstance(provider, LLMProvider)
assert isinstance(provider, TransformersProvider)
```

`LLMProviderFactory.from_config(cfg)` with `cfg.planner.provider = "transformers"`
MUST produce a valid `TransformersProvider` with `device_map` and `torch_dtype` read
from `cfg.planner`.

---

## Evaluation Output Contract (unchanged)

The ReAct evaluator expects `chat_completion()` to return a `str` that it will
parse as a JSON object with keys `"Think"` and `"Act"`. The `TransformersProvider`
has no special responsibility here — it returns the raw model output as a string,
and the existing `ReActTaskPlanner` handles all parsing and sanitization (including
`<think>` block stripping).

This means the provider is completely decoupled from output parsing.
