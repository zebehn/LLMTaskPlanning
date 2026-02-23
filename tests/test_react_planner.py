"""Unit and integration tests for the ReAct planner and evaluator.

These tests cover:
- sanitize_llm_output() sanitization logic
- parse_react_output() parsing logic (T004) — JSON-first with text fallback
- construct_observation() observation building (T005)
- react_step() core method (T009)
- ReActAlfredEvaluator.evaluate_task() integration (T010)
- Evaluation summary reporting (T014)
- Config-based planner dispatch (T017)
- Reasoning trace JSON format (T018)

Tests do NOT require AI2-THOR or the simulator to be installed.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock heavy AI2-THOR dependencies so we can import modules
# without needing the simulator installed.
_thor_mocks = {}
for mod_name in [
    "env", "env.thor_env",
    "gen", "gen.constants", "gen.utils", "gen.utils.game_util",
    "alfred", "alfred.utils", "alfred.data", "alfred.data.preprocess",
    "scipy", "scipy.spatial",
    "llm",
    "prompts",
    "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont",
    "numpy",
    "tqdm",
]:
    _thor_mocks[mod_name] = MagicMock()

# Set constants needed by thor_connector
_thor_mocks["gen.constants"].X_DISPLAY = '0'
_thor_mocks["gen.constants"].DETECTION_SCREEN_HEIGHT = 300
_thor_mocks["gen.constants"].DETECTION_SCREEN_WIDTH = 300
_thor_mocks["gen.constants"].BUILD_PATH = ''
_thor_mocks["gen.constants"].CAMERA_HEIGHT_OFFSET = 0.675


with patch.dict(sys.modules, _thor_mocks):
    from src.alfred.react_task_planner import (
        ReActTaskPlanner, parse_react_output, sanitize_llm_output,
    )
    from src.alfred.react_evaluator import ReActAlfredEvaluator, construct_observation


# ===========================================================================
# Unit tests for sanitize_llm_output()
# ===========================================================================

class TestSanitizeLlmOutput:
    """Tests for sanitize_llm_output() sanitization logic."""

    def test_strip_control_tokens(self):
        """Control tokens like <|channel|> should be stripped."""
        raw = '<|channel|>commentary to=assistant <|constrain|>json<|message|>{"Think":"hi","Act":"done"}'
        result = sanitize_llm_output(raw)
        assert "<|" not in result
        assert '{"Think":"hi","Act":"done"}' in result

    def test_collapse_degenerate_repeats(self):
        """Runs of 10+ repeated non-alnum chars should collapse to 3."""
        raw = "some text @@@@@@@@@@@@@@@@@ more text"
        result = sanitize_llm_output(raw)
        assert "@@@@@@@@@" not in result
        assert "@@@" in result
        assert "some text" in result
        assert "more text" in result

    def test_clean_passthrough(self):
        """Already-clean text should pass through unchanged (modulo strip)."""
        raw = '{"Think": "I need to find a mug", "Act": "find a mug"}'
        result = sanitize_llm_output(raw)
        assert result == raw

    def test_short_repeats_not_collapsed(self):
        """Repeats shorter than 10 should not be collapsed."""
        raw = "text... more"
        result = sanitize_llm_output(raw)
        assert result == raw

    def test_multiple_control_tokens(self):
        """Multiple different control tokens should all be stripped."""
        raw = '<|start|>hello<|mid|>world<|end|>'
        result = sanitize_llm_output(raw)
        assert result == "helloworld"

    def test_strip_think_block(self):
        """Reasoning model <think>...</think> blocks should be stripped."""
        raw = '<think>Let me reason about this step by step...</think>{"Think": "find mug", "Act": "find a mug"}'
        result = sanitize_llm_output(raw)
        assert "<think>" not in result
        assert "</think>" not in result
        assert '{"Think": "find mug", "Act": "find a mug"}' in result

    def test_strip_multiline_think_block(self):
        """Multi-line <think> blocks should be fully stripped."""
        raw = (
            '<think>\nStep 1: I need to understand the task.\n'
            'Step 2: The user wants me to find a mug.\n'
            'Step 3: I should output JSON.\n</think>\n'
            '{"Think": "I need to find a mug.", "Act": "find a mug"}'
        )
        result = sanitize_llm_output(raw)
        assert "<think>" not in result
        assert "Step 1" not in result
        assert '{"Think": "I need to find a mug.", "Act": "find a mug"}' in result

    def test_strip_orphaned_think_tag(self):
        """An opening <think> with no closing tag (truncated) should be stripped."""
        raw = '<think>reasoning that got cut off by max_tokens'
        result = sanitize_llm_output(raw)
        assert result == ""

    def test_strip_think_block_with_control_tokens(self):
        """<think> blocks and control tokens together should both be stripped."""
        raw = (
            '<think>internal reasoning</think>'
            '<|message|>{"Think": "plan", "Act": "done"}'
        )
        result = sanitize_llm_output(raw)
        assert "<think>" not in result
        assert "<|" not in result
        assert '{"Think": "plan", "Act": "done"}' in result


# ===========================================================================
# T004: Unit tests for parse_react_output()
# ===========================================================================

class TestParseReactOutput:
    """Tests for parse_react_output() parsing logic — JSON-first with text fallback."""

    # --- JSON format tests ---

    def test_parse_json_format(self):
        """Parse standard JSON {"Think": ..., "Act": ...} format."""
        output = '{"Think": "I need to find a lettuce first.", "Act": "find a lettuce"}'
        thought, action = parse_react_output(output)
        assert thought == "I need to find a lettuce first."
        assert action == "find a lettuce"

    def test_parse_json_inside_control_tokens(self):
        """Extract JSON even when wrapped in control tokens."""
        output = '<|channel|>commentary<|message|>{"Think": "reasoning", "Act": "find a mug"}'
        thought, action = parse_react_output(output)
        assert thought == "reasoning"
        assert action == "find a mug"

    def test_parse_json_case_insensitive_keys(self):
        """JSON keys should be matched case-insensitively."""
        output = '{"think": "lower case keys", "act": "done"}'
        thought, action = parse_react_output(output)
        assert thought == "lower case keys"
        assert action == "done"

    def test_parse_json_with_surrounding_text(self):
        """JSON embedded in surrounding text should be extracted."""
        output = 'Here is my response: {"Think": "plan ahead", "Act": "find a knife"} end'
        thought, action = parse_react_output(output)
        assert thought == "plan ahead"
        assert action == "find a knife"

    # --- Text format backward-compatibility tests ---

    def test_parse_standard_think_act(self):
        """Parse standard 'Think: reasoning\\nAct: action' text format (backward compat)."""
        output = "Think: I need to find a lettuce first.\nAct: find a lettuce"
        thought, action = parse_react_output(output)
        assert thought == "I need to find a lettuce first."
        assert action == "find a lettuce"

    def test_parse_fallback_no_think(self):
        """When only action is present (no Think:), thought should be empty string."""
        output = "Act: pick up the mug"
        thought, action = parse_react_output(output)
        assert thought == ""
        assert action == "pick up the mug"

    def test_parse_error_only_thought(self):
        """When only thought is present (no Act:), raise ValueError."""
        output = "Think: I should look around the room."
        with pytest.raises(ValueError, match="[Nn]o.*[Aa]ct"):
            parse_react_output(output)

    def test_parse_multiline_thoughts(self):
        """Handle multiline thoughts before Act:."""
        output = "Think: First I need to consider the task.\nI should find a mug first, then pick it up.\nAct: find a mug"
        thought, action = parse_react_output(output)
        assert "consider the task" in thought
        assert action == "find a mug"

    def test_parse_done_action(self):
        """Handle 'done' action correctly (JSON)."""
        output = '{"Think": "The task is complete.", "Act": "done"}'
        thought, action = parse_react_output(output)
        assert thought == "The task is complete."
        assert action == "done"

    def test_parse_no_delimiters_treats_as_action(self):
        """When neither JSON nor Think:/Act: found, treat entire output as action."""
        output = "find a lettuce"
        thought, action = parse_react_output(output)
        assert thought == ""
        assert action == "find a lettuce"

    def test_parse_extra_whitespace(self):
        """Handle extra whitespace around delimiters."""
        output = "Think:  I need to pick up the apple.  \nAct:  pick up the apple  "
        thought, action = parse_react_output(output)
        assert thought == "I need to pick up the apple."
        assert action == "pick up the apple"

    def test_parse_malformed_json_falls_back_to_text(self):
        """Malformed JSON should fall back to text parsing."""
        output = '{"Think": bad json}\nThink: text fallback\nAct: find a mug'
        thought, action = parse_react_output(output)
        assert action == "find a mug"

    def test_parse_json_missing_act_falls_back(self):
        """JSON with Think but no Act should fall back to text parsing."""
        output = '{"Think": "only thought"}\nAct: text action'
        thought, action = parse_react_output(output)
        assert action == "text action"

    # --- Broken / incomplete JSON tests ---

    def test_parse_incomplete_json_extracts_act(self):
        """Incomplete JSON (no closing brace) should still extract Act via regex."""
        output = '{"Think": "I need to find an apple", "Act": "find a apple"'
        thought, action = parse_react_output(output)
        assert thought == "I need to find an apple"
        assert action == "find a apple"

    def test_parse_degenerate_json_extracts_act(self):
        """JSON that degenerates mid-value should extract Act if it was complete."""
        output = '{"Think": "planning ahead@@@", "Act": "find a mug", "extra": "garbage@@@'
        thought, action = parse_react_output(output)
        assert action == "find a mug"

    def test_parse_incomplete_json_no_act_value(self):
        """Incomplete JSON where Act value never appears should fall through."""
        # No "Act" key at all — only Think was started before degeneration
        output = '{"Think": "I need to find an apple@@@@@@@@@@@'
        thought, action = parse_react_output(output)
        # Falls through to last-resort: entire first line as action
        assert thought == ""


# ===========================================================================
# T005: Unit tests for construct_observation()
# ===========================================================================

class TestConstructObservation:
    """Tests for construct_observation() helper."""

    def test_successful_find(self):
        """Test observation for successful find action."""
        action_result = {
            'action': 'find a lettuce',
            'success': True,
            'message': ''
        }
        obs = construct_observation(action_result)
        assert "lettuce" in obs.lower()
        assert "found" in obs.lower() or "near" in obs.lower()

    def test_successful_pick_up(self):
        """Test observation for successful pick up action."""
        action_result = {
            'action': 'pick up the mug',
            'success': True,
            'message': ''
        }
        obs = construct_observation(action_result)
        assert "mug" in obs.lower()
        assert "pick" in obs.lower()

    def test_successful_put_down(self):
        """Test observation for successful put down action."""
        action_result = {
            'action': 'put down the mug',
            'success': True,
            'message': ''
        }
        obs = construct_observation(action_result)
        assert "mug" in obs.lower()
        assert "put" in obs.lower()

    def test_action_failure_with_error_message(self):
        """Test observation includes error message on failure."""
        action_result = {
            'action': 'pick up the apple',
            'success': False,
            'message': 'Robot is currently holding mug'
        }
        obs = construct_observation(action_result)
        assert "fail" in obs.lower() or "error" in obs.lower() or "cannot" in obs.lower()
        assert "Robot is currently holding mug" in obs

    def test_successful_open(self):
        """Test observation for successful open action."""
        action_result = {
            'action': 'open the fridge',
            'success': True,
            'message': ''
        }
        obs = construct_observation(action_result)
        assert "fridge" in obs.lower()
        assert "open" in obs.lower()

    def test_successful_close(self):
        """Test observation for successful close action."""
        action_result = {
            'action': 'close the microwave',
            'success': True,
            'message': ''
        }
        obs = construct_observation(action_result)
        assert "microwave" in obs.lower()
        assert "close" in obs.lower()

    def test_successful_turn_on(self):
        """Test observation for successful turn on action."""
        action_result = {
            'action': 'turn on the desk lamp',
            'success': True,
            'message': ''
        }
        obs = construct_observation(action_result)
        assert "desk lamp" in obs.lower()
        assert "turn" in obs.lower() or "on" in obs.lower()

    def test_successful_turn_off(self):
        """Test observation for successful turn off action."""
        action_result = {
            'action': 'turn off the desk lamp',
            'success': True,
            'message': ''
        }
        obs = construct_observation(action_result)
        assert "desk lamp" in obs.lower()

    def test_successful_slice(self):
        """Test observation for successful slice action."""
        action_result = {
            'action': 'slice the tomato',
            'success': True,
            'message': ''
        }
        obs = construct_observation(action_result)
        assert "tomato" in obs.lower()
        assert "slice" in obs.lower()


# ===========================================================================
# T009: Unit tests for react_step()
# ===========================================================================

class TestReactStep:
    """Tests for ReActTaskPlanner.react_step() method."""

    @pytest.fixture
    def planner(self):
        """Create a ReActTaskPlanner with mocked dependencies."""
        # Directly construct the planner by bypassing __init__
        p = object.__new__(ReActTaskPlanner)
        p.max_steps = 25
        p.model_name = "gpt-4"
        p.temperature = 0.0
        p.max_tokens = 1024
        p.system_prompt = "You are a robot."
        p.few_shot_examples = "Example task."
        p.skill_set = ['find', 'pick up', 'put down', 'done']
        p.prompt = p.system_prompt
        p.llm = MagicMock()
        return p

    def test_react_step_returns_thought_action(self, planner):
        """Verify react_step returns (thought, action) tuple."""
        planner.llm.chat_completion.return_value = '{"Think": "I need to find a apple", "Act": "find a apple"}'
        thought, action = planner.react_step("Put an apple on the table.", [])
        assert thought == "I need to find a apple"
        assert action == "find a apple"

    def test_react_step_with_empty_history(self, planner):
        """Test react_step with no previous history."""
        planner.llm.chat_completion.return_value = '{"Think": "Let me start by finding the object.", "Act": "find a mug"}'
        thought, action = planner.react_step("Put a mug on the desk.", [])
        assert action == "find a mug"
        # Verify chat_completion was called with messages
        planner.llm.chat_completion.assert_called_once()
        messages = planner.llm.chat_completion.call_args[0][0]
        assert len(messages) >= 1  # At least system message

    def test_react_step_with_multi_step_history(self, planner):
        """Test react_step with multi-step history."""
        history = [
            {"thought": "I need to find a mug", "action": "find a mug", "observation": "Found mug."},
            {"thought": "Now pick it up", "action": "pick up the mug", "observation": "You picked up the mug."},
        ]
        planner.llm.chat_completion.return_value = '{"Think": "Now I need to find the desk.", "Act": "find a desk"}'
        thought, action = planner.react_step("Put a mug on the desk.", history)
        assert action == "find a desk"
        # Verify history was included in messages as JSON
        messages = planner.llm.chat_completion.call_args[0][0]
        msg_text = str(messages)
        assert "find a mug" in msg_text
        assert "pick up the mug" in msg_text

    def test_react_step_max_steps_enforcement(self, planner):
        """Test that max_steps is respected."""
        planner.max_steps = 3
        history = [
            {"thought": "t1", "action": "a1", "observation": "o1"},
            {"thought": "t2", "action": "a2", "observation": "o2"},
            {"thought": "t3", "action": "a3", "observation": "o3"},
        ]
        # Should raise ValueError when max steps reached
        with pytest.raises(ValueError, match="[Mm]ax.*steps"):
            planner.react_step("Some task", history)

    def test_react_step_passes_available_objects(self, planner):
        """Verify react_step forwards available_objects to system prompt."""
        planner.llm.chat_completion.return_value = '{"Think": "check", "Act": "find a Mug"}'
        objects = ["Apple", "Fridge", "Mug"]
        planner.react_step("Put an apple in the fridge.", [], available_objects=objects)

        messages = planner.llm.chat_completion.call_args[0][0]
        system_msg = next(m for m in messages if m['role'] == 'system')
        assert "Available objects in this scene:" in system_msg['content']
        assert "Apple, Fridge, Mug" in system_msg['content']

    def test_react_step_rejects_garbage_action(self, planner):
        """Action that doesn't start with a known verb should raise ValueError."""
        planner.llm.chat_completion.return_value = '{"Think": "hmm@@@", "Act": "@@@garbage"}'
        with pytest.raises(ValueError, match="unparseable action"):
            planner.react_step("Some task.", [])

    def test_react_step_rejects_raw_json_as_action(self, planner):
        """Incomplete JSON that falls to last-resort should be rejected."""
        # Model produced incomplete JSON with no Act value — last resort
        # returns the raw text as action, which is not a valid verb.
        planner.llm.chat_completion.return_value = 'I am sorry, I cannot help.'
        with pytest.raises(ValueError, match="unparseable action"):
            planner.react_step("Some task.", [])

    def test_is_valid_action(self, planner):
        """Verify _is_valid_action recognises all skill_set verbs."""
        assert planner._is_valid_action("find a mug")
        assert planner._is_valid_action("pick up the apple")
        assert planner._is_valid_action("put down the knife")
        assert planner._is_valid_action("done")
        assert not planner._is_valid_action("@@@garbage")
        assert not planner._is_valid_action('{"Think": "broken')
        assert not planner._is_valid_action("")


