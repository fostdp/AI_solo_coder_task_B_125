"""
collapse_simulator - 倒塌模拟独立模块（含GPU加速与多进程Worker）

提供木塔在地震作用下的倒塌过程模拟、极限承载力评估(Pushover)、
人工地震动生成等功能。

主要组件:
- CollapseSimulator: 倒塌模拟器主类（CPU/GPU自适应）
- CollapseWorkerPool: 多进程Worker池，将FEA计算移出主线程
- CollapseState: 楼层倒塌状态数据类
- AcceleratorInfo: 加速器信息数据类
- generate_earthquake_motion: 独立的地震动生成函数

用法:
    from collapse_simulator import CollapseSimulator, CollapseWorkerPool

向后兼容:
    from simulation.collapse_simulator import CollapseSimulator  (仍然可用)
"""

from .accelerator import AcceleratorInfo, has_cupy, to_numpy, get_xp
from .state import CollapseState
from .motion import generate_earthquake_motion
from .simulator import CollapseSimulator
from .worker import (
    CollapseWorkerPool,
    get_global_worker_pool,
    shutdown_global_pool,
)

__all__ = [
    "AcceleratorInfo",
    "CollapseState",
    "CollapseSimulator",
    "CollapseWorkerPool",
    "generate_earthquake_motion",
    "has_cupy",
    "to_numpy",
    "get_xp",
    "get_global_worker_pool",
    "shutdown_global_pool",
]
