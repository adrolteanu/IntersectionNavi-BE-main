import time
import platform
import psutil
import json
import hashlib
from pathlib import Path

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            "start_time": time.perf_counter(),
            "simulations": [],
            "system": {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "cpu": platform.processor(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "memory": psutil.virtual_memory().total
            }
        }

    def mark_db_fetch_start(self):
        self.db_fetch_start = time.perf_counter()

    def mark_db_fetch_end(self, payload_count):
        self.metrics["db_fetch_duration"] = time.perf_counter() - self.db_fetch_start
        self.metrics["payload_count"] = payload_count

    def mark_simulation_start(self, speed):
        self.current_sim = {"speed": speed, "start": time.perf_counter()}

    def mark_simulation_end(self):
        self.current_sim["duration"] = time.perf_counter() - self.current_sim["start"]
        self.metrics["simulations"].append(self.current_sim)

    def _get_device_hash(self):
        device_string = (
            self.metrics["system"]["platform"] +
            self.metrics["system"]["platform_version"] +
            self.metrics["system"]["cpu"] +
            str(self.metrics["system"]["cpu_count"])
        )
        return hashlib.md5(device_string.encode()).hexdigest()

    def finalize(self, output_dir="results"):
        self.metrics["total_duration"] = time.perf_counter() - self.metrics["start_time"]
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        device_hash = self._get_device_hash()
        output_path = Path(output_dir) / f"performance_{device_hash}.json"
        with open(output_path, "w") as f:
            json.dump(self.metrics, f, indent=2)
