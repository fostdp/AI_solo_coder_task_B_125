from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import asyncio

from core.database import get_async_session
from core.models import DamageAnalysis, DamageResult, ModalParameter, SensorData, Sensor
from core.schemas import DamageAnalysisRequest, DamageResultOut, ModalParameterOut
from damage_detection.damage_service import DamageDetectionService
from alerts.websocket_manager import websocket_manager

router = APIRouter(prefix="/api/damage", tags=["损伤识别"])

damage_service = DamageDetectionService()


async def run_damage_analysis_background(
    db: AsyncSession,
    analysis_id: uuid.UUID,
    request: DamageAnalysisRequest
):
    try:
        stmt = select(DamageAnalysis).where(DamageAnalysis.id == analysis_id)
        result = await db.execute(stmt)
        analysis = result.scalar_one()
        
        await websocket_manager.broadcast_to_room("damage", {
            "type": "damage_update",
            "analysis_id": str(analysis_id),
            "status": "processing",
            "progress": 10,
            "message": "正在采集传感器数据..."
        })
        
        end_time = analysis.end_time
        start_time = end_time - timedelta(seconds=request.analysis_window)
        
        floors = [request.floor] if request.floor else [1, 2, 3, 4, 5]
        sensor_data_by_floor = {}
        
        for floor in floors:
            stmt_sensors = select(Sensor.id, Sensor.sensor_type).where(
                and_(
                    Sensor.floor_number == floor,
                    Sensor.sensor_type.in_(['acceleration_x', 'acceleration_y', 'displacement_x', 'displacement_y'])
                )
            )
            result_sensors = await db.execute(stmt_sensors)
            sensors = result_sensors.all()
            
            floor_data = {}
            for sensor_id, sensor_type in sensors:
                stmt_data = select(SensorData).where(
                    and_(
                        SensorData.sensor_id == sensor_id,
                        SensorData.time >= start_time,
                        SensorData.time <= end_time
                    )
                ).order_by(SensorData.time)
                result_data = await db.execute(stmt_data)
                data_points = result_data.scalars().all()
                
                if data_points:
                    floor_data[sensor_type] = {
                        "timestamps": [d.time.isoformat() for d in data_points],
                        "values": [d.value for d in data_points]
                    }
            
            sensor_data_by_floor[floor] = floor_data
        
        await websocket_manager.broadcast_to_room("damage", {
            "type": "damage_update",
            "analysis_id": str(analysis_id),
            "status": "processing",
            "progress": 40,
            "message": "正在进行模态参数识别..."
        })
        
        await asyncio.sleep(0.5)
        
        modal_params = damage_service.extract_modal_parameters(sensor_data_by_floor)
        
        for floor, params in modal_params.items():
            for i, freq in enumerate(params.get('natural_frequencies', [])):
                modal_param = ModalParameter(
                    floor_number=floor,
                    mode_order=i + 1,
                    natural_frequency=freq,
                    damping_ratio=params.get('damping_ratios', [0.02])[i] if i < len(params.get('damping_ratios', [])) else 0.02,
                    mode_shape=params.get('mode_shapes', [{}])[i] if i < len(params.get('mode_shapes', [])) else {},
                    is_baseline=False,
                    measured_at=end_time
                )
                db.add(modal_param)
        
        await db.commit()
        
        await websocket_manager.broadcast_to_room("damage", {
            "type": "damage_update",
            "analysis_id": str(analysis_id),
            "status": "processing",
            "progress": 70,
            "message": "正在进行损伤定位..."
        })
        
        await asyncio.sleep(0.5)
        
        damage_results = damage_service.detect_damage(modal_params)
        
        for floor, damages in damage_results.items():
            for damage in damages:
                damage_result = DamageResult(
                    analysis_id=analysis_id,
                    floor_number=floor,
                    element_id=damage.get('element_id', 0),
                    damage_index=damage.get('damage_index', 0.0),
                    natural_frequency=damage.get('natural_frequency'),
                    frequency_change=damage.get('frequency_change'),
                    confidence=damage.get('confidence', 0.0),
                    modal_parameters=damage.get('modal_parameters', {})
                )
                db.add(damage_result)
        
        analysis.status = "completed"
        analysis.completed_at = datetime.utcnow()
        await db.commit()
        
        await websocket_manager.broadcast_to_room("damage", {
            "type": "damage_complete",
            "analysis_id": str(analysis_id),
            "status": "completed",
            "progress": 100,
            "message": "损伤识别完成",
            "results": [
                {
                    "floor": floor,
                    "damages": damages
                }
                for floor, damages in damage_results.items()
            ]
        })
        
    except Exception as e:
        stmt = select(DamageAnalysis).where(DamageAnalysis.id == analysis_id)
        result = await db.execute(stmt)
        analysis = result.scalar_one()
        analysis.status = "failed"
        await db.commit()
        
        await websocket_manager.broadcast_to_room("damage", {
            "type": "damage_error",
            "analysis_id": str(analysis_id),
            "status": "failed",
            "error": str(e)
        })


