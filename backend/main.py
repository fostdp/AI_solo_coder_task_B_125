from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import json
import logging

from config import settings
from core.database import async_session, init_db
from api.sensor_routes import router as sensor_router
from api.simulation_routes import router as simulation_router
from api.damage_routes import router as damage_router
from api.alert_routes import router as alert_router
from api.auth_routes import router as auth_router
from alerts.websocket_manager import websocket_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("正在初始化数据库...")
    await init_db()
    logger.info("数据库初始化完成")
    
    logger.info("正在启动告警检查定时任务...")
    task = asyncio.create_task(periodic_alert_check())
    
    yield
    
    logger.info("正在关闭服务...")
    task.cancel()
    await websocket_manager.disconnect_all()
    logger.info("服务已关闭")


async def periodic_alert_check():
    while True:
        try:
            await asyncio.sleep(300)
            logger.info("执行定时告警检查...")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"定时告警检查出错: {e}")


app = FastAPI(
    title="应县木塔结构抗风抗震仿真与健康监测系统",
    description="基于有限元法和木材各向异性本构的木塔结构健康监测系统，支持风/地震动力响应仿真、神经网络损伤识别、实时告警推送",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(sensor_router)
app.include_router(simulation_router)
app.include_router(damage_router)
app.include_router(alert_router)


@app.get("/", summary="系统根路径")
async def root():
    return {
        "name": "应县木塔结构健康监测系统",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", summary="健康检查")
async def health_check():
    try:
        async with async_session() as db:
            await db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "websocket_connections": len(websocket_manager.active_connections)
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_id = await websocket_manager.connect(websocket)
    logger.info(f"WebSocket客户端连接: {client_id}")
    
    try:
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "message": "已连接到监测系统"
        })
        
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                action = message.get("action")
                room = message.get("room")
                
                if action == "subscribe" and room:
                    await websocket_manager.join_room(client_id, room)
                    await websocket.send_json({
                        "type": "subscribed",
                        "room": room,
                        "message": f"已订阅房间: {room}"
                    })
                elif action == "unsubscribe" and room:
                    await websocket_manager.leave_room(client_id, room)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "room": room,
                        "message": f"已取消订阅房间: {room}"
                    })
                elif action == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": message.get("timestamp")
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "未知的消息格式"
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "消息格式错误，需要JSON格式"
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket客户端断开: {client_id}")
        await websocket_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        await websocket_manager.disconnect(client_id)


@app.websocket("/ws/monitoring")
async def monitoring_websocket(websocket: WebSocket):
    await websocket.accept()
    client_id = await websocket_manager.connect(websocket)
    await websocket_manager.join_room(client_id, "monitoring")
    
    try:
        await websocket.send_json({
            "type": "connected",
            "room": "monitoring",
            "client_id": client_id,
            "message": "已连接到实时监控频道"
        })
        
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        await websocket_manager.leave_room(client_id, "monitoring")
        await websocket_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"监控WebSocket错误: {e}")
        await websocket_manager.leave_room(client_id, "monitoring")
        await websocket_manager.disconnect(client_id)


@app.websocket("/ws/alerts")
async def alerts_websocket(websocket: WebSocket):
    await websocket.accept()
    client_id = await websocket_manager.connect(websocket)
    await websocket_manager.join_room(client_id, "alerts")
    
    try:
        await websocket.send_json({
            "type": "connected",
            "room": "alerts",
            "client_id": client_id,
            "message": "已连接到告警推送频道"
        })
        
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        await websocket_manager.leave_room(client_id, "alerts")
        await websocket_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"告警WebSocket错误: {e}")
        await websocket_manager.leave_room(client_id, "alerts")
        await websocket_manager.disconnect(client_id)


@app.websocket("/ws/simulation")
async def simulation_websocket(websocket: WebSocket):
    await websocket.accept()
    client_id = await websocket_manager.connect(websocket)
    await websocket_manager.join_room(client_id, "simulation")
    
    try:
        await websocket.send_json({
            "type": "connected",
            "room": "simulation",
            "client_id": client_id,
            "message": "已连接到仿真进度频道"
        })
        
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        await websocket_manager.leave_room(client_id, "simulation")
        await websocket_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"仿真WebSocket错误: {e}")
        await websocket_manager.leave_room(client_id, "simulation")
        await websocket_manager.disconnect(client_id)


@app.websocket("/ws/damage")
async def damage_websocket(websocket: WebSocket):
    await websocket.accept()
    client_id = await websocket_manager.connect(websocket)
    await websocket_manager.join_room(client_id, "damage")
    
    try:
        await websocket.send_json({
            "type": "connected",
            "room": "damage",
            "client_id": client_id,
            "message": "已连接到损伤识别频道"
        })
        
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        await websocket_manager.leave_room(client_id, "damage")
        await websocket_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"损伤识别WebSocket错误: {e}")
        await websocket_manager.leave_room(client_id, "damage")
        await websocket_manager.disconnect(client_id)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "服务器内部错误",
            "message": str(exc) if settings.debug else "请联系系统管理员"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
