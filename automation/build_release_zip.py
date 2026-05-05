"""Build a clean Blender add-on ZIP for release distribution.

The working tree may contain local-only folders such as `.venv/`, `test_output/`,
or legacy reference docs. This script packages only the runtime files that belong
in the shipped add-on.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib


ROOT_FILES = [
    "__init__.py",
    "blender_manifest.toml",
    "constants.py",
    "ops.py",
    "preset_handler.py",
    "property.py",
    "state_manager.py",
    "translations.py",
    "translations.json",
    "ui.py",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
]

RECURSIVE_DIRS = {
    "core": "*.py",
    "test_cases": "*.py",
}

AUTOMATION_FILES = [
    "automation/__init__.py",
    "automation/cli_runner.py",
    "automation/headless_bake.py",
]

DOC_FILES = [
    "docs/USER_MANUAL.md",
    "docs/ROADMAP.md",
    "docs/RELEASE_CHECKLIST.md",
    "docs/task.md",
    "docs/dev/DEVELOPER_GUIDE.md",
    "docs/dev/AUTOMATION_REFERENCE.md",
    "docs/dev/ECOSYSTEM_GUIDE.md",
    "docs/dev/STANDARDIZATION_GUIDE.md",
]


def load_manifest(addon_root: Path) -> dict:
    manifest_path = addon_root / "blender_manifest.toml"
    with manifest_path.open("rb") as handle:
        return tomllib.load(handle)


def collect_files(addon_root: Path) -> list[Path]:
    missing = [
        path
        for path in ROOT_FILES + DOC_FILES + AUTOMATION_FILES
        if not (addon_root / path).exists()
    ]
    if missing:
        missing_list = ", ".join(missing)
        raise FileNotFoundError(f"Required release files are missing: {missing_list}")

    files = [addon_root / path for path in ROOT_FILES]
    files.extend(addon_root / path for path in DOC_FILES)
    files.extend(addon_root / path for path in AUTOMATION_FILES)

    for folder, pattern in RECURSIVE_DIRS.items():
        files.extend(
            path
            for path in sorted((addon_root / folder).rglob(pattern))
            if "__pycache__" not in path.parts
        )

    unique_files = []
    seen = set()
    for path in files:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_files.append(path)

    return unique_files


def build_zip(addon_root: Path, output_path: Path, addon_dir_name: str | None = None) -> tuple[int, Path]:
    if addon_dir_name is None:
        addon_dir_name = addon_root.name
    files = collect_files(addon_root)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in files:
            relative = file_path.relative_to(addon_root)
            archive_name = Path(addon_dir_name) / relative
            archive.write(file_path, archive_name.as_posix())

    return len(files), output_path


def main() -> int:
    addon_root = Path(__file__).resolve().parent.parent
    manifest = load_manifest(addon_root)
    addon_id = manifest.get("id", addon_root.name)
    version = manifest.get("version", "0.0.0")

    parser = argparse.ArgumentParser(description="Build a clean BakeNexus release ZIP.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output path for the ZIP file.",
    )
    args = parser.parse_args()

    default_output = addon_root / "dist" / f"{addon_id}-{version}.zip"
    output_path = args.output if args.output else default_output

    try:
        file_count, zip_path = build_zip(
            addon_root, output_path, addon_dir_name=addon_root.name
        )
    except Exception as exc:
        print(f"Release packaging failed: {exc}", file=sys.stderr)
        return 1

    print(f"Created {zip_path} with {file_count} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
