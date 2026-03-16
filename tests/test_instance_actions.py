"""Tests for instance-specific action primitives (feature 002).

Uses the established AI2-THOR module mocking pattern to test without the simulator.
"""
import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock AI2-THOR and other heavy dependencies before importing
_thor_mocks = {}
for mod_name in [
    "env", "env.thor_env",
    "gen", "gen.constants", "gen.utils", "gen.utils.game_util",
    "alfred", "alfred.utils", "alfred.data", "alfred.data.preprocess",
    "scipy", "scipy.spatial",
    "llm", "prompts",
    "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont",
    "numpy",
]:
    _thor_mocks[mod_name] = MagicMock()

# ThorEnv must be a real class (not MagicMock) so ThorConnector can inherit properly
class _FakeThorEnv:
    def __init__(self, *args, **kwargs):
        pass
    def step(self, action_dict):
        return MagicMock()
    def restore_scene(self, *args, **kwargs):
        pass

_env_mod = MagicMock()
_env_mod.ThorEnv = _FakeThorEnv
_thor_mocks["env.thor_env"] = _env_mod

# TaskPlanner must be a real class so AlfredTaskPlanner can inherit
class _FakeTaskPlanner:
    pass

_task_planner_mod = MagicMock()
_task_planner_mod.TaskPlanner = _FakeTaskPlanner
_thor_mocks["src.task_planner"] = _task_planner_mod

# Provide natural_word_to_ithor_name in the mock so imports work
def _mock_natural_word_to_ithor_name(w):
    if w == 'CD':
        return w
    return ''.join([x.capitalize() for x in w.split()])

_thor_mocks["alfred.utils"].natural_word_to_ithor_name = _mock_natural_word_to_ithor_name

# Also make the function accessible via the alfred module's utils
_thor_mocks["alfred"].utils = _thor_mocks["alfred.utils"]

with patch.dict(sys.modules, _thor_mocks):
    from src.alfred.thor_connector import ThorConnector
    from src.alfred.alfred_task_planner import AlfredTaskPlanner


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _make_obj(obj_id, obj_type=None, visible=True, distance=1.0,
              pickupable=False, openable=False, toggleable=False,
              parent_receptacles=None, is_open=False, name=None):
    """Create a minimal AI2-THOR object metadata dict."""
    if obj_type is None:
        obj_type = obj_id.split('|')[0]
    return {
        'objectId': obj_id,
        'objectType': obj_type,
        'name': name or obj_type,
        'visible': visible,
        'distance': distance,
        'pickupable': pickupable,
        'openable': openable,
        'toggleable': toggleable,
        'isOpen': is_open,
        'parentReceptacles': parent_receptacles or [],
        'receptacleObjectIds': [],
        'position': {'x': 0, 'y': 0, 'z': 0},
        'rotation': {'x': 0, 'y': 0, 'z': 0},
    }


def _make_connector(objects):
    """Create a ThorConnector with mocked internals and given objects."""
    tc = ThorConnector.__new__(ThorConnector)
    tc._obj_registry = {}
    tc._obj_registry_by_name = {}
    tc.cur_receptacle = None
    tc.sliced = False
    tc.agent_height = 0.9
    tc._last_found_label = None

    # Mock last_event
    tc.last_event = MagicMock()
    tc.last_event.metadata = {
        'objects': objects,
        'lastActionSuccess': True,
        'errorMessage': '',
        'inventoryObjects': [],
    }

    # Build registry
    type_counts = {}
    for obj in sorted(objects, key=lambda o: o['objectId']):
        oid = obj['objectId']
        otype = oid.split('|')[0]
        type_counts[otype] = type_counts.get(otype, 0) + 1
        readable = f"{otype}_{type_counts[otype]}"
        tc._obj_registry[oid] = readable
        tc._obj_registry_by_name[readable] = oid

    return tc


# ──────────────────────────────────────────────
# Phase 2: T004 — _is_instance_id tests
# ──────────────────────────────────────────────

