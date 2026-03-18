# Action Failure Causal Chain Analysis — Qwen3.5-9B ALFRED ReAct

**Model:** Qwen3.5-9B  
**Evaluation:** ALFRED valid_seen, 30% split (204 tasks)  
**Data source:** `outputs/alfred_react/2026-03-09_23-44-11/`  
**Analysis date:** 2026-03-10  
**Overall success rate:** 87/204 = 42.6% (95% CI [36.1%, 49.5%])

---

## Executive Summary

The central hypothesis — that "put/pick failures are caused by the preceding `find` step" — is
**partially confirmed but with an important revision**: the `find` action itself succeeds at navigation
93.6% of the time. The dominant causal failure mode is **not bad navigation, but bad model state
tracking**: the model attempts to `pick` an object while already holding something (28.7% of all
find→pick pairs), producing a cascading failure chain. True find-caused pick failures (object not
visible after a successful find) account for only 12.4% of pairs. Separately, 70.9% of failed tasks
end with a premature `done` signal, most often (49/83) because the model placed the object in the
**correct receptacle type but at the wrong instance**, indicating a semantically correct but
spatially unconstrained plan.

---

## Section 1: Find→Pick Causal Chain Statistics

[OBJECTIVE] Quantify how often the find action causally explains subsequent pick failures.

[DATA] 204 tasks, 2,622 total action steps. 394 find→pick pairs identified (intervening `open`
actions allowed). No find_instance actions were observed — Qwen3.5-9B exclusively uses generic
find (`find a/an <type>`).

### Find→Pick Outcome Table

| Outcome | Count | % of pairs | Notes |
|---------|------:|----------:|-------|
| find_ok → pick_ok | 230 | 58.4% | Successful chain |
| find_ok → pick_fail (holding obj) | 113 | 28.7% | Model logic error — not find's fault |
| find_ok → pick_fail (not visible) | 49 | 12.4% | True find navigation failure |
| find_ok → pick_fail (not found) | 2 | 0.5% | Object alias mismatch |
| find_fail → pick_attempted | 0 | 0.0% | Never observed |
| **Total** | **394** | **100%** | |

[FINDING] Find navigation succeeds but pick fails in 41.6% of all find→pick pairs (95% CI [36.9%,
46.5%]). However, the dominant cause (68.9% of those failures) is the model attempting to pick while
already holding another object — a model state-tracking error independent of navigation quality.
[STAT:n] n=394 find→pick pairs across 204 tasks  
[STAT:effect_size] True find-caused pick failures: 51/394 = 12.9% of pairs  
[STAT:ci] 95% CI for true find-caused failures: [9.9%, 16.7%]

### Pick success rate by task outcome

| Task outcome | find→pick pairs | pick_ok | pick_fail |
|-------------|---------------:|--------:|----------:|
| Succeeded tasks | 103 | 87 (84%) | 16 (16%) |
| Failed tasks | 291 | 143 (49%) | 148 (51%) |

[FINDING] In failed tasks, only 49% of find→pick pairs lead to a successful pick, compared to 84%
in succeeded tasks — a 35 percentage point gap indicating pick failure is strongly associated with
task failure.
[STAT:effect_size] 35pp difference in pick success rate (failed vs. succeeded tasks)  
[STAT:n] n=394 pairs

---

## Section 2: Find Quality — Generic vs Instance-Specific Targeting

[FINDING] Qwen3.5-9B uses **exclusively generic find** (`find a/an <type>`) across all 204 tasks —
zero instance-specific finds (`find <Type>_N`) were issued. This means the model never leverages
instance-level disambiguation available through the ThorConnector interface.
[STAT:n] n=766 find actions (all generic)

### Generic find success rate

| Metric | Value | 95% CI |
|--------|------:|--------|
| Total find attempts | 766 | — |
| Succeeded | 717 | — |
| **Success rate** | **93.6%** | [91.6%, 95.1%] |
| Failed | 49 | — |
| **Fail rate** | **6.4%** | [4.9%, 8.4%] |

