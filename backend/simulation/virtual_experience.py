import numpy as np
import uuid
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class AntiMotionSicknessConfig:
    comfort_mode: str = "standard"
    fov_reduction_pct: float = 0.0
    motion_smoothing_strength: float = 0.5
    max_sway_rate_mm_per_sec: float = 300.0
    max_tilt_rate_deg_per_sec: float = 8.0
    show_fixed_reticle: bool = False
    vignetting_enabled: bool = True
    vignetting_intensity: float = 0.25
    low_pass_cutoff_hz: float = 0.8
    break_reminder_enabled: bool = True
    break_reminder_interval_min: float = 15.0
    max_session_duration_min: float = 60.0

    _COMFORT_PRESETS = {
        "comfort_max": {
            "fov_reduction_pct": 0.35,
            "motion_smoothing_strength": 0.85,
            "max_sway_rate_mm_per_sec": 80.0,
            "max_tilt_rate_deg_per_sec": 2.0,
            "show_fixed_reticle": True,
            "vignetting_enabled": True,
            "vignetting_intensity": 0.55,
            "low_pass_cutoff_hz": 0.3,
        },
        "comfort": {
            "fov_reduction_pct": 0.20,
            "motion_smoothing_strength": 0.65,
            "max_sway_rate_mm_per_sec": 160.0,
            "max_tilt_rate_deg_per_sec": 4.0,
            "show_fixed_reticle": True,
            "vignetting_enabled": True,
            "vignetting_intensity": 0.35,
            "low_pass_cutoff_hz": 0.5,
        },
        "standard": {
            "fov_reduction_pct": 0.0,
            "motion_smoothing_strength": 0.5,
            "max_sway_rate_mm_per_sec": 300.0,
            "max_tilt_rate_deg_per_sec": 8.0,
            "show_fixed_reticle": False,
            "vignetting_enabled": True,
            "vignetting_intensity": 0.25,
            "low_pass_cutoff_hz": 0.8,
        },
        "immersive": {
            "fov_reduction_pct": 0.0,
            "motion_smoothing_strength": 0.2,
            "max_sway_rate_mm_per_sec": 600.0,
            "max_tilt_rate_deg_per_sec": 15.0,
            "show_fixed_reticle": False,
            "vignetting_enabled": False,
            "vignetting_intensity": 0.0,
            "low_pass_cutoff_hz": 1.5,
        },
    }

    def apply_preset(self, preset: str) -> "AntiMotionSicknessConfig":
        preset = preset.lower()
        if preset not in self._COMFORT_PRESETS:
            preset = "standard"
        self.comfort_mode = preset
        vals = self._COMFORT_PRESETS[preset]
        for k, v in vals.items():
            setattr(self, k, v)
        return self

    def to_dict(self) -> dict:
        return {
            "comfort_mode": self.comfort_mode,
            "fov_reduction_pct": float(self.fov_reduction_pct),
            "motion_smoothing_strength": float(self.motion_smoothing_strength),
            "max_sway_rate_mm_per_sec": float(self.max_sway_rate_mm_per_sec),
            "max_tilt_rate_deg_per_sec": float(self.max_tilt_rate_deg_per_sec),
            "show_fixed_reticle": bool(self.show_fixed_reticle),
            "vignetting_enabled": bool(self.vignetting_enabled),
            "vignetting_intensity": float(self.vignetting_intensity),
            "low_pass_cutoff_hz": float(self.low_pass_cutoff_hz),
            "break_reminder_enabled": bool(self.break_reminder_enabled),
            "break_reminder_interval_min": float(self.break_reminder_interval_min),
            "max_session_duration_min": float(self.max_session_duration_min),
            "available_presets": list(self._COMFORT_PRESETS.keys()),
        }


