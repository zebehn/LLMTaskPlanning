"""ALFRED instruction validation script.

Classifies task instructions into 4 categories by comparing annotator-written
instructions against scene objects and PDDL ground truth using a lightweight LLM:

  0 (valid):        Instruction matches ground truth and objects exist in scene.
  1 (non_existent): Instruction mentions objects not in the scene.
  2 (goal_mismatch): Mentioned objects exist but don't match ground truth targets.
  3 (ambiguous):    Vague/colloquial terms that could plausibly refer to targets.

Usage:
    PYTHONPATH="alfred:src:$PYTHONPATH" python src/alfred/instruction_validator.py \\
        --split valid_seen [--portion 5] [--model gpt-5-mini]
"""

import argparse
import datetime
import json
import logging
import os
import random
import re
import time

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CATEGORY_LABELS = {
    0: "valid",
    1: "non_existent",
    2: "goal_mismatch",
    3: "ambiguous",
}

CLASSIFICATION_SYSTEM_PROMPT = """\
You are classifying ALFRED household task instructions for annotation quality.
You will be given a natural language instruction, the list of objects available \
in the scene, and the ground truth task targets.
Classify the instruction into exactly one category and explain your reasoning.

Categories (in priority order):
1 (non_existent): The instruction mentions objects or receptacles that do not \
exist in the scene at all.
2 (goal_mismatch): The mentioned objects exist in the scene but do not match \
the ground truth targets.
3 (ambiguous): The instruction uses vague or colloquial terms that could \
plausibly refer to the correct targets but are not clear or exact.
0 (valid): The instruction correctly describes the task — mentioned objects \
match the ground truth targets and exist in the scene. Common synonyms like \
"fridge" for "Fridge" or "counter" for "CounterTop" are acceptable as valid.

Important: "Sliced" suffixes in targets (e.g., "PotatoSliced") mean the \
annotator should reference the base object ("potato"). This is valid, not a \
mismatch.

Respond ONLY with a JSON object: {"category": N, "reason": "brief explanation"}\
"""

ALFRED_TASK_TYPES = [
    'pick_and_place_with_movable_recep',
    'pick_clean_then_place_in_recep',
    'pick_heat_then_place_in_recep',
    'pick_cool_then_place_in_recep',
    'pick_and_place_simple',
    'look_at_obj_in_light',
]

# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------


def extract_scene_objects(traj_data: dict) -> list[str]:
    """Extract sorted unique object type names from scene object_poses.

    Strips the instance suffix (hex hash after last ``_``) from each
    ``objectName`` — e.g. ``Candle_96bce45a`` → ``Candle``.
    """
    poses = traj_data.get('scene', {}).get('object_poses', [])
    types = set()
    for p in poses:
        name = p.get('objectName', '')
        # Strip the hex hash suffix: everything after the last '_'
        # But handle multi-word objects like "RemoteControl_abc123"
        parts = name.rsplit('_', 1)
        if len(parts) == 2 and len(parts[1]) >= 6:
            # Looks like a hex hash suffix
            types.add(parts[0])
        else:
            types.add(name)
    types.discard('')
    return sorted(types)


def extract_pddl_targets(traj_data: dict, task_path: str = '') -> dict:
    """Extract PDDL ground truth targets.

    Tries ``traj_data['pddl_params']`` first; falls back to parsing the
    task directory name ``{type}-{object}-{mrecep}-{receptacle}-{scene}``.
    """
    params = traj_data.get('pddl_params', {})
    if params and params.get('object_target'):
        return {
            'object_target': params.get('object_target', ''),
            'parent_target': params.get('parent_target', ''),
            'mrecep_target': params.get('mrecep_target', ''),
            'object_sliced': params.get('object_sliced', False),
        }

    # Fallback: parse directory name
    if task_path:
        dir_name = task_path.split('/')[0] if '/' in task_path else task_path
        m = re.match(r'^(.+?)-([\w]+)-([\w]+)-([\w]+)-(\d+)$', dir_name)
        if m:
            obj = m.group(2)
            return {
                'object_target': obj,
                'parent_target': m.group(4),
                'mrecep_target': '' if m.group(3) == 'None' else m.group(3),
                'object_sliced': obj.endswith('Sliced'),
            }

    return {
        'object_target': '',
        'parent_target': '',
        'mrecep_target': '',
        'object_sliced': False,
    }


def _extract_task_type(task_path: str) -> str:
    """Extract ALFRED task type from task directory path."""
    for t in ALFRED_TASK_TYPES:
        if task_path.startswith(t):
            return t
    return task_path.split('-')[0]


# ---------------------------------------------------------------------------
# LLM prompt & parsing
# ---------------------------------------------------------------------------