class TestIsInstanceId:
    def test_simple_type(self):
        assert ThorConnector._is_instance_id("Apple_1") is True

    def test_zero_padded(self):
        assert ThorConnector._is_instance_id("Apple_01") is True

    def test_multi_word_type(self):
        assert ThorConnector._is_instance_id("DeskLamp_2") is True

    def test_stove_burner(self):
        assert ThorConnector._is_instance_id("StoveBurner_1") is True

    def test_cd(self):
        assert ThorConnector._is_instance_id("CD_1") is True

    def test_lowercase_rejected(self):
        assert ThorConnector._is_instance_id("apple") is False

    def test_natural_word_rejected(self):
        assert ThorConnector._is_instance_id("desk lamp") is False

    def test_article_rejected(self):
        assert ThorConnector._is_instance_id("a apple") is False

    def test_the_article_rejected(self):
        assert ThorConnector._is_instance_id("the mug") is False

    def test_trailing_underscore_rejected(self):
        assert ThorConnector._is_instance_id("Apple_") is False

    def test_leading_underscore_rejected(self):
        assert ThorConnector._is_instance_id("_01") is False

    def test_lowercase_with_underscore_rejected(self):
        assert ThorConnector._is_instance_id("apple_1") is False

    def test_reversed_format_rejected(self):
        assert ThorConnector._is_instance_id("01_Apple") is False

    def test_empty_string_rejected(self):
        assert ThorConnector._is_instance_id("") is False

    def test_no_number_rejected(self):
        assert ThorConnector._is_instance_id("Apple") is False


# ──────────────────────────────────────────────
# Phase 2: T005 — _normalize_instance_id tests
# ──────────────────────────────────────────────

class TestNormalizeInstanceId:
    def test_strips_leading_zeros(self):
        assert ThorConnector._normalize_instance_id("Apple_01") == "Apple_1"

    def test_no_change_needed(self):
        assert ThorConnector._normalize_instance_id("Mug_1") == "Mug_1"

    def test_multi_leading_zeros(self):
        assert ThorConnector._normalize_instance_id("DeskLamp_002") == "DeskLamp_2"

    def test_zero_preserved(self):
        assert ThorConnector._normalize_instance_id("Apple_0") == "Apple_0"

    def test_large_number(self):
        assert ThorConnector._normalize_instance_id("Mug_10") == "Mug_10"


# ──────────────────────────────────────────────
# Phase 2: T006 — _resolve_instance_id tests
# ──────────────────────────────────────────────

class TestResolveInstanceId:
    def test_found(self):
        tc = _make_connector([
            _make_obj("Apple|01|02|03|04"),
        ])
        result = tc._resolve_instance_id("Apple_1")
        assert result is not None
        assert result == ("Apple|01|02|03|04", "Apple")

    def test_not_found(self):
        tc = _make_connector([
            _make_obj("Apple|01|02|03|04"),
        ])
        assert tc._resolve_instance_id("Mug_1") is None

    def test_normalized_match(self):
        tc = _make_connector([
            _make_obj("Apple|01|02|03|04"),
        ])
        result = tc._resolve_instance_id("Apple_01")
        assert result is not None
        assert result[0] == "Apple|01|02|03|04"

    def test_empty_registry(self):
        tc = _make_connector([])
        assert tc._resolve_instance_id("Apple_1") is None


# ──────────────────────────────────────────────
# Phase 2: T007 — Reverse registry tests
# ──────────────────────────────────────────────

class TestReverseRegistry:
    def test_built_correctly(self):
        tc = _make_connector([
            _make_obj("Apple|01|02|03|04"),
            _make_obj("Apple|01|02|03|05"),
            _make_obj("Mug|01|02|03|06"),
        ])
        assert tc._obj_registry_by_name["Apple_1"] == "Apple|01|02|03|04"
        assert tc._obj_registry_by_name["Apple_2"] == "Apple|01|02|03|05"
        assert tc._obj_registry_by_name["Mug_1"] == "Mug|01|02|03|06"

    def test_forward_reverse_consistent(self):
        tc = _make_connector([
            _make_obj("Apple|01|02|03|04"),
            _make_obj("Fridge|01|02|03|07"),
        ])
        for thor_id, readable in tc._obj_registry.items():
            assert tc._obj_registry_by_name[readable] == thor_id

    def test_registry_counts(self):
        objects = [
            _make_obj("Apple|01|02|03|04"),
            _make_obj("Apple|01|02|03|05"),
            _make_obj("Mug|01|02|03|06"),
        ]
        tc = _make_connector(objects)
        assert len(tc._obj_registry) == 3
        assert len(tc._obj_registry_by_name) == 3


