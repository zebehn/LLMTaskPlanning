# Data Model: Instance-Specific Action Primitives

**Feature**: `002-instance-action-primitives`
**Date**: 2026-02-08

## Entities

### Object Instance Registry (Extended)

**Current state** (`ThorConnector._obj_registry`):
- Forward mapping: `Dict[str, str]` — AI2-THOR objectId -> readable name
- Example: `{"Mug|01|02|03|04": "Mug_1", "Apple|01|02|03|05": "Apple_1"}`

**New addition** (`ThorConnector._obj_registry_by_name`):
- Reverse mapping: `Dict[str, str]` — readable name -> AI2-THOR objectId
- Example: `{"Mug_1": "Mug|01|02|03|04", "Apple_1": "Apple|01|02|03|05"}`
- Built simultaneously with forward mapping in `_build_object_registry()`
- Canonical keys use the format `{ObjectType}_{N}` (no zero-padding)

### Instance-Specific Directive

A parsed representation of an instance-targeted action command.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `action_verb` | str | The action prefix | `"find"`, `"pick up"`, `"open"` |
| `instance_id` | str | Registry ID (normalized) | `"Apple_1"` |
| `thor_object_id` | str | Resolved AI2-THOR objectId | `"Apple\|01\|02\|03\|05"` |

### Directive Detection Result

Result of checking whether a directive is instance-specific or generic.

| Field | Type | Description |
|-------|------|-------------|
| `is_instance` | bool | True if instance ID pattern detected |
| `instance_id` | str or None | Normalized registry ID if instance-specific |
| `generic_name` | str or None | Natural language object name if generic |

## State Transitions

### Registry Lifecycle

```
Scene Load
  └─> restore_scene()
       └─> _build_object_registry()
            ├─> _obj_registry: {objectId -> readable_name}
            └─> _obj_registry_by_name: {readable_name -> objectId}

Slice Action
  └─> slice() completes successfully
       └─> _build_object_registry()  [rebuild to capture new sliced instances]
            ├─> _obj_registry: updated with BreadSliced_1, BreadSliced_2, etc.
            └─> _obj_registry_by_name: updated correspondingly
```

### Action Dispatch Flow

```
llm_skill_interact(instruction)
  │
  ├─> detect_instance_id(instruction)
  │     ├─> instance detected: resolve via _obj_registry_by_name
  │     │     └─> pass target_obj_id to action method
  │     └─> generic detected: proceed with existing natural_word_to_ithor_name flow
  │
  ├─> Action Methods (pick, open, close, toggleon, toggleoff, slice):
  │     ├─> target_obj_id provided: use directly (skip get_obj_id_from_name)
  │     └─> target_obj_id not provided: existing behavior (find by type)
  │
  └─> nav_obj():
        ├─> target_obj_id provided: navigate to exact object
        └─> target_obj_id not provided: existing behavior (find closest by type)
```

## Validation Rules

1. **Instance ID format**: Must match `^[A-Z][a-zA-Z]*_\d+$` after extraction from directive
2. **Registry existence**: Instance ID must exist in `_obj_registry_by_name` after normalization
3. **Registry initialization**: `_obj_registry_by_name` must be non-empty before instance lookups (built during `restore_scene()`)
4. **Normalization**: Leading zeros in numeric suffix are stripped: `Apple_01` -> `Apple_1`

## Relationships

```
ThorConnector
  ├── _obj_registry: Dict[thor_id, readable_name]  (existing)
  ├── _obj_registry_by_name: Dict[readable_name, thor_id]  (new)
  ├── llm_skill_interact(instruction)  (modified: instance dispatch)
  ├── nav_obj(target_obj, ..., target_obj_id=None)  (modified: optional direct ID)
  ├── pick(obj_name, target_obj_id=None)  (modified)
  ├── put(receptacle_name, target_obj_id=None)  (modified)
  ├── open(obj_name, target_obj_id=None)  (modified)
  ├── close(obj_name, target_obj_id=None)  (modified)
  ├── toggleon(obj_name, target_obj_id=None)  (modified)
  ├── toggleoff(obj_name, target_obj_id=None)  (modified)
  └── slice(obj_name, target_obj_id=None)  (modified + registry rebuild)

AlfredTaskPlanner
  ├── init_skill_set()  (existing, unchanged)
  └── init_instance_skill_set(registry, object_metadata)  (new)
```
