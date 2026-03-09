# Data Model: Local Transformers Provider

**Feature**: 001-local-transformers-provider
**Date**: 2026-03-05

## Entities

### LLMConfig (extended)

Existing dataclass in `src/llm/base.py`. Two new optional fields are added:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `model_name` | `str` | (required) | HuggingFace model ID (e.g., `"Qwen/Qwen3-8B"`) |
| `api_key` | `Optional[str]` | `None` | Unused by TransformersProvider; kept for ABC compatibility |
| `api_base` | `Optional[str]` | `None` | Unused by TransformersProvider; kept for ABC compatibility |
| `temperature` | `float` | `0.0` | Sampling temperature; `0.0` → greedy decoding |
| `max_tokens` | `int` | `500` | Max new tokens to generate |
| `reasoning_effort` | `Optional[str]` | `None` | Unused by TransformersProvider |
| `reasoning_model_prefixes` | `Tuple[str, ...]` | `(...)` | Used by `is_reasoning_model()` |
| **`device_map`** | `str` | `"auto"` | **NEW** — device placement strategy (`"auto"`, `"cpu"`, `"cuda:0"`) |
| **`torch_dtype`** | `str` | `"auto"` | **NEW** — model precision (`"auto"`, `"float16"`, `"bfloat16"`, `"float32"`) |

**Validation rules**:
- `device_map` MUST be one of `"auto"`, `"cpu"`, `"cuda"`, or a valid CUDA device string
  (e.g., `"cuda:0"`). Invalid values raise `ValueError` before model loading begins.
- `torch_dtype` MUST be one of `"auto"`, `"float16"`, `"bfloat16"`, `"float32"`.
  Invalid values raise `ValueError` before model loading begins.

---

### TransformersProvider

New class in `src/llm/transformers_provider.py`.

**State** (instance variables):

| Attribute | Type | Set in | Description |
|-----------|------|--------|-------------|
| `config` | `LLMConfig` | `__init__` | Full config (inherited from LLMProvider) |
| `model_name` | `str` | `__init__` | HuggingFace model ID (inherited) |
| `tokenizer` | `AutoTokenizer` | `__init__` | Loaded tokenizer for the model |
| `model` | `AutoModelForCausalLM` | `__init__` | Loaded model weights on device |

**Lifecycle**:
1. `__init__`: validates config, loads tokenizer, loads model to device(s)
2. `chat_completion()`: formats messages → generates text → decodes → returns str
3. `select_action()`: delegates to `chat_completion()` via `_build_selection_messages()`

---

### Hydra Config (new file)

**File**: `conf/config_alfred_react_local.yaml`

```yaml
name: alfred_react

defaults:
  - hydra: default.yaml
  - planner: default.yaml
  - override hydra/help: custom
  - _self_

out_dir: ${hydra:run.dir}

planner:
  provider: "transformers"
  model_name: "Qwen/Qwen3-8B"
  device_map: "auto"
  torch_dtype: "auto"
  max_steps: 25
  temperature: 0.0
  max_tokens: 1024

prompt:
  react_system_prompt: "src/prompts/templates/react_system.txt"
  react_few_shot_examples: "src/prompts/templates/react_few_shot_examples.txt"

alfred:
  x_display: '0'
  eval_set: 'valid_seen'
  eval_portion_in_percent: 5
  random_seed_for_eval_subset: 1
  stratified_sampling: false
  validation_report: ""
  skip_categories: [1]
```

---

### Factory Registration

**File**: `src/llm/factory.py` — `PROVIDERS` dict change:

```python
PROVIDERS = {
    "openai": OpenAIProvider,
    "vllm": VLLMProvider,
    "ollama": OllamaProvider,
    "lmstudio": LMStudioProvider,
    "transformers": TransformersProvider,  # NEW
}
```

**`from_config()` additions** — reads two new fields from `planner_cfg`:
```python
device_map = getattr(planner_cfg, 'device_map', 'auto')
torch_dtype = getattr(planner_cfg, 'torch_dtype', 'auto')
```
These are passed to `cls.create()` and forwarded to `LLMConfig`.

---

### Evaluation Result (unchanged)

Existing schema from `react_evaluator.py` output. No changes required — `TransformersProvider`
returns a plain `str` from `chat_completion()`, identical to all other providers.

---

## State Transitions

### TransformersProvider initialization

```
Config provided
    │
    ▼
Validate device_map, torch_dtype
    │ invalid → ValueError (before any model loading)
    ▼
Load tokenizer (AutoTokenizer.from_pretrained)
    │ network/disk error → propagate exception with clear message
    ▼
Load model (AutoModelForCausalLM.from_pretrained)
    │ OOM error → propagate RuntimeError
    ▼
Provider ready for inference
```

### chat_completion() call

```
messages: List[Dict]
    │
    ▼
apply_chat_template(messages, enable_thinking=False)
    │
    ▼
tokenize → input_ids on device
    │
    ▼
model.generate(input_ids, max_new_tokens, do_sample, temperature)
    │
    ▼
decode output_ids (skip input tokens)
    │
    ▼
strip() → return str
```
