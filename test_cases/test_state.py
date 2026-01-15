import unittest
from ..state_manager import BakeStateManager

class TestStateManager(unittest.TestCase):
    """Test the BakeStateManager for logging and crash detection."""
    
    def setUp(self):
        self.mgr = BakeStateManager()
        self.mgr.finish_session()
        
    def tearDown(self):
        self.mgr.finish_session()

    def test_session_lifecycle(self):
        self.mgr.start_session(10, "Test_Job")
        self.assertTrue(self.mgr.has_crash_record())
        
        data = self.mgr.read_log()
        self.assertEqual(data['status'], 'STARTED')
        self.assertEqual(data['total_steps'], 10)
        
        self.mgr.update_step(1, "Cube", "Color")
        data = self.mgr.read_log()
        self.assertEqual(data['status'], 'RUNNING')
        self.assertEqual(data['current_step'], 1)
        
        self.mgr.finish_session()
        self.assertFalse(self.mgr.has_crash_record())

    def test_error_logging(self):
        self.mgr.start_session(5, "Error_Test")
        self.mgr.log_error("Simulated Error")
        
        data = self.mgr.read_log()
        self.assertEqual(data['status'], 'ERROR')
        self.assertEqual(data['last_error'], "Simulated Error")
        self.assertTrue(self.mgr.has_crash_record())

    def test_corrupted_log_file(self):
        """测试：日志文件损坏（非 JSON 格式）时的处理"""
        with open(self.mgr.log_file, 'w') as f:
            f.write("{ invalid json ... ")
            
        self.assertTrue(self.mgr.has_crash_record())
        data = self.mgr.read_log()
        self.assertIsNone(data)

