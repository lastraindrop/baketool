import bpy
import json
import logging
import os
from mathutils import Vector, Color, Matrix, Quaternion
from bpy.app.handlers import persistent
from .constants import PRESET_DEFAULT_EXCLUDE, PRESET_MIGRATION_MAP

logger = logging.getLogger(__name__)


class PropertyIO:
    """
    Generic Blender property serialization and deserialization tool.
    Supports recursive processing of PropertyGroup, CollectionProperty, PointerProperty.
    Automatically filters Blender IDs (Object, Material, Image) for safe preset saving.
    Built-in migration logic for supporting legacy property mapping.
    """

    def __init__(self, exclude_props=None, custom_filter=None):
        """
        :param exclude_props: Set of property names to exclude from export.
        :param custom_filter: Custom filtering function (callable), signature func(prop_group, key) -> bool.
        """
        self.exclude_props = PRESET_DEFAULT_EXCLUDE.copy()
        if exclude_props:
            self.exclude_props.update(exclude_props)
        self.custom_filter = custom_filter

        self.stats = {
            'loaded': 0,
            'skipped_match': 0,
            'skipped_readonly': 0,
            'error': 0
        }

    def to_dict(self, prop_group):
        """Convert PropertyGroup to dictionary recursively."""
        if prop_group is None:
            return None

        data = {}

        for prop in prop_group.bl_rna.properties:
            key = prop.identifier

            if key in self.exclude_props:
                continue

            if self.custom_filter and not self.custom_filter(prop_group, key):
                continue

            try:
                value = getattr(prop_group, key)
            except (AttributeError, KeyError):
                continue

            if isinstance(prop, bpy.types.CollectionProperty):
                if value and len(value) > 0:
                    data[key] = [self.to_dict(item) for item in value]

            elif isinstance(prop, bpy.types.PointerProperty):
                if value is None:
                    continue

                if isinstance(value, bpy.types.ID):
                    continue

                if isinstance(value, bpy.types.PropertyGroup):
                    data[key] = self.to_dict(value)

            else:
                if hasattr(value, "to_list"):
                    data[key] = value.to_list()
                elif hasattr(value, "to_tuple"):
                    data[key] = value.to_tuple()
                elif hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
                    try:
                        data[key] = list(value)
                    except (TypeError, ValueError):
                        data[key] = str(value)
                else:
                    data[key] = value

        return data

    def from_dict(self, prop_group, data, clear_collection=True):
        """Write dictionary data to PropertyGroup recursively."""
        if not isinstance(data, dict):
            logger.debug(f"FromDict aborted: Input data is not a dictionary (got {type(data).__name__})")
            return

        if not data or not prop_group:
            return

        processed_data = data.copy()
        for old_key, new_path in PRESET_MIGRATION_MAP.items():
            if old_key in data:
                val = processed_data.pop(old_key)

                if isinstance(val, bool):
                    curr_val = self._get_nested_attr(prop_group, new_path)
                    if isinstance(curr_val, bool):
                        val = val or curr_val

                self._set_nested_attr(prop_group, new_path, val)

        valid_keys = set(p.identifier for p in prop_group.bl_rna.properties)

        for key, val in processed_data.items():
            if key not in valid_keys:
                self.stats['skipped_match'] += 1
                continue

            if key in self.exclude_props:
                continue

            prop_def = prop_group.bl_rna.properties[key]

            try:
                if isinstance(prop_def, bpy.types.CollectionProperty):
                    target_collection = getattr(prop_group, key)

                    if clear_collection:
                        target_collection.clear()

                    if isinstance(val, list):
                        for item_data in val:
                            new_item = target_collection.add()
                            self.from_dict(new_item, item_data, clear_collection)
                    else:
                        self.stats['error'] += 1

                elif isinstance(prop_def, bpy.types.PointerProperty):
                    target_pointer = getattr(prop_group, key)
                    if isinstance(target_pointer, bpy.types.PropertyGroup):
                        if isinstance(val, dict):
                            self.from_dict(target_pointer, val, clear_collection)
                        else:
                            self.stats['error'] += 1

                else:
                    if prop_def.is_readonly:
                        self.stats['skipped_readonly'] += 1
                        continue

                    setattr(prop_group, key, val)
                    self.stats['loaded'] += 1

            except (AttributeError, TypeError, ValueError) as e:
                self.stats['error'] += 1
                logger.debug(f"FromDict: Failed to load property '{key}' in {type(prop_group).__name__}: {e}")

    def _set_nested_attr(self, obj, path, val):
        """Set nested attribute, e.g. 'mesh_settings.samples'."""
        parts = path.split(".")
        target = obj
        for part in parts[:-1]:
            if hasattr(target, part):
                target = getattr(target, part)
            else:
                return
        try:
            setattr(target, parts[-1], val)
            self.stats['loaded'] += 1
        except (AttributeError, TypeError) as e:
            logger.debug(f"FromDict: Nested set failed '{path}': {e}")
            pass

    def _get_nested_attr(self, obj, path):
        """Get nested attribute value, e.g. 'mesh_settings.samples'."""
        parts = path.split(".")
        target = obj
        for part in parts[:-1]:
            if hasattr(target, part):
                target = getattr(target, part)
            else:
                return None
        return getattr(target, parts[-1], None)

    def report_stats(self):
        """Return loading statistics string."""
        return (f"Loaded: {self.stats['loaded']}, "
                f"Obsolete keys: {self.stats['skipped_match']}, "
                f"Read-only skipped: {self.stats['skipped_readonly']}, "
                f"Errors: {self.stats['error']}")


class AutoLoadHandler:
    """Manages automatic loading of default presets on Blender file load."""

    @staticmethod
    @persistent
    def load_default_preset(dummy):
        """Handler to load default preset on file load if enabled."""
        package_name = __package__.split(".")[0] if "." in __package__ else __package__

        try:
            prefs = bpy.context.preferences.addons[package_name].preferences
        except KeyError:
            return

        if not prefs.auto_load or not prefs.default_preset_path:
            return

        filepath = prefs.default_preset_path
        filepath = filepath.strip('"').strip("'")

        if not os.path.exists(filepath):
            return

        scene = bpy.context.scene
        if not scene:
            return

        if hasattr(scene, "BakeJobs") and len(scene.BakeJobs.jobs) == 0:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                PropertyIO().from_dict(scene.BakeJobs, data)
                logger.info(f"BakeTool: Auto-loaded default preset from {filepath}")
            except (OSError, IOError, json.JSONDecodeError) as e:
                logger.warning(f"BakeTool: Failed to auto-load preset: {e}")

    @classmethod
    def register(cls):
        if cls.load_default_preset not in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.append(cls.load_default_preset)

    @classmethod
    def unregister(cls):
        if cls.load_default_preset in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(cls.load_default_preset)