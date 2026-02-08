# Action Interface Contract: Instance-Specific Primitives

**Feature**: `002-instance-action-primitives`
**Date**: 2026-02-08

## Contract: llm_skill_interact()

### Input

| Parameter | Type | Description |
|-----------|------|-------------|
| `instruction` | `str` | Natural language action directive |

### Supported Instruction Formats

#### Instance-Specific (new)
| Pattern | Example | Action |
|---------|---------|--------|
| `find <InstanceID>` | `find Apple_01` | Navigate to specific instance |
| `pick up <InstanceID>` | `pick up Mug_02` | Pick up specific instance |
| `put down <InstanceID>` | `put down Apple_01` | Put down held object (uses cur_receptacle) |
| `open <InstanceID>` | `open Fridge_01` | Open specific instance |
| `close <InstanceID>` | `close Fridge_01` | Close specific instance |
| `turn on <InstanceID>` | `turn on DeskLamp_01` | Toggle on specific instance |
| `turn off <InstanceID>` | `turn off DeskLamp_01` | Toggle off specific instance |
| `slice <InstanceID>` | `slice Bread_01` | Slice specific instance |

#### Generic (existing, unchanged)
| Pattern | Example |
|---------|---------|
| `find a/an <object>` | `find a apple` |
| `pick up the <object>` | `pick up the mug` |
| `put down the <object>` | `put down the apple` |
| `open the <object>` | `open the fridge` |
| `close the <object>` | `close the fridge` |
| `turn on the <object>` | `turn on the desk lamp` |
| `turn off the <object>` | `turn off the desk lamp` |
| `slice the <object>` | `slice the bread` |
| `drop` | `drop` |

### Output

```python
{
    "action": str,      # Original instruction string
    "success": bool,    # True if action completed successfully
    "message": str      # Error message (empty string if successful)
}
```

### Error Responses

| Condition | message value |
|-----------|---------------|
| Instance ID not in registry | `"Instance ID '{id}' not found in object registry"` |
| Object not found in scene | `"Cannot find {obj_name}"` |
| Object not visible | `"{obj_name} is not visible because it is in {receptacle}"` |
| Navigation failure | `"Cannot move to {obj_name}"` |
| Inventory conflict | `"Robot is currently holding {type}"` |
| Action execution failure | `"{Action} action failed"` |

## Contract: Reverse Registry Lookup

### resolve_instance_id()

| Parameter | Type | Description |
|-----------|------|-------------|
| `instance_id` | `str` | Human-readable registry ID (e.g., "Apple_01") |

**Returns**: `str | None` — AI2-THOR objectId or None if not found

**Normalization**: Leading zeros stripped from numeric suffix before lookup.

## Contract: Instance-Aware Skill Set

### init_instance_skill_set()

| Parameter | Type | Description |
|-----------|------|-------------|
| `registry` | `Dict[str, str]` | Reverse registry (readable_name -> objectId) |
| `object_metadata` | `List[dict]` | AI2-THOR object metadata list |

**Returns**: `List[str]` — Skill set with instance-specific directives

**Generated skill categories**:
- `find <InstanceID>` for all objects in registry
- `pick up <InstanceID>` for pickupable objects
- `open <InstanceID>` / `close <InstanceID>` for openable objects
- `turn on <InstanceID>` / `turn off <InstanceID>` for toggleable objects
- `slice <InstanceID>` for sliceable objects
- `done` terminator

## Contract: Instance ID Detection

### Pattern

```
^[A-Z][a-zA-Z]*_\d+$
```

**Matches**: `Apple_1`, `Apple_01`, `DeskLamp_2`, `StoveBurner_1`
**Does not match**: `apple`, `desk lamp`, `a apple`, `the mug`, `Apple_`, `_01`
