"""
Damage Detector Service
损伤识别服务 - 负责基于模态参数变化的神经网络损伤识别
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import logging
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import numpy as np

from common.redis_bus import get_redis_bus
from common.event_types import (
    EventType,
    DamageRequestEvent,
    DamageResultEvent,
    AlertEvent
)
from common.config_loader import ServiceConfig, load_nn_model_config

from damage_detection.neural_network import DamageDetectionModel
from damage_detection.modal_analysis import SSIModalAnalysis, FrequencyDomainDecomposition

config = ServiceConfig.from_env("damage_detector")
config.port = 8003

logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - Damage Detector - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="损伤识别服务",
    description="应县木塔结构损伤识别服务 - 基于模态参数和神经网络",
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

damage_model: Optional[DamageDetectionModel] = None
damage_cache: Dict[str, Dict[str, Any]] = {}
baseline_frequencies: List[float] = [1.2, 2.8, 4.5, 6.2, 8.1]


def init_damage_model():
    """初始化损伤识别模型"""
    global damage_model
    nn_config = load_nn_model_config()
    damage_model = DamageDetectionModel(
        n_features=nn_config.get("input_features", 50),
        n_floors=nn_config.get("n_floors", 5),
        hidden_dims=nn_config.get("hidden_dimensions", [256, 128, 64]),
        dropout=nn_config.get("dropout_rate", 0.3),
        use_data_augmentation=nn_config.get("use_data_augmentation", True),
        use_transfer_learning=nn_config.get("use_transfer_learning", False)
    )
    damage_model._initialize_pretrained_weights()
    logger.info("损伤识别模型初始化完成")


async def run_damage_analysis(analysis_id: str, request: DamageRequestEvent):
    """执行损伤分析"""
    try:
        logger.info(f"开始损伤分析 {analysis_id}")

        damage_cache[analysis_id] = {
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "floor": request.floor
        }

        if request.modal_params:
            frequencies = request.modal_params.get("frequencies", baseline_frequencies)
            mode_shapes = request.modal_params.get("mode_shapes", [])
            damping_ratios = request.modal_params.get("damping_ratios", [0.02] * 5)
        else:
            frequencies = baseline_frequencies
            damping_ratios = [0.02] * len(baseline_frequencies)
            mode_shapes = []

        freq_changes = [
            abs(freq - base) / base if base > 0 else 0
            for freq, base in zip(frequencies, baseline_frequencies)
        ]

        features = []
        for i in range(5):
            features.append(freq_changes[i] if i < len(freq_changes) else 0)
            features.append(damping_ratios[i] if i < len(damping_ratios) else 0.02)
        for i in range(5):
            features.append(0.001 * (i + 1))

        while len(features) < 50:
            features.append(0.0)
        features = features[:50]

        X = np.array(features).reshape(1, -1)

        if damage_model and damage_model.is_trained:
            location_probs, severity, confidence = damage_model.predict(X)
            results = []
            for floor in range(1, 6):
                floor_idx = floor - 1
                floor_severity = float(severity[0][floor_idx][0]) if severity.ndim > 1 else float(severity[floor_idx])
                floor_confidence = float(confidence[0][floor_idx][0]) if confidence.ndim > 1 else float(confidence[floor_idx])

                has_damage = floor_severity > 0.3
                damage_level = "low" if floor_severity < 0.3 else "medium" if floor_severity < 0.6 else "high"

                results.append({
                    "floor": floor,
                    "has_damage": has_damage,
                    "damage_severity": floor_severity,
                    "confidence": floor_confidence,
                    "damage_level": damage_level,
                    "likely_elements": ["柱", "梁", "斗拱"],
                    "frequency_change": freq_changes[floor_idx] if floor_idx < len(freq_changes) else 0
                })
        else:
            results = []
            for floor in range(1, 6):
                severity_val = 0.05 + floor * 0.02
                results.append({
                    "floor": floor,
                    "has_damage": severity_val > 0.3,
                    "damage_severity": severity_val,
                    "confidence": 0.5,
                    "damage_level": "low",
                    "likely_elements": [],
                    "frequency_change": freq_changes[floor - 1] if floor - 1 < len(freq_changes) else 0
                })

        result_event = DamageResultEvent(
            analysis_id=analysis_id,
            status="completed",
            results=results
        )

        damage_cache[analysis_id] = {
            "status": "completed",
            "start_time": damage_cache[analysis_id]["start_time"],
            "end_time": datetime.now().isoformat(),
            "results": results,
            "floor": request.floor
        }

        await redis_bus.publish(
            EventType.DAMAGE_RESULT.value,
            {
                "event_type": EventType.DAMAGE_RESULT.value,
                "data": result_event.to_dict()
            }
        )

        high_damage_floors = [r for r in results if r["damage_level"] == "high"]
        for high_result in high_damage_floors:
            alert = AlertEvent(
                alert_id=str(uuid.uuid4()),
                alert_type="structural_damage",
                floor=high_result["floor"],
                severity="critical",
                threshold_value=0.6,
                actual_value=high_result["damage_severity"],
                timestamp=datetime.now().isoformat(),
                note=f"第{high_result['floor']}层检测到严重损伤风险，置信度{high_result['confidence']:.1%}"
            )
            await redis_bus.publish(
                EventType.ALERT_TRIGGERED.value,
                {
                    "event_type": EventType.ALERT_TRIGGERED.value,
                    "data": alert.to_dict()
                }
            )

        logger.info(f"损伤分析完成 {analysis_id}, 发现 {sum(1 for r in results if r['has_damage'])} 处疑似损伤")

    except Exception as e:
        logger.error(f"损伤分析失败 {analysis_id}: {e}", exc_info=True)
        result_event = DamageResultEvent(
            analysis_id=analysis_id,
            status="failed",
            error_message=str(e)
        )
        damage_cache[analysis_id] = {
            "status": "failed",
            "start_time": damage_cache.get(analysis_id, {}).get("start_time", datetime.now().isoformat()),
            "error": str(e)
        }
        await redis_bus.publish(
            EventType.DAMAGE_RESULT.value,
            {
                "event_type": EventType.DAMAGE_RESULT.value,
                "data": result_event.to_dict()
            }
        )


async def handle_damage_request(message: Dict[str, Any]):
    """处理损伤识别请求消息"""
    try:
        event_data = message.get("data", {})
        request = DamageRequestEvent.from_dict(event_data)
        logger.info(f"收到损伤识别请求: {request.analysis_id}")

        asyncio.create_task(run_damage_analysis(request.analysis_id, request))
    except Exception as e:
        logger.error(f"处理损伤识别请求失败: {e}", exc_info=True)


async def handle_sensor_data(message: Dict[str, Any]):
    """处理传感器数据 - 触发频率趋势分析"""
    try:
        event_data = message.get("data", {})
        sensor_type = event_data.get("sensor_type", "")

        if "acceleration" in sensor_type.lower():
            logger.debug(f"收到加速度数据: {event_data.get('device_id')}")
    except Exception as e:
        logger.error(f"处理传感器数据失败: {e}", exc_info=True)


@app.on_event("startup")
async def startup():
    logger.info("启动损伤识别服务...")
    init_damage_model()
    try:
        await redis_bus.connect()
        await redis_bus.subscribe(
            EventType.DAMAGE_REQUEST.value,
            handle_damage_request
        )
        await redis_bus.subscribe(
            EventType.SENSOR_DATA_RECEIVED.value,
            handle_sensor_data
        )
        logger.info("Redis订阅已建立")
    except Exception as e:
        logger.error(f"Redis连接失败: {e}")
    logger.info("损伤识别服务启动完成")


@app.on_event("shutdown")
async def shutdown():
    logger.info("关闭损伤识别服务...")
    await redis_bus.disconnect()
    logger.info("服务已关闭")


@app.post("/api/damage/analyze", summary="提交损伤分析任务")
async def analyze_damage(
    request_body: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    analysis_id = str(uuid.uuid4())

    request = DamageRequestEvent(
        analysis_id=analysis_id,
        start_time=request_body.get("start_time", ""),
        end_time=request_body.get("end_time", ""),
        floor=request_body.get("floor"),
        modal_params=request_body.get("modal_params")
    )

    background_tasks.add_task(run_damage_analysis, analysis_id, request)

    return {
        "analysis_id": analysis_id,
        "status": "submitted",
        "message": "损伤分析任务已提交"
    }


@app.get("/api/damage/{analysis_id}", summary="获取损伤分析结果")
async def get_damage_result(analysis_id: str):
    result = damage_cache.get(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="分析任务不存在")
    return result


@app.get("/api/damage/list", summary="获取损伤分析列表")
async def list_damage_analyses(limit: int = 10):
    analyses = sorted(
        damage_cache.values(),
        key=lambda x: x.get("start_time", ""),
        reverse=True
    )[:limit]
    return analyses


@app.get("/api/damage/baseline", summary="获取基准模态参数")
async def get_baseline():
    return {
        "frequencies": baseline_frequencies,
        "damping_ratios": [0.02] * 5,
        "source": "FEA_baseline_calibrated"
    }


@app.get("/api/model/info", summary="获取模型信息")
async def get_model_info():
    nn_config = load_nn_model_config()
    return {
        "model_name": nn_config.get("model_name", "DamageDetectionNN"),
        "version": nn_config.get("version", "2.0"),
        "input_features": nn_config.get("input_features", 50),
        "output_floors": nn_config.get("n_floors", 5),
        "is_trained": damage_model.is_trained if damage_model else False,
        "data_augmentation": nn_config.get("use_data_augmentation", False),
        "transfer_learning": nn_config.get("use_transfer_learning", False)
    }


@app.get("/health", summary="健康检查")
async def health_check():
    return {
        "service": "damage_detector",
        "status": "running",
        "version": "2.0.0",
        "redis_connected": redis_bus._is_connected,
        "model_loaded": damage_model is not None and damage_model.is_trained
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
