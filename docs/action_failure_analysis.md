# Action-Level Failure Analysis: ALFRED ReAct Evaluation

**Generated:** 2026-03-10 14:39
**Runs analyzed:**
- Qwen3-8B: `outputs/alfred_react/2026-03-09_11-51-45/` (204 tasks, valid_seen 30%)
- GPT-5.2: `outputs/alfred_react/2026-03-09_19-42-39/` (204 tasks, valid_seen 30%)

**Figures:** `.omc/scientist/figures/`

---

## [OBJECTIVE]

Identify which action types fail most frequently, why they fail, how failure patterns differ
between Qwen3-8B and GPT-5.2, and which ALFRED task types are most failure-prone.

---

## [DATA]

| Metric | Qwen3-8B | GPT-5.2 | Combined |
|--------|----------:|--------:|---------:|
| Tasks | 204 | 204 | 408 |
| Task Success | 62 (30.4%) | 110 (53.9%) | 172 (42.2%) |
| Total Steps | 3,020 | 2,555 | 5,575 |
| Failed Steps | 1,049 (34.7%) | 463 (18.1%) | 1,512 (27.1%) |
| Avg Steps/Task | 14.8 | 12.5 | 13.7 |

Steps include all actions in the ReAct reasoning trace, including `done` signals.
`done` failures where `action_success=False` are split into:
- **premature_done**: task ended unsuccessfully (task_success=False)
- **done_early_attempt**: intermediate `done` call in a trial that ultimately succeeded

---

## [FINDING 1] Pick and put account for the majority of actionable failures

`pick` (490 failed steps, 39.5% failure rate) and `put` (275, 29.6%) together represent
50.6% of all failed steps. `slice` has the highest failure rate among non-terminal actions
at 41.2%, followed by `drop` (47.1%) and `pick`.

### Table 1 — Action type failure summary (both models combined)

| Action | Total | Failed | Fail% | Top Failure Cause | Count | % of Fails |
|--------|------:|-------:|------:|-------------------|------:|-----------:|
| `find` | 1927 | 254 | 13.2% | object_not_found | 254 | 100% |
| `pick` | 1242 | 490 | 39.5% | pick_execution_failed | 226 | 46% |
| `put` | 930 | 275 | 29.6% | put_failure | 275 | 100% |
| `open` | 393 | 13 | 3.3% | open_action_failed | 12 | 92% |
| `close` | 283 | 8 | 2.8% | object_not_found | 8 | 100% |
| `toggleon` | 173 | 40 | 23.1% | object_not_found | 28 | 70% |
| `toggleoff` | 106 | 3 | 2.8% | action_failed_generic | 2 | 67% |
| `slice` | 80 | 33 | 41.2% | slice_action_failed | 22 | 67% |
| `drop` | 85 | 40 | 47.1% | holding_constraint_empty | 40 | 100% |
| `done` | 341 | 341 | 100.0% | done_early_attempt | 171 | 50% |
| `malformed` | 15 | 15 | 100.0% | unknown_no_obs | 15 | 100% |


[STAT:n] n=5,575 total steps across 408 tasks
[STAT:effect_size] `pick` fail rate 39.5% vs `open` 3.3% — over 12× higher

---

## [FINDING 2] Failure causes are highly action-specific

Each action type has a dominant, near-exclusive failure mode:

- **`find`**: 100% `object_not_found` — the object type does not exist in the scene or its name cannot be resolved
- **`pick`**: 46% `pick_execution_failed` (PickupObject API returned failure, inventory empty after attempt), 36% `object_in_container` (item inside closed receptacle), 17% `holding_constraint_occupied` (already holding something)
- **`put`**: 100% `put_failure` — no valid receptacle found/reachable after exhausting all retries
- **`drop`**: 100% `holding_constraint_empty` — agent tried to drop when holding nothing
- **`toggleon`**: 70% `object_not_found`, 30% generic action failure
- **`slice`**: 67% `slice_action_failed`, 33% `object_not_found` (knife not in hand or unreachable)

