# Research: 003-react-planner-eval

**Date**: 2026-02-21

## R1: ReAct Planning Approach for Embodied Agents

**Decision**: Implement the ReAct Thought-Action-Observation loop from Yao et al. (ICLR 2023) adapted for the project's high-level action abstraction layer.

**Rationale**: The paper demonstrates that interleaving reasoning traces with actions significantly outperforms action-only baselines on ALFWorld (71% vs 45% best trial). Thoughts serve four key purposes: (1) task decomposition, (2) commonsense object location reasoning, (3) subgoal progress tracking, (4) error recovery. The project's existing `llm_skill_interact()` already provides a high-level action abstraction (e.g., `find a apple`, `pick up the mug`) that maps well to the ReAct paradigm.

**Alternatives considered**:
- **Action-only (Act)**: Already the existing approach. Paper shows 45% success (best of 6 trials) vs 71% for ReAct.
- **Inner Monologue (IM)**: Dense feedback thoughts only about current goal/subgoal status. Paper shows 53% vs 71% for ReAct. IM lacks abstract reasoning about high-level plans and commonsense.
- **Chain-of-Thought (CoT)**: Pure reasoning without environment interaction. Not applicable -- embodied tasks require closed-loop environment feedback.

## R2: LLM Interaction Mode

**Decision**: Use `chat_completion()` (free-form generation) instead of `select_action()` (constrained scoring) for the ReAct planner.

**Rationale**: The existing `plan_step_by_step()` method uses `select_action()` to pick from a predefined skill set. ReAct requires free-form thought generation followed by action generation. The `chat_completion()` method on `LLMProvider` already supports this. The planner will generate thoughts as free text and actions as parseable commands, then extract the action to pass to `llm_skill_interact()`.

**Alternatives considered**:
- **Constrained scoring with reasoning prefix**: Force the LLM to output a thought, then score skills. Loses the flexibility of ReAct -- the LLM can't propose novel search strategies or reason about failures dynamically.
- **Two-call approach**: One call for thought, one for action selection. Doubles API calls and breaks the natural flow of the ReAct paradigm.

## R3: Evaluator Architecture

**Decision**: Create a new `ReActAlfredEvaluator` class that reuses the existing `AlfredEvaluator`'s setup/teardown but implements a distinct execution loop for the ReAct Thought-Action-Observation cycle.

**Rationale**: The existing evaluator's step-by-step loop (a) stops on first failure, (b) doesn't generate thoughts, and (c) doesn't construct observations from environment state. The ReAct loop is fundamentally different: it continues after failures (the failure becomes an observation), generates reasoning before each action, and needs richer observation construction. Subclassing `AlfredEvaluator` allows reusing scene setup, dataset loading, and result saving while replacing only the task execution loop.

**Alternatives considered**:
- **Modify existing evaluator with mode flag**: Would add complexity to already long methods. Violates single responsibility. Makes A/B comparison between planners harder.
- **Completely new evaluator**: Duplicates scene setup, dataset loading, result saving code. Not DRY.

## R4: Prompt Design

**Decision**: Adapt the paper's ALFWorld ReAct prompts (Appendix C.4) to the project's action vocabulary. Use 1-2 few-shot examples per task type with explicit Think/Act/Obs formatting.

**Rationale**: The paper uses 3 annotated trajectories per task type with a text-game action format (`go to fridge 1`, `take lettuce 1 from countertop 2`). The project uses a higher-level action abstraction (`find a lettuce`, `pick up the lettuce`). The few-shot examples must demonstrate: (a) the correct action vocabulary, (b) the Think/Act/Obs format, (c) task decomposition patterns, and (d) error recovery. Two examples per task type keeps the prompt manageable while showing variety.

**Alternatives considered**:
- **Zero-shot**: The paper notes ReAct benefits significantly from few-shot examples. Zero-shot would likely underperform.
- **Direct paper prompts**: The paper's ALFWorld text-game commands don't match this project's action format. Would cause parsing failures.
- **6+ examples per type**: Paper found more examples don't improve performance. Would waste context window.

## R5: Observation Construction

**Decision**: Construct text observations from the action return dict plus minimal environment metadata (visible objects, inventory). Format as natural language sentences.

**Rationale**: The paper's ALFWorld observations describe what the agent sees after each action (e.g., "On the countertop 1, you see a lettuce 2, a mug 2"). The project's `llm_skill_interact()` returns `{action, success, message}` which is insufficient for rich reasoning. By querying the environment metadata after each action, we can construct informative observations that tell the planner what objects are nearby, what it's holding, and whether the action succeeded.

**Alternatives considered**:
- **Success/failure only**: Minimal information. Planner can't reason about where to go next or what objects are available.
- **Full metadata dump**: Too verbose. Would consume context window rapidly. The planner needs human-readable summaries, not raw JSON.

## R6: Configuration and Non-Headless Mode

**Decision**: Create a new config file `conf/config_alfred_react.yaml` with `name: alfred_react`. Non-headless mode is already the default (controlled by `cfg.alfred.x_display`). The 5% subset is already supported via `cfg.alfred.eval_portion_in_percent`.

**Rationale**: The project's pattern is one config file per evaluation mode. The existing `x_display: '0'` setting renders to the local display (non-headless). The `eval_portion_in_percent: 5` setting already handles 5% subset selection with reproducible seeding.

**Alternatives considered**:
- **Reuse config_alfred.yaml with overrides**: Would require CLI overrides for planner type selection. Less discoverable.

## R7: Failure Handling Strategy

**Decision**: On action failure, continue the ReAct loop (don't stop). Feed the failure as an observation to the planner so it can reason about alternatives.

**Rationale**: The existing evaluator stops on first failure (`if not action_ret['success']: break`). This is appropriate for action-only planning but defeats the purpose of ReAct. The core advantage of ReAct is that the planner can reason about failures and try alternative strategies. The paper shows this as a key differentiator.

**Alternatives considered**:
- **Stop on failure (existing behavior)**: Negates ReAct's error recovery capability. Would produce worse results than necessary.
- **Retry same action N times**: Doesn't leverage reasoning. If an action fails, retrying the same action is unlikely to succeed.
