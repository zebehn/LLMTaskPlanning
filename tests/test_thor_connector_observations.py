"""Tests for instance-label observation strings in ThorConnector (feature 006).

TDD: These tests MUST FAIL before the implementation changes to pick() and put().
After changes, all 5 must pass.
"""
import re
import sys
from unittest.mock import MagicMock, patch

import pytest

# ── Module mocking (same pattern as test_instance_actions.py) ────────────────

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


def _mock_natural_word_to_ithor_name(w):
    return "".join([x.capitalize() for x in w.split()])


_thor_mocks["alfred.utils"].natural_word_to_ithor_name = _mock_natural_word_to_ithor_name
_thor_mocks["alfred"].utils = _thor_mocks["alfred.utils"]

with patch.dict(sys.modules, _thor_mocks):
    from src.alfred.thor_connector import ThorConnector


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_obj(obj_id, pickupable=False, receptacle=False,
              visible=True, distance=0.5, parent_receptacles=None):
    return {
        "objectId": obj_id,
        "objectType": obj_id.split("|")[0],
        "pickupable": pickupable,
        "receptacle": receptacle,
        "visible": visible,
        "distance": distance,
        "parentReceptacles": parent_receptacles or [],
        "receptacleObjectIds": [],
        "isOpen": True,
        "position": {"x": 0, "y": 0, "z": 0},
        "rotation": {"x": 0, "y": 0, "z": 0},
    }


def _make_connector(objects, inventory_obj_id=None):
    """Create a ThorConnector with mocked internals."""
    tc = ThorConnector.__new__(ThorConnector)
    tc._obj_registry = {}
    tc._obj_registry_by_name = {}
    tc.cur_receptacle = None
    tc.sliced = False
    tc.agent_height = 0.9
    tc._last_found_label = None

    tc.last_event = MagicMock()
    inventory = (
        [{"objectId": inventory_obj_id, "objectType": inventory_obj_id.split("|")[0]}]
        if inventory_obj_id else []
    )
    tc.last_event.metadata = {
        "objects": objects,
        "lastActionSuccess": True,
        "errorMessage": "",
        "inventoryObjects": inventory,
    }

    # Build registry (same logic as ThorConnector._build_object_registry)
    type_counts = {}
    for obj in sorted(objects, key=lambda o: o["objectId"]):
        oid = obj["objectId"]
        otype = oid.split("|")[0]
        type_counts[otype] = type_counts.get(otype, 0) + 1
        readable = f"{otype}_{type_counts[otype]}"
        tc._obj_registry[oid] = readable
        tc._obj_registry_by_name[readable] = oid

    return tc


# ── Tests ─────────────────────────────────────────────────────────────────────

_INSTANCE_LABEL_PATTERN = re.compile(r"^Picked up \w+_\d+\.$")
_PUT_LABEL_PATTERN = re.compile(r"^Put \w+_\d+ in \w+_\d+\.$")


class TestPickObservation:

    def test_pick_success_returns_instance_label(self):
        """On successful pick, observation must match 'Picked up <Type>_<N>.'"""
        cup_id = "Cup|0|0|0"
        tc = _make_connector([_make_obj(cup_id, pickupable=True, visible=True)])

        with patch.object(ThorConnector, "step", return_value=MagicMock()):
            tc.last_event.metadata["lastActionSuccess"] = True
            result = tc.pick("Cup", target_obj_id=cup_id)

        assert _INSTANCE_LABEL_PATTERN.match(result), (
            f"Expected observation matching '{_INSTANCE_LABEL_PATTERN.pattern}', "
            f"got: {result!r}"
        )

    def test_pick_failure_observation_unchanged(self):
        """On failed pick, observation must NOT contain an instance label."""
        cup_id = "Cup|0|0|0"
        tc = _make_connector([_make_obj(cup_id, pickupable=True, visible=True)])
        # Simulate agent already holding something
        tc.last_event.metadata["inventoryObjects"] = [
            {"objectId": "Mug|1|1|1", "objectType": "Mug"}
        ]

        with patch.object(ThorConnector, "step", return_value=MagicMock()):
            tc.last_event.metadata["lastActionSuccess"] = False
            result = tc.pick("Cup", target_obj_id=cup_id)

        assert not _INSTANCE_LABEL_PATTERN.match(result), (
            f"Failure observation must not look like success label, got: {result!r}"
        )
        # Must be a non-empty failure message
        assert result != "", "Failure observation must not be empty"

    def test_pick_label_matches_registry_entry(self):
        """The instance label in observation must exactly match readable_id(obj_id)."""
        cup_id = "Cup|0|0|0"
        tc = _make_connector([_make_obj(cup_id, pickupable=True, visible=True)])
        expected_label = tc.readable_id(cup_id)  # e.g. "Cup_1"

        with patch.object(ThorConnector, "step", return_value=MagicMock()):
            tc.last_event.metadata["lastActionSuccess"] = True
            result = tc.pick("Cup", target_obj_id=cup_id)

        assert expected_label in result, (
            f"Expected '{expected_label}' in observation, got: {result!r}"
        )


class TestPutObservation:

    def test_put_success_returns_object_and_receptacle_labels(self):
        """On successful put, observation must match 'Put <Type>_<N> in <Type>_<M>.'"""
        cup_id = "Cup|0|0|0"
        counter_id = "CounterTop|1|1|1"
        tc = _make_connector(
            [_make_obj(cup_id, pickupable=True), _make_obj(counter_id, receptacle=True)],
            inventory_obj_id=cup_id,
        )

        with patch.object(ThorConnector, "step", return_value=MagicMock()), \
             patch.object(tc, "get_obj_id_from_name", return_value=(counter_id, None)):
            tc.last_event.metadata["lastActionSuccess"] = True
            result = tc.put("countertop")

        assert _PUT_LABEL_PATTERN.match(result), (
            f"Expected observation matching '{_PUT_LABEL_PATTERN.pattern}', "
            f"got: {result!r}"
        )

    def test_put_failure_observation_unchanged(self):
        """On failed put, observation must NOT contain the 'Put X in Y' label pattern."""
        cup_id = "Cup|0|0|0"
        counter_id = "CounterTop|1|1|1"
        tc = _make_connector(
            [_make_obj(cup_id, pickupable=True), _make_obj(counter_id, receptacle=True)],
            inventory_obj_id=cup_id,
        )

        with patch.object(ThorConnector, "step", return_value=MagicMock()), \
             patch.object(tc, "get_obj_id_from_name", return_value=(counter_id, None)):
            tc.last_event.metadata["lastActionSuccess"] = False
            result = tc.put("countertop")

        assert not _PUT_LABEL_PATTERN.match(result), (
            f"Failure observation must not look like success label, got: {result!r}"
        )
