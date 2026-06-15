from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional
from datetime import datetime
import uuid

from core.database import get_async_session
from core.models import Sensor, SensorData, Floor, DtuDevice
from core.schemas import SensorDataIn, SensorDataOut, SensorInfo, FloorInfo, QueryParams
from alerts.alert_engine import AlertEngine
from alerts.websocket_manager import websocket_manager

router = APIRouter(prefix="/api/sensors", tags=["传感器数据"])

alert_engine = AlertEngine()


@router.post("/data", response_model=dict, summary="上报传感器数据")
async def submit_sensor_data(
    data: SensorDataIn,
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(Sensor).where(Sensor.device_id == data.device_id)
    result = await db.execute(stmt)
    sensor = result.scalar_one_or_none()
    
    if not sensor:
        raise HTTPException(status_code=404, detail=f"传感器设备 {data.device_id} 未找到")
    
    sensor_data = SensorData(
        time=data.timestamp,
        sensor_id=sensor.id,
        value=data.value,
        unit=data.unit,
        raw_data=data.raw_data
    )
    db.add(sensor_data)
    await db.commit()
    
    alerts = await alert_engine.check_and_generate_alerts(
        db, sensor, data.value, data.timestamp
    )
    
    ws_data = {
        "type": "sensor_data",
        "sensor_id": str(sensor.id),
        "device_id": data.device_id,
        "floor": sensor.floor_number,
        "sensor_type": sensor.sensor_type,
        "value": data.value,
        "unit": data.unit,
        "timestamp": data.timestamp.isoformat()
    }
    await websocket_manager.broadcast_to_room("monitoring", ws_data)
    
    for alert in alerts:
        await alert_engine.process_alert(db, alert)
        alert_data = {
            "type": "alert",
            "id": str(alert.id),
            "alert_type": alert.alert_type,
            "floor": alert.floor_number,
            "severity": alert.severity,
            "actual_value": alert.actual_value,
            "threshold_value": alert.threshold_value,
            "timestamp": alert.created_at.isoformat()
        }
        await websocket_manager.broadcast_to_room("alerts", alert_data)
    
    return {"status": "success", "message": "数据已接收", "alerts_count": len(alerts)}


@router.get("/data", response_model=List[SensorDataOut], summary="查询传感器历史数据")
async def get_sensor_data(
    floor: Optional[int] = Query(None, description="楼层号"),
    sensor_type: Optional[str] = Query(None, description="传感器类型"),
    sensor_id: Optional[uuid.UUID] = Query(None, description="传感器ID"),
    start_time: datetime = Query(..., description="开始时间"),
    end_time: datetime = Query(..., description="结束时间"),
    aggregation: str = Query("raw", description="聚合方式: raw/1m/10m/1h/1d"),
    db: AsyncSession = Depends(get_async_session)
):
    conditions = [
        SensorData.time >= start_time,
        SensorData.time <= end_time
    ]
    
    if sensor_id:
        conditions.append(SensorData.sensor_id == sensor_id)
    else:
        sensor_conditions = []
        if floor:
            sensor_conditions.append(Sensor.floor_number == floor)
        if sensor_type:
            sensor_conditions.append(Sensor.sensor_type == sensor_type)
        
        if sensor_conditions:
            stmt = select(Sensor.id).where(and_(*sensor_conditions))
            result = await db.execute(stmt)
            sensor_ids = [row[0] for row in result.all()]
            if sensor_ids:
                conditions.append(SensorData.sensor_id.in_(sensor_ids))
    
    if aggregation == "raw":
        stmt = select(SensorData).where(and_(*conditions)).order_by(SensorData.time)
    else:
        bucket_map = {
            "1m": "1 minute",
            "10m": "10 minutes",
            "1h": "1 hour",
            "1d": "1 day"
        }
        bucket = bucket_map.get(aggregation, "10 minutes")
        stmt = select(
            func.time_bucket(bucket, SensorData.time).label("time"),
            SensorData.sensor_id,
            func.avg(SensorData.value).label("value"),
            SensorData.unit
        ).where(and_(*conditions)).group_by(
            func.time_bucket(bucket, SensorData.time),
            SensorData.sensor_id,
            SensorData.unit
        ).order_by("time")
    
    result = await db.execute(stmt)
    return result.all()


@router.get("", response_model=List[SensorInfo], summary="获取传感器列表")
async def get_sensors(
    floor: Optional[int] = Query(None, description="楼层号"),
    sensor_type: Optional[str] = Query(None, description="传感器类型"),
    status: Optional[str] = Query(None, description="状态"),
    db: AsyncSession = Depends(get_async_session)
):
    conditions = []
    if floor:
        conditions.append(Sensor.floor_number == floor)
    if sensor_type:
        conditions.append(Sensor.sensor_type == sensor_type)
    if status:
        conditions.append(Sensor.status == status)
    
    stmt = select(Sensor).where(and_(*conditions)).order_by(Sensor.floor_number, Sensor.sensor_type)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/floors", response_model=List[FloorInfo], summary="获取楼层信息")
async def get_floors(
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(Floor).order_by(Floor.floor_number)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/dtu-devices", summary="获取DTU设备列表")
async def get_dtu_devices(
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(DtuDevice).order_by(DtuDevice.floor_number)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/realtime/{floor}", summary="获取指定楼层实时数据")
async def get_floor_realtime_data(
    floor: int,
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(Sensor).where(Sensor.floor_number == floor)
    result = await db.execute(stmt)
    sensors = result.scalars().all()
    
    realtime_data = {}
    for sensor in sensors:
        stmt_latest = select(SensorData).where(
            SensorData.sensor_id == sensor.id
        ).order_by(SensorData.time.desc()).limit(1)
        result_latest = await db.execute(stmt_latest)
        latest_data = result_latest.scalar_one_or_none()
        
        if latest_data:
            realtime_data[sensor.sensor_type] = {
                "value": latest_data.value,
                "unit": latest_data.unit,
                "timestamp": latest_data.time.isoformat(),
                "sensor_id": str(sensor.id),
                "device_id": sensor.device_id
            }
    
    return {
        "floor": floor,
        "realtime_data": realtime_data,
        "sensor_count": len(sensors)
    }


@router.get("/statistics", summary="获取数据统计")
async def get_statistics(
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(func.count(Sensor.id)).where(Sensor.status == "active")
    result = await db.execute(stmt)
    active_sensors = result.scalar()
    
    stmt = select(func.count(func.distinct(SensorData.sensor_id))).select_from(SensorData)
    result = await db.execute(stmt)
    reporting_sensors = result.scalar()
    
    stmt = select(func.count(SensorData.id)).select_from(SensorData)
    result = await db.execute(stmt)
    total_records = result.scalar()
    
    return {
        "active_sensors": active_sensors,
        "reporting_sensors": reporting_sensors,
        "total_records": total_records,
        "offline_sensors": active_sensors - reporting_sensors if active_sensors and reporting_sensors else 0
    }