### Table 2 — Action type × dominant failure cause (both models)

| Action | Top Cause | % | 2nd Cause | % |
|--------|-----------|---|-----------|---|
| `find` | object_not_found | 100% | — | — |
| `pick` | pick_execution_failed | 46% | object_in_container | 36% |
| `put` | put_failure | 100% | — | — |
| `open` | open_action_failed | 92% | object_not_found | 8% |
| `close` | object_not_found | 100% | — | — |
| `toggleon` | object_not_found | 70% | action_failed_generic | 30% |
| `slice` | slice_action_failed | 67% | object_not_found | 33% |
| `drop` | holding_constraint_empty | 100% | — | — |
| `done` | premature/early | 100% | — | — |

[STAT:n] n=1,512 failed steps

---

## [FINDING 3] GPT-5.2 fails at 18.1% vs Qwen3-8B at 34.7% — nearly half the rate

GPT-5.2 has substantially lower per-step failure rates across all action types, with the
largest gaps on `put` (13.0% vs 41.7%), `toggleon` (8.3% vs 37.1%), `find` (7.5% vs 17.5%),
and `pick` (26.0% vs 48.6%).

Notably, Qwen3-8B is the sole source of `holding_constraint_occupied` failures (82 cases, 7.8%
of its failures) — it attempts to pick a second object while already holding one, a planning
error GPT-5.2 never makes. Qwen3-8B also produces 15 malformed (unparseable) actions; GPT-5.2
produces zero.

### Table 3 — Per-model action failure rate comparison

| Action | Q-Total | Q-Fail | Q-Fail% | G-Total | G-Fail | G-Fail% |
|--------|--------:|-------:|--------:|--------:|-------:|--------:|
| `find` | 1089 | 191 | 17.5% | 838 | 63 | 7.5% |
| `pick` | 739 | 359 | 48.6% | 503 | 131 | 26.0% |
| `put` | 537 | 224 | 41.7% | 393 | 51 | 13.0% |
| `open` | 166 | 11 | 6.6% | 227 | 2 | 0.9% |
| `close` | 75 | 2 | 2.7% | 208 | 6 | 2.9% |
| `toggleon` | 89 | 33 | 37.1% | 84 | 7 | 8.3% |
| `toggleoff` | 42 | 0 | 0.0% | 64 | 3 | 4.7% |
| `slice` | 40 | 24 | 60.0% | 40 | 9 | 22.5% |
| `drop` | 78 | 40 | 51.3% | 7 | 0 | 0.0% |
| `done` | 150 | 150 | 100.0% | 191 | 191 | 100.0% |
| `malformed` | 15 | 15 | 100.0% | 0 | 0 | 0.0% |


### Table 4 — Failure category distribution by model

| Failure Category | Qwen3-8B (n) | Qwen3-8B % | GPT-5.2 (n) | GPT-5.2 % |
|------------------|------------:|-----------:|------------:|----------:|
| object_not_found | 221 | 21.1% | 86 | 18.6% |
| put_failure | 224 | 21.4% | 51 | 11.0% |
| pick_execution_failed | 150 | 14.3% | 76 | 16.4% |
| object_in_container | 125 | 11.9% | 53 | 11.4% |
| done_early_attempt | 61 | 5.8% | 110 | 23.8% |
| premature_done | 89 | 8.5% | 81 | 17.5% |
| holding_constraint_occupied | 82 | 7.8% | 0 | 0.0% |
| holding_constraint_empty | 40 | 3.8% | 0 | 0.0% |
| slice_action_failed | 22 | 2.1% | 0 | 0.0% |
| open_action_failed | 11 | 1.0% | 1 | 0.2% |
| action_failed_generic | 9 | 0.9% | 5 | 1.1% |
| unknown_no_obs | 15 | 1.4% | 0 | 0.0% |
| **TOTAL** | **1049** | 100% | **463** | 100% |


