from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class SensorDataIn(BaseModel):
    device_id: str = Field(..., description="设备ID")
    floor: int = Field(..., ge=1, le=5, description="楼层号")
    sensor_type: str = Field(..., description="传感器类型")
    timestamp: datetime = Field(..., description="数据时间戳")
    value: float = Field(..., description="测量值")
    unit: str = Field(..., description="单位")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="原始数据")


class SensorDataOut(BaseModel):
    time: datetime
    sensor_id: uuid.UUID
    value: float
    unit: Optional[str]

    class Config:
        from_attributes = True


class SensorInfo(BaseModel):
    id: uuid.UUID
    device_id: str
    floor_number: int
    sensor_type: str
    x_position: Optional[float]
    y_position: Optional[float]
    z_position: Optional[float]
    status: str
    dtu_id: Optional[str]

    class Config:
        from_attributes = True


class FloorInfo(BaseModel):
    floor_number: int
    height: float
    diameter: float
    beam_count: int
    column_count: int
    description: Optional[str]

    class Config:
        from_attributes = True


class AlertThresholdConfig(BaseModel):
    parameter_name: str
    warning_threshold: float
    critical_threshold: float
    unit: Optional[str]
    description: Optional[str]


class AlertOut(BaseModel):
    id: uuid.UUID
    alert_type: str
    floor_number: Optional[int]
    threshold_value: float
    actual_value: float
    severity: str
    status: str
    created_at: datetime
    note: Optional[str]

    class Config:
        from_attributes = True


class TimberProperties(BaseModel):
    E_L: float = Field(10000.0, description="顺纹弹性模量 MPa")
    E_R: float = Field(800.0, description="径向弹性模量 MPa")
    E_T: float = Field(500.0, description="弦向弹性模量 MPa")
    G_LR: float = Field(700.0, description="LR面剪切模量 MPa")
    G_LT: float = Field(600.0, description="LT面剪切模量 MPa")
    G_RT: float = Field(100.0, description="RT面剪切模量 MPa")
    v_LR: float = Field(0.35, description="LR面泊松比")
    v_LT: float = Field(0.45, description="LT面泊松比")
    v_RT: float = Field(0.55, description="RT面泊松比")
    density: float = Field(450.0, description="密度 kg/m³")


class LoadParams(BaseModel):
    wind_speed: Optional[float] = Field(None, description="风速 m/s")
    earthquake_level: Optional[float] = Field(None, description="地震烈度")
    duration: float = Field(10.0, description="持时 s")
    time_step: float = Field(0.01, description="时间步长 s")


class SimulationConfig(BaseModel):
    simulation_type: str = Field(..., description="仿真类型: wind/earthquake")
    timber_properties: TimberProperties = Field(..., description="木材材料参数")
    load_params: LoadParams = Field(..., description="荷载参数")
    damping_ratio: float = Field(0.02, description="阻尼比")


class SimulationResultOut(BaseModel):
    id: uuid.UUID
    simulation_id: uuid.UUID
    floor_number: Optional[int]
    max_displacement: Optional[float]
    max_stress: Optional[float]
    max_acceleration: Optional[float]
    natural_frequencies: Optional[List[float]]
    time_history_data: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class DamageAnalysisRequest(BaseModel):
    analysis_window: int = Field(3600, description="分析时间窗口 秒")
    floor: Optional[int] = Field(None, description="指定楼层，None表示所有楼层")


class DamageResultOut(BaseModel):
    id: uuid.UUID
    analysis_id: uuid.UUID
    floor_number: int
    element_id: int
    damage_index: float
    natural_frequency: Optional[float]
    frequency_change: Optional[float]
    confidence: float
    created_at: datetime

    class Config:
        from_attributes = True


class ModalParameterOut(BaseModel):
    id: uuid.UUID
    floor_number: int
    mode_order: int
    natural_frequency: float
    damping_ratio: Optional[float]
    is_baseline: bool
    measured_at: datetime
    description: Optional[str]

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    role: str
    email: Optional[str]
    full_name: Optional[str]

    class Config:
        from_attributes = True


class QueryParams(BaseModel):
    floor: Optional[int] = None
    sensor_type: Optional[str] = None
    start_time: datetime
    end_time: datetime
    aggregation: str = Field("raw", description="聚合方式: raw/1m/10m/1h/1d")
    sensor_id: Optional[uuid.UUID] = None
