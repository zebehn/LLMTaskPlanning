# Contract: Action Observation Format

**Feature**: `006-instance-object-tracking`

---

## Overview

The observation string returned by `ThorConnector.llm_skill_interact()` is the text shown to the LLM after each action. This contract defines the expected format for pick and put success observations.

---

## pick — success observation

**Format**: `"Picked up <InstanceLabel>."`

**Examples**:
- `"Picked up Egg_1."`
- `"Picked up Cup_2."`
- `"Picked up TomatoSliced_1."`

**Rules**:
- Instance label format: `<ObjectType>_<N>` where N ≥ 1
- Emitted only when `lastActionSuccess` is True
- Failure observations are unchanged (e.g., `"Cannot find egg to pick up"`, `"Robot is currently holding Mug"`)

---

## put — success observation

**Format**: `"Put <ObjectInstanceLabel> in <ReceptacleInstanceLabel>."`

**Examples**:
- `"Put Egg_1 in Microwave_1."`
- `"Put Cup_2 in CounterTop_3."`
- `"Put Knife_1 in Drawer_2."`

**Rules**:
- Object label: readable_id of the held object at time of put
- Receptacle label: readable_id of the receptacle that accepted the object
- Emitted only when `lastActionSuccess` is True
- Failure observations are unchanged (e.g., `"Putting the object on microwave failed"`, `"Robot is not holding any object"`)

---

## find — success observation (unchanged)

**Format**: `"Found <type>. You are now near the <type> on the <location>."` (existing, no change)

When navigating to an instance-specific target, the format becomes:
`"Found <InstanceLabel>. You are now near <InstanceLabel> in the <receptacle>."`

---

## Instance label contract

- Labels are assigned at scene reset by `_build_object_registry()`
- Labels are stable for the entire episode duration
- Format: `<PascalCaseObjectType>_<N>` where N is a 1-based counter per type, assigned in sorted objectId order
- Labels accepted as input to `find`, `pick up`, `put down` actions (existing routing)
