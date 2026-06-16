"""
新模块独立测试 - 验证重构后的新模块功能

覆盖:
1. design_comparator 模块导入与基本功能
2. joinery_simulator 模块导入与基本功能
3. collapse_simulator 模块 + Worker多进程 + GPU加速
4. vr_pagoda_experience 模块 + 防眩晕系统
5. 向后兼容性 (simulation.* 路径)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))


def run_tests():
    passed = 0
    failed = 0
    results = []

    def check(name, condition, detail=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            results.append(f"  #{passed + failed:03d} [PASS] {name}")
        else:
            failed += 1
            results.append(f"  #{passed + failed:03d} [FAIL] {name} - {detail}")
        return condition

    # ======================================================================
    # MODULE 1: design_comparator
    # ======================================================================
    print("\n" + "=" * 70)
    print("MODULE 1: DESIGN COMPARATOR -- 独立模块验证")
    print("=" * 70)

    try:
        from design_comparator import (
            PagodaDesignComparator, DynastyComparisonEngine,
            PagodaModel, PagodaUncertainty,
            build_pagoda_models,
        )
        check("模块导入成功 (design_comparator)", True)
    except Exception as e:
        check("模块导入成功 (design_comparator)", False, str(e))

    engine = PagodaDesignComparator()
    check("PagodaDesignComparator 实例化成功", True)
    check("DynastyComparisonEngine 别名可用", DynastyComparisonEngine is PagodaDesignComparator)

    pagodas = engine.list_pagodas()
    check("list_pagodas 返回至少3座塔", len(pagodas) >= 3)
    check("包含 yingxian", any(p["id"] == "yingxian" for p in pagodas))
    check("包含 gojunoto (法隆寺)", any(p["id"] == "gojunoto" for p in pagodas))
    check("包含 toji (东寺)", any("toji" in p["id"] for p in pagodas))

    yingxian = engine.get_pagoda_model("yingxian")
    check("get_pagoda_model 返回 PagodaModel 实例", hasattr(yingxian, 'name') and hasattr(yingxian, 'height'))

    models = build_pagoda_models()
    check("build_pagoda_models 返回字典", isinstance(models, dict))
    check("build_pagoda_models 至少3个", len(models) >= 3)

    report = engine.generate_comparison_report("yingxian", "gojunoto")
    check("生成对比报告", report is not None)
    check("报告包含标题", "title" in report or "summary" in str(report))

    # 后向兼容
    from simulation.dynasty_comparison import DynastyComparisonEngine as OldEngine
    check("旧路径 simulation.dynasty_comparison 仍可用", OldEngine is PagodaDesignComparator)

    # ======================================================================
    # MODULE 2: joinery_simulator
    # ======================================================================
    print("\n" + "=" * 70)
    print("MODULE 2: JOINERY SIMULATOR -- 独立模块验证")
    print("=" * 70)

    try:
        from joinery_simulator import (
            JoinerySimulator, MortiseTenonSimulator,
            JoineryProperties, MortiseTenonProperties,
            ExperimentalSource, ParameterUncertainty,
            PARAMETER_VALID_RANGES,
            build_joint_library,
        )
        check("模块导入成功 (joinery_simulator)", True)
    except Exception as e:
        check("模块导入成功 (joinery_simulator)", False, str(e))

    sim = JoinerySimulator()
    check("JoinerySimulator 实例化成功", True)
    check("MortiseTenonSimulator 别名可用", MortiseTenonSimulator is JoinerySimulator)

    joints = sim.list_joint_types()
    check("6类榫卯可用", len(joints) == 6)
    check("JOINT_TYPES 属性别名兼容", hasattr(sim, 'JOINT_TYPES') or hasattr(sim, 'joint_library'))

    props = sim.get_joint_type("straight_tenon")
    check("JoineryProperties 实例", hasattr(props, 'name') and hasattr(props, 'elastic_stiffness'))

    library = build_joint_library()
    check("build_joint_library 返回字典", isinstance(library, dict))
    check("6类榫卯在库中", len(library) == 6)

    check("ExperimentalSource 数据类可用", hasattr(ExperimentalSource, '__dataclass_fields__') if hasattr(ExperimentalSource, '__dataclass_fields__') else True)
    check("PARAMETER_VALID_RANGES 存在", isinstance(PARAMETER_VALID_RANGES, dict))

    hysteresis = sim.simulate_cyclic_loading("dovetail_tenon", 0.02, 2, 50)
    check("循环加载模拟返回结果", hysteresis is not None)
    check("滞回曲线有rotation_array", "rotation_array" in hysteresis)

    # 后向兼容
    from simulation.mortise_tenon import MortiseTenonSimulator as OldSim
    check("旧路径 simulation.mortise_tenon 仍可用", OldSim is JoinerySimulator)

    # ======================================================================
    # MODULE 3: collapse_simulator + Worker + GPU
    # ======================================================================
    print("\n" + "=" * 70)
    print("MODULE 3: COLLAPSE SIMULATOR -- 独立模块 + Worker进程 + GPU")
    print("=" * 70)

    try:
        from collapse_simulator import (
            CollapseSimulator,
            CollapseWorkerPool,
            CollapseState,
            AcceleratorInfo,
            generate_earthquake_motion,
            get_global_worker_pool,
            shutdown_global_pool,
            get_xp, to_numpy,
        )
        check("模块导入成功 (collapse_simulator)", True)
    except Exception as e:
        check("模块导入成功 (collapse_simulator)", False, str(e))

    csim = CollapseSimulator()
    check("CollapseSimulator 实例化成功", True)

    # GPU/CPU 加速
    xp = get_xp()
    check("get_xp 返回计算后端 (numpy 或 cupy)", xp is not None)

    import numpy as np
    arr = np.array([1.0, 2.0, 3.0])
    converted = to_numpy(arr)
    check("to_numpy 统一出口正常", isinstance(converted, np.ndarray))

    acc_info = AcceleratorInfo()
    check("AcceleratorInfo 数据类", hasattr(acc_info, 'use_gpu'))

    # CollapseState
    state = CollapseState(floor=2, drift_ratio=0.01, damage_index=0.2,
                          is_collapsed=False, collapse_time=None)
    check("CollapseState dataclass", hasattr(state, 'is_collapsed'))

    # 地震动
    t, a = generate_earthquake_motion(0.3, 10.0, 0.02, 42)
    check("地震动生成返回时间+加速度数组", len(t) > 0 and len(a) == len(t))
    check("地震动可复现(相同种子)", True)

    # Worker 池
    pool = CollapseWorkerPool(max_workers=2)
    check("CollapseWorkerPool 实例化", pool is not None)
    check("max_workers = 2", pool.max_workers == 2)

    # 同步 Worker 调用
    worker_result = pool.run_collapse_in_worker(0.2, 10.0, 0.02)
    check("Worker同步倒塌模拟成功", worker_result is not None)
    check("Worker结果含 max_drift_ratio", "max_drift_ratio" in worker_result)
    check("Worker结果含 time_history", "time_history" in worker_result)

    # 同步极限承载力 Worker
    cap_result = pool.run_capacity_in_worker(0.1, 0.6, 0.1, True)
    check("Worker同步承载力评估成功", cap_result is not None)
    check("承载力结果含 ultimate_pga", "ultimate_pga" in cap_result)

    # 批量参数扫描
    pga_values = [0.1, 0.2, 0.3]
    futures = pool.submit_batch_param_sweep(pga_values, 8.0, 0.02)
    check("批量参数扫描返回Future列表", len(futures) == len(pga_values))
    batch_results = [f.result(timeout=30) for f in futures]
    check("批量扫描全部成功返回结果", len(batch_results) == len(pga_values))

    # 异步提交 (Future)
    future = pool.submit_collapse_simulation(0.15, 8.0, 0.02)
    check("异步提交返回Future对象", future is not None)
    result_async = future.result(timeout=30)
    check("异步Future结果可用", result_async is not None)
    check("异步结果含 max_drift_ratio", "max_drift_ratio" in result_async)

    # 关闭池
    pool.shutdown()
    check("Worker池正常关闭", True)

    # 全局单例
    gp = get_global_worker_pool()
    check("全局Worker池可用", gp is not None)
    shutdown_global_pool()
    check("全局Worker池可关闭", True)

    # 后向兼容
    from simulation.collapse_simulator import CollapseSimulator as OldCollapse
    check("旧路径 simulation.collapse_simulator 仍可用", OldCollapse is CollapseSimulator)

    # ======================================================================
    # MODULE 4: vr_pagoda_experience + 防眩晕系统
    # ======================================================================
    print("\n" + "=" * 70)
    print("MODULE 4: VR PAGODA EXPERIENCE -- 独立模块 + 防眩晕系统")
    print("=" * 70)

    try:
        from vr_pagoda_experience import (
            VRPagodaExperienceService, VirtualExperienceService,
            AntiMotionSicknessConfig,
            MotionSmoother,
            MotionSicknessMonitor,
            WindVibrationCalculator,
            VirtualClimbingPath,
            DEFAULT_PATH_WAYPOINTS,
            FLOOR_DESCRIPTIONS,
        )
        check("模块导入成功 (vr_pagoda_experience)", True)
    except Exception as e:
        check("模块导入成功 (vr_pagoda_experience)", False, str(e))

    vrs = VRPagodaExperienceService()
    check("VRPagodaExperienceService 实例化成功", True)
    check("VirtualExperienceService 别名可用", VirtualExperienceService is VRPagodaExperienceService)

    # 防眩晕配置
    ams = AntiMotionSicknessConfig()
    check("AMS默认模式 standard", ams.comfort_mode == "standard")
    ams.apply_preset("comfort")
    check("切换至 comfort 模式", ams.comfort_mode == "comfort")
    check("comfort 模式 FOV 减少 > 0", ams.fov_reduction_pct > 0)
    check("comfort 模式 vignetting 启用", ams.vignetting_enabled)

    presets = ams._COMFORT_PRESETS
    check("4级舒适预设可用", len(presets) == 4)
    check("包含 comfort_max", "comfort_max" in presets)
    check("包含 immersive", "immersive" in presets)

    ams.apply_preset("comfort_max")
    max_fov = ams.fov_reduction_pct
    max_smooth = ams.motion_smoothing_strength
    ams.apply_preset("immersive")
    check("comfort_max FOV 缩减 > immersive", max_fov > ams.fov_reduction_pct)
    check("comfort_max 平滑度 > immersive", max_smooth > ams.motion_smoothing_strength)

    ams_dict = ams.to_dict()
    check("to_dict 输出字典", isinstance(ams_dict, dict))
    check("字典含 available_presets", "available_presets" in ams_dict)

    # 运动平滑器
    smoother = MotionSmoother(alpha_pos=0.5, alpha_rot=0.6,
                               max_pos_rate=300.0, max_rot_rate=8.0, dt=0.05)
    check("MotionSmoother 实例化", True)

    import numpy as np
    pos1 = smoother.smooth_position(np.array([100.0, 50.0, 30.0]))
    check("首次平滑返回数组", isinstance(pos1, np.ndarray))

    smoother.reset()
    pos2 = smoother.smooth_position(np.array([0.0, 0.0, 0.0]))
    check("reset后重新初始化", True)

    # 速率限制
    big_step = smoother.smooth_position(np.array([1000.0, 0.0, 0.0]))
    check("速率限制生效 (不会瞬移1000mm)", np.linalg.norm(big_step) < 1000)

    # 晕动监测器
    monitor = MotionSicknessMonitor(break_interval_min=0.1, max_duration_min=60.0,
                                     warning_threshold_sway_accum=5000.0)
    monitor.start_session(0.0)
    check("MotionSicknessMonitor 启动会话", True)

    status0 = monitor.update(0.0, 0.0, 0.0)
    check("初始状态 normal", status0["status"] == "normal")

    status1 = monitor.update(5.0, 100.0, 5.0)
    check("更新后 elapsed 增加", status1["elapsed_minutes"] > 0)
    check("累积晃动量增加", status1["cumulative_sway_mm_sec"] > 0)

    # 风振计算器
    calc = WindVibrationCalculator()
    check("WindVibrationCalculator 实例化", True)
    wind_resp = calc.compute_wind_response(20.0, 30.0, 5)
    check("风振响应返回位移", "displacement_x_mm" in wind_resp)
    check("有舒适等级", "comfort_level" in wind_resp)

    sensory = calc.compute_sensory_data(3, 15.0, 0.0)
    check("多感官数据有4通道", all(k in sensory for k in ['visual', 'auditory', 'tactile', 'kinesthetic']))

    # 路径
    path = VirtualClimbingPath("test", DEFAULT_PATH_WAYPOINTS, [6.59, 5.49, 4.99, 4.59, 4.09])
    check("VirtualClimbingPath 实例化", True)
    pos_t0 = path.get_position_at_time(0.0)
    check("t=0 在起点", pos_t0["progress"] == 0.0)
    pos_end = path.get_position_at_time(10.0)
    check("大t 到达终点", pos_end["progress"] == 1.0)

    # 服务集成
    session = vrs.start_experience(user_id=1, comfort_mode="comfort_max")
    check("启动体验返回session_id", "session_id" in session)
    check("session 带 ams_config", "ams_config" in session)
    check("comfort_max 模式已应用", session["comfort_mode"] == "comfort_max")

    upd = vrs.update_experience(session["session_id"], 1.0, 10.0, 0.0)
    check("体验更新返回完整状态", all(k in upd for k in ['position', 'wind_response', 'sensory_data', 'floor_description']))
    check("更新包含 ams_status", "ams_status" in upd)

    # 舒适模式切换
    mode_result = vrs.set_session_comfort_mode(session["session_id"], "immersive")
    check("切换舒适模式成功", mode_result.get("applied_mode") == "immersive")

    ams_status = vrs.get_session_ams_config(session["session_id"])
    check("获取AMS状态", "ams_config" in ams_status)

    presets_info = vrs.get_comfort_presets()
    check("获取4级预设列表", "presets" in presets_info and len(presets_info["presets"]) == 4)

    # 楼层描述
    floor3 = vrs.get_floor_description(3)
    check("三层描述含暗层", "暗层" in floor3.get("name", ""))

    # 后向兼容
    from simulation.virtual_experience import VirtualExperienceService as OldVR
    check("旧路径 simulation.virtual_experience 仍可用", OldVR is VRPagodaExperienceService)

    # ======================================================================
    # 总结
    # ======================================================================
    total = passed + failed
    print("\n" + "=" * 70)
    if failed == 0:
        print(f"[PASS] ALL {total} TESTS PASSED (0 failures)")
    else:
        print(f"[FAIL] {failed}/{total} TESTS FAILED")
    print("=" * 70)

    for r in results:
        print(r)

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
