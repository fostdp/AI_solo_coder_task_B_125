import numpy as np
from typing import Tuple
from .accelerator import get_xp, to_numpy


def generate_earthquake_motion(pga: float, duration: float,
                               time_step: float, seed: int = 42,
                               use_gpu: bool = None) -> Tuple[np.ndarray, np.ndarray]:
    """生成人工地震动（矢量化版本，支持GPU加速）

    Args:
        pga: 峰值地面加速度 (g)
        duration: 地震动持时 (秒)
        time_step: 时间步长 (秒)
        seed: 随机种子
        use_gpu: 是否使用GPU加速，None=自动检测

    Returns:
        (time_array, acceleration_array) - 均为 NumPy 数组
    """
    xp = get_xp(use_gpu)
    xp.random.seed(seed)
    n_steps = int(duration / time_step) + 1
    t = xp.linspace(0, duration, n_steps)
    freqs = xp.array([0.5, 1.0, 2.0, 3.0, 5.0, 8.0])
    amps = xp.array([0.3, 1.0, 0.8, 0.5, 0.2, 0.1])
    phases = xp.random.uniform(0, 2 * xp.pi, len(freqs))
    omega = 2 * xp.pi * freqs[:, None]
    t_bc = t[None, :]
    raw = xp.sum(amps[:, None] * xp.sin(omega * t_bc + phases[:, None]), axis=0)
    max_raw = xp.max(xp.abs(raw)) or 1.0
    g = 9.81
    accel = raw / max_raw * pga * g
    ramp_end = int(0.15 * n_steps)
    ramp_idx = xp.arange(ramp_end)
    accel[:ramp_end] *= (ramp_idx / max(ramp_end, 1))
    decay_start = int(0.65 * n_steps)
    decay_idx = xp.arange(decay_start, n_steps)
    decay = xp.exp(-3.0 * (decay_idx - decay_start) / max((n_steps - decay_start), 1))
    accel[decay_start:] *= decay
    return to_numpy(t).astype(float), to_numpy(accel).astype(float)
