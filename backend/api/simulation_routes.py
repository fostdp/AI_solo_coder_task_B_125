from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime
import uuid
import asyncio

from core.database import get_async_session
from core.models import Simulation, SimulationResult
from core.schemas import SimulationConfig, SimulationResultOut
from simulation.simulation_service import SimulationService
from alerts.websocket_manager import websocket_manager

router = APIRouter(prefix="/api/simulation", tags=["结构仿真"])

simulation_service = SimulationService()


async def run_simulation_background(
    db: AsyncSession,
    simulation_id: uuid.UUID,
    config: SimulationConfig
):
    try:
        stmt = select(Simulation).where(Simulation.id == simulation_id)
        result = await db.execute(stmt)
        simulation = result.scalar_one()
        
        simulation.status = "running"
        simulation.started_at = datetime.utcnow()
        await db.commit()
        
        await websocket_manager.broadcast_to_room("simulation", {
            "type": "simulation_update",
            "simulation_id": str(simulation_id),
            "status": "running",
            "progress": 10,
            "message": "正在构建有限元模型..."
        })
        
        await asyncio.sleep(0.5)
        
        results = simulation_service.run_structural_simulation(config)
        
        await websocket_manager.broadcast_to_room("simulation", {
            "type": "simulation_update",
            "simulation_id": str(simulation_id),
            "status": "processing",
            "progress": 50,
            "message": "正在计算动力响应..."
        })
        
        await asyncio.sleep(0.5)
        
        for floor_result in results.get('floor_results', []):
            sim_result = SimulationResult(
                simulation_id=simulation_id,
                floor_number=floor_result.get('floor_number'),
                max_displacement=floor_result.get('max_displacement_mm'),
                max_stress=floor_result.get('max_stress_mpa'),
                max_acceleration=floor_result.get('max_acceleration_g'),
                natural_frequencies=results.get('natural_frequencies'),
                time_history_data=floor_result.get('time_history_data')
            )
            db.add(sim_result)
        
        simulation.status = "completed"
        simulation.completed_at = datetime.utcnow()
        await db.commit()
        
        await websocket_manager.broadcast_to_room("simulation", {
            "type": "simulation_complete",
            "simulation_id": str(simulation_id),
            "status": "completed",
            "progress": 100,
            "message": "仿真计算完成",
            "results": {
                "natural_frequencies": results.get('natural_frequencies'),
                "floor_results": results.get('floor_results')
            }
        })
        
    except Exception as e:
        stmt = select(Simulation).where(Simulation.id == simulation_id)
        result = await db.execute(stmt)
        simulation = result.scalar_one()
        simulation.status = "failed"
        await db.commit()
        
        await websocket_manager.broadcast_to_room("simulation", {
            "type": "simulation_error",
            "simulation_id": str(simulation_id),
            "status": "failed",
            "error": str(e)
        })


@router.post("/run", summary="创建并运行结构仿真")
async def run_simulation(
    config: SimulationConfig,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session)
):
    simulation = Simulation(
        simulation_type=config.simulation_type,
        config=config.model_dump(),
        status="pending"
    )
    db.add(simulation)
    await db.commit()
    await db.refresh(simulation)
    
    background_tasks.add_task(
        run_simulation_background,
        db,
        simulation.id,
        config
    )
    
    await websocket_manager.broadcast_to_room("simulation", {
        "type": "simulation_created",
        "simulation_id": str(simulation.id),
        "status": "pending",
        "simulation_type": config.simulation_type
    })
    
    return {
        "simulation_id": str(simulation.id),
        "status": "pending",
        "message": "仿真任务已提交，正在后台运行"
    }


@router.get("", summary="获取仿真列表")
async def get_simulations(
    status: Optional[str] = None,
    simulation_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(Simulation).order_by(Simulation.created_at.desc())
    
    if status:
        stmt = stmt.where(Simulation.status == status)
    if simulation_type:
        stmt = stmt.where(Simulation.simulation_type == simulation_type)
    
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    simulations = result.scalars().all()
    
    return [
        {
            "id": str(sim.id),
            "simulation_type": sim.simulation_type,
            "status": sim.status,
            "created_at": sim.created_at.isoformat(),
            "started_at": sim.started_at.isoformat() if sim.started_at else None,
            "completed_at": sim.completed_at.isoformat() if sim.completed_at else None
        }
        for sim in simulations
    ]


@router.get("/{simulation_id}", summary="获取仿真详情")
async def get_simulation(
    simulation_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(Simulation).where(Simulation.id == simulation_id)
    result = await db.execute(stmt)
    simulation = result.scalar_one_or_none()
    
    if not simulation:
        raise HTTPException(status_code=404, detail="仿真任务不存在")
    
    stmt_results = select(SimulationResult).where(
        SimulationResult.simulation_id == simulation_id
    ).order_by(SimulationResult.floor_number)
    result_results = await db.execute(stmt_results)
    results = result_results.scalars().all()
    
    return {
        "id": str(simulation.id),
        "simulation_type": simulation.simulation_type,
        "config": simulation.config,
        "status": simulation.status,
        "created_at": simulation.created_at.isoformat(),
        "started_at": simulation.started_at.isoformat() if simulation.started_at else None,
        "completed_at": simulation.completed_at.isoformat() if simulation.completed_at else None,
        "results": [
            {
                "floor_number": r.floor_number,
                "max_displacement_mm": r.max_displacement,
                "max_stress_mpa": r.max_stress,
                "max_acceleration_g": r.max_acceleration,
                "natural_frequencies": r.natural_frequencies,
                "time_history_data": r.time_history_data
            }
            for r in results
        ]
    }


@router.get("/{simulation_id}/results", response_model=List[SimulationResultOut], summary="获取仿真结果")
async def get_simulation_results(
    simulation_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(SimulationResult).where(
        SimulationResult.simulation_id == simulation_id
    ).order_by(SimulationResult.floor_number)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/model/info", summary="获取木塔有限元模型信息")
async def get_model_info():
    info = simulation_service.get_model_info()
    return info


@router.post("/modal-analysis", summary="执行模态分析")
async def run_modal_analysis(
    config: SimulationConfig,
    db: AsyncSession = Depends(get_async_session)
):
    try:
        result = simulation_service.run_modal_analysis(config)
        return {
            "status": "success",
            "natural_frequencies": result.get('natural_frequencies'),
            "mode_shapes": result.get('mode_shapes'),
            "damping_ratios": result.get('damping_ratios')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"模态分析失败: {str(e)}")
