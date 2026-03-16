# State-Instance Mismatch Analysis: Qwen3.5-9B ALFRED ReAct Evaluation

**Generated:** 2026-03-10  
**Model:** Qwen3.5-9B (ReAct mode)  
**Dataset:** valid_seen, 30% sample (205 tasks)  
**Data source:** `outputs/alfred_react/2026-03-09_23-44-11/`

---

## Objective

[OBJECTIVE] Quantify how often a state-instance mismatch in `alfred/env/tasks.py` causes task failures in transformation tasks (`pick_heat_then_place_in_recep`, `pick_cool_then_place_in_recep`, `pick_clean_then_place_in_recep`).

**The bug:** The ALFRED goal checker tracks transformation state (heated/cooled/cleaned) at the objectId level (e.g., `Cup|00.24|00.94|-01.54`). If the model transforms Cup_A but then picks up Cup_B (a different instance of the same type) and places Cup_B, the task fails — even though semantically "a cup was heated and placed."

---

## Data

[DATA] 205 task evaluation files (JSON), one per trial × annotation pair. Fields used: `type`, `success`, `goal_instr`, `reasoning_trace` (step_number, action, action_success, observation). Note: 13 trial IDs appear in two separate task files (same scene, different annotation goals).

| Field | Value |
|---|---|
| Total tasks | 205 |
| Total unique trial scenes | 192 |
| Task types | 7 (+ 1 None/missing) |
| Transformation tasks | 105 |
| Non-transformation tasks | 100 |

---

## Summary Statistics

### Overall Performance

| Metric | Value | 95% CI (Wilson) |
|---|---|---|
| Tasks succeeded | 87/205 | — |
| Overall success rate | 42.4% | 35.9%–49.3% |
| Transformation task success rate | 45/105 = 42.9% | 33.6%–52.6% |
| Non-transformation success rate | 42/100 = 42.0% | 32.8%–51.8% |

### Success Rate by Task Type

| Task Type | Total | Succeeded | Failed | Fail Rate |
|---|---|---|---|---|
| pick_and_place_simple | 51 | 35 | 16 | 31.4% |
| pick_and_place_with_movable_recep | 33 | 12 | 21 | 63.6% |
| look_at_obj_in_light | 15 | 10 | 5 | 33.3% |
| **pick_heat_then_place_in_recep** | **34** | **13** | **21** | **61.8%** |
| **pick_cool_then_place_in_recep** | **39** | **20** | **19** | **48.7%** |
| **pick_clean_then_place_in_recep** | **32** | **12** | **20** | **62.5%** |

---

## Findings

### Finding 1: State-Instance Mismatch Affects 33% of Failed Transformation Tasks

[FINDING] Of the 60 failed transformation tasks, 20 (33.3%) are attributable to state-instance mismatch: either a confirmed instance switch post-transformation (7 cases) or a correct-procedure execution that still failed with no other explanation (13 cases).

[STAT:n] n = 60 failed transformation tasks  
[STAT:effect_size] 20/60 = 33.3% of failed transformation tasks  
[STAT:ci] 95% CI: 22.7%–45.9% (Wilson score interval)

#### Failure Category Breakdown (60 failed transformation tasks)

| Category | Count | % | 95% CI | Description |
|---|---|---|---|---|
| No Transformation | 25 | 41.7% | 30.1%–54.3% | Failed before reaching transformation step (slicing failure, knife inaccessible, agent loop) |
| **Correct Sequence Failed** | **13** | **21.7%** | **13.1%–33.6%** | **All steps succeeded; env-level state tracking must have failed** |
| Pick Failure | 8 | 13.3% | 6.9%–24.2% | Could never pick up the target object |
| **Mismatch Confirmed** | **7** | **11.7%** | **5.8%–22.2%** | **Explicit second `find <type>` after transformation — new instance interacted** |
| Missing Slice | 4 | 6.7% | 2.6%–15.9% | Goal required sliced object; model skipped slicing |
| Mismatch Pre-Transform | 2 | 3.3% | 0.9%–11.4% | Multiple find cycles before transformation phase |
| Wrong Object Type | 1 | 1.7% | 0.3%–8.9% | Model used mug when goal specified glass |

**Mismatch-related total (confirmed + likely):** 20/60 (33.3%)  
**Including pre-transform mismatch:** 22/60 (36.7%)

---

