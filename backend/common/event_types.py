from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid


class EventType(str, Enum):
    SENSOR_DATA_RECEIVED = "sensor.data.received"
    SIMULATION_REQUEST = "simulation.request"
    SIMULATION_PROGRESS = "simulation.progress"
    SIMULATION_RESULT = "simulation.result"
    DAMAGE_REQUEST = "damage.request"
    DAMAGE_RESULT = "damage.result"
    ALERT_TRIGGERED = "alert.triggered"
    ALERT_RESOLVED = "alert.resolved"


@dataclass
class SensorDataEvent:
    device_id: str
    sensor_type: str
    floor: int
    value: float
    unit: str
    timestamp: str
    raw_data: Optional[Dict[str, Any]] = None
    sensor_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "sensor_type": self.sensor_type,
            "floor": self.floor,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp,
            "raw_data": self.raw_data,
            "sensor_id": self.sensor_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SensorDataEvent':
        return cls(**data)


@dataclass
class SimulationRequestEvent:
    simulation_id: str
    simulation_type: str
    timber_properties: Dict[str, float]
    load_params: Dict[str, Any]
    damping_ratio: float = 0.02
    use_mortise_tenon: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "simulation_type": self.simulation_type,
            "timber_properties": self.timber_properties,
            "load_params": self.load_params,
            "damping_ratio": self.damping_ratio,
            "use_mortise_tenon": self.use_mortise_tenon
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimulationRequestEvent':
        return cls(**data)


@dataclass
class SimulationResultEvent:
    simulation_id: str
    status: str
    floor_results: List[Dict[str, Any]] = field(default_factory=list)
    natural_frequencies: List[float] = field(default_factory=list)
    mode_shapes: List[List[float]] = field(default_factory=list)
    time_history: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "status": self.status,
            "floor_results": self.floor_results,
            "natural_frequencies": self.natural_frequencies,
            "mode_shapes": self.mode_shapes,
            "time_history": self.time_history,
            "error_message": self.error_message
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimulationResultEvent':
        return cls(**data)


@dataclass
class DamageRequestEvent:
    analysis_id: str
    start_time: str
    end_time: str
    floor: Optional[int] = None
    modal_params: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "floor": self.floor,
            "modal_params": self.modal_params
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DamageRequestEvent':
        return cls(**data)


@dataclass
class DamageResultEvent:
    analysis_id: str
    status: str
    results: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "status": self.status,
            "results": self.results,
            "error_message": self.error_message
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DamageResultEvent':
        return cls(**data)


@dataclass
class AlertEvent:
    alert_id: str
    alert_type: str
    floor: Optional[int]
    severity: str
    threshold_value: float
    actual_value: float
    timestamp: str
    sensor_id: Optional[str] = None
    note: Optional[str] = None
    status: str = "pending"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type,
            "floor": self.floor,
            "severity": self.severity,
            "threshold_value": self.threshold_value,
            "actual_value": self.actual_value,
            "timestamp": self.timestamp,
            "sensor_id": self.sensor_id,
            "note": self.note,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlertEvent':
        return cls(**data)
