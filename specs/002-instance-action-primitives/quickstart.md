# Quickstart: Instance-Specific Action Primitives

**Feature**: `002-instance-action-primitives`

## Overview

This feature extends the AI2-THOR action primitive system to support targeting specific object instances by their registry ID (e.g., "find Apple_01", "pick up Mug_02") instead of only generic type-based commands (e.g., "find a apple").

## Files Modified

| File | Change |
|------|--------|
| `src/alfred/thor_connector.py` | Add reverse registry, instance detection, modify `llm_skill_interact()` and all action methods |
| `src/alfred/alfred_task_planner.py` | Add `init_instance_skill_set()` method |
| `tests/test_instance_actions.py` | New test file for instance-specific action logic |

## How It Works

### 1. Instance Detection

When `llm_skill_interact("find Apple_01")` is called:

1. Extract the object token after the action prefix: `"Apple_01"`
2. Check if it matches the instance ID pattern: `^[A-Z][a-zA-Z]*_\d+$`
3. If yes: look up in `_obj_registry_by_name` to get the AI2-THOR objectId
4. If no: proceed with existing generic flow (natural_word_to_ithor_name)

### 2. Action Execution

Instance-specific actions pass the resolved objectId directly to action methods:
- `nav_obj(target_obj="Apple", target_obj_id="Apple|01|02|03|05")` — navigates to the exact object
- `pick(obj_name="Apple", target_obj_id="Apple|01|02|03|05")` — picks up the exact object

Generic actions continue to use `get_obj_id_from_name()` for closest-match lookup.

### 3. Skill Set Generation

```python
# After scene setup, with registry available:
instance_skills = planner.init_instance_skill_set(
    registry=env._obj_registry_by_name,
    object_metadata=env.last_event.metadata['objects']
)
# Returns: ["find Apple_01", "find Apple_02", "pick up Mug_01", "open Fridge_01", ...]
```

## Usage Examples

```python
# Instance-specific (new)
env.llm_skill_interact("find Apple_01")       # Navigate to specific apple
env.llm_skill_interact("pick up Mug_02")      # Pick up specific mug
env.llm_skill_interact("open Fridge_01")       # Open specific fridge
env.llm_skill_interact("turn on DeskLamp_01")  # Toggle specific lamp

# Generic (still works, unchanged)
env.llm_skill_interact("find a apple")         # Navigate to nearest apple
env.llm_skill_interact("pick up the mug")      # Pick up nearest mug
```

## Testing

```bash
cd src && pytest ../tests/test_instance_actions.py -v
```

Tests use the existing mock pattern (mock AI2-THOR dependencies) to test:
- Instance ID detection and normalization
- Reverse registry lookup
- Instance-specific action dispatch
- Backward compatibility with generic directives
- Error handling for invalid instance IDs
