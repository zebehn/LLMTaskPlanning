"""ReAct-style task planner for ALFRED household tasks.

Implements the ReAct paradigm (Yao et al., ICLR 2023) that interleaves
Thought-Action-Observation steps using free-form LLM generation via
chat_completion() rather than constrained action selection.
"""

import json
import logging
import os
import re

from src.task_planner import TaskPlanner
from llm import LLMProviderFactory

log = logging.getLogger(__name__)


def sanitize_llm_output(text: str) -> str:
    """Sanitize raw LLM output by stripping control tokens and degenerate text.

    - Strips ``<think>...</think>`` reasoning-model thinking blocks
      (e.g. DeepSeek-R1, QwQ).
    - Strips ``<|...|>`` control tokens (e.g. from LM Studio models).
    - Collapses runs of 10+ repeated non-alphanumeric characters to 3,
      preventing ``@@@`` degeneration loops.
    """
    # Strip <think>...</think> blocks from reasoning models (DOTALL for newlines)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Strip orphaned opening <think> with no closing tag (model truncated mid-thought)
    text = re.sub(r'<think>.*', '', text, flags=re.DOTALL)
    # Strip control tokens like <|channel|>, <|constrain|>, <|message|>
    text = re.sub(r'<\|[^|]*\|>', '', text)
    # Collapse 10+ repeats of the same non-alphanumeric char to 3
    text = re.sub(r'([^\w])\1{9,}', r'\1\1\1', text)
    return text.strip()


def _extract_json_value(text: str, key: str) -> str | None:
    """Extract a string value for *key* from possibly-broken JSON text.

    Uses regex to find ``"key"\\s*:\\s*"value"`` even when the outer braces
    or other keys are malformed / missing.  Returns ``None`` if not found.
    """
    pattern = rf'"{re.escape(key)}"\s*:\s*"((?:[^"\\]|\\.)*)"'
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return m.group(1) if m else None


def parse_react_output(llm_output: str) -> tuple:
    """Parse LLM output into thought and action components.

    Tries JSON extraction first, then falls back to text-based parsing.

    JSON format (preferred):
        ``{"Think": "reasoning", "Act": "action command"}``

    Text format (backward-compatible fallback):
        ``Think: reasoning\\nAct: action command``

    Returns:
        Tuple of (thought, action) strings

    Fallback behavior:
        - If only action found (no Think:), thought = ""
        - If only thought found (no Act:), raises ValueError
        - If neither found, treats entire output as action
    """
    text = sanitize_llm_output(llm_output)

    # --- JSON-first extraction (complete JSON) ---
    # Find the outermost {...} in the text
    match = re.search(r'\{[^{}]*\}', text)
    if match:
        try:
            data = json.loads(match.group())
            # Case-insensitive key lookup
            lower_keys = {k.lower(): v for k, v in data.items()}
            if 'think' in lower_keys and 'act' in lower_keys:
                thought = str(lower_keys['think']).strip()
                action = str(lower_keys['act']).strip()
                action = action.split('\n', 1)[0].strip()
                return thought, action
        except (json.JSONDecodeError, ValueError):
            pass

    # --- Broken-JSON extraction (incomplete / malformed JSON) ---
    # The model may have started a JSON object but degenerated before
    # closing it.  Try to extract "Think" and "Act" values via regex.
    if '{' in text:
        act_val = _extract_json_value(text, 'Act')
        if act_val:
            think_val = _extract_json_value(text, 'Think') or ""
            action = act_val.split('\n', 1)[0].strip()
            return think_val.strip(), action

    # --- Text-based fallback ---
    has_think = "Think:" in text
    has_act = "Act:" in text

    if has_think and has_act:
        think_idx = text.index("Think:")
        act_idx = text.index("Act:")
        thought = text[think_idx + len("Think:"):act_idx].strip()
        action = text[act_idx + len("Act:"):].strip()
        action = action.split('\n', 1)[0].strip()
        return thought, action

    elif has_act and not has_think:
        act_idx = text.index("Act:")
        action = text[act_idx + len("Act:"):].strip()
        action = action.split('\n', 1)[0].strip()
        return "", action

    elif has_think and not has_act:
        raise ValueError("No Act: found in LLM output. Cannot extract action.")

    else:
        return "", text.split('\n', 1)[0].strip()


