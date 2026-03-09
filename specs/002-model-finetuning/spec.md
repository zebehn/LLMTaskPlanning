# Feature Specification: Local Model Fine-Tuning Pipeline

**Feature Branch**: `002-model-finetuning`
**Created**: 2026-03-05
**Status**: Draft
**Input**: User description: "Local models may later be fine-tuned using SFT, RLHF, DPO etc."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fine-Tune Local Model with SFT (Priority: P1)

A researcher wants to fine-tune a local model (e.g., Qwen3-8B) on task planning
demonstrations using Supervised Fine-Tuning (SFT), so that the model learns from
correct ALFRED task plans and improves its planning performance.

**Why this priority**: SFT is the simplest and most foundational fine-tuning method.
It provides the training data infrastructure and model-saving pipeline that all other
methods (RLHF, DPO) build upon.

**Independent Test**: Run SFT fine-tuning on a small subset of ALFRED task demonstrations,
confirm a fine-tuned model checkpoint is saved, and verify the checkpoint can be loaded
and used for evaluation.

**Acceptance Scenarios**:

1. **Given** a set of ALFRED task planning demonstrations, **When** the researcher
   launches SFT fine-tuning on a local model, **Then** the training completes and
   saves a fine-tuned model checkpoint to a configurable output directory.

2. **Given** a completed SFT run, **When** the researcher loads the saved checkpoint,
   **Then** the fine-tuned model can be used with the existing ReAct evaluator without
   any additional configuration.

3. **Given** insufficient GPU memory for the configured batch size, **When** fine-tuning
   is launched, **Then** the system reports a clear error message with guidance on
   reducing batch size or using memory-efficient training settings.

4. **Given** an interrupted fine-tuning run, **When** the researcher restarts training,
   **Then** training resumes from the most recent saved checkpoint rather than from
   scratch.

---

### User Story 2 - Generate Training Data from Evaluation Runs (Priority: P2)

A researcher wants to automatically extract training signal from existing evaluation
runs—successful task plans for SFT, and success/failure pairs for preference-based
methods (DPO/RLHF)—so that the evaluation infrastructure feeds directly into the
training pipeline.

**Why this priority**: Without automatic data extraction, researchers must manually
curate training data, which is error-prone and time-consuming. This story enables
closed-loop experimentation.

**Independent Test**: Run a ReAct evaluation, then invoke the data extraction tool and
confirm it produces a training dataset file in the expected format for the target
fine-tuning method.

**Acceptance Scenarios**:

1. **Given** a completed ReAct evaluation with mixed success/failure outcomes, **When**
   the researcher runs the training data extractor for SFT, **Then** a dataset file is
   produced containing only the successful task plans in the correct training format.

2. **Given** a completed ReAct evaluation with at least one success and one failure per
   task, **When** the researcher runs the data extractor for DPO, **Then** a dataset
   file is produced containing (instruction, chosen, rejected) triples derived from
   the evaluation outcomes.

3. **Given** an evaluation run with no successes, **When** the data extractor is run
   for SFT, **Then** the system warns the researcher that no valid training examples
   were found and produces an empty dataset rather than failing silently.

---

### User Story 3 - Compare Fine-Tuned vs Base Model Performance (Priority: P3)

A researcher wants to evaluate the fine-tuned model on the ALFRED benchmark and compare
its task success rate against the base model, so they can quantify the improvement
achieved by fine-tuning.

**Why this priority**: Without comparison tooling, researchers cannot confirm that
fine-tuning improved performance or determine which fine-tuning method worked best.

**Independent Test**: Run evaluation with both the base and fine-tuned checkpoints on
the same task subset; confirm a side-by-side comparison report is generated.

**Acceptance Scenarios**:

1. **Given** a fine-tuned checkpoint and the original base model, **When** the researcher
   runs evaluation on both, **Then** a comparison report shows per-task and aggregate
   success rates for each model side-by-side.

2. **Given** comparison results across multiple fine-tuning runs (SFT, DPO), **When**
   the researcher reviews the report, **Then** the report clearly identifies which
   method achieved the highest task success rate.

---

### User Story 4 - Fine-Tune with DPO or RLHF (Priority: P4)

A researcher wants to apply preference-based fine-tuning (DPO or RLHF) using
success/failure pairs from ALFRED evaluation runs as training signal, enabling
alignment of the model's planning behavior with task success outcomes.

**Why this priority**: DPO and RLHF represent more advanced alignment methods with
higher complexity; they depend on the SFT and data extraction infrastructure from P1
and P2.

**Independent Test**: Run DPO fine-tuning using preference pairs extracted from a
prior evaluation run; confirm a fine-tuned checkpoint is saved and can be loaded for
evaluation.

