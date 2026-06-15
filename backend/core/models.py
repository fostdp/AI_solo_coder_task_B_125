from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean,
    ForeignKey, JSON, ARRAY, DECIMAL, Text
)
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMPTZ
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from .database import Base


class Floor(Base):
    __tablename__ = "floors"

    floor_number = Column(Integer, primary_key=True)
    height = Column(DECIMAL(10, 4), nullable=False)
    diameter = Column(DECIMAL(10, 4), nullable=False)
    beam_count = Column(Integer, nullable=False)
    column_count = Column(Integer, nullable=False)
    description = Column(Text)
    created_at = Column(TIMESTAMPTZ, default=datetime.utcnow)

    sensors = relationship("Sensor", back_populates="floor")
    alerts = relationship("Alert", back_populates="floor")


class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(50), unique=True, nullable=False)
    floor_number = Column(Integer, ForeignKey("floors.floor_number"))
    sensor_type = Column(String(30), nullable=False)
    x_position = Column(DECIMAL(10, 4))
    y_position = Column(DECIMAL(10, 4))
    z_position = Column(DECIMAL(10, 4))
    status = Column(String(20), default="active")
    dtu_id = Column(String(50))
    sampling_interval = Column(Integer, default=600)
    created_at = Column(TIMESTAMPTZ, default=datetime.utcnow)

    floor = relationship("Floor", back_populates="sensors")
    sensor_data = relationship("SensorData", back_populates="sensor")
    alerts = relationship("Alert", back_populates="sensor")


class SensorData(Base):
    __tablename__ = "sensor_data"

    time = Column(TIMESTAMPTZ, primary_key=True)
    sensor_id = Column(UUID(as_uuid=True), ForeignKey("sensors.id"), primary_key=True)
    value = Column(Float, nullable=False)
    unit = Column(String(20))
    raw_data = Column(JSON)

    sensor = relationship("Sensor", back_populates="sensor_data")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="monitor")
    email = Column(String(100))
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMPTZ, default=datetime.utcnow)
    last_login = Column(TIMESTAMPTZ)

    resolved_alerts = relationship("Alert", back_populates="resolved_by_user")
    simulations = relationship("Simulation", back_populates="created_by_user")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_type = Column(String(50), nullable=False)
    floor_number = Column(Integer, ForeignKey("floors.floor_number"))
    sensor_id = Column(UUID(as_uuid=True), ForeignKey("sensors.id"))
    threshold_value = Column(Float, nullable=False)
    actual_value = Column(Float, nullable=False)
    severity = Column(String(20), nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(TIMESTAMPTZ, default=datetime.utcnow)
    resolved_at = Column(TIMESTAMPTZ)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    note = Column(Text)

    floor = relationship("Floor", back_populates="alerts")
    sensor = relationship("Sensor", back_populates="alerts")
    resolved_by_user = relationship("User", back_populates="resolved_alerts")


class AlertThreshold(Base):
    __tablename__ = "alert_thresholds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parameter_name = Column(String(50), unique=True, nullable=False)
    warning_threshold = Column(Float, nullable=False)
    critical_threshold = Column(Float, nullable=False)
    unit = Column(String(20))
    description = Column(Text)
    updated_at = Column(TIMESTAMPTZ, default=datetime.utcnow)


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_type = Column(String(20), nullable=False)
    config = Column(JSON, nullable=False)
    status = Column(String(20), default="pending")
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(TIMESTAMPTZ, default=datetime.utcnow)
    started_at = Column(TIMESTAMPTZ)
    completed_at = Column(TIMESTAMPTZ)

    created_by_user = relationship("User", back_populates="simulations")
    results = relationship("SimulationResult", back_populates="simulation")


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=False)
    floor_number = Column(Integer)
    max_displacement = Column(Float)
    max_stress = Column(Float)
    max_acceleration = Column(Float)
    natural_frequencies = Column(ARRAY(Float))
    mode_shapes = Column(JSON)
    time_history_data = Column(JSON)
    created_at = Column(TIMESTAMPTZ, default=datetime.utcnow)

    simulation = relationship("Simulation", back_populates="results")


class DamageAnalysis(Base):
    __tablename__ = "damage_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(20), default="processing")
    analysis_window = Column(Integer, nullable=False)
    start_time = Column(TIMESTAMPTZ, nullable=False)
    end_time = Column(TIMESTAMPTZ, nullable=False)
    created_at = Column(TIMESTAMPTZ, default=datetime.utcnow)
    completed_at = Column(TIMESTAMPTZ)

    results = relationship("DamageResult", back_populates="analysis")


class DamageResult(Base):
    __tablename__ = "damage_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("damage_analyses.id"), nullable=False)
    floor_number = Column(Integer, nullable=False)
    element_id = Column(Integer, nullable=False)
    damage_index = Column(Float, nullable=False)
    natural_frequency = Column(Float)
    frequency_change = Column(Float)
    confidence = Column(Float, nullable=False)
    modal_parameters = Column(JSON)
    created_at = Column(TIMESTAMPTZ, default=datetime.utcnow)

    analysis = relationship("DamageAnalysis", back_populates="results")


class ModalParameter(Base):
    __tablename__ = "modal_parameters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    floor_number = Column(Integer, nullable=False)
    mode_order = Column(Integer, nullable=False)
    natural_frequency = Column(Float, nullable=False)
    damping_ratio = Column(Float)
    mode_shape = Column(JSON)
    is_baseline = Column(Boolean, default=False)
    measured_at = Column(TIMESTAMPTZ, default=datetime.utcnow)
    description = Column(Text)


class DtuDevice(Base):
    __tablename__ = "dtu_devices"

    id = Column(String(50), primary_key=True)
    name = Column(String(100))
    floor_number = Column(Integer, ForeignKey("floors.floor_number"))
    ip_address = Column(String(50))
    status = Column(String(20), default="online")
    last_heartbeat = Column(TIMESTAMPTZ)
    created_at = Column(TIMESTAMPTZ, default=datetime.utcnow)
