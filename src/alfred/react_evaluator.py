"""ReAct evaluation loop for ALFRED household tasks.

Implements the Thought-Action-Observation loop that:
1. Calls planner.react_step() to generate thought + action
2. Executes action via env.llm_skill_interact()
3. Constructs natural language observation from result
4. Records full reasoning trace for analysis

Critical difference from AlfredEvaluator: does NOT stop on action failure.
Failed actions become observations that inform the next reasoning step.
"""

import json
import logging
import os
import time
import datetime

from src.alfred.alfred_evaluator import AlfredEvaluator
from src.alfred.react_task_planner import ReActTaskPlanner

log = logging.getLogger(__name__)


def construct_observation(action_result: dict) -> str:
    """Construct a natural language observation from action result.

    Args:
        action_result: Dict from llm_skill_interact() with keys:
            - action: str
            - success: bool
            - message: str

    Returns:
        Natural language observation string.
    """
    action = action_result['action']
    success = action_result['success']
    message = action_result.get('message', '')

    if not success:
        return f"Action failed: {action}. {message}".strip()

    # Parse action type and object
    if action.startswith("find "):
        obj = action.replace("find a ", "").replace("find an ", "").replace("find ", "")
        return f"Found {obj}. You are now near the {obj}."

    elif action.startswith("pick up "):
        obj = action.replace("pick up the ", "").replace("pick up ", "")
        return f"You picked up the {obj}."

    elif action.startswith("put down "):
        obj = action.replace("put down the ", "").replace("put down ", "")
        return f"You put the {obj} down."

    elif action.startswith("open "):
        obj = action.replace("open the ", "").replace("open ", "")
        return f"You opened the {obj}."

    elif action.startswith("close "):
        obj = action.replace("close the ", "").replace("close ", "")
        return f"You closed the {obj}."

    elif action.startswith("turn on "):
        obj = action.replace("turn on the ", "").replace("turn on ", "")
        return f"You turned on the {obj}."

    elif action.startswith("turn off "):
        obj = action.replace("turn off the ", "").replace("turn off ", "")
        return f"You turned off the {obj}."

    elif action.startswith("drop "):
        obj = action.replace("drop the ", "").replace("drop ", "")
        return f"You dropped the {obj} on the floor."

    elif action.startswith("slice "):
        obj = action.replace("slice the ", "").replace("slice ", "")
        return f"You sliced the {obj}."

    else:
        return f"Action completed: {action}"


