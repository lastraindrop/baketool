#!/usr/bin/env python3
"""Extract translation strings from BakeTool source code.

This script scans Python source files for strings that should be
internationalized and outputs them in Blender's translation format.
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Set


class TranslationExtractor(ast.NodeVisitor):
    """AST visitor to extract translatable strings."""

    def __init__(self):
        self.strings: Set[str] = set()

    def add(self, s: str) -> None:
        if s and len(s.strip()) > 0:
            self.strings.add(s)

    def _get_str(self, node: ast.AST) -> str:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Str):  # Python 3.7 compatibility
            return node.s
        return ""

    def visit_Call(self, node: ast.Call):
        func_name = getattr(node.func, "id", None) or getattr(
            getattr(node.func, "attr", None), "id", None
        )
        if func_name == "pgettext":
            if node.args:
                self.add(self._get_str(node.args[0]))
        if func_name == "gettext" and node.args:
            self.add(self._get_str(node.args[0]))
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        target = node.targets[0] if node.targets else None

        if isinstance(target, ast.Name):
            # bl_label, bl_description
            if target.id in {
                "bl_label",
                "bl_description",
                "bl_category",
                "bl_warning",
                "bl_info",
            }:
                self.add(self._get_str(node.value))

            # UI_MESSAGES dict
            if target.id == "UI_MESSAGES" and isinstance(node.value, ast.Dict):
                for val_node in node.value.values:
                    self.add(self._get_str(val_node))

            # Enum list items
            is_list_var = (
                "item" in target.id.lower()
                or "list" in target.id.lower()
                or target.id.isupper()
            )
            if is_list_var and isinstance(node.value, ast.List):
                self._extract_list(node.value)

        self.generic_visit(node)

    def _extract_list(self, list_node: ast.List):
        """Extract from list of tuples (Enum items)."""
        for el in list_node.elts:
            if isinstance(el, ast.Tuple) and len(el.elts) >= 3:
                idx = 1 if len(el.elts) > 1 else 0
                self.add(self._get_str(el.elts[idx]))

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Docstring
        if ast.get_docstring(node):
            self.add(ast.get_docstring(node))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        if ast.get_docstring(node):
            self.add(ast.get_docstring(node))
        self.generic_visit(node)


def find_py_files(source_dir: Path) -> List[Path]:
    """Find all Python files in source directory."""
    py_files = []
    for root, _, files in os.walk(source_dir):
        for f in files:
            if f.endswith(".py"):
                py_files.append(Path(root) / f)
    return py_files


def extract_translations(source_dir: Path, output_path: Path, mode: str = "update"):
    """Extract translatable strings from source files."""
    py_files = find_py_files(source_dir)

    # Exclude test directories
    py_files = [f for f in py_files if "test_cases" not in str(f)]

    all_strings: Set[str] = set()

    for py_file in py_files:
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(py_file))
            extractor = TranslationExtractor()
            extractor.visit(tree)
            all_strings.update(extractor.strings)
        except SyntaxError:
            pass
        except Exception:
            pass

    # Output
    if mode == "clean":
        return

    output_data = {"data": {}}

    for s in sorted(all_strings):
        output_data["data"][s] = {"en_US": s}

    with open(output_path, "w", encoding="utf-8") as f:
        import json

        json.dump(output_data, f, indent=4, ensure_ascii=False)

    print(f"Extracted {len(all_strings)} strings to {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract translation strings")
    parser.add_argument(
        "--input",
        "-i",
        default=".",
        help="Input/source directory (default: .)",
    )
    parser.add_argument(
        "--output", "-o", default="translations.json", help="Output file"
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["update", "clean"],
        default="update",
        help="Mode: update or clean",
    )

    args = parser.parse_args()

    source_dir = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    extract_translations(source_dir, output_path, args.mode)