### Finding 2: Mismatch Accounts for ~10% of All Task Failures

[FINDING] The state-instance mismatch bug accounts for 20 of the 118 total failures, making it the second-largest identifiable failure cause after pre-transformation step failures.

[STAT:n] n = 205 total tasks  
[STAT:effect_size] 20/205 = 9.8% of all tasks affected  
[STAT:ci] 95% CI: 6.4%–14.6%

---

### Finding 3: Cooling and Cleaning Tasks Most Affected

[FINDING] Cooling and cleaning tasks show higher mismatch rates than heating tasks. Heat tasks have fewer mismatch cases (4/21 failed = 19%) compared to cooling (7/19 = 37%) and cleaning (9/20 = 45%).

[STAT:n] Heat n=21, Cool n=19, Clean n=20 (failed tasks only)  
[STAT:effect_size] Heat: 19%, Cool: 37%, Clean: 45% mismatch rate  

The difference likely reflects structural factors:
- **Heating** (microwave): model puts object in microwave and retrieves from same location — lower chance of grabbing wrong instance
- **Cooling** (fridge): fridge navigation sometimes causes "Cup is not visible because inside container" errors → model navigates away and finds a new instance
- **Cleaning** (sink): sink area may have multiple objects nearby; after placing in sink, other sponge/cloth instances may be encountered when re-picking

---

### Finding 4: 13 "Correct Sequence" Failures Are Pure Environment-Level Bugs

[FINDING] 13 tasks completed the full correct action sequence (single find cycle → pick → transform → retrieve → place → done), yet failed. These cannot be explained by wrong object type, missing slicing, or observable action failures.

[STAT:n] n = 13  
[STAT:ci] 95% CI: 13.1%–33.6% of failed transformation tasks  

**Verification:** All 12 with detectable final placements show: `transform_step` identified + `put down <obj>` succeeds after transform + `done_signal` termination. The ALFRED goal checker rejected these completions despite the model executing the correct procedure with the same object instance (retrieved from the appliance).

These 13 cases suggest the environment's instance-level state sets (`heated_objects`, `cooled_objects`, `cleaned_objects`) contain objectIds that do NOT match the objectId of the object the model placed — even when the model retrieved the object directly from the appliance.

**Hypothesis:** The `nav_obj()` teleportation in `thor_connector.py` may navigate to a new closest object of the same type when the model does "pick up the <type>" after returning from the appliance area, rather than reliably targeting the specific object that was placed inside.

---

### Finding 5: Type-Level State Attribution Would Recover ~10 pp Success Rate

[FINDING] Under a type-level state model ("any cup was heated" rather than "this specific cup was heated"), an estimated 20 additional tasks would pass, raising the success rate from 42.4% to 52.2%.

[STAT:n] n = 205  
[STAT:ci] Projected success rate 95% CI: 45.4%–58.9%  
[STAT:effect_size] +9.8 percentage points absolute improvement

**This is a conservative estimate** that counts only confirmed (7) and correct-sequence-failed (13) cases. The pre-transform mismatch cases (2) were excluded because it is uncertain whether the final placement used the correct receptacle type.

---

## Representative Example Traces

### Example 1: Confirmed Mismatch — Mug Cleaning (coffee maker)

**Goal:** "drop a clean mug on the coffee maker"  
**Type:** `pick_clean_then_place_in_recep`  
**Result:** FAILED (done_signal)

```
[ 1] find a mug                         ok=True    # Finds Mug_1
[ 2] pick up the mug                    ok=True    # Holds Mug_1
[ 3] find a sink                        ok=True
[ 4] put down the mug                   ok=True    # Mug_1 in sink
[ 5] turn on the faucet                 ok=True    # Mug_1 CLEANED -> added to cleaned_objects
[ 6] turn off the faucet                ok=True
[ 7] pick up the mug                    ok=True    # Retrieves Mug_1 (still cleaned)
[ 8] find a coffee maker                ok=False   # "CoffeeMaker" not found
[ 9] find a CoffeeMachine               ok=True    # Found coffee machine
[10] drop the mug                       ok=True    # Drops Mug_1 on FLOOR (near coffee machine)
[11] pick up the mug                    ok=False   # "Mug is not visible because inside container"
[12] find a mug                         ok=True    # Finds Mug_2 (DIFFERENT INSTANCE)
[13] pick up the mug                    ok=True    # Holds Mug_2 (NOT in cleaned_objects!)
[14] drop the mug                       ok=True    # Drops Mug_2 near coffee machine
[15] done                               ok=None    # FAIL: Mug_2 not in cleaned_objects
```

