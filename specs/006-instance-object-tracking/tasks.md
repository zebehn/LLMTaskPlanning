# Tasks: Instance-Aware Object Tracking in ReAct Loop

**Input**: Design documents from `/specs/006-instance-object-tracking/`
**Prerequisites**: plan.md, spec.md, research.md, contracts/observation-format.md, quickstart.md

**TDD**: All production code is preceded by a failing test (Red → Green per constitution).

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

**Purpose**: No new project structure is needed. The object registry, `readable_id()`, and instance routing are already implemented. This phase verifies the test harness is ready.

- [X] T001 Confirm `tests/test_thor_connector_observations.py` does not exist yet and `pytest tests/` passes (271 pass, 8 pre-existing AI2-THOR mock failures)

---

## Phase 2: Foundational

No blocking prerequisites — the object registry (`_obj_registry`, `readable_id()`) and `_dispatch_instance_or_generic()` are fully implemented. Proceed directly to user stories.

**Checkpoint**: Skip — foundation already exists.

---

## Phase 3: User Story 1 — Instance ID in Observations (Priority: P1) 🎯 MVP

**Goal**: `pick()` and `put()` success observations include `<Type>_<N>` instance labels so the LLM can refer back to specific objects.

**Independent Test**: Run `pytest tests/test_thor_connector_observations.py` — all 5 tests pass. Inspect a single-task ReAct trace and confirm observations read `"Picked up Cup_1."` and `"Put Cup_1 in CounterTop_2."`.

### Tests for User Story 1 (TDD — write FIRST, verify FAIL before implementing)

- [X] T002 [US1] Write test `test_pick_success_returns_instance_label` in `tests/test_thor_connector_observations.py` — mock a successful PickupObject; assert return value matches regex `r"^Picked up \w+_\d+\.$"`
- [X] T003 [US1] Write test `test_pick_failure_observation_unchanged` in `tests/test_thor_connector_observations.py` — mock a failed pick; assert return value does NOT contain an instance label (existing message format preserved)
- [X] T004 [P] [US1] Write test `test_put_success_returns_object_and_receptacle_labels` in `tests/test_thor_connector_observations.py` — mock a successful PutObject; assert return value matches regex `r"^Put \w+_\d+ in \w+_\d+\.$"`
- [X] T005 [P] [US1] Write test `test_put_failure_observation_unchanged` in `tests/test_thor_connector_observations.py` — mock a failed put; assert return value does NOT contain `" in "` label pattern (existing message preserved)
- [X] T006 [P] [US1] Write test `test_pick_label_matches_registry_entry` in `tests/test_thor_connector_observations.py` — set up registry with a known objectId→label mapping; assert the label in the observation exactly matches `readable_id(obj_id)`

### Implementation for User Story 1

> **Note**: Implement only AFTER T002–T006 are confirmed FAILING.

- [X] T007 [US1] In `src/alfred/thor_connector.py` `pick()` method (line ~502): change `ret_msg = ''` on success branch to `ret_msg = f"Picked up {self.readable_id(obj_id)}."`
- [X] T008 [US1] In `src/alfred/thor_connector.py` `put()` method (line ~592): change `ret_msg = ''` on success branch to `ret_msg = f"Put {self.readable_id(holding_obj_id)} in {self.readable_id(recep_id)}."`
- [X] T009 [US1] Run `pytest tests/test_thor_connector_observations.py` — all 5 new tests must pass
- [X] T010 [US1] Run `pytest tests/test_instance_actions.py` — all 53 pre-existing tests must still pass

**Checkpoint**: US1 complete — `pytest tests/test_thor_connector_observations.py tests/test_instance_actions.py` all green.

---

## Phase 4: User Story 2 — Instance-Specific Find in Few-Shot Prompt (Priority: P2)

**Goal**: The "hot egg" few-shot example updated to demonstrate `find Egg_1` return navigation after heating, teaching the model to track object instances across transformation tasks.

**Independent Test**: Inspect `src/prompts/templates/react_few_shot_examples.txt` — the hot egg example must contain at least one `find Egg_1` action and the observations `"Picked up Egg_1."` and `"Put Egg_1 in Microwave_1."`.

**Note**: No test file is needed for prompt changes — validation is done by inspection and a manual trace check.

### Implementation for User Story 2

- [X] T011 [US2] In `src/prompts/templates/react_few_shot_examples.txt`, update the hot egg example:
  - Obs after first `pick up the egg` → `"Picked up Egg_1."`
  - Obs after `put down the egg` (into microwave) → `"Put Egg_1 in Microwave_1."`
  - Replace post-heating `find a egg` → `find Egg_1`
  - Replace post-heating `pick up the egg` → `pick up the Egg_1`
  - Obs after second pick → `"Picked up Egg_1."`
  - Obs after final put (into fridge) → `"Put Egg_1 in Fridge_1."`
  - Update Think steps to reflect instance-aware reasoning (e.g., "I need to find Egg_1 that I already heated")
- [X] T012 [US2] Verify the updated prompt against `specs/006-instance-object-tracking/quickstart.md` Scenario 1 — all observation strings and action tokens match
- [X] T013 [US2] Run `pytest tests/test_react_planner.py` — all 27 pre-existing tests must still pass (prompt loading is not broken)

**Checkpoint**: US2 complete — prompt updated, all existing tests green.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T014 Run full test suite `pytest tests/ --ignore=tests/test_ai2thor_compatibility.py` — 276+ tests pass (271 pre-existing + 5 new)
- [X] T015 [P] Update `docs/action_failure_causal_analysis.md` notes section to record that the instance-mismatch failure pattern identified in analysis is now addressed by this feature

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **US1 (Phase 3)**: Depends on Phase 1 only — tests written first, then implementation
- **US2 (Phase 4)**: Independent of US1 (different files) but logically sequenced after US1 so the prompt shows observations consistent with the updated format
- **Polish (Phase 5)**: Depends on US1 + US2 completion

### Within User Story 1

- T002 (test) → T007 (impl): sequential, TDD order
- T003 (test) → T007 (impl): sequential, TDD order
- T004, T005, T006 (tests): parallelizable [P] — different test functions, same file
- T007, T008 (impl): parallelizable — different lines of same file, no dependency
- T009, T010 (verification): sequential after T007–T008

### Parallel Opportunities

```bash
# Tests T004, T005, T006 can be written in parallel (same file, different functions):
# Write test_put_success, test_put_failure, test_pick_label_matches_registry

# Implementations T007 and T008 can be done in the same edit pass (adjacent methods):
# Edit pick() then put() in thor_connector.py
```

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. T001 — confirm baseline
2. T002–T006 — write all 5 tests (Red)
3. T007–T008 — implement the two return-value changes (Green)
4. T009–T010 — verify no regressions
5. **STOP and VALIDATE** — observations contain instance labels in all success cases

### Full Delivery

1. MVP complete
2. T011–T013 — update few-shot prompt and verify
3. T014–T015 — polish and documentation

---

## Notes

- [P] tasks touch different functions or files — safe to parallelise
- All tests MUST be written and confirmed FAILING before implementing T007–T008
- The 8 pre-existing failures in `test_ai2thor_compatibility.py` are unrelated mock issues — ignore them
- `readable_id()` already handles unknown objectIds gracefully (returns the raw ID) — no defensive coding needed
