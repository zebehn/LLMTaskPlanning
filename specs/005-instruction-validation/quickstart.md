# Quickstart: ALFRED Instruction Validation

**Feature**: 005-instruction-validation

## Prerequisites

- Conda environment `llmtaskplanning` activated
- ALFRED dataset preprocessed (pp/ann_N.json files exist in `alfred/data/json_2.1.0/`)
- OpenAI API key configured (`OPENAI_API_KEY` environment variable or `.env` file)

## Usage

### 1. Validate instructions

```bash
# Validate all instructions in valid_seen (uses gpt-5-mini by default)
PYTHONPATH="alfred:src:$PYTHONPATH" python src/alfred/instruction_validator.py --split valid_seen

# Validate only the 5% subset matching evaluator config
PYTHONPATH="alfred:src:$PYTHONPATH" python src/alfred/instruction_validator.py \
  --split valid_seen --portion 5 --seed 1

# Use a different model or provider
PYTHONPATH="alfred:src:$PYTHONPATH" python src/alfred/instruction_validator.py \
  --split valid_seen --model gpt-4 --reasoning-effort low
```

Output: `outputs/alfred_react/instruction_validation_valid_seen.json`

### 2. Run evaluation with filtering

```bash
# Run evaluation, skipping non-existent instructions (category 1)
PYTHONPATH="alfred:src:$PYTHONPATH" python src/evaluate.py \
  --config-name=config_alfred_react \
  "alfred.x_display=\"1\"" \
  alfred.validation_report=outputs/alfred_react/instruction_validation_valid_seen.json \
  "alfred.skip_categories=[1]"

# Skip both non-existent and mismatched instructions
PYTHONPATH="alfred:src:$PYTHONPATH" python src/evaluate.py \
  --config-name=config_alfred_react \
  "alfred.x_display=\"1\"" \
  alfred.validation_report=outputs/alfred_react/instruction_validation_valid_seen.json \
  "alfred.skip_categories=[1,2]"
```

### 3. Run tests

```bash
pytest tests/test_instruction_validator.py -v
```

## File Layout

```
src/alfred/
  instruction_validator.py    # Main validation script (CLI + library)

tests/
  test_instruction_validator.py  # Unit tests (mocked LLM calls)
  fixtures/validation/            # Test fixture annotations

specs/005-instruction-validation/
  spec.md                     # Feature specification
  plan.md                     # Implementation plan
  research.md                 # Research findings
  data-model.md               # Data model
  contracts/
    validation-report.md      # JSON schema + CLI + prompt contract
  quickstart.md               # This file
```
