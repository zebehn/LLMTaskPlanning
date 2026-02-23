# Feature Specification: LLM Provider Expansion for Reasoning Models

**Feature Branch**: `004-llm-provider-expansion`
**Created**: 2026-02-23
**Status**: Draft
**Input**: User description: "expand the coverage of LLM services into reasoning models like OpenAI gpt-5.2, gpt-5-mini, gpt-5-nano, and qwen3.5, glm-5, kimi-k2.5 on Ollama and LMStudio via OpenAI-compatible API."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Evaluation with OpenAI Reasoning Models (Priority: P1)

A researcher wants to evaluate ALFRED task planning performance using OpenAI's latest reasoning models (gpt-5.2, gpt-5-mini, gpt-5-nano) which support extended thinking and reasoning effort control. They change the model name and reasoning effort level in the config and run the evaluation without any code changes.

**Why this priority**: OpenAI reasoning models are the primary cloud-hosted models already partially supported. Completing their coverage (gpt-5-mini, gpt-5-nano) enables immediate cost/performance tradeoff experiments across model sizes.

**Independent Test**: Can be fully tested by setting `model_name: gpt-5-mini` in config and running a 1% evaluation. Delivers value by enabling cheaper reasoning model evaluation.

**Acceptance Scenarios**:

1. **Given** config has `provider: openai` and `model_name: gpt-5.2`, **When** evaluation runs, **Then** the system uses `max_completion_tokens` (not `max_tokens`), respects `reasoning_effort`, and returns valid action outputs.
2. **Given** config has `model_name: gpt-5-mini` and `reasoning_effort: low`, **When** a chat completion is requested, **Then** the API call includes `reasoning_effort: low` and `max_completion_tokens`.
3. **Given** config has `model_name: gpt-5-nano`, **When** evaluation runs, **Then** it behaves identically to other gpt-5 variants in parameter handling.

---

### User Story 2 - Run Evaluation with Local Reasoning Models via Ollama (Priority: P2)

A researcher wants to evaluate open-source reasoning models (qwen3.5, glm-5, kimi-k2.5) served locally through Ollama. They configure the provider as `ollama`, set the model name, and optionally enable reasoning-model parameter handling if the model supports it.

**Why this priority**: Ollama is the most popular local inference server. Supporting reasoning-model-aware parameter handling for locally served models enables zero-cost experimentation with open-source alternatives.

**Independent Test**: Can be fully tested by running Ollama with `qwen3.5` pulled locally, setting `provider: ollama` and `model_name: qwen3.5`, and running a 1% evaluation.

**Acceptance Scenarios**:

1. **Given** Ollama is running with qwen3.5 loaded, and config has `provider: ollama` and `model_name: qwen3.5`, **When** evaluation runs, **Then** the system sends chat completion requests to Ollama and receives valid responses.
2. **Given** config has `provider: ollama`, `model_name: glm-5`, and `reasoning_effort: medium`, **When** a chat completion is requested, **Then** the system detects glm-5 as a reasoning model and logs the detection, but always uses standard parameters (`max_tokens` + `temperature`) because Ollama's handling of `reasoning_effort` is unreliable.
3. **Given** Ollama is not running, **When** evaluation attempts to connect, **Then** a clear error message indicates Ollama is unreachable and suggests starting it.

---

### User Story 3 - Run Evaluation with Local Reasoning Models via LM Studio (Priority: P3)

A researcher wants to evaluate reasoning models (qwen3.5, glm-5, kimi-k2.5) served through LM Studio. They configure the provider as `lmstudio`, set the model name, and run the evaluation.

**Why this priority**: LM Studio is an alternative local inference server with a GUI. Supporting it provides flexibility for researchers who prefer LM Studio's model management interface.

**Independent Test**: Can be fully tested by loading kimi-k2.5 in LM Studio, setting `provider: lmstudio` and `model_name: kimi-k2.5`, and running a 1% evaluation.

**Acceptance Scenarios**:

1. **Given** LM Studio is running with kimi-k2.5 loaded, and config has `provider: lmstudio` and `model_name: kimi-k2.5`, **When** evaluation runs, **Then** the system sends chat completion requests and receives valid responses.
2. **Given** config has `provider: lmstudio` and a reasoning model is configured with `reasoning_effort`, **When** a chat completion is requested, **Then** reasoning-aware parameters are used if the model supports them.

---

### User Story 4 - Unified Reasoning Model Detection Across Providers (Priority: P2)

A researcher wants to add a new reasoning model to the system without modifying provider code. They add the model's prefix to a centralized reasoning model registry, and all providers automatically handle it with the correct parameters.

**Why this priority**: Currently, reasoning model detection is hardcoded in `OpenAIProvider._is_reasoning_model()` with only OpenAI prefixes. Centralizing detection enables all providers (including Ollama and LM Studio) to correctly handle any reasoning model.

**Independent Test**: Can be tested by adding a new model prefix to the registry and verifying that all providers recognize it as a reasoning model.

**Acceptance Scenarios**:

1. **Given** the reasoning model registry includes `"qwen3"` as a known prefix, **When** `model_name: qwen3.5` is used with any provider, **Then** the system detects it as a reasoning model and applies reasoning-aware parameters.
2. **Given** a model name that does NOT match any known reasoning prefix, **When** used with any provider, **Then** the system uses standard chat completion parameters (temperature + max_tokens).
3. **Given** a user adds a new model prefix to the configuration, **When** evaluation runs with that model, **Then** no code changes are needed beyond the config update.

