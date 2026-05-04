import bpy
import json
import logging
import os
from bpy.app.handlers import persistent
from .constants import PRESET_DEFAULT_EXCLUDE, PRESET_MIGRATION_MAP, SYSTEM_NAMES

logger = logging.getLogger(__name__)

ID_POINTER_MARKER = "__id_pointer__"
ID_COLLECTION_BY_TYPE = {
    "Action": "actions",
    "Armature": "armatures",
    "Brush": "brushes",
    "Camera": "cameras",
    "Collection": "collections",
    "Curve": "curves",
    "GreasePencil": "grease_pencils",
    "Image": "images",
    "Lattice": "lattices",
    "Light": "lights",
    "Material": "materials",
    "Mesh": "meshes",
    "MovieClip": "movieclips",
    "NodeTree": "node_groups",
    "Object": "objects",
    "Scene": "scenes",
    "Text": "texts",
    "Texture": "textures",
    "World": "worlds",
}
TRANSIENT_ID_NAMES = {
    SYSTEM_NAMES["TEMP_UV"],
    SYSTEM_NAMES["DUMMY_IMG"],
    SYSTEM_NAMES["PROTECTION_NODE"],
    SYSTEM_NAMES["RESULT_COLLECTION"],
    SYSTEM_NAMES["VIEWER_IMG"],
}
TRANSIENT_ID_PREFIXES = (
    SYSTEM_NAMES["ATTR_PREFIX"],
    SYSTEM_NAMES["TEMP_IMG_PREFIX"],
    "BT_Denoise_",
    "BT_Compositor_",
)


def _get_id_type_name(value):
    """Return a stable RNA identifier for a Blender ID datablock."""
    bl_rna = getattr(value, "bl_rna", None)
    if bl_rna and getattr(bl_rna, "identifier", None):
        return bl_rna.identifier
    return value.__class__.__name__


def _get_id_collection_name(id_type):
    """Map an RNA ID type name to the corresponding bpy.data collection."""
    if id_type in ID_COLLECTION_BY_TYPE:
        return ID_COLLECTION_BY_TYPE[id_type]
    return f"{id_type.lower()}s"


def _get_pointer_fixed_type_name(prop_def):
    """Read the RNA fixed_type identifier when available."""
    fixed_type = getattr(prop_def, "fixed_type", None)
    if fixed_type is None:
        return None
    return getattr(fixed_type, "identifier", None) or getattr(fixed_type, "name", None)


def _normalize_library_path(filepath):
    if not filepath:
        return ""
    return os.path.normcase(os.path.abspath(filepath))


def _is_transient_id(value):
    """Skip internal runtime datablocks from preset serialization."""
    name = getattr(value, "name_full", None) or getattr(value, "name", "")
    if not name:
        return True
    if name in TRANSIENT_ID_NAMES:
        return True
    if any(name.startswith(prefix) for prefix in TRANSIENT_ID_PREFIXES):
        return True
    if getattr(value, "source", "") == "VIEWER":
        return True
    return False


