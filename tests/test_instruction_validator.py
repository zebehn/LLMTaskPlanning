"""Tests for ALFRED instruction validation script.

Covers:
  - T007: extract_scene_objects
  - T008: extract_pddl_targets
  - T009: build_classification_prompt
  - T010: parse_classification_response
  - T011: classify_instruction (mocked LLM)
  - T012: validate_split (mocked LLM + data)
  - T021: load_validation_report
  - T022: evaluator skips tasks (integration)
  - T025: print_summary
"""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock heavy dependencies before importing the module under test
# ---------------------------------------------------------------------------
# These are only needed for validate_split which imports tqdm and load_task_json.
# The individual functions (extract_*, build_*, parse_*) have no such deps.

_MOCK_MODULES = [
    'ai2thor', 'ai2thor.controller', 'ai2thor.server',
    'alfred', 'alfred.env', 'alfred.env.thor_env',
    'alfred.gen', 'alfred.gen.constants',
    'alfred.gen.utils', 'alfred.gen.utils.game_util',
    'alfred.gen.utils.image_util',
    'scipy', 'scipy.spatial',
    'PIL', 'PIL.Image',
    'numpy', 'tqdm',
]
for mod_name in _MOCK_MODULES:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# Now safe to import
from src.alfred.instruction_validator import (
    CATEGORY_LABELS,
    build_classification_prompt,
    build_summary,
    classify_instruction,
    extract_pddl_targets,
    extract_scene_objects,
    load_validation_report,
    parse_classification_response,
    print_summary,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures', 'validation')


def _load_fixture(name: str) -> dict:
    with open(os.path.join(FIXTURE_DIR, name)) as f:
        return json.load(f)


@pytest.fixture
def valid_ann():
    return _load_fixture('sample_ann_valid.json')


@pytest.fixture
def nonexistent_ann():
    return _load_fixture('sample_ann_nonexistent.json')


@pytest.fixture
def mismatch_ann():
    return _load_fixture('sample_ann_mismatch.json')


# ===========================================================================
# T007: test_extract_scene_objects
# ===========================================================================

class TestExtractSceneObjects:
    def test_basic_extraction(self, valid_ann):
        result = extract_scene_objects(valid_ann)
        assert isinstance(result, list)
        assert result == sorted(result), "Result should be sorted"
        assert 'Candle' in result
        assert 'SoapBar' in result
        assert 'SprayBottle' in result

    def test_strips_hash_suffix(self, valid_ann):
        result = extract_scene_objects(valid_ann)
        # Should not contain any hash suffixes
        for name in result:
            assert '_' not in name or len(name.split('_')[-1]) < 6, \
                f"Object name still has hash suffix: {name}"

    def test_unique_types(self, valid_ann):
        """Scene has two Candle_96bce45a entries; should appear once."""
        result = extract_scene_objects(valid_ann)
        assert result.count('Candle') == 1

    def test_empty_poses(self):
        data = {'scene': {'object_poses': []}}
        assert extract_scene_objects(data) == []

    def test_missing_scene(self):
        assert extract_scene_objects({}) == []


# ===========================================================================
# T008: test_extract_pddl_targets
# ===========================================================================

class TestExtractPddlTargets:
    def test_from_pddl_params(self, valid_ann):
        result = extract_pddl_targets(valid_ann)
        assert result['object_target'] == 'Candle'
        assert result['parent_target'] == 'Toilet'
        assert result['mrecep_target'] == ''
        assert result['object_sliced'] is False

    def test_fallback_to_directory_name(self):
        data = {'pddl_params': {}}
        path = 'pick_and_place_simple-Candle-None-Toilet-429/trial_T20190908_052232_887934'
        result = extract_pddl_targets(data, task_path=path)
        assert result['object_target'] == 'Candle'
        assert result['parent_target'] == 'Toilet'
        assert result['mrecep_target'] == ''

    def test_sliced_target_from_directory(self):
        data = {'pddl_params': {}}
        path = 'pick_cool_then_place_in_recep-PotatoSliced-None-SinkBasin-13/trial_T20190909'
        result = extract_pddl_targets(data, task_path=path)
        assert result['object_target'] == 'PotatoSliced'
        assert result['parent_target'] == 'SinkBasin'
        assert result['object_sliced'] is True

    def test_movable_recep_from_directory(self):
        data = {'pddl_params': {}}
        path = 'pick_and_place_with_movable_recep-Tomato-Bowl-Fridge-13/trial_T20190909'
        result = extract_pddl_targets(data, task_path=path)
        assert result['object_target'] == 'Tomato'
        assert result['parent_target'] == 'Fridge'
        assert result['mrecep_target'] == 'Bowl'

    def test_empty_fallback(self):
        result = extract_pddl_targets({}, task_path='')
        assert result['object_target'] == ''


# ===========================================================================
# T009: test_build_classification_prompt
# ===========================================================================

class TestBuildClassificationPrompt:
    def test_basic_structure(self):
        sys_msg, user_msg = build_classification_prompt(
            'Place the candle on the toilet.',
            ['Candle', 'SoapBar', 'Towel'],
            {'object_target': 'Candle', 'parent_target': 'Toilet', 'mrecep_target': ''}
        )
        assert 'category' in sys_msg.lower()
        assert 'non_existent' in sys_msg or 'non-existent' in sys_msg.lower()
        assert 'Place the candle on the toilet.' in user_msg
        assert 'Candle' in user_msg
        assert 'Toilet' in user_msg

    def test_sliced_target_shows_base_form(self):
        sys_msg, user_msg = build_classification_prompt(
            'Put a potato in the sink.',
            ['Potato', 'Knife', 'SinkBasin'],
            {'object_target': 'PotatoSliced', 'parent_target': 'SinkBasin', 'mrecep_target': ''}
        )
        assert 'PotatoSliced' in user_msg
        assert 'Potato' in user_msg  # base form
        assert 'base form' in user_msg.lower()

    def test_movable_recep_included(self):
        sys_msg, user_msg = build_classification_prompt(
            'Put the tomato in a bowl and place in fridge.',
            ['Tomato', 'Bowl', 'Fridge'],
            {'object_target': 'Tomato', 'parent_target': 'Fridge', 'mrecep_target': 'Bowl'}
        )
        assert 'Bowl' in user_msg
        assert 'movable_receptacle' in user_msg.lower()

    def test_returns_tuple(self):
        result = build_classification_prompt(
            'test', ['A'], {'object_target': 'A', 'parent_target': 'B', 'mrecep_target': ''}
        )
        assert isinstance(result, tuple)
        assert len(result) == 2


# ===========================================================================
# T010: test_parse_classification_response
# ===========================================================================

class TestParseClassificationResponse:
    def test_valid_json(self):
        cat, reason = parse_classification_response('{"category": 1, "reason": "no bottle"}')
        assert cat == 1
        assert reason == "no bottle"

    def test_valid_json_category_0(self):
        cat, reason = parse_classification_response('{"category": 0, "reason": "matches"}')
        assert cat == 0

    def test_json_with_surrounding_text(self):
        raw = 'Here is the result:\n{"category": 2, "reason": "wrong object"}\n'
        cat, reason = parse_classification_response(raw)
        assert cat == 2
        assert reason == "wrong object"

    def test_malformed_json_falls_back_to_3(self):
        cat, reason = parse_classification_response('not json at all')
        assert cat == 3
        assert 'unparseable' in reason.lower()

    def test_category_out_of_range_falls_back_to_3(self):
        cat, reason = parse_classification_response('{"category": 5, "reason": "oops"}')
        assert cat == 3

    def test_missing_category_falls_back_to_3(self):
        cat, reason = parse_classification_response('{"reason": "no category field"}')
        assert cat == 3

    def test_empty_string(self):
        cat, reason = parse_classification_response('')
        assert cat == 3


# ===========================================================================
# T011: test_classify_instruction
# ===========================================================================

class TestClassifyInstruction:
    def test_successful_classification(self):
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = '{"category": 1, "reason": "non-existent"}'

        cat, reason = classify_instruction(
            mock_llm,
            'Put a bottle on a newspaper.',
            ['Candle', 'SoapBar'],
            {'object_target': 'Candle', 'parent_target': 'Toilet', 'mrecep_target': ''},
        )
        assert cat == 1
        assert 'non-existent' in reason
        mock_llm.chat_completion.assert_called_once()

    def test_retries_on_exception(self):
        mock_llm = MagicMock()
        mock_llm.chat_completion.side_effect = [
            RuntimeError("API error"),
            RuntimeError("API error"),
            '{"category": 0, "reason": "ok"}',
        ]

        with patch('src.alfred.instruction_validator.time.sleep'):
            cat, reason = classify_instruction(
                mock_llm,
                'Place candle on toilet.',
                ['Candle'],
                {'object_target': 'Candle', 'parent_target': 'Toilet', 'mrecep_target': ''},
            )
        assert cat == 0
        assert mock_llm.chat_completion.call_count == 3

    def test_exhausted_retries(self):
        mock_llm = MagicMock()
        mock_llm.chat_completion.side_effect = RuntimeError("persistent failure")

        with patch('src.alfred.instruction_validator.time.sleep'):
            cat, reason = classify_instruction(
                mock_llm,
                'test',
                ['A'],
                {'object_target': 'A', 'parent_target': 'B', 'mrecep_target': ''},
            )
        assert cat == 3
        assert 'failed after retries' in reason


# ===========================================================================
# T012: test_validate_split
# ===========================================================================

class TestBuildSummary:
    """T012: Test report summary computation (the testable core of validate_split)."""

    def test_overall_counts(self):
        entries = [
            {'task_type': 'pick_and_place_simple', 'category': 0},
            {'task_type': 'pick_and_place_simple', 'category': 1},
            {'task_type': 'pick_clean_then_place_in_recep', 'category': 2},
        ]
        summary = build_summary(entries)
        assert summary['overall']['total'] == 3
        assert summary['overall']['category_0'] == 1
        assert summary['overall']['category_1'] == 1
        assert summary['overall']['category_2'] == 1
        assert summary['overall']['category_3'] == 0

    def test_per_task_type_breakdown(self):
        entries = [
            {'task_type': 'pick_and_place_simple', 'category': 0},
            {'task_type': 'pick_and_place_simple', 'category': 1},
            {'task_type': 'pick_clean_then_place_in_recep', 'category': 2},
        ]
        summary = build_summary(entries)
        assert 'pick_and_place_simple' in summary['by_task_type']
        assert summary['by_task_type']['pick_and_place_simple']['total'] == 2
        assert summary['by_task_type']['pick_and_place_simple']['category_0'] == 1
        assert summary['by_task_type']['pick_and_place_simple']['category_1'] == 1

    def test_empty_entries(self):
        summary = build_summary([])
        assert summary['overall']['total'] == 0

    def test_all_same_category(self):
        entries = [{'task_type': 'a', 'category': 0} for _ in range(5)]
        summary = build_summary(entries)
        assert summary['overall']['category_0'] == 5
        assert summary['overall']['category_1'] == 0


# ===========================================================================
# T021: test_load_validation_report
# ===========================================================================

class TestLoadValidationReport:
    def test_builds_lookup_dict(self, tmp_path):
        report = {
            'entries': [
                {'task_path': 'path/A', 'repeat_idx': 0, 'category': 1,
                 'category_label': 'non_existent'},
                {'task_path': 'path/B', 'repeat_idx': 2, 'category': 0,
                 'category_label': 'valid'},
            ]
        }
        report_file = tmp_path / 'report.json'
        report_file.write_text(json.dumps(report))

        lookup = load_validation_report(str(report_file))
        assert ('path/A', 0) in lookup
        assert ('path/B', 2) in lookup
        assert lookup[('path/A', 0)]['category'] == 1
        assert lookup[('path/B', 2)]['category'] == 0

    def test_empty_report(self, tmp_path):
        report = {'entries': []}
        report_file = tmp_path / 'report.json'
        report_file.write_text(json.dumps(report))

        lookup = load_validation_report(str(report_file))
        assert lookup == {}


# ===========================================================================
# T022: test_evaluator_skips_tasks
# ===========================================================================

class TestEvaluatorSkipsTasks:
    """Verify that the lookup + skip logic works correctly."""

    def test_skip_logic(self):
        """Simulate the evaluator skip check."""
        lookup = {
            ('type-A-None-B-1/trial_T001', 0): {
                'category': 1, 'category_label': 'non_existent',
                'reason': 'no such object'
            },
            ('type-A-None-B-1/trial_T002', 0): {
                'category': 0, 'category_label': 'valid',
                'reason': 'ok'
            },
        }
        skip_categories = [1]

        tasks = [
            {'task': 'type-A-None-B-1/trial_T001', 'repeat_idx': 0},
            {'task': 'type-A-None-B-1/trial_T002', 'repeat_idx': 0},
            {'task': 'type-A-None-B-1/trial_T003', 'repeat_idx': 0},  # not in report
        ]

        skipped = []
        evaluated = []
        for task in tasks:
            key = (task['task'], task['repeat_idx'])
            entry = lookup.get(key)
            if entry and entry['category'] in skip_categories:
                skipped.append(task['task'])
            else:
                evaluated.append(task['task'])

        assert len(skipped) == 1
        assert 'trial_T001' in skipped[0]
        assert len(evaluated) == 2  # T002 (valid) + T003 (not in report)


# ===========================================================================
# T025: test_print_summary
# ===========================================================================

class TestPrintSummary:
    def test_logs_summary(self, caplog):
        report = {
            'split': 'valid_seen',
            'model': 'test-model',
            'total_entries': 10,
            'summary': {
                'total': 10,
                'category_0': 7,
                'category_1': 1,
                'category_2': 1,
                'category_3': 1,
            },
            'by_task_type': {
                'pick_and_place_simple': {
                    'total': 6,
                    'category_0': 5,
                    'category_1': 1,
                    'category_2': 0,
                    'category_3': 0,
                },
                'pick_heat_then_place_in_recep': {
                    'total': 4,
                    'category_0': 2,
                    'category_1': 0,
                    'category_2': 1,
                    'category_3': 1,
                },
            },
        }

        import logging
        with caplog.at_level(logging.INFO,
                             logger='src.alfred.instruction_validator'):
            print_summary(report)

        output = caplog.text
        assert 'Category 0' in output or 'category_0' in output.lower()
        assert 'valid_seen' in output
        assert 'pick_and_place_simple' in output
        assert '10' in output