# ──────────────────────────────────────────────
# Phase 3: T011-T013 — US1 Navigate instance tests
# ──────────────────────────────────────────────

class TestNavigateInstance:
    def test_find_instance_calls_nav_with_target_obj_id(self):
        """T011: 'find Apple_01' resolves and passes target_obj_id to nav_obj."""
        tc = _make_connector([
            _make_obj("Apple|01|02|03|04"),
            _make_obj("Apple|01|02|03|05"),
        ])
        with patch.object(tc, 'nav_obj', return_value='') as mock_nav:
            tc.last_event.metadata['lastActionSuccess'] = True
            tc.llm_skill_interact("find Apple_1")
            mock_nav.assert_called_once()
            _, kwargs = mock_nav.call_args
            assert kwargs.get('target_obj_id') == "Apple|01|02|03|04" or \
                   mock_nav.call_args[0][0] == "Apple" and \
                   mock_nav.call_args.kwargs.get('target_obj_id') == "Apple|01|02|03|04"

    def test_find_instance_not_in_registry(self):
        """T012: 'find Plate_05' with non-existent ID returns error."""
        tc = _make_connector([
            _make_obj("Apple|01|02|03|04"),
        ])
        tc.last_event.metadata['lastActionSuccess'] = True
        result = tc.llm_skill_interact("find Plate_05")
        assert result['success'] is False
        assert "Instance ID" in result['message']
        assert "Plate_05" in result['message']

    def test_nav_obj_with_target_obj_id_skips_generic_lookup(self):
        """T013: nav_obj with target_obj_id uses it directly."""
        tc = _make_connector([
            _make_obj("Apple|01|02|03|04", visible=True, distance=0.5),
            _make_obj("Apple|01|02|03|05", visible=True, distance=0.3),
        ])
        # Mock the reachable positions and step
        tc.reachable_positions = MagicMock()
        tc.reachable_position_kdtree = MagicMock()

        with patch.object(tc, 'get_obj_id_from_name') as mock_lookup:
            # Object is visible and close, so nav_obj returns immediately
            tc.nav_obj("Apple", target_obj_id="Apple|01|02|03|04")
            # Should NOT call get_obj_id_from_name when target_obj_id is provided
            mock_lookup.assert_not_called()


# ──────────────────────────────────────────────
# Phase 4: T016-T020 — US2 Manipulate instance tests
# ──────────────────────────────────────────────

