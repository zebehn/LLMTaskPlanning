# Implementation Plan: ReAct-Based Planner with Evaluation

**Branch**: `003-react-planner-eval` | **Date**: 2026-02-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-react-planner-eval/spec.md`

## Summary

Implement a ReAct-style planner (Yao et al., ICLR 2023) that interleaves Thought-Action-Observation steps, integrate it into the AI2-THOR evaluation pipeline as a modular drop-in planner, and evaluate on 5% of the ALFRED dataset in non-headless mode. The planner uses `chat_completion()` for free-form generation of reasoning traces and actions, with few-shot prompts adapted from the paper's ALFWorld examples to match the project's action vocabulary.

## Technical Context

**Language/Version**: Python 3.10+ (matches existing codebase)
**Primary Dependencies**: ai2thor>=5.0.0, hydra-core==1.3.2, omegaconf==2.3.0, openai (LLM provider)
**Storage**: JSON files for per-task results and reasoning traces (existing pattern)
**Testing**: pytest with mocked AI2-THOR/LLM dependencies (existing pattern)
**Target Platform**: Linux/macOS with X11 display for non-headless AI2-THOR
**Project Type**: Single project (existing structure)
**Performance Goals**: Complete 5% evaluation subset within 2 hours in non-headless mode
**Constraints**: Max 25 steps per task (configurable), LLM context window limits prompt + history
**Scale/Scope**: ~100 tasks at 5% of valid_seen (~2000 tasks), 6 ALFRED task types

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **TDD Cycle**: Tests written first for ReActTaskPlanner (parsing, prompting, step generation) before implementation. Integration tests with mocked env/LLM.
- [x] **Tidy First**: Structural prep (extracting shared evaluator helpers) committed separately from behavioral changes (new planner, new evaluator).
- [x] **Commit Discipline**: Atomic commits: `refactor:` for extracting helpers, `feat:` for new planner class, `feat:` for evaluator, `feat:` for config, `test:` for test files.
- [x] **Code Quality**: ReActTaskPlanner follows single responsibility (planning only). Observation construction is a separate method. No duplication with existing planner -- shared base class methods reused.
- [x] **Refactoring**: Extract common evaluation helpers (scene setup, result saving) from AlfredEvaluator before adding new evaluator subclass.
- [x] **Simplicity**: Minimal changes -- new planner class + evaluator subclass + config file + dispatch entry. Reuses existing LLM provider, environment connector, dataset loading, and result saving.

## Project Structure

### Documentation (this feature)

```text
specs/003-react-planner-eval/
├── plan.md              # This file
├── research.md          # Research decisions (7 decisions)
├── data-model.md        # ReActStep, ReasoningTrace, EvaluationResult
├── quickstart.md        # How to run the evaluation
├── contracts/           # Interface contracts
│   └── react_planner_interface.md
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── evaluate.py                          # MODIFIED: add alfred_react dispatch
├── task_planner.py                      # UNCHANGED: base class
├── alfred/
│   ├── alfred_evaluator.py              # MODIFIED: extract shared helpers
│   ├── alfred_task_planner.py           # UNCHANGED
│   ├── react_task_planner.py            # NEW: ReAct planner class
│   ├── react_evaluator.py              # NEW: ReAct evaluation loop
│   └── thor_connector.py               # MODIFIED: add observation helpers
├── prompts/
│   └── templates/
│       ├── react_system.txt             # NEW: ReAct system prompt
│       └── react_few_shot_examples.txt  # NEW: ReAct few-shot examples
└── llm/                                 # UNCHANGED

conf/
├── config_alfred_react.yaml             # NEW: ReAct evaluation config

