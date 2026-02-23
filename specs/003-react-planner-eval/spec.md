# Feature Specification: ReAct-Based Planner with Evaluation

**Feature Branch**: `003-react-planner-eval`
**Created**: 2026-02-21
**Status**: Draft
**Input**: User description: "Create a ReAct-based planner as a modularized class, plug it into the ai2thor-based evaluation process, and evaluate on 5% of the dataset, run the evaluation in non-headless mode, refer to the ReAct paper (Yao et al., ICLR 2023) to develop a nice ReAct agent code and prompts"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run ReAct Planner on Household Tasks (Priority: P1)

A researcher wants to evaluate whether a reasoning-and-acting (ReAct) planning approach can successfully complete household tasks in a simulated environment. They launch an evaluation run and the system uses the ReAct planner to solve tasks by interleaving explicit reasoning steps (thoughts) with physical actions, receiving environment observations after each action. The researcher can visually observe the agent's behavior in the simulator window (non-headless mode) and review the reasoning trace alongside the actions taken.

**Why this priority**: This is the core value of the feature -- without a working ReAct planner that integrates into the evaluation loop, nothing else matters. A researcher needs to see the planner reason and act in a closed loop to validate the approach.

**Independent Test**: Can be fully tested by launching a single evaluation task and verifying the planner produces an interleaved sequence of thoughts and actions, receives observations from the environment, and arrives at a task completion or step limit.

**Acceptance Scenarios**:

1. **Given** a household task (e.g., "put a clean lettuce in diningtable"), **When** the ReAct planner processes the task, **Then** it generates an initial reasoning step that decomposes the task into subgoals (find, clean, place), followed by actions that interact with the environment, with each observation feeding back into the next reasoning step.
2. **Given** a task in the evaluation set, **When** the planner encounters an unexpected observation (e.g., the target object is not where expected), **Then** the planner generates a reasoning step that acknowledges the failed expectation and adjusts its strategy accordingly, rather than repeating the same action.
3. **Given** the evaluation is started, **When** the simulator launches, **Then** the environment renders visually in a window (non-headless) so the researcher can observe the agent navigating and interacting with objects.

---

### User Story 2 - Evaluate on a Dataset Subset (Priority: P2)

A researcher wants to run the ReAct planner on a small, representative subset (5%) of the evaluation dataset to get quick feedback on performance before committing to a full evaluation run. They specify the subset size in the evaluation configuration and receive a summary report at the end.

**Why this priority**: Running on 5% of the dataset provides rapid iteration feedback without requiring hours of compute. This is essential for the development and tuning cycle.

**Independent Test**: Can be tested by running the evaluation command with a 5% subset configuration and verifying that approximately 5% of available tasks are evaluated, with a success-rate summary reported at the end.

**Acceptance Scenarios**:

1. **Given** a dataset with hundreds of tasks and a configuration specifying 5% evaluation, **When** the evaluation runs, **Then** only approximately 5% of the tasks from the chosen split are evaluated, selected via a reproducible random seed.
2. **Given** the evaluation completes on the 5% subset, **When** results are reported, **Then** the output includes the number of tasks attempted, the number of successes, and the overall success rate.

---

### User Story 3 - Modular Planner Integration (Priority: P3)

A researcher wants to swap between different planning strategies (e.g., the existing action-only planner vs. the new ReAct planner) without modifying the evaluation harness. They select the planner through configuration and the evaluation pipeline uses whichever planner is specified.

**Why this priority**: Modularity enables fair A/B comparison between planning approaches and makes the system extensible for future planner variants.

**Independent Test**: Can be tested by running the same set of tasks with two different planner configurations and verifying both produce valid (but potentially different) evaluation results using the same evaluation pipeline.

**Acceptance Scenarios**:

1. **Given** the evaluation system with multiple planner options, **When** a researcher selects the ReAct planner via configuration, **Then** the evaluation uses the ReAct planner without any code changes to the evaluation pipeline.
2. **Given** the ReAct planner is selected, **When** a task completes (success or failure), **Then** the evaluation results include the full reasoning trace (all thoughts, actions, and observations) for post-hoc analysis.

---

### User Story 4 - Interpretable Reasoning Traces (Priority: P3)

A researcher wants to inspect why the planner succeeded or failed on a given task. The ReAct planner produces a human-readable trace of its thought process alongside the actions it took, making it easy to diagnose failures and understand the agent's decision-making.

**Why this priority**: Interpretability is a key advantage of ReAct over action-only approaches. Without readable traces, the researcher cannot debug or publish meaningful analysis.

**Independent Test**: Can be tested by reviewing the output of a single completed task and confirming the trace contains explicit reasoning about subgoal decomposition, object search strategy, progress tracking, and error recovery.

**Acceptance Scenarios**:

1. **Given** a completed evaluation task, **When** the researcher reviews the output, **Then** the trace shows alternating thought and action entries, where each thought explains the rationale for the next action.
2. **Given** a task where the planner fails (e.g., exceeds step limit), **When** the researcher reviews the trace, **Then** they can identify the point of failure from the reasoning steps (e.g., "stuck in a loop searching the wrong locations").