class TestManipulateInstance:
    def test_pick_up_instance(self):
        """T016: 'pick up Mug_01' calls pick() with target_obj_id."""
        tc = _make_connector([
            _make_obj("Mug|01|02|03|04", pickupable=True),
            _make_obj("Mug|01|02|03|05", pickupable=True),
        ])
        with patch.object(tc, 'pick', return_value='') as mock_pick:
            tc.last_event.metadata['lastActionSuccess'] = True
            tc.llm_skill_interact("pick up Mug_1")
            mock_pick.assert_called_once()
            assert mock_pick.call_args.kwargs.get('target_obj_id') == "Mug|01|02|03|04"

    def test_open_instance(self):
        """T017: 'open Fridge_01' calls open() with target_obj_id."""
        tc = _make_connector([
            _make_obj("Fridge|01|02|03|04", openable=True),
        ])
        with patch.object(tc, 'open', return_value='') as mock_open:
            tc.last_event.metadata['lastActionSuccess'] = True
            tc.llm_skill_interact("open Fridge_1")
            mock_open.assert_called_once()
            assert mock_open.call_args.kwargs.get('target_obj_id') == "Fridge|01|02|03|04"

    def test_close_instance(self):
        """T018a: 'close Fridge_01' calls close() with target_obj_id."""
        tc = _make_connector([
            _make_obj("Fridge|01|02|03|04", openable=True),
        ])
        with patch.object(tc, 'close', return_value='') as mock_close:
            tc.last_event.metadata['lastActionSuccess'] = True
            tc.llm_skill_interact("close Fridge_1")
            mock_close.assert_called_once()
            assert mock_close.call_args.kwargs.get('target_obj_id') == "Fridge|01|02|03|04"

    def test_turn_on_instance(self):
        """T018b: 'turn on DeskLamp_01' calls toggleon() with target_obj_id."""
        tc = _make_connector([
            _make_obj("DeskLamp|01|02|03|04", toggleable=True),
        ])
        with patch.object(tc, 'toggleon', return_value='') as mock_toggle:
            tc.last_event.metadata['lastActionSuccess'] = True
            tc.llm_skill_interact("turn on DeskLamp_1")
            mock_toggle.assert_called_once()
            assert mock_toggle.call_args.kwargs.get('target_obj_id') == "DeskLamp|01|02|03|04"

    def test_turn_off_instance(self):
        """T018c: 'turn off DeskLamp_01' calls toggleoff() with target_obj_id."""
        tc = _make_connector([
            _make_obj("DeskLamp|01|02|03|04", toggleable=True),
        ])
        with patch.object(tc, 'toggleoff', return_value='') as mock_toggle:
            tc.last_event.metadata['lastActionSuccess'] = True
            tc.llm_skill_interact("turn off DeskLamp_1")
            mock_toggle.assert_called_once()
            assert mock_toggle.call_args.kwargs.get('target_obj_id') == "DeskLamp|01|02|03|04"

    def test_slice_instance(self):
        """T018d: 'slice Bread_01' calls slice() with target_obj_id."""
        tc = _make_connector([
            _make_obj("Bread|01|02|03|04"),
        ])
        with patch.object(tc, 'slice', return_value='') as mock_slice:
            tc.last_event.metadata['lastActionSuccess'] = True
            tc.llm_skill_interact("slice Bread_1")
            mock_slice.assert_called_once()
            assert mock_slice.call_args.kwargs.get('target_obj_id') == "Bread|01|02|03|04"

    def test_pick_with_target_obj_id_skips_lookup(self):
        """T019: pick() with target_obj_id skips get_obj_id_from_name."""
        tc = _make_connector([
            _make_obj("Mug|01|02|03|04", pickupable=True, visible=True, distance=0.5),
        ])
        # Mock super().step to simulate successful pickup
        with patch.object(ThorConnector, 'step', return_value=MagicMock()):
            tc.last_event.metadata['lastActionSuccess'] = True
            with patch.object(tc, 'get_obj_id_from_name') as mock_lookup:
                tc.pick("Mug", target_obj_id="Mug|01|02|03|04")
                mock_lookup.assert_not_called()

    def test_slice_rebuilds_registry(self):
        """T020: After successful slice, _build_object_registry is called."""
        tc = _make_connector([
            _make_obj("Bread|01|02|03|04", visible=True),
        ])
        with patch.object(ThorConnector, 'step', return_value=MagicMock()):
            tc.last_event.metadata['lastActionSuccess'] = True
            with patch.object(tc, '_build_object_registry') as mock_rebuild:
                tc.slice("Bread", target_obj_id="Bread|01|02|03|04")
                mock_rebuild.assert_called_once()


# ──────────────────────────────────────────────
# Phase 5: T026-T028 — US3 Instance skill set tests
# ──────────────────────────────────────────────