def build_classification_prompt(
    instruction_text: str,
    scene_objects: list[str],
    pddl_targets: dict,
) -> tuple[str, str]:
    """Build (system_message, user_message) for LLM classification."""
    obj_target = pddl_targets['object_target']
    parent_target = pddl_targets['parent_target']
    mrecep_target = pddl_targets.get('mrecep_target', '')

    # Handle Sliced targets — show base form
    obj_display = obj_target
    if obj_target.endswith('Sliced'):
        base = obj_target.replace('Sliced', '')
        obj_display = f"{obj_target} (base form: {base})"

    user_parts = [
        f'Instruction: "{instruction_text}"',
        f'Scene objects: {", ".join(scene_objects)}',
        f'Ground truth targets: object={obj_display}, receptacle={parent_target}',
    ]
    if mrecep_target:
        user_parts[-1] += f', movable_receptacle={mrecep_target}'

    return CLASSIFICATION_SYSTEM_PROMPT, '\n'.join(user_parts)


def parse_classification_response(raw_response: str) -> tuple[int, str]:
    """Parse LLM JSON response into (category, reason).

    Falls back to category 3 ("ambiguous") on parse failure.
    """
    # Try to extract JSON object from response
    match = re.search(r'\{[^{}]*\}', raw_response)
    if match:
        try:
            data = json.loads(match.group())
            category = int(data.get('category', 3))
            reason = str(data.get('reason', ''))
            if category not in CATEGORY_LABELS:
                log.warning("Category %d out of range, falling back to 3", category)
                category = 3
            return category, reason
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    log.warning("Unparseable LLM response: %s", raw_response[:200])
    return 3, "unparseable LLM response"


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def classify_instruction(
    llm,
    instruction_text: str,
    scene_objects: list[str],
    pddl_targets: dict,
    max_retries: int = 3,
) -> tuple[int, str]:
    """Classify a single instruction via LLM.

    Returns (category, reason). Retries on API failure with exponential
    backoff.
    """
    system_msg, user_msg = build_classification_prompt(
        instruction_text, scene_objects, pddl_targets
    )
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    last_error = None
    for attempt in range(max_retries):
        try:
            raw = llm.chat_completion(messages, temperature=0.0, max_tokens=256)
            return parse_classification_response(raw)
        except Exception as e:
            last_error = e
            wait = 2 ** attempt  # 1s, 2s, 4s
            log.warning("LLM call failed (attempt %d/%d): %s. Retrying in %ds...",
                        attempt + 1, max_retries, e, wait)
            time.sleep(wait)

    log.error("Classification failed after %d retries: %s", max_retries, last_error)
    return 3, "classification failed after retries"


# ---------------------------------------------------------------------------
# Validation orchestrator
# ---------------------------------------------------------------------------


def validate_split(
    split: str,
    llm,
    portion: int = 100,
    seed: int = 1,
    stratified: bool = False,
) -> dict:
    """Validate all instructions in an ALFRED split.

    Returns a ValidationReport dict.
    """
    from collections import defaultdict
    from src.alfred.utils import load_task_json
    from tqdm import tqdm

    # Load split file
    splits_path = 'alfred/data/splits/oct21.json'
    with open(splits_path) as f:
        splits = json.load(f)

    assert split in splits, f"Split '{split}' not found. Available: {list(splits.keys())}"

    # Filter out pick_two_obj_and_place
    files = [e for e in splits[split] if 'pick_two_obj_and_place' not in e['task']]

    # Subset sampling (matching react_evaluator.py logic)
    if portion < 100:
        random.seed(seed)
        n_sample = max(1, int(len(files) * portion / 100))

        if stratified:
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

            extra_needed = max(0, n_sample - len(selected))
            if extra_needed > 0:
                random.shuffle(remaining_pool)
                selected.extend(remaining_pool[:extra_needed])
            files = selected
        else:
            files = random.sample(files, n_sample)

    # Validate each entry
    entries = []
    for task_entry in tqdm(files, desc="Validating instructions"):
        task_path = task_entry['task']
        repeat_idx = task_entry['repeat_idx']

        try:
            traj_data = load_task_json(task_entry, split=split)
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            log.warning("Skipping %s (repeat %d): %s", task_path, repeat_idx, e)
            continue

        # Extract data
        scene_objects = extract_scene_objects(traj_data)
        pddl_targets = extract_pddl_targets(traj_data, task_path)
        task_type = traj_data.get('task_type') or _extract_task_type(task_path)

        # Get instruction
        anns = traj_data.get('turk_annotations', {}).get('anns', [])
        if repeat_idx >= len(anns):
            log.warning("Skipping %s: repeat_idx %d >= %d annotations",
                        task_path, repeat_idx, len(anns))
            continue
        instruction_text = anns[repeat_idx].get('task_desc', '')

        # Classify
        category, reason = classify_instruction(
            llm, instruction_text, scene_objects, pddl_targets
        )

        entry = {
            'task_path': task_path,
            'trial_id': traj_data.get('task_id', ''),
            'repeat_idx': repeat_idx,
            'task_type': task_type,
            'category': category,
            'category_label': CATEGORY_LABELS[category],
            'instruction_text': instruction_text,
            'pddl_targets': pddl_targets,
            'scene_objects': scene_objects,
            'reason': reason,
        }
        entries.append(entry)

    # Build report
    summary = build_summary(entries)
    report = {
        'split': split,
        'model': getattr(llm, 'model_name', 'unknown'),
        'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'total_entries': len(entries),
        'summary': summary['overall'],
        'by_task_type': summary['by_task_type'],
        'entries': entries,
    }
    return report


