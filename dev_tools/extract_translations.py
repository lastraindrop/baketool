#!/usr/bin/env python3
"""AST-based translation extraction, audit, and sync tool."""
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Iterable

DEFAULT_EXCLUDES = {
    ".git",
    ".venv",
    "__pycache__",
    "automation",
    "dev_tools",
    "dist",
    "reports",
    "test_cases",
}
PROPERTY_KEYWORDS = {"name", "description"}
UI_TEXT_KEYWORDS = {"text"}
OPERATOR_ID_PATTERN = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")
IDENTIFIER_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")
FILE_NAME_PATTERN = re.compile(r".+\.(py|json|blend|md|txt|toml)$", re.IGNORECASE)
VERSION_PATTERN = re.compile(r"^\d+(?:\.\d+)+$")
UPPER_IDENTIFIER_PATTERN = re.compile(r"^[A-Z0-9_]+$")
ACRONYM_TOKEN_PATTERN = re.compile(r"[A-Za-z]+")
ALLOWED_SAME_AS_SOURCE = {
    "fr_FR": {
        "Angle",
        "Animation",
        "Cage",
        "Direct",
        "Direction",
        "Distance",
        "Format",
        "Indirect",
        "Position",
        "Simple",
        "Source",
        "Standard",
        "Texel",
        "Total",
        "Transmission",
    },
}


