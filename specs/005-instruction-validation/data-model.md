# Data Model: ALFRED Instruction Validation

**Feature**: 005-instruction-validation
**Date**: 2026-02-26

## Entities

### ValidationEntry

Represents the classification result for a single (task, repeat_idx) combination.

| Field | Type | Description |
|---|---|---|
| task_path | string | Full task path from split file (e.g., "pick_and_place_simple-Candle-None-Toilet-429/trial_T20190908_052232_887934") |
| trial_id | string | Trial identifier (e.g., "trial_T20190908_052232_887934") |
| repeat_idx | int | Annotator index (0, 1, or 2) |
| task_type | string | ALFRED task type extracted from directory name |
| category | int | Classification: 0=valid, 1=non_existent, 2=goal_mismatch, 3=ambiguous |
| category_label | string | Human-readable label: "valid", "non_existent", "goal_mismatch", "ambiguous" |
| instruction_text | string | Raw annotator instruction text |
| pddl_targets | PddlTargets | Ground truth object/receptacle targets |
| scene_objects | list[string] | Unique object type names in the scene |
| reason | string | LLM-generated explanation of classification |

### PddlTargets

Ground truth targets from the PDDL specification.

| Field | Type | Description |
|---|---|---|
| object_target | string | Target object to manipulate (e.g., "Candle", "PotatoSliced") |
| parent_target | string | Target receptacle for placement (e.g., "Toilet", "SinkBasin") |
| mrecep_target | string | Movable receptacle if applicable (e.g., "Bowl", "Plate"), empty string if N/A |
| object_sliced | bool | Whether the object needs to be sliced |

### ValidationReport

Top-level report structure.

| Field | Type | Description |
|---|---|---|
| split | string | ALFRED split name (e.g., "valid_seen") |
| model | string | LLM model used for classification (e.g., "gpt-5-mini") |
| generated_at | string | ISO 8601 timestamp |
| total_entries | int | Total number of validated entries |
| summary | CategorySummary | Aggregate counts per category |
| by_task_type | dict[string, CategorySummary] | Per-task-type breakdown |
| entries | list[ValidationEntry] | All individual results |

### CategorySummary

Aggregate statistics for a group of entries.

| Field | Type | Description |
|---|---|---|
| total | int | Total entries in group |
| category_0 | int | Count of category 0 (valid) |
| category_1 | int | Count of category 1 (non_existent) |
| category_2 | int | Count of category 2 (goal_mismatch) |
| category_3 | int | Count of category 3 (ambiguous) |

## Relationships

```
ValidationReport
  └── has many → ValidationEntry
                    └── has one → PddlTargets
```

## Classification Flow

The LLM receives a structured prompt per instruction and returns a JSON response:

```
Input to LLM:
  - instruction_text (from annotator)
  - scene_objects (from object_poses)
  - pddl_targets (from pddl_params or directory name)

LLM classifies → {"category": N, "reason": "explanation"}

Priority guidance in prompt: 1 > 2 > 3 > 0
  - If objects don't exist in scene → 1 (non_existent)
  - If objects exist but wrong target → 2 (goal_mismatch)
  - If vague/colloquial terms → 3 (ambiguous)
  - If all match → 0 (valid)
```

## Input Data Sources

| Source | Path | Used for |
|---|---|---|
| Split file | `alfred/data/splits/oct21.json` | Task list enumeration |
| Preprocessed annotations | `alfred/data/json_2.1.0/{task_path}/pp/ann_{repeat_idx}.json` | Instruction text, pddl_params, scene object_poses |
| LLM provider | `src/llm/factory.py` → `LLMProviderFactory.create()` | Classification calls |
