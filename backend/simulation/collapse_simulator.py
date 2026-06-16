"""
collapse_simulator - 向后兼容层

新代码请使用 collapse_simulator 独立包:
    from collapse_simulator import CollapseSimulator, CollapseWorkerPool

本模块保留原名，从 collapse_simulator 包重新导出所有符号，确保不破坏现有调用方。
"""

from collapse_simulator import (
    AcceleratorInfo,
    CollapseState,
    CollapseSimulator,
    CollapseWorkerPool,
    generate_earthquake_motion,
    has_cupy,
    to_numpy,
    get_xp,
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
