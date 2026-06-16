import uuid
import numpy as np
from typing import Dict, Optional

from .anti_sickness import (
    AntiMotionSicknessConfig,
    MotionSmoother,
    MotionSicknessMonitor,
)
from .wind import WindVibrationCalculator
from .path import VirtualClimbingPath


DEFAULT_PATH_WAYPOINTS = [
    {"x": 0.0, "y": 0.0, "z": 0.0, "floor": 1, "name": "塔基入口"},
    {"x": 5.0, "y": 0.0, "z": 5.0, "floor": 1, "name": "一层大厅"},
    {"x": 5.0, "y": 6.59, "z": 5.0, "floor": 2, "name": "一层至二层楼梯"},
    {"x": 3.0, "y": 12.08, "z": 3.0, "floor": 2, "name": "二层回廊"},
    {"x": 3.0, "y": 17.07, "z": 3.0, "floor": 3, "name": "三层暗层"},
    {"x": 2.0, "y": 22.06, "z": 2.0, "floor": 4, "name": "四层佛殿"},
    {"x": 2.0, "y": 26.65, "z": 2.0, "floor": 5, "name": "五层明层"},
    {"x": 0.0, "y": 30.74, "z": 0.0, "floor": 5, "name": "塔顶观景台"}
]

FLOOR_DESCRIPTIONS = {
    1: {
        "name": "一层释迦佛像",
        "architecture_features": "高大内槽空间，24根立柱环绕，梁架结构宏大",
        "buddha_info": "释迦牟尼佛像端坐中央，高约11米，庄严肃穆",
        "view_description": "四周立柱排列有序，光线从门窗射入，照亮佛面"
    },
    2: {
        "name": "二层平座回廊",
        "architecture_features": "外槽围廊，平座出挑，斗拱承托",
        "buddha_info": "四周供奉小型佛像与壁画，描绘佛教故事",
        "view_description": "可远眺周边景致，凭栏而望，风光尽收眼底"
    },
    3: {
        "name": "三层暗层",
        "architecture_features": "结构加固层，斜撑密布，增强整体刚度",
        "buddha_info": "无佛像供奉，为结构功能层",
        "view_description": "内部空间狭窄昏暗，木构件交错，可感受古人匠心"
    },
    4: {
        "name": "四层佛殿",
        "architecture_features": "内槽佛像，斗拱精美，层层叠叠",
        "buddha_info": "殿内供奉佛像，四周飞天壁画，栩栩如生",
        "view_description": "斗拱结构精巧绝伦，木构之美令人叹为观止"
    },
    5: {
        "name": "五层明层",
        "architecture_features": "最高佛殿，全景视野，结构收分明显",
        "buddha_info": "顶层佛殿供奉毗卢遮那佛，光明普照",
        "view_description": "全景视野开阔，可俯瞰全城，远山近水尽收眼底"
    },
}


