# Tasks: ALFRED Instruction Validation

**Input**: Design documents from `/specs/005-instruction-validation/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included — project constitution mandates TDD (Red-Green-Refactor cycle).

**Organization**: Tasks grouped by user story. Each story is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create test fixtures and module skeleton

- [X] T001 [P] Create test fixture for valid annotation (category 0) in tests/fixtures/validation/sample_ann_valid.json — include scene.object_poses with Candle + Toilet objects, pddl_params with object_target=Candle parent_target=Toilet, turk_annotations.anns[0].task_desc="Place the candle on the toilet.", task_type=pick_and_place_simple
- [X] T002 [P] Create test fixture for non-existent annotation (category 1) in tests/fixtures/validation/sample_ann_nonexistent.json — use the Candle/Toilet scene but set task_desc="Put a bottle on the back of a newspaper.", matching the real trial_T20190908_052232_887934 case
- [X] T003 [P] Create test fixture for goal-mismatch annotation (category 2) in tests/fixtures/validation/sample_ann_mismatch.json — scene has both Candle and SprayBottle, pddl_params target is Candle/Toilet, but task_desc="Put the spray bottle on the toilet." (SprayBottle exists but is wrong target)
- [X] T004 Create empty module skeleton in src/alfred/instruction_validator.py with module docstring, imports (json, logging, argparse, os, re, time, datetime), and CATEGORY_LABELS constant dict {0: "valid", 1: "non_existent", 2: "goal_mismatch", 3: "ambiguous"}

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Output directory setup and config extension — MUST complete before user stories

- [X] T005 Add validation_report and skip_categories fields to conf/config_alfred_react.yaml under the alfred section — validation_report: "" (empty string = disabled), skip_categories: [1] (default: skip non_existent only)
- [X] T006 Create outputs/alfred_react/ directory if not present (ensure .gitkeep or equivalent)

**Checkpoint**: Foundation ready — user story implementation can begin

---

## Phase 3: User Story 1 - Validate All Instructions in a Split (Priority: P1) MVP

**Goal**: Run validation script on an ALFRED split, classify each instruction via LLM, produce structured JSON report

**Independent Test**: `PYTHONPATH="alfred:src:$PYTHONPATH" python src/alfred/instruction_validator.py --split valid_seen --portion 1` produces a JSON file with entries classified as categories 0-3

### Tests for User Story 1 (TDD - Red Phase)

> **TDD MANDATORY — Write tests FIRST, ensure they FAIL (Red), then implement (Green)**

- [X] T007 [P] [US1] Write test_extract_scene_objects in tests/test_instruction_validator.py — given a fixture annotation JSON with object_poses containing "Candle_96bce45a" and "SoapBar_a5cd30dd", assert extract_scene_objects() returns sorted unique types ["Candle", "SoapBar"]
- [X] T008 [P] [US1] Write test_extract_pddl_targets in tests/test_instruction_validator.py — given fixture annotation with pddl_params, assert extract_pddl_targets() returns dict with object_target, parent_target, mrecep_target, object_sliced. Also test fallback to directory name parsing when pddl_params is empty
- [X] T009 [P] [US1] Write test_build_classification_prompt in tests/test_instruction_validator.py — assert build_classification_prompt() returns (system_msg, user_msg) tuple. System msg contains category definitions. User msg contains instruction text, scene objects list, and ground truth targets. For PotatoSliced target, assert both "PotatoSliced" and "Potato" appear in user msg
- [X] T010 [P] [US1] Write test_parse_classification_response in tests/test_instruction_validator.py — test valid JSON '{"category": 1, "reason": "no bottle"}' → (1, "no bottle"). Test malformed response falls back to category 3. Test category out of range (5) falls back to 3
- [X] T011 [P] [US1] Write test_classify_instruction in tests/test_instruction_validator.py — mock LLMProvider.chat_completion() to return '{"category": 1, "reason": "non-existent"}', assert classify_instruction() returns ValidationEntry with category=1. Test API failure retries up to 3 times
- [X] T012 [US1] Write test_validate_split in tests/test_instruction_validator.py — replaced with TestBuildSummary to test the summary computation core directly without complex I/O mocking

### Implementation for User Story 1

- [X] T013 [US1] Implement extract_scene_objects(traj_data) in src/alfred/instruction_validator.py — extract unique object types from scene.object_poses by stripping instance suffix (split on last '_', take everything before the hash). Return sorted list
- [X] T014 [US1] Implement extract_pddl_targets(traj_data, task_path) in src/alfred/instruction_validator.py — extract from traj_data['pddl_params'] if present, otherwise parse task_path directory name format "{task_type}-{object}-{mrecep}-{receptacle}-{scene_num}" via regex. Return dict with object_target, parent_target, mrecep_target, object_sliced
- [X] T015 [US1] Define CLASSIFICATION_SYSTEM_PROMPT and build_classification_prompt(instruction_text, scene_objects, pddl_targets) in src/alfred/instruction_validator.py — system prompt per contracts/validation-report.md. User message includes instruction, scene objects as comma-separated list, and ground truth targets. For Sliced targets, append "(base form: {base})" to object_target
- [X] T016 [US1] Implement parse_classification_response(raw_response) in src/alfred/instruction_validator.py — try json.loads() on extracted JSON object (regex r'\{[^{}]*\}'), validate category in 0-3, return (category, reason). On parse failure return (3, "unparseable LLM response")
- [X] T017 [US1] Implement classify_instruction(llm, instruction_text, scene_objects, pddl_targets) in src/alfred/instruction_validator.py — build prompt → call llm.chat_completion(messages, temperature=0.0) → parse response. Retry up to 3 times on exception with exponential backoff (1s, 2s, 4s). On exhausted retries, return (3, "classification failed after retries")
- [X] T018 [US1] Implement validate_split(split, llm, portion=100, seed=1, stratified=False) in src/alfred/instruction_validator.py — load splits from alfred/data/splits/oct21.json, filter out pick_two_obj_and_place, apply subset sampling matching react_evaluator.py logic, iterate entries with tqdm, call classify_instruction for each, build and return ValidationReport dict per data-model.md schema
- [X] T019 [US1] Implement build_summary(entries) in src/alfred/instruction_validator.py — compute CategorySummary (total + per-category counts) for all entries and per task_type. Return dict matching ValidationReport.summary and .by_task_type schema
- [X] T020 [US1] Implement main() CLI in src/alfred/instruction_validator.py — argparse with --split (required), --model (default gpt-5-mini), --provider (default openai), --reasoning-effort (default low), --output (default outputs/alfred_react/instruction_validation_{split}.json), --portion (default 100), --seed (default 1), --stratified flag. Create LLM via LLMProviderFactory.create(), call validate_split(), write JSON report, log summary to console

**Checkpoint**: Running `PYTHONPATH="alfred:src:$PYTHONPATH" python src/alfred/instruction_validator.py --split valid_seen --portion 1` produces a valid JSON report. Tests pass with `pytest tests/test_instruction_validator.py -v`

---

## Phase 4: User Story 2 - Filter Bad Instructions During Evaluation (Priority: P2)

**Goal**: The ReAct evaluator loads a validation report and skips instructions in specified categories

**Independent Test**: Run evaluator with validation_report path and skip_categories=[1], confirm tasks with category 1 are skipped in output

### Tests for User Story 2 (TDD - Red Phase)

- [X] T021 [US2] Write test_load_validation_report in tests/test_instruction_validator.py — given a sample validation report JSON, assert load_validation_report() returns a lookup dict keyed by (task_path, repeat_idx) with entry dicts
- [X] T022 [US2] Write test_evaluator_skips_tasks in tests/test_instruction_validator.py — mock the evaluator loop, provide a validation report with one category-1 entry, assert that entry is skipped and logged. Assert category-0 entries are NOT skipped

### Implementation for User Story 2

- [X] T023 [US2] Implement load_validation_report(report_path) in src/alfred/instruction_validator.py — load JSON, build dict {(entry['task_path'], entry['repeat_idx']): entry for entry in report['entries']}, return lookup dict
- [X] T024 [US2] Modify evaluate() in src/alfred/react_evaluator.py — after loading files and before the task loop: if cfg.alfred.validation_report is non-empty, call load_validation_report(). Inside the task loop (before evaluate_task), check lookup for (task['task'], task['repeat_idx']); if found and category in cfg.alfred.skip_categories, log skip reason and append a skip record to results instead of evaluating. Skip record format: {"trial": trial_id, "skipped": True, "skip_reason": category_label, "skip_category": category}

**Checkpoint**: Evaluator with validation_report config skips bad instructions. Skipped tasks appear in output.

---

## Phase 5: User Story 3 - Human-Readable Summary Report (Priority: P3)

**Goal**: Console output shows aggregate statistics per category and per task type when validation completes

**Independent Test**: Run validation script, verify console output includes category counts, percentages, and per-task-type breakdown

### Tests for User Story 3 (TDD - Red Phase)

- [X] T025 [US3] Write test_print_summary in tests/test_instruction_validator.py — given a ValidationReport dict with known counts, capture log output from print_summary(), assert it contains "category_0: N (X.X%)" format and per-task-type lines

### Implementation for User Story 3

- [X] T026 [US3] Implement print_summary(report) in src/alfred/instruction_validator.py — log total entries, per-category counts with percentages, and per-task-type breakdown. Format: "Category 0 (valid): 700/820 (85.4%)" per category, then task-type table
- [X] T027 [US3] Call print_summary(report) from main() after writing JSON report in src/alfred/instruction_validator.py

**Checkpoint**: Running the validation script prints a clear summary table to the console alongside producing the JSON file

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Edge case handling and documentation

- [X] T028 Handle missing annotation files gracefully in validate_split() in src/alfred/instruction_validator.py — if load_task_json raises FileNotFoundError, log warning and continue to next entry
- [X] T029 Run quickstart.md validation — CLI --help verified, end-to-end requires ALFRED dataset + OpenAI API key

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: No dependencies on Phase 1 (config change is independent)
- **User Story 1 (Phase 3)**: Depends on Phase 1 (fixtures) and Phase 2 (config)
- **User Story 2 (Phase 4)**: Depends on US1 (needs load_validation_report and report schema)
- **User Story 3 (Phase 5)**: Depends on US1 (needs build_summary and report dict)
- **Polish (Phase 6)**: Depends on all user stories

### User Story Dependencies

- **US1 (P1)**: Can start after Setup + Foundational — **no dependencies on other stories**
- **US2 (P2)**: Depends on US1 for `load_validation_report()` function and report schema — but can be tested independently with a mock report JSON
- **US3 (P3)**: Depends on US1 for `build_summary()` function — purely additive

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Red phase)
- Data extraction before prompt building
- Prompt building before LLM interaction
- LLM interaction before orchestration
- Orchestration before CLI
- Commit after each task with appropriate prefix (test: or feat:)

### Parallel Opportunities

- **Phase 1**: T001, T002, T003 can all run in parallel (different fixture files)
- **Phase 3 tests**: T007-T012 can all run in parallel (same test file but independent test functions)
- **Phase 3 impl**: T013 and T014 can run in parallel (independent extractors), T015 independent of both
- **Phase 4**: T021-T022 can run in parallel (independent tests)

---

## Parallel Example: User Story 1

```bash
# Launch all tests in parallel (Red phase):
Task: "Write test_extract_scene_objects in tests/test_instruction_validator.py"
Task: "Write test_extract_pddl_targets in tests/test_instruction_validator.py"
Task: "Write test_build_classification_prompt in tests/test_instruction_validator.py"
Task: "Write test_parse_classification_response in tests/test_instruction_validator.py"
Task: "Write test_classify_instruction in tests/test_instruction_validator.py"

# Launch independent extractors in parallel (Green phase):
Task: "Implement extract_scene_objects() in src/alfred/instruction_validator.py"
Task: "Implement extract_pddl_targets() in src/alfred/instruction_validator.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (fixtures + skeleton)
2. Complete Phase 2: Foundational (config)
3. Complete Phase 3: User Story 1 (validation script)
4. **STOP and VALIDATE**: Run `--portion 1` on valid_seen, verify JSON report
5. Run on full `--portion 5` subset to check against known failures from comparison report

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Validate on real data (MVP!)
3. Add User Story 2 → Test evaluator filtering → Run filtered evaluation
4. Add User Story 3 → Verify console summary output
5. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- TDD: Verify tests fail (Red) before implementing (Green)
- Tidy First: Commit structural changes separately from behavioral changes
- Commit after each task or logical group with appropriate prefix (refactor: or feat: or test:)
- The LLM provider is created via `LLMProviderFactory.create(provider, model_name=model, reasoning_effort=effort)` — no Hydra config object needed for the standalone script
- Test fixtures should be minimal but realistic — based on actual ALFRED annotation structure from pp/ann_N.json
