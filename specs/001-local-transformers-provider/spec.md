# Feature Specification: Local Transformers Provider for ReAct Experiments

**Feature Branch**: `001-local-transformers-provider`
**Created**: 2026-03-05
**Status**: Draft
**Input**: User description: "run an experiment with ReAct-based planner using a local Qwen3-8B model. Use the model on huggingface(Qwen/Qwen3-8B). Support for local models using transformers library should be implemented."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run ReAct Experiment with Local Model (Priority: P1)

A researcher wants to run the ReAct-based task planner evaluation against the ALFRED
benchmark using a locally-hosted Qwen3-8B model, without requiring any external API
access or internet connectivity during inference.

**Why this priority**: Core goal of the feature. Enables cost-free offline experimentation
and reproducible research with a specific open-weight model.

**Independent Test**: Run the full ReAct evaluation on a subset of ALFRED tasks using
the local Qwen3-8B model and verify that a results summary file is produced with
task success/failure metrics identical in structure to API-based runs.

**Acceptance Scenarios**:

1. **Given** a researcher has the Qwen/Qwen3-8B model available locally, **When** they
   launch the ReAct evaluation configured to use the local model, **Then** the evaluation
   completes and produces a results file with per-task outcomes and aggregate metrics.

2. **Given** the local model is not yet downloaded, **When** the researcher launches the
   evaluation, **Then** the system downloads the model and proceeds with evaluation,
   reporting download progress clearly.

3. **Given** the local model configuration is invalid (e.g., unsupported model name),
   **When** the researcher launches the evaluation, **Then** the system reports a clear
   error message before starting any tasks.

---

### User Story 2 - Configure Local Model for Hardware (Priority: P2)

A researcher wants to control how the local model is loaded—choosing which compute
device to use and what memory/precision trade-offs to apply—so they can run experiments
on available hardware (single GPU, multi-GPU, or CPU).

**Why this priority**: Without hardware configuration, the system may fail on resource-
constrained machines or underutilize available hardware.

**Independent Test**: Launch evaluation with different device and precision settings
and confirm the system honors those settings (model runs on the specified device without
errors).

**Acceptance Scenarios**:

1. **Given** a machine with one GPU, **When** the researcher configures the local model
   to use that GPU with half-precision, **Then** the model loads and runs inference on
   that GPU.

2. **Given** a CPU-only machine, **When** the researcher configures CPU mode, **Then**
   the evaluation runs (slower) without crashing.

3. **Given** insufficient memory for the configured precision, **When** the evaluation
   starts, **Then** the system reports a clear out-of-memory error with guidance.

---

### User Story 3 - Compare Local Model Results with API-Based Providers (Priority: P3)

A researcher wants to compare the ReAct task planning performance of the local Qwen3-8B
model against previously run API-based providers using the same evaluation format.

**Why this priority**: Without output parity, cross-provider comparison requires manual
data wrangling. Parity enables direct benchmarking.

**Independent Test**: Run evaluation with both the local provider and an API provider
on the same task subset; confirm output files share identical schema and can be read
by the same analysis scripts.

**Acceptance Scenarios**:

1. **Given** results from a prior API-based ReAct run, **When** a local model run
   completes, **Then** both result files share the same JSON schema and field names.

2. **Given** both result sets, **When** loaded into the existing analysis/reporting
   tools, **Then** both load without errors and produce comparable summary statistics.

---

### Edge Cases

- What happens when the model download is interrupted mid-way?
- How does the system handle GPU out-of-memory errors mid-evaluation (after some tasks
  have already completed)?
- What happens when the local model produces malformed JSON responses that the ReAct
  parser cannot handle?
- How does the system behave when disk space is insufficient to store the downloaded
  model weights?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support a local model provider that loads and runs the
  Qwen/Qwen3-8B model without external API calls during inference.
- **FR-002**: The local model provider MUST integrate with the existing provider factory
  so it can be selected via the same configuration mechanism as other providers.
- **FR-003**: The ReAct evaluator MUST be able to use the local model provider as a
  drop-in replacement for API-based providers, with no changes to evaluation logic.
- **FR-004**: Users MUST be able to configure the compute device (e.g., specific GPU,
  multi-GPU, CPU) and inference precision for the local model via the existing
  configuration system.
- **FR-005**: Evaluation output files produced by the local model provider MUST be
  schema-compatible with those produced by existing API-based providers.
- **FR-006**: The system MUST report clear, actionable error messages when the local
  model fails to load (missing weights, insufficient memory, unsupported device).
- **FR-007**: The system MUST display progress feedback when downloading model weights
  for the first time.
- **FR-008**: The local model provider MUST respect the existing `max_tokens` and
  temperature configuration parameters used across all providers.

### Key Entities

- **Local Model Provider**: A provider that loads model weights onto local hardware
  and runs inference on-device; configured with model identifier, device, and precision.
- **Model Configuration**: Settings controlling which model to load, on which device,
  and with what precision/memory constraints.
- **Evaluation Result**: Per-task and aggregate outcome records; schema-compatible
  across all provider types.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A researcher can run a complete ReAct evaluation using the local Qwen3-8B
  model with a single configuration change (provider type), requiring no code modifications.
- **SC-002**: Evaluation result files from the local provider are readable by the same
  analysis tooling used for API-based provider results, with zero schema differences.
- **SC-003**: All existing provider and ReAct evaluator tests continue to pass after
  the local provider is added (no regressions).
- **SC-004**: The local provider can be selected and configured entirely through the
  existing configuration system, consistent with how other providers are configured.
- **SC-005**: When model weights are already cached, evaluation startup adds no
  significant overhead compared to other provider initialization (no redundant downloads
  on repeat runs).

## Assumptions

- The researcher has sufficient local disk space to store Qwen3-8B model weights
  (~16 GB for the base model).
- Hardware with at least one CUDA-capable GPU is the primary target; CPU mode is
  supported but expected to be significantly slower.
- The Qwen/Qwen3-8B model on HuggingFace is publicly accessible without authentication.
- The existing ReAct evaluator's prompt templates and JSON parsing are compatible with
  Qwen3-8B's output format; if not, prompt adaptation is considered a separate concern.
- Model caching follows the default HuggingFace cache directory convention.

## Out of Scope

- Fine-tuning or quantization of the Qwen3-8B model.
- Support for other local model formats (GGUF, ONNX) beyond the transformers library
  checkpoint format.
- A UI or interactive configuration wizard for local model setup.
- Automated performance benchmarking or speed comparison tooling.