tests/
├── test_react_planner.py               # NEW: ReAct planner unit tests
```

**Structure Decision**: Extends the existing single-project structure. New files follow the established pattern of `{domain}_{role}.py` naming (e.g., `react_task_planner.py` alongside `alfred_task_planner.py`). Config follows the `config_{name}.yaml` convention.

## Design Decisions

### D1: ReAct Planner as Subclass of TaskPlanner

The `ReActTaskPlanner` extends `TaskPlanner` but overrides the planning methods to use free-form `chat_completion()` instead of constrained `select_action()`.

**Key differences from AlfredTaskPlanner**:
- Uses `chat_completion()` for Thought+Action generation (not `score()` with skill set)
- Maintains conversation as a list of messages (not flat string concatenation)
- Parses LLM output to extract Think/Act components
- Uses ReAct-specific few-shot prompt with Think/Act/Obs format
- Skill set is used for validation only (not for constrained selection)

### D2: ReAct Evaluator Loop

The `ReActAlfredEvaluator` subclasses `AlfredEvaluator` and overrides `evaluate_task()`:

```
for each step in 1..max_steps:
    1. Build messages: system prompt + few-shot + task + history
    2. Call llm.chat_completion(messages) → get "Think: ... Act: ..."
    3. Parse output → (thought, action)
    4. Record thought in trace
    5. If action == "done": end task, check goal
    6. Execute action via env.llm_skill_interact(action)
    7. Construct observation from action result + env metadata
    8. Record action + observation in trace
    9. Append thought/action/observation to history for next iteration
```

**Critical difference**: Does NOT stop on action failure. Failure becomes an observation.

### D3: Prompt Architecture

**System prompt** (`react_system.txt`): Describes the robot, the environment, available actions, and the Think/Act/Obs format.

**Few-shot examples** (`react_few_shot_examples.txt`): 1-2 examples per task type adapted from paper's Appendix C.4, using this project's action vocabulary:

```
Task: Put a clean lettuce in diningtable.
Think: To solve the task, I need to find a lettuce, pick it up, find a sinkbasin to clean it, then find the diningtable and put it down. Let me start by finding a lettuce.
Act: find a lettuce
Obs: Found lettuce. You are now near the lettuce on countertop.
Think: I found the lettuce on the countertop. Now I need to pick it up.
Act: pick up the lettuce
Obs: You picked up the lettuce.
Think: I have the lettuce. Now I need to clean it at a sinkbasin.
Act: find a sinkbasin
Obs: Found sinkbasin. You are now near the sinkbasin.
...
Act: done
```

### D4: Observation Construction

A new helper method `construct_observation()` on the evaluator builds human-readable observation text:

- **On successful find**: "Found {object}. You are now near the {object}."
- **On successful pick up**: "You picked up the {object}."
- **On successful put down**: "You put the {object} on/in the {receptacle}."
- **On successful open/close**: "You opened/closed the {object}."
- **On successful toggle**: "You turned on/off the {object}."
- **On failure**: "Action failed: {action}. {error_message}"

Optionally appends visible objects from environment metadata for richer context.

### D5: Configuration

New `conf/config_alfred_react.yaml`:
```yaml
name: alfred_react

defaults:
  - hydra: default.yaml
  - planner: default.yaml
  - override hydra/help: custom
  - _self_

out_dir: ${hydra:run.dir}

planner:
  provider: "openai"
  model_name: "gpt-4"
  max_steps: 25
  temperature: 0.0
  max_tokens: 1024  # Higher for ReAct (thoughts + actions)

prompt:
  react_system_prompt: "resource/prompts/react_system.txt"
  react_few_shot_examples: "resource/prompts/react_few_shot_examples.txt"

alfred:
  x_display: '0'
  eval_set: 'valid_seen'
  eval_portion_in_percent: 5
  random_seed_for_eval_subset: 1
```

### D6: Dispatch Integration

Add to `src/evaluate.py`:
```python
elif cfg.name == 'alfred_react':
    from src.alfred.react_evaluator import ReActAlfredEvaluator
    evaluator = ReActAlfredEvaluator(cfg)
```

## Implementation Order

1. **Structural prep** (refactor): Extract shared evaluation helpers from `AlfredEvaluator`
2. **ReAct prompt templates**: Create system prompt and few-shot examples
3. **ReActTaskPlanner class**: Implement with parsing, message building, step generation
4. **Observation construction**: Add helper to build text observations from env state
5. **ReActAlfredEvaluator**: Implement the Thought-Action-Observation loop
6. **Configuration**: New config file + dispatch entry
7. **Tests**: Unit tests for planner parsing, integration tests with mocked env/LLM
8. **Validation**: Run on 5% subset, verify traces and results
