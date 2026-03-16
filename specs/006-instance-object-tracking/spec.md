# Feature Specification: Instance-Aware Object Tracking in ReAct Loop

**Feature Branch**: `006-instance-object-tracking`
**Created**: 2026-03-10
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Instance ID Exposed in Action Observations (Priority: P1)

A researcher running a ReAct evaluation on a transformation task (pick, heat/cool/clean, place) needs the agent to know *which specific object instance* it just interacted with, so it can refer back to that same instance later in the episode. Today, observations say "Picked up Cup" — after this change they will say "Picked up Cup_2", giving the agent the token it needs to issue a targeted return action.

**Why this priority**: Without instance IDs in observations, no amount of prompt engineering can teach the model to track a specific object. This is the prerequisite for User Story 2.

**Independent Test**: Run a transformation task episode in a headless environment (no real simulator required). Confirm that the observation string returned after a successful pick action contains the object's instance label (e.g. "Cup_2"), and that the observation after a successful put contains the receptacle's instance label.

**Acceptance Scenarios**:

1. **Given** an agent picks up the second cup in the scene, **When** the pick action succeeds, **Then** the observation includes the instance label (e.g. "Picked up Cup_2").
2. **Given** an agent puts an object down, **When** the put action succeeds, **Then** the observation includes the instance labels of both the object and the destination receptacle (e.g. "Put Cup_2 in CounterTop_3").
3. **Given** an action fails, **When** the failure observation is returned, **Then** no spurious instance label is appended — failure messages are unchanged.
4. **Given** there is only one object of the target type in the scene, **When** the pick succeeds, **Then** the observation still includes the instance label (e.g. "Picked up Mug_1").

---

### User Story 2 - Instance-Specific Find in Few-Shot Prompt (Priority: P2)

A researcher wants the ReAct agent to navigate back to the *same object instance* it interacted with earlier in an episode, rather than being redirected to the nearest object of that type. The few-shot examples in the prompt must demonstrate the pattern: after interacting with Cup_2, the model should issue `find Cup_2` rather than `find a Cup`.

**Why this priority**: Depends on User Story 1 — the model must first see instance IDs in observations before it can learn to reuse them. Once IDs are visible, updating the prompt examples is sufficient to teach the behaviour without any model retraining.

**Independent Test**: Inspect the updated few-shot prompt for at least one transformation task example that shows the instance-specific find pattern. Verify that when the model's context contains "Picked up Cup_2", the model generates `find Cup_2` for the return-navigation step.

**Acceptance Scenarios**:

1. **Given** the updated few-shot prompt, **When** the prompt is inspected, **Then** at least one heat/cool/clean example demonstrates `find <Type>_<N>` for the return navigation after transformation.
2. **Given** a model that has seen "Picked up Cup_2" in its context, **When** it needs to return to that cup after closing the microwave, **Then** the model generates `find Cup_2` rather than `find a Cup`.
3. **Given** the model issues `find Cup_2`, **When** the navigation system processes it, **Then** the agent is teleported to the specific Cup_2 instance, not the nearest Cup.
4. **Given** the model issues `find Cup_2` but Cup_2 is unreachable, **When** navigation is attempted, **Then** a clear failure observation is returned and nearest-type fallback does NOT occur silently.

---

### Edge Cases

- What if two objects of the same type have both been interacted with? The model should use the most recently mentioned instance label.
- What if an object is dropped and picked up again — does the instance label remain consistent across the episode?
- What if the scene contains only one object of the target type — the system still produces a labelled observation (no skipping).
- What if the model generates `find Cup_2` but Cup_2 no longer exists or has moved inside a closed container — does navigation fail gracefully?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The observation returned after a successful pick action MUST include the instance label of the picked object (e.g. "Picked up Cup_2").
- **FR-002**: The observation returned after a successful put action MUST include the instance labels of both the placed object and the destination receptacle (e.g. "Put Cup_2 in CounterTop_3").
- **FR-003**: Instance labels MUST use a consistent, human-readable format: `<ObjectType>_<N>` where N is a 1-based index assigned at the start of each episode and stable for the episode's duration.
- **FR-004**: Failure observations MUST NOT be altered — failure messages remain exactly as produced today.
- **FR-005**: The few-shot prompt for transformation tasks (heat, cool, clean) MUST include at least one example demonstrating instance-specific return navigation (`find <Type>_<N>`) after the transformation step.
- **FR-006**: When the agent issues `find <Type>_<N>`, the navigation system MUST teleport to that specific instance, not the nearest object of the same type.
- **FR-007**: If `find <Type>_<N>` is issued for an instance that cannot be reached, the system MUST return a clear failure observation and MUST NOT silently fall back to nearest-type navigation.

### Key Entities

- **Instance Label**: A short, stable identifier (`<ObjectType>_<N>`) assigned to each interactable object at episode start; exposed in observations and accepted as navigation target.
- **Object Registry**: The per-episode mapping from instance label to simulator object ID; extended to support reverse lookup (simulator ID → instance label) for embedding labels in observations.
- **Few-Shot Example**: A complete heat/cool/clean episode trace (think → act → observe) included in the LLM prompt; updated to demonstrate instance-specific navigation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After the change, 100% of successful pick and put action observations include an instance label.
- **SC-002**: The pick_heat/cool/clean combined success rate on valid_seen (30% sample, Qwen3.5-9B) improves by at least 5 percentage points over the pre-change baseline (heat: 38.2%, cool: 51.3%, clean: 37.5%).
- **SC-003**: Zero regressions on pick_and_place_simple and look_at_obj_in_light task types — success rates do not drop more than 2 percentage points.
- **SC-004**: Instance-specific `find <Type>_<N>` actions account for at least 30% of all find actions in generated transformation task traces, confirming the model adopts the new pattern.

## Assumptions

- The existing object registry in ThorConnector already maps simulator object IDs to human-readable names; instance label generation (Cup_1, Cup_2, …) will extend this existing structure with reverse lookup.
- The few-shot examples are stored in editable template files; no model retraining is required — prompt changes alone are sufficient to teach the new pattern.
- The local Qwen3.5-9B model is capable of adopting instance-specific find from few-shot examples without fine-tuning.
- Other action types (open, close, toggleon, toggleoff, slice) are out of scope for observation labelling in this feature; only pick and put observations are changed.
