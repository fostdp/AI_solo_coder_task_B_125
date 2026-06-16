import sys, os, json, time, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from fastapi import FastAPI
import uvicorn

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from api.new_features_routes import router as new_features_router

app = FastAPI(title="Test FEA New Features")
app.include_router(new_features_router)

BASE = "http://127.0.0.1:8765"

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="error")

def http(method, path, json_body=None, params=None):
    import urllib.request, urllib.parse
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    data = None
    headers = {}
    if json_body is not None:
        data = json.dumps(json_body).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            body = resp.read().decode('utf-8')
            return resp.status, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='replace')
        return e.code, err_body
    except Exception as e:
        return 0, str(e)

def test_api():
    print("=== 启动本地测试服务 (127.0.0.1:8765)... ===")
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(3.0)
    
    print(f"\n==== 测试 API 路由前缀: /api/new ====")
    
    print("\n[1/18] 朝代 - list_pagodas:")
    c, r = http('GET', '/api/new/dynasty/pagodas')
    print(f"  -> HTTP {c}")
    assert c == 200, f"失败: {r}"
    pagodas = r['pagodas']
    print(f"    木塔数: {len(pagodas)}")
    for p in pagodas[:2]:
        print(f"      - {p.get('id')}: {p.get('name')} ({p.get('country')})")
    a_id, b_id = pagodas[0]['id'], pagodas[1]['id']
    
    print(f"\n[2/18] 朝代 - get_pagoda({a_id}):")
    c, r = http('GET', f'/api/new/dynasty/pagoda/{a_id}')
    print(f"  -> HTTP {c}")
    assert c == 200, f"失败: {r}"
    pg_a = r
    print(f"    {pg_a['name']} - {pg_a['dynasty']} {pg_a['country']}")
    print(f"    结构: 高{pg_a['height']}m, {pg_a['floor_count']}层, {pg_a['structural_type']}")
    
    print(f"\n[3/18] 朝代 - compare (GET a={a_id}&b={b_id}):")
    c, r = http('GET', '/api/new/dynasty/compare', params={"a": a_id, "b": b_id})
    print(f"  -> HTTP {c}, status: {r.get('status')}")
    assert c == 200, f"失败: {r}"
    rep = r['report']
    print(f"    title: {rep.get('title')}")
    nf = rep.get('natural_frequency_comparison', {})
    print(f"    频率(前3) a: {nf.get('frequencies_a', [])[:3]}")
    print(f"    频率(前3) b: {nf.get('frequencies_b', [])[:3]}")
    print(f"    理念差异条数: {len(rep.get('seismic_philosophy_comparison', {}).get('differences', []))}")
    
    print(f"\n[4/18] 朝代 - frequency_compare:")
    c, r = http('GET', '/api/new/dynasty/frequency_compare', params={"a": a_id, "b": b_id})
    print(f"  -> HTTP {c}, ratio_a_to_b[:3]: {r.get('ratio_a_to_b', [])[:3]}")
    assert c == 200
    
    print(f"\n[5/18] 朝代 - wind_compare (30m/s):")
    c, r = http('GET', '/api/new/dynasty/wind_compare', params={"a": a_id, "b": b_id, "wind_speed": 30})
    print(f"  -> HTTP {c}")
    assert c == 200
    wc = r
    print(f"    top_disp_a_mm: {wc.get('top_disp_a_mm'):.2f}")
    print(f"    top_disp_b_mm: {wc.get('top_disp_b_mm'):.2f}")
    print(f"    分析: {str(wc.get('analysis'))[:40]}...")
    
    print(f"\n[6/18] 榫卯 - list_types:")
    c, r = http('GET', '/api/new/mortise/types')
    print(f"  -> HTTP {c}")
    assert c == 200
    jts = r['joint_types']
    print(f"    榫卯类型数: {len(jts)}")
    for j in jts:
        print(f"      - {j['id']}: {j['name']} μ={j['ductility_factor']}")
    j_id = jts[0]['id']
    
    print(f"\n[7/18] 榫卯 - get_type({j_id}):")
    c, r = http('GET', f'/api/new/mortise/type/{j_id}')
    print(f"  -> HTTP {c} -> {r.get('name')}, M_y={r.get('yield_moment')}")
    assert c == 200
    
    print(f"\n[8/18] 榫卯 - run_cyclic (max_rot=0.05, cycles=3):")
    c, r = http('POST', '/api/new/mortise/cyclic', json_body={"joint_type_id": j_id, "max_rotation": 0.05, "cycles": 3, "steps_per_cycle": 80})
    print(f"  -> HTTP {c}, status: {r.get('status')}")
    assert c == 200
    hl = r.get('hysteresis_loop', {})
    print(f"    总步数: {hl.get('total_steps')}")
    ma = hl.get('moment_array',[0])
    print(f"    M_min/max: {min(ma):.1f}/{max(ma):.1f}")
    energy = r.get('energy_dissipation', {})
    print(f"    耗散能: {energy.get('total_energy',0):.1f} J")
    print(f"    等效阻尼比: {energy.get('equivalent_damping_ratio',0)*100:.1f}%")
    stiff = r.get('stiffness_degradation', {})
    print(f"    刚度退化(末/初): {stiff.get('final_to_initial_ratio',1)*100:.1f}%")
    
    print(f"\n[9/18] 榫卯 - backbone({j_id}):")
    c, r = http('GET', f'/api/new/mortise/backbone/{j_id}')
    print(f"  -> HTTP {c}, 骨架点数: {len(r.get('rotation_array', []))}")
    assert c == 200
    bb = r
    yield_point = bb.get('yield_point', {})
    print(f"    屈服点 M={yield_point.get('moment'):.1f} θ={yield_point.get('rotation'):.4f}")
    
    print(f"\n[10/18] 榫卯 - compare_joints (前3类):")
    ids = [j['id'] for j in jts[:3]]
    c, r = http('POST', '/api/new/mortise/compare', json_body=ids)
    print(f"  -> HTTP {c}, 对比项数: {len(r)}")
    assert c == 200
    
    print(f"\n[11/18] 倒塌 - generate_motion (0.3g, 10s):")
    c, r = http('POST', '/api/new/collapse/generate_motion', params={"pga": 0.3, "duration": 10})
    print(f"  -> HTTP {c}")
    assert c == 200
    gm = r
    print(f"    步数: {len(gm.get('time_array', []))}, PGA={gm.get('pga')}g")
    
    print(f"\n[12/18] 倒塌 - run_collapse (0.6g, 15s):")
    c, r = http('POST', '/api/new/collapse/run', json_body={"earthquake_pga": 0.6, "duration": 15, "time_step": 0.02})
    print(f"  -> HTTP {c}, status: {r.get('status')}")
    assert c == 200
    cs = r['result']
    print(f"    倒塌模式: {cs.get('collapse_mode')}")
    print(f"    倒塌时间: {cs.get('collapse_time')}s (None=未倒塌)")
    dr = cs.get('max_interstory_drift',1)
    print(f"    最大层间位移角: 1/{int(1/dr)}")
    ds = cs.get('performance_summary', {})
    print(f"    性能水准: {ds.get('performance_level')}")
    
    print(f"\n[13/18] 倒塌 - evaluate_capacity:")
    c, r = http('POST', '/api/new/collapse/evaluate_capacity', json_body={"start_pga": 0.1, "end_pga": 0.8, "pga_step": 0.1})
    print(f"  -> HTTP {c}, status: {r.get('status')}")
    assert c == 200
    cap = r['result']
    print(f"    屈服PGA: {cap.get('yield_pga_g')}g")
    print(f"    极限PGA: {cap.get('collapse_pga_g')}g")
    print(f"    超强系数Ω: {cap.get('overstrength_factor',0):.2f}")
    print(f"    安全储备(vs8度0.16g): {cap.get('safety_reserve_ratio',0):.2f}x")
    
    print(f"\n[14/18] 虚拟登塔 - list_paths:")
    c, r = http('GET', '/api/new/virtual/paths')
    print(f"  -> HTTP {c}, 路径数: {len(r.get('paths', []))}")
    assert c == 200
    paths = r['paths']
    path_id = paths[0].get('id')
    print(f"    路径: {paths[0].get('name')}, 航点数: {paths[0].get('waypoint_count')}")
    
    print(f"\n[15/18] 虚拟登塔 - start_experience:")
    c, r = http('POST', '/api/new/virtual/start', params={"path_id": path_id})
    print(f"  -> HTTP {c}, status: {r.get('status')}")
    assert c == 200
    sx = r['session']
    sid = sx.get('session_id')
    print(f"    会话ID: {sid[:16]}...")
    
    print(f"\n[16/18] 虚拟登塔 - update (60s, 风15m/s, 震0.05g):")
    c, r = http('POST', '/api/new/virtual/update', json_body={"session_id": sid, "time_elapsed": 60, "wind_speed": 15, "earthquake_pga": 0.05})
    print(f"  -> HTTP {c}, status: {r.get('status')}")
    assert c == 200
    ux = r['state']
    pos = ux.get('position', {})
    wr = ux.get('wind_response', {})
    print(f"    位置: {pos.get('waypoint_name')}, Y={pos.get('y'):.1f}m")
    print(f"    风振: Δx={wr.get('displacement_x_mm'):.2f}mm, 舒适={wr.get('comfort_level')}")
    sn = ux.get('sensory_data', {})
    print(f"    体感: 视觉{sn.get('visual',{}).get('sway_magnitude_mm')}mm / 听觉{sn.get('auditory',{}).get('noise_level_db')}dB")
    
    print(f"\n[17/18] 虚拟登塔 - get_floor_info (3层):")
    c, r = http('GET', '/api/new/virtual/floor/3')
    print(f"  -> HTTP {c}")
    assert c == 200
    fi = r['info']
    print(f"    楼层: {fi.get('floor_name')}")
    print(f"    建筑特色: {str(fi.get('architecture_features'))[:30]}...")
    
    print(f"\n[18/18] 虚拟登塔 - wind_response (30m, 风30m/s, 4层):")
    c, r = http('POST', '/api/new/virtual/wind_response', params={"height": 30, "wind_speed": 30, "floor": 4})
    print(f"  -> HTTP {c}")
    assert c == 200
    wr = r['wind_response']
    print(f"    位移: {wr.get('displacement_x_mm'):.2f}mm, 加速: {wr.get('acceleration_x'):.4f}m/s2")
    print(f"    舒适度: {wr.get('comfort_level')}")
    
    print("\n\n========== [PASS] 全部 18 个 API 端点测试通过 ==========")

if __name__ == "__main__":
    test_api()
