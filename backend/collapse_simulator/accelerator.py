import numpy as np

try:
    import cupy as cp
    _HAS_CUPY = True
except ImportError:
    cp = np
    _HAS_CUPY = False


def to_numpy(arr):
    if _HAS_CUPY and hasattr(arr, 'get'):
        return cp.asnumpy(arr)
    return np.asarray(arr)


def has_cupy() -> bool:
    return _HAS_CUPY


def get_xp(use_gpu: bool = None):
    if use_gpu is None:
        use_gpu = _HAS_CUPY
    return cp if use_gpu else np


from dataclasses import dataclass


@dataclass
class AcceleratorInfo:
    use_gpu: bool = False
    device_name: str = "CPU (NumPy)"
    memory_used_mb: float = 0.0
    vectorization_enabled: bool = True
    cache_hit_rate: float = 0.0
