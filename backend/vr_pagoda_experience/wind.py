import numpy as np
from typing import Optional

from .anti_sickness import AntiMotionSicknessConfig, MotionSmoother


class WindVibrationCalculator:
    """木塔风振响应计算器 - 基于平均风+脉动风的简化模型

    计算给定高度和风速下的位移、加速度、舒适度评价，
    并与防眩晕系统(AMS)集成输出视觉/听觉/触觉/动觉多感官数据。
    """

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
