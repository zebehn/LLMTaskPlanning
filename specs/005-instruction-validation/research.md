# Research: ALFRED Instruction Validation

**Feature**: 005-instruction-validation
**Date**: 2026-02-26

## R1: Classification Strategy

**Decision**: Use a lightweight LLM (gpt-5-mini with reasoning_effort=low) to classify each instruction given the scene object list, PDDL targets, and instruction text.

**Rationale**: ALFRED annotators use highly variable language — "black fabric" for Cloth, "bottle of nail polish" for Candle, "garbage" / "recycling bin" / "trash" for GarbageCan, "table" for DiningTable/SideTable/CoffeeTable/Desk. A curated synonym dictionary would require ongoing maintenance and still miss novel phrasings. An LLM handles semantic equivalence naturally, including:
- Colloquial terms ("fridge" → Fridge, "couch" → Sofa)
- Ambiguous references ("bottle" when scene has SprayBottle, SoapBottle, WineBottle)
- Completely wrong annotations ("bottle of nail polish" for Candle)
- Partial descriptions ("black fabric" for Cloth)

**Cost estimate**: 820 entries × ~300 tokens/call ≈ 250K tokens total. With gpt-5-mini at reasoning_effort=low, this is ~$0.10-0.50 and completes in a few minutes.

**Alternatives considered**:
- **Curated synonym dictionary + tokenization**: Simpler, fully offline, but brittle. Would require 50+ manually curated mappings and still miss edge cases like "bottle of nail polish". Rejected as primary approach but the colloquial mapping research remains useful as context for the LLM prompt.
- **spaCy noun-chunk extraction**: Adds a heavy dependency for a bounded vocabulary problem. Rejected.
- **Regex-only**: Too brittle for multi-word terms and semantic matching. Rejected.

## R2: LLM Prompt Design

**Decision**: Single-shot structured prompt that provides the instruction, scene objects, and PDDL targets, asking for a JSON response with category (0-3) and reason.

**Rationale**: The classification task is well-scoped — all context fits in a short prompt. gpt-5-mini with reasoning_effort=low can handle this with a single call per instruction. JSON output parsing reuses the pattern from `react_task_planner.py` (regex-based JSON extraction as fallback).

**Prompt structure**:
```
System: You classify ALFRED task instructions for annotation quality.
User:
  Instruction: "{instruction}"
  Scene objects: [list]
  Ground truth: object={object_target}, receptacle={parent_target}, movable_recep={mrecep_target}

  Categories:
  0 (valid): instruction matches ground truth and objects exist in scene
  1 (non_existent): instruction mentions objects not in the scene
  2 (goal_mismatch): mentioned objects exist but don't match ground truth
  3 (ambiguous): vague/colloquial terms that could plausibly refer to targets

  Respond as: {"category": N, "reason": "explanation"}
```

## R3: Existing Codebase Utilities

**Decision**: Reuse `LLMProviderFactory.create()` from `src/llm/factory.py` for LLM access. Reuse `load_task_json()` from `src/alfred/utils.py` for data loading. Reference `OBJECTS` and `RECEPTACLES` from `alfred/gen/constants.py` for the canonical object list.

**Key files**:
- `src/llm/factory.py`: `LLMProviderFactory.create("openai", model_name=..., reasoning_effort=...)`
- `src/alfred/utils.py`: `load_task_json()`
- `alfred/gen/constants.py`: `OBJECTS`, `RECEPTACLES`

## R4: Sliced Object Handling

**Decision**: When presenting PDDL targets to the LLM, include both the raw target (e.g., "PotatoSliced") and the base form ("Potato") so the LLM understands that "potato" in the instruction validly refers to the sliced variant.

**Rationale**: Annotators describe the unsliced form ("potato") since slicing is a procedural step. The 5 sliceable objects: Apple, Bread, Lettuce, Potato, Tomato.

## R5: Classification Priority

**Decision**: Instruct the LLM to follow priority: category 1 > category 2 > category 3 > category 0. If the instruction references an object that doesn't exist in the scene at all, classify as 1 even if it also mismatches the ground truth.

**Rationale**: Non-existence is the most severe (task is physically impossible). Mismatch means the task could be attempted but would be graded wrong. Ambiguity means the agent might succeed depending on interpretation.

## R6: Evaluator Integration Pattern

**Decision**: Add an optional `validation_report` config path to Hydra config. The evaluator loads the JSON report at startup and builds a lookup dict keyed by `(task_path, repeat_idx)`. Before evaluating each task, check the lookup; if category is in the configured skip set, log and skip.

**Rationale**: Minimally invasive — a single `if` check in the evaluation loop. The existing task iteration pattern in `react_evaluator.py` (lines 206-231) easily accommodates this.

## R7: Test Framework

**Decision**: Use pytest with the existing mock pattern. For the LLM-dependent classification, mock the `chat_completion()` call in unit tests and provide canned responses. Integration tests against the real LLM are optional and marked as slow.

**Rationale**: Existing tests in `tests/test_react_planner.py` mock the LLM provider. The validation script's data loading and report generation can be tested fully offline; only the classification call needs mocking.

## R8: Rate Limiting & Batching

**Decision**: Process entries sequentially with a configurable delay between calls (default 0). gpt-5-mini handles high throughput. Add a `--concurrency` flag for parallel processing if needed later.

**Rationale**: 820 serial calls at ~0.5s each ≈ 7 minutes. Acceptable for a one-time validation run. Parallel processing can be added as an optimization but isn't needed for MVP.
