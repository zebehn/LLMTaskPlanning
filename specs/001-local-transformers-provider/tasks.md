---
description: "Task list for Local Transformers Provider for ReAct Experiments"
---

# Tasks: Local Transformers Provider for ReAct Experiments

**Input**: Design documents from `/specs/001-local-transformers-provider/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Note**: The TDD phase (plan.md test plan) already completed all foundational provider
tasks. Those are marked `[x]` below. Remaining work is the Hydra config (US1),
hardware-config smoke test (US2), schema parity test (US3), and documentation.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Dependencies)

**Purpose**: Ensure required packages are declared

- [x] T001 Add `transformers>=4.51.0`, `torch>=2.0.0`, `accelerate>=0.26.0` to `requirements.txt`

---

## Phase 2: Foundational (Core Provider — completed via TDD)

**Purpose**: LLMProvider extension enabling all user stories
**Status**: ✅ Complete — implemented and tested in TDD phase

**⚠️ CRITICAL**: All user story work depends on this foundation being present.

- [x] T002 Extend `LLMConfig` with `device_map` and `torch_dtype` fields and update `is_reasoning_model()` for HuggingFace namespace format in `src/llm/base.py`
- [x] T003 Create `TransformersProvider` with lazy imports, dtype validation, `chat_completion()`, and `select_action()` in `src/llm/transformers_provider.py`
- [x] T004 Register `TransformersProvider` in `LLMProviderFactory.PROVIDERS` and update `create()` / `from_config()` to pass `device_map` and `torch_dtype` in `src/llm/factory.py`
- [x] T005 [P] Write 27 unit tests covering LLMConfig fields, factory registration, provider initialization, `chat_completion()`, `select_action()`, `is_reasoning_model()`, and regression guards in `tests/test_transformers_provider.py`

**Checkpoint**: Foundation complete — `provider="transformers"` can be selected via config

---

## Phase 3: User Story 1 - Run ReAct Experiment with Local Model (Priority: P1) 🎯 MVP

**Goal**: Researcher can launch a full ReAct evaluation using local Qwen3-8B with a
single config change, producing results identical in structure to API-based runs.

**Independent Test**: `PYTHONPATH="alfred:src:$PYTHONPATH" python src/evaluate.py --config-name=config_alfred_react_local alfred.eval_portion_in_percent=1`
— completes without error and produces `react_summary.json` in the output directory.

### Implementation for User Story 1

- [x] T006 [US1] Create `conf/config_alfred_react_local.yaml` with `provider="transformers"`, `model_name="Qwen/Qwen3-8B"`, `device_map="auto"`, `torch_dtype="auto"` (see data-model.md for full schema)
- [x] T007 [US1] Verify config loads correctly: run `python -c "from omegaconf import OmegaConf; from hydra import compose, initialize; ..."` or write a config-load unit test in `tests/test_transformers_provider.py` confirming `config_alfred_react_local` resolves to `provider="transformers"`

**Checkpoint**: Running `--config-name=config_alfred_react_local` selects TransformersProvider
and initiates evaluation (model download or load from cache)

---

## Phase 4: User Story 2 - Configure Local Model for Hardware (Priority: P2)

**Goal**: Researcher can override device and precision via CLI flags without code changes.

**Independent Test**: `python src/evaluate.py --config-name=config_alfred_react_local planner.device_map=cpu planner.torch_dtype=float32`
— launches without error on a CPU-only configuration.

### Implementation for User Story 2

- [x] T008 [US2] Add a unit test `test_provider_init_respects_device_map_cpu` in `tests/test_transformers_provider.py` verifying that `LLMConfig(device_map="cpu")` is passed through to `AutoModelForCausalLM.from_pretrained(device_map="cpu")`
- [x] T009 [US2] Add a unit test `test_provider_init_respects_torch_dtype_float32` in `tests/test_transformers_provider.py` verifying `torch_dtype="float32"` is passed through to `from_pretrained()`
- [x] T010 [US2] Update `specs/001-local-transformers-provider/quickstart.md` Troubleshooting section with confirmed OOM guidance and CPU fallback CLI example (verify examples match actual CLI flags)

**Checkpoint**: All device/precision combinations configurable via CLI; unit-tested

---

## Phase 5: User Story 3 - Compare Local Model Results with API-Based Providers (Priority: P3)

**Goal**: Evaluation output from TransformersProvider shares identical JSON schema with
API-based provider runs, enabling direct comparison without manual data wrangling.

**Independent Test**: Inspect `react_summary.json` and a per-task `result.json` from
both a local-model run and an API-model run — field names and types must match exactly.

### Implementation for User Story 3

- [x] T011 [US3] Write `test_transformers_provider_output_schema_matches_api_provider` in `tests/test_transformers_provider.py`: mock a full ReAct evaluation step using both `OpenAIProvider` (mocked) and `TransformersProvider` (mocked); assert both return the same type (`str`) from `chat_completion()` and that the `ReActTaskPlanner` produces identically-structured result dicts for both
- [x] T012 [US3] Review `src/alfred/react_evaluator.py` output construction to confirm no provider-specific branches exist that would produce different result schemas for `TransformersProvider` vs API providers — document finding in `specs/001-local-transformers-provider/research.md`

**Checkpoint**: Schema parity confirmed by test and code review

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and final validation

- [x] T013 [P] Update `README.md` to document the `transformers` provider: add a "Local Model Evaluation" section with prerequisites, run command, and pointer to `quickstart.md`
- [x] T014 Run full test suite and confirm no regressions: `PYTHONPATH="alfred:src:$PYTHONPATH" python -m pytest tests/ --ignore=tests/test_ai2thor_compatibility.py -v`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: ✅ Already complete — unblocks all user stories
- **US1 (Phase 3)**: Depends on Foundational — can start now
- **US2 (Phase 4)**: Depends on Foundational — can start in parallel with US1
- **US3 (Phase 5)**: Depends on US1 completing (needs evaluation output to verify)
- **Polish (Phase 6)**: Depends on US1, US2, US3 completion

### User Story Dependencies

- **US1 (P1)**: Requires only T001 (requirements) + T006-T007 — **start immediately**
- **US2 (P2)**: Requires T001 + T008-T010 — can run in parallel with US1 (different files)
- **US3 (P3)**: Requires US1 complete to have real evaluation output for schema inspection

### Within Each User Story

- Config file (T006) before config-load test (T007) for US1
- Unit tests (T008, T009) can run in parallel within US2
- Code review (T012) can run in parallel with schema test (T011) for US3

### Parallel Opportunities

- T008 and T009 (US2 unit tests) can run in parallel — different test functions, same file
- T013 (README) can run in parallel with any phase — documentation only
- T011 and T012 (US3) can run in parallel

---

## Parallel Example: User Story 1

```bash
# US1 is a single sequential task:
Task: "Create conf/config_alfred_react_local.yaml"          # T006
Task: "Verify config loads correctly"                        # T007 (depends on T006)
```

## Parallel Example: User Story 2

```bash
# T008 and T009 can run in parallel:
Task: "test_provider_init_respects_device_map_cpu"          # T008
Task: "test_provider_init_respects_torch_dtype_float32"     # T009
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: T001 (add requirements)
2. Phase 2 already complete ✅
3. Complete Phase 3: T006, T007 (Hydra config + config load test)
4. **STOP and VALIDATE**: Run evaluation with `--config-name=config_alfred_react_local`
5. Confirm `react_summary.json` is produced with expected structure

### Incremental Delivery

1. T001 → requirements declared
2. T006-T007 → Local evaluation launchable (MVP!)
3. T008-T010 → Hardware configuration verified and tested
4. T011-T012 → Schema parity confirmed
5. T013-T014 → Documented and final suite passing

---

## Notes

- [P] tasks = different files, no shared state dependencies
- [US*] label maps task to its user story for traceability
- T002-T005 are `[x]` — completed via the TDD phase in plan.md
- All unit tests use `mock_transformers` fixture — no actual model download required
- Stop at Phase 3 checkpoint to validate MVP before continuing to US2/US3
- Commit discipline: structural changes (`refactor:`) separate from behavioral (`feat:`/`test:`)
