# ReAct Planner Sequence Diagram

## Overview

The ReAct (Reasoning + Acting) planner interleaves LLM-generated thoughts and actions
with environment observations in a closed loop until the task is complete or max steps reached.

## Sequence Diagram

```mermaid
sequenceDiagram
    participant E as evaluate.py
    participant RE as ReActAlfredEvaluator
    participant P as ReActTaskPlanner
    participant Parse as parse_react_output()
    participant LLM as OpenAI API (GPT-4)
    participant Env as ThorConnector (AI2-THOR)
    participant Obs as construct_observation()

    %% === Initialization Phase ===
    Note over E,Env: Initialization Phase

    E->>RE: evaluate()
    RE->>P: ReActTaskPlanner(cfg)
    P->>P: init_prompt(cfg)
    Note right of P: Load react_system.txt
    P->>P: _load_few_shot_examples(cfg)
    Note right of P: Load react_few_shot_examples.txt
    P->>P: LLMProviderFactory.from_config(cfg)
    Note right of P: Initialize OpenAI client

    RE->>RE: Load splits, select 5% subset
    RE->>Env: ThorConnector(x_display)
    Note right of Env: Start AI2-THOR Unity process

    %% === Per-Task Loop ===
    Note over E,Env: Per-Task Evaluation Loop (for each task in subset)

    RE->>Env: reset(scene_name)
    RE->>Env: restore_scene(poses, toggles, dirty)
    RE->>Env: step(init_action)
    RE->>Env: set_task(traj_data, args, reward)
    RE->>RE: instruction = traj_data['turk_annotations']

    %% === ReAct Loop ===
    Note over RE,Env: ReAct Loop (while not done and t < max_steps)

    loop Step t = 1, 2, ..., max_steps

        %% --- LLM Call ---
        RE->>P: react_step(instruction, history)

        P->>P: _build_messages(instruction, history)
        Note right of P: Build multi-turn messages:<br/>1. system: react_system.txt<br/>2. user: few_shot + "Task: ..."<br/>3. For each history step:<br/>   assistant: "Think:...\nAct:..."<br/>   user: "Obs: ..."

        P->>LLM: chat_completion(messages, temp=0.0)
        LLM-->>P: raw_response: "Think: I need to...\nAct: find a plate"

        %% --- Parsing ---
        P->>Parse: parse_react_output(raw_response)
        Note right of Parse: Extract Think: ... and Act: ...<br/>Truncate action at first \n<br/>(防止 hallucinated multi-step)
        Parse-->>P: (thought, action)

        P-->>RE: (thought, action)

        %% --- Done Check ---
        alt action == "done"
            RE->>RE: done = True, termination = "done_signal"
            Note right of RE: Break loop
        else action is environment command

            %% --- Environment Execution ---
            RE->>Env: llm_skill_interact(action)
            Note right of Env: Dispatches to:<br/>find → nav_obj()<br/>pick up → pick()<br/>put down → put()<br/>open → open_obj()<br/>close → close_obj()<br/>turn on/off → toggle()<br/>slice → slice_obj()
            Env-->>RE: action_ret = {action, success, message}

            %% --- Observation Construction ---
            RE->>Obs: construct_observation(action_ret)
            alt success == True
                Obs-->>RE: "Found plate. You are now near the plate."
            else success == False
                Obs-->>RE: "Action failed: find a soap. Cannot find Soap"
            end

            %% --- Record & Append ---
            RE->>RE: reasoning_trace.append({step, thought, action, obs})
            RE->>RE: history.append({thought, action, observation})
            Note right of RE: history feeds into next<br/>_build_messages() call

            RE->>Env: write_step_on_img(t, action_ret)
            Note right of Env: Annotate frame with step info
        end
    end

    %% === Post-Loop ===
    Note over RE,Env: Post-Loop: Goal Check & Save

    RE->>Env: get_goal_satisfied()
    Env-->>RE: goal_satisfied (bool)

    RE->>RE: Build log_entry {trial, scene, type, success,<br/>total_steps, reasoning_trace, inferred_steps}

    RE->>RE: save_result(log_entry, imgs, save_path)
    Note right of RE: Save .json + composite .png

    %% === Summary ===
    Note over E,Env: After All Tasks

    RE->>RE: build_summary_report(results)
    Note right of RE: Aggregate: success_rate,<br/>avg_steps, by_task_type
    RE->>RE: Save react_summary.json
```

## Message Structure Detail

At step `t`, `_build_messages()` produces this chat history:

```
┌─────────────────────────────────────────────────────┐
│ role: system                                        │
│ content: react_system.txt                           │
│   (actions list, format rules, task procedures)     │
├─────────────────────────────────────────────────────┤
│ role: user                                          │
│ content: react_few_shot_examples.txt + "\n"         │
│          + "Task: Put a plate in a cabinet."        │
├─────────────────────────────────────────────────────┤
│ role: assistant  ← injected from history[0]         │
│ content: "Think: I need to find a plate.\n          │
│           Act: find a plate"                        │
├─────────────────────────────────────────────────────┤
│ role: user       ← injected from history[0]         │
│ content: "Obs: Found plate. You are near the plate."│
├─────────────────────────────────────────────────────┤
│ role: assistant  ← injected from history[1]         │
│ content: "Think: Now I pick it up.\n                │
│           Act: pick up the plate"                   │
├─────────────────────────────────────────────────────┤
│ role: user       ← injected from history[1]         │
│ content: "Obs: You picked up the plate."            │
├─────────────────────────────────────────────────────┤
│ ... (model generates next Think + Act here) ...     │
└─────────────────────────────────────────────────────┘
```

## Data Flow Summary

```
                    ┌──────────────┐
                    │  System Prompt│
                    │  + Few-Shot   │
                    └──────┬───────┘
                           │
              ┌────────────▼────────────┐
              │   _build_messages()     │◄──── history[]
              │   (multi-turn format)   │
              └────────────┬────────────┘
                           │ messages
                    ┌──────▼───────┐
                    │  OpenAI API  │
                    │  (GPT-4)     │
                    └──────┬───────┘
                           │ raw text
                ┌──────────▼──────────┐
                │ parse_react_output()│
                │ Extract Think + Act │
                │ Truncate at \n      │
                └──────────┬──────────┘
                           │ (thought, action)
                    ┌──────▼───────┐
               ┌────┤  "done"?     ├────┐
               │ no └──────────────┘yes │
               │                        │
        ┌──────▼──────┐          ┌──────▼──────┐
        │  AI2-THOR   │          │  Check Goal │
        │  Execute    │          │  Save Result│
        └──────┬──────┘          └─────────────┘
               │ {action, success, message}
     ┌─────────▼─────────┐
     │construct_observation│
     │ → NL observation   │
     └─────────┬─────────┘
               │
        ┌──────▼──────┐
        │ Append to   │
        │ history[]   │──── feeds back to _build_messages()
        └─────────────┘
```
