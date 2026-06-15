import asyncio
import uuid
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from .finite_element_solver import PagodaFEAModel
from .load_generator import WindLoadGenerator, EarthquakeLoadGenerator
from core.models import Simulation, SimulationResult
from core.schemas import SimulationConfig


class SimulationService:
    """结构仿真服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_simulation(self, config: SimulationConfig,
                                 user_id: Optional[uuid.UUID] = None) -> Simulation:
        """创建仿真任务"""
        simulation = Simulation(
            id=uuid.uuid4(),
            simulation_type=config.simulation_type,
            config=config.model_dump(),
            status='pending',
            created_by=user_id,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(simulation)
        await self.db.commit()
        await self.db.refresh(simulation)
        return simulation

    async def run_simulation(self, simulation_id: uuid.UUID,
                              config: SimulationConfig) -> Dict[str, Any]:
        """运行仿真"""
        simulation = await self.db.execute(
            select(Simulation).where(Simulation.id == simulation_id)
        )
        simulation = simulation.scalar_one_or_none()

        if not simulation:
            raise ValueError(f"仿真任务 {simulation_id} 不存在")

        simulation.status = 'running'
        simulation.started_at = datetime.now(timezone.utc)
        await self.db.commit()

        try:
            result = await self._execute_simulation(config)
            await self._save_simulation_result(simulation_id, result)

            simulation.status = 'completed'
            simulation.completed_at = datetime.now(timezone.utc)
            await self.db.commit()

            return result

        except Exception as e:
            simulation.status = 'failed'
            simulation.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            raise e

    async def _execute_simulation(self, config: SimulationConfig) -> Dict[str, Any]:
        """执行仿真计算"""
        loop = asyncio.get_event_loop()

        model = PagodaFEAModel(config.timber_properties.model_dump())
        model.build_model()
        model.compute_modal_analysis(n_modes=10)

        floor_heights = model.floor_heights
        floor_diameters = model.floor_diameters
        projected_areas = np.pi * (floor_diameters / 2) ** 2 * 0.6

        if config.simulation_type == 'wind':
            wind_gen = WindLoadGenerator(
                wind_speed=config.load_params.wind_speed or 20.0
            )
            loads, t = await loop.run_in_executor(
                None,
                wind_gen.generate_distributed_wind_loads,
                floor_heights,
                config.load_params.duration,
                config.load_params.time_step,
                1.3,
                projected_areas
            )

            node_loads = {}
            for floor_idx, force in loads.items():
                for col_idx in range(model.columns_per_floor):
                    node_id = (floor_idx + 1) * model.columns_per_floor + col_idx
                    node_loads[node_id] = force / model.columns_per_floor

        else:
            eq_gen = EarthquakeLoadGenerator(
                magnitude=config.load_params.earthquake_level or 7.0,
                peak_acceleration=0.1 * (config.load_params.earthquake_level or 7.0) / 7.0
            )
            t, a_g, v_g, d_g = await loop.run_in_executor(
                None,
                eq_gen.generate_artificial_ground_motion,
                config.load_params.duration,
                config.load_params.time_step,
                42
            )

            floor_masses = projected_areas * 0.5 * 450.0
            inertia_forces = await loop.run_in_executor(
                None,
                eq_gen.compute_inertia_forces,
                floor_masses,
                a_g
            )

            node_loads = {}
            for floor_idx in range(model.n_floors):
                for col_idx in range(model.columns_per_floor):
                    node_id = (floor_idx + 1) * model.columns_per_floor + col_idx
                    node_loads[node_id] = inertia_forces[floor_idx, :] / model.columns_per_floor

        results = await loop.run_in_executor(
            None,
            model.solve_dynamic_response,
            node_loads,
            t,
            config.damping_ratio,
            'modal'
        )

        processed_results = self._process_results(results, model.n_floors)

        return processed_results

    def _process_results(self, results: Dict, n_floors: int) -> Dict[str, Any]:
        """处理仿真结果"""
        t = results['time']

        floor_results = []
        for floor in range(1, n_floors + 1):
            disp = results['floor_displacements'][floor]
            acc = results['floor_accelerations'][floor]

            max_disp = np.max(np.sqrt(disp['x'] ** 2 + disp['y'] ** 2)) * 1000
            max_acc = np.max(np.sqrt(acc['x'] ** 2 + acc['y'] ** 2)) / 9.81

            floor_results.append({
                'floor_number': floor,
                'max_displacement_mm': float(max_disp),
                'max_acceleration_g': float(max_acc),
                'displacement_time_history': {
                    'time': t.tolist(),
                    'x_mm': (disp['x'] * 1000).tolist(),
                    'y_mm': (disp['y'] * 1000).tolist()
                },
                'acceleration_time_history': {
                    'time': t.tolist(),
                    'x_g': (acc['x'] / 9.81).tolist(),
                    'y_g': (acc['y'] / 9.81).tolist()
                }
            })

        element_stresses = results['element_stresses']
        max_stress = max([s['max_stress'] for s in element_stresses]) if element_stresses else 0

        return {
            'natural_frequencies_hz': results['natural_frequencies'].tolist(),
            'mode_shapes': results['mode_shapes'],
            'max_displacement_mm': max([f['max_displacement_mm'] for f in floor_results]),
            'max_stress_mpa': float(max_stress),
            'max_acceleration_g': max([f['max_acceleration_g'] for f in floor_results]),
            'floor_results': floor_results,
            'element_stresses': element_stresses,
            'duration_seconds': float(t[-1] - t[0]),
            'time_step': float(t[1] - t[0])
        }

    async def _save_simulation_result(self, simulation_id: uuid.UUID,
                                       result: Dict[str, Any]):
        """保存仿真结果"""
        for floor_result in result['floor_results']:
            sim_result = SimulationResult(
                id=uuid.uuid4(),
                simulation_id=simulation_id,
                floor_number=floor_result['floor_number'],
                max_displacement=floor_result['max_displacement_mm'],
                max_acceleration=floor_result['max_acceleration_g'],
                max_stress=result['max_stress_mpa'],
                natural_frequencies=result['natural_frequencies_hz'],
                time_history_data={
                    'displacement': floor_result['displacement_time_history'],
                    'acceleration': floor_result['acceleration_time_history']
                },
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(sim_result)

        await self.db.commit()

    async def get_simulation_status(self, simulation_id: uuid.UUID) -> Dict[str, Any]:
        """获取仿真状态"""
        simulation = await self.db.execute(
            select(Simulation).where(Simulation.id == simulation_id)
        )
        simulation = simulation.scalar_one_or_none()

        if not simulation:
            raise ValueError(f"仿真任务 {simulation_id} 不存在")

        results = await self.db.execute(
            select(SimulationResult).where(
                SimulationResult.simulation_id == simulation_id
            ).order_by(SimulationResult.floor_number)
        )
        results = results.scalars().all()

        return {
            'id': simulation.id,
            'status': simulation.status,
            'simulation_type': simulation.simulation_type,
            'created_at': simulation.created_at,
            'started_at': simulation.started_at,
            'completed_at': simulation.completed_at,
            'results': [
                {
                    'floor': r.floor_number,
                    'max_displacement': r.max_displacement,
                    'max_acceleration': r.max_acceleration,
                    'max_stress': r.max_stress
                }
                for r in results
            ]
        }

    async def get_simulation_result(self, simulation_id: uuid.UUID) -> Dict[str, Any]:
        """获取仿真结果详情"""
        results = await self.db.execute(
            select(SimulationResult).where(
                SimulationResult.simulation_id == simulation_id
            ).order_by(SimulationResult.floor_number)
        )
        results = results.scalars().all()

        if not results:
            raise ValueError(f"仿真结果 {simulation_id} 不存在")

        return {
            'simulation_id': simulation_id,
            'natural_frequencies': results[0].natural_frequencies,
            'floor_results': [
                {
                    'floor_number': r.floor_number,
                    'max_displacement_mm': r.max_displacement,
                    'max_acceleration_g': r.max_acceleration,
                    'max_stress_mpa': r.max_stress,
                    'time_history_data': r.time_history_data
                }
                for r in results
            ]
        }