def _matches_id_reference(item, name, library_path):
    item_name = getattr(item, "name_full", None) or getattr(item, "name", None)
    if item_name != name:
        return False

    if not library_path:
        return True

    item_library = getattr(getattr(item, "library", None), "filepath", "")
    return _normalize_library_path(item_library) == _normalize_library_path(library_path)


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

                if isinstance(value, bpy.types.PropertyGroup):
                    data[key] = self.to_dict(value)
                elif isinstance(value, bpy.types.ID):
                    pointer_payload = self._serialize_id_pointer(value)
                    if pointer_payload is not None:
                        data[key] = pointer_payload

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
                    if isinstance(val, dict) and ID_POINTER_MARKER in val:
                        resolved_id = self._resolve_id_pointer(
                            val[ID_POINTER_MARKER], prop_def
                        )
                        if resolved_id is not None:
                            setattr(prop_group, key, resolved_id)
                            self.stats['loaded'] += 1
                        else:
                            self.stats['skipped_match'] += 1
                    elif isinstance(target_pointer, bpy.types.PropertyGroup):
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

    def _serialize_id_pointer(self, value):
        """Serialize Blender ID pointers by stable type/name reference."""
        if _is_transient_id(value):
            return None

        payload = {
            "id_type": _get_id_type_name(value),
            "name": getattr(value, "name_full", None) or getattr(value, "name", ""),
        }
        library = getattr(getattr(value, "library", None), "filepath", "")
        if library:
            payload["library"] = library
        return {ID_POINTER_MARKER: payload}

    def _resolve_id_pointer(self, payload, prop_def=None):
        """Resolve a serialized Blender ID pointer back to a live datablock."""
        if not isinstance(payload, dict):
            return None

        fixed_type = _get_pointer_fixed_type_name(prop_def) if prop_def else None
        id_type = fixed_type or payload.get("id_type")
        name = payload.get("name")
        library_path = payload.get("library", "")

        if not id_type or not name:
            return None

        collection_name = _get_id_collection_name(id_type)
        id_collection = getattr(bpy.data, collection_name, None)
        if id_collection is None:
            return None

        getter = getattr(id_collection, "get", None)
        if callable(getter):
            direct = getter(name)
            if direct and _matches_id_reference(direct, name, library_path):
                return direct

        for item in id_collection:
            if _matches_id_reference(item, name, library_path):
                return item

        return None

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


def load_preset_into_jobs_manager(jobs_manager, data, clear_existing=True):
    """Load either a BakeJobs snapshot or a single BakeJob preset.

    The UI exposes single-job export/import, while startup/library loading works
    at the BakeJobs level. Accept both shapes so exported presets remain reusable.
    """
    if not isinstance(data, dict) or not hasattr(jobs_manager, "jobs"):
        return False

    io = PropertyIO()

    if isinstance(data.get("jobs"), list):
        io.from_dict(jobs_manager, data, clear_collection=clear_existing)
        if jobs_manager.jobs:
            jobs_manager.job_index = min(
                max(jobs_manager.job_index, 0), len(jobs_manager.jobs) - 1
            )
        return True

    job_like_keys = {"setting", "custom_bake_channels", "name", "enabled"}
    if not any(key in data for key in job_like_keys):
        return False

    if clear_existing:
        jobs_manager.jobs.clear()

    job = jobs_manager.jobs.add()
    io.from_dict(job, data, clear_collection=clear_existing)
    jobs_manager.job_index = len(jobs_manager.jobs) - 1
    return True


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
                if load_preset_into_jobs_manager(scene.BakeJobs, data):
                    logger.info(f"BakeNexus: Auto-loaded default preset from {filepath}")
                else:
                    logger.warning(
                        f"BakeNexus: Preset at {filepath} does not match a supported schema."
                    )
            except (OSError, IOError, json.JSONDecodeError) as e:
                logger.warning(f"BakeNexus: Failed to auto-load preset: {e}")

        UpdateCrashCacheHandler.update_crash_cache()

    @classmethod
    def register(cls):
        if cls.load_default_preset not in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.append(cls.load_default_preset)

    @classmethod
    def unregister(cls):
        if cls.load_default_preset in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(cls.load_default_preset)


class UpdateCrashCacheHandler:
    """Updates cached crash record in scene properties to avoid disk I/O in UI draw."""

    @staticmethod
    @persistent
    def update_crash_cache(dummy=None):
        """Cache crash record data in scene properties on file load."""
        try:
            from .state_manager import BakeStateManager
        except ImportError:
            return

        scene = bpy.context.scene
        if not scene:
            return

        mgr = BakeStateManager()
        has_crash = mgr.has_crash_record()
        scene.baketool_has_crash_record = has_crash

        if has_crash:
            data = mgr.read_log()
            if data:
                scene.baketool_crash_data_cache = json.dumps(data)
            else:
                scene.baketool_crash_data_cache = ""
        else:
            scene.baketool_crash_data_cache = ""

    @classmethod
    def register(cls):
        if cls.update_crash_cache not in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.append(cls.update_crash_cache)

    @classmethod
    def unregister(cls):
        if cls.update_crash_cache in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(cls.update_crash_cache)