class MotionSmoother:
    def __init__(self, alpha_pos: float = 0.7, alpha_rot: float = 0.75,
                 max_pos_rate: float = 300.0, max_rot_rate: float = 8.0, dt: float = 0.05):
        self.alpha_pos = alpha_pos
        self.alpha_rot = alpha_rot
        self.max_pos_rate = max_pos_rate
        self.max_rot_rate = max_rot_rate
        self.dt = dt
        self._smoothed_pos: Optional[np.ndarray] = None
        self._smoothed_sway_mm: float = 0.0
        self._smoothed_tilt_deg: float = 0.0

    def reset(self):
        self._smoothed_pos = None
        self._smoothed_sway_mm = 0.0
        self._smoothed_tilt_deg = 0.0

    def smooth_position(self, target_xyz: np.ndarray) -> np.ndarray:
        target = np.asarray(target_xyz, dtype=float)
        if self._smoothed_pos is None:
            self._smoothed_pos = target.copy()
            return target
        max_step = self.max_pos_rate * self.dt
        raw_diff = target - self._smoothed_pos
        raw_step = np.linalg.norm(raw_diff)
        if raw_step > max_step and raw_step > 0:
            raw_diff = raw_diff * (max_step / raw_step)
        blended = self._smoothed_pos + self.alpha_pos * raw_diff
        self._smoothed_pos = blended
        return blended

    def smooth_sway_mm(self, target_sway_mm: float) -> float:
        max_step = self.max_pos_rate * self.dt
        diff = target_sway_mm - self._smoothed_sway_mm
        if abs(diff) > max_step:
            diff = math.copysign(max_step, diff)
        self._smoothed_sway_mm += self.alpha_pos * diff
        return self._smoothed_sway_mm

    def smooth_tilt_deg(self, target_tilt_deg: float) -> float:
        max_step = self.max_rot_rate * self.dt
        diff = target_tilt_deg - self._smoothed_tilt_deg
        if abs(diff) > max_step:
            diff = math.copysign(max_step, diff)
        self._smoothed_tilt_deg += self.alpha_rot * diff
        return self._smoothed_tilt_deg


class MotionSicknessMonitor:
    def __init__(self, break_interval_min: float = 15.0,
                 max_duration_min: float = 60.0,
                 warning_threshold_sway_accum: float = 20000.0):
        self.break_interval_sec = break_interval_min * 60.0
        self.max_duration_sec = max_duration_min * 60.0
        self.warning_threshold = warning_threshold_sway_accum
        self.session_start_time: Optional[float] = None
        self.elapsed_sec: float = 0.0
        self.last_break_at: float = 0.0
        self.cumulative_sway_mm_sec: float = 0.0
        self.warnings_issued: List[dict] = []

    def start_session(self, t0: float = 0.0):
        self.session_start_time = t0
        self.elapsed_sec = 0.0
        self.last_break_at = 0.0
        self.cumulative_sway_mm_sec = 0.0
        self.warnings_issued = []

    def update(self, dt_sec: float, current_sway_mm: float,
               current_tilt_deg: float) -> dict:
        self.elapsed_sec += dt_sec
        self.cumulative_sway_mm_sec += abs(current_sway_mm) * dt_sec

        alerts = []
        status = "normal"

        if self.break_interval_sec > 0:
            next_break = self.last_break_at + self.break_interval_sec
            if self.elapsed_sec >= next_break:
                alerts.append({
                    "type": "break_reminder",
                    "severity": "info",
                    "message": f"已连续体验{self.elapsed_sec/60:.0f}分钟，建议休息5分钟并远眺",
                    "suggested_break_min": 5,
                })
                self.last_break_at = self.elapsed_sec

        if self.cumulative_sway_mm_sec >= self.warning_threshold:
            alerts.append({
                "type": "motion_exposure_warning",
                "severity": "warning",
                "message": "体感晃动量已达建议阈值，建议切换至舒适模式或暂停",
                "cumulative_sway_mm_sec": float(self.cumulative_sway_mm_sec),
                "recommended_mode": "comfort",
            })
            self.cumulative_sway_mm_sec = 0.0

        if self.max_duration_sec > 0 and self.elapsed_sec >= self.max_duration_sec:
            alerts.append({
                "type": "max_duration_reached",
                "severity": "critical",
                "message": f"已达最大建议体验时长({self.max_duration_sec/60:.0f}分钟)，请结束体验",
                "max_duration_min": float(self.max_duration_sec / 60.0),
            })
            status = "must_terminate"

        if alerts:
            for a in alerts:
                a["elapsed_minutes"] = float(self.elapsed_sec / 60.0)
                self.warnings_issued.append(a)

        return {
            "status": status,
            "elapsed_minutes": float(self.elapsed_sec / 60.0),
            "cumulative_sway_mm_sec": float(self.cumulative_sway_mm_sec),
            "alerts": alerts,
            "total_warnings_issued": len(self.warnings_issued),
        }