@router.post("/analyze", summary="创建损伤识别分析任务")
async def create_damage_analysis(
    request: DamageAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session)
):
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(seconds=request.analysis_window)
    
    analysis = DamageAnalysis(
        status="pending",
        analysis_window=request.analysis_window,
        start_time=start_time,
        end_time=end_time
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    
    background_tasks.add_task(
        run_damage_analysis_background,
        db,
        analysis.id,
        request
    )
    
    await websocket_manager.broadcast_to_room("damage", {
        "type": "damage_created",
        "analysis_id": str(analysis.id),
        "status": "pending",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat()
    })
    
    return {
        "analysis_id": str(analysis.id),
        "status": "pending",
        "message": "损伤识别任务已提交，正在后台运行"
    }


@router.get("", summary="获取损伤分析列表")
async def get_damage_analyses(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(DamageAnalysis).order_by(DamageAnalysis.created_at.desc())
    
    if status:
        stmt = stmt.where(DamageAnalysis.status == status)
    
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    analyses = result.scalars().all()
    
    return [
        {
            "id": str(ana.id),
            "status": ana.status,
            "analysis_window": ana.analysis_window,
            "start_time": ana.start_time.isoformat(),
            "end_time": ana.end_time.isoformat(),
            "created_at": ana.created_at.isoformat(),
            "completed_at": ana.completed_at.isoformat() if ana.completed_at else None
        }
        for ana in analyses
    ]


@router.get("/{analysis_id}", summary="获取损伤分析详情")
async def get_damage_analysis(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(DamageAnalysis).where(DamageAnalysis.id == analysis_id)
    result = await db.execute(stmt)
    analysis = result.scalar_one_or_none()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="分析任务不存在")
    
    stmt_results = select(DamageResult).where(
        DamageResult.analysis_id == analysis_id
    ).order_by(DamageResult.floor_number, DamageResult.element_id)
    result_results = await db.execute(stmt_results)
    results = result_results.scalars().all()
    
    return {
        "id": str(analysis.id),
        "status": analysis.status,
        "analysis_window": analysis.analysis_window,
        "start_time": analysis.start_time.isoformat(),
        "end_time": analysis.end_time.isoformat(),
        "created_at": analysis.created_at.isoformat(),
        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
        "results": [
            {
                "floor_number": r.floor_number,
                "element_id": r.element_id,
                "damage_index": r.damage_index,
                "natural_frequency": r.natural_frequency,
                "frequency_change": r.frequency_change,
                "confidence": r.confidence
            }
            for r in results
        ]
    }


@router.get("/{analysis_id}/results", response_model=List[DamageResultOut], summary="获取损伤分析结果")
async def get_damage_results(
    analysis_id: uuid.UUID,
    min_damage_index: Optional[float] = None,
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(DamageResult).where(DamageResult.analysis_id == analysis_id)
    
    if min_damage_index is not None:
        stmt = stmt.where(DamageResult.damage_index >= min_damage_index)
    
    stmt = stmt.order_by(DamageResult.damage_index.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/modal-parameters", response_model=List[ModalParameterOut], summary="获取模态参数历史")
async def get_modal_parameters(
    floor: Optional[int] = None,
    is_baseline: Optional[bool] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(ModalParameter).order_by(ModalParameter.measured_at.desc())
    
    if floor:
        stmt = stmt.where(ModalParameter.floor_number == floor)
    if is_baseline is not None:
        stmt = stmt.where(ModalParameter.is_baseline == is_baseline)
    if start_time:
        stmt = stmt.where(ModalParameter.measured_at >= start_time)
    if end_time:
        stmt = stmt.where(ModalParameter.measured_at <= end_time)
    
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/modal-parameters/baseline", summary="设置基准模态参数")
async def set_baseline_modal_parameters(
    floor: int,
    natural_frequencies: List[float],
    mode_shapes: Optional[List[dict]] = None,
    db: AsyncSession = Depends(get_async_session)
):
    try:
        for i, freq in enumerate(natural_frequencies):
            modal_param = ModalParameter(
                floor_number=floor,
                mode_order=i + 1,
                natural_frequency=freq,
                mode_shape=mode_shapes[i] if mode_shapes and i < len(mode_shapes) else {},
                is_baseline=True,
                description=f"第{floor}层基准模态参数 - 第{i+1}阶"
            )
            db.add(modal_param)
        
        await db.commit()
        
        return {
            "status": "success",
            "message": f"第{floor}层基准模态参数已设置",
            "natural_frequencies": natural_frequencies
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置基准参数失败: {str(e)}")


@router.get("/health/assessment", summary="获取结构健康评估")
async def get_health_assessment(
    db: AsyncSession = Depends(get_async_session)
):
    stmt_latest = select(DamageAnalysis).where(
        DamageAnalysis.status == "completed"
    ).order_by(DamageAnalysis.created_at.desc()).limit(1)
    result_latest = await db.execute(stmt_latest)
    latest_analysis = result_latest.scalar_one_or_none()
    
    if not latest_analysis:
        return {
            "health_status": "unknown",
            "overall_health_index": 1.0,
            "message": "暂无损伤分析数据"
        }
    
    stmt_results = select(DamageResult).where(
        DamageResult.analysis_id == latest_analysis.id
    )
    result_results = await db.execute(stmt_results)
    results = result_results.scalars().all()
    
    if not results:
        return {
            "health_status": "good",
            "overall_health_index": 1.0,
            "message": "未检测到损伤"
        }
    
    max_damage = max(r.damage_index for r in results)
    avg_damage = sum(r.damage_index for r in results) / len(results)
    
    if max_damage > 0.5:
        health_status = "critical"
    elif max_damage > 0.2:
        health_status = "warning"
    elif max_damage > 0.05:
        health_status = "attention"
    else:
        health_status = "good"
    
    overall_health_index = 1.0 - avg_damage
    
    damaged_floors = list(set(r.floor_number for r in results if r.damage_index > 0.1))
    
    return {
        "health_status": health_status,
        "overall_health_index": round(overall_health_index, 4),
        "max_damage_index": round(max_damage, 4),
        "avg_damage_index": round(avg_damage, 4),
        "damaged_floors": damaged_floors,
        "last_analysis_time": latest_analysis.completed_at.isoformat() if latest_analysis.completed_at else None,
        "total_damage_locations": len([r for r in results if r.damage_index > 0.05]),
        "critical_locations": [
            {
                "floor": r.floor_number,
                "element_id": r.element_id,
                "damage_index": round(r.damage_index, 4),
                "confidence": round(r.confidence, 4)
            }
            for r in results if r.damage_index > 0.3
        ]
    }
