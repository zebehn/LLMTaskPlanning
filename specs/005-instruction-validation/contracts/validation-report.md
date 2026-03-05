# Contract: Validation Report JSON Schema

**Feature**: 005-instruction-validation
**Date**: 2026-02-26

## Output File

**Path**: `outputs/alfred_react/instruction_validation_{split}.json`
**Format**: JSON

## Schema

```json
{
  "split": "valid_seen",
  "model": "gpt-5-mini",
  "generated_at": "2026-02-26T15:30:00Z",
  "total_entries": 820,
  "summary": {
    "total": 820,
    "category_0": 700,
    "category_1": 30,
    "category_2": 50,
    "category_3": 40
  },
  "by_task_type": {
    "pick_and_place_simple": {
      "total": 200,
      "category_0": 180,
      "category_1": 5,
      "category_2": 10,
      "category_3": 5
    }
  },
  "entries": [
    {
      "task_path": "pick_and_place_simple-Candle-None-Toilet-429/trial_T20190908_052232_887934",
      "trial_id": "trial_T20190908_052232_887934",
      "repeat_idx": 0,
      "task_type": "pick_and_place_simple",
      "category": 1,
      "category_label": "non_existent",
      "instruction_text": "Put a bottle on the back of a newspaper.",
      "pddl_targets": {
        "object_target": "Candle",
        "parent_target": "Toilet",
        "mrecep_target": "",
        "object_sliced": false
      },
      "scene_objects": ["Candle", "Cloth", "HandTowel", "Plunger", "ScrubBrush", "SoapBar", "SoapBottle", "SprayBottle", "TissueBox", "ToiletPaper", "Towel"],
      "reason": "Instruction mentions 'bottle' and 'newspaper' — neither exists in the scene. Scene contains SprayBottle and SoapBottle but no generic Bottle, and no Newspaper at all."
    }
  ]
}
```

## CLI Interface

```
PYTHONPATH="alfred:src:$PYTHONPATH" python src/alfred/instruction_validator.py \
  --split valid_seen \
  [--model gpt-5-mini] \
  [--provider openai] \
  [--reasoning-effort low] \
  [--output path/to/output.json] \
  [--portion 5] \
  [--seed 1] \
  [--stratified]
```

| Argument | Required | Default | Description |
|---|---|---|---|
| `--split` | yes | — | ALFRED split to validate (valid_seen, valid_unseen, train) |
| `--model` | no | `gpt-5-mini` | LLM model for classification |
| `--provider` | no | `openai` | LLM provider (openai, vllm, ollama, lmstudio) |
| `--reasoning-effort` | no | `low` | Reasoning effort for reasoning models |
| `--output` | no | `outputs/alfred_react/instruction_validation_{split}.json` | Output report path |
| `--portion` | no | 100 | Percentage of tasks to validate (matches evaluator's sampling) |
| `--seed` | no | 1 | Random seed for subset sampling |
| `--stratified` | no | false | Enable stratified sampling by task type |

## LLM Classification Prompt

### System message
```
You are classifying ALFRED household task instructions for annotation quality.
You will be given a natural language instruction, the list of objects available in the scene, and the ground truth task targets.
Classify the instruction into exactly one category and explain your reasoning.

Categories (in priority order):
1 (non_existent): The instruction mentions objects or receptacles that do not exist in the scene at all.
2 (goal_mismatch): The mentioned objects exist in the scene but do not match the ground truth targets.
3 (ambiguous): The instruction uses vague or colloquial terms that could plausibly refer to the correct targets but are not clear or exact.
0 (valid): The instruction correctly describes the task — mentioned objects match the ground truth targets and exist in the scene. Common synonyms like "fridge" for "Fridge" or "counter" for "CounterTop" are acceptable as valid.

Important: "Sliced" suffixes in targets (e.g., "PotatoSliced") mean the annotator should reference the base object ("potato"). This is valid, not a mismatch.

Respond ONLY with a JSON object: {"category": N, "reason": "brief explanation"}
```

### User message template
```
Instruction: "{instruction_text}"
Scene objects: {scene_objects}
Ground truth targets: object={object_target}, receptacle={parent_target}{mrecep_info}
```

## Evaluator Integration

### Config Addition (config_alfred_react.yaml)

```yaml
alfred:
  validation_report: ""  # Path to instruction_validation JSON; empty = no filtering
  skip_categories: [1]   # Categories to skip during evaluation; default: skip non_existent only
```

### Evaluator Behavior

When `validation_report` is set:
1. Load report JSON at startup
2. Build lookup: `{(task_path, repeat_idx): entry}`
3. Before each task evaluation:
   - Look up `(task['task'], task['repeat_idx'])`
   - If found and `entry.category` in `skip_categories`: skip with log message
   - If not found in report: evaluate normally (conservative default)
4. Skipped tasks recorded in results as:
   ```json
   {
     "trial": "trial_T20190908_052232_887934",
     "skipped": true,
     "skip_reason": "non_existent",
     "skip_category": 1
   }
   ```
