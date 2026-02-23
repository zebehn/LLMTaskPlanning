# Tasks: ReAct-Based Planner with Evaluation

**Input**: Design documents from `/specs/003-react-planner-eval/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included per constitution TDD mandate (Red-Green-Refactor cycle).

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create configuration and prompt template files needed by all user stories

- [x] T001 Create Hydra config file for ReAct evaluation in conf/config_alfred_react.yaml with name=alfred_react, planner settings (model_name, max_steps=25, max_tokens=1024), prompt paths (react_system_prompt, react_few_shot_examples), and alfred settings (x_display='0', eval_portion_in_percent=5, eval_set='valid_seen')
- [x] T002 [P] Create ReAct system prompt template in src/prompts/templates/react_system.txt describing the robot role, available actions (find, pick up, put down, open, close, turn on, turn off, slice, done), and the Think/Act/Obs output format with parsing instructions
- [x] T003 [P] Create ReAct few-shot examples in src/prompts/templates/react_few_shot_examples.txt with 1-2 complete Thought-Action-Observation trajectories per ALFRED task type (Pick & Place, Examine in Light, Clean & Place, Heat & Place, Cool & Place, Pick Two & Place) using the project's action vocabulary (find a X, pick up the X, etc.), adapted from the paper's Appendix C.4

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core components that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

### Tests (TDD Red Phase)

- [x] T004 [P] Write unit tests for parse_react_output() in tests/test_react_planner.py: test parsing "Think: reasoning\nAct: action" format, test fallback when only action present (no Think:), test ValueError when only thought present (no Act:), test handling of multiline thoughts, test handling of "done" action
- [x] T005 [P] Write unit tests for construct_observation() in tests/test_react_planner.py: test successful find observation, test successful pick up observation, test successful put down observation, test action failure observation with error message, test observation includes visible objects when available

### Implementation

- [x] T006 Implement parse_react_output() method on ReActTaskPlanner in src/alfred/react_task_planner.py: parse LLM output into (thought, action) tuple using "Think:" and "Act:" delimiters with fallback behavior per contract spec
- [x] T007 Create ReActTaskPlanner class skeleton in src/alfred/react_task_planner.py extending TaskPlanner: implement __init__(cfg), init_prompt(cfg) to load react_system.txt and react_few_shot_examples.txt, init_skill_set() returning the standard ALFRED action vocabulary for validation
- [x] T008 Add construct_observation() helper method to src/alfred/react_evaluator.py (or as a standalone function): build natural language observation from llm_skill_interact() return dict + optional visible objects from environment metadata. Map action types to observation templates per plan.md D4

**Checkpoint**: Foundation ready -- ReAct planner can parse output and observations can be constructed

---

## Phase 3: User Story 1 - Run ReAct Planner on Household Tasks (Priority: P1) MVP

**Goal**: A working ReAct planner that interleaves Thought-Action-Observation steps, executes actions in AI2-THOR, and completes household tasks with visible reasoning

**Independent Test**: Launch single task evaluation with `python src/evaluate.py --config-name=config_alfred_react alfred.eval_portion_in_percent=1` and verify the planner produces interleaved thought/action/observation trace

### Tests (TDD Red Phase)

- [x] T009 [P] [US1] Write unit tests for react_step() in tests/test_react_planner.py: mock LLMProvider.chat_completion() to return "Think: I need to find X\nAct: find a apple", verify returns (thought, action) tuple, test with empty history, test with multi-step history, test max_steps enforcement
- [x] T010 [P] [US1] Write integration test for ReActAlfredEvaluator.evaluate_task() in tests/test_react_planner.py: mock ThorConnector and LLMProvider, simulate 3-step task (think+find, think+pick, think+done), verify trace contains all thoughts/actions/observations, verify success detection

### Implementation

- [x] T011 [US1] Implement react_step() core method in src/alfred/react_task_planner.py: build messages list from system prompt + few-shot + task instruction + history (formatted as Think/Act/Obs blocks), call self.llm.chat_completion(messages), parse output via parse_react_output(), return (thought, action) tuple
- [x] T012 [US1] Create ReActAlfredEvaluator class in src/alfred/react_evaluator.py extending AlfredEvaluator: override evaluate_task() with the ReAct loop -- for each step: call planner.react_step(), record thought, execute action via env.llm_skill_interact(), construct observation, append to history. Continue on failure (failure = observation). Stop on "done" or max_steps. Check goal satisfaction at end.
- [x] T013 [US1] Add alfred_react dispatch entry to src/evaluate.py: add `elif cfg.name == 'alfred_react': from src.alfred.react_evaluator import ReActAlfredEvaluator; evaluator = ReActAlfredEvaluator(cfg)` in the main() dispatch block

**Checkpoint**: User Story 1 functional -- ReAct planner runs in the eval loop, produces reasoning traces, executes actions in AI2-THOR

---

## Phase 4: User Story 2 - Evaluate on Dataset Subset (Priority: P2)

**Goal**: Run the ReAct planner on a 5% configurable subset of the evaluation dataset with a summary report

**Independent Test**: Run evaluation with 5% config, verify ~5% of tasks are evaluated and a summary report with success rate is produced

### Tests (TDD Red Phase)

- [x] T014 [US2] Write unit test for evaluation summary reporting in tests/test_react_planner.py: mock a completed evaluation run with known results, verify output JSON includes total_evaluated, total_success, success_rate, avg_steps, by_task_type breakdown

### Implementation

- [x] T015 [US2] Ensure ReActAlfredEvaluator.evaluate() reuses parent AlfredEvaluator's dataset loading and subset selection (cfg.alfred.eval_portion_in_percent, cfg.alfred.random_seed_for_eval_subset) in src/alfred/react_evaluator.py -- verify the override or inheritance path works correctly
- [x] T016 [US2] Implement evaluation summary reporting in src/alfred/react_evaluator.py: after all tasks complete, output aggregate JSON with total_evaluated, total_success, success_rate, avg_steps, and by_task_type breakdown (similar to gt_evaluator.py report format)

**Checkpoint**: User Story 2 functional -- 5% subset evaluation completes with summary statistics

---

## Phase 5: User Story 3 + 4 - Modular Integration + Interpretable Traces (Priority: P3)

**Goal (US3)**: Planner is selectable via config only -- switching between existing planner and ReAct requires no code changes

**Goal (US4)**: Per-task JSON output includes full reasoning trace with Think/Act/Obs entries for post-hoc analysis

**Independent Test (US3)**: Run same task set with `--config-name=config_alfred` and `--config-name=config_alfred_react`, both produce valid results

**Independent Test (US4)**: Inspect per-task JSON output and verify it contains reasoning_trace array with alternating think/act/obs entries

### Tests (TDD Red Phase)

- [x] T017 [P] [US3] Write integration test for config-based planner dispatch in tests/test_react_planner.py: mock Hydra config with name='alfred_react', verify ReActAlfredEvaluator is instantiated; mock with name='alfred', verify AlfredEvaluator is instantiated
- [x] T018 [P] [US4] Write unit test for reasoning trace JSON format in tests/test_react_planner.py: verify per-task result dict contains 'reasoning_trace' key with list of dicts each having 'step_number', 'thought', 'action', 'observation', 'action_success' fields per data-model.md

### Implementation

- [x] T019 [US4] Implement full reasoning trace recording in src/alfred/react_evaluator.py: build reasoning_trace list during evaluate_task(), each entry a dict with step_number, thought, action, observation, action_success per data-model.md ReActStep entity. Include in per-task result JSON and save via existing save_result() pattern.
- [x] T020 [US3] Verify planner modularity: ensure evaluate.py dispatch routes alfred_react correctly, ensure both config_alfred.yaml and config_alfred_react.yaml work with the same evaluation pipeline, add compatibility field 'inferred_steps' to result dict for backward compatibility with existing result analysis tools

**Checkpoint**: All user stories functional -- modular planner selection + interpretable traces in output

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Quality assurance, linting, and validation

- [x] T021 Run ruff lint check on all new and modified files: src/alfred/react_task_planner.py, src/alfred/react_evaluator.py, src/evaluate.py, tests/test_react_planner.py
- [x] T022 Run full pytest suite to ensure no regressions in existing tests (test_instance_actions.py, test_gt_evaluator.py, test_gt_report.py)
- [x] T023 Validate quickstart.md instructions: verify `python src/evaluate.py --config-name=config_alfred_react` runs successfully on 5% subset in non-headless mode
- [x] T024 Review reasoning traces from validation run: confirm traces are interpretable, contain task decomposition thoughts, show error recovery when actions fail

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies -- can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (prompts + config must exist for planner init)
- **US1 (Phase 3)**: Depends on Phase 2 (needs planner skeleton + parsing + observation)
- **US2 (Phase 4)**: Depends on US1 (needs working evaluator to test subset evaluation)
- **US3+US4 (Phase 5)**: Depends on US1 (needs working evaluator for modularity + traces)
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 -- no dependencies on other stories
- **US2 (P2)**: Depends on US1 (evaluator must exist before testing subset behavior)
- **US3 (P3)**: Depends on US1 (planner + evaluator must exist for config switching test)
- **US4 (P3)**: Depends on US1 (trace recording is part of evaluator loop)

### Within Each Phase

- Tests MUST be written and FAIL before implementation (Red phase)
- Implementation makes tests pass (Green phase)
- Refactoring only after tests green

### Parallel Opportunities

**Phase 1**: T002 and T003 can run in parallel (different files)
**Phase 2 Tests**: T004 and T005 can run in parallel (different test classes in same file)
**Phase 3 Tests**: T009 and T010 can run in parallel
**Phase 5 Tests**: T017 and T018 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch tests in parallel (TDD Red phase):
Task: "Write unit tests for react_step() in tests/test_react_planner.py"
Task: "Write integration test for evaluate_task() in tests/test_react_planner.py"

# Then implement sequentially (Green phase):
Task: "Implement react_step() in src/alfred/react_task_planner.py"
Task: "Create ReActAlfredEvaluator in src/alfred/react_evaluator.py"
Task: "Add dispatch entry to src/evaluate.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (config + prompt templates)
2. Complete Phase 2: Foundational (planner skeleton + parsing + observation)
3. Complete Phase 3: User Story 1 (react_step + evaluator loop + dispatch)
4. **STOP and VALIDATE**: Run single task with `--config-name=config_alfred_react alfred.eval_portion_in_percent=1`
5. Verify: planner generates thoughts, executes actions, receives observations, produces trace

### Incremental Delivery

1. Setup + Foundational → Core building blocks ready
2. Add US1 → ReAct planner works end-to-end (MVP!)
3. Add US2 → 5% subset evaluation with reporting
4. Add US3+US4 → Config switching + interpretable JSON traces
5. Polish → Lint clean, all tests pass, quickstart validated

### Commit Strategy (Tidy First)

1. `refactor: extract shared evaluation helpers from AlfredEvaluator` (if needed)
2. `feat: add ReAct config, system prompt, and few-shot examples`
3. `test: add unit tests for ReAct output parsing and observation construction`
4. `feat: implement ReActTaskPlanner with parse_react_output and react_step`
5. `feat: implement ReActAlfredEvaluator with Thought-Action-Observation loop`
6. `feat: add alfred_react dispatch and evaluation reporting`
7. `test: add integration tests for ReAct evaluation pipeline`
8. `feat: add reasoning trace JSON recording and modular planner verification`

---

## Notes

- [P] tasks = different files or independent test classes, no dependencies
- [Story] label maps task to specific user story for traceability
- ReAct prompts must use project's action vocabulary: find/pick up/put down/open/close/turn on/turn off/slice/done
- Observation construction is critical for ReAct quality -- richer observations enable better reasoning
- The existing evaluator stops on failure; the ReAct evaluator MUST continue (failure = observation)
- max_tokens set to 1024 in config (higher than default 500) to accommodate Think + Act output
- Tidy First: structural changes (refactoring helpers) committed separately from behavioral changes (new planner)