class TestInstanceSkillSet:
    @pytest.fixture
    def planner(self):
        """Create AlfredTaskPlanner without full initialization."""
        p = AlfredTaskPlanner.__new__(AlfredTaskPlanner)
        return p

    def test_basic_generation(self, planner):
        """T026: Skill set contains find/pick entries for registered objects."""
        registry = {
            "Apple_1": "Apple|01|02|03|04",
            "Apple_2": "Apple|01|02|03|05",
            "Mug_1": "Mug|01|02|03|06",
        }
        metadata = [
            _make_obj("Apple|01|02|03|04", pickupable=True),
            _make_obj("Apple|01|02|03|05", pickupable=True),
            _make_obj("Mug|01|02|03|06", pickupable=True),
        ]
        skills = planner.init_instance_skill_set(registry, metadata)
        skill_strs = [s.strip() for s in skills]
        assert "find Apple_1" in skill_strs
        assert "find Apple_2" in skill_strs
        assert "find Mug_1" in skill_strs
        assert "pick up Apple_1" in skill_strs
        assert "pick up Mug_1" in skill_strs

    def test_property_filtering(self, planner):
        """T027: Openable/toggleable/sliceable objects get correct actions."""
        registry = {
            "Apple_1": "Apple|01|02|03|04",
            "Fridge_1": "Fridge|01|02|03|05",
            "DeskLamp_1": "DeskLamp|01|02|03|06",
        }
        metadata = [
            _make_obj("Apple|01|02|03|04", pickupable=True),
            _make_obj("Fridge|01|02|03|05", openable=True),
            _make_obj("DeskLamp|01|02|03|06", toggleable=True),
        ]
        skills = planner.init_instance_skill_set(registry, metadata)
        skill_strs = [s.strip() for s in skills]

        # Fridge should get open/close but NOT pick up
        assert "open Fridge_1" in skill_strs
        assert "close Fridge_1" in skill_strs
        assert "pick up Fridge_1" not in skill_strs

        # DeskLamp should get turn on/off
        assert "turn on DeskLamp_1" in skill_strs
        assert "turn off DeskLamp_1" in skill_strs

        # Apple is sliceable
        assert "slice Apple_1" in skill_strs

    def test_done_terminator(self, planner):
        """T028: Skill set always includes 'done'."""
        skills = planner.init_instance_skill_set({}, [])
        assert any('done' in s for s in skills)


# ──────────────────────────────────────────────
# Phase 6: T030-T032 — US4 Backward compatibility tests
# ──────────────────────────────────────────────

