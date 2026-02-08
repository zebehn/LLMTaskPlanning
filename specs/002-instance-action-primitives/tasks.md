# Tasks: Instance-Specific Action Primitives

**Input**: Design documents from `/specs/002-instance-action-primitives/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: TDD is required per constitution. Tests are written before implementation in each user story phase.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Structural preparation (Tidy First — no behavioral changes)

- [X] T001 Add `self._obj_registry_by_name = {}` attribute in `ThorConnector.__init__()` and populate it in `_build_object_registry()` as a reverse mapping (`readable_name -> objectId`) alongside the existing forward mapping in `src/alfred/thor_connector.py`
- [X] T002 Add `target_obj_id=None` optional parameter to `nav_obj()` method signature in `src/alfred/thor_connector.py` (no behavioral change — parameter unused)
- [X] T003 Add `target_obj_id=None` optional parameter to `pick()`, `put()`, `open()`, `close()`, `toggleon()`, `toggleoff()`, and `slice()` method signatures in `src/alfred/thor_connector.py` (no behavioral change — parameter unused)

**Checkpoint**: Structural changes complete. All existing tests still pass. Existing behavior unchanged. Commit with `refactor:` prefix.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Instance ID detection and resolution helpers that ALL user stories depend on

**Critical**: No user story work can begin until this phase is complete

### Tests (TDD - Red Phase)

- [X] T004 [P] Write tests for `_is_instance_id()` in `tests/test_instance_actions.py`: positive cases (`Apple_1`, `Apple_01`, `DeskLamp_2`, `StoveBurner_1`, `CD_1`), negative cases (`apple`, `desk lamp`, `a apple`, `the mug`, `Apple_`, `_01`, `apple_1`, `01_Apple`, empty string). Use AI2-THOR module mocking pattern from `tests/test_gt_evaluator.py`.
- [X] T005 [P] Write tests for `_normalize_instance_id()` in `tests/test_instance_actions.py`: `Apple_01` -> `Apple_1`, `Mug_1` -> `Mug_1`, `DeskLamp_002` -> `DeskLamp_2`, `Apple_0` -> `Apple_0`
- [X] T006 [P] Write tests for `_resolve_instance_id()` in `tests/test_instance_actions.py`: found in registry, not found returns None, normalized match (`Apple_01` resolves same as `Apple_1`), empty registry returns None
- [X] T007 [P] Write tests for reverse registry (`_obj_registry_by_name`) in `tests/test_instance_actions.py`: built correctly from mock metadata with multiple object types, forward and reverse mappings are consistent (every key in forward has corresponding entry in reverse), registry rebuild updates both mappings

### Implementation

- [X] T008 Implement `_is_instance_id(token: str) -> bool` static method in `ThorConnector` class in `src/alfred/thor_connector.py`: regex check `^[A-Z][a-zA-Z]*_\d+$` using `re.match()`
- [X] T009 Implement `_normalize_instance_id(instance_id: str) -> str` static method in `ThorConnector` class in `src/alfred/thor_connector.py`: split on last `_`, strip leading zeros from numeric suffix (keep at least one digit), rejoin
- [X] T010 Implement `_resolve_instance_id(self, instance_id: str) -> tuple[str, str] | None` method in `ThorConnector` class in `src/alfred/thor_connector.py`: normalize the instance_id, look up in `self._obj_registry_by_name`, return `(thor_object_id, object_type)` where object_type is extracted from thor_object_id via `split('|')[0]`, or return None if not found

**Checkpoint**: All detection helper tests pass (Green). Commit with `feat:` prefix.

---

## Phase 3: User Story 1 - Navigate to a Specific Object Instance (Priority: P1) MVP

**Goal**: Agent can navigate to a specific object instance by registry ID (e.g., "find Apple_01")

**Independent Test**: Issue "find Apple_01" in a scene with multiple apples; verify the agent targets the correct one

### Tests for User Story 1 (TDD - Red Phase)

- [X] T011 [P] [US1] Write test for `llm_skill_interact("find Apple_01")` in `tests/test_instance_actions.py`: mock `_resolve_instance_id` to return a known objectId, verify `nav_obj()` is called with `target_obj_id` set to that objectId (not generic flow)
- [X] T012 [P] [US1] Write test for `llm_skill_interact("find Plate_05")` where instance ID is not in registry in `tests/test_instance_actions.py`: verify returns `{'success': False, 'message': "Instance ID 'Plate_05' not found in object registry"}`
- [X] T013 [P] [US1] Write test for `nav_obj()` with `target_obj_id` parameter in `tests/test_instance_actions.py`: verify it skips `get_obj_id_from_name()` and uses the provided objectId directly to look up object data from metadata

### Implementation for User Story 1

- [X] T014 [US1] Modify the `"find "` branch in `llm_skill_interact()` in `src/alfred/thor_connector.py`: after extracting obj_name, check `_is_instance_id(obj_name)`. If instance: resolve via `_resolve_instance_id()`, handle not-found error, call `nav_obj(obj_type, prefer_sliced, target_obj_id=resolved_id)`. If generic: proceed with existing `natural_word_to_ithor_name()` flow unchanged.
- [X] T015 [US1] Implement `target_obj_id` handling in `nav_obj()` method in `src/alfred/thor_connector.py`: when `target_obj_id` is provided, skip the `get_obj_id_from_name()` call and instead find the object data directly from `self.last_event.metadata['objects']` by matching `objectId == target_obj_id`. Rest of navigation logic (teleport, visibility check, rotation sweep) remains the same.

**Checkpoint**: "find Apple_01" works end-to-end. "find a apple" still works identically. All US1 tests pass. Commit with `feat:` prefix.

---

## Phase 4: User Story 2 - Manipulate a Specific Object Instance (Priority: P1)

**Goal**: Agent can pick up, put down, open, close, toggle, and slice specific instances by registry ID

**Independent Test**: Issue "pick up Mug_01" in a scene with two mugs; verify only Mug_01 is picked up

### Tests for User Story 2 (TDD - Red Phase)

- [X] T016 [P] [US2] Write test for `llm_skill_interact("pick up Mug_01")` in `tests/test_instance_actions.py`: verify `pick()` is called with `target_obj_id` set to the resolved objectId
- [X] T017 [P] [US2] Write test for `llm_skill_interact("open Fridge_01")` in `tests/test_instance_actions.py`: verify `open()` is called with `target_obj_id` set to resolved objectId
- [X] T018 [P] [US2] Write tests for remaining instance actions in `tests/test_instance_actions.py`: `"put down Apple_01"`, `"close Fridge_01"`, `"turn on DeskLamp_01"`, `"turn off DeskLamp_01"`, `"slice Bread_01"` — each verifying the correct action method is called with `target_obj_id`
- [X] T019 [P] [US2] Write test for `pick()` with `target_obj_id` parameter in `tests/test_instance_actions.py`: verify it skips `get_obj_id_from_name()` and uses the provided objectId directly for the PickupObject action
- [X] T020 [P] [US2] Write test for registry rebuild after slice in `tests/test_instance_actions.py`: after `slice()` succeeds, verify `_build_object_registry()` is called to capture new sliced instances (BreadSliced_1, etc.)

### Implementation for User Story 2

- [X] T021 [US2] Modify `"pick up "`, `"open "`, `"close "`, `"turn on "`, `"turn off "`, `"slice "`, and `"put down "` branches in `llm_skill_interact()` in `src/alfred/thor_connector.py`: for each branch, after extracting obj_name, check `_is_instance_id(obj_name)`. If instance: resolve via `_resolve_instance_id()`, handle not-found error, pass `target_obj_id` to the action method. If generic: proceed with existing flow unchanged.
- [X] T022 [US2] Implement `target_obj_id` handling in `pick()` method in `src/alfred/thor_connector.py`: when `target_obj_id` is provided, skip `get_obj_id_from_name()`, find object data from metadata by objectId, use it directly for PickupObject action. Existing visibility/receptacle checks still apply using the looked-up object data.
- [X] T023 [US2] Implement `target_obj_id` handling in `open()`, `close()`, `toggleon()`, `toggleoff()` methods in `src/alfred/thor_connector.py`: same pattern as `pick()` — when `target_obj_id` provided, skip `get_obj_id_from_name()`, find object data from metadata by objectId, use directly for the simulator action.
- [X] T024 [US2] Implement `target_obj_id` handling in `put()` method in `src/alfred/thor_connector.py`: when `target_obj_id` is provided, use it as the receptacle objectId directly instead of calling `get_obj_id_from_name()` for the receptacle lookup.
- [X] T025 [US2] Implement `target_obj_id` handling in `slice()` method and add registry rebuild in `src/alfred/thor_connector.py`: when `target_obj_id` provided, use directly. After successful slice (regardless of instance vs generic), call `self._build_object_registry()` to capture newly created sliced instances.

**Checkpoint**: All manipulation actions work with instance IDs. "pick up the mug" generic flow still works identically. All US2 tests pass. Commit with `feat:` prefix.

---

## Phase 5: User Story 3 - Instance-Aware Skill Set Generation (Priority: P2)

**Goal**: LLM planner can receive candidate actions using instance-specific IDs from the live scene registry

**Independent Test**: Initialize a scene, call skill set generation, verify instance-specific entries present

### Tests for User Story 3 (TDD - Red Phase)

- [X] T026 [P] [US3] Write test for `init_instance_skill_set()` basic generation in `tests/test_instance_actions.py`: given mock registry with Apple_1, Apple_2, Mug_1 and mock metadata with pickupable/openable properties, verify returned skill set contains "find Apple_1", "find Apple_2", "find Mug_1", "pick up Apple_1", "pick up Mug_1"
- [X] T027 [P] [US3] Write test for `init_instance_skill_set()` property filtering in `tests/test_instance_actions.py`: verify openable objects get "open"/"close" entries, toggleable objects get "turn on"/"turn off" entries, sliceable types get "slice" entries, and non-applicable actions are excluded (e.g., no "pick up Fridge_1")
- [X] T028 [P] [US3] Write test for `init_instance_skill_set()` always includes "done" terminator in `tests/test_instance_actions.py`

### Implementation for User Story 3

- [X] T029 [US3] Implement `init_instance_skill_set(self, registry, object_metadata)` method in `AlfredTaskPlanner` class in `src/alfred/alfred_task_planner.py`: iterate over registry entries, cross-reference each instance ID with its object properties in metadata (pickupable, openable, toggleable, objectType for sliceable check against `alfred_slice_obj`), generate skill entries: "find {id}" for all, "pick up {id}" for pickupable, "open {id}"/"close {id}" for openable, "turn on {id}"/"turn off {id}" for toggleable, "slice {id}" for sliceable. Prepend "done" to the list. Return skill list.

**Checkpoint**: Instance-aware skill sets generated correctly from live registry. Existing `init_skill_set()` unchanged. All US3 tests pass. Commit with `feat:` prefix.

---

## Phase 6: User Story 4 - Backward Compatibility with Generic Actions (Priority: P2)

**Goal**: All existing generic directives continue to work identically to pre-change behavior

**Independent Test**: Run existing ground-truth evaluation plans and verify identical results

### Tests for User Story 4 (TDD - Red Phase)

- [X] T030 [P] [US4] Write backward compatibility tests for generic `find` in `tests/test_instance_actions.py`: `llm_skill_interact("find a apple")` calls `nav_obj()` with `natural_word_to_ithor_name("apple")` and `target_obj_id=None` (generic path)
- [X] T031 [P] [US4] Write backward compatibility tests for generic `pick up`, `open`, `close`, `turn on`, `turn off`, `slice` in `tests/test_instance_actions.py`: verify each generic format uses the existing code path without `target_obj_id`
- [X] T032 [P] [US4] Write mixed-mode test in `tests/test_instance_actions.py`: execute a plan with alternating instance and generic directives (e.g., ["find Apple_01", "pick up the apple", "find Fridge_01", "open the fridge"]) and verify instance steps use resolved IDs while generic steps use type-based lookup

### Implementation for User Story 4

- [X] T033 [US4] Verify that all `llm_skill_interact()` branches correctly fall through to the existing generic path when `_is_instance_id()` returns False in `src/alfred/thor_connector.py` — this should already work from US1/US2 implementation but verify with the US4 tests and fix any edge cases (e.g., "drop" action which has no object parameter, malformed tokens like "apple_" that fail the regex)

**Checkpoint**: Generic directives produce identical behavior. Mixed plans work correctly. All US4 tests pass. Commit with `feat:` prefix.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Edge case handling, error robustness, code cleanup

- [X] T034 Add structured logging for instance-specific action dispatch in `src/alfred/thor_connector.py`: log instance ID detection, resolution result, and resolved objectId at INFO level using existing `log.info()` pattern
- [X] T035 [P] Write edge case tests in `tests/test_instance_actions.py`: malformed instance IDs ("Apple_", "01_Apple", "Apple" without underscore), empty string, instance ID with zero-padded suffix resolving correctly, "drop" action unaffected by instance detection
- [X] T036 Run `ruff check .` from `src/` directory and fix any linting issues in modified files (`src/alfred/thor_connector.py`, `src/alfred/alfred_task_planner.py`, `tests/test_instance_actions.py`)
- [X] T037 Run full test suite (`pytest` from `src/`) and verify all existing tests plus new tests pass with zero failures

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (structural changes must be in place for tests)
- **User Story 1 (Phase 3)**: Depends on Phase 2 (detection helpers required)
- **User Story 2 (Phase 4)**: Depends on Phase 2 (detection helpers required). Can run in parallel with US1 since they modify different code sections, but US1 first is recommended (navigation before manipulation)
- **User Story 3 (Phase 5)**: Depends on Phase 2 only (skill set generation is independent of action dispatch). Can run in parallel with US1/US2.
- **User Story 4 (Phase 6)**: Depends on US1 + US2 completion (backward compat tests verify all branches work)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (Navigate)**: After Phase 2 — no dependencies on other stories
- **US2 (Manipulate)**: After Phase 2 — independent of US1 but recommended after US1 (similar pattern)
- **US3 (Skill Sets)**: After Phase 2 — fully independent of US1/US2
- **US4 (Backward Compat)**: After US1 + US2 (tests validate all branches modified in those stories)

### Within Each User Story

- Tests (Red phase) MUST be written and FAIL before implementation
- Implementation makes tests pass (Green phase)
- Commit structural and behavioral changes separately per constitution

### Parallel Opportunities

- **Phase 1**: T002 and T003 can run in parallel (different method signatures, same file but non-overlapping)
- **Phase 2 Tests**: T004, T005, T006, T007 can all run in parallel (different test classes, same test file)
- **Phase 2 Impl**: T008, T009 can run in parallel (independent static methods); T010 depends on T008+T009
- **US1 Tests**: T011, T012, T013 can all run in parallel
- **US2 Tests**: T016, T017, T018, T019, T020 can all run in parallel
- **US3 Tests**: T026, T027, T028 can all run in parallel
- **US4 Tests**: T030, T031, T032 can all run in parallel
- **Cross-story**: US1, US2, US3 can start in parallel after Phase 2 (different code sections)

---

## Parallel Example: Phase 2 (Foundational)

```
# Launch all foundational tests in parallel:
T004: Write _is_instance_id() tests in tests/test_instance_actions.py
T005: Write _normalize_instance_id() tests in tests/test_instance_actions.py
T006: Write _resolve_instance_id() tests in tests/test_instance_actions.py
T007: Write reverse registry tests in tests/test_instance_actions.py

