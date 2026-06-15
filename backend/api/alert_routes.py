from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from core.database import get_async_session
from core.models import Alert, AlertThreshold
from core.schemas import AlertOut, AlertThresholdConfig
from alerts.alert_engine import AlertEngine

router = APIRouter(prefix="/api/alerts", tags=["告警系统"])

alert_engine = AlertEngine()


@router.get("", response_model=List[AlertOut], summary="获取告警列表")
async def get_alerts(
    status: Optional[str] = Query(None, description="告警状态: pending/acknowledged/resolved"),
    severity: Optional[str] = Query(None, description="告警级别: warning/critical"),
    floor: Optional[int] = Query(None, description="楼层号"),
    alert_type: Optional[str] = Query(None, description="告警类型"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(100, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(Alert).order_by(Alert.created_at.desc())
    
    conditions = []
    if status:
        conditions.append(Alert.status == status)
    if severity:
        conditions.append(Alert.severity == severity)
    if floor:
        conditions.append(Alert.floor_number == floor)
    if alert_type:
        conditions.append(Alert.alert_type == alert_type)
    if start_time:
        conditions.append(Alert.created_at >= start_time)
    if end_time:
        conditions.append(Alert.created_at <= end_time)
    
    if conditions:
        stmt = stmt.where(and_(*conditions))
    
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{alert_id}", response_model=AlertOut, summary="获取告警详情")
async def get_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    return alert


@router.put("/{alert_id}/acknowledge", summary="确认告警")
async def acknowledge_alert(
    alert_id: uuid.UUID,
    note: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    alert.status = "acknowledged"
    if note:
        alert.note = note
    
    await db.commit()
    
    return {
        "status": "success",
        "message": "告警已确认",
        "alert_id": str(alert_id)
    }


@router.put("/{alert_id}/resolve", summary="处理告警")
async def resolve_alert(
    alert_id: uuid.UUID,
    note: Optional[str] = None,
    resolved_by: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    alert.status = "resolved"
    alert.resolved_at = datetime.utcnow()
    if resolved_by:
        alert.resolved_by = resolved_by
    if note:
        alert.note = note
    
    await db.commit()
    
    return {
        "status": "success",
        "message": "告警已处理",
        "alert_id": str(alert_id)
    }


@router.get("/statistics", summary="获取告警统计")
async def get_alert_statistics(
    hours: int = Query(24, description="统计时间范围（小时）"),
    db: AsyncSession = Depends(get_async_session)
):
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    stmt_total = select(func.count(Alert.id)).where(Alert.created_at >= start_time)
    result_total = await db.execute(stmt_total)
    total = result_total.scalar()
    
    stmt_pending = select(func.count(Alert.id)).where(
        and_(Alert.created_at >= start_time, Alert.status == "pending")
    )
    result_pending = await db.execute(stmt_pending)
    pending = result_pending.scalar()
    
    stmt_warning = select(func.count(Alert.id)).where(
        and_(Alert.created_at >= start_time, Alert.severity == "warning")
    )
    result_warning = await db.execute(stmt_warning)
    warning_count = result_warning.scalar()
    
    stmt_critical = select(func.count(Alert.id)).where(
        and_(Alert.created_at >= start_time, Alert.severity == "critical")
    )
    result_critical = await db.execute(stmt_critical)
    critical_count = result_critical.scalar()
    
    stmt_by_type = select(
        Alert.alert_type,
        func.count(Alert.id).label("count")
    ).where(
        Alert.created_at >= start_time
    ).group_by(Alert.alert_type)
    result_by_type = await db.execute(stmt_by_type)
    by_type = {row[0]: row[1] for row in result_by_type.all()}
    
    stmt_by_floor = select(
        Alert.floor_number,
        func.count(Alert.id).label("count")
    ).where(
        and_(Alert.created_at >= start_time, Alert.floor_number.isnot(None))
    ).group_by(Alert.floor_number).order_by(Alert.floor_number)
    result_by_floor = await db.execute(stmt_by_floor)
    by_floor = {row[0]: row[1] for row in result_by_floor.all()}
    
    return {
        "time_range_hours": hours,
        "total_alerts": total,
        "pending_alerts": pending,
        "warning_alerts": warning_count,
        "critical_alerts": critical_count,
        "alerts_by_type": by_type,
        "alerts_by_floor": by_floor
    }


@router.get("/thresholds", summary="获取告警阈值配置")
async def get_alert_thresholds(
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(AlertThreshold).order_by(AlertThreshold.parameter_name)
    result = await db.execute(stmt)
    thresholds = result.scalars().all()
    
    return [
        {
            "id": str(t.id),
            "parameter_name": t.parameter_name,
            "warning_threshold": t.warning_threshold,
            "critical_threshold": t.critical_threshold,
            "unit": t.unit,
            "description": t.description,
            "updated_at": t.updated_at.isoformat()
        }
        for t in thresholds
    ]


@router.post("/thresholds", summary="设置告警阈值")
async def set_alert_threshold(
    config: AlertThresholdConfig,
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(AlertThreshold).where(AlertThreshold.parameter_name == config.parameter_name)
    result = await db.execute(stmt)
    threshold = result.scalar_one_or_none()
    
    if threshold:
        threshold.warning_threshold = config.warning_threshold
        threshold.critical_threshold = config.critical_threshold
        threshold.unit = config.unit
        threshold.description = config.description
        threshold.updated_at = datetime.utcnow()
    else:
        threshold = AlertThreshold(
            parameter_name=config.parameter_name,
            warning_threshold=config.warning_threshold,
            critical_threshold=config.critical_threshold,
            unit=config.unit,
            description=config.description
        )
        db.add(threshold)
    
    await db.commit()
    
    await alert_engine.reload_thresholds(db)
    
    return {
        "status": "success",
        "message": "阈值配置已更新",
        "parameter_name": config.parameter_name
    }


@router.delete("/{alert_id}", summary="删除告警")
async def delete_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    await db.delete(alert)
    await db.commit()
    
    return {
        "status": "success",
        "message": "告警已删除",
        "alert_id": str(alert_id)
    }


@router.post("/check/{sensor_id}", summary="手动触发告警检查")
async def manual_alert_check(
    sensor_id: uuid.UUID,
    value: float,
    db: AsyncSession = Depends(get_async_session)
):
    from core.models import Sensor
    
    stmt = select(Sensor).where(Sensor.id == sensor_id)
    result = await db.execute(stmt)
    sensor = result.scalar_one_or_none()
    
    if not sensor:
        raise HTTPException(status_code=404, detail="传感器不存在")
    
    alerts = await alert_engine.check_and_generate_alerts(
        db, sensor, value, datetime.utcnow()
    )
    
    return {
        "alerts_generated": len(alerts),
        "alerts": [
            {
                "id": str(a.id),
                "alert_type": a.alert_type,
                "severity": a.severity,
                "actual_value": a.actual_value,
                "threshold_value": a.threshold_value
            }
            for a in alerts
        ]
    }
