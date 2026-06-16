"""
collapse_simulator.worker - 有限元计算独立Worker进程

使用多进程将倒塌模拟等CPU密集型计算移出主线程/事件循环，
避免阻塞API服务。

支持：
- 单任务同步执行（run_collapse_in_worker）
- 多任务并行提交（submit_collapse_simulation → Future）
- Pushover评估（run_capacity_in_worker）
- 批量参数扫描（submit_batch_param_sweep）

实现原理：
- 使用 concurrent.futures.ProcessPoolExecutor
- 每个Worker进程内独立创建 CollapseSimulator 实例
- 通过 pickle 序列化参数与结果
"""

import os
import sys
import numpy as np
from typing import Dict, List, Optional, Callable, Any
from concurrent.futures import ProcessPoolExecutor, Future
from dataclasses import dataclass, asdict


def _worker_run_collapse(params: Dict[str, Any]) -> Dict[str, Any]:
    """Worker进程内运行单次倒塌模拟（顶层函数，可被pickle）

    params 包含：
        - simulator_kwargs: 构造 CollapseSimulator 的参数
        - earthquake_pga, duration, time_step: 模拟参数
    """
    from .simulator import CollapseSimulator
    sim_kwargs = params.get("simulator_kwargs", {})
    sim = CollapseSimulator(**sim_kwargs)
    result = sim.run_collapse_simulation(
        earthquake_pga=params.get("earthquake_pga", 0.4),
        duration=params.get("duration", 30.0),
        time_step=params.get("time_step", 0.01),
    )
    return result


def _worker_run_capacity(params: Dict[str, Any]) -> Dict[str, Any]:
    """Worker进程内运行Pushover极限承载力评估"""
    from .simulator import CollapseSimulator
    sim_kwargs = params.get("simulator_kwargs", {})
    sim = CollapseSimulator(**sim_kwargs)
    result = sim.evaluate_ultimate_capacity(
        start_pga=params.get("start_pga", 0.05),
        end_pga=params.get("end_pga", 2.0),
        pga_step=params.get("pga_step", 0.05),
        early_stop=params.get("early_stop", True),
    )
    return result


class CollapseWorkerPool:
    """倒塌模拟Worker进程池

    用法:
        pool = CollapseWorkerPool(max_workers=4)
        future = pool.submit_collapse_simulation(0.4, 30.0, 0.01)
        result = future.result()  # 阻塞等待

        # 同步调用
        result = pool.run_collapse_in_worker(0.4, 30.0, 0.01)
    """

    def __init__(self, max_workers: int = None):
        if max_workers is None:
            max_workers = max(1, min(os.cpu_count() or 2, 4))
        self.max_workers = max_workers
        self._pool: Optional[ProcessPoolExecutor] = None
        self._stats = {
            "tasks_submitted": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
        }

    def _ensure_pool(self):
        if self._pool is None:
            self._pool = ProcessPoolExecutor(max_workers=self.max_workers)

    @property
    def stats(self) -> Dict[str, int]:
        return dict(self._stats)

    def submit_collapse_simulation(self,
                                    earthquake_pga: float,
                                    duration: float = 30.0,
                                    time_step: float = 0.01,
                                    simulator_kwargs: Dict = None) -> Future:
        """提交单次倒塌模拟任务，返回 Future 对象"""
        self._ensure_pool()
        params = {
            "simulator_kwargs": simulator_kwargs or {},
            "earthquake_pga": earthquake_pga,
            "duration": duration,
            "time_step": time_step,
        }
        self._stats["tasks_submitted"] += 1
        fut = self._pool.submit(_worker_run_collapse, params)
        fut.add_done_callback(self._on_task_done)
        return fut

    def submit_capacity_evaluation(self,
                                    start_pga: float = 0.05,
                                    end_pga: float = 2.0,
                                    pga_step: float = 0.05,
                                    early_stop: bool = True,
                                    simulator_kwargs: Dict = None) -> Future:
        """提交Pushover极限承载力评估任务"""
        self._ensure_pool()
        params = {
            "simulator_kwargs": simulator_kwargs or {},
            "start_pga": start_pga,
            "end_pga": end_pga,
            "pga_step": pga_step,
            "early_stop": early_stop,
        }
        self._stats["tasks_submitted"] += 1
        fut = self._pool.submit(_worker_run_capacity, params)
        fut.add_done_callback(self._on_task_done)
        return fut

    def submit_batch_param_sweep(self,
                                  pga_values: List[float],
                                  duration: float = 20.0,
                                  time_step: float = 0.02,
                                  simulator_kwargs: Dict = None) -> List[Future]:
        """批量提交参数扫描任务（多个PGA值并行计算）

        Args:
            pga_values: 要计算的PGA值列表
            duration: 地震动持续时间
            time_step: 时间步长
            simulator_kwargs: 模拟器构造参数

        Returns:
            Future 列表，顺序与 pga_values 对应
        """
        futures = []
        for pga in pga_values:
            fut = self.submit_collapse_simulation(
                earthquake_pga=pga,
                duration=duration,
                time_step=time_step,
                simulator_kwargs=simulator_kwargs,
            )
            futures.append(fut)
        return futures

    def run_collapse_in_worker(self,
                                earthquake_pga: float,
                                duration: float = 30.0,
                                time_step: float = 0.01,
                                simulator_kwargs: Dict = None) -> Dict:
        """同步版本：在Worker进程中运行并等待结果"""
        fut = self.submit_collapse_simulation(
            earthquake_pga, duration, time_step, simulator_kwargs
        )
        return fut.result()

    def run_capacity_in_worker(self,
                                start_pga: float = 0.05,
                                end_pga: float = 2.0,
                                pga_step: float = 0.05,
                                early_stop: bool = True,
                                simulator_kwargs: Dict = None) -> Dict:
        """同步版本：运行Pushover评估并等待结果"""
        fut = self.submit_capacity_evaluation(
            start_pga, end_pga, pga_step, early_stop, simulator_kwargs
        )
        return fut.result()

    def _on_task_done(self, fut: Future):
        try:
            fut.result()
            self._stats["tasks_completed"] += 1
        except Exception:
            self._stats["tasks_failed"] += 1

    def shutdown(self, wait: bool = True):
        if self._pool:
            self._pool.shutdown(wait=wait)
            self._pool = None

    def __enter__(self):
        self._ensure_pool()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown(wait=True)
        return False


_global_pool: Optional[CollapseWorkerPool] = None


def get_global_worker_pool(max_workers: int = None) -> CollapseWorkerPool:
    """获取全局单例Worker池（懒加载）"""
    global _global_pool
    if _global_pool is None:
        _global_pool = CollapseWorkerPool(max_workers=max_workers)
    return _global_pool


def shutdown_global_pool():
    global _global_pool
    if _global_pool:
        _global_pool.shutdown()
        _global_pool = None
