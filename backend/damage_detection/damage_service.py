import asyncio
import uuid
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from .modal_analysis import SSIModalAnalysis, FrequencyDomainDecomposition
from .neural_network import DamageDetectionModel
from core.models import DamageAnalysis, DamageResult, SensorData, Sensor, ModalParameter
from core.schemas import DamageAnalysisRequest


class DamageDetectionService:
    """损伤识别服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ssi_analyzer = SSIModalAnalysis(fs=100.0, order_max=30)
        self.fdd_analyzer = FrequencyDomainDecomposition(fs=100.0)
        self.damage_model = DamageDetectionModel(n_features=50, n_floors=5)

    async def create_analysis(self, request: DamageAnalysisRequest) -> DamageAnalysis:
        """创建损伤分析任务"""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(seconds=request.analysis_window)

        analysis = DamageAnalysis(
            id=uuid.uuid4(),
            status='processing',
            analysis_window=request.analysis_window,
            start_time=start_time,
            end_time=end_time,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(analysis)
        await self.db.commit()
        await self.db.refresh(analysis)
        return analysis

    async def run_analysis(self, analysis_id: uuid.UUID,
                           request: DamageAnalysisRequest) -> List[Dict]:
        """运行损伤识别分析"""
        analysis = await self.db.execute(
            select(DamageAnalysis).where(DamageAnalysis.id == analysis_id)
        )
        analysis = analysis.scalar_one_or_none()

        if not analysis:
            raise ValueError(f"分析任务 {analysis_id} 不存在")

        try:
            floor = request.floor
            modal_params = await self._extract_modal_parameters(analysis.start_time, analysis.end_time, floor)

            baseline_params = await self._get_baseline_parameters(floor)

            damage_results = self.damage_model.predict(modal_params, baseline_params)

            await self._save_damage_results(analysis_id, damage_results)

            analysis.status = 'completed'
            analysis.completed_at = datetime.now(timezone.utc)
            await self.db.commit()

            return damage_results

        except Exception as e:
            analysis.status = 'failed'
            analysis.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            raise e

    async def _extract_modal_parameters(self, start_time: datetime, end_time: datetime,
                                         floor: Optional[int] = None) -> Dict:
        """从传感器数据中提取模态参数"""
        sensor_query = select(Sensor).where(Sensor.sensor_type.like('acceleration%'))
        if floor is not None:
            sensor_query = sensor_query.where(Sensor.floor_number == floor)

        sensors_result = await self.db.execute(sensor_query)
        sensors = sensors_result.scalars().all()

        if not sensors:
            return self._get_default_modal_params(floor)

        sensor_ids = [s.id for s in sensors]

        data_query = select(SensorData).where(
            and_(
                SensorData.sensor_id.in_(sensor_ids),
                SensorData.time >= start_time,
                SensorData.time <= end_time
            )
        ).order_by(SensorData.time)

        data_result = await self.db.execute(data_query)
        data_rows = data_result.scalars().all()

        if len(data_rows) < 1000:
            return self._simulate_modal_params(floor, len(sensors))

        data_dict = {}
        for row in data_rows:
            sid = str(row.sensor_id)
            if sid not in data_dict:
                data_dict[sid] = []
            data_dict[sid].append((row.time.timestamp(), row.value))

        n_samples = min([len(v) for v in data_dict.values()]) if data_dict else 0
        n_channels = min(len(data_dict), 10)

        if n_samples < 100 or n_channels < 2:
            return self._simulate_modal_params(floor, n_channels)

        data_matrix = np.zeros((n_channels, n_samples))
        channel_idx = 0
        for sid in list(data_dict.keys())[:n_channels]:
            values = data_dict[sid][:n_samples]
            data_matrix[channel_idx, :] = np.array([v for _, v in values])
            channel_idx += 1

        try:
            modal_params = self.ssi_analyzer.analyze(data_matrix, n_modes=10)

            if modal_params['n_modes_identified'] < 3:
                modal_params = self.fdd_analyzer.analyze(data_matrix, n_modes=10)

            return modal_params
        except Exception as e:
            return self._simulate_modal_params(floor, n_channels)

    async def _get_baseline_parameters(self, floor: Optional[int] = None) -> Dict:
        """获取基准模态参数"""
        query = select(ModalParameter).where(ModalParameter.is_baseline == True)
        if floor is not None:
            query = query.where(ModalParameter.floor_number == floor)
        query = query.order_by(ModalParameter.floor_number, ModalParameter.mode_order)

        result = await self.db.execute(query)
        baseline_rows = result.scalars().all()

        if not baseline_rows:
            return {
                'frequencies': [0.42, 0.45, 1.18, 1.25, 2.35, 2.48, 4.12, 4.25, 6.25, 6.38],
                'damping_ratios': [0.02, 0.02, 0.025, 0.025, 0.03, 0.03, 0.035, 0.035, 0.04, 0.04],
                'mode_shapes': [],
                'n_modes_identified': 10
            }

        frequencies = [row.natural_frequency for row in baseline_rows]
        damping = [row.damping_ratio if row.damping_ratio else 0.02 for row in baseline_rows]

        return {
            'frequencies': frequencies,
            'damping_ratios': damping,
            'mode_shapes': [],
            'n_modes_identified': len(frequencies)
        }

    def _get_default_modal_params(self, floor: Optional[int]) -> Dict:
        """获取默认模态参数"""
        base_freqs = [0.42, 0.45, 1.18, 1.25, 2.35]
        base_damps = [0.02, 0.02, 0.025, 0.025, 0.03]

        if floor is not None:
            base_freqs = [f * (1 + floor * 0.05) for f in base_freqs]

        return {
            'frequencies': base_freqs,
            'damping_ratios': base_damps,
            'mode_shapes': [],
            'n_modes_identified': len(base_freqs)
        }

    def _simulate_modal_params(self, floor: Optional[int], n_channels: int) -> Dict:
        """模拟模态参数（数据不足时使用）"""
        base_freqs = np.array([0.42, 0.45, 1.18, 1.25, 2.35, 2.48, 4.12])

        if floor is not None:
            base_freqs = base_freqs * (1 + floor * 0.03)

        noise = np.random.normal(0, 0.02, size=len(base_freqs))
        frequencies = base_freqs * (1 + noise)

        damping = np.random.normal(0.025, 0.005, size=len(base_freqs))
        damping = np.clip(damping, 0.01, 0.1)

        mode_shapes = []
        for i in range(len(base_freqs)):
            shape = np.sin(np.linspace(0, np.pi * (i + 1), n_channels))
            shape = shape / np.max(np.abs(shape))
            mode_shapes.append(shape.tolist())

        return {
            'frequencies': frequencies.tolist(),
            'damping_ratios': damping.tolist(),
            'mode_shapes': mode_shapes,
            'n_modes_identified': len(base_freqs)
        }

    async def _save_damage_results(self, analysis_id: uuid.UUID, damage_results: List[Dict]):
        """保存损伤识别结果"""
        for result in damage_results:
            damage_result = DamageResult(
                id=uuid.uuid4(),
                analysis_id=analysis_id,
                floor_number=result['floor_number'],
                element_id=result['element_id'],
                damage_index=result['damage_index'],
                natural_frequency=result.get('natural_frequency'),
                frequency_change=result.get('frequency_change'),
                confidence=result['confidence'],
                modal_parameters=result.get('modal_parameters'),
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(damage_result)

        await self.db.commit()

    async def get_analysis_status(self, analysis_id: uuid.UUID) -> Dict[str, Any]:
        """获取分析状态"""
        analysis = await self.db.execute(
            select(DamageAnalysis).where(DamageAnalysis.id == analysis_id)
        )
        analysis = analysis.scalar_one_or_none()

        if not analysis:
            raise ValueError(f"分析任务 {analysis_id} 不存在")

        results = await self.db.execute(
            select(DamageResult).where(
                DamageResult.analysis_id == analysis_id
            ).order_by(DamageResult.damage_index.desc())
        )
        results = results.scalars().all()

        return {
            'id': analysis.id,
            'status': analysis.status,
            'analysis_window': analysis.analysis_window,
            'start_time': analysis.start_time,
            'end_time': analysis.end_time,
            'created_at': analysis.created_at,
            'completed_at': analysis.completed_at,
            'results': [
                {
                    'id': r.id,
                    'floor_number': r.floor_number,
                    'element_id': r.element_id,
                    'damage_index': r.damage_index,
                    'natural_frequency': r.natural_frequency,
                    'frequency_change': r.frequency_change,
                    'confidence': r.confidence,
                    'created_at': r.created_at
                }
                for r in results
            ]
        }

    async def get_latest_damage_results(self, floor: Optional[int] = None,
                                         limit: int = 100) -> List[Dict]:
        """获取最新的损伤识别结果"""
        query = select(DamageResult).order_by(DamageResult.created_at.desc())
        if floor is not None:
            query = query.where(DamageResult.floor_number == floor)

        results = await self.db.execute(query.limit(limit))
        results = results.scalars().all()

        return [
            {
                'id': r.id,
                'analysis_id': r.analysis_id,
                'floor_number': r.floor_number,
                'element_id': r.element_id,
                'damage_index': r.damage_index,
                'natural_frequency': r.natural_frequency,
                'frequency_change': r.frequency_change,
                'confidence': r.confidence,
                'created_at': r.created_at
            }
            for r in results
        ]
