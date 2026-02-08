# Implementation Plan: Instance-Specific Action Primitives

**Branch**: `002-instance-action-primitives` | **Date**: 2026-02-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-instance-action-primitives/spec.md`

## Summary

Extend the AI2-THOR action primitive system to support targeting specific object instances by their registry ID (e.g., "find Apple_01", "pick up Mug_02"). The approach adds a reverse registry lookup (`readable_name -> objectId`), an instance ID detection layer in `llm_skill_interact()`, and optional `target_obj_id` parameters to all action methods. A new `init_instance_skill_set()` method generates instance-aware candidate action lists for LLM planners. Full backward compatibility with generic directives is preserved.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: ai2thor>=5.0.0, hydra-core==1.3.2, omegaconf==2.3.0, scipy, numpy, Pillow>=9.4.0
**Storage**: N/A (in-memory registry dicts)
**Testing**: pytest (with AI2-THOR module mocking via `unittest.mock.patch.dict(sys.modules, ...)`)
**Target Platform**: Linux/macOS (AI2-THOR simulator host)
**Project Type**: Single project
**Performance Goals**: Instance lookup O(1) via dict; registry rebuild O(N) where N = scene object count (~100-300 objects)
**Constraints**: All changes must be backward-compatible; no new external dependencies
**Scale/Scope**: 2 files modified (`thor_connector.py`, `alfred_task_planner.py`), 1 new test file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with TDD and Tidy First principles:

- [x] **TDD Cycle**: Plan includes test-first approach — tests written before each implementation increment (see Implementation Phases below)
- [x] **Tidy First**: Structural changes (adding `target_obj_id` parameter to method signatures) separated from behavioral changes (instance dispatch logic)
- [x] **Commit Discipline**: Plan supports small, atomic commits: `refactor:` for structural prep, `feat:` for instance detection, `feat:` for action methods, `feat:` for skill sets, `test:` for tests
- [x] **Code Quality**: DRY (single detection function, single resolve function), YAGNI (no speculative features), single responsibility (detection separate from dispatch separate from execution)
- [x] **Refactoring**: `_build_object_registry()` extension is structural (adding reverse dict); separated from behavioral instance dispatch
- [x] **Simplicity**: Reuses existing action methods with optional parameter; no new classes or abstractions

## Project Structure

### Documentation (this feature)

```text
specs/002-instance-action-primitives/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: Research decisions
├── data-model.md        # Phase 1: Data model
├── quickstart.md        # Phase 1: Usage guide
├── contracts/           # Phase 1: Interface contracts
│   └── action-interface.md
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── alfred/
│   ├── thor_connector.py       # MODIFIED: reverse registry, instance detection, action method signatures
│   ├── alfred_task_planner.py  # MODIFIED: add init_instance_skill_set()
│   └── utils.py                # UNCHANGED (existing name conversion utilities)
├── task_planner.py             # UNCHANGED (base class)
└── evaluate.py                 # UNCHANGED (dispatch)