class WindVibrationCalculator:
    def __init__(self, floor_heights=None, base_diameter=30.27,
                 damping_ratio=0.05, natural_frequency=0.42):
        self.floor_heights = floor_heights or [6.59, 5.49, 4.99, 4.59, 4.09]
        self.base_diameter = base_diameter
        self.damping_ratio = damping_ratio
        self.natural_frequency = natural_frequency
        self.E = 10.0e9
        self.wall_ratio = 0.15
        self.Cd = 1.2
        self.I10 = 0.14
        D = base_diameter
        d = D * (1 - 2 * self.wall_ratio)
        self.I_section = np.pi / 64 * (D ** 4 - d ** 4)
        self.EI = self.E * self.I_section

    def compute_wind_response(self, wind_speed: float, height: float, floor: int,
                              ams_config: Optional[AntiMotionSicknessConfig] = None,
                              smoother: Optional[MotionSmoother] = None) -> dict:
        height_factor = (height / 10) ** 0.16 if height > 0 else 0.0
        Cd_factor = self.Cd
        mean_wind_pressure = 0.5 * 1.225 * 1.2 * Cd_factor * wind_speed ** 2
        wind_force = mean_wind_pressure * self.base_diameter * height * height_factor
        if self.EI > 0 and height > 0:
            x_mean = wind_force * height ** 3 / (3 * self.EI)
        else:
            x_mean = 0.0
        Iu = 0.14 * self.I10
        gu = 3.0
        x_dynamic = x_mean * (2 * gu / Iu) if Iu > 0 else 0.0
        x_total = x_mean + x_dynamic
        f = self.natural_frequency
        omega = 2 * np.pi * f
        acceleration_x = omega ** 2 * x_dynamic
        cross_wind_ratio = 0.35
        displacement_x_mm_raw = x_total * 1000
        displacement_y_mm_raw = x_total * cross_wind_ratio * 1000
        acceleration_y = acceleration_x * cross_wind_ratio

        max_rate = 300.0
        if ams_config:
            max_rate = ams_config.max_sway_rate_mm_per_sec
        if smoother:
            smoother.max_pos_rate = max_rate
            displacement_x_mm = smoother.smooth_sway_mm(displacement_x_mm_raw)
            displacement_y_mm = smoother.smooth_sway_mm(displacement_y_mm_raw)
        else:
            displacement_x_mm = displacement_x_mm_raw
            displacement_y_mm = displacement_y_mm_raw

        accel_eff = omega ** 2 * (displacement_x_mm / 1000)
        if accel_eff < 0.05:
            comfort_level = "无感"
        elif accel_eff < 0.15:
            comfort_level = "有感"
        elif accel_eff < 0.30:
            comfort_level = "不适"
        else:
            comfort_level = "难以忍受"
        perception_map = {
            "无感": "几乎感觉不到任何晃动，建筑稳固如常",
            "有感": "轻微晃动，可感知建筑在风中微微摇曳，类似于站在缓慢摆动的吊桥上",
            "不适": "明显晃动，身体需要调整重心保持平衡，物品可能发生位移，类似于船在中等波浪中",
            "难以忍受": "剧烈晃动，站立困难，必须抓紧固定物，有强烈的晕眩感，类似于强烈地震"
        }
        perception_description = perception_map[comfort_level]
        return {
            "height": height,
            "wind_speed": wind_speed,
            "height_factor": height_factor,
            "displacement_x_mm": float(displacement_x_mm),
            "displacement_y_mm": float(displacement_y_mm),
            "displacement_raw_x_mm": float(displacement_x_mm_raw),
            "acceleration_x": float(accel_eff),
            "acceleration_y": float(acceleration_y),
            "comfort_level": comfort_level,
            "perception_description": perception_description,
            "smoothing_applied": smoother is not None,
        }

    def compute_sensory_data(self, floor: int, wind_speed: float,
                             earthquake_pga: float = 0.0,
                             ams_config: Optional[AntiMotionSicknessConfig] = None,
                             smoother: Optional[MotionSmoother] = None) -> dict:
        height = sum(self.floor_heights[:floor]) if floor <= len(self.floor_heights) else sum(self.floor_heights)
        wind_response = self.compute_wind_response(wind_speed, height, floor, ams_config, smoother)
        sway_amplitude_mm = wind_response["displacement_x_mm"]
        if sway_amplitude_mm < 1:
            visual_desc = "建筑稳固，无明显可见晃动"
        elif sway_amplitude_mm < 5:
            visual_desc = "轻微晃动，仔细观察可察觉屋檐微微颤动"
        elif sway_amplitude_mm < 20:
            visual_desc = "可见晃动，悬挂物缓慢摆动，窗框发出轻微摩擦声"
        else:
            visual_desc = "明显晃动，远处景物相对移动，立柱与地面连接处可见位移"
        wind_noise_db = 20 + 30 * np.log10(wind_speed + 0.1) + 10 * (height / 50)
        wind_noise_db = float(max(0.0, min(120.0, wind_noise_db)))
        if wind_noise_db < 40:
            auditory_desc = "安静，仅可闻微风拂过屋檐的细声"
        elif wind_noise_db < 55:
            auditory_desc = "风声轻柔，如同低语，可闻门窗轻微振动"
        elif wind_noise_db < 70:
            auditory_desc = "风声明显，呼啸而过，木构件发出吱嘎声"
        else:
            auditory_desc = "风声咆哮，震耳欲聋，结构构件发出强烈响声"
        vibration_level = wind_response["acceleration_x"] + earthquake_pga * 9.81
        temperature = 15.0 - 0.6 * (height / 10)
        humidity = 60.0 + 5.0 * np.sin(height / 20)
        raw_tilt = (np.degrees(np.arctan(wind_response["displacement_x_mm"] / (1000 * height)))
                    if height > 0 else 0.0) + earthquake_pga * 2.0
        max_tilt_rate = 8.0
        if ams_config:
            max_tilt_rate = ams_config.max_tilt_rate_deg_per_sec
        if smoother:
            smoother.max_rot_rate = max_tilt_rate
            floor_tilt_degrees = smoother.smooth_tilt_deg(float(raw_tilt))
        else:
            floor_tilt_degrees = float(raw_tilt)
        stair_slope = 38.0 if floor < len(self.floor_heights) else 0.0
        handrail_force = wind_response["acceleration_x"] * 70 * 0.3

        visual_overrides = {}
        if ams_config:
            visual_overrides = {
                "fov_reduction_pct": float(ams_config.fov_reduction_pct),
                "effective_fov_degrees": float(90.0 * (1.0 - ams_config.fov_reduction_pct)),
                "vignetting_enabled": bool(ams_config.vignetting_enabled),
                "vignetting_intensity": float(ams_config.vignetting_intensity),
                "fixed_reticle_visible": bool(ams_config.show_fixed_reticle),
                "reticle_style": "crosshair_dot" if ams_config.show_fixed_reticle else "none",
            }
        return {
            "visual": {
                "sway_amplitude_mm": float(sway_amplitude_mm),
                "sway_magnitude_mm": float(sway_amplitude_mm),
                "description": visual_desc,
                **visual_overrides,
            },
            "auditory": {
                "wind_noise_db": float(wind_noise_db),
                "noise_level_db": float(wind_noise_db),
                "description": auditory_desc,
                "spatialized_panning": 0.0 if sway_amplitude_mm < 1 else float(
                    np.clip(sway_amplitude_mm / 20.0, -0.6, 0.6))
            },
            "tactile": {
                "vibration_level": float(vibration_level),
                "temperature": float(temperature),
                "humidity": float(humidity),
                "vibration_hz": float(self.natural_frequency),
            },
            "kinesthetic": {
                "floor_tilt_degrees": float(floor_tilt_degrees),
                "stair_slope": float(stair_slope),
                "handrail_force": float(handrail_force),
                "tilt_raw_degrees": float(raw_tilt),
                "smoothing_applied": smoother is not None,
            }
        }


