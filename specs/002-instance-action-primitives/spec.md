# Feature Specification: Instance-Specific Action Primitives

**Feature Branch**: `002-instance-action-primitives`
**Created**: 2026-02-08
**Status**: Draft
**Input**: User description: "Provide additional action primitives for AI2Thor environment to act upon specific object instances e.g. 'find Apple_01' to find a specific apple with instance id 'Apple_01'. Object instance repository is already implemented and use the IDs registered in the repository. Allow skill set directives like 'pick up Apple_1' which would be interpreted as an action to be performed on a specific object instance."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Navigate to a Specific Object Instance (Priority: P1)

A planning agent issues a directive like "find Apple_01" to navigate the robot to a particular apple instance in the scene, rather than any arbitrary apple. The system resolves "Apple_01" against the object instance repository, looks up the corresponding simulator object, and navigates the agent to that exact instance.

**Why this priority**: This is the foundational capability. Without the ability to locate a specific instance by its registry ID, no other instance-targeted actions (pick, open, toggle, etc.) can be performed. Navigation is the first step in any interaction chain.

**Independent Test**: Can be fully tested by issuing a "find Apple_01" directive in a scene containing multiple apples and verifying the agent navigates to the correct one (not just any apple).

**Acceptance Scenarios**:

1. **Given** a scene with two apples registered as Apple_01 and Apple_02, **When** the agent receives "find Apple_01", **Then** the agent navigates to the specific apple mapped to Apple_01 in the registry and that object is visible in the agent's view.
2. **Given** a scene with one mug registered as Mug_01, **When** the agent receives "find Mug_01", **Then** the agent navigates to that mug successfully.
3. **Given** a scene with no object registered as "Plate_05", **When** the agent receives "find Plate_05", **Then** the system returns a clear error indicating the instance ID is not found in the registry.

---

### User Story 2 - Manipulate a Specific Object Instance (Priority: P1)

A planning agent issues manipulation directives targeting specific instances, such as "pick up Apple_01", "put down Apple_01", "open Fridge_01", "close Fridge_01", "slice Bread_01". The system resolves the instance ID from the registry and performs the action on that exact object rather than searching for the nearest matching type.

**Why this priority**: Manipulation is core to task execution. In scenes with multiple objects of the same type, acting on the wrong instance leads to task failure. This is equally critical as navigation and co-dependent with it.

**Independent Test**: Can be tested by issuing "pick up Mug_01" in a scene with two mugs and verifying only Mug_01 is picked up.

**Acceptance Scenarios**:

1. **Given** a scene with Mug_01 on CounterTop and Mug_02 on DiningTable, and the agent is near Mug_01, **When** the agent receives "pick up Mug_01", **Then** the agent picks up Mug_01 specifically (not Mug_02).
2. **Given** the agent is holding Apple_01 and is near Fridge_01, **When** the agent receives "put down Apple_01", **Then** Apple_01 is placed in/on the current target receptacle.
3. **Given** a scene with Fridge_01 that is closed, **When** the agent receives "open Fridge_01", **Then** Fridge_01 is opened.
4. **Given** a scene with two lamps Lamp_01 and Lamp_02, **When** the agent receives "turn on Lamp_01", **Then** only Lamp_01 is toggled on.
5. **Given** a scene with Bread_01 on a counter, **When** the agent receives "slice Bread_01", **Then** Bread_01 is sliced.

---

### User Story 3 - Instance-Aware Skill Set Generation (Priority: P2)

The task planning system generates candidate action lists (skill sets) that include instance-specific directives alongside or instead of generic type-based directives. For example, the LLM planner sees candidates like "find Apple_01", "find Apple_02", "pick up Mug_01" rather than just "find a apple", "pick up the mug".

**Why this priority**: Without instance-aware skill sets, the LLM planner cannot select instance-specific actions. This bridges the gap between the new primitives and the planning system but is secondary to the primitives themselves working correctly.

**Independent Test**: Can be tested by initializing a scene and verifying the generated skill set contains instance-specific entries using registry IDs.

**Acceptance Scenarios**:

1. **Given** a scene with Apple_01, Apple_02, and Mug_01 in the registry, **When** the skill set is generated for action selection, **Then** the candidate list includes "find Apple_01", "find Apple_02", and "find Mug_01".
2. **Given** a scene where Apple_01 is pickupable and Fridge_01 is openable, **When** the skill set is generated, **Then** it includes "pick up Apple_01" and "open Fridge_01" as candidates.
3. **Given** the agent just picked up Apple_01, **When** the skill set is updated, **Then** it includes "put down Apple_01" options targeting available receptacles.

---

### User Story 4 - Backward Compatibility with Generic Actions (Priority: P2)

Existing generic directives like "find a mug" and "pick up the apple" continue to work as before. The system supports both generic type-based and instance-specific action formats simultaneously. A planner can mix and match both styles in a single task plan.

**Why this priority**: Existing plans and evaluation pipelines must not break. Backward compatibility ensures the new feature is additive, not disruptive.

