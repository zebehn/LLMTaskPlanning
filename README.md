# LoTa-Bench: Benchmarking Language-oriented Task Planners for Embodied Agents

> **Fork Notice**: This is a fork of the original [LoTa-Bench](https://github.com/lbaa2022/LLMTaskPlanning) repository with significant updates for modern compatibility and extended LLM support.

### [Paper (ICLR 2024)](https://arxiv.org/abs/2402.08178) | [Project Page](https://choi-jaewoo.github.io/LoTa-Bench/) | [Original Repository](https://github.com/lbaa2022/LLMTaskPlanning)

[Jae-Woo Choi](https://choi-jaewoo.github.io/)<sup>1*</sup>, [Youngwoo Yoon](https://sites.google.com/view/youngwoo-yoon/)<sup>1*</sup>, Hyobin Ong<sup>1, 2</sup>, Jaehong Kim<sup>1</sup>, Minsu Jang<sup>1, 2</sup> (*equal contribution)

<sup>1</sup> Electronics and Telecommunications Research Institute, <sup>2</sup> University of Science and Technology

We introduce a system for automatically quantifying performance of task planning for home-service agents. Task planners are tested on two pairs of datasets and simulators: 1) [ALFRED](https://github.com/askforalfred/alfred) and [AI2-THOR](https://ai2thor.allenai.org/), 2) an extension of [Watch-And-Help](https://github.com/xavierpuigf/watch_and_help) and [VirtualHome](http://virtual-home.org/). Using the proposed benchmark system, we perform extensive experiments with LLMs and prompts, and explore several extentions of the baseline planner.

---

## Changes in This Fork

This fork introduces the following improvements over the original repository:

### AI2-THOR 5.x Compatibility
- **Updated from AI2-THOR 2.x to 5.0.0+** - The original codebase used AI2-THOR 2.x which is no longer maintained. This fork includes all necessary API changes:
  - `TeleportFull` action now uses Vector3 rotation format (`{'x': 0, 'y': 90, 'z': 0}`) instead of scalar rotation
  - Removed deprecated `rotateOnTeleport` parameter
  - Added required `standing` parameter for teleport actions
  - Replaced removed `SetStateOfAllObjects` with individual object state actions
  - Fixed `visibilityDistance` parameter naming (camelCase)
  - Platform-specific controller initialization (no `x_display` on macOS)

### OpenAI API Compatible LLM Support
- **Unified LLM provider interface** - Refactored to support any OpenAI API compatible endpoint:
  - Native OpenAI support (GPT-4, GPT-4-turbo, GPT-5.x, o1, o3)
  - **vLLM support** - Run evaluations with locally hosted models via vLLM server
  - Easy extensibility for other OpenAI-compatible providers (Ollama, LM Studio, etc.)
- **Reasoning model support** - Added `reasoning_effort` parameter for o1/o3/GPT-5.x models

### Ground-Truth Plan Evaluation
- **New `config_alfred_gt` evaluation mode** — Execute known-correct ground-truth plans from the ALFRED training set in AI2-THOR and produce a structured report:
  - Configurable evaluation portion (1-100%) with reproducible random selection via seed
  - Automatic failure categorization (object not found, navigation failure, inventory error, visibility error, interaction failure, exception)
  - Per-task-type success rate breakdown and aggregate statistics
  - Machine-readable JSON report alongside human-readable log summary
  - 47 unit tests covering all evaluation logic (no simulator required to run tests)

### Instance-Specific Action Primitives
- **Target specific object instances** by registry ID (e.g., `find Apple_1`, `pick up Mug_02`) instead of only generic type-based commands
- **Object instance registry** maps AI2-THOR objectIds to human-readable names (`Apple_1`, `Fridge_1`) and vice versa, rebuilt automatically on scene load and after slice actions
- **Full backward compatibility** — existing generic directives (`find a apple`, `pick up the mug`) continue to work identically
- **Instance-aware skill set generation** provides LLM planners with instance-specific action candidates from live scene state
- 53 unit tests covering detection, navigation, manipulation, skill generation, backward compatibility, and edge cases

### ReAct-Based Task Planner
- **New `config_alfred_react` evaluation mode** — Implements the ReAct paradigm (Yao et al., ICLR 2023) that interleaves Thought-Action-Observation steps using free-form LLM generation:
  - **Multi-turn conversation format** — Each Think+Act is an assistant message, each Obs is a user message, preventing hallucinated multi-step trajectories
  - **Failure-resilient loop** — Failed actions become observations that inform the next reasoning step (does NOT stop on failure like the base evaluator)
  - **7 few-shot examples** covering all ALFRED task types: simple pick-and-place, clean, heat, cool, examine, slice, and movable receptacle
  - Full reasoning trace recorded per task (thought, action, observation, success for each step)
  - Per-task-type success rate breakdown and aggregate statistics saved as `react_summary.json`
  - 27 unit tests covering output parsing, observation construction, evaluation loop, and config dispatch

### Other Improvements
- Modernized Python compatibility (3.8 - 3.12)
- Environment variable configuration via `.env` file
- Improved cross-platform support (removed Linux-specific dependencies)
- Added comprehensive test suite for AI2-THOR compatibility

---

## Environment

- **OS**: Ubuntu 14.04+, macOS, or Windows with WSL
- **Python**: 3.8 - 3.12
- **AI2-THOR**: 5.0.0+ (updated for compatibility)

## Install

1. Clone the repository:
    ```bash
    git clone {repo_url}
    cd LLMTaskPlanning
    ```

2. Setup a virtual environment:
    ```bash
    conda create -n llmtaskplanning python=3.10
    conda activate llmtaskplanning
    ```

3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4. Configure API keys by creating a `.env` file:
    ```bash
    cp .env.example .env
    # Edit .env and add your API keys
    ```

## LLM Provider Configuration

The system supports OpenAI API compatible LLM providers through a unified interface:

| Provider | Models | Default Port | Configuration |
|----------|--------|--------------|---------------|
| **OpenAI** | gpt-4, gpt-4-turbo, gpt-5.2, o1, o3 | N/A | `OPENAI_API_KEY` |
| **vLLM** | Any model served locally | 8000 | `VLLM_API_BASE` |
| **Ollama** | llama2, llama3, mistral, codellama, etc. | 11434 | `OLLAMA_API_BASE` |
| **LM Studio** | Any loaded model | 1234 | `LMSTUDIO_API_BASE` |

### Environment Variables (.env file)

```bash
# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# vLLM (local server)
VLLM_API_BASE=http://localhost:8000/v1

# Ollama (local server)
OLLAMA_API_BASE=http://localhost:11434/v1

# LM Studio (local server)
LMSTUDIO_API_BASE=http://localhost:1234/v1
```

## Benchmarking on ALFRED

### Download ALFRED dataset
```bash
cd alfred/data
bash download_data.sh json
cd ../..
```

### Run Benchmarking

**With OpenAI GPT-4:**
```bash
python src/evaluate.py --config-name=config_alfred \
    planner.provider=openai \
    planner.model_name=gpt-4
```

**With OpenAI GPT-5.2:**
```bash
python src/evaluate.py --config-name=config_alfred \
    planner.provider=openai \
    planner.model_name=gpt-5.2
```

**With local vLLM server:**
```bash
# First, start vLLM server
vllm serve meta-llama/Llama-2-7b-chat-hf --port 8000

# Then run evaluation
python src/evaluate.py --config-name=config_alfred \
    planner.provider=vllm \
    planner.model_name=meta-llama/Llama-2-7b-chat-hf
```

**With Ollama:**
```bash
# First, start Ollama and pull a model
ollama serve
ollama pull llama2

# Then run evaluation
python src/evaluate.py --config-name=config_alfred \
    planner.provider=ollama \
    planner.model_name=llama2
```

**With LM Studio:**
```bash
# Start LM Studio and load a model, then run evaluation
python src/evaluate.py --config-name=config_alfred \
    planner.provider=lmstudio \
    planner.model_name=your-loaded-model

# With custom endpoint (e.g., remote LM Studio server)
python src/evaluate.py --config-name=config_alfred \
    planner.provider=lmstudio \
    planner.model_name=openai/gpt-oss-20b \
    planner.api_base=http://10.254.90.90:1234/v1
```

### Configuration Options

We use [Hydra](https://hydra.cc/) for configuration management. Key options:

```bash
# Change evaluation portion
python src/evaluate.py --config-name=config_alfred alfred.eval_portion_in_percent=10

# Change number of prompt examples
python src/evaluate.py --config-name=config_alfred prompt.num_examples=8

# Change X display for headless servers
python src/evaluate.py --config-name=config_alfred alfred.x_display='1'

# Adjust max planning steps
python src/evaluate.py --config-name=config_alfred planner.max_steps=30
```

### Planning Modes

- **API providers** (OpenAI): Use `plan_whole` mode - generates complete action sequence in one API call
- **Local providers** (vLLM): Use `plan_step_by_step` mode - generates actions iteratively

### Reasoning Models (o1, o3, GPT-5.x)

For reasoning models, you can control the thinking depth with `reasoning_effort`:

```bash
# Low effort - faster responses, less thorough reasoning
python src/evaluate.py --config-name=config_alfred \
    planner.model_name=gpt-5.2 \
    planner.reasoning_effort=low

# Medium effort - balanced
python src/evaluate.py --config-name=config_alfred \
    planner.model_name=gpt-5.2 \
    planner.reasoning_effort=medium

# High effort - thorough reasoning but slower
python src/evaluate.py --config-name=config_alfred \
    planner.model_name=gpt-5.2 \
    planner.reasoning_effort=high
```

### Headless Server Setup

For headless servers, run `startx.py` before evaluation:

```bash
sudo python3 alfred/scripts/startx.py 1
```


## Ground-Truth Plan Evaluation

The ground-truth evaluation mode executes known-correct (ground-truth) action plans from the ALFRED training dataset in the AI2-THOR simulator and produces a detailed report with success rates, failure cause categorization, and per-task-type breakdowns. This is useful for validating that the simulator correctly executes reference plans and for diagnosing systematic failure patterns.

### Data Sources

The evaluator uses two data files:

| File | Contents |
|------|----------|
| `resource/alfred_examples_for_prompt.json` | 17,469 ground-truth entries with `task id`, `task type`, `task description`, and `NL steps` (the executable action sequence) |
| `alfred/data/splits/oct21.json` | Maps task IDs to filesystem paths for loading scene data (object poses, toggles, initial state) |

### Running the Evaluation

**Evaluate 5% of plans (default):**
```bash
python src/evaluate.py --config-name=config_alfred_gt
```

**Evaluate a custom portion:**
```bash
# 10% of all ground-truth plans
python src/evaluate.py --config-name=config_alfred_gt gt.eval_portion_in_percent=10

# All plans (full dataset)
python src/evaluate.py --config-name=config_alfred_gt gt.eval_portion_in_percent=100
```

**Reproducible runs with a specific random seed:**
```bash
python src/evaluate.py --config-name=config_alfred_gt \
    gt.eval_portion_in_percent=10 \
    gt.random_seed=42
```

Running the same command twice with the same seed and portion will select and evaluate the identical set of tasks.

**Evaluate a single specific trial:**
```bash
python src/evaluate.py --config-name=config_alfred_gt \
    gt.trial_id=trial_T20190907_174127_043461
```

This skips random selection and evaluates only the specified task. Useful for debugging a specific failure or re-running a single plan.

**On Linux with X11 display:**
```bash
python src/evaluate.py --config-name=config_alfred_gt gt.x_display='0'
```

### Configuration Parameters

All parameters live under the `gt` key in `conf/config_alfred_gt.yaml` and can be overridden from the command line:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `gt.eval_portion_in_percent` | `5` | Percentage of plans to evaluate (must be >0 and <=100) |
| `gt.random_seed` | `42` | Seed for reproducible random task selection |
| `gt.gt_data_file` | `resource/alfred_examples_for_prompt.json` | Path to the ground-truth examples file |
| `gt.x_display` | `'0'` | X11 display number for AI2-THOR (Linux only) |
| `gt.trial_id` | `null` | Evaluate a single specific trial ID (skips random selection when set) |

### Output

Results are saved to `outputs/alfred_gt/{timestamp}/` (Hydra-managed output directory):

| File | Description |
|------|-------------|
| `gt_evaluation_report.json` | Full structured report with all results and aggregate statistics |
| `{trial_id}_{entry_index}.json` | Individual task result with execution details |

### Report Structure

The `gt_evaluation_report.json` contains:

**Top-level fields:**
- `timestamp` — ISO 8601 timestamp of the run
- `config` — The evaluation configuration used (portion, seed, data file)
- `total_evaluated` — Number of plans executed
- `total_success` / `total_failure` — Count of successes and failures
- `success_rate` — Overall success rate as a percentage

**Per-task-type breakdown** (`by_task_type`):
```json
{
  "pick_and_place_simple": {"total": 50, "success": 42, "failure": 8, "success_rate": 84.0},
  "look_at_obj_in_light": {"total": 30, "success": 25, "failure": 5, "success_rate": 83.33}
}
```

**Failure category breakdown** (`by_failure_category`):
```json
{
  "object_not_found": 5,
  "navigation_failure": 3,
  "interaction_failure": 3,
  "visibility_error": 1,
  "inventory_error": 1
}
```

**Per-task results** (`results`): Each entry includes the task ID, task type, description, whether it succeeded, the list of executed steps, and — for failures — the step number, action text, error message, and categorized failure reason.

### Failure Categories

Failed plans are automatically categorized based on the simulator error message:

| Category | Meaning | Example Error |
|----------|---------|---------------|
| `object_not_found` | Target object not in scene or not locatable | "Cannot find mug" |
| `navigation_failure` | Agent cannot navigate to target | "Cannot move to mug" |
| `inventory_error` | Inventory state prevents action | "Robot is not holding any object" |
| `visibility_error` | Object hidden inside a closed receptacle | "mug is not visible because it is in Fridge" |
| `interaction_failure` | Simulator action failed despite finding object | "Open action failed" |
| `exception` | Unexpected Python exception during execution | Any caught Exception |
| `unknown` | Error doesn't match known patterns | Fallback |

### Example: Interpreting a Failed Task Result

```json
{
  "task_id": "trial_T20190907_174127_043461",
  "task_type": "look_at_obj_in_light",
  "task_description": "Examine an alarm clock under a desk lamp",
  "success": false,
  "executed_steps": ["find an alarm clock", "pick up the alarm clock"],
  "total_steps": 4,
  "failure_step": 3,
  "failure_action": "find a desk lamp",
  "failure_message": "Cannot find DeskLamp",
  "failure_category": "object_not_found",
  "goal_satisfied": false,
  "scene_name": "FloorPlan301"
}
```

This tells you: the plan failed at step 3 ("find a desk lamp") because the DeskLamp object was not found in the scene. Steps 1-2 executed successfully.

### Running Tests

Unit tests for the GT evaluator do not require AI2-THOR and can run anywhere:

```bash
pytest tests/test_gt_evaluator.py tests/test_gt_report.py -v
```

This runs 47 tests covering data loading, portion validation, random selection, failure categorization, report generation, and JSON serialization.

---

## ReAct Evaluation

The ReAct evaluation mode implements the ReAct paradigm (Yao et al., ICLR 2023) that interleaves LLM-generated Thought-Action-Observation steps in a closed loop. Unlike the base evaluator that generates a complete plan upfront, the ReAct planner reasons one step at a time, observes the result, and adapts.

### How It Works

1. The LLM receives a system prompt, few-shot examples, and the task instruction
2. At each step, the LLM generates a `Think:` (reasoning) and `Act:` (action) response
3. The action is executed in AI2-THOR and the result becomes an `Obs:` (observation)
4. The full history is fed back as a multi-turn conversation for the next step
5. The loop continues until the LLM outputs `done` or max steps is reached

The multi-turn conversation format (each Think+Act as an assistant message, each Obs as a user message) prevents the LLM from hallucinating future observation-action sequences.

### Running the Evaluation

**Evaluate 5% of valid_seen tasks (default):**
```bash
PYTHONPATH="alfred:src:$PYTHONPATH" python src/evaluate.py --config-name=config_alfred_react
```

**Evaluate a custom portion:**
```bash
# 10% of valid_seen tasks
PYTHONPATH="alfred:src:$PYTHONPATH" python src/evaluate.py --config-name=config_alfred_react \
    alfred.eval_portion_in_percent=10

# Different eval set
PYTHONPATH="alfred:src:$PYTHONPATH" python src/evaluate.py --config-name=config_alfred_react \
    alfred.eval_set=valid_unseen
```

**With a different model:**
```bash
PYTHONPATH="alfred:src:$PYTHONPATH" python src/evaluate.py --config-name=config_alfred_react \
    planner.model_name=gpt-4-turbo
```

### Configuration Parameters

All parameters live in `conf/config_alfred_react.yaml` and can be overridden from the command line:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `planner.provider` | `openai` | LLM provider (openai, vllm, etc.) |
| `planner.model_name` | `gpt-4` | Model to use for reasoning |
| `planner.max_steps` | `25` | Maximum Think-Act-Obs cycles per task |
| `planner.temperature` | `0.0` | Sampling temperature (0.0 = deterministic) |
| `planner.max_tokens` | `1024` | Max tokens per LLM response |
| `prompt.react_system_prompt` | `src/prompts/templates/react_system.txt` | System prompt file |
| `prompt.react_few_shot_examples` | `src/prompts/templates/react_few_shot_examples.txt` | Few-shot examples file |
| `alfred.eval_set` | `valid_seen` | Evaluation split (valid_seen or valid_unseen) |
| `alfred.eval_portion_in_percent` | `5` | Percentage of tasks to evaluate (1-100) |
| `alfred.random_seed_for_eval_subset` | `1` | Seed for reproducible task selection |
| `alfred.x_display` | `'0'` | X11 display number (Linux only) |

### Output

Results are saved to `outputs/alfred_react/{timestamp}/` (Hydra-managed output directory):

| File | Description |
|------|-------------|
| `react_summary.json` | Aggregate statistics: success rate, average steps, per-task-type breakdown |
| `{trial_id}.json` | Individual task result with full reasoning trace |
| `{trial_id}.png` | Composite image of annotated frames from the task execution |

### Reasoning Trace Format

Each task result includes a `reasoning_trace` array recording every step:

```json
{
  "trial_id": "trial_T20190907_174127_043461",
  "scene": "FloorPlan1",
  "task_type": "pick_and_place_simple",
  "instruction": "Put a plate in a cabinet.",
  "success": true,
  "total_steps": 6,
  "termination": "done_signal",
  "reasoning_trace": [
    {
      "step": 1,
      "thought": "I need to find a plate first.",
      "action": "find a plate",
      "observation": "Found plate. You are now near the plate on the countertop.",
      "success": true
    },
    {
      "step": 2,
      "thought": "I found the plate. Now I need to pick it up.",
      "action": "pick up the plate",
      "observation": "You picked up the plate.",
      "success": true
    }
  ]
}
```

### Few-Shot Examples

The prompt includes 7 few-shot examples covering all ALFRED task types:

| Example | Task Type | Key Steps |
|---------|-----------|-----------|
| Clean lettuce on diningtable | `pick_clean_then_place_in_recep` | find → pick → find sinkbasin → put → faucet on → faucet off → pick → find target → put |
| Examine pencil under desk lamp | `look_at_obj_in_light` | find → pick → find lamp → turn on |
| Hot egg in fridge | `pick_heat_then_place_in_recep` | find → pick → find microwave → open → put → close → on → off → open → pick → close → find fridge → open → put |
| Cooled mug on coffee table | `pick_cool_then_place_in_recep` | find → pick → find fridge → open → put → close → open → pick → close → find target → put |
| Knife on countertop | `pick_and_place_simple` | find → pick → find target → put |
| Slice of tomato on countertop | `pick_two_obj_and_place` (slice) | find knife → pick → find tomato → slice → put knife → pick slice → find target → put |
| Spatula in pan on countertop | `pick_and_place_with_movable_recep` | find spatula → pick → find pan → put in pan → pick pan → find target → put |

### Sequence Diagram

A detailed Mermaid sequence diagram of the ReAct planner flow is available at [`docs/react_sequence_diagram.md`](docs/react_sequence_diagram.md).

---

## Benchmarking on Watch-And-Help

### Download the VirtualHome Simulator
```bash
cd virtualhome/simulation/unity_simulator/
wget http://virtual-home.org//release/simulator/v2.0/v2.2.2/linux_exec.zip
unzip linux_exec.zip
cd ../../..
```

### Run Benchmarking

1. Start VirtualHome simulator in one terminal:
    ```bash
    ./virtualhome/simulation/unity_simulator/linux_exec.x86_64
    ```

2. Run evaluation in another terminal:
    ```bash
    python src/evaluate.py --config-name=config_wah \
        planner.provider=openai \
        planner.model_name=gpt-4
    ```

### Headless Server Setup

1. Start Xserver:
    ```bash
    cd virtualhome
    sudo python helper_scripts/startx.py $display_num
    ```

2. Start simulator in batchmode:
    ```bash
    DISPLAY=:$display_num ./simulation/unity_simulator/linux_exec.x86_64 -batchmode
    ```

3. Run evaluation:
    ```bash
    python src/evaluate.py --config-name=config_wah_headless \
        planner.provider=openai \
        planner.model_name=gpt-4
    ```


## Extensions

### In-context Example Selection
```bash
python src/evaluate.py --config-name=config_wah prompt.select_method=same_task
python src/evaluate.py --config-name=config_wah prompt.select_method=topk
```

### Replanning with Feedback
```bash
python src/evaluate.py --config-name=config_alfred planner.use_predefined_prompt=True
```


## Customizing Prompts

The system uses externalized prompt templates that can be easily customized without modifying code.

### Prompt Template Files

All prompt templates are stored in `src/prompts/templates/`:

| File | Purpose |
|------|---------|
| `action_selection_system.txt` | System message for action selection |
| `action_selection_user.txt` | User message template for action selection |
| `plan_generation_system.txt` | System message for plan generation |
| `plan_generation_user.txt` | User message template for plan generation |
| `step_by_step_format.txt` | Format for initial step-by-step prompt |
| `step_continuation.txt` | Format for continuing steps |
| `step_with_failure.txt` | Format for steps that failed |
| `react_system.txt` | ReAct planner system prompt (actions, format rules, task procedures) |
| `react_few_shot_examples.txt` | ReAct few-shot examples (7 examples covering all ALFRED task types) |

### Customization Examples

**Change the robot's persona** by editing `plan_generation_system.txt`:
```
You are a helpful home assistant robot. When given a task, you carefully plan
each step to accomplish it safely and efficiently.
```

**Change action selection behavior** by editing `action_selection_system.txt`:
```
You are a robot operating in a home environment. Given the current situation
and a list of possible actions, select the single best action to take next.
Respond with ONLY the exact action text.
```

### Template Variables

Templates use Python's `str.format()` syntax for variable substitution:

| Template | Variables |
|----------|-----------|
| `action_selection_user.txt` | `{prompt}`, `{candidates}` |
| `plan_generation_user.txt` | `{examples}`, `{skills}`, `{query}` |
| `step_by_step_format.txt` | `{query}` |
| `step_continuation.txt` | `{step}`, `{next_step_num}` |
| `step_with_failure.txt` | `{step}`, `{failure_message}`, `{next_step_num}` |


## WAH-NL Dataset

You can find the WAH-NL data, which is our extension of WAH, in `./dataset` folder.


## Action Primitives

The agent interacts with the AI2-THOR simulator through a set of action primitives. Each primitive is issued as a natural-language instruction string and executed via `ThorConnector.llm_skill_interact()`.

All actions return a result dict:
```python
{"action": "find a apple", "success": True, "message": ""}
```

### Generic Actions

Generic actions target objects by type. The simulator selects the closest matching instance automatically.

| Instruction Format | Action | Example |
|-------------------|--------|---------|
| `find a/an <object>` | Navigate to nearest object of type | `find a apple`, `find an egg` |
| `pick up the <object>` | Pick up the nearest object of type | `pick up the mug` |
| `put down the <object>` | Place held object on current receptacle | `put down the apple` |
| `open the <object>` | Open a container | `open the fridge` |
| `close the <object>` | Close a container | `close the microwave` |
| `turn on the <object>` | Toggle a device on | `turn on the desk lamp` |
| `turn off the <object>` | Toggle a device off | `turn off the faucet` |
| `slice the <object>` | Slice a sliceable object (requires holding a knife) | `slice the bread` |
| `drop` | Drop the currently held object | `drop` |
| `done` | Terminate the plan | `done` |

**Object categories:**

| Category | Objects |
|----------|---------|
| **Pickupable** (51) | Apple, Bread, Mug, Knife, Egg, Tomato, Potato, Lettuce, Plate, Bowl, Cup, Fork, Spoon, ... |
| **Openable** (7) | Safe, Laptop, Fridge, Box, Microwave, Cabinet, Drawer |
| **Sliceable** (5) | Potato, Lettuce, Tomato, Apple, Bread |
| **Toggleable** (4) | Microwave, DeskLamp, FloorLamp, Faucet |
| **Receptacles** (30) | CounterTop, Sink, Fridge, DiningTable, Shelf, Drawer, Cabinet, Bed, Desk, ... |

### Instance-Specific Actions

Instance-specific actions target a particular object by its registry ID (e.g., `Apple_1`, `Mug_02`). This allows the agent to disambiguate between multiple objects of the same type.

**Instance ID format:** `<ObjectType>_<number>` — CamelCase type name, underscore, numeric suffix (e.g., `Apple_1`, `DeskLamp_02`, `StoveBurner_1`). Leading zeros are normalized (`Apple_01` resolves to the same object as `Apple_1`).

| Instruction Format | Action | Example |
|-------------------|--------|---------|
| `find <InstanceID>` | Navigate to specific instance | `find Apple_1` |
| `pick up <InstanceID>` | Pick up specific instance | `pick up Mug_02` |
| `open <InstanceID>` | Open specific container | `open Fridge_1` |
| `close <InstanceID>` | Close specific container | `close Cabinet_3` |
| `turn on <InstanceID>` | Toggle specific device on | `turn on DeskLamp_1` |
| `turn off <InstanceID>` | Toggle specific device off | `turn off FloorLamp_2` |
| `slice <InstanceID>` | Slice specific instance | `slice Bread_1` |

**How it works:**
1. On scene load, an **object registry** maps each AI2-THOR objectId (e.g., `Mug|01|02|03|04`) to a human-readable name (e.g., `Mug_1`)
2. When an instruction contains an instance ID, the system resolves it to the exact AI2-THOR objectId via the reverse registry
3. The resolved objectId is passed directly to the action method, bypassing the type-based closest-object lookup
4. After a `slice` action, the registry is rebuilt to include newly created sliced instances

**Mixed-mode plans** are fully supported — generic and instance-specific actions can be freely interleaved:
```
1. find Apple_1          # instance: navigate to specific apple
2. pick up the apple     # generic: pick up nearest apple
3. find Fridge_1         # instance: navigate to specific fridge
4. open the fridge       # generic: open nearest fridge
5. put down the apple    # generic: put down on current receptacle
6. close Fridge_1        # instance: close specific fridge
```

### Skill Set Generation

The `AlfredTaskPlanner` provides two methods for generating candidate action lists for LLM planners:

- **`init_skill_set()`** — Generates generic skill set from hardcoded object categories (e.g., `find a apple`, `pick up the mug`). Used for type-based planning.
- **`init_instance_skill_set(registry, object_metadata)`** — Generates instance-aware skill set from the live scene registry. Cross-references each object's properties (pickupable, openable, toggleable, sliceable) to produce only valid actions per instance (e.g., `find Apple_1`, `pick up Apple_1`, `slice Apple_1` but not `open Apple_1`).

---

## CLI Reference

The system uses a single entry point with [Hydra](https://hydra.cc/) configuration management:

```bash
python src/evaluate.py --config-name=<CONFIG> [OVERRIDES...]
```

### Evaluation Modes

| Config Name | Mode | Description |
|------------|------|-------------|
| `config_alfred` | LLM-based ALFRED | Run an LLM planner on ALFRED tasks in AI2-THOR |
| `config_alfred_gt` | Ground-truth ALFRED | Execute known-correct plans to validate the simulator |
| `config_alfred_react` | ReAct ALFRED | Run a ReAct (Thought-Action-Observation) planner on ALFRED tasks |
| `config_wah` | Watch-And-Help | Run an LLM planner on WAH tasks in VirtualHome |
| `config_wah_headless` | WAH (headless) | Same as `config_wah` for headless server setups |

### Common Options

These options apply across all evaluation modes:

```bash
# LLM provider selection
planner.provider=openai          # openai, vllm, ollama, lmstudio
planner.model_name=gpt-4         # model identifier for the provider
planner.api_base=http://...      # custom API endpoint URL

# Planning behavior
planner.max_steps=30             # maximum action steps per task
planner.random_seed=42           # seed for reproducibility
planner.reasoning_effort=medium  # low/medium/high (for o1/o3/GPT-5.x)
planner.use_predefined_prompt=True  # use predefined prompt (enables replanning with feedback)

# Prompt configuration
prompt.num_examples=6            # number of in-context examples
prompt.select_method=uniform     # uniform, same_task, topk
```

### ALFRED Options (`config_alfred`)

```bash
alfred.x_display='0'                    # X11 display number (Linux)
alfred.eval_set=valid_seen              # valid_seen or valid_unseen
alfred.eval_portion_in_percent=5        # percentage of tasks to evaluate (1-100)
alfred.random_seed_for_eval_subset=1    # seed for task subset selection
```

### Ground-Truth Options (`config_alfred_gt`)

```bash
gt.eval_portion_in_percent=5     # percentage of GT plans to evaluate (1-100)
gt.random_seed=42                # seed for reproducible task selection
gt.gt_data_file=resource/alfred_examples_for_prompt.json  # ground-truth data file
gt.x_display='0'                 # X11 display number (Linux)
gt.trial_id=null                 # evaluate a single specific trial ID
```

### WAH Options (`config_wah`)

```bash
planner.scoring_batch_size=10    # batch size for scoring
planner.score_function=sum       # scoring function
planner.dynamic_skill_set=False  # dynamic skill set updates

dataset.wah_testset=dataset/wah_nl_test.json    # test set path
dataset.wah_trainset=dataset/wah_nl_train.json  # training set path

environment.use_editor=True      # use Unity editor mode
environment.base_port=8080       # VirtualHome base port
environment.port_id=1            # port offset
```

### Quick Examples

```bash
# ALFRED with GPT-4, 10% of valid_seen tasks
python src/evaluate.py --config-name=config_alfred \
    planner.provider=openai planner.model_name=gpt-4 \
    alfred.eval_portion_in_percent=10

# ALFRED with local vLLM, step-by-step planning
vllm serve meta-llama/Llama-2-7b-chat-hf --port 8000
python src/evaluate.py --config-name=config_alfred \
    planner.provider=vllm planner.model_name=meta-llama/Llama-2-7b-chat-hf

# ALFRED with Ollama
python src/evaluate.py --config-name=config_alfred \
    planner.provider=ollama planner.model_name=llama2

# ALFRED with LM Studio on a remote server
python src/evaluate.py --config-name=config_alfred \
    planner.provider=lmstudio planner.model_name=openai/gpt-oss-20b \
    planner.api_base=http://10.254.90.90:1234/v1

# Ground-truth evaluation: all plans, seed 0
python src/evaluate.py --config-name=config_alfred_gt \
    gt.eval_portion_in_percent=100 gt.random_seed=0

# Ground-truth evaluation: single trial
python src/evaluate.py --config-name=config_alfred_gt \
    gt.trial_id=trial_T20190907_174127_043461

# ReAct planner: 5% of valid_seen with GPT-4
PYTHONPATH="alfred:src:$PYTHONPATH" python src/evaluate.py --config-name=config_alfred_react

# ReAct planner: 10% with GPT-4-turbo
PYTHONPATH="alfred:src:$PYTHONPATH" python src/evaluate.py --config-name=config_alfred_react \
    planner.model_name=gpt-4-turbo alfred.eval_portion_in_percent=10

# WAH with GPT-4 and same-task example selection
python src/evaluate.py --config-name=config_wah \
    planner.provider=openai planner.model_name=gpt-4 \
    prompt.select_method=same_task

# Reasoning model with high effort
python src/evaluate.py --config-name=config_alfred \
    planner.model_name=gpt-5.2 planner.reasoning_effort=high
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Instance-specific action tests only (53 tests)
pytest tests/test_instance_actions.py -v

# Ground-truth evaluator tests only (47 tests)
pytest tests/test_gt_evaluator.py tests/test_gt_report.py -v

# ReAct planner tests only (27 tests)
pytest tests/test_react_planner.py -v

# AI2-THOR compatibility tests only
pytest tests/test_ai2thor_compatibility.py -v

# Lint check
ruff check src/
```

---

## Project Structure

```
LLMTaskPlanning/
├── src/
│   ├── evaluate.py             # Main entry point (dispatches by config name)
│   ├── evaluator.py            # Base Evaluator class
│   ├── task_planner.py         # Base task planner
│   ├── llm/                    # LLM provider abstraction
│   │   ├── base.py             # Abstract base class
│   │   ├── factory.py          # Provider factory
│   │   ├── openai_provider.py  # OpenAI implementation
│   │   ├── vllm_provider.py    # vLLM implementation
│   │   ├── ollama_provider.py  # Ollama implementation
│   │   └── lmstudio_provider.py # LM Studio implementation
│   ├── prompts/                # Prompt template system
│   │   ├── loader.py           # Template loader
│   │   └── templates/          # Externalized prompt templates
│   ├── alfred/                 # ALFRED evaluators
│   │   ├── alfred_evaluator.py # LLM-based evaluation
│   │   ├── alfred_task_planner.py # Skill set generation (generic + instance-aware)
│   │   ├── gt_evaluator.py     # Ground-truth plan evaluation
│   │   ├── gt_report.py        # Failure categorization & report generation
│   │   ├── react_evaluator.py  # ReAct evaluation loop (Thought-Action-Observation)
│   │   ├── react_task_planner.py # ReAct planner (LLM calls, parsing, message building)
│   │   ├── thor_connector.py   # AI2-THOR simulator interface & action primitives
│   │   └── utils.py            # Shared utilities (load_task_json, name conversion)
│   └── wah/                    # Watch-And-Help evaluator
├── conf/                       # Hydra configurations
│   ├── config_alfred.yaml      # LLM-based ALFRED evaluation
│   ├── config_alfred_gt.yaml   # Ground-truth plan evaluation
│   ├── config_alfred_react.yaml # ReAct planner evaluation
│   ├── config_wah.yaml         # Watch-And-Help evaluation
│   └── config_wah_headless.yaml # WAH headless server setup
├── tests/                      # Test suite (no simulator required)
│   ├── test_instance_actions.py    # Instance-specific action tests (53 tests)
│   ├── test_gt_evaluator.py        # GT evaluator unit tests (24 tests)
│   ├── test_gt_report.py           # GT report unit tests (23 tests)
│   ├── test_react_planner.py       # ReAct planner unit tests (27 tests)
│   ├── test_ai2thor_compatibility.py # AI2-THOR 5.x compatibility tests
│   └── test_llm_providers.py       # LLM provider unit tests
├── resource/                   # Prompt examples & ground-truth data
├── alfred/                     # ALFRED environment & dataset
├── virtualhome/                # VirtualHome environment
└── dataset/                    # WAH-NL dataset
```


## FAQ

**Q: I encounter 'cannot find X server with xdpyinfo' in running ALFRED experiments.**

A: Try a different x_display number:
```bash
python src/evaluate.py --config-name=config_alfred alfred.x_display='1'
```

**Q: How do I use a custom API endpoint?**

A: Set the API base URL in your `.env` file:
```bash
OPENAI_API_BASE=https://your-custom-endpoint.com/v1
```

**Q: Which planning mode should I use?**

A: The system automatically selects the appropriate mode:
- API providers (OpenAI) → `plan_whole` (faster, single API call)
- Local providers (vLLM) → `plan_step_by_step` (better for smaller models)


## Citation

```bibtex
@inproceedings{choi2024lota,
  title={LoTa-Bench: Benchmarking Language-oriented Task Planners for Embodied Agents},
  author={Choi, Jae-Woo and Yoon, Youngwoo and Ong, Hyobin and Kim, Jaehong and Jang, Minsu},
  booktitle={International Conference on Learning Representations (ICLR)},
  year={2024}
}
```
