import unittest
import bpy
from .helpers import cleanup_scene, create_test_object, JobBuilder
from ..constants import BAKE_MODES, BAKE_TYPES, BASIC_FORMATS

class SuiteParameterMatrix(unittest.TestCase):
    """
    Exhaustive validation of all parameter combinations.
    Ensures that for any Mode/Type/Format, the system can generate a valid queue.
    """
    
    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("MatrixCube")

    def test_exhaustive_queue_generation(self):
        """Matrix test for [Mode] x [Type] x [Format] queue generation."""
        from ..core.engine import JobPreparer
        
        # We test a subset of formats to keep it fast, but all modes and types
        test_formats = ['PNG', 'JPEG', 'OPEN_EXR']
        
        for mode_id, _, _, _ in BAKE_MODES:
            for type_id, _, _, _ in BAKE_TYPES:
                for fmt in test_formats:
                    with self.subTest(mode=mode_id, type=type_id, format=fmt):
                        builder = JobBuilder(f"Job_{mode_id}_{type_id}")
                        builder.mode(mode_id).type(type_id).save_to("/tmp/test", format=fmt)
                        builder.add_objects(self.obj)
                        
                        if mode_id == 'SELECT_ACTIVE':
                            builder.setting.active_object = self.obj
                        
                        job = builder.build()
                        queue = JobPreparer.prepare_execution_queue(bpy.context, [job])
                        
                        # Assertions
                        self.assertGreater(len(queue), 0, f"Failed to generate queue for {mode_id}/{type_id}")
                        for step in queue:
                            self.assertIsNotNone(step.task.base_name)
                            self.assertGreater(len(step.channels), 0)
                            # Verify format propagated
                            self.assertEqual(step.job.setting.external_save_format, fmt)

    def test_naming_policy_matrix(self):
        """Verify naming consistency across all NAMING_MODES."""
        from ..core.common import get_safe_base_name
        from ..constants import NAMING_MODES
        
        mat = self.obj.data.materials[0]
        for name_mode, _, _ in NAMING_MODES:
            with self.subTest(policy=name_mode):
                builder = JobBuilder().add_objects(self.obj)
                builder.setting.name_setting = name_mode
                name = get_safe_base_name(builder.setting, self.obj, mat)
                self.assertIsNotNone(name)
                if name_mode == 'OBJECT': self.assertEqual(name, self.obj.name)
                if name_mode == 'MAT': self.assertEqual(name, mat.name)

if __name__ == '__main__':
    unittest.main()
