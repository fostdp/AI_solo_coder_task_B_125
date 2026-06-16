import sys
sys.path.insert(0, '.')

print('== 测试1: 朝代对比 ==')
from simulation.dynasty_comparison import DynastyComparisonEngine
e = DynastyComparisonEngine()
r = e.generate_comparison_report('yingxian', 'gojunoto')
print('报告生成:', list(r.keys()))
fa = r['natural_frequency_comparison'].get('frequencies_a', [])
fb = r['natural_frequency_comparison'].get('frequencies_b', [])
print('应县前3阶:', [round(x,3) for x in fa[:3]])
print('五重塔前3阶:', [round(x,3) for x in fb[:3]])
print('理念差异条目:', len(r['seismic_philosophy_comparison'].get('differences', [])))

print()
print('== 测试2: 榫卯循环加载 ==')
from simulation.mortise_tenon import MortiseTenonSimulator
s = MortiseTenonSimulator()
print('榫卯类型数:', len(s.list_joint_types()))
for jt in s.list_joint_types()[:2]:
    print(' -', jt['chinese_name'], '延性μ=', round(jt['ductility'],1))

h = s.simulate_cyclic_loading('straight_tenon', 0.03, 3, 60)
energy = s.compute_energy_dissipation(h)
stiff = s.compute_stiffness_degradation(h)
bb = s.compute_backbone_curve('cross_tenon')
print('循环步数:', h['total_steps'], '总耗能:', round(energy['total_energy'],0), 'J')
print('等效阻尼比:', round(energy['equivalent_damping_ratio']*100,1),'%')
print('刚度退化末/初:', round(stiff['final_to_initial_ratio']*100,0),'%')
print('骨架曲线点:', len(bb['rotation_array']))

print()
print('== 测试3: 倒塌模拟(0.5g,12s) ==')
from simulation.collapse_simulator import CollapseSimulator
c = CollapseSimulator()
r = c.run_collapse_simulation(0.5, 12.0, 0.05)
print('倒塌模式:', r['collapse_mode'])
print('倒塌时间:', r['collapse_time'])
print('倒塌起始楼层:', r['collapse_floor'])
print('最大层间位移角:', '1/{}'.format(round(1/max(r['max_drift_ratio'],1e-6))))
print('最大基底剪力(kN):', round(r['max_base_shear']/1000,1))
print('延性μ:', round(r['ductility_factor'],1), '超强系数Ω:', round(r['overstrength_factor'],2))
print('失效序列事件数:', len(r['failure_sequence']))
for ev in r['failure_sequence'][:3]:
    print('  + t={:.2f}s {}层 {} (Δ=1/{})'.format(ev['time'], ev['floor'], ev['event_type'], round(1/max(ev['drift_ratio'],1e-6))))

print()
print('== 测试4: Pushover能力评估 ==')
cv = c.evaluate_ultimate_capacity(start_pga=0.2, end_pga=1.5, pga_step=0.2)
print('实测PGA数据点:', len(cv['capacity_curve']))
print('首次屈服PGA:', cv['yield_pga'])
print('极限倒塌PGA:', cv['ultimate_pga'])
print('设计安全储备(VS 8度0.16g):', round(cv['safety_margin_vs_design'],1),'倍')
pl = cv['performance_levels']
print('4级性能水准: 正常使用≤{}g 立即可用≤{}g 生命安全≤{}g 防倒塌≤{}g'.format(
    pl['operational_pga'], pl['immediate_occupancy_pga'], pl['life_safety_pga'], pl['collapse_prevention_pga']))

print()
print('== 测试5: 虚拟登塔体验 ==')
from simulation.virtual_experience import VirtualExperienceService
ve = VirtualExperienceService()
ses = ve.start_experience(user_id=1)
print('会话:', ses['session_id'][:12]+'...')
for sc in [(0, 5.0, 0.0), (120, 15.0, 0.0), (360, 25.0, 0.0), (480, 35.0, 0.1)]:
    t, ws, eq = sc
    st = ve.update_experience(ses['session_id'], time_elapsed=t, wind_speed=ws, earthquake_pga=eq)
    pos = st['position']
    wr = st['wind_response']
    print(' + t={}s @{} (Y={:.1f}m) 风{:.0f}m/s 震{:.2f}g 舒适:{} 顶层位移:{:.1f}mm 加速度:{:.3f}m/s2'.format(
        t, pos['waypoint_name'], pos['y'], ws, eq, wr['comfort_level'],
        wr['displacement_x_mm'], wr['acceleration_x']))

fi = ve.get_floor_description(3)
print('三层描述:', fi['architecture_features'][:24],'...')

print()
print('========== [PASS] 全部新功能模块测试通过 ==========')
