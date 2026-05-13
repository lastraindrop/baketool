
"""Blender Extensions manifest compliance tests."""
import unittest
from pathlib import Path

class SuiteExtensionValidation(unittest.TestCase):
    """
    Validates the addon's compliance with Blender 4.2+ Extensions system.
    """

    @classmethod
    def setUpClass(cls):
        try:
            import tomllib
            cls._tomllib = tomllib
        except ImportError:
            try:
                import tomli as tomllib
                cls._tomllib = tomllib
            except ImportError:
                cls._tomllib = None

    def setUp(self):
        self.addon_root = Path(__file__).resolve().parents[1]
        self.manifest_path = self.addon_root / "blender_manifest.toml"
        self.init_path = self.addon_root / "__init__.py"

    def test_manifest_file_exists(self):
        """Verify that blender_manifest.toml is present in the root."""
        self.assertTrue(self.manifest_path.exists(), "blender_manifest.toml is missing from root")

    def test_manifest_schema_compliance(self):
        """Verify that mandatory fields for Extensions are present and correct."""
        if self._tomllib is None:
            self.skipTest("tomllib not available in Blender < 4.2")

        with open(self.manifest_path, "rb") as f:
            data = self._tomllib.load(f)

        self.assertIn("schema_version", data, "Missing schema_version")

        mandatory = ["id", "name", "version", "type", "license", "blender_version_min", "maintainer"]
        for field in mandatory:
            self.assertIn(field, data, f"Missing mandatory field: {field}")

        self.assertEqual(data["id"], "bakenexus", "Package id should be 'bakenexus'")
        self.assertEqual(data["type"], "add-on", "Package type should be 'add-on'")

    def test_sync_between_manifest_and_bl_info(self):
        """Verify that version and metadata are synced between bl_info and manifest."""
        if self._tomllib is None:
            self.skipTest("tomllib not available in Blender < 4.2")

        from baketool import bl_info

        with open(self.manifest_path, "rb") as f:
            manifest = self._tomllib.load(f)

        manifest_version = tuple(int(x) for x in manifest["version"].split("."))
        self.assertEqual(bl_info["version"], manifest_version, "Version mismatch between bl_info and manifest")

        manifest_bl_min = tuple(int(x) for x in manifest["blender_version_min"].split("."))
        self.assertEqual(bl_info["blender"], manifest_bl_min, "Blender version min mismatch")

        self.assertEqual(bl_info["name"], manifest["name"], "Name mismatch")

    def test_permissions_declaration(self):
        """Verify that file permissions are declared for baking operations."""
        if self._tomllib is None:
            self.skipTest("tomllib not available in Blender < 4.2")

        with open(self.manifest_path, "rb") as f:
            data = self._tomllib.load(f)

        permissions = data.get("permissions")
        self.assertIsNotNone(permissions, "BakeNexus requires [permissions] to save textures")
        self.assertIn("files", permissions, "Missing 'files' permission for texture output")

    def test_recommended_metadata_presence(self):
        """Verify that recommended fields for better marketplace visibility are present."""
        if self._tomllib is None:
            self.skipTest("tomllib not available in Blender < 4.2")

        with open(self.manifest_path, "rb") as f:
            manifest = self._tomllib.load(f)

        recommended = ["tagline", "website", "tags", "maintainer"]
        for field in recommended:
            self.assertIn(field, manifest, f"Missing recommended field: {field}")
            self.assertTrue(manifest[field], f"Recommended field '{field}' is empty")

if __name__ == "__main__":
    unittest.main()
