# Feature Specification: ALFRED Instruction Validation

**Feature Branch**: `005-instruction-validation`
**Created**: 2026-02-26
**Status**: Draft
**Input**: User description: "Create a script to check all ALFRED task instructions to identify obviously wrong instructions: (1) objects/receptacles not in scene, (2) mismatch with PDDL ground truth, (3) semantically ambiguous descriptions. Produce a structured report classifying instructions into 4 categories (0-3) so the evaluator can skip bad instructions."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Validate All Instructions in a Split (Priority: P1)

A researcher wants to validate all task instructions in a given ALFRED evaluation split (e.g., `valid_seen`) before running an expensive LLM evaluation. They run the validation script, which scans every task/annotator combination, compares the instruction text against the scene objects and PDDL ground truth, and produces a structured JSON report classifying each instruction into one of four categories.

**Why this priority**: This is the core functionality. Without it, the researcher wastes LLM API credits and GPU time on tasks that are impossible to complete due to bad annotations.

**Independent Test**: Can be tested by running the script on `valid_seen` split and verifying the output report contains entries for all 820 task/annotator combinations with valid category assignments.

**Acceptance Scenarios**:

1. **Given** the ALFRED dataset is preprocessed and available at `alfred/data/json_2.1.0/`, **When** the user runs the validation script for `valid_seen`, **Then** a JSON report is produced with one entry per (task, repeat_idx) combination, each classified as category 0, 1, 2, or 3.
2. **Given** a task where the annotator wrote "Put a bottle on the back of a newspaper" but the PDDL target is Candle→Toilet and neither Bottle nor Newspaper exist in the scene, **When** validation runs, **Then** the instruction is classified as category 1 (non-existent object) and/or category 2 (goal mismatch).
3. **Given** a task where the annotator wrote "black fabric" but the PDDL target is "Cloth" and Cloth exists in the scene, **When** validation runs, **Then** the instruction is classified as category 3 (semantically ambiguous) rather than category 1 or 2.

---

### User Story 2 - Filter Bad Instructions During Evaluation (Priority: P2)

A researcher wants the ReAct evaluator to automatically skip instructions that are classified as problematic (categories 1, 2, or 3) based on the validation report, so only correct and valid instructions (category 0) are evaluated.

**Why this priority**: This directly improves evaluation accuracy by eliminating noise from bad annotations. Depends on the report existing (US1).

**Independent Test**: Can be tested by running the evaluator with a validation report and confirming that tasks marked as categories 1/2/3 are skipped, while category 0 tasks are evaluated normally.

**Acceptance Scenarios**:

1. **Given** a validation report exists and the evaluator is configured to use it, **When** evaluation runs on a split, **Then** only instructions classified as category 0 are executed; others are skipped with a log message.
2. **Given** a validation report exists, **When** the evaluator skips a task, **Then** the skip is recorded in the evaluation output with the category and reason from the validation report.
3. **Given** the evaluator is configured to filter by specific categories (e.g., skip only category 1), **When** evaluation runs, **Then** only instructions in the specified categories are skipped.

---

### User Story 3 - Human-Readable Summary Report (Priority: P3)

A researcher wants a human-readable summary alongside the machine-readable JSON, showing aggregate statistics per category, per task type, and per split, to understand the annotation quality landscape.

**Why this priority**: Useful for understanding dataset quality at scale but not required for the core filtering functionality.

**Independent Test**: Can be tested by running the script and verifying the summary includes correct counts, percentages, and examples per category.

**Acceptance Scenarios**:

1. **Given** the validation script has classified all instructions, **When** the script completes, **Then** a summary section shows the count and percentage of instructions in each category.
2. **Given** the validation results, **When** the summary is generated, **Then** per-task-type breakdowns are included (e.g., "pick_and_place_simple: 85% valid, 5% non-existent, 7% mismatch, 3% ambiguous").

---

### Edge Cases

