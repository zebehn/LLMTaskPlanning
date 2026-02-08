# Research: Instance-Specific Action Primitives

**Feature**: `002-instance-action-primitives`
**Date**: 2026-02-08

## Research Task 1: Instance ID Detection Pattern

**Question**: How to reliably distinguish instance-specific directives (e.g., "find Apple_01") from generic directives (e.g., "find a apple") in the existing NL parsing pipeline?

**Decision**: Use regex pattern matching on the extracted object name token. After stripping the action prefix, check if the remaining token matches `^[A-Z][a-zA-Z]*_\d+$` (CamelCase type + underscore + digits). This leverages the existing registry naming convention (`Type_N`).

**Rationale**:
- The existing `_build_object_registry()` already creates IDs in exactly this format: `f"{obj_type}_{type_counts[obj_type]}"` where `obj_type` is CamelCase (e.g., `Apple_1`, `Mug_2`)
- Generic directives always include articles ("a", "an", "the") before the object name in lowercase natural language
- Instance IDs use CamelCase with underscores, which never appears in generic directives
- The pattern is unambiguous: "Apple_01" is instance-specific; "apple" is generic

**Alternatives considered**:
1. **Lookup-first approach**: Try registry lookup first, fall back to generic. Rejected because it adds latency and doesn't clearly separate code paths.
2. **Prefix-based approach**: Use a different prefix (e.g., "find instance Apple_01"). Rejected because it changes the NL format unnecessarily and complicates LLM prompting.

## Research Task 2: Registry Reverse Lookup Architecture

**Question**: The current `_obj_registry` maps `AI2Thor_objectId -> readable_name`. We need to go from `readable_name -> AI2Thor_objectId`. What's the best approach?

**Decision**: Build a reverse mapping `_obj_registry_by_name` (dict: `readable_name -> AI2Thor_objectId`) alongside the existing registry in `_build_object_registry()`. Both are built in a single pass.

**Rationale**:
- O(1) lookup vs O(N) scan of the forward registry
- Built once at scene initialization (same time as forward registry) — zero extra scene queries
- Memory overhead is negligible (one extra dict with same number of entries)
- The existing `readable_id()` method uses the forward mapping for logging; the reverse mapping is the natural complement for action dispatch

**Alternatives considered**:
1. **Scan _obj_registry values on each call**: O(N) per lookup, inefficient for frequent use. Rejected.
2. **Use `get_obj_id_from_name()` with objectType + index**: Would require parsing the instance ID into type and count, then iterating all objects and counting — fragile and slow. Rejected.

## Research Task 3: Integration with Existing Action Methods

**Question**: The action methods (`pick()`, `put()`, `open()`, etc.) all accept objectType strings and internally call `get_obj_id_from_name()` to find the closest matching object. For instance-specific actions, we already know the exact objectId. How should we integrate?

**Decision**: Add an optional `target_obj_id` parameter to each action method. When provided, skip the `get_obj_id_from_name()` lookup and use the provided objectId directly. The `llm_skill_interact()` method handles the dispatch: if instance ID detected, resolve via reverse registry, then pass `target_obj_id` to the action method.

**Rationale**:
- Minimal code change per action method (add one parameter, add one early-return branch)
- Preserves all existing behavior when `target_obj_id` is not provided
- Avoids duplicating action logic in separate methods
- The `nav_obj()` method similarly needs `target_obj_id` to navigate to the exact object instead of the closest match by type

**Alternatives considered**:
1. **Create parallel `pick_by_id()`, `open_by_id()` methods**: Rejected — massive code duplication, hard to maintain.
2. **Modify `get_obj_id_from_name()` to accept objectId directly**: Rejected — conflates two different lookup strategies in one method, unclear interface.

## Research Task 4: Instance-Aware Skill Set Generation

**Question**: How should instance-aware skill sets be generated for the AlfredTaskPlanner? Should they replace or augment generic skills?

**Decision**: Add a new method `init_instance_skill_set(registry)` to `AlfredTaskPlanner` that generates instance-specific skills from the live object registry. This can be called after scene setup (when the registry is available). It generates skills using registry IDs instead of generic type names. A configuration flag controls whether to use instance-aware or generic skill sets.

**Rationale**:
- The existing `init_skill_set()` uses hardcoded class-level object lists (e.g., `alfred_pick_obj`) that are not scene-specific
- Instance-aware skills must be generated per-scene since each scene has different objects
- Keeping both methods allows the system to switch between modes via config
- The skill set format matches LLM expectations: "find Apple_01", "pick up Mug_02"

**Alternatives considered**:
1. **Modify `init_skill_set()` to conditionally generate instance skills**: Rejected — too many conditionals, complicates the already working method.
2. **Generate both generic and instance skills in the same set**: Considered viable for mixed-mode planning but deferred to avoid skill set explosion (doubles the candidate count).

## Research Task 5: Registry Update on Slice

**Question**: When an object is sliced in AI2-THOR, new objects appear (e.g., slicing Bread creates BreadSliced instances). How should the registry handle this?

**Decision**: Call `_build_object_registry()` after any slice action to rebuild the full registry. This picks up newly created sliced objects automatically.

**Rationale**:
- Slicing is a destructive action that fundamentally changes the scene's object inventory
- Rebuilding is simple, correct, and avoids incremental update bugs
- Performance is negligible (single metadata scan, happens infrequently)
- The existing `_build_object_registry()` already handles any scene state — it just needs to be called again

**Alternatives considered**:
1. **Incremental registry update**: Parse slice result to find new objects and add them. Rejected — complex, error-prone, and slice is rare enough that full rebuild is fine.
2. **Lazy rebuild on next instance lookup**: Rejected — stale registry could cause lookup failures between slice and next action.

## Research Task 6: Instance ID Format Normalization

**Question**: The registry generates IDs like `Apple_1` (no zero-padding). Users might type `Apple_01`. How to handle format mismatches?

**Decision**: Normalize both the directive's instance ID and registry keys by stripping leading zeros from the numeric suffix during lookup. `Apple_01` and `Apple_1` both resolve to the same object.

**Rationale**:
- Zero-padding is a common user expectation (especially in LLM-generated text)
- Simple normalization function: split on last `_`, strip leading zeros from number part, rejoin
- Applied once at lookup time, no registry modification needed

**Alternatives considered**:
1. **Store both padded and unpadded forms in registry**: Rejected — pollutes the registry with duplicates.
2. **Force strict format matching**: Rejected — too brittle for LLM-generated directives.
