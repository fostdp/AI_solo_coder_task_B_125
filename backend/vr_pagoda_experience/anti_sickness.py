import math
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional


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
    """二重运动平滑器：速率限制 + 指数低通滤波

    同时对位置XYZ、水平摆动sway_mm、倾角tilt_deg独立平滑，
    防止VR晕动症的核心组件。
    """

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
    """晕动暴露监测器 - 多感官冲突累积量监测与分级告警

    三级告警:
    - break_reminder: 定时提醒休息（info级）
    - motion_exposure_warning: 晃动累积量达阈值（warning级）
    - max_duration_reached: 达到最大建议时长（critical级，必须终止）
    """

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