# ---------------------------------------------------------------------------
# Summary & reporting
# ---------------------------------------------------------------------------


def build_summary(entries: list[dict]) -> dict:
    """Compute category summary statistics.

    Returns dict with 'overall' and 'by_task_type' keys, each containing
    CategorySummary-shaped dicts.
    """
    from collections import defaultdict

    def _count(items):
        total = len(items)
        counts = {f'category_{i}': 0 for i in range(4)}
        for e in items:
            key = f"category_{e['category']}"
            counts[key] = counts.get(key, 0) + 1
        return {'total': total, **counts}

    by_type = defaultdict(list)
    for e in entries:
        by_type[e['task_type']].append(e)

    return {
        'overall': _count(entries),
        'by_task_type': {tt: _count(items) for tt, items in sorted(by_type.items())},
    }


def print_summary(report: dict) -> None:
    """Log a human-readable summary of the validation report."""
    total = report['total_entries']
    summary = report['summary']

    log.info("=" * 60)
    log.info("Instruction Validation Summary")
    log.info("=" * 60)
    log.info("Split: %s | Model: %s", report['split'], report.get('model', '?'))
    log.info("Total entries: %d", total)
    log.info("")

    for cat in range(4):
        count = summary.get(f'category_{cat}', 0)
        pct = (count / total * 100) if total > 0 else 0.0
        label = CATEGORY_LABELS[cat]
        log.info("  Category %d (%s): %d/%d (%.1f%%)", cat, label, count, total, pct)

    log.info("")
    log.info("By task type:")
    for task_type, stats in sorted(report.get('by_task_type', {}).items()):
        tt_total = stats['total']
        valid = stats.get('category_0', 0)
        pct = (valid / tt_total * 100) if tt_total > 0 else 0.0
        log.info("  %-45s %d/%d valid (%.1f%%)", task_type, valid, tt_total, pct)
    log.info("=" * 60)


# ---------------------------------------------------------------------------
# Evaluator integration helper
# ---------------------------------------------------------------------------


def load_validation_report(report_path: str) -> dict:
    """Load a validation report and build a lookup dict.

    Returns dict keyed by ``(task_path, repeat_idx)`` → entry dict.
    """
    with open(report_path) as f:
        report = json.load(f)

    lookup = {}
    for entry in report.get('entries', []):
        key = (entry['task_path'], entry['repeat_idx'])
        lookup[key] = entry
    return lookup


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    """CLI entry point for instruction validation."""
    parser = argparse.ArgumentParser(
        description='Validate ALFRED task instructions against scene objects '
                    'and PDDL ground truth.')
    parser.add_argument('--split', required=True,
                        help='ALFRED split to validate (valid_seen, valid_unseen, train)')
    parser.add_argument('--model', default='gpt-5-mini',
                        help='LLM model for classification (default: gpt-5-mini)')
    parser.add_argument('--provider', default='openai',
                        help='LLM provider (default: openai)')
    parser.add_argument('--reasoning-effort', default='low',
                        help='Reasoning effort for reasoning models (default: low)')
    parser.add_argument('--output', default=None,
                        help='Output report path (default: outputs/alfred_react/'
                             'instruction_validation_{split}.json)')
    parser.add_argument('--portion', type=int, default=100,
                        help='Percentage of tasks to validate (default: 100)')
    parser.add_argument('--seed', type=int, default=1,
                        help='Random seed for subset sampling (default: 1)')
    parser.add_argument('--stratified', action='store_true',
                        help='Enable stratified sampling by task type')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)s %(levelname)s: %(message)s',
    )

    # Create LLM provider
    from llm import LLMProviderFactory
    llm = LLMProviderFactory.create(
        provider_type=args.provider,
        model_name=args.model,
        reasoning_effort=args.reasoning_effort,
    )
    log.info("Using LLM: %s (%s)", args.model, args.provider)

    # Run validation
    report = validate_split(
        split=args.split,
        llm=llm,
        portion=args.portion,
        seed=args.seed,
        stratified=args.stratified,
    )

    # Write report
    output_path = args.output or f'outputs/alfred_react/instruction_validation_{args.split}.json'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    log.info("Report written to %s", output_path)

    # Print summary
    print_summary(report)


if __name__ == '__main__':
    main()
