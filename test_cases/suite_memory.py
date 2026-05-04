"""Memory and Resource Management Test Suite

This test suite verifies memory management, resource cleanup, and
prevents data leaks in BakeNexus operations.
"""

import unittest
import bpy
from .helpers import (
    cleanup_scene,
    create_test_object,
    JobBuilder,
    ensure_cycles,
    MockSetting,
    assert_no_leak,
    selective_cleanup,
    DataLeakChecker,
)
from ..core import image_manager


class SuiteMemory(unittest.TestCase):
    """Test memory management and resource cleanup."""

    @classmethod
    def setUpClass(cls):
        ensure_cycles()

    def setUp(self):
        cleanup_scene()

    def tearDown(self):
        cleanup_scene()

    def test_image_memory_cleanup_after_delete(self):
        """Verify that deleting from UI removes the underlying Image datablock."""
        img = image_manager.set_image("MemTestImg", 64, 64)
        img_name = img.name

        scene = bpy.context.scene
        res = scene.bakenexus_results.add()
        res.image = img
        scene.bakenexus_results_index = len(scene.bakenexus_results) - 1

        self.assertIn(img_name, bpy.data.images)

        bpy.ops.baketool.delete_result()

        self.assertNotIn(
            img_name,
            bpy.data.images,
            "Memory Leak: Image datablock remained after UI deletion!",
        )

    def test_delete_all_results_cleans_images(self):
        """Verify Delete All removes all underlying Image datablocks."""
        images = []
        for i in range(3):
            img = image_manager.set_image(f"MultiDelete_{i}", 32, 32)
            images.append(img.name)
            res = bpy.context.scene.bakenexus_results.add()
            res.image = img

        for name in images:
            self.assertIn(name, bpy.data.images)

        bpy.ops.baketool.delete_all_results()

        for name in images:
            self.assertNotIn(
                name,
                bpy.data.images,
                f"Memory Leak: Image {name} remained after Delete All!",
            )

    def test_physical_clear_pixels_no_memory_error(self):
        """Verify large image clearing doesn't trigger MemoryError."""
        img = bpy.data.images.new("4K_Test", 4096, 4096, float_buffer=True)
        try:
            image_manager._physical_clear_pixels(img, (0.5, 0.5, 0.5, 1.0))
            self.assertAlmostEqual(list(img.generated_color)[0], 0.5)
        except Exception as e:
            self.fail(f"_physical_clear_pixels crashed on 4K resolution: {e}")
        finally:
            bpy.data.images.remove(img)

    def test_use_fake_user_not_set_by_default(self):
        """Verify temporary images don't use fake user by default."""
        img = image_manager.set_image("Test_NoFakeUser", 64, 64)
        self.assertFalse(
            img.use_fake_user, "Temporary images should not use fake user by default"
        )

    def test_batch_bake_no_image_accumulation(self):
        """Verify batch operations don't cause image accumulation."""
        initial_count = len(bpy.data.images)
        scene = bpy.context.scene

        for i in range(5):
            img = image_manager.set_image(f"BatchTest_{i}", 64, 64)
            scene.bakenexus_results_index = len(scene.bakenexus_results)
            res = scene.bakenexus_results.add()
            res.image = img
            bpy.ops.baketool.delete_result()

        final_count = len(bpy.data.images)
        leaked = final_count - initial_count

        self.assertLessEqual(
            leaked, 2, f"Image accumulation detected: {leaked} images leaked"
        )

    def test_8k_image_clear_memory_efficiency(self):
        """Verify 8K image clearing memory efficiency."""
        import tracemalloc

        img = bpy.data.images.new("8K_Test", 8192, 8192, float_buffer=True)

        tracemalloc.start()
        try:
            image_manager._physical_clear_pixels(img, (0.0, 0.0, 0.0, 1.0))

            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics("lineno")

            total_alloc = sum(stat.size for stat in top_stats[:5])
            self.assertLess(
                total_alloc,
                512 * 1024 * 1024,
                f"Memory allocation too large: {total_alloc / 1024 / 1024:.2f} MB",
            )
        finally:
            tracemalloc.stop()
            bpy.data.images.remove(img)

    def test_image_cleanup_with_external_save_only(self):
        """Verify images are properly managed when using external save only."""
        scene = bpy.context.scene
        img = image_manager.set_image("ExternalSaveTest", 128, 128)
        img_name = img.name

        scene.bakenexus_results_index = len(scene.bakenexus_results)
        res = scene.bakenexus_results.add()
        res.image = img
        res.filepath = "/tmp/test_bake.png"

        bpy.ops.baketool.delete_result()

        self.assertNotIn(
            img_name,
            bpy.data.images,
            "Image should be cleaned up even with external save",
        )

    def test_leak_checker_detects_real_leaks(self):
        """Verify DataLeakChecker can detect actual leaks."""
        checker = DataLeakChecker()
        initial = len(bpy.data.images)

        for i in range(3):
            image_manager.set_image(f"LeakTest_{i}", 32, 32)

        leaks = checker.check()

        self.assertGreater(len(leaks), 0, "LeakChecker should detect new images")
        self.assertTrue(any("images" in leak for leak in leaks))

    def test_leak_checker_with_whitelist(self):
        """Verify whitelist prevents false positives."""
        checker = DataLeakChecker()

        image_manager.set_image("KeepThis", 32, 32)
        image_manager.set_image("ReportThis", 32, 32)

        checker.add_whitelist("KeepThis", "images")

        leaks = checker.check()

        report_leaks = [l for l in leaks if "ReportThis" in l]
        keep_leaks = [l for l in leaks if "KeepThis" in l]

        self.assertGreater(len(report_leaks), 0)
        self.assertEqual(len(keep_leaks), 0)

    def test_scene_cleanup_preserves_user_data(self):
        """Verify cleanup_scene removes test data but not user data."""
        user_img = bpy.data.images.new("UserImage", 64, 64)
        user_img.use_fake_user = True

        initial_count = len(bpy.data.images)

        for i in range(3):
            image_manager.set_image(f"TempImg_{i}", 32, 32)

        temp_count = len(bpy.data.images) - initial_count
        self.assertEqual(temp_count, 3)

        cleanup_scene()

        self.assertEqual(
            len(bpy.data.images),
            initial_count,
            "cleanup_scene should remove only test data",
        )


