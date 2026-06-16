from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from simulation.dynasty_comparison import DynastyComparisonEngine
from simulation.mortise_tenon import MortiseTenonSimulator
from simulation.collapse_simulator import CollapseSimulator
from simulation.virtual_experience import VirtualExperienceService

router = APIRouter(prefix="/api/new", tags=["新功能扩展"])

dynasty_engine = DynastyComparisonEngine()
mortise_simulator = MortiseTenonSimulator()
collapse_simulator = CollapseSimulator()
virtual_service = VirtualExperienceService()

@router.get("/dynasty/pagodas", summary="获取所有朝代木塔模型列表")
async def list_pagodas():
    return {"pagodas": dynasty_engine.list_pagodas()}

@router.get("/dynasty/pagoda/{pagoda_id}", summary="获取单个木塔详细参数")
async def get_pagoda(pagoda_id: str):
    try:
        m = dynasty_engine.get_pagoda_model(pagoda_id)
        return {
            "id": pagoda_id,
            "name": m.name,
            "dynasty": m.dynasty,
            "country": m.country,
            "height": m.height,
            "floor_count": m.floor_count,
            "structural_type": m.structural_type,
            "floor_heights": m.floor_heights,
            "floor_diameters": m.floor_diameters,
            "inner_diameters": m.inner_diameters,
            "wall_thickness": m.wall_thickness,
            "timber_properties": m.timber_properties,
            "joint_properties": m.joint_properties,
            "seismic_philosophy": m.seismic_philosophy,
            "shinbashira": m.shinbashira,
            "shinbashira_diameter": m.shinbashira_diameter
        }
    except ValueError:
        raise HTTPException(status_code=404, detail=f"木塔模型 {pagoda_id} 不存在")

@router.get("/dynasty/compare", summary="生成两座木塔对比报告")
async def compare_pagodas(a: str = "yingxian", b: str = "gojunoto"):
    try:
        report = dynasty_engine.generate_comparison_report(a, b)
        return {"status": "success", "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dynasty/frequency_compare", summary="对比固有频率")
async def frequency_compare(a: str = "yingxian", b: str = "gojunoto"):
    return dynasty_engine.compare_natural_frequencies(a, b)

@router.get("/dynasty/wind_compare", summary="对比风振位移")
async def wind_compare(a: str = "yingxian", b: str = "gojunoto", wind_speed: float = 25.0):
    return dynasty_engine.compare_displacement_under_wind(a, b, wind_speed)

@router.get("/mortise/types", summary="获取所有榫卯类型")
async def list_mortise_types():
    return {"joint_types": mortise_simulator.list_joint_types()}

@router.get("/mortise/type/{joint_id}", summary="获取单个榫卯类型详细参数")
async def get_mortise_type(joint_id: str):
    try:
        props = mortise_simulator.get_joint_type(joint_id)
        return {
            "id": joint_id,
            "name": props.name,
            "chinese_name": props.chinese_name,
            "category": props.category,
            "elastic_stiffness": props.elastic_stiffness,
            "yield_moment": props.yield_moment,
            "ultimate_moment": props.ultimate_moment,
            "yield_rotation": props.yield_rotation,
            "ultimate_rotation": props.ultimate_rotation,
            "damping_ratio": props.damping_ratio,
            "pinching_factor": props.pinching_factor,
            "model_type": props.model_type,
            "gap": props.gap,
            "torsional_stiffness": props.torsional_stiffness,
            "vertical_load_effect": props.vertical_load_effect,
            "ductility_factor": props.ultimate_rotation / props.yield_rotation
        }
    except ValueError:
        raise HTTPException(status_code=404, detail=f"榫卯类型 {joint_id} 不存在")

class CyclicLoadingRequest(BaseModel):
    joint_type_id: str = "straight_tenon"
    max_rotation: float = Field(0.03, ge=0.001, le=0.1)
    cycles: int = Field(3, ge=1, le=10)
    steps_per_cycle: int = Field(50, ge=10, le=200)

