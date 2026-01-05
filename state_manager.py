import json
import os
import time
import bpy
from pathlib import Path

class BakeStateManager:
    def __init__(self):
        # 优先存储在插件目录下的 logs 文件夹
        self.log_dir = Path(__file__).parent / "logs"
        self.log_file = self.log_dir / "last_session.json"
        
        # 确保目录存在，如果权限不足则回退到 Blender 临时目录
        try:
            if not self.log_dir.exists():
                self.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
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

    def finish_session(self):
        """正常结束，删除日志"""
        if self.log_file.exists():
            try:
                os.remove(self.log_file)
            except:
                pass

    def log_error(self, error_msg):
        """记录错误但不删除文件"""
        data = self.read_log()
        if data:
            data["status"] = "ERROR"
            data["last_error"] = str(error_msg)
            self._write(data)

    def _write(self, data):
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"BakeTool Log Error: {e}")

    def read_log(self):
        """读取日志，用于检测崩溃"""
        if not self.log_file.exists():
            return None
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
            
    def has_crash_record(self):
        """检测是否有未完成的记录"""
        return self.log_file.exists()
