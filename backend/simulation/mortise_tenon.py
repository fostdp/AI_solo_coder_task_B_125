"""
mortise_tenon - 向后兼容层

新代码请使用 joinery_simulator 模块:
    from joinery_simulator import JoinerySimulator, JoineryProperties

本模块保留原名，从 joinery_simulator 重新导出所有符号，确保不破坏现有调用方。
"""

from joinery_simulator import (
    ExperimentalSource,
    ParameterUncertainty,
    PARAMETER_VALID_RANGES,
    JoineryProperties,
    MortiseTenonProperties,
    build_joint_library,
    JoinerySimulator,
    MortiseTenonSimulator,
)

__all__ = [
    "ExperimentalSource",
    "ParameterUncertainty",
    "PARAMETER_VALID_RANGES",
    "JoineryProperties",
    "MortiseTenonProperties",
    "build_joint_library",
    "JoinerySimulator",
    "MortiseTenonSimulator",
]