def looks_like_internal_identifier(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if OPERATOR_ID_PATTERN.fullmatch(stripped):
        return True
    if IDENTIFIER_PATTERN.fullmatch(stripped):
        return True
    if FILE_NAME_PATTERN.fullmatch(stripped):
        return True
    if stripped.startswith(".") and stripped[1:].isalnum():
        return True
    if VERSION_PATTERN.fullmatch(stripped):
        return True
    if stripped.startswith(("BT_", "ShaderNode", "CompositorNode")):
        return True
    if ("/" in stripped or "\\" in stripped) and " " not in stripped:
        return True
    if stripped.startswith("__") and stripped.endswith("__"):
        return True
    if stripped.isupper() and "_" in stripped:
        return True
    return False


def is_human_facing_string(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if len(stripped) == 1 and stripped not in {"+", "-"}:
        return False
    return not looks_like_internal_identifier(stripped)


def looks_like_enum_identifier(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if looks_like_internal_identifier(stripped):
        return True
    return bool(UPPER_IDENTIFIER_PATTERN.fullmatch(stripped))


def needs_locale_translation(text: str) -> bool:
    stripped = text.strip()
    if not is_human_facing_string(stripped):
        return False
    if not any(ch.isalpha() for ch in stripped):
        return False

    tokens = ACRONYM_TOKEN_PATTERN.findall(stripped)
    if tokens and all(token.upper() == token and len(token) <= 4 for token in tokens):
        return False

    if len(stripped) <= 4 and stripped.upper() == stripped:
        return False

    return True


def looks_like_broken_translation(source_text: str, translated_text: str) -> bool:
    if not isinstance(translated_text, str):
        return False

    stripped = translated_text.strip()
    if not stripped:
        return False
    if "\ufffd" in stripped or "�" in stripped:
        return True
    if stripped.count("?") >= 2 and source_text.count("?") < stripped.count("?"):
        return True
    return False


def allows_same_as_source(locale: str, text: str) -> bool:
    return text.strip() in ALLOWED_SAME_AS_SOURCE.get(locale, set())


def _string_from_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


class TranslationExtractor(ast.NodeVisitor):
    """AST visitor that collects human-facing translatable strings from Python source."""

    def __init__(self):
        self.strings = set()

    def add(self, value: str | None) -> None:
        if value is None:
            return
        value = value.strip()
        if is_human_facing_string(value):
            self.strings.add(value)

    def visit_ClassDef(self, node: ast.ClassDef):
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id in {"bl_label", "bl_description", "bl_category"}
                    ):
                        self.add(_string_from_node(item.value))
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        target_names = {
            target.id for target in node.targets if isinstance(target, ast.Name)
        }
        if any("MESSAGE" in name for name in target_names):
            self._collect_message_values(node.value)
        elif any(name.isupper() for name in target_names) and isinstance(
            node.value, (ast.Dict, ast.List, ast.Tuple)
        ):
            self._collect_literal_strings(node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if isinstance(node.value, ast.Call):
            self._collect_property_call(node.value)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        self._collect_property_call(node)
        self._collect_ui_call(node)
        self.generic_visit(node)

    def _collect_property_call(self, node: ast.Call):
        attr_name = getattr(node.func, "attr", "") or getattr(node.func, "id", "")
        if not attr_name.endswith("Property"):
            return

        for keyword in node.keywords:
            if keyword.arg in PROPERTY_KEYWORDS:
                self.add(_string_from_node(keyword.value))
            elif keyword.arg == "items":
                self._collect_enum_items(keyword.value)

    def _collect_ui_call(self, node: ast.Call):
        attr_name = getattr(node.func, "attr", "") or getattr(node.func, "id", "")
        if attr_name in {"label", "operator", "menu", "prop"}:
            for keyword in node.keywords:
                if keyword.arg in UI_TEXT_KEYWORDS:
                    self.add(_string_from_node(keyword.value))
        elif attr_name == "report":
            if len(node.args) >= 2:
                self.add(_string_from_node(node.args[1]))
        elif attr_name == "pgettext":
            if node.args:
                self.add(_string_from_node(node.args[0]))
        elif attr_name == "draw_header":
            if len(node.args) >= 2:
                self.add(_string_from_node(node.args[1]))

    def _collect_message_values(self, node):
        if isinstance(node, ast.Dict):
            for value in node.values:
                self.add(_string_from_node(value))
        else:
            self._collect_literal_strings(node)

    def _collect_enum_items(self, node):
        if not isinstance(node, (ast.List, ast.Tuple)):
            return
        for item in node.elts:
            if not isinstance(item, (ast.Tuple, ast.List)):
                continue
            values = [_string_from_node(elt) for elt in item.elts[:3]]
            if len(values) >= 2:
                self.add(values[1])
            if len(values) >= 3:
                self.add(values[2])

    def _collect_literal_strings(self, node):
        if isinstance(node, ast.Dict):
            for key_node, value_node in zip(node.keys, node.values):
                key = _string_from_node(key_node)
                if key in {"name", "description", "header", "text", "label"}:
                    self._collect_literal_strings(value_node)
                elif key == "props":
                    self._collect_literal_strings(value_node)
                elif key in {
                    "defaults",
                    "extensions",
                    "depths",
                    "modes",
                    "bake_pass",
                    "cat",
                    "def_cs",
                    "def_mode",
                }:
                    continue
                elif isinstance(value_node, (ast.Dict, ast.List, ast.Tuple)):
                    self._collect_literal_strings(value_node)
            return

        if isinstance(node, (ast.List, ast.Tuple)):
            elements = list(node.elts)
            if len(elements) >= 2:
                first = _string_from_node(elements[0])
                second = _string_from_node(elements[1])
                third = _string_from_node(elements[2]) if len(elements) >= 3 else None

                if first and looks_like_enum_identifier(first) and second:
                    self.add(second)
                    if (
                        third
                        and not looks_like_enum_identifier(third)
                        and is_human_facing_string(third)
                    ):
                        self.add(third)
                    return

            for element in elements:
                self._collect_literal_strings(element)
            return

        self.add(_string_from_node(node))


def iter_python_files(source_dir: Path, excludes: Iterable[str] | None = None):
    excludes = set(excludes or DEFAULT_EXCLUDES)
    for py_file in source_dir.rglob("*.py"):
        if any(part in excludes for part in py_file.parts):
            continue
        yield py_file


def extract_strings(source_dir: Path, excludes: Iterable[str] | None = None):
    all_strings = set()
    for py_file in iter_python_files(source_dir, excludes):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue

        extractor = TranslationExtractor()
        extractor.visit(tree)
        all_strings.update(extractor.strings)

    return sorted(all_strings)


def load_translation_payload(path: Path):
    if not path.exists():
        return {"header": {}, "data": {}}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"header": {}, "data": {}}


def detect_locales(payload):
    locales = set()
    for entry in payload.get("data", {}).values():
        if isinstance(entry, dict):
            locales.update(entry.keys())
    locales.add("en_US")
    return sorted(locales)


def build_translation_entry(source_text, existing_entry, locales):
    if not isinstance(existing_entry, dict):
        existing_entry = {}

    entry = {}
    for locale in locales:
        if locale == "en_US":
            entry[locale] = existing_entry.get(locale, source_text)
        elif locale in existing_entry:
            entry[locale] = existing_entry[locale]
    return entry


def build_translation_payload(strings, locales):
    return {
        "header": {
            "author": "lastraindrop",
            "version": "1.0.0",
            "description": "BakeNexus extracted translations",
        },
        "data": {text: build_translation_entry(text, {}, locales) for text in strings},
    }


def build_audit_report(extracted_strings, existing_payload, locales):
    extracted = set(extracted_strings)
    existing_data = existing_payload.get("data", {})
    existing_keys = set(existing_data.keys())

    report = {
        "extracted_count": len(extracted),
        "existing_count": len(existing_keys),
        "missing_keys": sorted(extracted - existing_keys),
        "stale_keys": sorted(existing_keys - extracted),
        "suspicious_existing_keys": sorted(
            key for key in existing_keys if looks_like_internal_identifier(key)
        ),
        "missing_by_locale": {},
        "broken_by_locale": {},
        "untranslated_by_locale": {},
    }

    for locale in locales:
        if locale == "en_US":
            continue
        missing = sorted(
            key
            for key in extracted
            if not str(existing_data.get(key, {}).get(locale, "")).strip()
        )
        broken = sorted(
            key
            for key in extracted
            if looks_like_broken_translation(
                key, str(existing_data.get(key, {}).get(locale, ""))
            )
        )
        untranslated = sorted(
            key
            for key in extracted
            if key not in missing
            and key not in broken
            and needs_locale_translation(key)
            and not allows_same_as_source(locale, key)
            and str(existing_data.get(key, {}).get(locale, "")).strip() == key.strip()
        )
        report["missing_by_locale"][locale] = missing
        report["broken_by_locale"][locale] = broken
        report["untranslated_by_locale"][locale] = untranslated

    return report


def sync_translation_payload(
    source_dir: Path,
    translation_path: Path,
    locales=None,
    prune=False,
    excludes=None,
):
    existing_payload = load_translation_payload(translation_path)
    extracted_strings = extract_strings(source_dir, excludes=excludes)
    all_locales = sorted(set(locales or []) | set(detect_locales(existing_payload)))

    existing_data = existing_payload.get("data", {})
    target_keys = set(extracted_strings)
    if not prune:
        target_keys |= set(existing_data.keys())

    merged_data = {}
    for key in sorted(target_keys):
        if key in extracted_strings:
            merged_data[key] = build_translation_entry(
                key, existing_data.get(key, {}), all_locales
            )
        elif key in existing_data:
            merged_data[key] = existing_data[key]

    payload = {
        "header": {
            "author": existing_payload.get("header", {}).get("author", "lastraindrop"),
            "version": existing_payload.get("header", {}).get("version", "1.0.0"),
            "description": "BakeNexus translations",
        },
        "data": merged_data,
    }
    audit = build_audit_report(extracted_strings, existing_payload, all_locales)
    return payload, audit


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=4, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Extract, audit, and sync BakeNexus translation keys."
    )
    parser.add_argument("--source", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--existing",
        type=Path,
        default=Path("translations.json"),
        help="Existing translation file used for sync/audit.",
    )
    parser.add_argument("--sync", action="store_true", help="Merge into existing file.")
    parser.add_argument("--prune", action="store_true", help="Drop stale keys on sync.")
    parser.add_argument("--report", type=Path, default=None, help="Write audit JSON.")
    parser.add_argument(
        "--locales",
        nargs="*",
        default=None,
        help="Locales to ensure in synced output (for example zh_CN fr_FR).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero when missing or stale keys are found.",
    )
    parser.add_argument(
        "--print-missing",
        action="store_true",
        help="Print missing/stale keys summary to stdout.",
    )

    args = parser.parse_args()

    if args.sync:
        output_path = args.output or args.existing
        payload, audit = sync_translation_payload(
            source_dir=args.source.resolve(),
            translation_path=args.existing.resolve(),
            locales=args.locales,
            prune=args.prune,
        )
        write_json(output_path, payload)
    else:
        output_path = args.output or Path("translations_deep.json")
        extracted_strings = extract_strings(args.source.resolve())
        payload = build_translation_payload(extracted_strings, ["en_US"])
        audit = build_audit_report(extracted_strings, load_translation_payload(args.existing), ["en_US"])
        write_json(output_path, payload)

    if args.report:
        write_json(args.report, audit)

    if args.print_missing:
        print(f"Extracted keys: {audit['extracted_count']}")
        print(f"Missing keys: {len(audit['missing_keys'])}")
        print(f"Stale keys: {len(audit['stale_keys'])}")
        print(f"Suspicious existing keys: {len(audit['suspicious_existing_keys'])}")
        if "broken_by_locale" in audit:
            broken_total = sum(len(v) for v in audit["broken_by_locale"].values())
            untranslated_total = sum(
                len(v) for v in audit.get("untranslated_by_locale", {}).values()
            )
            print(f"Broken locale values: {broken_total}")
            print(f"Untranslated locale values: {untranslated_total}")

    if args.check and (
        audit["missing_keys"]
        or audit["stale_keys"]
        or any(audit.get("broken_by_locale", {}).values())
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
