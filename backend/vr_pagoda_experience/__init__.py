"""
vr_pagoda_experience - 虚拟登塔VR体验独立模块

提供应县木塔虚拟登塔体验的后端计算服务，包括：
- 登塔路径与航点插值
- 风振多感官响应计算（视觉/听觉/触觉/动觉）
- 防眩晕系统(AMS)：4级舒适预设 + 运动平滑 + 晕动监测
- 用户会话管理

主要组件:
- VRPagodaExperienceService: 主服务类
- WindVibrationCalculator: 风振响应计算器
- VirtualClimbingPath: 登塔路径定义
- AntiMotionSicknessConfig: 防眩晕配置与预设
- MotionSmoother: 运动二重平滑器
- MotionSicknessMonitor: 晕动暴露监测器

用法:
    from vr_pagoda_experience import VRPagodaExperienceService

向后兼容:
    from simulation.virtual_experience import VirtualExperienceService  (仍然可用)
"""

from .anti_sickness import (
    AntiMotionSicknessConfig,
    MotionSmoother,
    MotionSicknessMonitor,
)
from .wind import WindVibrationCalculator
from .path import VirtualClimbingPath
from .service import (
    VRPagodaExperienceService,
    VirtualExperienceService,
    DEFAULT_PATH_WAYPOINTS,
    FLOOR_DESCRIPTIONS,
)

__all__ = [
    "AntiMotionSicknessConfig",
    "MotionSmoother",
    "MotionSicknessMonitor",
    "WindVibrationCalculator",
    "VirtualClimbingPath",
    "VRPagodaExperienceService",
    "VirtualExperienceService",
    "DEFAULT_PATH_WAYPOINTS",
    "FLOOR_DESCRIPTIONS",
]
