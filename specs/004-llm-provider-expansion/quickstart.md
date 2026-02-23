# Quickstart: LLM Provider Expansion for Reasoning Models

**Branch**: `004-llm-provider-expansion`

## Prerequisites

- Python 3.10+
- `openai` Python package installed
- For local models: Ollama or LM Studio running with a model loaded

## Configuration Examples

### OpenAI Reasoning Models

```yaml
# conf/config_alfred_react.yaml
planner:
  provider: "openai"
  model_name: "gpt-5-mini"
  reasoning_effort: "low"
  max_tokens: 1024
  temperature: 0.0
```

Supported models: `gpt-5.2`, `gpt-5-mini`, `gpt-5-nano`

### Ollama (Local)

```bash
# Start Ollama and pull a model
ollama serve
ollama pull qwen3.5
```

```yaml
planner:
  provider: "ollama"
  model_name: "qwen3.5"
  max_tokens: 1024
  temperature: 0.6
```

Supported models: `qwen3.5`, `glm-5`, `kimi-k2.5` (any model available in Ollama)

### LM Studio (Local)

1. Open LM Studio, download and load a model
2. Start the local server (default: `localhost:1234`)

```yaml
planner:
  provider: "lmstudio"
  model_name: "kimi-k2.5"
  max_tokens: 1024
  temperature: 0.6
```

### Custom API Endpoint

```yaml
planner:
  provider: "ollama"
  model_name: "qwen3.5"
  api_base: "http://192.168.1.100:11434/v1"
  max_tokens: 1024
```

### Adding a New Reasoning Model

Add its prefix to the config — no code changes needed:

```yaml
planner:
  model_name: "deepseek-r1"
  reasoning_model_prefixes:
    - "gpt-5"
    - "o1"
    - "o3"
    - "o4"
    - "qwen3"
    - "glm-"
    - "kimi-k"
    - "deepseek-r"   # new prefix added here
```

## Running an Evaluation

```bash
# OpenAI gpt-5-mini on 1% of valid_seen
PYTHONPATH="alfred:src:$PYTHONPATH" python src/evaluate.py \
  --config-name=config_alfred_react \
  planner.provider=openai \
  planner.model_name=gpt-5-mini \
  planner.reasoning_effort=low \
  alfred.eval_portion_in_percent=1

# Ollama qwen3.5 on 5% of valid_seen
PYTHONPATH="alfred:src:$PYTHONPATH" python src/evaluate.py \
  --config-name=config_alfred_react \
  planner.provider=ollama \
  planner.model_name=qwen3.5 \
  alfred.eval_portion_in_percent=5
```

## Testing

```bash
# Run all unit tests (no live server needed)
PYTHONPATH="src:$PYTHONPATH" pytest tests/test_llm_providers.py -v

# Run integration tests (requires running server)
LMSTUDIO_TEST_BASE=http://localhost:1234/v1 \
LMSTUDIO_TEST_MODEL=kimi-k2.5 \
PYTHONPATH="src:$PYTHONPATH" pytest tests/test_llm_providers.py -v -m integration
```