- What happens when a task directory exists in the split but the preprocessed annotation file is missing? The script should log a warning and skip that entry.
- What happens when the scene `object_poses` list is empty? The instruction should be classified as category 1 if it references any objects.
- What happens when the PDDL `object_target` uses a "Sliced" variant (e.g., "PotatoSliced") but the instruction says "potato"? This should be treated as valid (category 0), since the sliced/unsliced distinction is a simulator detail not visible to annotators. The prompt should include both forms.
- What happens when the LLM API call fails (network error, rate limit)? The script should retry with exponential backoff (up to 3 retries), then log the failure and skip that entry.
- What happens when the LLM returns an unparseable response? The script should log the raw response and classify the entry as category 3 (ambiguous) as a conservative default.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST scan all (task, repeat_idx) entries in a given ALFRED split file (`alfred/data/splits/oct21.json`) and load the corresponding preprocessed annotation (`pp/ann_{repeat_idx}.json`).
- **FR-002**: System MUST extract the PDDL ground truth (`object_target`, `parent_target`, `mrecep_target`) from either the preprocessed annotation's `pddl_params` field or the task directory name (format: `{task_type}-{object}-{mrecep}-{receptacle}-{scene_num}`).
- **FR-003**: System MUST extract the list of unique object types from the scene's `object_poses` array by stripping the instance suffix (e.g., `Candle_96bce45a` → `Candle`).
- **FR-004**: System MUST use a lightweight LLM (e.g., gpt-5-mini with reasoning_effort=low) to classify each instruction by providing the instruction text, scene object list, and PDDL ground truth targets as context.
- **FR-005**: System MUST classify each instruction into exactly one of four categories:
  - **Category 0 ("valid")**: Mentioned objects/receptacles exist in scene AND match PDDL targets.
  - **Category 1 ("non_existent")**: Instruction mentions objects or receptacles that do not exist anywhere in the scene's object list, even after semantic matching.
  - **Category 2 ("goal_mismatch")**: Instruction objects exist in scene but do not match the PDDL ground truth targets (wrong object or wrong receptacle).
  - **Category 3 ("ambiguous")**: Instruction uses ambiguous or colloquial terms (e.g., "black fabric" for Cloth, "cup" when target is "Mug") that could plausibly refer to the correct targets but are not exact matches.
- **FR-006**: System MUST reuse the existing LLM provider infrastructure (`LLMProviderFactory`) for LLM access, supporting all configured providers (openai, vllm, ollama, lmstudio).
- **FR-007**: System MUST output a structured JSON report containing, for each entry: `task_path`, `trial_id`, `repeat_idx`, `task_type`, `category` (0-3), `category_label`, `instruction_text`, `pddl_targets` (object_target, parent_target, mrecep_target), `scene_objects` (list of unique object types), and `reason` (human-readable explanation of the classification).
- **FR-008**: System MUST handle the "Sliced" variant convention: if `object_target` is "PotatoSliced", the base form "Potato" should be accepted in the instruction.
- **FR-009**: System MUST exclude `pick_two_obj_and_place` task type from validation, consistent with the evaluator's existing exclusion.
- **FR-010**: System MUST support filtering by `eval_portion_in_percent` and `random_seed_for_eval_subset` to validate only the subset that would be evaluated, matching the evaluator's sampling logic.

### Key Entities

- **Validation Entry**: One (task, repeat_idx) combination with its classification result. Contains: task path, trial ID, repeat idx, category, reason, instruction text, PDDL targets, and scene objects.
- **Validation Report**: Collection of all validation entries for a split, plus aggregate summary statistics.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The validation script correctly classifies at least 95% of known-bad instructions (as identified by manual review of the 5% evaluation failures) into categories 1, 2, or 3.
- **SC-002**: The validation script classifies at least 90% of known-good instructions (tasks that succeeded in evaluation) as category 0.
- **SC-003**: The script processes the entire `valid_seen` split (820 entries) within 15 minutes using gpt-5-mini, at a cost under $1.00.
- **SC-004**: When the evaluator uses the validation report to skip bad instructions, the effective success rate on remaining tasks improves compared to evaluating all tasks indiscriminately.

## Assumptions

- The ALFRED dataset is already preprocessed (preprocessed `pp/ann_N.json` files exist). The script will not trigger preprocessing.
- An OpenAI API key (or equivalent LLM provider) is available and configured (via environment variable or config).
- Category assignment follows a priority order: category 1 (non-existent) takes precedence over category 2 (mismatch), which takes precedence over category 3 (ambiguous). An instruction that is both non-existent and mismatched is classified as category 1.
- The LLM classification is run once per split and the report is cached as a JSON file for reuse across evaluation runs.