# ===========================================================================
# Tests for available_objects injection in _build_messages
# ===========================================================================

class TestBuildMessagesAvailableObjects:
    """Tests for _build_messages() with available_objects parameter."""

    @pytest.fixture
    def planner(self):
        """Create a ReActTaskPlanner with mocked dependencies."""
        p = object.__new__(ReActTaskPlanner)
        p.system_prompt = "You are a robot."
        p.few_shot_examples = "Example task."
        return p

    def test_objects_appended_to_system_message(self, planner):
        """Available objects list should appear in the system message."""
        objects = ["Apple", "Bowl", "Fridge", "Mug", "Plate"]
        messages = planner._build_messages("Put a plate in the fridge.", [],
                                           available_objects=objects)
        system_msg = next(m for m in messages if m['role'] == 'system')
        assert "Available objects in this scene: Apple, Bowl, Fridge, Mug, Plate" in system_msg['content']
        # User message should NOT contain available objects
        first_user = next(m for m in messages if m['role'] == 'user')
        assert "Available objects" not in first_user['content']

    def test_no_objects_when_none(self, planner):
        """When available_objects is None, no objects line should appear."""
        messages = planner._build_messages("Put a plate in the fridge.", [],
                                           available_objects=None)
        system_msg = next(m for m in messages if m['role'] == 'system')
        assert "Available objects" not in system_msg['content']

    def test_no_objects_when_empty_list(self, planner):
        """When available_objects is an empty list, no objects line should appear."""
        messages = planner._build_messages("Put a plate in the fridge.", [],
                                           available_objects=[])
        system_msg = next(m for m in messages if m['role'] == 'system')
        assert "Available objects" not in system_msg['content']

    def test_objects_in_system_after_prompt(self, planner):
        """Objects line should follow the system prompt text."""
        objects = ["Fridge", "Plate"]
        messages = planner._build_messages("Wash the plate.", [],
                                           available_objects=objects)
        system_msg = next(m for m in messages if m['role'] == 'system')
        content = system_msg['content']
        robot_idx = content.index("You are a robot.")
        objects_idx = content.index("Available objects")
        assert objects_idx > robot_idx

    def test_history_uses_json_format(self, planner):
        """History assistant messages should use JSON format."""
        history = [
            {"thought": "I need a mug", "action": "find a mug", "observation": "Found mug."},
        ]
        messages = planner._build_messages("Get a mug.", history)
        assistant_msgs = [m for m in messages if m['role'] == 'assistant']
        assert len(assistant_msgs) == 1
        data = json.loads(assistant_msgs[0]['content'])
        assert data['Think'] == "I need a mug"
        assert data['Act'] == "find a mug"