---

### Edge Cases

- What happens when the planner generates a thought that cannot be parsed as a valid action? The system should treat thoughts as internal reasoning only and wait for the next action output.
- What happens when the planner exceeds the maximum number of allowed steps? The task should be marked as failed and the trace should be preserved for analysis.
- What happens when an action fails in the environment (e.g., trying to pick up an object that is not reachable)? The failure observation should be fed back to the planner so it can reason about an alternative approach.
- What happens when the planner generates a "done" signal prematurely before the task goal is actually met? The task should be scored based on actual goal completion, not the planner's self-assessment.
- What happens when the environment returns an ambiguous observation (e.g., multiple objects of the same type)? The planner should reason about which specific instance to interact with.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a ReAct-style planner that generates interleaved reasoning traces (thoughts) and actions in response to task instructions and environment observations.
- **FR-002**: The planner MUST follow the Thought-Action-Observation loop pattern from the ReAct paper: for each step, the planner first produces a reasoning thought, then selects an action; the environment returns an observation that feeds into the next iteration.
- **FR-003**: The planner's reasoning thoughts MUST include at minimum: (a) high-level task decomposition into subgoals, (b) commonsense reasoning about where objects are likely located, (c) progress tracking of completed vs. remaining subgoals, and (d) error recovery when actions fail.
- **FR-004**: The planner MUST be a self-contained, modular component that plugs into the existing evaluation pipeline through the same interface as other planners, selectable via configuration.
- **FR-005**: The system MUST support running evaluation in non-headless mode, rendering the simulated environment visually so the researcher can observe agent behavior in real time.
- **FR-006**: The system MUST support evaluating on a configurable percentage of the dataset (default: 5%) using a reproducible random seed for task selection.
- **FR-007**: The planner MUST use few-shot in-context examples (based on the ReAct paper's ALFWorld prompts) to guide the language model in producing properly formatted thought-action sequences.
- **FR-008**: The system MUST record the complete reasoning trace (all thoughts, actions, and observations) for each evaluated task and include it in the evaluation output.
- **FR-009**: The planner MUST respect a configurable maximum step limit per task, marking the task as failed if the limit is exceeded.
- **FR-010**: When an action fails in the environment, the failure message MUST be returned as an observation to the planner so it can reason about alternatives in the next thought step.
- **FR-011**: The planner MUST handle all six ALFRED task types: Pick & Place, Examine in Light, Clean & Place, Heat & Place, Cool & Place, and Pick Two & Place.

### Key Entities

- **Thought**: An internal reasoning step generated by the planner. Contains natural language reasoning about the current state, plan progress, and next action rationale. Does not affect the environment.
- **Action**: A command issued by the planner to interact with the environment (e.g., navigate to an object, pick up, place, open, close, toggle, slice, or signal task completion).
- **Observation**: Feedback from the environment after an action is executed. Describes the outcome (success or failure) and the current visible state (objects in view, inventory).
- **Reasoning Trace**: The complete ordered sequence of Thought-Action-Observation triples for a single task episode, used for analysis and debugging.
- **Task Episode**: A single attempt to complete one household task, beginning with the task instruction and ending with either successful goal completion, a "done" signal, or reaching the step limit.
- **Evaluation Run**: A batch of task episodes evaluated on a subset of the dataset, producing aggregate metrics (success rate, average steps) and per-task reasoning traces.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The ReAct planner successfully completes at least 1 household task out of the 5% evaluation subset, demonstrating end-to-end functionality of the reasoning-action loop.
- **SC-002**: 100% of evaluated tasks produce a complete reasoning trace containing at least one thought step and one action step, regardless of task success or failure.
- **SC-003**: The planner can be selected via configuration without modifying evaluation pipeline code -- switching between the existing planner and the ReAct planner requires only a configuration change.
- **SC-004**: The evaluation on 5% of the dataset completes within a reasonable time frame (under 2 hours for the subset) when run in non-headless mode.
- **SC-005**: Reasoning traces are interpretable: for at least 80% of task episodes, a human reviewer can identify from the trace what the planner was attempting to do and why it succeeded or failed.
- **SC-006**: The planner demonstrates reasoning adaptability -- when an initial action fails, the planner's subsequent thought reflects the failure and proposes an alternative strategy in at least 50% of failure-recovery situations.

## Assumptions

- The researcher has access to a machine with a display (or virtual display) capable of running the simulator in non-headless mode.
- The existing evaluation pipeline and environment connector already handle the low-level simulator interactions (navigation, object manipulation); the ReAct planner operates at the planning level, issuing high-level instructions.
- An external language model service is available and configured for the planner to use for generating thoughts and actions.
- The ALFRED dataset and task splits are already available in the project's data directory.
- The 5% subset is selected from the `valid_seen` or `valid_unseen` split as configured, using the existing subset selection mechanism.
- Few-shot prompt examples will be based on the ALFWorld ReAct prompts from the paper (Appendix C.4), adapted for the project's action format.
