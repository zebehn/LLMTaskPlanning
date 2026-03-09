# Quickstart: ReAct Evaluation with Local Qwen3-8B

**Feature**: 001-local-transformers-provider
**Date**: 2026-03-05

## Prerequisites

1. **Hardware**: GPU with ≥16 GB VRAM (for bfloat16) or ≥32 GB VRAM (for float32).
   CPU-only mode is supported but will be significantly slower.

2. **Disk space**: ~16 GB free for Qwen3-8B model weights (downloaded on first run,
   cached to `~/.cache/huggingface/` by default).

3. **Dependencies installed**:
   ```bash
   pip install transformers>=4.51.0 torch>=2.0.0 accelerate>=0.26.0
   ```

4. **ALFRED data**: ALFRED dataset in `alfred/data/json_2.1.0/` (same as other eval modes).

---

## Running the ReAct Evaluation with Local Qwen3-8B

```bash
PYTHONPATH="alfred:src:$PYTHONPATH" python src/evaluate.py \
    --config-name=config_alfred_react_local
```

This runs with the default settings from `conf/config_alfred_react_local.yaml`:
- Model: `Qwen/Qwen3-8B` (downloaded and cached automatically on first run)
- Device: `auto` (uses all available GPUs)
- Evaluation set: `valid_seen`, 5% sample

---

## Overriding Settings at the Command Line

```bash
# Use a different local model
PYTHONPATH="alfred:src:$PYTHONPATH" python src/evaluate.py \
    --config-name=config_alfred_react_local \
    planner.model_name="Qwen/Qwen3-4B"

# Force CPU-only mode
PYTHONPATH="alfred:src:$PYTHONPATH" python src/evaluate.py \
    --config-name=config_alfred_react_local \
    planner.device_map="cpu"

# Use float16 instead of auto precision
PYTHONPATH="alfred:src:$PYTHONPATH" python src/evaluate.py \
    --config-name=config_alfred_react_local \
    planner.torch_dtype="float16"

# Evaluate on a larger portion
PYTHONPATH="alfred:src:$PYTHONPATH" python src/evaluate.py \
    --config-name=config_alfred_react_local \
    alfred.eval_portion_in_percent=20
```

---

## First-Run Model Download

On first run, the model is downloaded from HuggingFace (~16 GB). Progress is displayed:

```
Downloading model Qwen/Qwen3-8B...
config.json: 100%|████████████| 663/663 [00:00<00:00, 4.21kB/s]
model.safetensors.index.json: 100%|████████████| 28.7k/28.7k [...]
Downloading shards: 100%|████████████| 5/5 [04:23<00:00, ...]
Loading checkpoint shards: 100%|████████████| 5/5 [00:42<00:00, ...]
```

Subsequent runs load from cache and skip downloading.

---

## Verifying Output Compatibility

ReAct evaluation output is written to `outputs/alfred_react/<timestamp>/`.
The output format is identical to API-based runs:

```
outputs/alfred_react/
├── react_summary.json          # Aggregate success rate and metrics
├── task_pick_cool_0/
│   ├── result.json             # Per-task outcome
│   └── frames/                 # Optional: environment frames
└── ...
```

To compare results between local and API-based runs, point your analysis scripts
at both output directories — the schemas are identical.

---

## Running Tests

```bash
# Run all tests (unit tests only, no model download required)
pytest tests/test_transformers_provider.py -v

# Run full test suite (confirm no regressions)
pytest tests/ -v
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `OutOfMemoryError` during model load | Use `planner.torch_dtype="float16"` (saves ~8 GB vs float32) or switch to CPU fallback (see below) |
| `OutOfMemoryError` on GPU with float16 | Fall back to CPU: `planner.device_map=cpu planner.torch_dtype=float32` — slow but works on any machine |
| `ModuleNotFoundError: accelerate` | Run `pip install accelerate>=0.26.0` |
| `ModuleNotFoundError: torch` | Run `pip install torch>=2.0.0 --index-url https://download.pytorch.org/whl/cu124` |
| `ModuleNotFoundError: transformers` | Run `pip install transformers>=4.51.0` |
| Model download stalls | Check internet connection; set `HF_HUB_OFFLINE=1` to use cached weights only |
| `ValueError: Unknown provider type: transformers` | `TransformersProvider` not registered; verify `src/llm/factory.py` has `"transformers"` key |
| Slow inference on CPU | Expected; Qwen3-8B requires ~32 GB RAM and is 10-100× slower than GPU |

### CPU Fallback (confirmed CLI flags)

```bash
PYTHONPATH="alfred:src:$PYTHONPATH" python src/evaluate.py \
    --config-name=config_alfred_react_local \
    planner.device_map=cpu \
    planner.torch_dtype=float32
```

This forces all computation to CPU with 32-bit precision. Suitable for machines without a GPU
or when VRAM is insufficient for the model.
