# Quickstart: 003-react-planner-eval

**Date**: 2026-02-21

## Prerequisites

- Python 3.10+
- ai2thor >= 5.0.0 installed
- OpenAI API key set in environment (`OPENAI_API_KEY`)
- ALFRED dataset with splits available at `alfred/data/splits/oct21.json`
- Display environment for non-headless mode (physical display or virtual framebuffer)

## Running the ReAct Evaluation

```bash
cd src
python evaluate.py --config-name=config_alfred_react
```

### Configuration Overrides

```bash
# Change model
python evaluate.py --config-name=config_alfred_react planner.model_name=gpt-4

# Change evaluation subset percentage
python evaluate.py --config-name=config_alfred_react alfred.eval_portion_in_percent=10

# Change evaluation split
python evaluate.py --config-name=config_alfred_react alfred.eval_set=valid_unseen

# Change max steps per task
python evaluate.py --config-name=config_alfred_react planner.max_steps=30
```

## Running Tests

```bash
# From repository root
cd src
pytest ../tests/test_react_planner.py -v
```

## Output

Results are saved to `outputs/alfred_react/{timestamp}/`:
- `{trial_id}_{repeat_idx}.json` - Per-task result with full reasoning trace
- `{trial_id}_{repeat_idx}_{success|fail}.png` - Visualization screenshot
- `prompt.txt` - The ReAct prompt used

## Comparing with Existing Planner

```bash
# Run existing planner
python evaluate.py --config-name=config_alfred

# Run ReAct planner
python evaluate.py --config-name=config_alfred_react

# Both use the same eval set (valid_seen, 5%) for comparison
```
