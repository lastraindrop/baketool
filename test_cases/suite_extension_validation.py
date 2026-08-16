
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

        self.assertEqual(data["type"], "add-on", "Package type should be 'add-on'")

    def test_manifest_id_matches_addon_directory(self):
        """[B-01 regression] Extension id must equal the ZIP's inner directory.

        Blender 4.2+ refuses to install a disk extension unless the manifest
        id matches the top-level folder name inside the archive. The release
        ZIP uses the repository folder name, so both must be identical.
        """
        if self._tomllib is None:
            self.skipTest("tomllib not available in Blender < 4.2")

        with open(self.manifest_path, "rb") as f:
            data = self._tomllib.load(f)

        addon_dir_name = self.addon_root.name
        self.assertEqual(
            data.get("id"),
            addon_dir_name,
            "blender_manifest.toml 'id' must match the add-on directory name "
            f"'{addon_dir_name}' or Blender 4.2+ extension install will fail",
        )

    def test_release_zip_includes_audit_dependencies(self):
        """[B-04 regression] Packaged Safety Audit must not hit import errors.

        The shipped ZIP keeps test_cases/ and automation/ so users can run the
        isolated audit. suite_localization imports ..dev_tools, so dev_tools
        must be listed in the packaging script's recursive dirs.
        """
        build_script = self.addon_root / "automation" / "build_release_zip.py"
        self.assertTrue(build_script.exists(), "build_release_zip.py missing")

        content = build_script.read_text(encoding="utf-8")
        self.assertIn(
            '"dev_tools": "*.py"',
            content,
            "build_release_zip.py no longer packages dev_tools/; the packaged "
            "Run Safety Audit will fail importing suite_localization",
        )
        self.assertTrue(
            (self.addon_root / "dev_tools" / "extract_translations.py").exists(),
            "dev_tools/extract_translations.py is required by suite_localization",
        )

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
