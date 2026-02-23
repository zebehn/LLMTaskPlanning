# Contract: ReActTaskPlanner Interface

**Date**: 2026-02-21

## Class: ReActTaskPlanner (extends TaskPlanner)

### Constructor

```python
def __init__(self, cfg):
    """
    Initialize ReAct planner from Hydra config.

    Expects:
        cfg.planner.provider: str - LLM provider ("openai", "vllm", etc.)
        cfg.planner.model_name: str - Model identifier
        cfg.planner.max_steps: int - Maximum steps per task (default: 25)
        cfg.planner.temperature: float - Generation temperature (default: 0.0)
        cfg.planner.max_tokens: int - Max tokens per generation (default: 500)
    """
```

### Core Method: react_step()

```python
def react_step(
    self,
    task_instruction: str,
    history: list[dict]
) -> tuple[str, str]:
    """
    Generate one ReAct step: a thought followed by an action.

    Args:
        task_instruction: Natural language task description
            (e.g., "Put a clean lettuce in diningtable")
        history: List of previous steps, each a dict with keys:
            - "thought": str (reasoning text)
            - "action": str (action command)
            - "observation": str (environment feedback)

    Returns:
        Tuple of (thought: str, action: str)
        - thought: Reasoning text (e.g., "I need to find a lettuce first...")
        - action: Parseable action command (e.g., "find a lettuce") or "done"

    Raises:
        ValueError: If LLM output cannot be parsed into thought + action
    """
```

### Overridden Methods

```python
def init_prompt(self, cfg) -> str:
    """
    Load ReAct-specific system prompt with few-shot examples.

    Returns: System prompt string containing:
        - Role description (robot in a home)
        - ReAct format explanation (Think/Act/Obs)
        - 1-2 few-shot examples per ALFRED task type
        - Available action vocabulary
    """

def init_skill_set(self) -> list[str]:
    """
    Return the ReAct action vocabulary (for reference/validation only).

    Unlike the base planner which scores against this list,
    the ReAct planner generates actions freely and validates
    against this list post-hoc.
    """
```

### Output Parsing

```python
def parse_react_output(self, llm_output: str) -> tuple[str, str]:
    """
    Parse LLM output into thought and action components.

    Expected LLM output format:
        "Think: [reasoning text]\nAct: [action command]"

    Args:
        llm_output: Raw text from LLM chat_completion()

    Returns:
        Tuple of (thought, action) strings

    Fallback behavior:
        - If only action found (no Think:), thought = ""
        - If only thought found (no Act:), raises ValueError
        - If neither found, treats entire output as action
    """
```

## Class: ReActAlfredEvaluator (extends AlfredEvaluator)

### Overridden Method: evaluate_task()

```python
def evaluate_task(
    self,
    env,           # ThorConnector instance
    traj_data,     # Task trajectory data dict
    r_idx,         # Repeat index
    model_args,    # Model arguments dict
    planner,       # ReActTaskPlanner instance
    save_path,     # Output directory path
    x_display      # X11 display string
) -> dict:
    """
    Evaluate a single task using the ReAct loop.

    Returns dict with keys:
        - trial: str (trial ID)
        - scene: str (scene name)
        - type: str (task type)
        - repeat_idx: int
        - goal_instr: str (task instruction)
        - success: bool
        - total_steps: int
        - termination_reason: str
        - reasoning_trace: list[dict] (full Think/Act/Obs history)
        - inferred_steps: list[str] (action sequence for compatibility)
    """
```

### New Method: construct_observation()

```python
def construct_observation(
    self,
    action_result: dict,
    env  # ThorConnector instance
) -> str:
    """
    Construct a natural language observation from action result and env state.

    Args:
        action_result: Dict from llm_skill_interact() with keys:
            - action: str
            - success: bool
            - message: str
        env: ThorConnector for querying current environment state

    Returns:
        Natural language observation string, e.g.:
        - "You picked up the lettuce."
        - "Action failed: could not find apple. Nothing matching was visible."
        - "You are now near the countertop. You see: a mug, a knife, a plate."
    """
```
