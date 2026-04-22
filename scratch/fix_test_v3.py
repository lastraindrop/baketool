import os

path = r"e:\blender project\project\script project\Addons\baketool\test_cases\suite_code_review.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if 'def test_manifest_version_matches_bl_info(self):' in line:
        new_lines.append(line)
        new_lines.append('        """Verify blender_manifest.toml version matches bl_info version."""\n')
        new_lines.append('        import os\n')
        new_lines.append('        from pathlib import Path\n')
        new_lines.append('        test_file = Path(__file__).resolve()\n')
        new_lines.append('        manifest_path = test_file.parent.parent / "blender_manifest.toml"\n')
        new_lines.append('        if not manifest_path.exists():\n')
        new_lines.append('            self.skipTest(f"blender_manifest.toml not found at {manifest_path}")\n')
        new_lines.append('\n')
        new_lines.append('        with open(manifest_path, "r", encoding="utf-8") as f:\n')
        new_lines.append('            content = f.read()\n')
        new_lines.append('\n')
        new_lines.append('        import re\n')
        new_lines.append('        match = re.search(r\'version\s*=\s*"(\d+)\.(\d+)\.(\d+)"\', content)\n')
        new_lines.append('        self.assertIsNotNone(match, "Version not found in manifest")\n')
        new_lines.append('        manifest_version = tuple(int(x) for x in match.groups())\n')
        new_lines.append('\n')
        new_lines.append('        from baketool import bl_info\n')
        new_lines.append('        self.assertEqual(bl_info["version"], manifest_version, "bl_info version doesn\'t match manifest")\n')
        skip = True
    elif skip and 'def test_all_test_suites_importable(self):' in line:
        new_lines.append('\n')
        new_lines.append(line)
        skip = False
    elif not skip:
        new_lines.append(line)

with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