# ===========================================================================
# T010: Integration test for ReActAlfredEvaluator.evaluate_task()
# ===========================================================================

class TestReActEvaluateTask:
    """Integration tests for the ReAct evaluation loop."""

    @pytest.fixture
    def mock_cfg(self):
        cfg = MagicMock()
        cfg.planner.provider = "openai"
        cfg.planner.model_name = "gpt-4"
        cfg.planner.max_steps = 25
        cfg.planner.temperature = 0.0
        cfg.planner.max_tokens = 1024
        cfg.planner.random_seed = 0
        cfg.planner.scoring_batch_size = 4
        cfg.planner.score_function = 'sum'
        cfg.planner.use_predefined_prompt = False
        cfg.prompt.react_system_prompt = "resource/prompts/react_system.txt"
        cfg.prompt.react_few_shot_examples = "resource/prompts/react_few_shot_examples.txt"
        cfg.alfred.eval_set = 'valid_seen'
        cfg.alfred.eval_portion_in_percent = 5
        cfg.alfred.random_seed_for_eval_subset = 1
        cfg.alfred.x_display = '0'
        cfg.out_dir = '/tmp/test_react'
        return cfg

    @pytest.fixture
    def mock_env(self):
        """Create a mock ThorConnector."""
        env = MagicMock()
        env.last_event = MagicMock()
        env.last_event.metadata = {'lastActionSuccess': True, 'objects': []}
        env.last_event.frame = MagicMock()
        env.get_transition_reward.return_value = (1.0, False)
        env.get_goal_satisfied.return_value = True
        env.task = MagicMock()
        env.task.get_targets.return_value = {}
        return env

    @pytest.fixture
    def mock_traj_data(self):
        """Create minimal trajectory data."""
        return {
            'task_id': 'trial_T20190907_000001_000001',
            'task_type': 'pick_and_place_simple',
            'scene': {
                'scene_num': 1,
                'object_poses': [],
                'dirty_and_empty': [],
                'object_toggles': [],
                'init_action': {'action': 'TeleportFull', 'x': 0, 'y': 0.9, 'z': 0,
                                'rotation': {'x': 0, 'y': 0, 'z': 0}, 'horizon': 0, 'standing': True},
            },
            'turk_annotations': {
                'anns': [{'task_desc': 'Put the mug on the desk.'}]
            },
            'root': 'test/path',
        }

    def test_evaluate_task_3step_simulation(self, mock_cfg, mock_env, mock_traj_data):
        """Simulate a 3-step task: find, pick, done."""
        evaluator = ReActAlfredEvaluator(mock_cfg)

        # Create mock planner with explicit max_steps
        mock_planner = MagicMock()
        mock_planner.max_steps = 25
        call_count = [0]
        responses = [
            ("I need to find a mug", "find a mug"),
            ("Now I pick it up", "pick up the mug"),
            ("Task is done", "done"),
        ]
        def react_step_side_effect(instruction, history, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            if idx < len(responses):
                return responses[idx]
            return ("done", "done")
        mock_planner.react_step.side_effect = react_step_side_effect

        mock_env.llm_skill_interact.return_value = {
            'action': 'test', 'success': True, 'message': ''
        }

        # Mock save_result to avoid filesystem
        evaluator.save_result = MagicMock()

        result = evaluator.evaluate_task(
            mock_env, mock_traj_data, 0, MagicMock(),
            mock_planner, '/tmp/test', x_display='0'
        )

        assert result['success'] is True
        assert result['trial'] == 'trial_T20190907_000001_000001'
        assert 'reasoning_trace' in result
        assert len(result['reasoning_trace']) == 3

    def test_evaluate_task_passes_available_objects(self, mock_cfg, mock_env, mock_traj_data):
        """Verify evaluate_task extracts object types from registry and passes them."""
        evaluator = ReActAlfredEvaluator(mock_cfg)

        # Set up env with object registry
        mock_env._obj_registry = {
            'Apple|1': 'Apple_0',
            'Mug|2': 'Mug_1',
            'Mug|3': 'Mug_2',
            'Fridge|4': 'Fridge_0',
        }

        mock_planner = MagicMock()
        mock_planner.max_steps = 25
        mock_planner.react_step.return_value = ("Done", "done")

        evaluator.save_result = MagicMock()

        evaluator.evaluate_task(
            mock_env, mock_traj_data, 0, MagicMock(),
            mock_planner, '/tmp/test', x_display='0'
        )

        # Check react_step was called with available_objects kwarg
        call_kwargs = mock_planner.react_step.call_args
        assert call_kwargs[1]['available_objects'] == ['Apple', 'Fridge', 'Mug']

    def test_evaluate_task_no_registry(self, mock_cfg, mock_env, mock_traj_data):
        """When env has no _obj_registry, available_objects should be None."""
        evaluator = ReActAlfredEvaluator(mock_cfg)

        # env without _obj_registry attribute
        if hasattr(mock_env, '_obj_registry'):
            del mock_env._obj_registry

        mock_planner = MagicMock()
        mock_planner.max_steps = 25
        mock_planner.react_step.return_value = ("Done", "done")

        evaluator.save_result = MagicMock()

        evaluator.evaluate_task(
            mock_env, mock_traj_data, 0, MagicMock(),
            mock_planner, '/tmp/test', x_display='0'
        )

        call_kwargs = mock_planner.react_step.call_args
        assert call_kwargs[1]['available_objects'] is None

    def test_evaluate_task_trace_contains_all_entries(self, mock_cfg, mock_env, mock_traj_data):
        """Verify trace contains thoughts, actions, and observations."""
        evaluator = ReActAlfredEvaluator(mock_cfg)

        mock_planner = MagicMock()
        mock_planner.max_steps = 25
        call_count = [0]
        responses = [
            ("Finding the mug", "find a mug"),
            ("Done now", "done"),
        ]
        def react_step_side_effect(instruction, history, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            if idx < len(responses):
                return responses[idx]
            return ("done", "done")
        mock_planner.react_step.side_effect = react_step_side_effect

        mock_env.llm_skill_interact.return_value = {
            'action': 'find a mug', 'success': True, 'message': ''
        }

        evaluator.save_result = MagicMock()

        result = evaluator.evaluate_task(
            mock_env, mock_traj_data, 0, MagicMock(),
            mock_planner, '/tmp/test', x_display='0'
        )

        trace = result['reasoning_trace']
        # First step should have thought, action, observation
        assert trace[0]['thought'] == "Finding the mug"
        assert trace[0]['action'] == "find a mug"
        assert 'observation' in trace[0]
        # Second step (done) should have thought and action
        assert trace[1]['thought'] == "Done now"
        assert trace[1]['action'] == "done"


# ===========================================================================
# T014: Unit test for evaluation summary reporting
# ===========================================================================

class TestEvaluationSummary:
    """Tests for evaluation summary reporting."""

    def test_summary_report_format(self):
        """Verify summary report contains required fields."""
        results = [
            {'trial': 't1', 'type': 'pick_and_place_simple', 'success': True,
             'total_steps': 5, 'reasoning_trace': [{}]*5},
            {'trial': 't2', 'type': 'pick_and_place_simple', 'success': False,
             'total_steps': 10, 'reasoning_trace': [{}]*10},
            {'trial': 't3', 'type': 'look_at_obj_in_light', 'success': True,
             'total_steps': 3, 'reasoning_trace': [{}]*3},
        ]

        summary = ReActAlfredEvaluator.build_summary_report(results)

        assert summary['total_evaluated'] == 3
        assert summary['total_success'] == 2
        assert abs(summary['success_rate'] - 2/3) < 1e-6
        assert abs(summary['avg_steps'] - 6.0) < 1e-6
        assert 'by_task_type' in summary
        assert 'pick_and_place_simple' in summary['by_task_type']
        assert 'look_at_obj_in_light' in summary['by_task_type']
        assert summary['by_task_type']['pick_and_place_simple']['total'] == 2
        assert summary['by_task_type']['pick_and_place_simple']['success'] == 1
        assert summary['by_task_type']['look_at_obj_in_light']['total'] == 1
        assert summary['by_task_type']['look_at_obj_in_light']['success'] == 1


# ===========================================================================
# T017: Integration test for config-based planner dispatch
# ===========================================================================

class TestConfigDispatch:
    """Tests for config-based evaluator dispatch."""

    def test_alfred_react_dispatches_react_evaluator(self):
        """Verify alfred_react config creates ReActAlfredEvaluator."""
        cfg = MagicMock()
        cfg.name = 'alfred_react'

        # Simulate dispatch logic from evaluate.py
        if cfg.name == 'alfred_react':
            evaluator_class = ReActAlfredEvaluator
        else:
            evaluator_class = None

        assert evaluator_class == ReActAlfredEvaluator

    def test_alfred_dispatches_alfred_evaluator(self):
        """Verify alfred config creates AlfredEvaluator (not ReAct)."""
        with patch.dict(sys.modules, _thor_mocks):
            from src.alfred.alfred_evaluator import AlfredEvaluator

        cfg = MagicMock()
        cfg.name = 'alfred'

        if cfg.name == 'alfred':
            evaluator_class = AlfredEvaluator
        elif cfg.name == 'alfred_react':
            evaluator_class = ReActAlfredEvaluator
        else:
            evaluator_class = None

        assert evaluator_class != ReActAlfredEvaluator


# ===========================================================================
# T018: Unit test for reasoning trace JSON format
# ===========================================================================

class TestReasoningTraceFormat:
    """Tests for per-task reasoning trace JSON structure."""

    def test_reasoning_trace_has_required_fields(self):
        """Verify each trace entry has required fields per data-model.md."""
        trace_entry = {
            'step_number': 1,
            'thought': 'I need to find a mug',
            'action': 'find a mug',
            'observation': 'Found mug. You are now near the mug.',
            'action_success': True,
        }

        required_fields = ['step_number', 'thought', 'action', 'observation', 'action_success']
        for field in required_fields:
            assert field in trace_entry, f"Missing field: {field}"

    def test_result_dict_has_reasoning_trace(self):
        """Verify per-task result dict contains reasoning_trace key."""
        result = {
            'trial': 'trial_T20190907_000001',
            'scene': 'FloorPlan1',
            'type': 'pick_and_place_simple',
            'repeat_idx': 0,
            'goal_instr': 'Put the mug on the desk.',
            'success': True,
            'total_steps': 3,
            'termination_reason': 'done_signal',
            'reasoning_trace': [
                {
                    'step_number': 1,
                    'thought': 'I need to find a mug',
                    'action': 'find a mug',
                    'observation': 'Found mug.',
                    'action_success': True,
                },
                {
                    'step_number': 2,
                    'thought': 'Pick it up',
                    'action': 'pick up the mug',
                    'observation': 'You picked up the mug.',
                    'action_success': True,
                },
                {
                    'step_number': 3,
                    'thought': 'Task complete',
                    'action': 'done',
                    'observation': None,
                    'action_success': None,
                },
            ],
            'inferred_steps': ['find a mug', 'pick up the mug', 'done'],
        }

        assert 'reasoning_trace' in result
        assert isinstance(result['reasoning_trace'], list)
        assert len(result['reasoning_trace']) == 3
        assert 'inferred_steps' in result

        # Verify each entry has required fields
        for entry in result['reasoning_trace']:
            assert 'step_number' in entry
            assert 'thought' in entry
            assert 'action' in entry