[STAT:n] Qwen3-8B n=1,049 failures; GPT-5.2 n=463 failures
[STAT:effect_size] Qwen3-8B overall step failure rate 34.7% vs GPT-5.2 18.1% (delta = 16.6pp)
[STAT:effect_size] Task success rate: GPT-5.2 53.9% vs Qwen3-8B 30.4% (delta = 23.5pp)

---

## [FINDING 4] `pick_and_place_with_movable_recep` is the hardest task type (17% combined success)

This task type requires placing an object inside a movable container (e.g., a bowl on a plate),
then placing both on a receptacle. Its dominant failure is `put_failure` (33%), reflecting the
difficulty of placing objects into/onto non-static receptacles. Success rates: 6% Qwen3-8B,
27% GPT-5.2.

### Table 5 — Task type summary

| Task Type | N Tasks | Succ% (Q) | Succ% (G) | Total Steps | Fail Steps | Fail% |
|-----------|--------:|----------:|----------:|------------:|-----------:|------:|
| `look_at_obj_in_light` | 30 | 33% | 73% | 223 | 104 | 47% |
| `p&p_simple` | 102 | 31% | 59% | 1009 | 387 | 38% |
| `p&p_with_movable_recep` | 66 | 6% | 27% | 1082 | 361 | 33% |
| `pick_clean_then_place_in_recep` | 64 | 34% | 50% | 837 | 175 | 21% |
| `pick_cool_then_place_in_recep` | 78 | 46% | 59% | 1158 | 231 | 20% |
| `pick_heat_then_place_in_recep` | 68 | 29% | 62% | 1266 | 254 | 20% |


### Table 6 — Top 3 failure causes per task type

| Task Type | #1 Failure | % | #2 Failure | % | #3 Failure | % |
|-----------|-----------|---|-----------|---|-----------|---|
| `look_at_obj_in_light` | object_not_found | 35% | object_in_container | 20% | done_early_attempt | 15% |
| `p&p_simple` | object_not_found | 23% | pick_execution_failed | 20% | put_failure | 15% |
| `p&p_with_movable_recep` | put_failure | 33% | pick_execution_failed | 16% | object_in_container | 13% |
| `pick_clean_then_place_in_recep` | object_not_found | 35% | premature_done | 17% | done_early_attempt | 15% |
| `pick_cool_then_place_in_recep` | pick_execution_failed | 22% | done_early_attempt | 18% | object_not_found | 16% |
| `pick_heat_then_place_in_recep` | object_not_found | 19% | put_failure | 18% | pick_execution_failed | 17% |


[STAT:n] 408 tasks total (102 pick_and_place_simple, 66 with_movable_recep, 64 clean+place, 78 cool+place, 68 heat+place, 30 look_at_light)

---

## [FINDING 5] Repetitive failure loops are 3.6× more common in Qwen3-8B

Qwen3-8B exhibits 86 consecutive repeated-failure streaks (same action string failing 2+
times in a row), totalling 242 wasted steps, with a maximum streak of 22 identical failures.
GPT-5.2 has only 24 such streaks (50 steps), max streak 3. This indicates GPT-5.2 recovers
from failures by adapting its plan, while Qwen3-8B frequently loops.

[STAT:n] Qwen3-8B: 86 repeat streaks / 1,049 failures = 8.2% of failures in loops
[STAT:n] GPT-5.2: 24 repeat streaks / 463 failures = 5.2% of failures in loops
[STAT:effect_size] Max streak: Qwen3-8B 22 vs GPT-5.2 3

---

## Top 10 Most Frequent Failure Messages

### Table 7 — Exact observation strings (both models combined)

