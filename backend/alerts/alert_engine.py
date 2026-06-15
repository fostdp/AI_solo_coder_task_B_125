import asyncio
import uuid
import numpy as np
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from core.models import Alert, AlertThreshold, SensorData, Sensor, Floor
from core.schemas import AlertThresholdConfig


class AlertEngine:
    """告警规则引擎"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.thresholds: Dict[str, AlertThreshold] = {}
        self.alert_callbacks: List[Callable] = []

    async def load_thresholds(self):
        """加载所有告警阈值"""
        result = await self.db.execute(select(AlertThreshold))
        thresholds = result.scalars().all()
        for t in thresholds:
            self.thresholds[t.parameter_name] = t

    async def check_alerts(self, sensor_data: Dict[str, Any]) -> List[Alert]:
        """
        检查传感器数据是否触发告警

        Args:
            sensor_data: 传感器数据

        Returns:
            alerts: 触发的告警列表
        """
        if not self.thresholds:
            await self.load_thresholds()

        alerts = []

        device_id = sensor_data.get('device_id')
        sensor_type = sensor_data.get('sensor_type')
        value = sensor_data.get('value')
        floor = sensor_data.get('floor')
        timestamp = sensor_data.get('timestamp')

        sensor_result = await self.db.execute(
            select(Sensor).where(Sensor.device_id == device_id)
        )
        sensor = sensor_result.scalar_one_or_none()

        if not sensor:
            return alerts

        if sensor_type in ['displacement_x', 'displacement_y']:
            alert = await self._check_displacement(
                value, sensor_type, floor, sensor, timestamp
            )
            if alert:
                alerts.append(alert)

        elif sensor_type in ['acceleration_x', 'acceleration_y']:
            alert = await self._check_acceleration(
                value, floor, sensor, timestamp
            )
            if alert:
                alerts.append(alert)

        elif sensor_type == 'temperature':
            alert = await self._check_temperature(
                value, floor, sensor, timestamp
            )
            if alert:
                alerts.append(alert)

        elif sensor_type == 'moisture':
            alert = await self._check_moisture(
                value, floor, sensor, timestamp
            )
            if alert:
                alerts.append(alert)

        for alert in alerts:
            await self._trigger_alert(alert)

        return alerts

    async def _check_displacement(self, value: float, sensor_type: str, floor: int,
                                   sensor: Sensor, timestamp: datetime) -> Optional[Alert]:
        """检查位移告警"""
        threshold = self.thresholds.get('displacement_x' if 'x' in sensor_type else 'displacement_y')
        if not threshold:
            return None

        value_mm = abs(value) * 1000

        if value_mm >= threshold.critical_threshold:
            severity = 'critical'
            threshold_value = threshold.critical_threshold
        elif value_mm >= threshold.warning_threshold:
            severity = 'warning'
            threshold_value = threshold.warning_threshold
        else:
            return None

        drift_alert = await self._check_inter_story_drift(floor, value, timestamp, sensor)
        if drift_alert:
            return drift_alert

        return Alert(
            id=uuid.uuid4(),
            alert_type=f"{sensor_type}_exceed",
            floor_number=floor,
            sensor_id=sensor.id,
            threshold_value=threshold_value,
            actual_value=value_mm,
            severity=severity,
            status='pending',
            created_at=timestamp
        )

    async def _check_inter_story_drift(self, floor: int, displacement: float,
                                        timestamp: datetime, sensor: Sensor) -> Optional[Alert]:
        """检查层间位移角"""
        if floor <= 1:
            return None

        try:
            upper_floor = floor
            lower_floor = floor - 1

            floor_height = 9.23 if lower_floor == 1 else 8.5

            upper_disp = await self._get_recent_displacement(upper_floor, timestamp)
            lower_disp = await self._get_recent_displacement(lower_floor, timestamp)

            if upper_disp is None or lower_disp is None:
                return None

            relative_disp = abs(upper_disp - lower_disp)
            drift_ratio = relative_disp / floor_height

            threshold = self.thresholds.get('inter_story_drift_ratio')
            if not threshold:
                return None

            if drift_ratio >= threshold.critical_threshold:
                severity = 'critical'
                threshold_value = threshold.critical_threshold
            elif drift_ratio >= threshold.warning_threshold:
                severity = 'warning'
                threshold_value = threshold.warning_threshold
            else:
                return None

            return Alert(
                id=uuid.uuid4(),
                alert_type='inter_story_drift_exceed',
                floor_number=floor,
                sensor_id=sensor.id,
                threshold_value=threshold_value,
                actual_value=float(drift_ratio),
                severity=severity,
                status='pending',
                created_at=timestamp,
                note=f"层间位移角: {drift_ratio*100:.4f}%"
            )
        except Exception:
            return None

    async def _get_recent_displacement(self, floor: int, timestamp: datetime) -> Optional[float]:
        """获取最近的位移数据"""
        end_time = timestamp
        start_time = end_time - timedelta(minutes=10)

        sensor_result = await self.db.execute(
            select(Sensor).where(
                and_(
                    Sensor.floor_number == floor,
                    Sensor.sensor_type == 'displacement_x'
                )
            )
        )
        sensor = sensor_result.scalar_one_or_none()

        if not sensor:
            return None

        data_result = await self.db.execute(
            select(SensorData).where(
                and_(
                    SensorData.sensor_id == sensor.id,
                    SensorData.time >= start_time,
                    SensorData.time <= end_time
                )
            ).order_by(SensorData.time.desc()).limit(1)
        )
        data = data_result.scalar_one_or_none()

        return data.value if data else None

    async def _check_acceleration(self, value: float, floor: int,
                                   sensor: Sensor, timestamp: datetime) -> Optional[Alert]:
        """检查加速度告警"""
        threshold = self.thresholds.get('acceleration')
        if not threshold:
            return None

        value_g = abs(value) / 9.81

        if value_g >= threshold.critical_threshold:
            severity = 'critical'
            threshold_value = threshold.critical_threshold
        elif value_g >= threshold.warning_threshold:
            severity = 'warning'
            threshold_value = threshold.warning_threshold
        else:
            return None

        return Alert(
            id=uuid.uuid4(),
            alert_type='acceleration_exceed',
            floor_number=floor,
            sensor_id=sensor.id,
            threshold_value=threshold_value,
            actual_value=value_g,
            severity=severity,
            status='pending',
            created_at=timestamp
        )

    async def _check_temperature(self, value: float, floor: int,
                                   sensor: Sensor, timestamp: datetime) -> Optional[Alert]:
        """检查温度告警"""
        threshold = self.thresholds.get('temperature')
        if not threshold:
            return None

        if value >= threshold.critical_threshold:
            severity = 'critical'
            threshold_value = threshold.critical_threshold
        elif value >= threshold.warning_threshold:
            severity = 'warning'
            threshold_value = threshold.warning_threshold
        else:
            return None

        return Alert(
            id=uuid.uuid4(),
            alert_type='temperature_exceed',
            floor_number=floor,
            sensor_id=sensor.id,
            threshold_value=threshold_value,
            actual_value=value,
            severity=severity,
            status='pending',
            created_at=timestamp
        )

    async def _check_moisture(self, value: float, floor: int,
                               sensor: Sensor, timestamp: datetime) -> Optional[Alert]:
        """检查木材含水率告警"""
        threshold = self.thresholds.get('moisture_content')
        if not threshold:
            return None

        if value >= threshold.critical_threshold:
            severity = 'critical'
            threshold_value = threshold.critical_threshold
        elif value >= threshold.warning_threshold:
            severity = 'warning'
            threshold_value = threshold.warning_threshold
        else:
            return None

        return Alert(
            id=uuid.uuid4(),
            alert_type='moisture_content_exceed',
            floor_number=floor,
            sensor_id=sensor.id,
            threshold_value=threshold_value,
            actual_value=value,
            severity=severity,
            status='pending',
            created_at=timestamp
        )

    async def check_frequency_change(self, current_freq: float, baseline_freq: float,
                                      floor: int, sensor_id: Optional[uuid.UUID] = None) -> Optional[Alert]:
        """检查固有频率变化"""
        if baseline_freq <= 0:
            return None

        frequency_drop = abs(current_freq - baseline_freq) / baseline_freq

        threshold = self.thresholds.get('natural_frequency_drop')
        if not threshold:
            return None

        if frequency_drop >= threshold.critical_threshold:
            severity = 'critical'
            threshold_value = threshold.critical_threshold
        elif frequency_drop >= threshold.warning_threshold:
            severity = 'warning'
            threshold_value = threshold.warning_threshold
        else:
            return None

        alert = Alert(
            id=uuid.uuid4(),
            alert_type='natural_frequency_drop',
            floor_number=floor,
            sensor_id=sensor_id,
            threshold_value=threshold_value * 100,
            actual_value=frequency_drop * 100,
            severity=severity,
            status='pending',
            created_at=datetime.now(timezone.utc),
            note=f"固有频率: {current_freq:.4f} Hz, 基准: {baseline_freq:.4f} Hz, 下降: {frequency_drop*100:.2f}%"
        )

        await self._trigger_alert(alert)
        return alert

    async def _trigger_alert(self, alert: Alert):
        """触发告警并保存"""
        self.db.add(alert)
        await self.db.commit()

        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                print(f"告警回调执行失败: {e}")

    def register_callback(self, callback: Callable):
        """注册告警回调"""
        self.alert_callbacks.append(callback)

    async def update_threshold(self, config: AlertThresholdConfig) -> AlertThreshold:
        """更新告警阈值"""
        result = await self.db.execute(
            select(AlertThreshold).where(AlertThreshold.parameter_name == config.parameter_name)
        )
        threshold = result.scalar_one_or_none()

        if not threshold:
            threshold = AlertThreshold(
                id=uuid.uuid4(),
                parameter_name=config.parameter_name
            )
            self.db.add(threshold)

        threshold.warning_threshold = config.warning_threshold
        threshold.critical_threshold = config.critical_threshold
        threshold.unit = config.unit
        threshold.description = config.description
        threshold.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(threshold)

        self.thresholds[config.parameter_name] = threshold

        return threshold

    async def get_all_thresholds(self) -> List[Dict[str, Any]]:
        """获取所有告警阈值"""
        if not self.thresholds:
            await self.load_thresholds()

        return [
            {
                'parameter_name': t.parameter_name,
                'warning_threshold': t.warning_threshold,
                'critical_threshold': t.critical_threshold,
                'unit': t.unit,
                'description': t.description,
                'updated_at': t.updated_at
            }
            for t in self.thresholds.values()
        ]

    async def get_pending_alerts(self, floor: Optional[int] = None,
                                  severity: Optional[str] = None,
                                  limit: int = 100) -> List[Alert]:
        """获取待处理告警"""
        query = select(Alert).where(Alert.status == 'pending').order_by(Alert.created_at.desc())

        if floor is not None:
            query = query.where(Alert.floor_number == floor)
        if severity is not None:
            query = query.where(Alert.severity == severity)

        result = await self.db.execute(query.limit(limit))
        return result.scalars().all()

    async def resolve_alert(self, alert_id: uuid.UUID, user_id: uuid.UUID,
                             note: Optional[str] = None) -> Optional[Alert]:
        """处理告警"""
        result = await self.db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        alert.status = 'resolved'
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolved_by = user_id
        if note:
            alert.note = note

        await self.db.commit()
        await self.db.refresh(alert)

        return alert

    async def get_alert_history(self, start_time: Optional[datetime] = None,
                                 end_time: Optional[datetime] = None,
                                 floor: Optional[int] = None,
                                 limit: int = 1000) -> List[Alert]:
        """获取告警历史"""
        query = select(Alert).order_by(Alert.created_at.desc())

        if start_time:
            query = query.where(Alert.created_at >= start_time)
        if end_time:
            query = query.where(Alert.created_at <= end_time)
        if floor is not None:
            query = query.where(Alert.floor_number == floor)

        result = await self.db.execute(query.limit(limit))
        return result.scalars().all()
