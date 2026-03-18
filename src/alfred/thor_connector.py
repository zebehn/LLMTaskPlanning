import os, math, re
import textwrap

import numpy as np
from scipy import spatial
from PIL import Image, ImageDraw, ImageFont
import logging

from env.thor_env import ThorEnv
from gen import constants
from gen.utils.game_util import get_objects_with_name_and_prop
from alfred.utils import natural_word_to_ithor_name

log = logging.getLogger(__name__)


class ThorConnector(ThorEnv):
    def __init__(self, x_display=constants.X_DISPLAY,
                 player_screen_height=constants.DETECTION_SCREEN_HEIGHT,
                 player_screen_width=constants.DETECTION_SCREEN_WIDTH,
                 quality='MediumCloseFitShadows',
                 build_path=constants.BUILD_PATH):
        super().__init__(x_display, player_screen_height, player_screen_width, quality, build_path)
        # Try to load a font, fall back to default if not available
        try:
            self.font = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuMono-B.ttf", 24)
        except OSError:
            try:
                self.font = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", 24)  # macOS
            except OSError:
                self.font = ImageFont.load_default()
        self.agent_height = 0.9
        self.cur_receptacle = None
        self.reachable_positions, self.reachable_position_kdtree = None, None
        self.sliced = False
        self._obj_registry = {}  # AI2-THOR objectId -> readable name
        self._obj_registry_by_name = {}  # readable name -> AI2-THOR objectId
        self._last_found_label = None  # readable_id of last successfully navigated object

    def restore_scene(self, object_poses, object_toggles, dirty_and_empty):
        super().restore_scene(object_poses, object_toggles, dirty_and_empty)
        self.reachable_positions, self.reachable_position_kdtree = self.get_reachable_positions()
        self.cur_receptacle = None
        self._build_object_registry()

    def _build_object_registry(self, preserve_existing=False):
        """Build a mapping from AI2-THOR objectIds to human-readable names.

        Args:
            preserve_existing: If True, keeps existing objectId→label mappings
                and only assigns new labels to objects not yet registered.
                Use this after in-scene state changes (e.g. slicing) so that
                instance labels remain stable across object state transitions.
                If False (default), rebuilds the registry from scratch.
        """
        objects = self.last_event.metadata['objects']

        if not preserve_existing:
            self._obj_registry = {}
            self._obj_registry_by_name = {}
            type_counts = {}
            for obj in sorted(objects, key=lambda o: o['objectId']):
                obj_id = obj['objectId']
                obj_type = obj_id.split('|')[0]
                type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
                readable_name = f"{obj_type}_{type_counts[obj_type]}"
                self._obj_registry[obj_id] = readable_name
                self._obj_registry_by_name[readable_name] = obj_id
        else:
            # Incremental update: preserve existing labels, add new objects only.
            existing_ids = {obj['objectId'] for obj in objects}

            # Build a lookup for quick property access.
            obj_by_id = {o['objectId']: o for o in objects}

            # Remove stale entries for objects AI2-THOR removed (e.g. consumed items).
            # For sliceable objects, AI2-THOR replaces the original with slice children
            # whose objectIds are prefixed by the original (e.g. Bread|x|y|z →
            # Bread|x|y|z|BreadSliced_1). Remap the original label to the first slice
            # so that instance IDs remain stable across the slice state transition.
            for oid in list(self._obj_registry.keys()):
                if oid not in existing_ids:
                    label = self._obj_registry.pop(oid)
                    self._obj_registry_by_name.pop(label, None)
                    # Look for slice children: objectIds that start with oid + '|'
                    slice_ids = sorted(
                        sid for sid in existing_ids
                        if sid.startswith(oid + '|') and sid not in self._obj_registry
                    )
                    if slice_ids:
                        first_slice = slice_ids[0]
                        self._obj_registry[first_slice] = label
                        self._obj_registry_by_name[label] = first_slice
                        log.info(f"      [registry] remapped {label}: {oid} → {first_slice}")

            # Handle the case where the original objectId stays in the scene but
            # AI2-THOR marks it isSliced=True (non-pickupable). In this case the
            # original is a "marker" and the actual pickupable pieces are new
            # objects whose type is {OrigType}Sliced or whose objectId is prefixed
            # by the original oid. Remap the label to the best slice piece so that
            # the model can continue using the same instance label (e.g. Bread_1).
            for oid in list(self._obj_registry.keys()):
                obj = obj_by_id.get(oid)
                if obj is None:
                    continue
                if not obj.get('isSliced', False):
                    continue
                # Already pickupable sliced object — no remap needed.
                if obj.get('pickupable', True):
                    continue
                label = self._obj_registry[oid]
                orig_type = oid.split('|')[0]
                slice_type = orig_type + 'Sliced'
                # Candidate slice pieces: prefix-children OR same {Type}Sliced type, not yet registered.
                candidates = sorted(
                    (o for o in objects
                     if o['objectId'] not in self._obj_registry
                     and (o['objectId'].startswith(oid + '|')
                          or o['objectId'].split('|')[0] == slice_type)),
                    key=lambda o: o['distance']
                )
                if candidates:
                    best = next((c for c in candidates if c.get('pickupable', False)), candidates[0])
                    new_oid = best['objectId']
                    del self._obj_registry[oid]
                    self._obj_registry_by_name.pop(label, None)
                    self._obj_registry[new_oid] = label
                    self._obj_registry_by_name[label] = new_oid
                    log.info(f"      [registry] remapped sliced {label}: {oid} → {new_oid}")

            # Determine current max count per type from preserved labels.
            type_counts = {}
            for label in self._obj_registry.values():
                parts = label.rsplit('_', 1)
                if len(parts) == 2 and parts[1].isdigit():
                    obj_type = parts[0]
                    type_counts[obj_type] = max(type_counts.get(obj_type, 0), int(parts[1]))

            # Assign labels only to objects not yet in the registry.
            for obj in sorted(objects, key=lambda o: o['objectId']):
                obj_id = obj['objectId']
                if obj_id not in self._obj_registry:
                    obj_type = obj_id.split('|')[0]
                    type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
                    readable_name = f"{obj_type}_{type_counts[obj_type]}"
                    self._obj_registry[obj_id] = readable_name
                    self._obj_registry_by_name[readable_name] = obj_id

        num_types = len(set(lbl.rsplit('_', 1)[0] for lbl in self._obj_registry.values()))
        log.info(f"      Object registry: {len(self._obj_registry)} objects "
                 f"({num_types} types)")

    @staticmethod
    def _is_instance_id(token: str) -> bool:
        """Check if a token matches the instance ID pattern (e.g., Apple_1, DeskLamp_02)."""
        return bool(re.match(r'^[A-Z][a-zA-Z]*_\d+$', token))

    @staticmethod
    def _normalize_instance_id(instance_id: str) -> str:
        """Normalize instance ID by stripping leading zeros from numeric suffix."""
        parts = instance_id.rsplit('_', 1)
        if len(parts) == 2:
            return f"{parts[0]}_{parts[1].lstrip('0') or '0'}"
        return instance_id

    def _resolve_instance_id(self, instance_id: str):
        """Resolve a human-readable instance ID to (thor_object_id, object_type) or None."""
        normalized = self._normalize_instance_id(instance_id)
        thor_id = self._obj_registry_by_name.get(normalized)
        if thor_id is None:
            return None
        obj_type = thor_id.split('|')[0]
        return thor_id, obj_type

    def readable_id(self, obj_id):
        """Return human-readable name for an AI2-THOR objectId."""
        if obj_id is None:
            return "None"
        return self._obj_registry.get(obj_id, obj_id)

    def get_reachable_positions(self):
        free_positions = super().step(dict(action="GetReachablePositions")).metadata["actionReturn"]
        free_positions = np.array([[p['x'], p['y'], p['z']] for p in free_positions])
        kd_tree = spatial.KDTree(free_positions)
        return free_positions, kd_tree

    def write_step_on_img(self, cfg, idx, description):
        img = Image.fromarray(self.last_event.frame)
        text = str(idx) + ':' + description['action']
        lines = textwrap.wrap(text, width=20)
        y_text = 6
        draw = ImageDraw.Draw(img)
        for line in lines:
            # Use getbbox for Pillow 10+ compatibility (getsize was deprecated)
            bbox = self.font.getbbox(line)
            height = bbox[3] - bbox[1]
            draw.text((6, y_text), line, font=self.font, fill=(255, 255, 255))
            y_text += height
        if cfg is True:
            if not description['success']:
                text_msg = 'error : ' + description['message']
                lines = textwrap.wrap(text_msg, width=20)
                for line in lines:
                    bbox = self.font.getbbox(line)
                    height = bbox[3] - bbox[1]
                    draw.text((6, y_text + 6), line, font=self.font, fill=(255, 0, 0))
                    y_text += height
        return img


    def find_close_reachable_position(self, loc, nth=1):
        d, i = self.reachable_position_kdtree.query(loc, k=nth + 1)
        selected = i[nth - 1]
        return self.reachable_positions[selected]

    def _dispatch_instance_or_generic(self, obj_name, action_method, **kwargs):
        """Dispatch to action method with instance ID resolution or generic flow."""
        if self._is_instance_id(obj_name):
            resolved = self._resolve_instance_id(obj_name)
            if resolved is None:
                log.info(f"      [instance] '{obj_name}' not found in registry")
                return f"Instance ID '{obj_name}' not found in object registry"
            thor_id, obj_type = resolved
            log.info(f"      [instance] {obj_name} -> {thor_id}")
            return action_method(obj_type, target_obj_id=thor_id, **kwargs)
        else:
            return action_method(natural_word_to_ithor_name(obj_name), **kwargs)

    def llm_skill_interact(self, instruction: str):
        # Determine whether this instruction should preserve the current receptacle target.
        # - "put down" / "open": explicit carve-outs (receptacle is actively being used)
        # - "pick up": agent is about to carry an object to the already-chosen receptacle
        # - instance find (e.g. "find Plate_1"): navigating back to an object to pick it up,
        #   so the previous type-based receptacle (e.g. "sink") must not be overwritten.
        # Everything else (type-based find, turn on/off, slice, drop, close) resets the
        # receptacle so stale state cannot carry over to a later put-down.
        _find_target = (instruction.replace('find a ', '').replace('find an ', '').replace('find ', '')
                        if instruction.startswith("find ") else None)
        _is_instance_find = _find_target is not None and self._is_instance_id(_find_target)
        _preserve_receptacle = (
            instruction.startswith("put down ")
            or instruction.startswith("open ")
            or instruction.startswith("pick up ")
            or _is_instance_find
        )
        if not _preserve_receptacle:
            self.cur_receptacle = None

        if instruction.startswith("find "):
            obj_name = _find_target
            if _is_instance_find:
                # Instance find: navigate to a known object without changing the receptacle.
                resolved = self._resolve_instance_id(obj_name)
                if resolved is None:
                    log.info(f"      [instance] '{obj_name}' not found in registry")
                    ret = f"Instance ID '{obj_name}' not found in object registry"
                else:
                    thor_id, obj_type = resolved
                    log.info(f"      [instance] {obj_name} -> {thor_id}")
                    ret = self.nav_obj(obj_type, self.sliced, target_obj_id=thor_id)
            else:
                # Type-based find (e.g. "find a sink") — set the receptacle target.
                self.cur_receptacle = obj_name
                ret = self.nav_obj(natural_word_to_ithor_name(obj_name), self.sliced)
        elif instruction.startswith("pick up "):
            obj_name = instruction.replace('pick up the ', '').replace('pick up ', '')
            ret = self._dispatch_instance_or_generic(obj_name, self.pick)
            # If pick up failed (e.g. already holding something), clear the receptacle
            # so a subsequent "put down" drops the held object safely instead of
            # attempting to place it into a stale / irrelevant receptacle.
            if not self.last_event.metadata['lastActionSuccess']:
                self.cur_receptacle = None
        elif instruction.startswith("put down "):
            if self.cur_receptacle is None:
                ret = self.drop()
            else:
                m = re.match(r'put down (.+)', instruction)
                obj = m.group(1).replace('the ', '')
                receptacle = self.cur_receptacle
                if self._is_instance_id(receptacle):
                    resolved = self._resolve_instance_id(receptacle)
                    if resolved is None:
                        ret = f"Instance ID '{receptacle}' not found in object registry"
                    else:
                        thor_id, obj_type = resolved
                        ret = self.put(obj_type, target_obj_id=thor_id)
                else:
                    ret = self.put(natural_word_to_ithor_name(receptacle))

            # put() now returns a success annotation on success (e.g. "Put Pan_1 in Fridge_1.").
            # Only override to failure message when the action actually failed.
            if not self.last_event.metadata['lastActionSuccess']:
                ret = 'put down failed'

        elif instruction.startswith("open "):
            obj_name = instruction.replace('open the ', '').replace('open ', '')
            ret = self._dispatch_instance_or_generic(obj_name, self.open)
        elif instruction.startswith("close "):
            obj_name = instruction.replace('close the ', '').replace('close ', '')
            ret = self._dispatch_instance_or_generic(obj_name, self.close)
        elif instruction.startswith("turn on "):
            obj_name = instruction.replace('turn on the ', '').replace('turn on ', '')
            ret = self._dispatch_instance_or_generic(obj_name, self.toggleon)
        elif instruction.startswith("turn off "):
            obj_name = instruction.replace('turn off the ', '').replace('turn off ', '')
            ret = self._dispatch_instance_or_generic(obj_name, self.toggleoff)
        elif instruction.startswith("slice "):
            obj_name = instruction.replace('slice the ', '').replace('slice ', '')
            ret = self._dispatch_instance_or_generic(obj_name, self.slice)
            self.sliced = True
        elif instruction.startswith("drop"):
            ret = self.drop()
        else:
            assert False, 'instruction not supported'

        # nav_obj returns '' on success and a non-empty error string on failure.
        # Do NOT use lastActionSuccess for find: nav_obj may skip every simulator
        # step when the target is already visible and close, leaving lastActionSuccess
        # stale from the previous action (which may have been a failure).
        # For all other actions trust lastActionSuccess as the ground truth.
        if instruction.startswith("find "):
            action_failed = (len(ret) > 0)
            # Ensure lastActionSuccess reflects the nav_obj outcome so that
            # subsequent actions start from a clean state.
            if not action_failed:
                self.last_event.metadata['lastActionSuccess'] = True
        else:
            action_failed = not self.last_event.metadata['lastActionSuccess']

        if action_failed:
            # Ensure lastActionSuccess reflects the actual failure
            self.last_event.metadata['lastActionSuccess'] = False
            if len(ret) > 0:
                log.info(f"      => FAIL: {ret}")
        else:
            # For find actions, include the instance label in the message so
            # construct_observation can emit e.g. "You are now near the Fridge_1."
            if instruction.startswith("find ") and self._last_found_label:
                ret = self._last_found_label
            log.info(f"      => ok" + (f": {ret}" if ret else ""))

        ret_dict = {
            'action': instruction,
            'success': not action_failed,
            'message': ret
        }

        return ret_dict

    def get_object_prop(self, name, prop, metadata):
        for obj in metadata['objects']:
            if name in obj['objectId']:
                return obj[prop]
        return None

    @staticmethod
    def angle_diff(x, y):
        x = math.radians(x)
        y = math.radians(y)
        return math.degrees(math.atan2(math.sin(x - y), math.cos(x - y)))
    def nav_obj(self, target_obj: str, prefer_sliced=False, target_obj_id=None):
        objects = self.last_event.metadata['objects']
        ret_msg = ''
        log.info(f'      [nav_obj] target={target_obj}' + (f', target_obj_id={target_obj_id}' if target_obj_id else ''))

        if target_obj_id is not None:
            # Instance-specific: use provided objectId directly
            obj_id = target_obj_id
            obj_data = None
            for o in objects:
                if o['objectId'] == target_obj_id:
                    obj_data = o
                    break
            if obj_data:
                log.info(f'      [nav_obj] selected {self.readable_id(obj_id)}, visible={obj_data["visible"]}, distance={obj_data["distance"]:.2f}')
        else:
            # Generic: find closest matching object by type
            obj_id, obj_data = self.get_obj_id_from_name(target_obj, priority_in_visibility=True, priority_sliced=prefer_sliced)
            if obj_id:
                log.info(f'      [nav_obj] selected {self.readable_id(obj_id)}, visible={obj_data["visible"]}, distance={obj_data["distance"]:.2f}')

        # find object index from id
        obj_idx = -1
        for i, o in enumerate(objects):
            if o['objectId'] == obj_id:
                obj_idx = i
                break

        if obj_idx == -1:
            # Log available object types in scene for debugging
            available_types = sorted(set(o['objectId'].split('|')[0] for o in objects))
            log.warning(f'Cannot find {target_obj}. Available object types: {available_types}')
            ret_msg = f'Cannot find {target_obj}'
        else:
            # teleport sometimes fails even with reachable positions. if fails, repeat with the next closest reachable positions.
            max_attempts = 20
            teleport_success = False

            # get obj location
            loc = objects[obj_idx]['position']
            obj_rot = objects[obj_idx]['rotation']['y']

            # do not move if the object is already visible and close
            if objects[obj_idx]['visible'] and objects[obj_idx]['distance'] < 1.0:
                log.info('      [nav_obj] already visible and close')
                max_attempts = 0
                teleport_success = True

            # try teleporting
            reachable_pos_idx = 0
            for i in range(max_attempts):
                reachable_pos_idx += 1
                if i == 10 and (target_obj == 'Fridge' or target_obj == 'Microwave'):
                    reachable_pos_idx -= 10

                closest_loc = self.find_close_reachable_position([loc['x'], loc['y'], loc['z']], reachable_pos_idx)

                # calculate desired rotation angle (see https://github.com/allenai/ai2thor/issues/806)
                rot_angle = math.atan2(-(loc['x'] - closest_loc[0]), loc['z'] - closest_loc[2])
                if rot_angle > 0:
                    rot_angle -= 2 * math.pi
                rot_angle = -(180 / math.pi) * rot_angle  # in degrees

                if i < 10 and (target_obj == 'Fridge' or target_obj == 'Microwave'):  # not always correct, but better than nothing
                    angle_diff = abs(self.angle_diff(rot_angle, obj_rot))
                    if target_obj == 'Fridge' and \
                            not ((90 - 20 < angle_diff < 90 + 20) or (270 - 20 < angle_diff < 270 + 20)):
                        continue
                    if target_obj == 'Microwave' and \
                            not ((180 - 20 < angle_diff < 180 + 20) or (0 - 20 < angle_diff < 0 + 20)):
                        continue

                # calculate desired horizon angle
                camera_height = self.agent_height + constants.CAMERA_HEIGHT_OFFSET
                xz_dist = math.hypot(loc['x'] - closest_loc[0], loc['z'] - closest_loc[2])
                hor_angle = math.atan2((loc['y'] - camera_height), xz_dist)
                hor_angle = (180 / math.pi) * hor_angle  # in degrees
                hor_angle *= 0.9  # adjust angle for better view
                # AI2-THOR 5.x: horizon must be in [-30, 60] range
                horizon = max(-30, min(60, -hor_angle))

                # teleport (AI2-THOR 5.x: Vector3 rotation, standing required, use y from reachable positions)
                super().step(dict(action="TeleportFull",
                                  x=closest_loc[0], y=closest_loc[1], z=closest_loc[2],
                                  rotation={'x': 0, 'y': rot_angle, 'z': 0},
                                  horizon=horizon,
                                  standing=True))

                if not self.last_event.metadata['lastActionSuccess']:
                    log.debug(
                        f"TeleportFull attempt {i+1}: {self.last_event.metadata['errorMessage']}")
                else:
                    teleport_success = True
                    log.info(f'      [nav_obj] TeleportFull ok (attempt {i+1})')
                    break

            if not teleport_success:
                log.info(f'      [nav_obj] TeleportFull failed after {max_attempts} attempts')
                ret_msg = f'Cannot move to {target_obj}'
            else:
                # Verify target object is visible after navigation
                # If not visible, try rotating to find it
                if target_obj_id is not None:
                    # Instance path: look up specific object by ID
                    obj_data_check = None
                    for o in self.last_event.metadata['objects']:
                        if o['objectId'] == target_obj_id:
                            obj_data_check = o
                            break
                else:
                    _, obj_data_check = self.get_obj_id_from_name(target_obj, priority_sliced=prefer_sliced)

                if obj_data_check and not obj_data_check['visible']:
                    log.info(f'      [nav_obj] {target_obj} not visible, scanning...')
                    found = False
                    # Fine-grained horizontal sweep: 12x30° = 360°
                    for rotation_attempt in range(12):
                        super().step(dict(action="RotateRight", degrees=30))
                        if target_obj_id is not None:
                            obj_data_check = None
                            for o in self.last_event.metadata['objects']:
                                if o['objectId'] == target_obj_id:
                                    obj_data_check = o
                                    break
                        else:
                            _, obj_data_check = self.get_obj_id_from_name(target_obj, priority_sliced=prefer_sliced)
                        if obj_data_check and obj_data_check['visible']:
                            log.info(f'      [nav_obj] {target_obj} visible after {(rotation_attempt+1)*30}deg rotation')
                            found = True
                            break

                    if not found:
                        # Try vertical camera adjustments at current rotation
                        for look_action in ["LookUp", "LookDown", "LookDown"]:
                            super().step(dict(action=look_action))
                            if target_obj_id is not None:
                                obj_data_check = None
                                for o in self.last_event.metadata['objects']:
                                    if o['objectId'] == target_obj_id:
                                        obj_data_check = o
                                        break
                            else:
                                _, obj_data_check = self.get_obj_id_from_name(target_obj, priority_sliced=prefer_sliced)
                            if obj_data_check and obj_data_check['visible']:
                                log.info(f'      [nav_obj] {target_obj} visible after camera tilt')
                                found = True
                                break

        # Record which instance was successfully navigated to (used by llm_skill_interact
        # to include an instance label in the find observation).
        if ret_msg == '':
            self._last_found_label = self.readable_id(obj_id)
        else:
            self._last_found_label = None

        return ret_msg

    def get_obj_id_from_name(self, obj_name, only_pickupable=False, only_toggleable=False, priority_sliced=False, get_inherited=False,
                             parent_receptacle_penalty=True, priority_in_visibility=False, require_visibility=False, exclude_obj_id=None,
                             only_open_receptacles=False):
        obj_id = None
        obj_data = None
        min_distance = 1e+8
        for obj in self.last_event.metadata['objects']:
            if obj['objectId'] == exclude_obj_id:
                continue

            # Skip non-visible objects if visibility is required
            if require_visibility and not obj['visible']:
                continue

            # Skip closed openable receptacles if only_open_receptacles is True
            if only_open_receptacles and obj.get('openable') and not obj.get('isOpen'):
                continue

            if (only_pickupable is False or obj['pickupable']) and \
                    (only_toggleable is False or obj['toggleable']) and \
                    obj['objectId'].split('|')[0].casefold() == obj_name.casefold() and \
                    (get_inherited is False or len(obj['objectId'].split('|')) == 5):
                if obj["distance"] < min_distance:
                    penalty_advantage = 0  # low priority for objects in closable receptacles such as fridge, microwave
                    if parent_receptacle_penalty and obj['parentReceptacles']:
                        for p in obj['parentReceptacles']:
                            is_open = self.get_object_prop(p, 'isOpen', self.last_event.metadata)
                            openable = self.get_object_prop(p, 'openable', self.last_event.metadata)
                            if openable is True and is_open is False:
                                penalty_advantage += 100000
                                break

                    if obj_name.casefold() == 'stoveburner':
                        # try to find an empty stove
                        if len(obj['receptacleObjectIds']) > 0:
                            penalty_advantage += 10000

                    if priority_in_visibility and obj['visible'] is False:
                        penalty_advantage += 1000

                    if priority_sliced and '_Slice' in obj['name']:
                        penalty_advantage += -100  # prefer sliced objects; this prevents picking up non-sliced objects

                    if obj["distance"] + penalty_advantage < min_distance:
                        min_distance = obj["distance"] + penalty_advantage
                        obj_data = obj
                        obj_id = obj["objectId"]

        return obj_id, obj_data

    def pick(self, obj_name, target_obj_id=None):
        if target_obj_id is not None:
            obj_id = target_obj_id
            obj_data = None
            for o in self.last_event.metadata['objects']:
                if o['objectId'] == target_obj_id:
                    obj_data = o
                    break
        else:
            obj_id, obj_data = self.get_obj_id_from_name(obj_name, only_pickupable=True, priority_in_visibility=True, priority_sliced=self.sliced)
        ret_msg = ''
        log.info(f'      [pick] target={obj_name}, obj={self.readable_id(obj_id)}')

        if obj_id is None:
            ret_msg = f'Cannot find {obj_name} to pick up'
        else:
            if obj_data['visible'] is False and obj_data['parentReceptacles'] is not None and len(obj_data['parentReceptacles']) > 0:
                recep_name = obj_data["parentReceptacles"][0].split('|')[0]
                recep_is_open = self.get_object_prop(
                    obj_data['parentReceptacles'][0], 'isOpen', self.last_event.metadata)

                if recep_is_open:
                    # Receptacle is open — object should be accessible, just not in camera view.
                    # Try camera adjustments to bring object into view.
                    log.info(f'      [pick] {obj_name} not visible in open {recep_name}, adjusting camera')
                    picked = False
                    for look_action in ["LookUp", "LookDown", "LookDown"]:
                        super().step(dict(action=look_action))
                        super().step(dict(
                            action="PickupObject",
                            objectId=obj_id,
                            forceAction=False
                        ))
                        if self.last_event.metadata['lastActionSuccess']:
                            picked = True
                            break

                    if not picked:
                        # Camera adjustments didn't help — force pickup since receptacle is open
                        log.info(f'      [pick] forcing pickup from open {recep_name}')
                        super().step(dict(
                            action="PickupObject",
                            objectId=obj_id,
                            forceAction=True
                        ))
                        if not self.last_event.metadata['lastActionSuccess']:
                            ret_msg = f'{obj_name} is not visible because it is in {recep_name}'
                else:
                    ret_msg = f'{obj_name} is not visible because it is in {recep_name}'
                    # try anyway (will fail if container is closed)
                    super().step(dict(
                        action="PickupObject",
                        objectId=obj_id,
                        forceAction=False
                    ))
            else:
                super().step(dict(
                    action="PickupObject",
                    objectId=obj_id,
                    forceAction=False
                ))
                
                if not self.last_event.metadata['lastActionSuccess']:
                    if len(self.last_event.metadata['inventoryObjects']) == 0:
                        ret_msg = f'Robot is not holding any object'
                    else:
                        # check if the agent is holding the object
                        holding_obj_id = self.last_event.metadata['inventoryObjects'][0]['objectId']
                        holding_obj_type = self.last_event.metadata['inventoryObjects'][0]['objectType']
                        ret_msg = f'Robot is currently holding {holding_obj_type}'

            if self.last_event.metadata['lastActionSuccess']:
                ret_msg = f"Picked up {self.readable_id(obj_id)}."
                log.info('      [pick] PickupObject -> ok')

        return ret_msg

    def put(self, receptacle_name, target_obj_id=None):
        # assume the agent always put the object currently holding
        ret_msg = ''

        if len(self.last_event.metadata['inventoryObjects']) == 0:
            ret_msg = f'Robot is not holding any object'
            return ret_msg
        else:
            holding_obj_id = self.last_event.metadata['inventoryObjects'][0]['objectId']

        halt = False
        last_recep_id = None
        exclude_obj_id = None
        for k in range(2):  # try closest and next closest one
            for j in range(7):  # move/look around or rotate obj
                for i in range(2):  # try inherited receptacles too (e.g., sink basin, bath basin)
                    if target_obj_id is not None:
                        # Instance-specific: use provided receptacle objectId directly
                        recep_id = target_obj_id
                    elif k == 1 and exclude_obj_id is None:
                        exclude_obj_id = last_recep_id  # previous recep id

                    if target_obj_id is None:
                        if i == 0:
                            # Prioritize open receptacles for openable containers (e.g., cabinet, fridge)
                            recep_id, _ = self.get_obj_id_from_name(receptacle_name, exclude_obj_id=exclude_obj_id, only_open_receptacles=True)
                            # If no open receptacle found, try any receptacle (will fail but gives better error message)
                            if not recep_id:
                                recep_id, _ = self.get_obj_id_from_name(receptacle_name, exclude_obj_id=exclude_obj_id)
                        else:
                            recep_id, _ = self.get_obj_id_from_name(receptacle_name, get_inherited=True, exclude_obj_id=exclude_obj_id, only_open_receptacles=True)
                            if not recep_id:
                                recep_id, _ = self.get_obj_id_from_name(receptacle_name, get_inherited=True, exclude_obj_id=exclude_obj_id)

                    if not recep_id:
                        ret_msg = f'Cannot find {receptacle_name}'
                        continue

                    log.info(f'      [put] {self.readable_id(holding_obj_id)} -> {self.readable_id(recep_id)}')

                    # look up (put action fails when a receptacle is not visible)
                    if j == 1:
                        super().step(dict(action="LookUp"))
                        super().step(dict(action="LookUp"))
                    elif j == 2:
                        super().step(dict(action="LookDown"))
                        super().step(dict(action="LookDown"))
                        super().step(dict(action="LookDown"))
                        super().step(dict(action="LookDown"))
                    elif j == 3:
                        super().step(dict(action="LookUp"))
                        super().step(dict(action="LookUp"))
                        super().step(dict(action="MoveBack"))
                    elif j == 4:
                        super().step(dict(action="MoveAhead"))
                        for r in range(4):
                            super().step(dict(action="MoveRight"))
                    elif j == 5:
                        for r in range(8):
                            super().step(dict(action="MoveLeft"))
                    elif j == 6:
                        for r in range(4):
                            super().step(dict(action="MoveRight"))
                        # AI2-THOR 5.x: RotateHand requires x, y, z parameters
                        super().step(dict(  # this somehow make putobject success in some cases
                            action="RotateHand",
                            x=40,
                            y=0,
                            z=0
                        ))

                    # AI2-THOR 5.x: PutObject takes objectId (receptacle) not receptacleObjectId
                    super().step(dict(
                        action="PutObject",
                        objectId=recep_id,
                        forceAction=True
                    ))
                    last_recep_id = recep_id

                    if not self.last_event.metadata['lastActionSuccess']:
                        log.debug(f"PutObject attempt failed: {self.last_event.metadata['errorMessage']}")
                        ret_msg = f'Putting the object on {receptacle_name} failed'
                    else:
                        log.info('      [put] PutObject ok')
                        ret_msg = f"Put {self.readable_id(holding_obj_id)} in {self.readable_id(recep_id)}."
                        halt = True
                        break
                if halt:
                    break
            if halt:
                break

        return ret_msg

    def drop(self):
        log.info('      [drop] DropHandObject')
        ret_msg = ''
        super().step(dict(
            action="DropHandObject",
            forceAction=True
        ))

        if not self.last_event.metadata['lastActionSuccess']:
            if len(self.last_event.metadata['inventoryObjects']) == 0:
                ret_msg = f'Robot is not holding any object'
            else:
                ret_msg = f"Drop action failed"

        return ret_msg

    def open(self, obj_name, target_obj_id=None):
        ret_msg = ''
        if target_obj_id is not None:
            obj_id = target_obj_id
        else:
            # Require visibility - can only interact with visible objects
            obj_id, _ = self.get_obj_id_from_name(obj_name, require_visibility=True)
        log.info(f'      [open] target={obj_name}, obj={self.readable_id(obj_id)}')

        if obj_id is None:
            ret_msg = f'Cannot find {obj_name} to open'
        else:
            for i in range(4):
                super().step(dict(
                    action="OpenObject",
                    objectId=obj_id,
                ))

                if not self.last_event.metadata['lastActionSuccess']:
                    log.debug(
                        f"OpenObject attempt {i+1}/4: {self.last_event.metadata['errorMessage']}")
                    ret_msg = f"Open action failed"

                    # move around to avoid self-collision and retry
                    if i == 0:
                        log.debug("Moving backward and trying again...")
                        super().step(dict(action="MoveBack"))
                    elif i == 1:
                        log.debug("Moving backward-right and trying again...")
                        super().step(dict(action="MoveBack"))
                        super().step(dict(action="MoveRight"))
                    elif i == 2:
                        log.debug("Moving left and trying again...")
                        super().step(dict(action="MoveLeft"))
                        super().step(dict(action="MoveLeft"))
                    # i == 3: no more retries
                else:
                    if i > 0:
                        log.info(f"      [open] OpenObject ok (retry {i+1})")
                    ret_msg = ''
                    break

            # Log final result
            if ret_msg:
                log.debug(f"OpenObject failed after all {i+1} attempts")

        return ret_msg

    def close(self, obj_name, target_obj_id=None):
        ret_msg = ''
        if target_obj_id is not None:
            obj_id = target_obj_id
        else:
            # Require visibility - can only interact with visible objects
            obj_id, _ = self.get_obj_id_from_name(obj_name, require_visibility=True)
        log.info(f'      [close] target={obj_name}, obj={self.readable_id(obj_id)}')
        if obj_id is None:
            ret_msg = f'Cannot find {obj_name} to close'
        else:
            super().step(dict(
                action="CloseObject",
                objectId=obj_id,
            ))

            if not self.last_event.metadata['lastActionSuccess']:
                ret_msg = f"Close action failed"

        return ret_msg

    def toggleon(self, obj_name, target_obj_id=None):
        ret_msg = ''
        if target_obj_id is not None:
            obj_id = target_obj_id
        else:
            # Require visibility - can only interact with visible objects
            obj_id, _ = self.get_obj_id_from_name(obj_name, only_toggleable=True, require_visibility=True)
        log.info(f'      [toggleon] target={obj_name}, obj={self.readable_id(obj_id)}')
        if obj_id is None:
            ret_msg = f'Cannot find {obj_name} to turn on'
        else:
            super().step(dict(
                action="ToggleObjectOn",
                objectId=obj_id,
            ))

            if not self.last_event.metadata['lastActionSuccess']:
                ret_msg = f"Turn on action failed"

        return ret_msg

    def toggleoff(self, obj_name, target_obj_id=None):
        ret_msg = ''
        if target_obj_id is not None:
            obj_id = target_obj_id
        else:
            # Require visibility - can only interact with visible objects
            obj_id, _ = self.get_obj_id_from_name(obj_name, only_toggleable=True, require_visibility=True)
        log.info(f'      [toggleoff] target={obj_name}, obj={self.readable_id(obj_id)}')
        if obj_id is None:
            ret_msg = f'Cannot find {obj_name} to turn off'
        else:
            super().step(dict(
                action="ToggleObjectOff",
                objectId=obj_id,
            ))

            if not self.last_event.metadata['lastActionSuccess']:
                ret_msg = f"Turn off action failed"

        return ret_msg

    def slice(self, obj_name, target_obj_id=None):
        ret_msg = ''
        if target_obj_id is not None:
            obj_id = target_obj_id
        else:
            # Require visibility - can only interact with visible objects
            obj_id, _ = self.get_obj_id_from_name(obj_name, require_visibility=True)
        log.info(f'      [slice] target={obj_name}, obj={self.readable_id(obj_id)}')
        if obj_id is None:
            ret_msg = f'Cannot find {obj_name} to slice'
        else:
            super().step(dict(
                action="SliceObject",
                objectId=obj_id,
            ))

            if not self.last_event.metadata['lastActionSuccess']:
                ret_msg = f"Slice action failed"
            else:
                # Incremental rebuild: preserve existing labels so instance IDs
                # remain stable; only new slice objects get new labels.
                self._build_object_registry(preserve_existing=True)

                # After slicing, the original objectId typically becomes non-pickupable
                # while AI2-THOR spawns new slice-piece objects of type {OrigType}Sliced.
                # Explicitly remap the label so the model can keep using the same ID.
                if obj_id in self._obj_registry:
                    label = self._obj_registry[obj_id]
                    orig_type = obj_id.split('|')[0]
                    slice_type = orig_type + 'Sliced'
                    all_objects = self.last_event.metadata['objects']
                    # Debug: log properties of the original sliced object
                    for o in all_objects:
                        if o['objectId'] == obj_id:
                            log.info(f"      [slice] original object after SliceObject: "
                                     f"isSliced={o.get('isSliced')}, pickupable={o.get('pickupable')}, "
                                     f"objectType={o.get('objectType')}")
                            break
                    # Find slice pieces: prefix-children or {Type}Sliced type objects
                    candidates = sorted(
                        (o for o in all_objects
                         if (o['objectId'].startswith(obj_id + '|')
                             or o['objectId'].split('|')[0] == slice_type)
                         and o['objectId'] != obj_id),
                        key=lambda o: o['distance']
                    )
                    log.info(f"      [slice] slice candidates for {label}: {[c['objectId'] for c in candidates[:3]]}")
                    if candidates:
                        # Prefer {OrigType}Sliced objects (e.g. BreadSliced) over
                        # other child objects (e.g. Bread_0) since tasks typically
                        # require the sliced-type variant.
                        # Slice-piece objectIds have format: Base|x|y|z|{SliceType}_{N}
                        # so the type is in the LAST segment, not the first.
                        sliced_candidates = [
                            c for c in candidates
                            if (c['objectId'].split('|')[-1].startswith(slice_type)
                                or c.get('objectType', '') == slice_type)
                        ]
                        pool = sliced_candidates if sliced_candidates else candidates
                        best = next((c for c in pool if c.get('pickupable', False)), pool[0])
                        new_oid = best['objectId']
                        del self._obj_registry[obj_id]
                        self._obj_registry_by_name.pop(label, None)
                        self._obj_registry[new_oid] = label
                        self._obj_registry_by_name[label] = new_oid
                        log.info(f"      [registry] remapped {label} to slice piece: {obj_id} → {new_oid}")

        return ret_msg
