# Research: Instance-Aware Object Tracking

**Feature**: `006-instance-object-tracking`
**Date**: 2026-03-10

---

## Decision 1: Observation string source

**Decision**: Modify `pick()` and `put()` return values in `ThorConnector` directly.

**Rationale**: Both methods already return a string that becomes the observation shown to the model (empty string `''` on success, error message on failure). The react evaluator passes this string through unchanged. Adding the instance label here requires changing exactly two lines (one per method) and is the minimal-diff approach.

**Alternatives considered**:
- Wrapping in the react evaluator: would require parsing the action type from the instruction string post-hoc — brittle.
- Adding a separate `last_observation` attribute: unnecessary indirection.

---

## Decision 2: Instance label format

**Decision**: Use the existing `readable_id(obj_id)` method which returns `<ObjectType>_<N>` (e.g., `Cup_1`, `Egg_2`). Labels are assigned by `_build_object_registry()` at scene reset, sorted by objectId for stability.

**Rationale**: The format is already implemented, tested, and consistent with instance-specific find/nav routing (which already accepts `Cup_1` style tokens). No new naming scheme is needed.

**Alternatives considered**:
- Using raw AI2-THOR objectIds (`Cup|-0.24|0.94|-1.54`): unreadable, leaks coordinates, model cannot parse them reliably.
- Using a separate instance counter: duplicates existing registry logic.

---

## Decision 3: put() observation — what receptacle label to include

**Decision**: In `put()`, the successful receptacle objectId is `recep_id` (local variable in the retry loop). Pass `holding_obj_id` (captured before the loop at line 516) and `recep_id` to `readable_id()` to produce `"Put Cup_1 in Microwave_1"`.

**Rationale**: Both IDs are already in scope at the success point (line 592). The holding object ID is captured once before the retry loop; `recep_id` is the last attempted (and successful) receptacle. No additional simulator queries needed.

---

## Decision 4: Few-shot example to update

**Decision**: Update the "hot egg" example (`pick_heat_then_place_in_recep`) — the highest-impact transformation task type (38.2% success, largest failure delta vs. GPT-5.2).

**Rationale**: One well-chosen example is sufficient for few-shot learning. The model will generalise the `find <Type>_N` pattern to cool and clean tasks from a single heat example. Adding all three would make the prompt longer without proportional gain.

**Pattern change**: After `pick up the egg` succeeds (obs: `"Picked up Egg_1"`), the model opens the microwave, puts the egg in, closes, turns on, turns off, opens — then issues `find Egg_1` instead of `find a egg`, and `pick up the Egg_1` instead of `pick up the egg`.

**Alternatives considered**:
- Updating all three transformation examples: increases prompt token count by ~60 tokens, unnecessary given few-shot generalisation capacity.
- Adding a fourth dedicated "recovery find" example: out of scope for MVP.

---

## Decision 5: Scope of observation labelling

**Decision**: Label only `pick` and `put` success observations. Other actions (open, close, toggleon, toggleoff, find, slice) are not changed.

**Rationale**:
- `find` already produces descriptive observations like "Found egg. You are now near the egg on the countertop." — these don't need an instance label since the model has just navigated to a known object.
- `open/close/toggleon/toggleoff` involve receptacles or light sources; the model does not need to refer back to these by instance in the current task types.
- Minimal change reduces regression risk.

---

## No NEEDS CLARIFICATION items remain.
