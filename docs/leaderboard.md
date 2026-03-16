# LoTa-Bench Leaderboard

Results of ReAct-based task planning evaluations on ALFRED.
Each row links to a detailed report with per-task-type breakdown.

---

## Main Leaderboard

| # | Model | Eval Mode | Split | Sample | Success | Rate | Avg Steps | Date | Report |
|---|-------|-----------|-------|--------|---------|------|-----------|------|--------|
| 1 | [gpt-5.2](#exp-3-gpt-52--react--valid_seen--30pct) | ReAct | valid_seen | 30% | 110 / 204 | **53.92%** | 12.5 | 2026-03-09 | [details](#exp-3-gpt-52--react--valid_seen--30pct) |
| 2 | [Qwen/Qwen3.5-9B+fixes](#exp-5-qwen35-9b-fixes--react--valid_seen--30pct) | ReAct | valid_seen | 30% | 94 / 204 | **46.08%** | 13.9 | 2026-03-14 | [details](#exp-5-qwen35-9b-fixes--react--valid_seen--30pct) |
| 3 | [Qwen/Qwen3.5-9B](#exp-4-qwen35-9b--react--valid_seen--30pct) | ReAct | valid_seen | 30% | 87 / 204 | 42.65% | 12.9 | 2026-03-10 | [details](#exp-4-qwen35-9b--react--valid_seen--30pct) |
| 4 | [Qwen/Qwen3.5-9B+fixes](#exp-6-qwen35-9b-fixes--react--valid_seen--5pct) | ReAct | valid_seen | 5% | 14 / 33 | 42.42% | 13.9 | 2026-03-13 | [details](#exp-6-qwen35-9b-fixes--react--valid_seen--5pct) |
| 5 | [Qwen/Qwen3-8B+fixes](#exp-7-qwen3-8b-fixes--react--valid_seen--5pct) | ReAct | valid_seen | 5% | 11 / 33 | 33.33% | 17.1 | 2026-03-13 | [details](#exp-7-qwen3-8b-fixes--react--valid_seen--5pct) |
| 6 | [Qwen/Qwen3-8B](#exp-2-qwen3-8b--react--valid_seen--30pct) | ReAct | valid_seen | 30% | 62 / 204 | 30.39% | 14.8 | 2026-03-09 | [details](#exp-2-qwen3-8b--react--valid_seen--30pct) |
| 7 | [Qwen/Qwen3-8B](#exp-1-qwen3-8b--react--valid_seen--5pct) | ReAct | valid_seen | 5% | 7 / 33 | 21.21% | 15.8 | 2026-03-05 | [details](#exp-1-qwen3-8b--react--valid_seen--5pct) |

> Sorted by success rate. Add new rows as experiments are completed.
> **Sample** = `alfred.eval_portion_in_percent` setting.
> All ReAct runs use `max_steps=25`, `temperature=0.0`.

---

## Experiment Details

---

### Exp 5: Qwen3.5-9B+fixes · ReAct · valid_seen · 30pct

**Date**: 2026-03-14
**Model**: `Qwen/Qwen3.5-9B` (local HuggingFace, bfloat16)
**Hardware**: 1× NVIDIA H200 NVL 141GB
**Config**: `conf/config_alfred_react_local.yaml`, `planner.model_name=Qwen/Qwen3.5-9B`, `alfred.eval_portion_in_percent=30`, `CUDA_VISIBLE_DEVICES=5`
**Wall time**: 8 h 0 min 47 s
**Fixes applied**: instance-label observations, `cur_receptacle` tracking, slice registry remap, stale `lastActionSuccess`, system prompt clarification, new few-shot example (slice+movable_recep)

#### Overall Results

| Metric | Value |
|--------|-------|
| Tasks evaluated | 204 |
| Tasks succeeded | 94 |
| **Success rate** | **46.08%** |
| Average steps (all) | 13.9 |

#### Results by Task Type

| Task Type | Success | Total | Rate |
|-----------|---------|-------|------|
| `pick_heat_then_place_in_recep` | 21 | 34 | **61.8%** |
| `look_at_obj_in_light` | 10 | 15 | **66.7%** |
| `pick_and_place_simple` | 27 | 51 | **52.9%** |
| `pick_cool_then_place_in_recep` | 19 | 39 | 48.7% |
| `pick_clean_then_place_in_recep` | 11 | 32 | 34.4% |
| `pick_and_place_with_movable_recep` | 6 | 33 | 18.2% |

Full report: `outputs/alfred_react/2026-03-13_19-36-48/evaluation_report.md`

---

### Exp 6: Qwen3.5-9B+fixes · ReAct · valid_seen · 5pct

**Date**: 2026-03-13
**Model**: `Qwen/Qwen3.5-9B` (local HuggingFace, bfloat16)
**Hardware**: 2× NVIDIA A100 80GB
**Config**: `conf/config_alfred_react_local.yaml`, `planner.model_name=Qwen/Qwen3.5-9B`, `alfred.eval_portion_in_percent=5`, `CUDA_VISIBLE_DEVICES=0,6`
**Wall time**: 1 h 57 min 46 s
**Fixes applied**: same as Exp 5

#### Overall Results

| Metric | Value |
|--------|-------|
| Tasks evaluated | 33 |
| Tasks succeeded | 14 |
| **Success rate** | **42.42%** |
| Average steps (all) | 13.9 |
| Termination: done_signal | 14 (73.7%) |
| Termination: max_steps | 3 (15.8%) |
| Termination: malformed_output | 2 (10.5%) |

#### Results by Task Type

| Task Type | Success | Total | Rate |
|-----------|---------|-------|------|
| `pick_and_place_simple` | 5 | 10 | **50.0%** |
| `pick_heat_then_place_in_recep` | 2 | 4 | **50.0%** |
| `pick_clean_then_place_in_recep` | 4 | 8 | 50.0% |
| `pick_and_place_with_movable_recep` | 3 | 7 | 42.9% |
| `pick_cool_then_place_in_recep` | 0 | 4 | 0.0% |

Full report: `outputs/alfred_react/2026-03-13_09-44-13/evaluation_report.md`

---

### Exp 7: Qwen3-8B+fixes · ReAct · valid_seen · 5pct

**Date**: 2026-03-13
**Model**: `Qwen/Qwen3-8B` (local HuggingFace, bfloat16)
**Hardware**: 2× NVIDIA A100 80GB
**Config**: `conf/config_alfred_react_local.yaml`, `alfred.eval_portion_in_percent=5`, `CUDA_VISIBLE_DEVICES=0,6`
**Wall time**: 1 h 16 min 17 s
**Fixes applied**: same as Exp 5

#### Overall Results

| Metric | Value |
|--------|-------|
| Tasks evaluated | 33 |
| Tasks succeeded | 11 |
| **Success rate** | **33.33%** |
| Average steps (all) | 17.1 |
| Termination: done_signal | 15 (68.2%) |
| Termination: max_steps | 7 (31.8%) |

#### Results by Task Type

| Task Type | Success | Total | Rate |
|-----------|---------|-------|------|
| `pick_clean_then_place_in_recep` | 5 | 8 | **62.5%** |
| `pick_and_place_with_movable_recep` | 2 | 7 | **28.6%** |
| `pick_and_place_simple` | 3 | 10 | 30.0% |
| `pick_heat_then_place_in_recep` | 1 | 4 | 25.0% |
| `pick_cool_then_place_in_recep` | 0 | 4 | 0.0% |

Full report: `outputs/alfred_react/2026-03-12_22-44-12/evaluation_report.md`

---

### Exp 3: gpt-5.2 · ReAct · valid_seen · 30pct

**Date**: 2026-03-09
**Model**: `gpt-5.2` (OpenAI API)
**Config**: `conf/config_alfred_react.yaml`, `alfred.eval_portion_in_percent=30`
**Wall time**: 3 h 47 min 43 s

#### Overall Results

| Metric | Value |
|--------|-------|
| Tasks evaluated | 204 |
| Tasks succeeded | 110 |
| **Success rate** | **53.92%** |
| Average steps (all) | 12.5 |
| Average steps (success) | 11.4 |
| Average steps (failure) | 13.9 |
| Action-level success | 88.5% (2092 / 2364) |
| Termination: done_signal | 191 (93.6%) |
| Termination: max_steps | 13 (6.4%) |
| Termination: malformed_output | 0 (0.0%) |

#### Results by Task Type

| Task Type | Success | Total | Rate |
|-----------|---------|-------|------|
| `look_at_obj_in_light` | 11 | 15 | **73.3%** |
| `pick_heat_then_place_in_recep` | 21 | 34 | **61.8%** |
| `pick_cool_then_place_in_recep` | 23 | 39 | **59.0%** |
| `pick_and_place_simple` | 30 | 51 | **58.8%** |
| `pick_clean_then_place_in_recep` | 16 | 32 | **50.0%** |
| `pick_and_place_with_movable_recep` | 9 | 33 | 27.3% |

Full report: `outputs/alfred_react/2026-03-09_19-42-39/evaluation_report.md`

---

### Exp 4: Qwen3.5-9B · ReAct · valid_seen · 30pct

**Date**: 2026-03-10
**Model**: `Qwen/Qwen3.5-9B` (local HuggingFace, bfloat16)
**Hardware**: 2× NVIDIA A100 80GB
**Config**: `conf/config_alfred_react_local.yaml`, `planner.model_name=Qwen/Qwen3.5-9B`, `alfred.eval_portion_in_percent=30`
**Wall time**: 6 h 20 min 43 s

#### Overall Results

| Metric | Value |
|--------|-------|
| Tasks evaluated | 204 |
| Tasks succeeded | 87 |
| **Success rate** | **42.65%** |
| Average steps (all) | 12.9 |
| Average steps (success) | 10.3 |
| Average steps (failure) | 14.8 |
| Action-level success | 80.4% (1971 / 2453) |
| Termination: done_signal | 169 (82.8%) |
| Termination: max_steps | 29 (14.2%) |
| Termination: malformed_output | 6 (2.9%) |

#### Results by Task Type

| Task Type | Success | Total | Rate |
|-----------|---------|-------|------|
| `look_at_obj_in_light` | 11 | 15 | **73.3%** |
| `pick_and_place_simple` | 29 | 51 | **56.9%** |
| `pick_cool_then_place_in_recep` | 20 | 39 | **51.3%** |
| `pick_clean_then_place_in_recep` | 12 | 32 | 37.5% |
| `pick_heat_then_place_in_recep` | 13 | 34 | 38.2% |
| `pick_and_place_with_movable_recep` | 2 | 33 | 6.1% |

Full report: `outputs/alfred_react/2026-03-09_23-44-11/evaluation_report.md`

---

### Exp 2: Qwen3-8B · ReAct · valid_seen · 30pct

**Date**: 2026-03-09
**Model**: `Qwen/Qwen3-8B` (local HuggingFace, bfloat16)
**Hardware**: 2× NVIDIA A100 80GB
**Config**: `conf/config_alfred_react_local.yaml`, `alfred.eval_portion_in_percent=30`
**Wall time**: 6 h 14 min 11 s

#### Overall Results

| Metric | Value |
|--------|-------|
| Tasks evaluated | 204 |
| Tasks succeeded | 62 |
| **Success rate** | **30.39%** |
| Average steps (all) | 14.8 |
| Average steps (success) | 11.6 |
| Average steps (failure) | 16.2 |
| Action-level success | 68.7% (1971 / 2870) |
| Termination: done_signal | 150 (73.5%) |
| Termination: max_steps | 49 (24.0%) |
| Termination: malformed_output | 5 (2.5%) |

#### Results by Task Type

| Task Type | Success | Total | Rate |
|-----------|---------|-------|------|
| `pick_cool_then_place_in_recep` | 18 | 39 | **46.2%** |
| `pick_clean_then_place_in_recep` | 11 | 32 | **34.4%** |
| `look_at_obj_in_light` | 5 | 15 | **33.3%** |
| `pick_and_place_simple` | 16 | 51 | 31.4% |
| `pick_heat_then_place_in_recep` | 10 | 34 | 29.4% |
| `pick_and_place_with_movable_recep` | 2 | 33 | 6.1% |

Full report: `outputs/alfred_react/2026-03-09_11-51-45/evaluation_report.md`

---

### Exp 1: Qwen3-8B · ReAct · valid_seen · 5pct

**Date**: 2026-03-05
**Model**: `Qwen/Qwen3-8B` (local HuggingFace, bfloat16)
**Hardware**: 2× NVIDIA A100 80GB
**Config**: `conf/config_alfred_react_local.yaml` (default 5%)
**Wall time**: 1 h 33 min 20 s

#### Overall Results

| Metric | Value |
|--------|-------|
| Tasks evaluated | 33 |
| Tasks succeeded | 7 |
| **Success rate** | **21.21%** |
| Average steps (all) | 15.8 |
| Average steps (success) | 12.6 |
| Average steps (failure) | 16.7 |
| Action-level success | 63.1% (316 / 501) |
| Termination: done_signal | 21 (80.8%) |
| Termination: max_steps | 10 (38.5%) |
| Termination: malformed_output | 2 (7.7%) |

#### Results by Task Type

| Task Type | Success | Total | Rate |
|-----------|---------|-------|------|
| `pick_heat_then_place_in_recep` | 2 | 4 | **50.0%** |
| `pick_clean_then_place_in_recep` | 3 | 8 | **37.5%** |
| `pick_and_place_simple` | 2 | 10 | 20.0% |
| `pick_cool_then_place_in_recep` | 0 | 4 | 0.0% |
| `pick_and_place_with_movable_recep` | 0 | 7 | 0.0% |

Full report: `outputs/alfred_react/2026-03-05_16-28-07/evaluation_report.md`