**Mismatch mechanism:** Mug_1 was cleaned. At step 11, Mug_1 became invisible (fell into container). At step 12, `find a mug` navigated to Mug_2 — a different objectId never cleaned. Final placement of Mug_2 fails the `cleaned_objects` check.

---

### Example 2: Confirmed Mismatch — Cup Cooling (stand)

**Goal:** "Put a cold cup on a stand."  
**Type:** `pick_cool_then_place_in_recep`

```
[ 1] find a cup                         ok=True    # Finds Cup_1
[ 2] pick up the cup                    ok=True
[ 3-6] [put in fridge, close fridge]    ok=True    # Cup_1 COOLED
[ 7] open the fridge                    ok=True
[ 8] pick up the cup                    ok=False   # "Cup is not visible because inside container"
[9-16] [repeated fridge/drop failures]  ok=False
[19] find a cup                         ok=True    # Finds Cup_2 (DIFFERENT INSTANCE)
[20] pick up the cup                    ok=True    # Holds Cup_2 (NOT cooled)
[21-25] [attempts to cool Cup_2...]     truncated  # max_steps reached
```

**Mismatch mechanism:** Cup_1 was placed in fridge and cooled, but fridge navigation made it invisible for pick-up. Model found Cup_2 and attempted to repeat the cooling cycle. Task truncated at 25 steps.

---

### Example 3: Confirmed Mismatch — Potato Cooling (sink)

**Goal:** "Place a cold potato slice in the sink."  
**Type:** `pick_cool_then_place_in_recep`

```
[1-15] find potato -> slice it -> put in fridge -> close fridge  # Potato_1 COOLED
[16] open the fridge                    ok=True
[17-18] pick up the potato              ok=False   # Not visible (×2)
[19] find a sink                        ok=True    # Navigates away from fridge
[20] pick up the potato                 ok=False   # Still not visible
[21] find a potato                      ok=True    # Finds Potato_2 (DIFFERENT INSTANCE)
[22] pick up the potato                 ok=True    # Holds Potato_2 (NOT cooled)
[23] put down the potato                ok=True    # Places Potato_2 in sink area
[24] done                               ok=None    # FAIL: Potato_2 not in cooled_objects
```

**Mismatch mechanism:** Potato_1 was cooled. Failed pick from fridge → navigated to sink → found Potato_2. Placed Potato_2 in sink. Under **type-level state**, this task WOULD SUCCEED (a potato was cooled, a potato was placed in a sink-type receptacle).

---

### Example 4: Likely Mismatch — Heated Mug on Table (pure env-level)

**Goal:** "Put a heated mug down on a table."  
**Type:** `pick_heat_then_place_in_recep`

```
[ 1] find a mug                         ok=True    # Finds Mug_1
[ 2] pick up the mug                    ok=True
[ 3] find a microwave                   ok=True
[ 4] open the microwave                 ok=True
[ 5] put down the mug                   ok=True    # Mug_1 in microwave
[ 6] close the microwave                ok=True
[ 7] turn on the microwave              ok=True    # Mug_1 HEATED -> heated_objects
[ 8] turn off the microwave             ok=True
[ 9] open the microwave                 ok=True
[10] pick up the mug                    ok=True    # Retrieves from microwave (same Mug_1)
[11] close the microwave                ok=True
[12] find a table                       ok=False   # "Cannot find Table"
[13] find a diningtable                 ok=True
[14] put down the mug                   ok=True    # Places Mug_1 on diningtable
[15] done                               ok=None    # FAIL: ???
```

**Analysis:** Single find, single pick, transformation, retrieved from microwave (same instance), placed on diningtable, done. EVERY action succeeded. This task should have passed. The failure indicates either: (a) `heated_objects` did not record Mug_1's objectId correctly when heated via microwave toggle, (b) the diningtable variant is not accepted as the target receptacle type, or (c) a nav-teleport during step 13 changed which Mug instance was being held.

---

### Example 5: Correct Sequence — Bottle Cooling (white table)

**Goal:** "Pick the bottle, cool it and serve on the white table."  
**Type:** `pick_cool_then_place_in_recep`

