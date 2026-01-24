"""
Abstract base class for LLM providers.
Implements the Strategy Pattern for interchangeable LLM backends.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""
    model_name: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 500
    # Reasoning model settings (for o1, o3, gpt-5.x models)
    reasoning_effort: Optional[str] = None  # "low", "medium", "high"


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM providers (OpenAI, vLLM) must implement this interface.
    This enables the Strategy Pattern for swapping LLM backends without changing client code.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.model_name = config.model_name

    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate a chat completion response.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens to generate

        Returns:
            The generated text response
        """
        pass

    @abstractmethod
    def select_action(
        self,
        prompt: str,
        candidates: List[str]
    ) -> str:
        """
        Select the best action from a list of candidates.

        Args:
            prompt: The context/prompt for action selection
            candidates: List of candidate actions to choose from

        Returns:
            The selected action string
        """
        pass

    def _build_selection_messages(self, prompt: str, candidates: List[str]) -> List[Dict[str, str]]:
        """
        Build messages for action selection task.

        This is a helper method that can be used by all providers.
        """
        candidates_text = '\n'.join([f"{i+1}. {c}" for i, c in enumerate(candidates)])

        return [
            {
                "role": "system",
                "content": "You are a robot operating in a home. Given a partial action sequence, select the most appropriate next action from the provided list. Respond with ONLY the exact action text, nothing else."
            },
            {
                "role": "user",
                "content": f"{prompt}\n\nCandidate actions:\n{candidates_text}\n\nSelect the best next action from the candidates above. Respond with only the exact action text."
            }
        ]

    def _build_plan_messages(self, example_text: str, skills_text: str, query: str) -> List[Dict[str, str]]:
        """
        Build messages for whole-plan generation task.
        """
        return [
            {
                "role": "system",
                "content": "You are a robot operating in a home. A human user can ask you to do various tasks and you are supposed to tell the sequence of actions you would do to accomplish your task."
            },
            {
                "role": "user",
                "content": f"""Examples of human instructions and possible your (robot) answers:
{example_text}

Now please answer the sequence of actions for the input instruction.
You should use one of actions of this list: {skills_text}.
List the actions with comma separator.

Input user instruction:
{query}"""
            }
        ]