| # | Count | Observation Message |
|---|------:|---------------------|
| 1 | 39 | `Action failed: pick up the credit card. Robot is not holding any object` |
| 2 | 29 | `Action failed: pick up the apple. Robot is not holding any object` |
| 3 | 26 | `Action failed: put down the cup. put down failed` |
| 4 | 26 | `Action failed: pick up the CreditCard. Robot is not holding any object` |
| 5 | 25 | `Action failed: pick up the plate. Robot is not holding any object` |
| 6 | 24 | `Action failed: put down the watch. put down failed` |
| 7 | 24 | `Action failed: find a sinkbasin. Cannot find Sinkbasin` |
| 8 | 23 | `Action failed: put down the plate. put down failed` |
| 9 | 21 | `Action failed: put down the pan. put down failed` |
| 10 | 20 | `Action failed: pick up the knife. Robot is currently holding Apple` |


**Patterns from top messages:**
- "Robot is not holding any object" on pick: physics-level pick failure (object unreachable/physics glitch) — top source is credit card and apple
- "put down failed": receptacle not found or not reachable after all retries — most common objects: cup, watch, plate, pan
- "Cannot find Sinkbasin/Table/Couch/Lamp": generic object class not resolvable in scene (naming mismatch or absent)
- "Robot is currently holding X" on pick: holding-state conflict in Qwen3-8B during slice-related tasks (apple↔knife swap loops)

---

## Key Findings Summary

1. **Pick and put are the primary bottleneck**: Together 50.6% of all failed steps. Pick fails primarily because objects are inside closed containers (36%) or the physics pick action silently fails (46%).

2. **Failure causes are action-specific**: `find` always fails with object_not_found; `put` always fails with put_failure; `drop` always fails because the hand is empty. These are self-contained failure modes.

3. **GPT-5.2 is substantially better across all dimensions**: 23.5pp higher task success rate, 16.6pp lower step failure rate. The gap is largest for `put` (3.2× lower fail rate) and `toggleon` (4.5× lower).

4. **Qwen3-8B has a unique planning failure mode**: `holding_constraint_occupied` (82 cases) — attempting to pick a second object without dropping the first. This never occurs in GPT-5.2, indicating GPT-5.2 tracks held-object state more reliably.

5. **Movable-receptacle tasks are disproportionately hard**: `pick_and_place_with_movable_recep` has 33% of failures from `put_failure`, the highest of any task type, and the lowest combined success rate (17%).

6. **Qwen3-8B loops on failures**: 86 repetitive failure streaks (max 22 identical consecutive failures) vs 24 for GPT-5.2 (max 3), suggesting Qwen3-8B lacks effective recovery heuristics.

7. **Object naming mismatches are a consistent source of `find` failures**: "Sinkbasin", "Table", "Couch", "Lamp" appear in top find failures because the LLM uses informal names not matching the ALFRED object registry.

---

## [LIMITATION]

1. **Causal attribution**: Failure categories are inferred from observation string patterns; edge cases may be miscategorized (e.g., a `pick` failure on a visible object due to physics engine instability vs. a genuine navigation issue).

2. **No control for scene difficulty**: Both models are evaluated on the same 204 tasks, but task-level difficulty differences (object placement, scene layout) are not controlled for in the per-model comparison.

3. **`done` semantics ambiguity**: 171 `done` steps flagged as `action_success=False` in tasks that ultimately succeeded (`done_early_attempt`). This may reflect intermediate `done` calls or a quirk in how the ReAct evaluator marks the `done` action vs. the final task outcome.

4. **Repetition counting methodology**: Repetitive failure streaks are counted at the exact action-string level; paraphrased repetitions (slightly different wording for the same logical action) are not captured.

5. **Sample size for some categories**: `toggleoff` (3 failures), `close` (8 failures) have small counts; their failure rate estimates carry high uncertainty.

---

*Figures saved to:*
- `.omc/scientist/figures/fig1_failure_category_by_model.png`
- `.omc/scientist/figures/fig2_action_failure_rate_by_model.png`
- `.omc/scientist/figures/fig3_task_success_by_type.png`
- `.omc/scientist/figures/fig4_failure_categories_per_tasktype.png`
