"""
Abstract base class for LLM providers.
Implements the Strategy Pattern for interchangeable LLM backends.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from prompts import PromptLoader, get_prompt_loader


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""
    model_name: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 500
    # Local model settings (for TransformersProvider)
    device_map: str = "auto"
    torch_dtype: str = "auto"
    # Reasoning model settings (for o1, o3, gpt-5.x models)
    reasoning_effort: Optional[str] = None  # "low", "medium", "high"
    # Model name prefixes that identify reasoning models
    reasoning_model_prefixes: Tuple[str, ...] = (
        "gpt-5", "o1", "o3", "o4", "qwen3", "glm-", "kimi-k"
    )


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM providers (OpenAI, vLLM) must implement this interface.
    This enables the Strategy Pattern for swapping LLM backends without changing client code.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.model_name = config.model_name
        self.prompt_loader = get_prompt_loader()

    def is_reasoning_model(self) -> bool:
        """Check if the current model is a reasoning model based on prefix matching.

        Handles both plain names (e.g., 'gpt-5') and HuggingFace namespace/model
        format (e.g., 'Qwen/Qwen3-8B') by checking both the full name and the
        part after '/' case-insensitively.
        """
        names = [self.model_name.lower()]
        if "/" in self.model_name:
            names.append(self.model_name.split("/", 1)[1].lower())
        return any(
            name.startswith(p.lower())
            for name in names
            for p in self.config.reasoning_model_prefixes
        )

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
        return self.prompt_loader.get_action_selection_messages(prompt, candidates)

    def _build_plan_messages(self, example_text: str, skills_text: str, query: str) -> List[Dict[str, str]]:
        """
        Build messages for whole-plan generation task.
        """
        return self.prompt_loader.get_plan_generation_messages(example_text, skills_text, query)
