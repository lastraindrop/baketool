import json
import os
import time
import bpy
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class BakeStateManager:
    def __init__(self):
        # 使用系统临时目录，避免插件安装目录的权限问题
        # Use system temp directory to avoid permission issues in addon dir
        self.log_dir = Path(bpy.app.tempdir)
        self.log_file = self.log_dir / "sbt_last_session.json"

    def start_session(self, total_steps, job_name):
        """开始任务，创建日志"""
        data = {
            "status": "STARTED",
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "job_name": job_name,
            "total_steps": total_steps,
            "current_step": 0,
            "current_object": "",
            "current_channel": "",
            "last_error": ""
        }
        self._write(data)

    def update_step(self, step_idx, obj_name, channel_name):
        """更新当前正在进行的步骤"""
        # 读取现有日志以保留 start_time 等信息，如果读取失败则创建新的
        data = self.read_log()
        if not data:
            data = {}
            
        data.update({
            "status": "RUNNING",
            "current_step": step_idx,
            "current_object": obj_name,
            "current_channel": channel_name,
            "update_time": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        self._write(data)

    def reset_ui_state(self, context, status="Idle"):
        """重置场景中的烘焙状态与进度条属性"""
        if not context or not hasattr(context, "scene"):
            return
            
        scene = context.scene
        scene.is_baking = False
        scene.bake_status = status
        scene.bake_progress = 0.0
        # 如果需要清理错误日志，可以在此处有选择地重置，但通常建议由用户手动清除
        # scene.bake_error_log = "" 

    def finish_session(self, context=None, status="Idle"):
        """正常结束，删除日志，并可选地重置 UI 状态"""
        if self.log_file.exists():
            try:
                os.remove(self.log_file)
            except Exception:
                pass
        
        if context:
            self.reset_ui_state(context, status)

    def log_error(self, error_msg):
        """记录错误但不删除文件"""
        data = self.read_log()
        if data:
            data["status"] = "ERROR"
            data["last_error"] = str(error_msg)
            self._write(data)

    def _write(self, data):
        try:
            if not self.log_dir.exists():
                self.log_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass # Some systems/mounts don't support fsync
        except Exception as e:
            logger.error(f"BakeTool Log Error: {e}")

    def read_log(self):
        """读取日志，用于检测崩溃"""
        if not self.log_file.exists():
            return None
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
            
    def has_crash_record(self):
        """检测是否有未完成的记录"""
        return self.log_file.exists()