class ReActAlfredEvaluator(AlfredEvaluator):
    """Evaluator that uses the ReAct planner for ALFRED tasks.

    Overrides evaluate() to use ReActTaskPlanner and evaluate_task()
    with the Thought-Action-Observation loop.
    """

    def __init__(self, hparams):
        super().__init__(hparams)

    def evaluate(self):
        """Run evaluation using ReActTaskPlanner instead of AlfredTaskPlanner."""
        cfg = self.cfg

        log.info("Starting ReAct evaluation")

        # Create ReAct planner
        if len(cfg.planner.model_name) > 0:
            planner = ReActTaskPlanner(cfg)
        else:
            planner = None

        # Reuse parent's dataset loading and subset selection
        import random
        import pprint

        splits_path = 'alfred/data/splits/oct21.json'
        with open(splits_path) as f:
            splits = json.load(f)
            pprint.pprint({k: len(v) for k, v in splits.items()})

        # Preprocessing check
        args_dict = {'data': 'alfred/data/json_2.1.0', 'pframe': 300, 'fast_epoch': False,
                     'use_templated_goals': False, 'dout': 'exp/model', 'pp_folder': 'pp',
                     'reward_config': 'alfred/models/config/rewards.json', 'max_steps': 1000}

        number_of_dirs = len(list(os.listdir(args_dict['data'])))
        do_preprocessing = number_of_dirs < 50
        if do_preprocessing:
            from alfred.data.preprocess import Dataset
            from src.alfred.utils import dotdict
            log.info("\nPreprocessing dataset...")
            dataset = Dataset(dotdict(args_dict), None)
            dataset.preprocess_splits(splits)

        # Load tasks
        assert cfg.alfred.eval_set in splits.keys()
        files = []
        for e in splits[cfg.alfred.eval_set]:
            if 'pick_two_obj_and_place' not in e['task']:
                files.append(e)

        # Select subset
        if cfg.alfred.eval_portion_in_percent < 100:
            seed = cfg.alfred.random_seed_for_eval_subset
            random.seed(seed)
            n_sample = max(1, int(len(files) * cfg.alfred.eval_portion_in_percent / 100))

            stratified = getattr(cfg.alfred, 'stratified_sampling', False)
            if stratified:
                # Group tasks by high-level ALFRED task type
                from collections import defaultdict
                ALFRED_TASK_TYPES = [
                    'pick_and_place_with_movable_recep',
                    'pick_clean_then_place_in_recep',
                    'pick_heat_then_place_in_recep',
                    'pick_cool_then_place_in_recep',
                    'pick_and_place_simple',
                    'look_at_obj_in_light',
                ]

                def _extract_task_type(task_path: str) -> str:
                    for t in ALFRED_TASK_TYPES:
                        if task_path.startswith(t):
                            return t
                    return task_path.split('-')[0]

                by_type = defaultdict(list)
                for e in files:
                    task_type = _extract_task_type(e['task'])
                    by_type[task_type].append(e)

                selected = []
                remaining_pool = []
                for task_type, tasks in by_type.items():
                    random.shuffle(tasks)
                    selected.append(tasks[0])
                    remaining_pool.extend(tasks[1:])

                # Fill remaining slots from the pool
                extra_needed = max(0, n_sample - len(selected))
                if extra_needed > 0:
                    random.shuffle(remaining_pool)
                    selected.extend(remaining_pool[:extra_needed])

                files = selected
                log.info(f"Stratified sampling: {len(files)} tasks across "
                         f"{len(by_type)} task types")
            else:
                files = random.sample(files, n_sample)

            random.seed(cfg.planner.random_seed)

        # Load validation report for instruction filtering
        validation_lookup = {}
        validation_report_path = getattr(cfg.alfred, 'validation_report', '')
        skip_categories = list(getattr(cfg.alfred, 'skip_categories', [1]))
        if validation_report_path:
            from src.alfred.instruction_validator import load_validation_report
            validation_lookup = load_validation_report(validation_report_path)
            log.info("Loaded validation report from %s (%d entries, skipping categories %s)",
                     validation_report_path, len(validation_lookup), skip_categories)

        # Run evaluation
        start = time.time()
        x_display = cfg.alfred.x_display
        save_path = cfg.out_dir

        from src.alfred.thor_connector import ThorConnector
        from src.alfred.utils import dotdict, load_task_json
        from tqdm import tqdm

        results = []
        model_args = dotdict(args_dict)
        env = ThorConnector(x_display=x_display)

        # Save prompt
        if planner is not None:
            with open(os.path.join(save_path, 'prompt.txt'), 'w') as f:
                f.write(planner.system_prompt + "\n\n" + planner.few_shot_examples)

        skipped_count = 0
        for i, task in enumerate(tqdm(files)):
            # Check validation report — skip flagged instructions
            if validation_lookup:
                key = (task['task'], task['repeat_idx'])
                val_entry = validation_lookup.get(key)
                if val_entry and val_entry['category'] in skip_categories:
                    skipped_count += 1
                    log.info("Skipping (%d/%d) %s (repeat %d): %s — %s",
                             i + 1, len(files), task['task'], task['repeat_idx'],
                             val_entry.get('category_label', ''),
                             val_entry.get('reason', ''))
                    results.append({
                        'trial': val_entry.get('task_path', task['task']),
                        'repeat_idx': task['repeat_idx'],
                        'skipped': True,
                        'skip_reason': val_entry.get('category_label', ''),
                        'skip_category': val_entry['category'],
                    })
                    continue

            try:
                log.info(task)
                traj_data = load_task_json(task, split=cfg.alfred.eval_set)
                r_idx = task['repeat_idx']
                log.info(f"Evaluating ({i+1}/{len(files)}): {traj_data['root']}")
                result = self.evaluate_task(env, traj_data, r_idx, model_args,
                                           planner, save_path, x_display=x_display)
                results.append(result)
            except ValueError as e:
                if "closed file" in str(e) or "closed pipe" in str(e):
                    log.warning("AI2-THOR connection lost, restarting environment...")
                    try:
                        env.controller.stop()
                    except Exception:
                        pass
                    env = ThorConnector(x_display=x_display)
                    log.info("Environment restarted successfully")
                else:
                    import traceback
                    traceback.print_exc()
                    log.info("Error: " + repr(e))
            except Exception as e:
                import traceback
                traceback.print_exc()
                log.info("Error: " + repr(e))

        # Print and save summary
        evaluated_results = [r for r in results if not r.get('skipped', False)]
        summary = self.build_summary_report(evaluated_results)
        summary['total_skipped'] = skipped_count
        log.info(f"\n{'='*60}")
        log.info("ReAct Evaluation Summary")
        log.info(f"{'='*60}")
        if skipped_count > 0:
            log.info(f"Skipped (validation filter): {skipped_count}")
        log.info(f"Total evaluated: {summary['total_evaluated']}")
        log.info(f"Total success: {summary['total_success']}")
        log.info(f"Success rate: {summary['success_rate']*100:.2f}%")
        log.info(f"Average steps: {summary['avg_steps']:.1f}")
        log.info("\nBy task type:")
        for task_type, stats in summary['by_task_type'].items():
            log.info(f"  {task_type}: {stats['success']}/{stats['total']} "
                    f"({stats['success_rate']*100:.1f}%)")
        log.info(f"\nElapsed: {str(datetime.timedelta(seconds=(time.time() - start)))}")

        # Save summary JSON
        summary_path = os.path.join(save_path, 'react_summary.json')
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        log.info(f"Summary saved to {summary_path}")

    def evaluate_task(self, env, traj_data, r_idx, model_args, planner, save_path,
                      log_prompt=False, train_gt_steps=None, x_display='0'):
        """Evaluate a single task using the ReAct loop.

        Critical difference from parent: does NOT stop on action failure.
        Failed actions become observations for the next reasoning step.
        """
        # Setup scene (reuse parent pattern)
        scene_num = traj_data['scene']['scene_num']
        object_poses = traj_data['scene']['object_poses']
        dirty_and_empty = traj_data['scene']['dirty_and_empty']
        object_toggles = traj_data['scene']['object_toggles']

        scene_name = 'FloorPlan%d' % scene_num
        env.reset(scene_name)
        env.restore_scene(object_poses, object_toggles, dirty_and_empty)

        # Initialize
        env.step(dict(traj_data['scene']['init_action']))
        env.set_task(traj_data, model_args, reward_type='dense')

        # Get task instruction
        instruction_text = traj_data['turk_annotations']['anns'][r_idx]['task_desc']
        log.info("Task: %s" % instruction_text)

        # Extract unique object types from the scene registry
        available_objects = None
        if hasattr(env, '_obj_registry') and env._obj_registry:
            available_objects = sorted(set(
                name.rsplit('_', 1)[0] for name in env._obj_registry.values()
            ))
            log.info("Available objects: %s", ", ".join(available_objects))

        # ReAct loop
        history = []
        reasoning_trace = []
        done = False
        success = False
        termination_reason = "max_steps"
        t = 0
        consecutive_failures = 0
        MAX_CONSECUTIVE_FAILURES = 3

        try:
            from PIL import Image
            imgs = [Image.fromarray(env.last_event.frame)]
        except Exception:
            imgs = []

        max_steps = planner.max_steps if planner else 25

        while not done and t < max_steps:
            t += 1

            # Generate thought + action
            try:
                thought, action = planner.react_step(
                    instruction_text, history,
                    available_objects=available_objects)
                consecutive_failures = 0  # reset on success
            except ValueError as e:
                consecutive_failures += 1
                log.warning(f"ReAct step {t} failed ({consecutive_failures}/"
                            f"{MAX_CONSECUTIVE_FAILURES}): {e}")
                # Record the malformed step but don't add it to history
                # so the model doesn't see garbage in its next context.
                reasoning_trace.append({
                    'step_number': t,
                    'thought': '',
                    'action': f'[malformed: {e}]',
                    'observation': None,
                    'action_success': False,
                })
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    log.warning("Too many consecutive malformed responses, "
                                "skipping task.")
                    termination_reason = "malformed_output"
                    break
                # Continue to next step — the model gets a fresh chance
                # without the garbage polluting its history.
                continue

            log.info(f"Step {t}: Think: {thought}")
            log.info(f"Step {t}: Act: {action}")

            # Build trace entry
            trace_entry = {
                'step_number': t,
                'thought': thought,
                'action': action,
                'observation': None,
                'action_success': None,
            }

            # Check for done signal
            if action.strip().lower() in ['done', 'done.', 'done.\n']:
                trace_entry['observation'] = None
                trace_entry['action_success'] = None
                reasoning_trace.append(trace_entry)
                history.append({
                    'thought': thought,
                    'action': action,
                    'observation': 'Task completed.'
                })
                done = True
                termination_reason = "done_signal"
                break

            # Execute action in environment
            try:
                action_ret = env.llm_skill_interact(action)
            except Exception as e:
                log.warning(f"Exception during step execution: {e}")
                action_ret = {
                    'action': action,
                    'success': False,
                    'message': f'Exception: {e}'
                }

            # Construct observation
            observation = construct_observation(action_ret)
            log.info(f"Step {t}: Obs: {observation}")

            # Record in trace
            trace_entry['observation'] = observation
            trace_entry['action_success'] = action_ret['success']
            reasoning_trace.append(trace_entry)

            # Add to history for next step
            history.append({
                'thought': thought,
                'action': action,
                'observation': observation,
            })

            # Capture image
            try:
                imgs.append(env.write_step_on_img(False, t, action_ret))
            except Exception:
                pass

            # NOTE: Do NOT break on failure -- failure becomes observation
            # This is the key difference from the parent evaluator

        # Check if goal was satisfied
        try:
            goal_satisfied = env.get_goal_satisfied()
            log.info('target goal: ' + json.dumps(env.task.get_targets()))
            log.info('success: ' + str(goal_satisfied))
            if goal_satisfied:
                success = True
        except Exception:
            pass

        # Record results
        inferred_steps = [entry['action'] for entry in reasoning_trace]
        log_entry = {
            'trial': traj_data['task_id'],
            'scene': scene_name,
            'type': traj_data['task_type'],
            'repeat_idx': int(r_idx),
            'goal_instr': instruction_text,
            'success': success,
            'total_steps': len(reasoning_trace),
            'termination_reason': termination_reason,
            'reasoning_trace': reasoning_trace,
            'inferred_steps': inferred_steps,
        }

        # Save result
        self.save_result(log_entry, imgs, save_path)

        return log_entry

    @staticmethod
    def build_summary_report(results: list) -> dict:
        """Build aggregate evaluation summary from individual results.

        Args:
            results: List of per-task result dicts

        Returns:
            Summary dict with total_evaluated, total_success, success_rate,
            avg_steps, and by_task_type breakdown.
        """
        if not results:
            return {
                'total_evaluated': 0,
                'total_success': 0,
                'success_rate': 0.0,
                'avg_steps': 0.0,
                'by_task_type': {},
            }

        total = len(results)
        successes = sum(1 for r in results if r.get('success', False))
        total_steps = sum(r.get('total_steps', len(r.get('reasoning_trace', []))) for r in results)

        # By task type breakdown
        by_type = {}
        for r in results:
            task_type = r.get('type', 'unknown')
            if task_type not in by_type:
                by_type[task_type] = {'total': 0, 'success': 0}
            by_type[task_type]['total'] += 1
            if r.get('success', False):
                by_type[task_type]['success'] += 1

        for stats in by_type.values():
            stats['success_rate'] = stats['success'] / stats['total'] if stats['total'] > 0 else 0.0

        return {
            'total_evaluated': total,
            'total_success': successes,
            'success_rate': successes / total if total > 0 else 0.0,
            'avg_steps': total_steps / total if total > 0 else 0.0,
            'by_task_type': by_type,
        }
