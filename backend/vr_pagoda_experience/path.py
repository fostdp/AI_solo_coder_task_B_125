import numpy as np
from typing import Optional, List
from .anti_sickness import MotionSmoother


class VirtualClimbingPath:
    """虚拟登塔路径 - 定义航点序列与位置插值

    支持在航点之间做线性插值，可叠加运动平滑器实现防眩晕效果。
    """

    def __init__(self, path_id: str, waypoints: list, floor_heights: list):
        self.path_id = path_id
        self.waypoints = waypoints
        self.floor_heights = floor_heights
        self._compute_segments()

    def _compute_segments(self):
        self.segment_lengths = []
        self.total_length = 0.0
        for i in range(len(self.waypoints) - 1):
            p1 = np.array([self.waypoints[i]["x"], self.waypoints[i]["y"], self.waypoints[i]["z"]])
            p2 = np.array([self.waypoints[i + 1]["x"], self.waypoints[i + 1]["y"], self.waypoints[i + 1]["z"]])
            length = np.linalg.norm(p2 - p1)
            self.segment_lengths.append(length)
            self.total_length += length

    def get_position_at_time(self, t: float,
                             smoother: Optional[MotionSmoother] = None) -> dict:
        if not self.waypoints:
            raw_pos = {"x": 0, "y": 0, "z": 0, "floor": 1, "waypoint_name": "", "progress": 0.0}
            if smoother:
                arr = smoother.smooth_position(np.array([0.0, 0.0, 0.0]))
                raw_pos.update(x=float(arr[0]), y=float(arr[1]), z=float(arr[2]))
            return raw_pos
        if t <= 0:
            wp = self.waypoints[0]
            raw = {"x": wp["x"], "y": wp["y"], "z": wp["z"],
                   "floor": wp.get("floor", 1),
                   "waypoint_name": wp.get("name", ""), "progress": 0.0}
            if smoother:
                arr = smoother.smooth_position(np.array([wp["x"], wp["y"], wp["z"]], dtype=float))
                raw.update(x=float(arr[0]), y=float(arr[1]), z=float(arr[2]))
            return raw
        total_time = len(self.waypoints) - 1
        if t >= total_time:
            wp = self.waypoints[-1]
            raw = {"x": wp["x"], "y": wp["y"], "z": wp["z"],
                   "floor": wp.get("floor", len(self.floor_heights)),
                   "waypoint_name": wp.get("name", ""), "progress": 1.0}
            if smoother:
                arr = smoother.smooth_position(np.array([wp["x"], wp["y"], wp["z"]], dtype=float))
                raw.update(x=float(arr[0]), y=float(arr[1]), z=float(arr[2]))
            return raw
        seg_idx = int(t)
        if seg_idx >= len(self.waypoints) - 1:
            seg_idx = len(self.waypoints) - 2
        frac = t - seg_idx
        wp1 = self.waypoints[seg_idx]
        wp2 = self.waypoints[seg_idx + 1]
        tx = wp1["x"] + (wp2["x"] - wp1["x"]) * frac
        ty = wp1["y"] + (wp2["y"] - wp1["y"]) * frac
        tz = wp1["z"] + (wp2["z"] - wp1["z"]) * frac
        if smoother:
            arr = smoother.smooth_position(np.array([tx, ty, tz], dtype=float))
            tx, ty, tz = float(arr[0]), float(arr[1]), float(arr[2])
        floor = wp1.get("floor", 1) if frac < 0.5 else wp2.get("floor", 1)
        waypoint_name = wp1.get("name", "") if frac < 0.5 else wp2.get("name", "")
        progress = t / total_time if total_time > 0 else 1.0
        return {"x": tx, "y": ty, "z": tz, "floor": floor,
                "waypoint_name": waypoint_name, "progress": progress}

    def get_floor_at_position(self, y: float) -> int:
        cumulative = 0.0
        for i, h in enumerate(self.floor_heights):
            cumulative += h
            if y <= cumulative:
                return i + 1
        return len(self.floor_heights)
