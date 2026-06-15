"""
Alarm & WebSocket Service
告警与WebSocket服务 - 负责告警评估生成和WebSocket实时推送
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import logging
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import json

from common.redis_bus import get_redis_bus
from common.event_types import EventType, AlertEvent, SensorDataEvent
from common.config_loader import ServiceConfig, load_alert_thresholds

from core.database import get_db, Base
from core.models import Alert, AlertThreshold, Sensor, SensorData

config = ServiceConfig.from_env("alarm_ws")
config.port = 8004

logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - Alarm WS - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="告警与WebSocket服务",
    description="应县木塔告警评估与WebSocket实时推送服务",
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

active_connections: Dict[str, WebSocket] = {}
connection_rooms: Dict[str, set] = {}
client_rooms: Dict[str, List[str]] = {}

recent_alerts: List[Dict[str, Any]] = []
alert_thresholds_cache: Dict[str, Any] = {}

FLOOR_HEIGHTS = {1: 9.23, 2: 8.5, 3: 7.8, 4: 7.2, 5: 6.5}


def init_thresholds():
    """初始化告警阈值"""
    global alert_thresholds_cache
    alert_thresholds_cache = load_alert_thresholds().get("thresholds", {})
    logger.info(f"加载告警阈值: {len(alert_thresholds_cache)} 项")


async def broadcast_to_room(room: str, message: Dict[str, Any]):
    """向指定房间广播消息"""
    room_clients = connection_rooms.get(room, set())
    disconnected = []

    for client_id in room_clients:
        ws = active_connections.get(client_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message, ensure_ascii=False, default=str))
            except Exception:
                disconnected.append(client_id)
        else:
            disconnected.append(client_id)

    for client_id in disconnected:
        if client_id in connection_rooms.get(room, set()):
            connection_rooms[room].discard(client_id)
        if client_id in client_rooms:
            if room in client_rooms[client_id]:
                client_rooms[client_id].remove(room)


async def handle_sensor_data(message: Dict[str, Any]):
    """处理传感器数据事件 - 检查阈值并生成告警"""
    try:
        event_data = message.get("data", {})
        event = SensorDataEvent.from_dict(event_data)

        thresholds = alert_thresholds_cache

        if event.sensor_type == "displacement_x":
            threshold = thresholds.get("displacement_x", {})
            await check_and_alert(
                event, threshold, "displacement_x",
                abs(event.value), "mm"
            )

        elif event.sensor_type == "displacement_y":
            threshold = thresholds.get("displacement_y", {})
            await check_and_alert(
                event, threshold, "displacement_y",
                abs(event.value), "mm"
            )

        elif event.sensor_type == "acceleration":
            threshold = thresholds.get("acceleration", {})
            value_g = abs(event.value) / 9810.0
            await check_and_alert(
                event, threshold, "acceleration",
                value_g, "g"
            )

        elif event.sensor_type == "temperature":
            threshold = thresholds.get("temperature", {})
            await check_and_alert(
                event, threshold, "temperature",
                abs(event.value), "℃"
            )

        elif event.sensor_type == "moisture_content":
            threshold = thresholds.get("moisture_content", {})
            await check_and_alert(
                event, threshold, "moisture_content",
                event.value, "%"
            )

    except Exception as e:
        logger.error(f"处理传感器数据告警失败: {e}", exc_info=True)


async def check_and_alert(
    sensor_event: SensorDataEvent,
    threshold: Dict[str, Any],
    alert_type: str,
    value: float,
    unit: str
):
    """检查阈值并生成告警"""
    warning_val = threshold.get("warning_threshold", 0)
    critical_val = threshold.get("critical_threshold", 0)

    if value >= critical_val:
        severity = "critical"
        threshold_value = critical_val
    elif value >= warning_val:
        severity = "warning"
        threshold_value = warning_val
    else:
        return

    alert_id = str(uuid.uuid4())
    alert = AlertEvent(
        alert_id=alert_id,
        alert_type=alert_type,
        floor=sensor_event.floor,
        severity=severity,
        threshold_value=threshold_value,
        actual_value=value,
        timestamp=sensor_event.timestamp,
        sensor_id=sensor_event.sensor_id,
        note=f"{alert_type} 超过{severity}阈值",
        status="pending"
    )

    recent_alerts.insert(0, alert.to_dict())
    if len(recent_alerts) > 100:
        recent_alerts.pop()

    await redis_bus.publish(
        EventType.ALERT_TRIGGERED.value,
        {
            "event_type": EventType.ALERT_TRIGGERED.value,
            "data": alert.to_dict()
        }
    )

    await broadcast_to_room("alerts", {
        "type": "alert",
        "data": alert.to_dict()
    })

    await broadcast_to_room("monitoring", {
        "type": "alert",
        "data": alert.to_dict()
    })

    logger.warning(
        f"告警触发: {alert_type} - 第{sensor_event.floor}层 - {severity} "
        f"实际值: {value:.3f}{unit} 阈值: {threshold_value}{unit}"
    )


async def handle_alert_triggered(message: Dict[str, Any]):
    """处理外部告警事件 - 转发到WebSocket"""
    try:
        event_data = message.get("data", {})
        alert = AlertEvent.from_dict(event_data)

        await broadcast_to_room("alerts", {
            "type": "alert",
            "data": alert.to_dict()
        })

        await broadcast_to_room("monitoring", {
            "type": "alert",
            "data": alert.to_dict()
        })

        logger.info(f"转发告警到WebSocket: {alert.alert_type} - {alert.severity}")
    except Exception as e:
        logger.error(f"处理告警转发失败: {e}", exc_info=True)


async def handle_simulation_progress(message: Dict[str, Any]):
    """处理仿真进度事件"""
    try:
        await broadcast_to_room("simulation", message)
    except Exception as e:
        logger.error(f"处理仿真进度失败: {e}", exc_info=True)


async def handle_damage_result(message: Dict[str, Any]):
    """处理损伤识别结果事件"""
    try:
        await broadcast_to_room("damage", message)
        await broadcast_to_room("monitoring", {
            "type": "damage_result",
            "data": message.get("data", {})
        })
    except Exception as e:
        logger.error(f"处理损伤结果失败: {e}", exc_info=True)


@app.on_event("startup")
async def startup():
    logger.info("启动告警与WebSocket服务...")
    init_thresholds()
    try:
        await redis_bus.connect()
        await redis_bus.subscribe(EventType.SENSOR_DATA_RECEIVED.value, handle_sensor_data)
        await redis_bus.subscribe(EventType.ALERT_TRIGGERED.value, handle_alert_triggered)
        await redis_bus.subscribe(EventType.SIMULATION_PROGRESS.value, handle_simulation_progress)
        await redis_bus.subscribe(EventType.SIMULATION_RESULT.value, handle_simulation_progress)
        await redis_bus.subscribe(EventType.DAMAGE_RESULT.value, handle_damage_result)
        logger.info("Redis订阅已建立")
    except Exception as e:
        logger.error(f"Redis连接失败: {e}")
    logger.info("告警与WebSocket服务启动完成")


@app.on_event("shutdown")
async def shutdown():
    logger.info("关闭告警与WebSocket服务...")
    for ws in active_connections.values():
        await ws.close()
    active_connections.clear()
    connection_rooms.clear()
    client_rooms.clear()
    await redis_bus.disconnect()
    logger.info("服务已关闭")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """通用WebSocket端点 - 支持动态订阅房间"""
    await websocket.accept()
    client_id = str(uuid.uuid4())
    active_connections[client_id] = websocket
    client_rooms[client_id] = []

    try:
        await websocket.send_text(json.dumps({
            "type": "connected",
            "client_id": client_id,
            "message": "连接成功"
        }))

        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                action = message.get("action")

                if action == "subscribe":
                    room = message.get("room")
                    if room:
                        if room not in connection_rooms:
                            connection_rooms[room] = set()
                        connection_rooms[room].add(client_id)
                        if room not in client_rooms[client_id]:
                            client_rooms[client_id].append(room)
                        await websocket.send_text(json.dumps({
                            "type": "subscribed",
                            "room": room
                        }))

                elif action == "unsubscribe":
                    room = message.get("room")
                    if room and room in connection_rooms:
                        connection_rooms[room].discard(client_id)
                        if room in client_rooms[client_id]:
                            client_rooms[client_id].remove(room)
                        await websocket.send_text(json.dumps({
                            "type": "unsubscribed",
                            "room": room
                        }))

                elif action == "get_rooms":
                    await websocket.send_text(json.dumps({
                        "type": "rooms",
                        "rooms": client_rooms.get(client_id, [])
                    }))

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        pass
    finally:
        if client_id in active_connections:
            del active_connections[client_id]
        for room in client_rooms.get(client_id, []):
            if room in connection_rooms:
                connection_rooms[room].discard(client_id)
        if client_id in client_rooms:
            del client_rooms[client_id]


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """告警专用WebSocket频道"""
    await websocket.accept()
    client_id = str(uuid.uuid4())
    active_connections[client_id] = websocket

    if "alerts" not in connection_rooms:
        connection_rooms["alerts"] = set()
    connection_rooms["alerts"].add(client_id)
    client_rooms[client_id] = ["alerts"]

    try:
        recent_data = recent_alerts[:20]
        await websocket.send_text(json.dumps({
            "type": "recent_alerts",
            "data": recent_data
        }, default=str))

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if client_id in active_connections:
            del active_connections[client_id]
        if "alerts" in connection_rooms:
            connection_rooms["alerts"].discard(client_id)
        if client_id in client_rooms:
            del client_rooms[client_id]


@app.websocket("/ws/monitoring")
async def websocket_monitoring(websocket: WebSocket):
    """实时监控专用WebSocket频道"""
    await websocket.accept()
    client_id = str(uuid.uuid4())
    active_connections[client_id] = websocket

    if "monitoring" not in connection_rooms:
        connection_rooms["monitoring"] = set()
    connection_rooms["monitoring"].add(client_id)
    client_rooms[client_id] = ["monitoring"]

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if client_id in active_connections:
            del active_connections[client_id]
        if "monitoring" in connection_rooms:
            connection_rooms["monitoring"].discard(client_id)
        if client_id in client_rooms:
            del client_rooms[client_id]


@app.get("/api/alerts", summary="获取告警列表")
async def get_alerts(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    floor: Optional[int] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    conditions = []
    if severity:
        conditions.append(Alert.severity == severity)
    if status:
        conditions.append(Alert.status == status)
    if floor:
        conditions.append(Alert.floor == floor)

    stmt = select(Alert).where(and_(*conditions)).order_by(
        Alert.triggered_at.desc()
    ).limit(limit)
    result = await db.execute(stmt)
    alerts = result.scalars().all()

    if not alerts:
        return recent_alerts[:limit]

    return alerts


@app.get("/api/alerts/{alert_id}", summary="获取告警详情")
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()

    if not alert:
        for a in recent_alerts:
            if a.get("alert_id") == alert_id:
                return a
        raise HTTPException(status_code=404, detail="告警不存在")

    return alert


@app.put("/api/alerts/{alert_id}/acknowledge", summary="确认告警")
async def acknowledge_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")

    alert.status = "acknowledged"
    await db.commit()
    return {"status": "success", "message": "告警已确认"}


@app.get("/api/thresholds", summary="获取告警阈值配置")
async def get_thresholds():
    return alert_thresholds_cache


@app.get("/api/statistics", summary="获取告警统计")
async def get_alert_statistics():
    total = len(recent_alerts)
    critical = sum(1 for a in recent_alerts if a.get("severity") == "critical")
    warning = sum(1 for a in recent_alerts if a.get("severity") == "warning")
    pending = sum(1 for a in recent_alerts if a.get("status") == "pending")

    return {
        "total_recent": total,
        "critical_count": critical,
        "warning_count": warning,
        "pending_count": pending,
        "active_connections": len(active_connections)
    }


@app.get("/health", summary="健康检查")
async def health_check():
    return {
        "service": "alarm_ws",
        "status": "running",
        "version": "2.0.0",
        "redis_connected": redis_bus._is_connected,
        "active_connections": len(active_connections),
        "rooms": list(connection_rooms.keys())
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