@router.post("/mortise/cyclic", summary="模拟循环加载下榫卯力学响应")
async def run_cyclic_loading(req: CyclicLoadingRequest):
    try:
        hysteresis = mortise_simulator.simulate_cyclic_loading(
            req.joint_type_id, req.max_rotation, req.cycles, req.steps_per_cycle
        )
        energy = mortise_simulator.compute_energy_dissipation(hysteresis)
        stiffness = mortise_simulator.compute_stiffness_degradation(hysteresis)
        backbone = mortise_simulator.compute_backbone_curve(req.joint_type_id)
        return {
            "status": "success",
            "hysteresis_loop": hysteresis,
            "energy_dissipation": energy,
            "stiffness_degradation": stiffness,
            "backbone_curve": backbone
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/mortise/backbone/{joint_id}", summary="获取骨架曲线")
async def get_backbone(joint_id: str):
    try:
        return mortise_simulator.compute_backbone_curve(joint_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"榫卯类型 {joint_id} 不存在")

@router.post("/mortise/compare", summary="对比多种榫卯力学性能")
async def compare_joints(joint_ids: List[str]):
    try:
        return mortise_simulator.compare_joints(joint_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class CollapseRequest(BaseModel):
    earthquake_pga: float = Field(0.4, ge=0.05, le=3.0)
    duration: float = Field(30.0, ge=5.0, le=120.0)
    time_step: float = Field(0.01, ge=0.005, le=0.1)

@router.post("/collapse/run", summary="运行地震倒塌模拟")
async def run_collapse(req: CollapseRequest):
    try:
        result = collapse_simulator.run_collapse_simulation(
            req.earthquake_pga, req.duration, req.time_step
        )
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CapacityRequest(BaseModel):
    start_pga: float = 0.2
    end_pga: float = 1.5
    pga_step: float = 0.1

@router.post("/collapse/evaluate_capacity", summary="评估极限抗震能力(Pushover)")
async def evaluate_capacity(req: CapacityRequest):
    try:
        result = collapse_simulator.evaluate_ultimate_capacity(
            req.start_pga, req.end_pga, req.pga_step
        )
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/collapse/generate_motion", summary="生成人工地震动")
async def generate_motion(pga: float = 0.4, duration: float = 30.0,
                          time_step: float = 0.01, seed: int = 42):
    t, accel = collapse_simulator.generate_earthquake_motion(pga, duration, time_step, seed)
    return {
        "pga": pga,
        "duration": duration,
        "time_step": time_step,
        "time_array": t.tolist(),
        "acceleration_array_m_s2": accel.tolist(),
        "acceleration_array_g": (accel / 9.81).tolist()
    }

@router.post("/virtual/start", summary="开始虚拟登塔体验")
async def start_virtual(user_id: Optional[int] = None, path_id: str = "default"):
    session = virtual_service.start_experience(user_id=user_id, path_id=path_id)
    return {"status": "success", "session": session}

class VirtualUpdateRequest(BaseModel):
    session_id: str
    time_elapsed: float = 0.0
    wind_speed: float = 5.0
    earthquake_pga: float = 0.0

@router.post("/virtual/update", summary="更新虚拟体验状态(获取当前位置和风振反馈)")
async def update_virtual(req: VirtualUpdateRequest):
    try:
        state = virtual_service.update_experience(
            req.session_id, req.time_elapsed, req.wind_speed, req.earthquake_pga
        )
        return {"status": "success", "state": state}
    except KeyError:
        raise HTTPException(status_code=404, detail="会话不存在")

@router.get("/virtual/floor/{floor}", summary="获取楼层建筑与文化介绍")
async def get_floor_info(floor: int):
    if floor < 1 or floor > 5:
        raise HTTPException(status_code=400, detail="楼层范围 1-5")
    desc = virtual_service.get_floor_description(floor)
    floor_names = {1: "一层佛殿", 2: "二层平座", 3: "三层暗层", 4: "四层佛殿", 5: "五层明层"}
    return {
        "floor": floor,
        "info": {
            "floor_name": floor_names.get(floor, desc.get("name")),
            "architecture_features": desc.get("architecture_features"),
            "buddha_info": desc.get("buddha_info"),
            "view_description": desc.get("view_description")
        }
    }

@router.post("/virtual/wind_response", summary="计算指定高度风振响应")
async def compute_wind_resp(height: float, wind_speed: float, floor: int = 1):
    calc = virtual_service.calculator
    resp = calc.compute_wind_response(wind_speed, height, floor)
    sensory = calc.compute_sensory_data(floor, wind_speed, 0.0)
    return {"wind_response": resp, "sensory_data": sensory}

@router.get("/virtual/paths", summary="获取登塔路径列表")
async def list_paths():
    return {"paths": [
        {"id": "default", "name": "朝圣之路", "difficulty": "medium",
         "description": "从台基一层逐层攀登至塔刹，体验完整的木塔内部空间序列",
         "total_duration_minutes": 10,
         "waypoint_count": 8}
    ]}
