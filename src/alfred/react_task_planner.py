"""ReAct-style task planner for ALFRED household tasks.

Implements the ReAct paradigm (Yao et al., ICLR 2023) that interleaves
Thought-Action-Observation steps using free-form LLM generation via
chat_completion() rather than constrained action selection.
"""

import logging
import os

from src.task_planner import TaskPlanner
from llm import LLMProviderFactory

log = logging.getLogger(__name__)


def parse_react_output(llm_output: str) -> tuple:
    """Parse LLM output into thought and action components.

    Expected LLM output format:
        "Think: [reasoning text]\\nAct: [action command]"

    Returns:
        Tuple of (thought, action) strings

    Fallback behavior:
        - If only action found (no Think:), thought = ""
        - If only thought found (no Act:), raises ValueError
        - If neither found, treats entire output as action
    """
    text = llm_output.strip()

    has_think = "Think:" in text
    has_act = "Act:" in text

    if has_think and has_act:
        # Standard format: Think: ... Act: ...
        think_idx = text.index("Think:")
        act_idx = text.index("Act:")
        thought = text[think_idx + len("Think:"):act_idx].strip()
        action = text[act_idx + len("Act:"):].strip()
        # Only take the first line -- LLM may hallucinate future Obs/Think/Act
        action = action.split('\n', 1)[0].strip()
        return thought, action

    elif has_act and not has_think:
        # Fallback: only Act present
        act_idx = text.index("Act:")
        action = text[act_idx + len("Act:"):].strip()
        action = action.split('\n', 1)[0].strip()
        return "", action

    elif has_think and not has_act:
        # Error: only Think present
        raise ValueError("No Act: found in LLM output. Cannot extract action.")

    else:
        # Neither found: treat entire output as action
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
            'find', 'pick up', 'put down', 'open', 'close',
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

        response = self.llm.chat_completion(
            messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        thought, action = parse_react_output(response)
        return thought, action

    def _build_messages(self, task_instruction: str, history: list,
                        available_objects: list[str] = None) -> list:
        """Build the message list for chat_completion().

        Uses multi-turn format so the model naturally generates only one
        Think+Act pair before waiting for the next Obs from the user turn.

        Structure:
            1. System message: role description + format instructions
            2. User message: few-shot examples + task instruction
               (+ available objects if provided)
            3. For each history step:
               - Assistant message: Think: ... / Act: ...
               - User message: Obs: ...
        """
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]

        # First user message: few-shot examples + current task
        user_content = self.few_shot_examples + "\n"
        user_content += f"Task: {task_instruction}"
        if available_objects:
            user_content += (
                "\nAvailable objects in this scene: "
                + ", ".join(available_objects)
            )
        messages.append({"role": "user", "content": user_content})

        # Each history step becomes assistant (Think+Act) then user (Obs)
        for step in history:
            assistant_msg = ""
            if step.get('thought'):
                assistant_msg += f"Think: {step['thought']}\n"
            if step.get('action'):
                assistant_msg += f"Act: {step['action']}"
            messages.append({"role": "assistant", "content": assistant_msg})

            if step.get('observation'):
                messages.append({"role": "user", "content": f"Obs: {step['observation']}"})

        return messages