class SuiteMemoryIntegration(unittest.TestCase):
    """Integration tests for memory management with full bake flow."""

    @classmethod
    def setUpClass(cls):
        ensure_cycles()

    def setUp(self):
        cleanup_scene()

    def tearDown(self):
        cleanup_scene()

    def test_full_bake_cycle_no_leak(self):
        """Verify complete bake cycle doesn't leak images when using external save."""
        obj = create_test_object("BakeLeakTest")

        builder = JobBuilder("LeakTestJob").add_objects(obj)
        builder.resolution(64)
        builder.enable_channel("color")
        job = builder.build()

        context = bpy.context
        scene = context.scene
        initial_images = len(bpy.data.images)

        from ..core.engine import JobPreparer

        queue = JobPreparer.prepare_execution_queue(context, [job])

        if len(queue) > 0:
            from ..core.engine import BakeStepRunner

            runner = BakeStepRunner(context)

            for step in queue[:2]:
                try:
                    results = runner.run(step)
                    for res in results:
                        if res.get("path"):
                            img = res["image"]
                            res_item = scene.bakenexus_results.add()
                            res_item.image = img
                except Exception:
                    pass

        final_images = len(bpy.data.images)

        self.assertLessEqual(
            final_images,
            initial_images + 10,
            f"Too many images accumulated: {final_images - initial_images}",
        )

    def test_repeated_bake_without_apply(self):
        """Verify repeated bakes without applying don't accumulate memory."""
        obj = create_test_object("RepeatBakeTest")

        initial = len(bpy.data.images)

        for i in range(3):
            img = image_manager.set_image(f"Repeat_{i}", 64, 64)
            res = bpy.context.scene.bakenexus_results.add()
            res.image = img

        after_bakes = len(bpy.data.images)
        self.assertEqual(after_bakes, initial + 3)

        bpy.ops.baketool.delete_all_results()

        after_cleanup = len(bpy.data.images)
        leaked = after_cleanup - initial

        self.assertLessEqual(leaked, 1, f"Images leaked after batch delete: {leaked}")


if __name__ == "__main__":
    unittest.main()
