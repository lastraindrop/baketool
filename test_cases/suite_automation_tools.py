
"""Automation tool integration tests."""
import os
import tempfile
import unittest

from ..automation import multi_version_test


class SuiteAutomationTools(unittest.TestCase):
    """Tests for CLI and cross-version automation helpers."""

    def test_load_blender_paths_merges_sources_and_dedupes(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False, encoding="utf-8"
        ) as handle:
            handle.write("D:\\B\\blender.exe\nE:\\C\\blender.exe\n")
            paths_file = handle.name

        try:
            sep = os.pathsep
            env = {
                "BLENDER_PATHS": sep.join(["C:\\A\\blender.exe", "D:\\B\\blender.exe"]),
                "BLENDER_PATHS_FILE": "",
            }
            paths = multi_version_test.load_blender_paths(
                extra_paths=["C:\\A\\blender.exe", "Z:\\Extra\\blender.exe"],
                paths_file=paths_file,
                env=env,
            )
            self.assertEqual(
                paths[:4],
                [
                    "C:\\A\\blender.exe",
                    "Z:\\Extra\\blender.exe",
                    "D:\\B\\blender.exe",
                    "E:\\C\\blender.exe",
                ],
            )
        finally:
            os.remove(paths_file)

    def test_build_cli_command_passes_suite_category_and_json(self):
        command = multi_version_test.build_cli_command(
            "X:\\Blender\\blender.exe",
            suite="preset",
            category="core",
            verification=False,
            json_output="report.json",
        )
        self.assertIn("--background", command)
        self.assertIn("--factory-startup", command)
        self.assertIn("--python", command)
        self.assertIn("--suite", command)
        self.assertIn("preset", command)
        self.assertIn("--category", command)
        self.assertIn("core", command)
        self.assertEqual(command[-2:], ["--json", "report.json"])

    def test_summarize_cli_result_prefers_json_report(self):
        # Case 1: Success scenario
        success, reason = multi_version_test.summarize_cli_result(
            0, "", {"summary": {"total": 4, "failures": 0, "errors": 0}}
        )
        self.assertTrue(success, f"Expected success but got reason='{reason}'")
        self.assertEqual(reason, "ok", f"Expected 'ok' but got '{reason}'")

        # Case 2: Failure scenario (returncode=1, failures=1)
        success, reason = multi_version_test.summarize_cli_result(
            1, "", {"summary": {"total": 4, "failures": 1, "errors": 0}}
        )
        self.assertFalse(success, f"Expected failure but got success=True, reason='{reason}'")
        self.assertEqual(reason, "test_fail", f"Expected 'test_fail' but got '{reason}'")

        # Case 3: Runner error (no parsed_report, no markers in stdout)
        success, reason = multi_version_test.summarize_cli_result(
            1, "No markers here", None
        )
        self.assertFalse(success)
        self.assertEqual(reason, "runner_error", f"Expected 'runner_error' but got '{reason}'")


if __name__ == "__main__":
    unittest.main()
