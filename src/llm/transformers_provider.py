"""Local model provider using HuggingFace transformers library."""
from typing import List, Dict, Optional

from .base import LLMProvider, LLMConfig

_VALID_TORCH_DTYPES = {"auto", "float16", "bfloat16", "float32"}


class TransformersProvider(LLMProvider):
    """
    LLM Provider for locally-hosted models via the transformers library.

    Supports any HuggingFace causal language model (e.g., Qwen/Qwen3-8B).
    Model weights are loaded once at initialization and reused for all calls.
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)

        if config.torch_dtype not in _VALID_TORCH_DTYPES:
            raise ValueError(
                f"Invalid torch_dtype: '{config.torch_dtype}'. "
                f"Must be one of: {sorted(_VALID_TORCH_DTYPES)}"
            )

        # Lazy import so the module loads without transformers installed
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(config.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            config.model_name,
            device_map=config.device_map,
            torch_dtype=config.torch_dtype,
        )

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate a response by running local inference."""
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )

        inputs = self.tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"].to(self.model.device)
        input_len = input_ids.shape[1]

        generate_kwargs = {"max_new_tokens": max_tok}
        if temp <= 0.0:
            generate_kwargs["do_sample"] = False
        else:
            generate_kwargs["do_sample"] = True
            generate_kwargs["temperature"] = temp

        output_ids = self.model.generate(input_ids, **generate_kwargs)
        new_tokens = output_ids[0][input_len:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    def select_action(self, prompt: str, candidates: List[str]) -> str:
        """Select best action using local inference."""
        messages = self._build_selection_messages(prompt, candidates)
        return self.chat_completion(messages, temperature=0, max_tokens=100)
