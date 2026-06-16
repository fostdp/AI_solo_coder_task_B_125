"""
virtual_experience - 向后兼容层

新代码请使用 vr_pagoda_experience 独立模块:
    from vr_pagoda_experience import VRPagodaExperienceService

本模块保留原名，从 vr_pagoda_experience 重新导出所有符号，确保不破坏现有调用方。
"""

from vr_pagoda_experience import (
    AntiMotionSicknessConfig,
    MotionSmoother,
    MotionSicknessMonitor,
    WindVibrationCalculator,
    VirtualClimbingPath,
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