class TestBackwardCompatibility:
    def test_generic_find(self):
        """T030: 'find a apple' uses generic path without target_obj_id."""
        tc = _make_connector([
            _make_obj("Apple|01|02|03|04", visible=True, distance=0.5),
        ])
        with patch.object(tc, 'nav_obj', return_value='') as mock_nav:
            tc.last_event.metadata['lastActionSuccess'] = True
            tc.llm_skill_interact("find a apple")
            mock_nav.assert_called_once()
            # Should NOT have target_obj_id
            args, kwargs = mock_nav.call_args
            assert kwargs.get('target_obj_id') is None
            # First arg should be the ithor name
            assert args[0] == "Apple"

    def test_generic_pick_up(self):
        """T031a: 'pick up the mug' uses generic path."""
        tc = _make_connector([
            _make_obj("Mug|01|02|03|04", pickupable=True),
        ])
        with patch.object(tc, 'pick', return_value='') as mock_pick:
            tc.last_event.metadata['lastActionSuccess'] = True
            tc.llm_skill_interact("pick up the mug")
            mock_pick.assert_called_once()
            args, kwargs = mock_pick.call_args
            assert kwargs.get('target_obj_id') is None
            assert args[0] == "Mug"

    def test_generic_open(self):
        """T031b: 'open the fridge' uses generic path."""
        tc = _make_connector([
            _make_obj("Fridge|01|02|03|04", openable=True),
        ])
        with patch.object(tc, 'open', return_value='') as mock_open:
            tc.last_event.metadata['lastActionSuccess'] = True
            tc.llm_skill_interact("open the fridge")
            mock_open.assert_called_once()
            args, kwargs = mock_open.call_args
            assert kwargs.get('target_obj_id') is None

    def test_generic_slice(self):
        """T031c: 'slice the bread' uses generic path."""
        tc = _make_connector([
            _make_obj("Bread|01|02|03|04"),
        ])
        with patch.object(tc, 'slice', return_value='') as mock_slice:
            tc.last_event.metadata['lastActionSuccess'] = True
            tc.llm_skill_interact("slice the bread")
            mock_slice.assert_called_once()
            args, kwargs = mock_slice.call_args
            assert kwargs.get('target_obj_id') is None

    def test_generic_turn_on(self):
        """T031d: 'turn on the desk lamp' uses generic path."""
        tc = _make_connector([
            _make_obj("DeskLamp|01|02|03|04", toggleable=True),
        ])
        with patch.object(tc, 'toggleon', return_value='') as mock_toggle:
            tc.last_event.metadata['lastActionSuccess'] = True
            tc.llm_skill_interact("turn on the desk lamp")
            mock_toggle.assert_called_once()
            args, kwargs = mock_toggle.call_args
            assert kwargs.get('target_obj_id') is None

    def test_mixed_mode_plan(self):
        """T032: Mixed instance + generic directives in same plan."""
        tc = _make_connector([
            _make_obj("Apple|01|02|03|04", pickupable=True, visible=True, distance=0.5),
            _make_obj("Fridge|01|02|03|05", openable=True, visible=True, distance=1.0),
        ])

        calls = []

        def track_nav(*args, **kwargs):
            calls.append(('nav_obj', args, kwargs))
            return ''

        def track_pick(*args, **kwargs):
            calls.append(('pick', args, kwargs))
            return ''

        def track_open(*args, **kwargs):
            calls.append(('open', args, kwargs))
            return ''

        tc.last_event.metadata['lastActionSuccess'] = True

        with patch.object(tc, 'nav_obj', side_effect=track_nav), \
             patch.object(tc, 'pick', side_effect=track_pick), \
             patch.object(tc, 'open', side_effect=track_open):

            # Instance: find Apple_1
            tc.llm_skill_interact("find Apple_1")
            # Generic: pick up the apple
            tc.llm_skill_interact("pick up the apple")
            # Instance: find Fridge_1
            tc.llm_skill_interact("find Fridge_1")
            # Generic: open the fridge
            tc.llm_skill_interact("open the fridge")

        # Verify instance calls have target_obj_id
        assert calls[0][0] == 'nav_obj'
        assert calls[0][2].get('target_obj_id') == "Apple|01|02|03|04"

        assert calls[1][0] == 'pick'
        assert calls[1][2].get('target_obj_id') is None  # generic

        assert calls[2][0] == 'nav_obj'
        assert calls[2][2].get('target_obj_id') == "Fridge|01|02|03|05"

        assert calls[3][0] == 'open'
        assert calls[3][2].get('target_obj_id') is None  # generic


# ──────────────────────────────────────────────
# Phase 7: T035 — Edge case tests
# ──────────────────────────────────────────────

class TestEdgeCases:
    def test_malformed_trailing_underscore(self):
        """'Apple_' is not a valid instance ID — falls through to generic."""
        assert ThorConnector._is_instance_id("Apple_") is False

    def test_malformed_reversed(self):
        """'01_Apple' is not a valid instance ID."""
        assert ThorConnector._is_instance_id("01_Apple") is False

    def test_no_underscore(self):
        """'Apple' without underscore is not an instance ID."""
        assert ThorConnector._is_instance_id("Apple") is False

    def test_empty_string(self):
        assert ThorConnector._is_instance_id("") is False

    def test_zero_padded_resolves(self):
        """Apple_01 should resolve to same object as Apple_1."""
        tc = _make_connector([
            _make_obj("Apple|01|02|03|04"),
        ])
        r1 = tc._resolve_instance_id("Apple_1")
        r2 = tc._resolve_instance_id("Apple_01")
        assert r1 == r2
        assert r1 is not None

    def test_drop_unaffected(self):
        """'drop' action has no object parameter — should not trigger instance detection."""
        tc = _make_connector([])
        with patch.object(tc, 'drop', return_value='') as mock_drop:
            tc.last_event.metadata['lastActionSuccess'] = True
            result = tc.llm_skill_interact("drop")
            mock_drop.assert_called_once()
            assert result['success'] is True
