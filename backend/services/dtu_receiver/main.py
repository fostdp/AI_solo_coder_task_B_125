"""
DTU Receiver Service
传感器数据采集服务 - 负责接收4G DTU上报的传感器数据，校验后写入数据库并通过Redis发布事件
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import logging
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional
from datetime import datetime
import uuid

from common.redis_bus import get_redis_bus
from common.event_types import EventType, SensorDataEvent
from common.config_loader import ServiceConfig

from core.database import get_db, Base
from core.models import Sensor, SensorData, Floor, DtuDevice
from core.schemas import SensorDataIn, SensorDataOut, SensorInfo, FloorInfo

config = ServiceConfig.from_env("dtu_receiver")
config.port = 8001

logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - DTU Receiver - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DTU数据采集服务",
    description="应县木塔传感器数据采集服务 - 接收4G DTU上报数据",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_bus = get_redis_bus(config.redis_url)


@app.on_event("startup")
async def startup():
    logger.info("启动DTU数据采集服务...")
    try:
        await redis_bus.connect()
        logger.info("Redis消息总线连接成功")
    except Exception as e:
        logger.error(f"Redis连接失败: {e}，服务仍可正常接收数据")
    logger.info("DTU数据采集服务启动完成")


@app.on_event("shutdown")
async def shutdown():
    logger.info("关闭DTU数据采集服务...")
    await redis_bus.disconnect()
    logger.info("服务已关闭")


@app.post("/api/sensors/data", summary="上报传感器数据")
async def submit_sensor_data(
    data: SensorDataIn,
    db: AsyncSession = Depends(get_db)
):
    """接收DTU上报的传感器数据"""
    stmt = select(Sensor).where(Sensor.device_id == data.device_id)
    result = await db.execute(stmt)
    sensor = result.scalar_one_or_none()

    if not sensor:
        raise HTTPException(status_code=404, detail=f"传感器设备 {data.device_id} 未找到")

    if sensor.status != "active":
        raise HTTPException(status_code=400, detail=f"传感器设备 {data.device_id} 状态为 {sensor.status}")

    sensor_data = SensorData(
        time=data.timestamp,
        sensor_id=sensor.id,
        value=data.value,
        unit=data.unit,
        raw_data=data.raw_data
    )
    db.add(sensor_data)
    await db.commit()

    event = SensorDataEvent(
        device_id=data.device_id,
        sensor_type=data.sensor_type,
        floor=sensor.floor_number,
        value=data.value,
        unit=data.unit,
        timestamp=data.timestamp.isoformat(),
        raw_data=data.raw_data,
        sensor_id=str(sensor.id)
    )

    try:
        await redis_bus.publish(
            EventType.SENSOR_DATA_RECEIVED.value,
            {
                "event_type": EventType.SENSOR_DATA_RECEIVED.value,
                "data": event.to_dict()
            }
        )
    except Exception as e:
        logger.warning(f"发布传感器数据事件失败: {e}")

    return {
        "status": "success",
        "message": "数据已接收",
        "sensor_id": str(sensor.id),
        "timestamp": data.timestamp.isoformat()
    }


@app.get("/api/sensors", response_model=List[SensorInfo], summary="获取传感器列表")
async def get_sensors(
    floor: Optional[int] = Query(None, description="楼层号"),
    sensor_type: Optional[str] = Query(None, description="传感器类型"),
    status: Optional[str] = Query(None, description="状态"),
    db: AsyncSession = Depends(get_db)
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


@app.get("/api/sensors/floors", response_model=List[FloorInfo], summary="获取楼层信息")
async def get_floors(db: AsyncSession = Depends(get_db)):
    stmt = select(Floor).order_by(Floor.floor_number)
    result = await db.execute(stmt)
    return result.scalars().all()


@app.get("/api/sensors/data", response_model=List[SensorDataOut], summary="查询传感器历史数据")
async def get_sensor_data(
    floor: Optional[int] = Query(None),
    sensor_type: Optional[str] = Query(None),
    sensor_id: Optional[uuid.UUID] = Query(None),
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    aggregation: str = Query("raw", description="聚合方式: raw/1m/10m/1h/1d"),
    db: AsyncSession = Depends(get_db)
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


@app.get("/api/sensors/realtime/{floor}", summary="获取指定楼层实时数据")
async def get_floor_realtime_data(
    floor: int,
    db: AsyncSession = Depends(get_db)
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


@app.get("/api/sensors/statistics", summary="获取数据统计")
async def get_statistics(db: AsyncSession = Depends(get_db)):
    stmt = select(func.count(Sensor.id)).where(Sensor.status == "active")
    result = await db.execute(stmt)
    active_sensors = result.scalar()

    stmt = select(func.count(func.distinct(SensorData.sensor_id))).select_from(SensorData)
    result = await db.execute(stmt)
    reporting_sensors = result.scalar()

    stmt = select(func.count(SensorData.time)).select_from(SensorData)
    result = await db.execute(stmt)
    total_records = result.scalar()

    return {
        "active_sensors": active_sensors,
        "reporting_sensors": reporting_sensors,
        "total_records": total_records,
        "offline_sensors": active_sensors - reporting_sensors if active_sensors and reporting_sensors else 0
    }


@app.get("/api/dtu-devices", summary="获取DTU设备列表")
async def get_dtu_devices(db: AsyncSession = Depends(get_db)):
    stmt = select(DtuDevice).order_by(DtuDevice.floor_number)
    result = await db.execute(stmt)
    return result.scalars().all()


@app.get("/health", summary="健康检查")
async def health_check():
    return {
        "service": "dtu_receiver",
        "status": "running",
        "version": "2.0.0",
        "redis_connected": redis_bus._is_connected
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
        reload=config.debug
    )