class ReActTaskPlanner(TaskPlanner):
    """ReAct planner that generates Thought-Action pairs via chat_completion().

    Unlike AlfredTaskPlanner which uses constrained select_action(),
    this planner generates free-form reasoning and actions using the
    ReAct (Reasoning + Acting) paradigm.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.max_steps = cfg.planner.max_steps
        self.model_name = cfg.planner.model_name
        self.temperature = getattr(cfg.planner, 'temperature', 0.0)
        self.max_tokens = getattr(cfg.planner, 'max_tokens', 1024)

        # Initialize LLM provider
        log.info(f"Loading LLM for ReAct planner: {self.model_name}")
        self.llm = LLMProviderFactory.from_config(cfg)
        log.info(f"Provider: {type(self.llm).__name__}")

        # Load prompts
        self.system_prompt = self.init_prompt(cfg)
        self.few_shot_examples = self._load_few_shot_examples(cfg)
        self.skill_set = self.init_skill_set()

        # Kept for compatibility with base class
        self.prompt = self.system_prompt

    def init_prompt(self, cfg) -> str:
        """Load ReAct system prompt from template file."""
        prompt_path = cfg.prompt.react_system_prompt
        # Try multiple paths for flexibility
        for path in [prompt_path, os.path.join('src/prompts/templates', 'react_system.txt')]:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return f.read()
        log.warning(f"ReAct system prompt not found at {prompt_path}, using empty prompt")
        return ""

    def _load_few_shot_examples(self, cfg) -> str:
        """Load ReAct few-shot examples from template file."""
        prompt_path = cfg.prompt.react_few_shot_examples
        for path in [prompt_path, os.path.join('src/prompts/templates', 'react_few_shot_examples.txt')]:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return f.read()
        log.warning(f"ReAct few-shot examples not found at {prompt_path}, using empty examples")
        return ""

    def init_skill_set(self) -> list:
        """Return the ReAct action vocabulary for reference/validation only.

        Unlike the base planner which scores against this list,
        the ReAct planner generates actions freely and validates
        against this list post-hoc.
        """
        return [
            'find', 'pick up', 'put down', 'drop', 'open', 'close',
            'turn on', 'turn off', 'slice', 'done'
        ]

    def react_step(self, task_instruction: str, history: list,
                   available_objects: list[str] = None) -> tuple:
        """Generate one ReAct step: a thought followed by an action.

        Args:
            task_instruction: Natural language task description
            history: List of previous steps, each a dict with keys:
                - "thought": str
                - "action": str
                - "observation": str
            available_objects: Optional sorted list of unique object type names
                present in the current scene (e.g. ["Apple", "Fridge", "Mug"]).

        Returns:
            Tuple of (thought: str, action: str)

        Raises:
            ValueError: If max_steps exceeded or LLM output cannot be parsed
        """
        if len(history) >= self.max_steps:
            raise ValueError(f"Max steps ({self.max_steps}) reached")

        messages = self._build_messages(task_instruction, history,
                                        available_objects=available_objects)

        raw_response = self.llm.chat_completion(
            messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        log.info("Raw LLM response: %s", raw_response[:200])
        response = sanitize_llm_output(raw_response)
        log.debug("Sanitized LLM response: %s", response)

        thought, action = parse_react_output(response)

        # Validate: action must start with a known verb or be "done".
        # This prevents degenerate / garbage text from entering history.
        if not self._is_valid_action(action):
            log.warning("Malformed action rejected: %s", action[:120])
            raise ValueError(
                f"LLM produced an unparseable action: {action[:120]!r}"
            )

        return thought, action

    def _is_valid_action(self, action: str) -> bool:
        """Return True if *action* starts with a recognised action verb."""
        a = action.strip().lower()
        return any(a.startswith(verb) for verb in self.skill_set)

    def _build_messages(self, task_instruction: str, history: list,
                        available_objects: list[str] = None) -> list:
        """Build the message list for chat_completion().

        Uses multi-turn format so the model naturally generates only one
        Think+Act pair before waiting for the next Obs from the user turn.

        Structure:
            1. System message: role description + format instructions
               (+ available objects if provided)
            2. User message: few-shot examples + task instruction
            3. For each history step:
               - Assistant message: JSON {"Think": ..., "Act": ...}
               - User message: Obs: ...
        """
        system_content = self.system_prompt
        if available_objects:
            system_content += (
                "\n\nAvailable objects in this scene: "
                + ", ".join(available_objects)
            )
        messages = [
            {"role": "system", "content": system_content}
        ]

        # First user message: few-shot examples + current task
        user_content = self.few_shot_examples + "\n"
        user_content += f"Task: {task_instruction}"
        messages.append({"role": "user", "content": user_content})

        # Each history step becomes assistant (JSON Think+Act) then user (Obs)
        for step in history:
            entry = {}
            if step.get('thought'):
                entry['Think'] = step['thought']
            if step.get('action'):
                entry['Act'] = step['action']
            messages.append({"role": "assistant", "content": json.dumps(entry)})

            if step.get('observation'):
                messages.append({"role": "user", "content": f"Obs: {step['observation']}"})

        return messages