class VirtualClimbingPath:
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


class VirtualExperienceService:
    DEFAULT_PATH = [
        {"x": 0.0, "y": 0.0, "z": 0.0, "floor": 1, "name": "塔基入口"},
        {"x": 5.0, "y": 0.0, "z": 5.0, "floor": 1, "name": "一层大厅"},
        {"x": 5.0, "y": 6.59, "z": 5.0, "floor": 2, "name": "一层至二层楼梯"},
        {"x": 3.0, "y": 12.08, "z": 3.0, "floor": 2, "name": "二层回廊"},
        {"x": 3.0, "y": 17.07, "z": 3.0, "floor": 3, "name": "三层暗层"},
        {"x": 2.0, "y": 22.06, "z": 2.0, "floor": 4, "name": "四层佛殿"},
        {"x": 2.0, "y": 26.65, "z": 2.0, "floor": 5, "name": "五层明层"},
        {"x": 0.0, "y": 30.74, "z": 0.0, "floor": 5, "name": "塔顶观景台"}
    ]

    def __init__(self, default_dt: float = 0.05):
        self.calculator = WindVibrationCalculator()
        self.paths = {}
        self.sessions: Dict[str, dict] = {}
        default_path = VirtualClimbingPath("default", self.DEFAULT_PATH, self.calculator.floor_heights)
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
        floor_info = {
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
            }
        }
        return floor_info.get(floor, {
            "name": "未知楼层",
            "architecture_features": "无相关描述",
            "buddha_info": "无相关描述",
            "view_description": "无相关描述"
        })
