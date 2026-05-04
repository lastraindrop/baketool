import unittest
from unittest import mock
import bpy
from .helpers import cleanup_scene, create_test_object
from ..ui import BAKE_PT_BakePanel
from ..constants import UI_MESSAGES, FORMAT_SETTINGS

try:
    from ..ui import (
        draw_header,
        draw_file_path,
        draw_template_list_ops,
        draw_image_format_options,
        draw_crash_report,
    )
except ImportError:
    draw_header = None
    draw_file_path = None
    draw_template_list_ops = None
    draw_image_format_options = None
    draw_crash_report = None


class SuiteUILogic(unittest.TestCase):
    """
    Tests for UI Poll functions and display logic.
    Uses mock context where necessary.
    """

    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("UIObj")

    def tearDown(self):
        cleanup_scene()

    def test_ui_message_consistency(self):
        """Ensure all expected system feedback strings exist."""
        expected_keys = [
            'NO_JOBS', 'PREP_FAILED', 'QUICK_PREP_FAILED', 'NO_OBJECTS',
            'JOB_SKIPPED_NO_OBJS', 'JOB_SKIPPED_NO_TARGET', 'JOB_SKIPPED_NOT_IN_VIEW_LAYER', 'JOB_SKIPPED_MISSING_UV',
            'JOB_SKIPPED_NO_MESH', 'CAGE_MISSING', 'VALIDATION_SUCCESS', 'VALIDATION_ERROR',
            'B5_SYNC_NOTICE'
        ]
        for key in expected_keys:
            self.assertIn(key, UI_MESSAGES, f"UI Message key missing: {key}")

    def test_baked_image_result_attributes(self):
        """Verify the BakedImageResult property group has expected fields."""
        scene = bpy.context.scene
        res = scene.bakenexus_results.add()
        expected_attrs = [
            'name', 'filepath', 'image', 'channel_type',
            'res_x', 'res_y', 'duration', 'file_size'
        ]
        for attr in expected_attrs:
            self.assertTrue(hasattr(res, attr), f"BakedImageResult missing attribute: {attr}")

        # Cleanup the test result
        scene.bakenexus_results.remove(len(scene.bakenexus_results) - 1)

    def test_bake_operator_poll_blocks_while_baking(self):
        """Verify that the Bake Operator poll fails if a bake is already in progress."""
        from ..ops import BAKETOOL_OT_BakeOperator
        scene = bpy.context.scene
        scene.is_baking = False
        self.assertTrue(BAKETOOL_OT_BakeOperator.poll(bpy.context))

        scene.is_baking = True
        self.assertFalse(BAKETOOL_OT_BakeOperator.poll(bpy.context))
        scene.is_baking = False

    def test_manage_objects_smart_set_logic(self):
        """Verify the SMART_SET logic for managing bake objects."""
        scene = bpy.context.scene
        scene.BakeJobs.jobs.add()
        job = scene.BakeJobs.jobs[0]
        s = job.setting

        target = create_test_object("TargetObj")
        low = self.obj

        from ..core.common import manage_objects_logic
        manage_objects_logic(s, 'SMART_SET', [target, low], low)

        self.assertEqual(s.active_object, low)
        self.assertEqual(len(s.bake_objects), 1)
        self.assertEqual(s.bake_objects[0].bakeobject, target)

        # Cleanup
        bpy.data.objects.remove(target)

    def test_draw_header_no_nameerror(self):
        """Verify draw_header doesn't raise NameError for undefined row."""
        if draw_header is None:
            self.skipTest("UI draw functions not importable")
        from unittest.mock import MagicMock

        mock_layout = MagicMock()
        draw_header(mock_layout, "Test Header", "NONE")
        mock_layout.row.assert_called_once()

    def test_draw_file_path_no_nameerror(self):
        """Verify draw_file_path doesn't raise NameError for undefined row."""
        if draw_file_path is None:
            self.skipTest("UI draw functions not importable")
        from unittest.mock import MagicMock

        mock_layout = MagicMock()
        mock_setting = MagicMock()
        mock_setting.external_save_path = "/test/path"
        draw_file_path(mock_layout, mock_setting, "external_save_path", 0)
        mock_layout.row.assert_called_once()

    def test_draw_template_list_ops_no_nameerror(self):
        """Verify draw_template_list_ops doesn't raise NameError for undefined col."""
        if draw_template_list_ops is None:
            self.skipTest("UI draw functions not importable")
        from unittest.mock import MagicMock

        mock_layout = MagicMock()
        draw_template_list_ops(mock_layout, "channels")
        mock_layout.column.assert_called_once()

    def test_draw_image_format_options_uses_f_p(self):
        """Verify draw_image_format_options uses correct variable name."""
        if draw_image_format_options is None:
            self.skipTest("UI draw functions not importable")
        from unittest.mock import MagicMock

        mock_layout = MagicMock()
        mock_setting = MagicMock()
        mock_setting.external_save_format = "PNG"
        draw_image_format_options(mock_layout, mock_setting, "")
        mock_layout.row.assert_called()

    def test_draw_crash_report_accepts_json_cache(self):
        """Verify draw_crash_report handles JSON-string crash cache safely."""
        if draw_crash_report is None:
            self.skipTest("UI draw functions not importable")
        from unittest.mock import MagicMock
        import json

        mock_layout = MagicMock()
        mock_context = MagicMock()
        mock_context.scene.baketool_has_crash_record = True
        mock_context.scene.baketool_crash_data_cache = json.dumps(
            {"start_time": "2026-04-20 10:00:00", "current_step": 1, "total_steps": 2}
        )
        draw_crash_report(mock_layout, mock_context)
        mock_layout.box.assert_called()

    def test_run_dev_tests_updates_ui_from_isolated_runner(self):
        """Verify the dev test operator uses isolated execution and stores the summary."""
        from ..ops import BAKETOOL_OT_RunDevTests

        class DummyOperator:
            def report(self, *args, **kwargs):
                return None

            def _run_isolated_test_suite(self):
                return BAKETOOL_OT_RunDevTests._run_isolated_test_suite()

        with mock.patch.object(
            BAKETOOL_OT_RunDevTests,
            "_run_isolated_test_suite",
            return_value=(True, "Isolated audit: 12/12 passed, 0 fails, 0 errors, 0 skipped."),
        ):
            result = BAKETOOL_OT_RunDevTests.execute(DummyOperator(), bpy.context)

        self.assertEqual(result, {"FINISHED"})
        self.assertTrue(bpy.context.scene.test_pass)
        self.assertIn("12/12 passed", bpy.context.scene.last_test_info)


if __name__ == '__main__':
    unittest.main()