class VRPagodaExperienceService:
    """VR木塔虚拟登塔体验服务 - 独立模块版本

    管理用户会话、登塔路径、风振响应计算、多感官数据输出、
    以及防眩晕(AMS)系统的全链路集成。
    """

    def __init__(self, default_dt: float = 0.05):
        self.calculator = WindVibrationCalculator()
        self.paths: Dict[str, VirtualClimbingPath] = {}
        self.sessions: Dict[str, dict] = {}
        default_path = VirtualClimbingPath("default", DEFAULT_PATH_WAYPOINTS, self.calculator.floor_heights)
        self.paths["default"] = default_path
        self.default_dt = default_dt
        self._global_ams = AntiMotionSicknessConfig()

    def get_comfort_presets(self) -> dict:
        return {
            "presets": list(AntiMotionSicknessConfig._COMFORT_PRESETS.keys()),
            "current_default": self._global_ams.comfort_mode,
            "details": {
                name: AntiMotionSicknessConfig().apply_preset(name).to_dict()
                for name in AntiMotionSicknessConfig._COMFORT_PRESETS.keys()
            }
        }

    def set_session_comfort_mode(self, session_id: str, mode: str) -> dict:
        sess = self.sessions.get(session_id)
        if not sess:
            return {"error": "Session not found"}
        cfg = AntiMotionSicknessConfig()
        cfg.apply_preset(mode)
        sess["ams_config"] = cfg
        sess["motion_smoother"].reset()
        return {
            "session_id": session_id,
            "applied_mode": cfg.comfort_mode,
            "ams_config": cfg.to_dict(),
        }

    def get_session_ams_config(self, session_id: str) -> dict:
        sess = self.sessions.get(session_id)
        if not sess:
            return {"error": "Session not found"}
        return {
            "session_id": session_id,
            "ams_config": sess["ams_config"].to_dict(),
            "monitor_status": sess["monitor"].update(0.0, 0.0, 0.0),
        }

    def start_experience(self, user_id: int, path_id: str = "default",
                         comfort_mode: Optional[str] = None) -> dict:
        path = self.paths.get(path_id, self.paths["default"])
        session_id = str(uuid.uuid4())
        ams_cfg = AntiMotionSicknessConfig()
        if comfort_mode:
            ams_cfg.apply_preset(comfort_mode)
        smoother = MotionSmoother(
            alpha_pos=1.0 - ams_cfg.motion_smoothing_strength * 0.8,
            alpha_rot=1.0 - ams_cfg.motion_smoothing_strength * 0.9,
            max_pos_rate=ams_cfg.max_sway_rate_mm_per_sec,
            max_rot_rate=ams_cfg.max_tilt_rate_deg_per_sec,
            dt=self.default_dt,
        )
        monitor = MotionSicknessMonitor(
            break_interval_min=ams_cfg.break_reminder_interval_min if ams_cfg.break_reminder_enabled else 0,
            max_duration_min=ams_cfg.max_session_duration_min,
        )
        monitor.start_session(0.0)
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "path_id": path_id,
            "time_elapsed": 0.0,
            "current_position": path.get_position_at_time(0.0, smoother),
            "wind_speed": 0.0,
            "earthquake_pga": 0.0,
            "active": True,
            "ams_config": ams_cfg,
            "motion_smoother": smoother,
            "monitor": monitor,
        }
        self.sessions[session_id] = session
        return {
            "session_id": session_id,
            "user_id": user_id,
            "path_id": path_id,
            "start_position": session["current_position"],
            "total_waypoints": len(path.waypoints),
            "status": "active",
            "comfort_mode": ams_cfg.comfort_mode,
            "ams_config": ams_cfg.to_dict(),
            "anti_motion_sickness": {
                "enabled": True,
                "break_reminders": ams_cfg.break_reminder_enabled,
                "motion_smoothing": ams_cfg.motion_smoothing_strength > 0,
            }
        }

    def update_experience(self, session_id: str, time_elapsed: float, wind_speed: float,
                          earthquake_pga: float = 0.0,
                          dt_sec: Optional[float] = None) -> dict:
        session = self.sessions.get(session_id)
        if not session or not session["active"]:
            return {"error": "Invalid or inactive session"}
        prev_time = session["time_elapsed"]
        actual_dt = float(dt_sec) if dt_sec is not None else float(max(time_elapsed - prev_time, 1e-4))
        session["time_elapsed"] = time_elapsed
        session["wind_speed"] = wind_speed
        session["earthquake_pga"] = earthquake_pga
        path = self.paths.get(session["path_id"], self.paths["default"])
        smoother: MotionSmoother = session["motion_smoother"]
        ams_cfg: AntiMotionSicknessConfig = session["ams_config"]
        smoother.alpha_pos = 1.0 - ams_cfg.motion_smoothing_strength * 0.8
        smoother.alpha_rot = 1.0 - ams_cfg.motion_smoothing_strength * 0.9
        position = path.get_position_at_time(time_elapsed, smoother)
        session["current_position"] = position
        floor = position["floor"]
        height = position["y"]
        wind_response = self.calculator.compute_wind_response(wind_speed, height, floor, ams_cfg, smoother)
        sensory_data = self.calculator.compute_sensory_data(floor, wind_speed, earthquake_pga, ams_cfg, smoother)
        floor_description = self.get_floor_description(floor)
        sway = wind_response["displacement_x_mm"]
        tilt = sensory_data["kinesthetic"]["floor_tilt_degrees"]
        monitor_report = session["monitor"].update(actual_dt, sway, tilt)
        if monitor_report["status"] == "must_terminate":
            session["active"] = False
        return {
            "session_id": session_id,
            "time_elapsed": time_elapsed,
            "position": position,
            "wind_response": wind_response,
            "sensory_data": sensory_data,
            "floor_description": floor_description,
            "active": session["active"],
            "ams_status": {
                "comfort_mode": ams_cfg.comfort_mode,
                "monitor": monitor_report,
                "config_snapshot": ams_cfg.to_dict(),
            }
        }

    def get_floor_description(self, floor: int) -> dict:
        return FLOOR_DESCRIPTIONS.get(floor, {
            "name": "未知楼层",
            "architecture_features": "无相关描述",
            "buddha_info": "无相关描述",
            "view_description": "无相关描述"
        })


VirtualExperienceService = VRPagodaExperienceService
