import os

path = r"e:\blender project\project\script project\Addons\baketool\test_cases\suite_negative.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_text = '        bad_path = "Z:\\\\Invalid|Path?*/Forbidden"'
new_text = """        import tempfile
        import shutil
        tmp_dir = tempfile.mkdtemp()
        blocker_file = os.path.join(tmp_dir, "blocker.txt")
        with open(blocker_file, "w") as f:
            f.write("blocker")
        try:
            bad_path = os.path.join(blocker_file, "Forbidden")"""

if old_text in content:
    content = content.replace(old_text, new_text)
    # Also update the assertion message
    content = content.replace('returned None for invalid path', 'returned None for blocked path')
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Success")
else:
    print("Not found")
    # Debug: print a slice
    start = content.find('bad_path =')
    if start != -1:
        print(f"Found something similar: {repr(content[start:start+50])}")