**Independent Test**: Can be tested by running existing ground-truth evaluation plans and verifying they produce the same results as before the change.

**Acceptance Scenarios**:

1. **Given** the new instance-specific system is active, **When** the agent receives "find a mug" (generic format), **Then** the system behaves exactly as before, finding the nearest/best matching mug.
2. **Given** a mixed plan with steps ["find Apple_01", "pick up the apple", "find Fridge_01", "open the fridge"], **When** executing the plan, **Then** instance-specific steps resolve by registry ID and generic steps resolve by type matching as before.

---

### Edge Cases

- What happens when an instance ID in a directive refers to an object that has been removed from the scene (e.g., consumed or destroyed)?
- How does the system handle an instance ID that exists in the registry but the object is unreachable (inside a closed container)?
- What happens when the agent issues "pick up Apple_01" but Apple_01 is not visible from the current position?
- How does the system handle malformed instance IDs (e.g., "Apple_", "01_Apple", "Apple")?
- What happens if the object registry has not been built yet when an instance-specific directive is issued?
- How does the system handle sliced objects that generate new instances (e.g., slicing Bread_01 creates BreadSliced_01, BreadSliced_02)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept action directives containing instance IDs in the format `<action> <ObjectType_NN>` (e.g., "find Apple_01", "pick up Mug_02") where the ID matches an entry in the object instance registry.
- **FR-002**: System MUST resolve instance IDs against the existing object instance repository to obtain the corresponding simulator object identifier before executing any action.
- **FR-003**: System MUST support instance-specific variants for all existing action types: find, pick up, put down, open, close, turn on, turn off, slice, and drop.
- **FR-004**: System MUST return a clear, descriptive error when a directive references an instance ID that does not exist in the registry.
- **FR-005**: System MUST continue to support existing generic directives (e.g., "find a mug", "pick up the apple") without any change in behavior.
- **FR-006**: System MUST distinguish between generic directives and instance-specific directives based on the presence of an instance ID pattern (ObjectType followed by underscore and numeric suffix).
- **FR-007**: System MUST support generating instance-aware skill sets that list available instance-specific actions derived from the current object registry state.
- **FR-008**: System MUST update instance-aware skill sets after each action to reflect changes in scene state (e.g., after picking up an object, add put-down options; after slicing, add new sliced-instance options).
- **FR-009**: System MUST handle the case where a referenced instance is inside a closed container by attempting to navigate to it with appropriate feedback if interaction fails.
- **FR-010**: System MUST handle sliced objects by updating the registry with newly created instances (e.g., BreadSliced_01, BreadSliced_02) so they can be targeted by subsequent directives.

### Key Entities

- **Object Instance**: A specific object in the scene identified by a human-readable registry ID (e.g., "Apple_01"). Has attributes: registry ID, simulator object ID, object type, and current state (position, visibility, receptacle, pickupable, toggleable).
- **Instance Registry**: A mapping from human-readable IDs to simulator object identifiers. Built from scene metadata on scene load. Updated when scene state changes (e.g., slicing creates new objects).
- **Instance-Specific Directive**: A natural language action command that targets a particular object instance by its registry ID rather than by object type. Format: `<verb phrase> <RegistryID>`.
- **Skill Set**: A list of candidate actions available to the planning agent at a given step. Now includes both generic type-based and instance-specific entries.

## Assumptions

- The object instance repository (registry) is already implemented in `ThorConnector._obj_registry` and reliably maps human-readable IDs (e.g., "Mug_1") to AI2-THOR object IDs.
- Instance IDs follow the existing convention: `<ObjectType>_<N>` where N is a 1-based integer (e.g., Apple_01, Mug_1). Both zero-padded and non-padded formats are accepted.
- The registry is built at scene initialization and the feature will extend it to update on state-changing actions (slicing).
- The existing action result format (`{'action': ..., 'success': ..., 'message': ...}`) is preserved for all instance-specific actions.
- The "put down" action with an instance ID refers to putting down the specified object the agent is currently holding; the target receptacle is determined by the existing `cur_receptacle` tracking mechanism.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All existing action types (find, pick up, put down, open, close, turn on, turn off, slice) can be executed targeting a specific instance by its registry ID, with 100% of valid directives correctly resolving to the intended object.
- **SC-002**: In scenes with multiple objects of the same type, instance-specific directives target the correct instance 100% of the time (zero ambiguity).
- **SC-003**: All existing generic directives ("find a mug", "pick up the apple") produce identical behavior to the pre-change baseline, ensuring zero regression in existing functionality.
- **SC-004**: Instance-aware skill sets are generated correctly, listing instance-specific candidates for all interactable objects in the current scene state.
- **SC-005**: Invalid instance IDs (non-existent, malformed) produce clear error messages in 100% of cases, with no unhandled exceptions.
- **SC-006**: Task plans using instance-specific directives achieve at least the same task completion rate as equivalent plans using generic directives, in scenes with single instances of each object type.
