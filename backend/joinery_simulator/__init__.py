"""
joinery_simulator - 榫卯工艺力学模拟独立模块

提供古建筑木构榫卯节点的：
- 力学参数库（6类节点，实验标定）
- 循环加载滞回模拟
- 骨架曲线计算
- 刚度退化分析
- 能量耗散评估
- 参数区间校验
- 实验标定更新

用法:
    from joinery_simulator import JoinerySimulator, JoineryProperties

向后兼容:
    from simulation.mortise_tenon import MortiseTenonSimulator  (仍然可用)
"""

from .properties import (
    ExperimentalSource,
    ParameterUncertainty,
    PARAMETER_VALID_RANGES,
    JoineryProperties,
    MortiseTenonProperties,
)
from .joint_data import build_joint_library
from .simulator import JoinerySimulator, MortiseTenonSimulator

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