**Acceptance Scenarios**:

1. **Given** a preference dataset (chosen/rejected pairs), **When** the researcher
   launches DPO fine-tuning, **Then** training completes and saves a fine-tuned
   checkpoint.

2. **Given** an RLHF configuration with a reward model derived from task success
   signals, **When** the researcher runs RLHF training, **Then** the model is updated
   according to the reward signal and a checkpoint is saved.

---

### Edge Cases

- What happens when the training dataset is too small to produce meaningful improvement?
- How does the system handle NaN losses or training instability mid-run?
- What happens when a fine-tuned checkpoint is incompatible with the current evaluator
  (e.g., vocabulary mismatch)?
- How does the system handle multiple concurrent fine-tuning runs competing for GPU
  resources?
- What happens when the preference dataset has no valid (success, failure) pairs for
  a given task type?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support SFT fine-tuning of local models on ALFRED task
  planning demonstrations, producing a saved model checkpoint upon completion.
- **FR-002**: System MUST support DPO fine-tuning using preference pairs derived from
  ALFRED evaluation outcomes (successful vs failed plans).
- **FR-003**: System MUST support RLHF fine-tuning using task success/failure signals
  from ALFRED evaluation runs as reward signal.
- **FR-004**: System MUST provide a training data extraction tool that converts
  evaluation output files into training datasets for the supported fine-tuning methods.
- **FR-005**: Fine-tuned model checkpoints MUST be loadable by the existing evaluation
  infrastructure as a drop-in replacement for the base model.
- **FR-006**: System MUST support checkpoint resumption so that interrupted training
  runs can be restarted from the last saved state.
- **FR-007**: Users MUST be able to configure training hyperparameters (learning rate,
  batch size, number of epochs, checkpoint frequency) via the existing configuration
  system.
- **FR-008**: System MUST report training progress (loss, step count, estimated time
  remaining) during fine-tuning runs.
- **FR-009**: System MUST generate a comparison report when evaluation results from
  multiple model checkpoints (base and fine-tuned) are available.
- **FR-010**: System MUST validate that the training dataset is non-empty and meets
  minimum size requirements before starting a fine-tuning run, reporting actionable
  errors if not.

### Key Entities

- **Training Dataset**: A collection of examples in the format required by a specific
  fine-tuning method (demonstrations for SFT, preference pairs for DPO, trajectory
  with rewards for RLHF).
- **Fine-Tuning Run**: A configured training job specifying the base model, method,
  dataset, hyperparameters, and output directory.
- **Model Checkpoint**: A saved model state at a point during or after training;
  loadable by the evaluator.
- **Comparison Report**: A structured summary of evaluation metrics across multiple
  model checkpoints, enabling side-by-side performance comparison.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A researcher can complete an end-to-end SFT fine-tuning run—from raw
  evaluation output to a usable fine-tuned checkpoint—using only configuration changes,
  with no code modifications.
- **SC-002**: Fine-tuned model checkpoints are loadable by the existing evaluation
  infrastructure without errors or manual file manipulation.
- **SC-003**: Training data extraction from a completed evaluation run produces a
  valid dataset file in under 60 seconds for a standard evaluation run size.
- **SC-004**: An interrupted fine-tuning run, when restarted, resumes from the last
  checkpoint and does not repeat already-completed training steps.
- **SC-005**: A comparison report is generated automatically when two or more model
  checkpoints are evaluated on the same task set, requiring no manual data merging.
- **SC-006**: All existing evaluation and provider tests continue to pass after the
  fine-tuning pipeline is added (no regressions).

## Assumptions

- The base model for fine-tuning is a local model loaded via the transformers library
  (as established in feature 001-local-transformers-provider).
- SFT is the first method to be implemented; DPO and RLHF are subsequent iterations
  that reuse the SFT infrastructure.
- Training data is sourced from existing ALFRED evaluation output files (ReAct or
  ground-truth runs); no external datasets are required.
- Hardware with at least one CUDA-capable GPU is available for fine-tuning; CPU-only
  fine-tuning is not a supported configuration.
- RLHF in this context uses task success/failure as the reward signal directly, not
  a separately trained reward model (simplified RLHF).
- Model checkpoints are saved in the same format as the base model, ensuring
  compatibility with the existing model loading infrastructure.

## Out of Scope

- Training a separate reward model from scratch for RLHF.
- Multi-node distributed training across multiple machines.
- Automated hyperparameter search or neural architecture search.
- Deployment or serving of fine-tuned models outside the existing evaluation framework.
- Fine-tuning models other than those supported by feature 001.
- Dataset curation or quality filtering beyond basic validity checks.