---

### Edge Cases

- What happens when a reasoning model is served via Ollama/LM Studio but the local server does not support `max_completion_tokens` or `reasoning_effort` parameters? The system should gracefully fall back to standard parameters (`temperature` + `max_tokens`).
- What happens when the configured model name does not match any model available on the local server? The local server's error should be propagated with a clear message.
- What happens when `reasoning_effort` is set for a non-reasoning model? The parameter should be silently ignored.
- What happens when a reasoning model is used with `temperature: 0.0`? Some reasoning models ignore temperature; the system should not error but may log a warning.
- What happens when the Ollama/LM Studio endpoint URL is customized (non-default port)? The `api_base` config option must be respected.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST recognize gpt-5.2, gpt-5-mini, and gpt-5-nano as reasoning models and use `max_completion_tokens` instead of `max_tokens` when calling the OpenAI API.
- **FR-002**: System MUST support `reasoning_effort` parameter ("low", "medium", "high") for recognized reasoning models on providers whose backends support it (OpenAI, vLLM). For providers with unreliable support (Ollama, LM Studio), the system MUST detect reasoning models and log it, but use standard parameters only.
- **FR-003**: System MUST support serving qwen3.5, glm-5, and kimi-k2.5 models through Ollama's OpenAI-compatible API endpoint.
- **FR-004**: System MUST support serving qwen3.5, glm-5, and kimi-k2.5 models through LM Studio's OpenAI-compatible API endpoint.
- **FR-005**: System MUST provide a centralized reasoning model detection mechanism that all providers share, replacing the current OpenAI-only `_is_reasoning_model()` method.
- **FR-006**: System MUST allow new reasoning model prefixes to be added via configuration without code changes.
- **FR-007**: Ollama and LM Studio providers MUST gracefully handle cases where the local server does not support reasoning-specific parameters (`max_completion_tokens`, `reasoning_effort`), falling back to standard parameters.
- **FR-008**: System MUST propagate clear, actionable error messages when a local server (Ollama/LM Studio) is unreachable or returns an error.
- **FR-009**: System MUST maintain backward compatibility — existing configurations using gpt-4, gpt-3.5-turbo, llama3, mistral, or other non-reasoning models must continue to work without changes.
- **FR-010**: System MUST allow custom API base URLs for all providers via the `api_base` configuration option.

### Key Entities

- **Reasoning Model Registry**: A centralized list of model name prefixes that identify reasoning models (e.g., `gpt-5`, `o1`, `o3`, `qwen3`, `glm-`, `kimi-k`). Used by all providers to determine parameter handling.
- **LLM Provider**: An abstraction that sends chat completion requests to an LLM service. Each provider (OpenAI, Ollama, LM Studio, vLLM) connects to a different backend but shares the same interface.
- **Provider Configuration**: Settings that define which provider, model, and parameters to use for evaluation (provider type, model name, API endpoint, reasoning effort level).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All six new models (gpt-5.2, gpt-5-mini, gpt-5-nano, qwen3.5, glm-5, kimi-k2.5) can be configured and used for evaluation by changing only YAML config values — zero code changes required per model.
- **SC-002**: Reasoning-aware parameter handling (max_completion_tokens, reasoning_effort) works correctly for all recognized reasoning models across all four providers (OpenAI, Ollama, LM Studio, vLLM).
- **SC-003**: Existing evaluations using gpt-4, gpt-3.5-turbo, and other non-reasoning models produce identical results before and after the change (backward compatibility).
- **SC-004**: When a local server (Ollama/LM Studio) does not support a reasoning-specific parameter, the system completes the request using standard parameters without crashing.
- **SC-005**: All new functionality is covered by automated tests that pass without requiring a live LLM service.
- **SC-006**: Adding support for a future reasoning model requires only adding its prefix to the configuration — no provider code modifications needed.

## Assumptions

- OpenAI's gpt-5-mini and gpt-5-nano follow the same API parameter conventions as gpt-5.2 (i.e., `max_completion_tokens` and `reasoning_effort`).
- LM Studio's OpenAI-compatible API silently ignores unsupported parameters. Ollama's handling is inconsistent: `max_completion_tokens` is silently ignored but `reasoning_effort` can cause HTTP errors with invalid values. Therefore, Ollama and LM Studio providers always use standard parameters (`max_tokens` + `temperature`) rather than reasoning-specific ones.
- The models qwen3.5, glm-5, and kimi-k2.5 are available for download and serving through Ollama and/or LM Studio at the time of implementation.
- Reasoning effort control via the `reasoning_effort` parameter is an OpenAI-specific feature; for local models, it may be passed but is likely ignored by the server.

## Scope Boundaries

**In scope**:
- Expanding reasoning model detection to cover new OpenAI models and open-source models
- Centralizing reasoning model detection logic shared across all providers
- Adding reasoning-aware parameter handling to Ollama and LM Studio providers
- Making the reasoning model prefix list configurable
- Updating tests for new model coverage

**Out of scope**:
- Adding entirely new LLM providers (e.g., Anthropic Claude, Google Gemini)
- Implementing model-specific prompt engineering or tuning
- Automatic model downloading or installation for Ollama/LM Studio
- Performance benchmarking or comparison across models
- Streaming response support
- Multi-modal (vision) model support
