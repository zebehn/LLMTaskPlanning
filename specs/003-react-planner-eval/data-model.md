# Data Model: 003-react-planner-eval

**Date**: 2026-02-21

## Entities

### ReActStep

Represents a single step in the ReAct loop (a thought-action-observation triple or a partial triple).

| Field | Type | Description |
|-------|------|-------------|
| step_number | int | Sequential step index (1-based) |
| thought | str or None | Reasoning text generated before the action |
| action | str or None | Action command (e.g., "find a lettuce", "done") |
| observation | str or None | Environment feedback after action execution |
| action_success | bool or None | Whether the action succeeded in the environment |
| raw_action_result | dict or None | Full return from `llm_skill_interact()` |

### ReasoningTrace

The complete ordered sequence of ReActSteps for a single task episode.

| Field | Type | Description |
|-------|------|-------------|
| task_id | str | ALFRED trial identifier |
| task_type | str | One of 6 ALFRED task types |
| task_instruction | str | Natural language task description |
| scene_name | str | AI2-THOR scene identifier |
| steps | list[ReActStep] | Ordered sequence of ReAct steps |
| total_steps | int | Number of steps taken |
| success | bool | Whether the task goal was achieved |
| termination_reason | str | "goal_met", "done_signal", "max_steps", "error" |

### EvaluationResult

Aggregate results for an evaluation run.

| Field | Type | Description |
|-------|------|-------------|
| timestamp | str | ISO timestamp of evaluation run |
| config | dict | Evaluation configuration snapshot |
| model_name | str | LLM model used |
| total_evaluated | int | Number of tasks attempted |
| total_success | int | Number of tasks completed successfully |
| success_rate | float | Ratio of successes to total |
| avg_steps | float | Average steps per task |
| traces | list[ReasoningTrace] | Per-task reasoning traces |
| by_task_type | dict | Success rates grouped by task type |

## Relationships

- An **EvaluationResult** contains many **ReasoningTraces** (one per task).
- A **ReasoningTrace** contains many **ReActSteps** (one per loop iteration).
- Each **ReActStep** may have a thought, action, and observation (the final step may be incomplete if terminated by max steps).

## State Transitions

### ReAct Loop State Machine

```
START → THINK → ACT → OBSERVE → THINK → ...
                  ↓
              (action = "done")
                  ↓
                 END
```

**Transitions**:
- `START → THINK`: Planner receives task instruction, generates initial reasoning
- `THINK → ACT`: Planner generates action based on reasoning
- `ACT → OBSERVE`: Environment executes action, returns observation
- `OBSERVE → THINK`: Planner reasons about observation, plans next step
- `ACT → END`: Action is "done" signal, task episode ends
- `OBSERVE → END`: Max steps reached, task episode ends
