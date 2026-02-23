# Implementation Plan: LLM Provider Expansion for Reasoning Models

**Branch**: `004-llm-provider-expansion` | **Date**: 2026-02-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-llm-provider-expansion/spec.md`

## Summary

Expand the LLM provider system to support reasoning models (OpenAI gpt-5.2/gpt-5-mini/gpt-5-nano, qwen3.5, glm-5, kimi-k2.5) across all four providers (OpenAI, Ollama, LM Studio, vLLM). The core change is centralizing reasoning model detection from `OpenAIProvider` into the base `LLMProvider` class with a configurable prefix registry, then adapting each provider's `chat_completion()` to handle reasoning-specific parameters appropriately for its backend.

Key research findings:
- OpenAI: requires `max_completion_tokens` (not `max_tokens`) for reasoning models
- Ollama: does NOT support `max_completion_tokens` or `reasoning_effort` reliably — always use `max_tokens`
- LM Studio: silently ignores unknown params — use `max_tokens` for safety
- vLLM: supports both, but `max_completion_tokens` has a known budget bug with reasoning parser

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: openai (Python SDK), hydra-core 1.3.2, omegaconf 2.3.0
**Storage**: N/A (configuration-only feature, YAML files)
**Testing**: pytest (unit tests with mocked OpenAI client, no live server required)
**Target Platform**: Linux/macOS (research workstation)
**Project Type**: Single project
**Performance Goals**: N/A (no performance-sensitive changes; API call overhead unchanged)
**Constraints**: Backward compatibility with existing gpt-4/gpt-3.5 configurations
**Scale/Scope**: 6 files modified, ~150 lines of code changed, ~200 lines of tests added

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with TDD and Tidy First principles:

- [x] **TDD Cycle**: Plan includes test-first approach — tests for `is_reasoning_model()` written before moving detection to base class; tests for provider parameter handling written before modifying `chat_completion()` methods
- [x] **Tidy First**: Structural changes (moving `_is_reasoning_model()` to base class) separated from behavioral changes (adding new prefixes, modifying Ollama/LM Studio providers)
- [x] **Commit Discipline**: Plan supports small, atomic commits: `refactor: move reasoning detection to base class` → `feat: add configurable reasoning prefixes` → `feat: add reasoning params to Ollama/LMStudio/vLLM` → `test: add reasoning model tests`
- [x] **Code Quality**: DRY (single `is_reasoning_model()` in base class), YAGNI (no thinking-mode support until needed), single responsibility (each provider handles only its own parameter mapping)
- [x] **Refactoring**: Step 1 is pure structural refactor (move method, no behavior change). Steps 2-4 are behavioral additions.
- [x] **Simplicity**: Prefix matching via `startswith()` is the simplest possible detection. Config list via Hydra YAML is the simplest extensibility mechanism.

## Project Structure

### Documentation (this feature)

```text
specs/004-llm-provider-expansion/
├── plan.md              # This file
├── research.md          # Phase 0 output - parameter handling research
├── data-model.md        # Phase 1 output - entity and config schema
├── quickstart.md        # Phase 1 output - usage examples
├── contracts/           # Phase 1 output - provider interface contracts
│   └── provider-interface.md
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── llm/
│   ├── __init__.py          # No changes needed
│   ├── base.py              # MODIFY: add is_reasoning_model(), reasoning_model_prefixes to LLMConfig
│   ├── factory.py           # MODIFY: pass reasoning_model_prefixes from config
│   ├── openai_provider.py   # MODIFY: remove _is_reasoning_model(), use base class method
│   ├── ollama_provider.py   # MODIFY: add reasoning-aware logging (always use standard params)
│   ├── lmstudio_provider.py # MODIFY: add reasoning-aware logging (always use standard params)
│   └── vllm_provider.py     # MODIFY: add reasoning-aware params with try/except fallback

conf/
└── planner/
    └── default.yaml         # MODIFY: add reasoning_model_prefixes list

tests/
└── test_llm_providers.py    # MODIFY: add reasoning model detection + parameter handling tests
```

**Structure Decision**: Single project structure (existing). All changes are modifications to existing files — no new files created except test additions.

## Implementation Steps

### Step 1: Structural Refactor — Centralize Reasoning Detection (Tidy First)

**Commit**: `refactor: move reasoning model detection to base LLMProvider class`

1. Add `reasoning_model_prefixes` field to `LLMConfig` dataclass in `base.py`
2. Add `is_reasoning_model()` method to `LLMProvider` base class
3. Update `OpenAIProvider` to call `self.is_reasoning_model()` instead of `self._is_reasoning_model()`
4. Remove `OpenAIProvider._is_reasoning_model()` private method
5. **Verify**: All existing tests pass with no behavior change

### Step 2: Configuration — Add Reasoning Prefixes to Config (Behavioral)

**Commit**: `feat: add configurable reasoning model prefixes to planner config`

1. Add `reasoning_model_prefixes` list to `conf/planner/default.yaml`
2. Update `LLMProviderFactory.create()` to accept `reasoning_model_prefixes` parameter
3. Update `LLMProviderFactory.from_config()` to read prefixes from `cfg.planner`
4. **Verify**: Factory correctly passes prefixes to LLMConfig

### Step 3: Ollama + LM Studio — Reasoning-Aware Parameter Handling (Behavioral)

**Commit**: `feat: add reasoning-aware parameter handling to Ollama and LM Studio providers`

1. Ollama: Add reasoning model detection logging; always use `max_tokens` + `temperature` (research shows `max_completion_tokens` and `reasoning_effort` are unreliable)
2. LM Studio: Same as Ollama — always use standard params, log when reasoning model detected
3. **Verify**: Both providers work with qwen3.5, glm-5, kimi-k2.5 model names

### Step 4: vLLM — Reasoning-Aware Parameter Handling with Fallback (Behavioral)

**Commit**: `feat: add reasoning-aware parameter handling to vLLM provider with fallback`

1. Add reasoning detection to vLLM provider
2. For reasoning models: try `max_completion_tokens` + `reasoning_effort`, catch errors and fallback to standard params
3. Log fallback when it occurs
4. **Verify**: vLLM provider handles both reasoning and non-reasoning models

### Step 5: Tests (TDD — written alongside each step above)

**Commit**: `test: add comprehensive reasoning model detection and provider parameter tests`

1. Test `is_reasoning_model()` on base class with all prefixes
2. Test `is_reasoning_model()` returns False for non-reasoning models (gpt-4, llama3, mistral)
3. Test custom `reasoning_model_prefixes` override via config
4. Test OpenAI provider uses `max_completion_tokens` for reasoning models
5. Test OpenAI provider uses `max_tokens` for non-reasoning models
6. Test Ollama/LM Studio always use `max_tokens` regardless of model
7. Test factory reads `reasoning_model_prefixes` from config
8. Test backward compatibility — existing configs produce same behavior

## Complexity Tracking

> No violations. All constitution checks pass.

No complexity tracking entries needed.
