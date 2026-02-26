# Implementation Plan: ALFRED Instruction Validation

**Branch**: `005-instruction-validation` | **Date**: 2026-02-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-instruction-validation/spec.md`

## Summary

Create a validation script that classifies ALFRED task instructions into 4 categories (valid, non_existent, goal_mismatch, ambiguous) using a lightweight LLM (gpt-5-mini) to compare annotator-written instructions against scene objects and PDDL ground truth. The LLM receives the instruction text, scene object list, and ground truth targets, then returns a structured JSON classification. The evaluator is extended to optionally skip bad instructions based on the generated report.

## Technical Context

**Language/Version**: Python 3.10 (conda env: llmtaskplanning)
**Primary Dependencies**: Existing `src/llm/` provider infrastructure (OpenAI API), standard library (json, argparse, logging). Reuses `src/alfred/utils.py` and `alfred/gen/constants.py`.
**Storage**: JSON files (input: ALFRED dataset; output: validation report)
**Testing**: pytest with existing mock patterns (mock `chat_completion()` for unit tests)
**Target Platform**: Linux (same machine as evaluation runs)
**Project Type**: Single project — CLI script + library module
**Performance Goals**: Process 820 entries in <15 minutes with gpt-5-mini
**Constraints**: Requires OpenAI API key (already configured for evaluation). Cost <$1.00 per full split validation.
**Scale/Scope**: ~820 entries per split (valid_seen), ~60 object types, ~26 receptacle types

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **TDD Cycle**: Plan includes test-first approach — tests for data loading, prompt construction, response parsing, classification, and report generation written before implementation
- [x] **Tidy First**: Structural changes (config additions) separated from behavioral changes (new module). Prompt template is a separate constant, not inlined in logic
- [x] **Commit Discipline**: Plan supports atomic commits: (1) test fixtures + data loading tests, (2) prompt + parsing, (3) classification orchestrator, (4) CLI, (5) evaluator integration
- [x] **Code Quality**: DRY via reuse of existing LLM provider and data loading. Single responsibility: data loading, prompt building, response parsing, orchestration, and reporting are separate functions
- [x] **Refactoring**: No refactoring of existing code needed; new code only
- [x] **Simplicity**: LLM handles all semantic matching — no synonym dictionaries, no NLP libraries, no noun extraction pipelines. The simplest approach that works.

## Project Structure

### Documentation (this feature)

```text
specs/005-instruction-validation/
├── plan.md              # This file
├── research.md          # Phase 0: Research findings
├── data-model.md        # Phase 1: Entity definitions
├── quickstart.md        # Phase 1: Usage guide
├── contracts/
│   └── validation-report.md  # Phase 1: JSON schema + CLI + prompt contract
└── tasks.md             # Phase 2 output (not created by /speckit.plan)
```

### Source Code (repository root)

```text
src/alfred/
├── instruction_validator.py   # NEW: Validation script (CLI + library)
├── react_evaluator.py         # MODIFIED: Add validation report filtering
└── utils.py                   # EXISTING: Reuse load_task_json

src/llm/
└── factory.py                 # EXISTING: Reuse LLMProviderFactory.create()

conf/
└── config_alfred_react.yaml   # MODIFIED: Add validation_report + skip_categories fields

tests/
├── test_instruction_validator.py  # NEW: Unit tests
└── fixtures/                      # NEW: Test fixture JSON files
    └── validation/
        ├── sample_ann_valid.json
        ├── sample_ann_nonexistent.json
        └── sample_ann_mismatch.json
```

**Structure Decision**: Single project, new module at `src/alfred/instruction_validator.py` following existing convention of one file per evaluator/tool.

## Implementation Approach

### Phase 1: Data Loading + Prompt Construction (US1 foundation)

1. **Data loading**: Extract scene objects and PDDL targets from preprocessed annotations
   - `load_task_data(task, split)` → (instruction_text, scene_objects, pddl_targets)
   - Reuses `load_task_json()` from utils.py
   - Strips "Sliced" suffix from object_target to include base form in prompt

2. **Prompt construction**: Build the classification prompt
   - System message: category definitions + priority rules + sliced object guidance
   - User message: instruction text, scene objects, PDDL targets
   - See `contracts/validation-report.md` for full prompt template

### Phase 2: LLM Classification + Response Parsing (US1 core)

1. **LLM call**: Send prompt via `LLMProviderFactory.create()` → `chat_completion()`
   - Model: gpt-5-mini, reasoning_effort=low, temperature=0.0
   - Returns JSON string `{"category": N, "reason": "..."}`

2. **Response parsing**: Extract category and reason from LLM response
   - Try `json.loads()` first, fall back to regex extraction (reuse pattern from `react_task_planner.py`)
   - Validate category is 0-3; default to 3 (ambiguous) if unparseable
   - Retry on API failure with exponential backoff (max 3 retries)

### Phase 3: Report Generation (US1 + US3)

1. Iterate all (task, repeat_idx) entries in split (with subset sampling support)
2. For each entry: load data → build prompt → classify via LLM → build ValidationEntry
3. Build ValidationReport with summary statistics (by_task_type breakdown)
4. Write JSON output with progress logging

### Phase 4: CLI Interface (US1 completion)

Standalone `argparse`-based CLI matching the contract in `contracts/validation-report.md`.
Arguments: `--split`, `--model`, `--provider`, `--reasoning-effort`, `--output`, `--portion`, `--seed`, `--stratified`.

### Phase 5: Evaluator Integration (US2)

1. Add `validation_report` and `skip_categories` to Hydra config
2. Add report loading + lookup dict in `react_evaluator.py` evaluate() method
3. Add skip logic before `evaluate_task()` call in the task loop

### TDD Order

Each phase follows Red-Green-Refactor:

| Step | Test (Red) | Implementation (Green) |
|---|---|---|
| 1 | test load_task_data extracts scene objects + PDDL targets | `load_task_data()` function |
| 2 | test scene object extraction strips instance suffixes | Object extraction logic |
| 3 | test build_classification_prompt produces correct structure | `build_classification_prompt()` function |
| 4 | test sliced object targets include base form in prompt | Sliced handling in prompt builder |
| 5 | test parse_classification_response extracts category + reason | `parse_classification_response()` function |
| 6 | test parse handles malformed LLM output gracefully | Fallback parsing + default category |
| 7 | test classify_instruction end-to-end with mocked LLM | `classify_instruction()` orchestrator |
| 8 | test validate_split produces correct report structure | `validate_split()` function |
| 9 | test summary statistics computation | `build_summary()` function |
| 10 | test CLI argument parsing | `main()` with argparse |
| 11 | test evaluator skips tasks based on report | Modified evaluator loop |
