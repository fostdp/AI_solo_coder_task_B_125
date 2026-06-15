"""
API Gateway Service
API网关服务 - 统一入口，反向代理各微服务，提供聚合API
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any
import httpx
import json

from common.redis_bus import get_redis_bus
from common.config_loader import ServiceConfig

config = ServiceConfig.from_env("api_gateway")
config.port = 8000

logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - API Gateway - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="应县木塔健康监测系统 - API网关",
    description="统一API入口，聚合各微服务接口",
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

SERVICE_URLS = {
    "dtu_receiver": "http://localhost:8001",
    "fea_simulator": "http://localhost:8002",
    "damage_detector": "http://localhost:8003",
    "alarm_ws": "http://localhost:8004",
}


@app.on_event("startup")
async def startup():
    logger.info("启动API网关服务...")
    try:
        await redis_bus.connect()
        logger.info("Redis消息总线连接成功")
    except Exception as e:
        logger.error(f"Redis连接失败: {e}")
    logger.info("API网关服务启动完成")


@app.on_event("shutdown")
async def shutdown():
    logger.info("关闭API网关服务...")
    await redis_bus.disconnect()
    logger.info("服务已关闭")


@app.get("/api/summary", summary="系统总览数据聚合")
async def get_system_summary():
    """聚合各服务的总览数据"""
    summary = {
        "system_name": "应县木塔健康监测系统",
        "version": "2.0.0",
        "architecture": "micro-services",
        "services": list(SERVICE_URLS.keys()),
        "sensor_data": {},
        "alerts": {},
        "damage": {},
        "simulation": {}
    }

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(f"{SERVICE_URLS['dtu_receiver']}/api/sensors/statistics")
            if resp.status_code == 200:
                summary["sensor_data"] = resp.json()
        except Exception as e:
            summary["sensor_data"] = {"error": str(e)}

        try:
            resp = await client.get(f"{SERVICE_URLS['alarm_ws']}/api/statistics")
            if resp.status_code == 200:
                summary["alerts"] = resp.json()
        except Exception as e:
            summary["alerts"] = {"error": str(e)}

        try:
            resp = await client.get(f"{SERVICE_URLS['damage_detector']}/api/model/info")
            if resp.status_code == 200:
                summary["damage"] = resp.json()
        except Exception as e:
            summary["damage"] = {"error": str(e)}

    return summary


@app.get("/api/sensors", summary="传感器列表")
async def proxy_sensors(request: Request):
    return await proxy_request("dtu_receiver", f"/api/sensors?{request.query_params}")


@app.get("/api/sensors/data", summary="传感器数据查询")
async def proxy_sensor_data(request: Request):
    return await proxy_request("dtu_receiver", f"/api/sensors/data?{request.query_params}")


@app.get("/api/sensors/realtime/{floor}", summary="楼层实时数据")
async def proxy_realtime(floor: int):
    return await proxy_request("dtu_receiver", f"/api/sensors/realtime/{floor}")


@app.get("/api/sensors/floors", summary="楼层信息")
async def proxy_floors():
    return await proxy_request("dtu_receiver", "/api/sensors/floors")


@app.post("/api/simulation/run", summary="提交仿真任务")
async def proxy_sim_run(request: Request):
    body = await request.json()
    return await proxy_request(
        "fea_simulator",
        "/api/simulation/run",
        method="POST",
        json_body=body
    )


@app.get("/api/simulation/{sim_id}", summary="仿真结果查询")
async def proxy_sim_result(sim_id: str):
    return await proxy_request("fea_simulator", f"/api/simulation/{sim_id}")


@app.get("/api/simulation/list", summary="仿真任务列表")
async def proxy_sim_list(request: Request):
    return await proxy_request("fea_simulator", f"/api/simulation/list?{request.query_params}")


@app.get("/api/modal-analysis/baseline", summary="基准模态参数")
async def proxy_modal_baseline():
    return await proxy_request("fea_simulator", "/api/modal-analysis/baseline")


@app.post("/api/damage/analyze", summary="提交损伤分析")
async def proxy_damage_analyze(request: Request):
    body = await request.json()
    return await proxy_request(
        "damage_detector",
        "/api/damage/analyze",
        method="POST",
        json_body=body
    )


@app.get("/api/damage/{analysis_id}", summary="损伤分析结果")
async def proxy_damage_result(analysis_id: str):
    return await proxy_request("damage_detector", f"/api/damage/{analysis_id}")


@app.get("/api/damage/list", summary="损伤分析列表")
async def proxy_damage_list(request: Request):
    return await proxy_request("damage_detector", f"/api/damage/list?{request.query_params}")


@app.get("/api/alerts", summary="告警列表")
async def proxy_alerts(request: Request):
    return await proxy_request("alarm_ws", f"/api/alerts?{request.query_params}")


@app.get("/api/alerts/{alert_id}", summary="告警详情")
async def proxy_alert_detail(alert_id: str):
    return await proxy_request("alarm_ws", f"/api/alerts/{alert_id}")


@app.get("/api/thresholds", summary="告警阈值")
async def proxy_thresholds():
    return await proxy_request("alarm_ws", "/api/thresholds")


async def proxy_request(
    service: str,
    path: str,
    method: str = "GET",
    json_body: Dict[str, Any] = None
):
    """转发请求到指定微服务"""
    base_url = SERVICE_URLS.get(service)
    if not base_url:
        raise HTTPException(status_code=503, detail=f"服务 {service} 未配置")

    url = f"{base_url}{path}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                resp = await client.get(url)
            elif method == "POST":
                resp = await client.post(url, json=json_body)
            else:
                raise HTTPException(status_code=405, detail="不支持的方法")

            return JSONResponse(
                status_code=resp.status_code,
                content=resp.json() if resp.content else {}
            )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"服务 {service} 不可用")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"代理请求失败: {str(e)}")


@app.get("/api/services/status", summary="各服务状态检查")
async def get_services_status():
    """检查所有微服务的运行状态"""
    statuses = {}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for service_name, url in SERVICE_URLS.items():
            try:
                resp = await client.get(f"{url}/health")
                if resp.status_code == 200:
                    statuses[service_name] = {
                        "status": "online",
                        "url": url,
                        "info": resp.json()
                    }
                else:
                    statuses[service_name] = {"status": "error", "url": url}
            except Exception as e:
                statuses[service_name] = {"status": "offline", "url": url, "error": str(e)}

    return statuses


@app.get("/health", summary="健康检查")
async def health_check():
    return {
        "service": "api_gateway",
        "status": "running",
        "version": "2.0.0",
        "redis_connected": redis_bus._is_connected,
        "registered_services": len(SERVICE_URLS)
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