tests/
└── test_instance_actions.py    # NEW: unit tests for instance-specific actions
```

**Structure Decision**: Follows existing single-project layout. Changes are confined to two existing files in `src/alfred/` plus one new test file. No new packages or directories needed in `src/`.

## Implementation Phases

### Phase A: Structural Preparation (Tidy First)

**Commit prefix**: `refactor:`

1. **Extend `_build_object_registry()`** to build both forward and reverse mappings
   - Add `self._obj_registry_by_name = {}` in `__init__`
   - Populate it in `_build_object_registry()` alongside existing forward mapping
   - No behavioral change — just additional data structure

2. **Add `target_obj_id=None` parameter** to action method signatures
   - Methods: `nav_obj()`, `pick()`, `put()`, `open()`, `close()`, `toggleon()`, `toggleoff()`, `slice()`
   - No behavioral change — parameter is unused until Phase B

### Phase B: Instance Detection & Resolution (Core Feature)

**Commit prefix**: `feat:`

1. **Add instance ID detection helper**
   - `_is_instance_id(token: str) -> bool`: regex check `^[A-Z][a-zA-Z]*_\d+$`
   - `_normalize_instance_id(instance_id: str) -> str`: strip leading zeros from numeric suffix
   - `_resolve_instance_id(instance_id: str) -> tuple[str, str] | None`: lookup in reverse registry, return `(thor_object_id, object_type)` or None

2. **Modify `llm_skill_interact()`** to detect and dispatch instance-specific directives
   - After extracting the object token from each action branch, check `_is_instance_id()`
   - If instance: resolve via `_resolve_instance_id()`, pass `target_obj_id` to action method
   - If generic: proceed with existing `natural_word_to_ithor_name()` flow
   - Handle error case: instance ID not found in registry

### Phase C: Action Method Integration

**Commit prefix**: `feat:`

1. **Implement `target_obj_id` handling in `nav_obj()`**
   - When `target_obj_id` is provided: skip `get_obj_id_from_name()`, look up object data directly from metadata by objectId
   - Rest of navigation logic (teleport, visibility check) remains the same

2. **Implement `target_obj_id` handling in manipulation methods**
   - `pick()`: when `target_obj_id` provided, skip `get_obj_id_from_name()` lookup
   - `open()`, `close()`, `toggleon()`, `toggleoff()`, `slice()`: same pattern
   - `put()`: when `target_obj_id` provided, use it as the receptacle objectId directly

3. **Registry rebuild after slice**
   - After successful `slice()`, call `_build_object_registry()` to capture new sliced instances

### Phase D: Instance-Aware Skill Set Generation

**Commit prefix**: `feat:`

1. **Add `init_instance_skill_set()` to `AlfredTaskPlanner`**
   - Takes `registry` (reverse mapping) and `object_metadata` (scene objects)
   - Cross-references registry IDs with object properties (pickupable, openable, toggleable, sliceable)
   - Generates instance-specific skill entries using the same action verb patterns

2. **Keep `init_skill_set()` unchanged** for backward compatibility

### Phase E: Tests

**Commit prefix**: `test:`

Tests are written incrementally following TDD (test-first for each phase above). Consolidated here for clarity.

1. **Instance ID detection tests**
   - `_is_instance_id()`: positive cases (Apple_1, DeskLamp_02), negative cases (apple, desk lamp, Apple_, _01)
   - `_normalize_instance_id()`: Apple_01 -> Apple_1, Mug_1 -> Mug_1
   - `_resolve_instance_id()`: found, not found, normalized match

2. **Reverse registry tests**
   - Registry built correctly from mock metadata
   - Forward and reverse mappings are consistent
   - Rebuild after slice updates both mappings

3. **Instance-specific action dispatch tests**
   - `llm_skill_interact("find Apple_01")` detects instance, resolves, calls nav_obj with target_obj_id
   - `llm_skill_interact("pick up Mug_01")` dispatches correctly
   - All action types tested: find, pick up, put down, open, close, turn on, turn off, slice

4. **Backward compatibility tests**
   - `llm_skill_interact("find a apple")` behaves identically to pre-change
   - `llm_skill_interact("pick up the mug")` behaves identically

5. **Error handling tests**
   - Invalid instance ID: "find Apple_99" when not in registry
   - Malformed: "find apple_" — falls through to generic path
   - Empty registry: error when `_obj_registry_by_name` is empty

6. **Instance-aware skill set tests**
   - Generated skills contain correct instance IDs
   - Pickupable/openable/toggleable filtering works
   - Skills match expected format ("find Apple_01", "pick up Mug_02")

### Mocking Strategy

All tests mock AI2-THOR dependencies using the established pattern:

```python
_thor_mocks = {}
for mod_name in ["env", "env.thor_env", "gen", "gen.constants",
                 "gen.utils", "gen.utils.game_util",
                 "alfred", "alfred.utils", "alfred.data", "alfred.data.preprocess",
                 "scipy", "scipy.spatial"]:
    _thor_mocks[mod_name] = MagicMock()

with patch.dict(sys.modules, _thor_mocks):
    from src.alfred.thor_connector import ThorConnector
```

For action method tests, mock `ThorConnector` as a class with controllable `_obj_registry`, `_obj_registry_by_name`, and `last_event.metadata` attributes.

## Constitution Check (Post-Design)

- [x] **TDD Cycle**: Tests defined for each phase; detection helpers testable in isolation
- [x] **Tidy First**: Phase A is purely structural (signatures, data structures); Phases B-D are behavioral
- [x] **Commit Discipline**: 5 clear commits: refactor (structural), feat (detection), feat (action methods), feat (skill sets), test (tests)
- [x] **Code Quality**: Single detection function reused across all action branches; no duplication
- [x] **Refactoring**: Registry extension is structural, tested independently before behavioral changes
- [x] **Simplicity**: No new classes, no new files in src/ (only test file is new), optional parameters preserve existing interfaces
