"""
design_comparator - 木塔设计对比独立模块

提供中日古代木塔的结构性能对比分析，包括：
- 固有频率对比
- 风振位移对比
- 耗能能力对比
- 抗震哲学对比

用法:
    from design_comparator import PagodaDesignComparator, PagodaModel

向后兼容:
    from simulation.dynasty_comparison import DynastyComparisonEngine  (仍然可用)
"""

from .models import PagodaModel, PagodaUncertainty, DynastyPagodaModel
from .engine import PagodaDesignComparator, DynastyComparisonEngine
from .pagoda_data import build_pagoda_models

__all__ = [
    "PagodaModel",
    "PagodaUncertainty",
    "DynastyPagodaModel",
    "PagodaDesignComparator",
    "DynastyComparisonEngine",
    "build_pagoda_models",
]