# Then implement (T008+T009 in parallel, then T010):
T008: Implement _is_instance_id() in src/alfred/thor_connector.py
T009: Implement _normalize_instance_id() in src/alfred/thor_connector.py
# Wait for T008+T009...
T010: Implement _resolve_instance_id() in src/alfred/thor_connector.py
```

## Parallel Example: User Stories After Foundation

```
# After Phase 2 completes, these can start in parallel:
US1 (Phase 3): Navigate to specific instance — modifies llm_skill_interact "find" branch + nav_obj()
US2 (Phase 4): Manipulate specific instance — modifies other llm_skill_interact branches + action methods
US3 (Phase 5): Skill set generation — modifies alfred_task_planner.py (different file entirely)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (structural prep)
2. Complete Phase 2: Foundational (detection helpers)
3. Complete Phase 3: User Story 1 (navigate to specific instance)
4. **STOP and VALIDATE**: Test "find Apple_01" independently
5. This alone delivers the core capability of instance-targeted navigation

### Incremental Delivery

1. Setup + Foundational -> Detection infrastructure ready
2. Add US1 (Navigate) -> Test independently -> "find Apple_01" works (MVP!)
3. Add US2 (Manipulate) -> Test independently -> "pick up Mug_01", "open Fridge_01" etc. work
4. Add US3 (Skill Sets) -> Test independently -> LLM planner gets instance-specific candidates
5. Add US4 (Backward Compat) -> Test independently -> Confirms zero regression in generic directives
6. Polish -> Lint clean, all tests green, edge cases handled

---

## Notes

- [P] tasks = different files or non-overlapping code sections, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- TDD: Verify tests fail (Red) before implementing (Green) per constitution
- Tidy First: Phase 1 commits use `refactor:` prefix; Phases 2+ use `feat:` or `test:` prefix
- Commit after each phase checkpoint with appropriate prefix
- All tests use AI2-THOR module mocking pattern (no simulator required)
- Total: 37 tasks across 7 phases
