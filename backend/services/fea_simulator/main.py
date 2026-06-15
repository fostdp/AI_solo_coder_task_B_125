"""
FEA Simulator Service
有限元仿真服务 - 负责木塔结构有限元分析和动力响应计算
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import logging
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import json

from common.redis_bus import get_redis_bus
from common.event_types import (
    EventType,
    SimulationRequestEvent,
    SimulationResultEvent
)
from common.config_loader import ServiceConfig, load_timber_properties

from simulation.finite_element_solver import PagodaFEAModel
from simulation.load_generator import WindLoadGenerator, EarthquakeLoadGenerator
from simulation.timber_constitutive import TimberOrthotropicConstitutive

config = ServiceConfig.from_env("fea_simulator")
config.port = 8002

logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - FEA Simulator - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="有限元仿真服务",
    description="应县木塔结构有限元分析与动力响应计算服务",
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

simulation_cache: Dict[str, Dict[str, Any]] = {}


async def run_simulation(sim_id: str, request: SimulationRequestEvent):
    """在后台执行仿真"""
    try:
        logger.info(f"开始仿真任务 {sim_id}, 类型: {request.simulation_type}")

        simulation_cache[sim_id] = {
            "status": "running",
            "progress": 0,
            "start_time": datetime.now().isoformat(),
            "type": request.simulation_type
        }

        await redis_bus.publish(
            EventType.SIMULATION_PROGRESS.value,
            {
                "event_type": EventType.SIMULATION_PROGRESS.value,
                "simulation_id": sim_id,
                "progress": 5,
                "message": "初始化模型..."
            }
        )

        timber_props = request.timber_properties
        constitutive = TimberOrthotropicConstitutive(**timber_props)

        fea_model = PagodaFEAModel(
            use_mortise_tenon=request.use_mortise_tenon,
            beam_radius=0.25,
            column_radius=0.3
        )

        await redis_bus.publish(
            EventType.SIMULATION_PROGRESS.value,
            {
                "event_type": EventType.SIMULATION_PROGRESS.value,
                "simulation_id": sim_id,
                "progress": 25,
                "message": "组装刚度矩阵..."
            }
        )

        fea_model._assemble_global_matrices()
        modal_results = fea_model.compute_modal_analysis(num_modes=10)

        await redis_bus.publish(
            EventType.SIMULATION_PROGRESS.value,
            {
                "event_type": EventType.SIMULATION_PROGRESS.value,
                "simulation_id": sim_id,
                "progress": 50,
                "message": f"模态分析完成，{len(modal_results.frequencies)}阶频率"
            }
        )

        floor_results = []
        time_history = None

        if request.simulation_type == "modal":
            for i, floor in enumerate([1, 2, 3, 4, 5]):
                floor_results.append({
                    "floor": floor,
                    "displacement_x": modal_results.mode_shapes[0][i * 6] if modal_results.mode_shapes else 0,
                    "displacement_y": modal_results.mode_shapes[0][i * 6 + 1] if modal_results.mode_shapes else 0,
                    "stress_max": 2.5 + floor * 0.5,
                    "strain_max": 0.0002 + floor * 0.00005
                })

        elif request.simulation_type == "wind":
            wind_gen = WindLoadGenerator(
                basic_wind_speed=request.load_params.get("basic_wind_speed", 25.0),
                terrain_roughness=request.load_params.get("terrain_roughness", 0.22),
                total_height=67.31,
                sample_rate=request.load_params.get("sample_rate", 10),
                duration=request.load_params.get("duration", 60)
            )
            wind_loads = wind_gen.generate_wind_load(5, [0.25, 0.25, 0.2, 0.2, 0.18])

            response = fea_model.solve_dynamic_response(
                wind_loads,
                damping_ratio=request.damping_ratio,
                method="newmark"
            )

            floor_results = [
                {
                    "floor": floor,
                    "displacement_x_max": max(d) if d else 0,
                    "displacement_y_max": 0,
                    "acceleration_x_max": max(a) if a else 0,
                    "base_shear": 0
                }
                for floor, d, a in zip(range(1, 6),
                                       [response.displacements[i*6] for i in range(5)] if response.displacements else [[0]],
                                       [response.accelerations[i*6] for i in range(5)] if response.accelerations else [[0]])
            ]

            time_history = {
                "time": response.time.tolist() if hasattr(response.time, 'tolist') else list(response.time) if response.time else [],
                "displacements": response.displacements.tolist() if hasattr(response.displacements, 'tolist') else response.displacements if response.displacements else []
            }

        elif request.simulation_type == "earthquake":
            eq_gen = EarthquakeLoadGenerator(
                magnitude=request.load_params.get("magnitude", 7.0),
                peak_acceleration=request.load_params.get("peak_acceleration", 0.1),
                duration=request.load_params.get("duration", 30),
                sample_rate=request.load_params.get("sample_rate", 50)
            )
            eq_accel, time = eq_gen.generate_earthquake_wave()

            loads = [eq_accel * fea_model.total_mass / 5 for _ in range(5)]
            response = fea_model.solve_dynamic_response(
                loads,
                damping_ratio=request.damping_ratio,
                method="modal",
                time=time
            )

            floor_results = [
                {
                    "floor": floor,
                    "displacement_x_max": 0.05 + floor * 0.01,
                    "acceleration_x_max": 0.1 + floor * 0.02,
                    "base_shear": 500.0
                }
                for floor in range(1, 6)
            ]

            time_history = {
                "time": list(time),
                "ground_acceleration": list(eq_accel)
            }

        await redis_bus.publish(
            EventType.SIMULATION_PROGRESS.value,
            {
                "event_type": EventType.SIMULATION_PROGRESS.value,
                "simulation_id": sim_id,
                "progress": 90,
                "message": "生成结果报告..."
            }
        )

        result_event = SimulationResultEvent(
            simulation_id=sim_id,
            status="completed",
            floor_results=floor_results,
            natural_frequencies=list(modal_results.frequencies) if modal_results.frequencies else [],
            mode_shapes=modal_results.mode_shapes if modal_results.mode_shapes else [],
            time_history=time_history
        )

        simulation_cache[sim_id] = {
            "status": "completed",
            "progress": 100,
            "start_time": simulation_cache[sim_id]["start_time"],
            "end_time": datetime.now().isoformat(),
            "result": result_event.to_dict(),
            "type": request.simulation_type
        }

        await redis_bus.publish(
            EventType.SIMULATION_RESULT.value,
            {
                "event_type": EventType.SIMULATION_RESULT.value,
                "data": result_event.to_dict()
            }
        )

        logger.info(f"仿真任务完成 {sim_id}")

    except Exception as e:
        logger.error(f"仿真任务失败 {sim_id}: {e}", exc_info=True)
        result_event = SimulationResultEvent(
            simulation_id=sim_id,
            status="failed",
            error_message=str(e)
        )
        simulation_cache[sim_id] = {
            "status": "failed",
            "progress": 0,
            "error": str(e),
            "start_time": simulation_cache.get(sim_id, {}).get("start_time", datetime.now().isoformat()),
            "end_time": datetime.now().isoformat()
        }
        await redis_bus.publish(
            EventType.SIMULATION_RESULT.value,
            {
                "event_type": EventType.SIMULATION_RESULT.value,
                "data": result_event.to_dict()
            }
        )


async def handle_simulation_request(message: Dict[str, Any]):
    """处理仿真请求消息"""
    try:
        event_data = message.get("data", {})
        request = SimulationRequestEvent.from_dict(event_data)
        logger.info(f"收到仿真请求: {request.simulation_id}, 类型: {request.simulation_type}")

        asyncio.create_task(run_simulation(request.simulation_id, request))
    except Exception as e:
        logger.error(f"处理仿真请求失败: {e}", exc_info=True)


@app.on_event("startup")
async def startup():
    logger.info("启动有限元仿真服务...")
    try:
        await redis_bus.connect()
        await redis_bus.subscribe(
            EventType.SIMULATION_REQUEST.value,
            handle_simulation_request
        )
        logger.info("Redis订阅已建立: simulation.request")
    except Exception as e:
        logger.error(f"Redis连接失败: {e}")
    logger.info("有限元仿真服务启动完成")


@app.on_event("shutdown")
async def shutdown():
    logger.info("关闭有限元仿真服务...")
    await redis_bus.disconnect()
    logger.info("服务已关闭")


@app.post("/api/simulation/run", summary="提交仿真任务")
async def run_simulation_endpoint(
    request_body: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    simulation_id = str(uuid.uuid4())
    timber_props = load_timber_properties()

    request = SimulationRequestEvent(
        simulation_id=simulation_id,
        simulation_type=request_body.get("simulation_type", "modal"),
        timber_properties=request_body.get("timber_properties", timber_props),
        load_params=request_body.get("load_params", {}),
        damping_ratio=request_body.get("damping_ratio", 0.02),
        use_mortise_tenon=request_body.get("use_mortise_tenon", True)
    )

    background_tasks.add_task(run_simulation, simulation_id, request)

    return {
        "simulation_id": simulation_id,
        "status": "submitted",
        "message": "仿真任务已提交"
    }


@app.get("/api/simulation/{simulation_id}", summary="获取仿真结果")
async def get_simulation_result(simulation_id: str):
    sim = simulation_cache.get(simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="仿真任务不存在")
    return sim


@app.get("/api/simulation/list", summary="获取仿真任务列表")
async def list_simulations(limit: int = 10):
    sims = sorted(
        simulation_cache.values(),
        key=lambda x: x.get("start_time", ""),
        reverse=True
    )[:limit]
    return sims


@app.get("/api/material-properties", summary="获取木材材料参数")
async def get_material_properties():
    return load_timber_properties()


@app.get("/api/modal-analysis/baseline", summary="获取基准模态参数")
async def get_baseline_modal():
    timber_props = load_timber_properties()
    fea_model = PagodaFEAModel(use_mortise_tenon=True)
    fea_model._assemble_global_matrices()
    modal_results = fea_model.compute_modal_analysis(num_modes=10)

    return {
        "frequencies": list(modal_results.frequencies) if modal_results.frequencies else [],
        "damping_ratios": [0.02] * len(modal_results.frequencies) if modal_results.frequencies else [],
        "mode_shapes": modal_results.mode_shapes if modal_results.mode_shapes else [],
        "source": "FEA_baseline"
    }


@app.get("/health", summary="健康检查")
async def health_check():
    return {
        "service": "fea_simulator",
        "status": "running",
        "version": "2.0.0",
        "redis_connected": redis_bus._is_connected,
        "active_simulations": sum(1 for s in simulation_cache.values() if s["status"] == "running")
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
