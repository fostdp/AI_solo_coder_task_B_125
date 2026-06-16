"""
dynasty_comparison - 向后兼容层

新代码请使用 design_comparator 模块:
    from design_comparator import PagodaDesignComparator, PagodaModel

本模块保留原名，从 design_comparator 重新导出所有符号，确保不破坏现有调用方。
"""

from design_comparator import (
    PagodaUncertainty,
    PagodaModel,
    DynastyPagodaModel,
    PagodaDesignComparator,
    DynastyComparisonEngine,
    build_pagoda_models,
)

__all__ = [
    "PagodaUncertainty",
    "PagodaModel",
    "DynastyPagodaModel",
    "PagodaDesignComparator",
    "DynastyComparisonEngine",
    "build_pagoda_models",
]
