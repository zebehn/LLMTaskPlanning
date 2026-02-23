# Research: LLM Provider Expansion for Reasoning Models

**Date**: 2026-02-23 | **Branch**: `004-llm-provider-expansion`

## R1: Ollama Handling of Reasoning Parameters

**Decision**: Use `max_tokens` (not `max_completion_tokens`) for Ollama. Do NOT pass `reasoning_effort` to Ollama unless the model explicitly supports it.

**Rationale**:
- Ollama does NOT support `max_completion_tokens` as a first-class parameter. It logs a warning but silently ignores it (GitHub issue #7125, open since 2024).
- `max_tokens` IS supported and is converted to `num_predict` internally.
- `reasoning_effort` has partial, buggy support in Ollama. Passing invalid values causes HTTP errors (not silent ignore). Only `"high"`, `"medium"`, `"low"` string values are accepted. Booleans and `"minimal"` cause crashes.

**Alternatives considered**:
- Always pass `max_completion_tokens` and catch errors → Rejected: unnecessary log noise and fragile.
- Wrap in try/except → Rejected: `reasoning_effort` can cause actual HTTP errors, not just warnings.

## R2: LM Studio Handling of Reasoning Parameters

**Decision**: LM Studio silently ignores unknown parameters. Safe to pass `max_completion_tokens` and `reasoning_effort`, but they will have no effect. Use `max_tokens` for actual length control.

**Rationale**:
- LM Studio's OpenAI-compatible layer is intentionally permissive — it silently ignores unrecognized parameters.
- `max_tokens` is the documented length-limiting parameter.
- No native `reasoning_effort` support exists.

**Alternatives considered**:
- Pass reasoning params and rely on silent ignore → Acceptable but provides false sense of control. Better to use standard params only.

## R3: vLLM Handling of Reasoning Parameters

**Decision**: vLLM supports both `max_tokens` and `max_completion_tokens`. `reasoning_effort` is partially supported for compatible models.

**Rationale**:
- Both parameters are accepted without error.
- Known bug (issue #28266): `max_completion_tokens` applies as total token budget when `--reasoning-parser` is enabled, not just visible output.
- `reasoning_effort` works for some models but is not uniformly supported.

**Alternatives considered**:
- Always use `max_completion_tokens` for vLLM → Rejected due to the budget bug. Use `max_tokens` as default, `max_completion_tokens` only when model is reasoning-aware.

## R4: Model-Specific Requirements for Local Deployment

**Decision**: Qwen3.5, GLM-5, and Kimi-K2.5 all support thinking modes via `extra_body` / `chat_template_kwargs`, but this is out of scope for the initial implementation. Standard `chat_completion` with `max_tokens` + `temperature` will work for all.

**Rationale**:
- **Qwen3.5**: Thinking mode controlled via `extra_body={"chat_template_kwargs": {"enable_thinking": False}}`. Default is thinking ON. When thinking is enabled, use `temperature=0.6`.
- **GLM-5**: Same `enable_thinking` mechanism via `chat_template_kwargs`. 745B MoE model — practical only via API, not local deployment.
- **Kimi-K2.5**: Thinking mode via `extra_body={"chat_template_kwargs": {"thinking": False}}` (different key than Qwen/GLM). 1T MoE model (32B active).
- All three work with standard OpenAI-compatible `chat_completion` parameters. Thinking mode is a model-level feature, not a provider-level concern.

**Alternatives considered**:
- Add `extra_body` support to the provider interface → Deferred: this is a separate feature. Standard params work for basic evaluation.

## R5: OpenAI `max_completion_tokens` vs `max_tokens`

**Decision**: Use conditional logic per model family: reasoning models use `max_completion_tokens`, non-reasoning models use `max_tokens`.

**Rationale**:
- OpenAI deprecated `max_tokens` in September 2024 for reasoning models (o1+).
- o1/o1-mini **reject** `max_tokens` with a 400 error — `max_completion_tokens` is required.
- gpt-3.5/gpt-4 still use `max_tokens`.
- gpt-5 variants use `max_completion_tokens`.

**Alternatives considered**:
- Always use `max_completion_tokens` → Rejected: older models may not recognize it.
- Always use `max_tokens` → Rejected: o1/o3 reject it with errors.

## R6: Centralized Reasoning Model Detection

**Decision**: Move `_is_reasoning_model()` from `OpenAIProvider` to the base `LLMProvider` class. Add a configurable list of reasoning model prefixes to `LLMConfig`.

**Rationale**:
- Currently hardcoded to `gpt-5`, `o1`, `o3` in `OpenAIProvider` only.
- Ollama/LM Studio/vLLM providers need the same detection to decide parameter handling.
- Making the prefix list configurable (via config YAML) satisfies FR-006.

**Alternatives considered**:
- Per-provider detection methods → Rejected: violates DRY, each provider would duplicate logic.
- Decorator pattern → Overengineered for a simple prefix check.
- External registry file → Overkill; config YAML is sufficient.

## R7: Graceful Fallback Strategy for Local Providers

**Decision**: Local providers (Ollama, LM Studio, vLLM) should attempt reasoning-aware parameters first, then catch API errors and retry with standard parameters.

**Rationale**:
- Ollama may error on `reasoning_effort` — need try/except.
- LM Studio silently ignores unknowns — try/except is harmless.
- vLLM supports both — try/except is harmless.
- Fallback ensures robustness across server versions and configurations.

**Alternatives considered**:
- Never pass reasoning params to local providers → Rejected: prevents future local models that DO support them.
- Always pass both sets of params → Rejected: Ollama errors on `reasoning_effort`.