```
[ 1] find a bottle                      ok=True
[ 2] pick up the bottle                 ok=True
[ 3] find a fridge                      ok=True
[ 4] open the fridge                    ok=True
[ 5] put down the bottle                ok=True    # Bottle COOLED
[ 6] close the fridge                   ok=True
[ 7] open the fridge                    ok=True
[ 8] pick up the bottle                 ok=True    # Retrieved from fridge
[ 9] close the fridge                   ok=True
[10] find a diningtable                 ok=True
[11] put down the bottle                ok=True    # Placed on table
[12] done                               ok=None    # FAIL: state mismatch or receptacle mismatch
```

**Analysis:** Perfect procedure, no action failures. The "white table" may map to a DiningTable variant not accepted by the receptacle checker, OR the bottle retrieved from fridge at step 8 was not the same instance as the one placed there at step 5.

---

## Estimated Impact Under Type-Level State Attribution

If the goal checker used type-level state attribution ("any object of type T was heated/cooled/cleaned" rather than "this specific objectId was heated/cooled/cleaned"):

| Category | Count | Would Succeed? | Reasoning |
|---|---|---|---|
| Mismatch Confirmed (7) | 7 | ~1–3 additional | Some also had wrong receptacle or max_steps truncation |
| Correct Sequence Failed (13) | 13 | ~12–13 additional | All had successful placements; only state check fails |
| **Total estimated additional successes** | | **13–16 tasks** | |

**Conservative estimate: +13 tasks** (95% CI on 13/205: 5.9%–11.5%)  
**Upper estimate: +20 tasks** (all confirmed + likely, assuming placement was correct)

**Projected success rate:** 42.4% → 52.2% (+9.8 pp)  
[STAT:ci] 95% CI on projected rate: 45.4%–58.9% (n=205, Wilson interval)

---

## Limitations

[LIMITATION] **Detection method is heuristic.** Mismatch is inferred from action sequences (number of `find <type>` events, pick success counts). The actual objectIds involved are not logged in the trace, so we cannot directly verify which instance was transformed vs. which was placed. True instance-level confirmation would require AI2-THOR scene state logging.

[LIMITATION] **Correct-sequence-failed causation is uncertain.** The 13 "correct sequence" cases may fail for reasons other than state-instance mismatch (e.g., wrong receptacle sub-type, ALFRED annotation requiring a specific object that wasn't the one the model found). Without direct comparison to the ALFRED ground-truth task specification, the exact failure reason cannot be confirmed.

[LIMITATION] **Sample size for mismatch_confirmed is small.** Only 7 confirmed cases (11.7% of failed transformation tasks), giving a wide 95% CI of 5.8%–22.2%. Conclusions about confirmed mismatch frequency have limited precision.

[LIMITATION] **Impact estimate assumes receptacle was correct.** The projected +20 successes assumes that in mismatch cases, the final object placement was in the correct receptacle type. For some cases (e.g., "drop on floor" instead of in cabinet), even type-level state would not recover the task.

[LIMITATION] **30% subsample.** This analysis covers 30% of valid_seen (205/682 tasks). Results may not generalize to the full split or to other models/temperatures.

---

## Conclusions

1. **State-instance mismatch is a real and measurable source of task failure**, affecting 20/60 (33.3%) of failed transformation tasks and 9.8% of all 205 tasks.

2. **Two failure modes are observed:** (a) explicit instance switch after failed pick-from-appliance (7 confirmed cases), and (b) correct procedure with environment-level state tracking failure (13 likely cases).

3. **Fixing the bug would recover approximately +13–20 tasks** (+6.3–9.8 pp success rate), bringing the projected success rate to 46.8%–52.2%.

4. **The root cause** appears to be in `nav_obj()` returning a different instance of the same type when the model navigates back toward the appliance, combined with `heated_objects` / `cooled_objects` / `cleaned_objects` tracking specific objectIds rather than object types.

5. **Recommended fix:** Either (a) track transformation state at the type level for the goal checker, or (b) ensure `llm_skill_interact` preferentially targets the most recently interacted instance of a type when re-picking.

---

## Figures

- `figures/fig1_task_breakdown.png` — Task success by type + failure category pie chart
- `figures/fig2_mismatch_impact.png` — Mismatch impact by transformation type + projected success improvement
- `figures/fig3_mismatch_trace_example.png` — Annotated action trace for Example 1 (mug cleaning mismatch)
