# Tasks: LLM Provider Expansion for Reasoning Models

**Input**: Design documents from `/specs/004-llm-provider-expansion/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included per constitution TDD mandate. Tests are written first (Red), then implementation (Green).

**Organization**: Tasks are grouped by user story. US4 (Unified Detection) is placed in the Foundational phase since it is a prerequisite for all other stories.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No new project scaffolding needed — all changes modify existing files.

- [X] T001 Verify existing tests pass before any changes: run `pytest tests/test_llm_providers.py -v`

---

## Phase 2: Foundational — Unified Reasoning Model Detection (US4, Priority: P2)

**Purpose**: Centralize reasoning model detection into the base class and make it configurable. This is the prerequisite for ALL user stories — no provider changes can begin until detection is unified.

**Goal**: Any provider can detect whether its model is a reasoning model via `self.is_reasoning_model()`, using a configurable prefix list.

**Independent Test**: Create a provider with `model_name: qwen3.5` and verify `is_reasoning_model()` returns True.

### Tests for US4 (TDD - Red Phase)

- [X] T002 [P] [US4] Write test `test_is_reasoning_model_gpt5_variants` — verify `is_reasoning_model()` returns True for "gpt-5.2", "gpt-5-mini", "gpt-5-nano" in `tests/test_llm_providers.py`
- [X] T003 [P] [US4] Write test `test_is_reasoning_model_open_source` — verify `is_reasoning_model()` returns True for "qwen3.5", "glm-5", "kimi-k2.5" in `tests/test_llm_providers.py`
- [X] T004 [P] [US4] Write test `test_is_reasoning_model_false_for_standard` — verify `is_reasoning_model()` returns False for "gpt-4", "gpt-3.5-turbo", "llama3", "mistral" in `tests/test_llm_providers.py`
- [X] T005 [P] [US4] Write test `test_custom_reasoning_prefixes_override` — verify custom `reasoning_model_prefixes` in LLMConfig overrides defaults in `tests/test_llm_providers.py`
- [X] T006 [P] [US4] Write test `test_factory_passes_reasoning_prefixes` — verify `LLMProviderFactory.from_config()` reads `reasoning_model_prefixes` from config and passes to LLMConfig in `tests/test_llm_providers.py`

### Implementation for US4 (refactor: structural — preserve original behavior)

- [X] T007 [US4] Add `reasoning_model_prefixes` field to `LLMConfig` dataclass with default tuple `("gpt-5", "o1", "o3")` (original OpenAI prefixes only — no behavior change) in `src/llm/base.py`
- [X] T008 [US4] Add `is_reasoning_model()` method to `LLMProvider` base class that checks `any(self.model_name.startswith(p) for p in self.config.reasoning_model_prefixes)` in `src/llm/base.py`
- [X] T009 [US4] Remove `_is_reasoning_model()` from `OpenAIProvider` and update `chat_completion()` to call `self.is_reasoning_model()` instead in `src/llm/openai_provider.py`

### Implementation for US4 (feat: expand prefixes + configuration)

- [X] T010 [US4] Expand `reasoning_model_prefixes` default in `LLMConfig` to `("gpt-5", "o1", "o3", "o4", "qwen3", "glm-", "kimi-k")` and add matching list to `conf/planner/default.yaml` in `src/llm/base.py` and `conf/planner/default.yaml`
- [X] T011 [US4] Update `LLMProviderFactory.create()` to accept optional `reasoning_model_prefixes` parameter and pass to LLMConfig in `src/llm/factory.py`
- [X] T012 [US4] Update `LLMProviderFactory.from_config()` to read `reasoning_model_prefixes` from `cfg.planner` and convert to tuple in `src/llm/factory.py`
- [X] T013 [US4] Run tests T002-T006 and verify they pass (Green phase)

**Checkpoint**: `is_reasoning_model()` works on base class, configurable via YAML. OpenAI provider uses base class method. All existing tests still pass.

---

## Phase 3: User Story 1 — OpenAI Reasoning Models (Priority: P1) MVP

**Goal**: gpt-5.2, gpt-5-mini, gpt-5-nano are fully supported with correct `max_completion_tokens` and `reasoning_effort` parameter handling.

**Independent Test**: Set `model_name: gpt-5-mini` and `reasoning_effort: low` in config, mock the OpenAI client, verify the API call includes `max_completion_tokens` and `reasoning_effort: low`.

### Tests for US1 (TDD - Red Phase)

- [X] T014 [P] [US1] Write test `test_openai_reasoning_model_uses_max_completion_tokens` — mock OpenAI client, verify `max_completion_tokens` (not `max_tokens`) is in API kwargs for "gpt-5-mini" in `tests/test_llm_providers.py`
- [X] T015 [P] [US1] Write test `test_openai_reasoning_model_passes_reasoning_effort` — mock OpenAI client, verify `reasoning_effort: "low"` is in API kwargs for "gpt-5.2" with effort configured in `tests/test_llm_providers.py`
- [X] T016 [P] [US1] Write test `test_openai_non_reasoning_model_uses_max_tokens` — mock OpenAI client, verify `max_tokens` and `temperature` are used for "gpt-4" (backward compat) in `tests/test_llm_providers.py`

### Implementation for US1

- [X] T017 [US1] Verify `OpenAIProvider.chat_completion()` correctly uses `self.is_reasoning_model()` (from T009 refactor) — no additional code changes expected, just verify the existing `max_completion_tokens` logic works for gpt-5-mini and gpt-5-nano in `src/llm/openai_provider.py`
- [X] T018 [US1] Run tests T014-T016 and verify they pass (Green phase)

**Checkpoint**: OpenAI reasoning models (gpt-5.2, gpt-5-mini, gpt-5-nano) work correctly with `max_completion_tokens` + `reasoning_effort`. Backward compatible with gpt-4.

---

## Phase 4: User Story 2 — Ollama Reasoning Models (Priority: P2)

**Goal**: qwen3.5, glm-5, kimi-k2.5 work correctly through Ollama with standard parameters (always `max_tokens`, never `reasoning_effort` — per research R1).

**Independent Test**: Set `provider: ollama` and `model_name: qwen3.5`, mock Ollama client, verify API call uses `max_tokens` (not `max_completion_tokens`) and does NOT include `reasoning_effort`.

### Tests for US2 (TDD - Red Phase)

- [X] T019 [P] [US2] Write test `test_ollama_reasoning_model_uses_standard_params` — mock client, verify Ollama always uses `max_tokens` + `temperature` even for recognized reasoning models ("qwen3.5") in `tests/test_llm_providers.py`
- [X] T020 [P] [US2] Write test `test_ollama_does_not_pass_reasoning_effort` — mock client, verify `reasoning_effort` is NOT in API kwargs even when configured in `tests/test_llm_providers.py`
- [X] T021 [P] [US2] Write test `test_ollama_reasoning_model_logs_detection` — verify logging output includes reasoning model detection message for "glm-5" in `tests/test_llm_providers.py`

### Implementation for US2

- [X] T022 [US2] Update `OllamaProvider.chat_completion()` to log when `self.is_reasoning_model()` is True, but always use standard `max_tokens` + `temperature` params in `src/llm/ollama_provider.py`
- [X] T023 [US2] Run tests T019-T021 and verify they pass (Green phase)

**Checkpoint**: Ollama works with qwen3.5, glm-5, kimi-k2.5 using safe standard parameters. Reasoning model is detected and logged but params are not sent to avoid Ollama errors.

---

## Phase 5: User Story 3 — LM Studio Reasoning Models (Priority: P3)

**Goal**: qwen3.5, glm-5, kimi-k2.5 work correctly through LM Studio with standard parameters (per research R2 — unknown params silently ignored).

**Independent Test**: Set `provider: lmstudio` and `model_name: kimi-k2.5`, mock LM Studio client, verify API call uses `max_tokens`.

### Tests for US3 (TDD - Red Phase)

- [X] T024 [P] [US3] Write test `test_lmstudio_reasoning_model_uses_standard_params` — mock client, verify LM Studio always uses `max_tokens` + `temperature` for reasoning models ("kimi-k2.5") in `tests/test_llm_providers.py`
- [X] T025 [P] [US3] Write test `test_lmstudio_reasoning_model_logs_detection` — verify logging output for reasoning model detection in `tests/test_llm_providers.py`

### Implementation for US3

- [X] T026 [US3] Update `LMStudioProvider.chat_completion()` to log when `self.is_reasoning_model()` is True, but always use standard `max_tokens` + `temperature` params in `src/llm/lmstudio_provider.py`
- [X] T027 [US3] Run tests T024-T025 and verify they pass (Green phase)

**Checkpoint**: LM Studio works with all reasoning models using standard parameters. Consistent behavior with Ollama.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: vLLM provider update (not a separate user story but affects reasoning model support), backward compatibility verification, and documentation.

- [X] T028 [P] Write test `test_vllm_reasoning_model_with_fallback` — mock client to raise error on `max_completion_tokens`, verify fallback to `max_tokens` in `tests/test_llm_providers.py`
- [X] T029 [P] Write test `test_vllm_non_reasoning_uses_standard_params` — verify standard param handling unchanged for non-reasoning models in `tests/test_llm_providers.py`
- [X] T030 Update `VLLMProvider.chat_completion()` to try `max_completion_tokens` + `reasoning_effort` for reasoning models, catch errors and fallback to standard params with warning log in `src/llm/vllm_provider.py`
- [X] T031 Run full test suite: `pytest tests/test_llm_providers.py -v` — all tests pass
- [X] T032 [P] Update `src/llm/__init__.py` docstring to list new supported models (qwen3.5, glm-5, kimi-k2.5)
- [X] T033 [P] Update `conf/planner/default.yaml` comments to document reasoning_model_prefixes usage
- [X] T034 Run backward compatibility check: verify existing test cases for gpt-4, llama2, test-model still pass unchanged

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — verify baseline
- **Phase 2 (Foundational / US4)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1 / OpenAI)**: Depends on Phase 2 completion
- **Phase 4 (US2 / Ollama)**: Depends on Phase 2 completion — can run in parallel with Phase 3
- **Phase 5 (US3 / LM Studio)**: Depends on Phase 2 completion — can run in parallel with Phase 3 and 4
- **Phase 6 (Polish)**: Depends on all user story phases being complete

### User Story Dependencies

- **US4 (Unified Detection)**: Foundational — no dependencies on other stories, blocks all others
- **US1 (OpenAI)**: Depends on US4 — independent of US2, US3
- **US2 (Ollama)**: Depends on US4 — independent of US1, US3
- **US3 (LM Studio)**: Depends on US4 — independent of US1, US2

### Within Each Phase

- Tests MUST be written and FAIL before implementation (TDD Red-Green)
- `[P]` tasks within the same phase can run in parallel
- Non-`[P]` tasks run sequentially within their phase

### Parallel Opportunities

Within Phase 2 (Foundational):
- T002, T003, T004, T005, T006 — all test writes can run in parallel

After Phase 2 completes, US1/US2/US3 can run in parallel:
- Phase 3 (US1), Phase 4 (US2), Phase 5 (US3) — independent providers, different files

Within each User Story phase:
- Test writes (Red phase) can run in parallel
- Implementation is sequential (depends on base class changes)

---

## Parallel Example: After Foundational Phase

```text
# All three user story phases can start simultaneously:
Phase 3 (US1): T014, T015, T016 → T017 → T018
Phase 4 (US2): T019, T020, T021 → T022 → T023
Phase 5 (US3): T024, T025 → T026 → T027
```

---

## Implementation Strategy

### MVP First (User Story 4 + User Story 1 Only)

1. Complete Phase 1: Verify baseline (T001)
2. Complete Phase 2: Foundational / US4 (T002-T013) — centralized detection + config
3. Complete Phase 3: US1 / OpenAI (T014-T018) — gpt-5-mini, gpt-5-nano support
4. **STOP and VALIDATE**: Test with `model_name: gpt-5-mini` config — verify `max_completion_tokens` in API call
5. This alone delivers value: all OpenAI reasoning models work correctly

### Incremental Delivery

1. Phase 2 (US4) → Centralized detection works
2. Phase 3 (US1) → OpenAI reasoning models tested and working (MVP)
3. Phase 4 (US2) → Ollama with qwen3.5/glm-5/kimi-k2.5 tested and working
4. Phase 5 (US3) → LM Studio with reasoning models tested and working
5. Phase 6 → vLLM fallback, docs, backward compat verified

Each phase adds value independently without breaking previous phases.

---

## Commit Strategy (Tidy First)

| Phase | Commit Prefix | Message |
|-------|--------------|---------|
| Phase 2 (T007-T009) | `refactor:` | move reasoning model detection to base LLMProvider class (original 3 prefixes only) |
| Phase 2 (T010-T012) | `feat:` | expand reasoning prefixes to cover qwen3/glm/kimi-k and add configurable list to planner config |
| Phase 2 (T002-T006, T013) | `test:` | add reasoning model detection tests |
| Phase 3 (T014-T018) | `test:` | add OpenAI reasoning parameter handling tests |
| Phase 4 (T019-T023) | `feat:` | add reasoning-aware parameter handling to Ollama provider |
| Phase 5 (T024-T027) | `feat:` | add reasoning-aware parameter handling to LM Studio provider |
| Phase 6 (T028-T034) | `feat:` | add reasoning-aware fallback to vLLM provider |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- TDD: Verify tests fail (Red) before implementing (Green)
- Tidy First: Structural refactor (T007-T009) committed separately from behavioral changes
- Ollama and LM Studio always use standard params (research R1, R2) — reasoning detection is for logging only
- vLLM gets try/except fallback (research R3) — most robust approach
- All tests use mocked OpenAI client — no live server required
