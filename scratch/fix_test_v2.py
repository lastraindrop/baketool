import os

path = r"e:\blender project\project\script project\Addons\baketool\test_cases\suite_negative.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if 'def test_export_to_readonly_directory(self):' in line:
        new_lines.append(line)
        new_lines.append('        """Verify graceful error reporting when saving to forbidden paths."""\n')
        new_lines.append('        from ..core import image_manager\n')
        new_lines.append('        import tempfile\n')
        new_lines.append('        import shutil\n')
        new_lines.append('        img = image_manager.set_image("FixedImg", 8, 8)\n')
        new_lines.append('        tmp_dir = tempfile.mkdtemp()\n')
        new_lines.append('        blocker_file = os.path.join(tmp_dir, "blocker.txt")\n')
        new_lines.append('        with open(blocker_file, "w") as f:\n')
        new_lines.append('            f.write("blocker")\n')
        new_lines.append('        try:\n')
        new_lines.append('            bad_path = os.path.join(blocker_file, "Forbidden")\n')
        new_lines.append('            res = image_manager.save_image(img, path=bad_path)\n')
        new_lines.append('            self.assertIsNone(res, "Save should have failed and returned None for blocked path")\n')
        new_lines.append('        finally:\n')
        new_lines.append('            shutil.rmtree(tmp_dir)\n')
        skip = True
    elif skip and 'def test_context_manager_exception_restores_state(self):' in line:
        new_lines.append('\n')
        new_lines.append(line)
        skip = False
    elif not skip:
        new_lines.append(line)

with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