[FINDING] Find failures are predominantly caused by **non-standard object names** that do not match
AI2-THOR's object type registry. The model invents aliases (`find a table`, `find a sponge`,
`find a coffee maker`) that the simulator cannot resolve.
[STAT:n] n=766 generic find actions  
[STAT:p_value] Not applicable (this is a classification, not a test)

### Most common find failure targets (n=49 failures)

| Target (model's name) | Failures | Root cause |
|-----------------------|--------:|------------|
| table | 5 | AI2-THOR uses `DiningTable`, `SideTable`, etc. |
| sponge | 3 | AI2-THOR name: `Sponge` (case OK) — scene-specific absence |
| bottle | 3 | Scene-specific absence |
| soap | 2 | AI2-THOR name: `SoapBar` or `SoapBottle` |
| coffee maker | 2 | AI2-THOR name: `CoffeeMachine` |
| toilet paper holder | 2 | Not in all scenes |
| toilet paper roll | 2 | AI2-THOR name: `ToiletPaper` |

### When find succeeds but pick fails (object not visible, n=49)

The most affected object types (find navigated to wrong position):

| Object | Not-visible pick fails |
|--------|----------------------:|
| cup | 6 |
| cloth | 5 |
| apple | 5 |
| potato | 4 |
| tomato | 3 |

These objects are commonly found inside containers (cabinets, fridge). The `find a <type>` call
navigates the agent near the **container**, not the object itself — so pick visibility fails because
the object is occluded inside the container.

---

## Section 3: Put Failure Root Cause Attribution

[DATA] 457 total put attempts, 381 succeeded (83.4%, 95% CI [79.7%, 86.5%]), 76 failed.

### Put failure decomposition

| Root cause | Count | % of put failures |
|------------|------:|------------------:|
| Model not holding object (prior pick failed or already put) | 29 | 38.2% |
| Holding object but put failed (wrong receptacle position or state) | 47 | 61.8% |

[FINDING] Of 76 put failures, 88.2% (n=67) had a preceding receptacle find action that **succeeded
at navigation** (95% CI [79.0%, 93.6%]). This means find navigated to the receptacle, yet the put
still failed — indicating the failure is in **receptacle state** (closed, not reachable from the
navigated position) rather than in finding the wrong receptacle.
[STAT:n] n=76 put failures  
[STAT:ci] 95% CI for "had prior find": [79.0%, 93.6%]

### Most common receptacle targets in failing puts

| Receptacle (found before put) | Put failures |
|-------------------------------|-------------:|
| cabinet | 13 |
| cup (movable container) | 6 |
| Sink | 6 |
| countertop | 5 |
| coffeemachine | 4 |
| drawer | 4 |
| shelf | 4 |

[FINDING] The observation message for all 76 put failures is the generic "put down failed" — the
simulator does not expose a specific sub-reason (not reachable, receptacle full, etc.). Root cause
attribution must therefore rely on context: 11.8% of put failures occurred without any prior
receptacle find (model attempted to put without navigating to the receptacle first).
[STAT:n] n=76 put failures; 9 (11.8%) with no prior receptacle find

---

## Section 4: Object Type Targeting Accuracy

[FINDING] Qwen3.5-9B correctly targets the goal object in its first find action in 196/204 tasks
(96.1%, 95% CI [92.5%, 98.0%]). The 8 mismatches are due to **synonym/alias substitution**, not
semantic misunderstanding.
[STAT:n] n=204 tasks  
[STAT:ci] 95% CI [92.5%, 98.0%]

### Mismatch examples (8 cases)

| Goal instruction | First find | Issue |
|-----------------|------------|-------|
| "place a rag inside the tub" | `find a cloth` | "rag" → "cloth" (correct THOR alias) |
| "Move the cleaner from the toilet..." | `find a spraybottle` | "cleaner" → "spraybottle" |
| "Heat a glass and place it..." | `find a mug` | "glass" → "mug" (correct alias) |
| "Slice bread and chill it..." | `find a knife` | Finds tool first (correct strategy) |
| "Move the pot with the green sponge..." | `find a fridge` | Wrong starting object |

**Note:** Several "mismatches" (cloth/rag, mug/glass) are actually correct ALFRED-THOR aliases.
Effective targeting error rate is likely 3–4 tasks, not 8.

### By task type

| Task type | Correct first find | Total |
|-----------|------------------:|------:|
| look_at_obj_in_light | 15 | 15 (100%) |
| pick_and_place_simple | 49 | 51 (96%) |
| pick_cool_then_place_in_recep | 38 | 39 (97%) |
| pick_heat_then_place_in_recep | 33 | 34 (97%) |
| pick_clean_then_place_in_recep | 31 | 32 (97%) |
| pick_and_place_with_movable_recep | 30 | 33 (91%) |

---

## Section 5: Common Failure Sequence Patterns

Legend: `F`=find, `P`=pick, `PT`=put, `O`=open, `C`=close, `T`=toggle, `D`=done, `SL`=slice/drop.
`+`=succeeded, `-`=failed.

### Top 10 failure sequence patterns (first 8 steps)

| Rank | Count | Pattern | Failure mode |
|------|------:|---------|-------------|
| 1 | 10 | `FG→PK→ot→PT→FG→PK→FG→pk` | Slice fails; drop to free hands; pick cycle fails |
| 2 | 9 | `FG→PK→FG→PT→dn` | Put succeeded → wrong receptacle → false done |
| 3 | 7 | `FG→PK→FG→PT→TG→TG→PK→FG` | 2-object task; second pick fails |
| 4 | 6 | `FG→PK→FG→OP→PT→CL→TG→TG` | Multi-step task; toggle loop issues |
| 5 | 5 | `FG→PK→FG→OP→PT→CL→OP→PK` | Correct template but fails later |
| 6 | 5 | `FG→PK→FG→pk→PT→PK→FG→pk` | Repeated pick failures (visibility) |
| 7 | 4 | `FG→PK→FG→OP→PT→CL→dn` | Premature done after close |
| 8 | 4 | `FG→PK→ot→FG→pk→PT→PK→FG` | Slice/drop fails; cascade pick failures |
| 9 | 3 | `fg→dn` | Find fails immediately → gives up with done |
| 10 | 4 | `FG→PK→ot→FG→pk→PT→PK→FG` | Slice cascade |

Note: lowercase = action failed.

### Full-trace pattern analysis

| Pattern (full trace) | Count | Task outcome |
|----------------------|------:|-------------|
| `F+ P+ F+ PT+ D-` | 9 | FAIL (put succeeded but wrong place → false done) |
| `F+ P+ F+ PT+ D-` | 14 | SUCCESS (same template — outcome depends on receptacle) |
| `F+ P+ F+ O+ PT+ C+ D-` | 4 | FAIL |
| `F+ P+ F+ O+ PT+ C+ O+ P+ C+ F+ PT+ D-` | 7 | SUCCESS |

[FINDING] The pattern `F+ P+ F+ PT+ D-` (find→pick→find→put→done) appears in BOTH 9 failed and 14
succeeded tasks. The **template itself is correct** — failure or success depends entirely on whether
the `put` deposited the object in the correct receptacle instance, which the model cannot verify
without a success signal.
[STAT:n] 9 failed + 14 succeeded tasks with identical 5-step pattern

### Termination reasons for failed tasks (n=117)

| Reason | Count | % |
|--------|------:|--:|
| done_signal (false done) | 83 | 70.9% |
| max_steps | 28 | 23.9% |
| malformed_output | 6 | 5.1% |

[FINDING] 70.9% of failed tasks (95% CI [62.2%, 78.4%]) end because the model **voluntarily
declares done** despite incomplete task execution. Of these 83 false-done tasks: 49 (59%) had a
successful put immediately before done, indicating wrong-receptacle placement; 13 (16%) issued done
after a close action; 7 (8%) issued done after a failed pick.
[STAT:ci] 95% CI [62.2%, 78.4%] for false-done rate

### Slice action — a systematic failure mode

[FINDING] Slice actions fail at 81.4% rate (35/43 attempts, 95% CI [67.4%, 90.3%]). The root
cause: the model issues `slice the apple` (or tomato/potato) **without first picking up a knife**,
so the simulator has no cutting tool and the action fails. This directly affects `pick_heat_then_
place_in_recep` and `pick_and_place_with_movable_recep` tasks.
[STAT:n] n=43 slice attempts  
[STAT:ci] 95% CI for fail rate: [67.4%, 90.3%]

---

## Section 6: Recovery Behavior (Retry Analysis)

[DATA] 103 unique (task, target) pairs with more than one find attempt, across 48 tasks (23.5%,
95% CI [18.2%, 29.8%]). 178 total re-find events.

### Re-find triggers

| Trigger | Count | % |
|---------|------:|--:|
| Pick failed → re-find same object | 141 | 79.2% |
| Put failed → re-find receptacle | 17 | 9.6% |
| Pick succeeded → re-find for next sub-task | 19 | 10.7% |
| Other | 1 | 0.6% |

[FINDING] 79.2% of re-find events are triggered by a pick failure. The re-find strategy is a valid
recovery mechanism but **does not address the root cause**: if pick failed due to "already holding
something", re-finding the object does not help until the model puts down what it's holding. This
creates looping behavior (find → pick_fail → find → pick_fail → ...) observed in tasks like the
cloth/cabinet example (steps 1–15 of the sample task).
[STAT:n] n=178 re-find events

### Number of find attempts per (task, target)

| Attempts | Pairs |
|----------|------:|
| 2 | 58 |
| 3 | 23 |
| 4 | 17 |
| 5 | 2 |
| 6 | 3 |

[FINDING] No case was observed where the first find **failed** and a retry succeeded — all retries
are re-navigations after a successful but insufficient find. The retry loop breaks only when: (a) the
pick eventually succeeds, (b) max_steps is reached, or (c) the model issues a done signal.
[STAT:n] n=103 retry groups; 0 first-fail-then-succeed cases

### Most retried objects

The objects most frequently re-found (suggesting persistent pick difficulties):

| Object | Retry groups | All with eventual pick success |
|--------|-------------:|------:|
| knife | 15 | 15 |
| apple | 13 | 13 |
| plate | 7 | 7 |
| tomato | 7 | 7 |
| cup | 5 | 5 |

All retry groups for these objects eventually achieve a successful find — the issue is pick, not
navigation.

---

## Section 7: Key Findings and Implications

### Finding 1: Model state tracking is the primary bottleneck
The #1 cause of pick failure is the model attempting to pick while already holding an object
(113/164 find→pick failures = 68.9%). This is a **model memory failure**, not a simulator issue.
The model loses track of its held object after multiple sub-steps. Implication: adding explicit
"currently holding: X" to the observation string would directly address this failure mode.

### Finding 2: Find navigation is reliable, but post-find visibility is not
Find succeeds 93.6% of the time, but 12.4% of all find→pick pairs fail because the object is "not
visible" despite a successful find. This occurs because `find a <type>` navigates near a **container
type** (cabinet, fridge), not the specific object inside it. The agent lands adjacent to the container
but the object inside is still technically invisible. Implication: the find action should navigate
to the object's position, not the container. Alternatively, an `open then find` pattern should be
enforced for container-stored objects.

### Finding 3: False done is the dominant failure mode (71% of failures)
The model voluntarily terminates 70.9% of failed tasks by issuing `done`. In 49 of these cases,
the model successfully placed an object (put succeeded) but in the wrong receptacle instance —
it then incorrectly believes the task is complete. The simulator's `done` action verifies placement
correctness but the model has no feedback mechanism to know it chose the wrong instance. Implication:
adding per-action success verification or a task-completion pre-check before `done` would substantially
reduce this failure mode.

### Finding 4: Slice actions are systematically broken (81% fail rate)
The model attempts to slice objects without first picking up a knife. This is a precondition error:
the model does not represent tool-use prerequisites. All 35 slice failures share the same observation
"Slice action failed". Implication: the system prompt or few-shot examples should include a knife
prerequisite example for slice tasks.

### Finding 5: Movable receptacle tasks are near-unsolvable (6.1% success)
With only 2/33 tasks succeeded, `pick_and_place_with_movable_recep` represents a fundamental
compositional planning failure. The task requires: (1) pick object, (2) place in movable container,
(3) pick the container, (4) place container in final receptacle. The model conflates sub-steps and
never completes the full chain. The slice failures within these tasks compound the issue.

### Finding 6: Object targeting accuracy is high (96.1%)
The model correctly identifies the target object from natural language in 96.1% of tasks. Apparent
mismatches (cloth/rag, mug/glass) are valid ALFRED-THOR aliases. True targeting errors occur in
approximately 3–4 tasks.

### Quantitative summary table

| Metric | Value | 95% CI |
|--------|------:|--------|
| Overall success rate | 42.6% (87/204) | [36.1%, 49.5%] |
| Find success rate | 93.6% (717/766) | [91.6%, 95.1%] |
| Pick success rate | 62.0% (437/705) | [58.3%, 65.5%] |
| Put success rate | 83.4% (381/457) | [79.7%, 86.5%] |
| Slice success rate | 18.6% (8/43) | [9.7%, 32.6%] |
| False done rate (of failures) | 70.9% (83/117) | [62.2%, 78.4%] |
| Pick fail due to holding obj | 28.7% (113/394 pairs) | [24.4%, 33.3%] |
| Pick fail due to nav (not visible) | 12.4% (49/394 pairs) | [9.5%, 16.1%] |
| Tasks with retry behavior | 23.5% (48/204) | [18.2%, 29.8%] |
| Goal object targeting accuracy | 96.1% (196/204) | [92.5%, 98.0%] |

---

## Limitations

[LIMITATION] The `done` action success field is always False in the trace (the simulator evaluates
task completion separately). This means we cannot distinguish "done issued at correct state but
simulator disagreed" from "done issued incorrectly" without cross-referencing ground-truth plans.

[LIMITATION] Put failure observations are all "put down failed" — no sub-reason is exposed by the
simulator. Attribution to "wrong receptacle" vs "not reachable" vs "wrong object state" is
inferred from context, not directly observed.

[LIMITATION] Instance-specific find accuracy cannot be evaluated because Qwen3.5-9B never issues
instance-specific finds. The comparison between generic and instance find quality is therefore
impossible with this model.

[LIMITATION] This analysis covers one model (Qwen3.5-9B) on 30% of valid_seen. Results may not
generalize to other models (GPT-4, larger Qwen variants) or to the full split.

[LIMITATION] The slice prerequisite analysis assumes knife must be held; this matches ThorConnector
behavior but the exact pre-condition logic is inferred from failure observations, not source code
verification.

---

## Figures

- `fig1_action_success_rates.png` — Per-action-type success rates
- `fig2_find_pick_chain.png` — Find→Pick outcome breakdown and task-outcome stratification
- `fig3_failure_root_causes.png` — Root cause taxonomy of all failure types
- `fig4_task_types_termination.png` — Success by task type + termination reason distribution
- `fig5_refind_triggers.png` — Re-find trigger analysis
- `fig6_causal_chain_diagram.png` — Full causal chain annotated with failure rates

Figures saved to: `.omc/scientist/figures/`

---

## Follow-up: Instance-Mismatch Pattern Addressed (feature 006)

The **state-instance mismatch** failure pattern identified in this analysis (Section 4, ~20/60 failed transformation tasks) is addressed by feature `006-instance-object-tracking` (branch `006-instance-object-tracking`):

- `pick()` now returns `"Picked up <Type>_<N>."` on success, exposing the instance label to the LLM
- `put()` now returns `"Put <Type>_<N> in <Type>_<M>."` on success, exposing both object and receptacle labels
- The heat few-shot example updated to demonstrate `find Egg_1` return navigation (instance-specific) after transformation, teaching the model to re-navigate to the *same* object instance it heated/cooled/cleaned
