import sys
import os
import json
import time
import threading
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import numpy as np
from simulation.dynasty_comparison import DynastyComparisonEngine, DynastyPagodaModel
from simulation.mortise_tenon import MortiseTenonSimulator, MortiseTenonProperties
from simulation.collapse_simulator import CollapseSimulator, CollapseState
from simulation.virtual_experience import VirtualExperienceService, WindVibrationCalculator, VirtualClimbingPath

PASS_COUNT = 0
FAIL_COUNT = 0
CASE_INDEX = 0

def assert_test(condition, msg, detail=""):
    global PASS_COUNT, FAIL_COUNT, CASE_INDEX
    CASE_INDEX += 1
    tag = "[PASS]" if condition else "[FAIL]"
    if condition:
        PASS_COUNT += 1
    else:
        FAIL_COUNT += 1
    line = "  #%03d %s %s" % (CASE_INDEX, tag, msg)
    if detail and not condition:
        line += " -- " + str(detail)[:120]
    print(line)
    assert condition, msg

def approx_eq(a, b, rel=0.05):
    if a == 0 and b == 0:
        return True
    if a == 0 or b == 0:
        return abs(a - b) < 1e-9
    return abs(a - b) / max(abs(a), abs(b)) < rel

# ============================================================
# MODULE 1: DYNASTY COMPARISON
# ============================================================
print("\n" + "=" * 70)
print("MODULE 1: DYNASTY COMPARISON -- Structural Performance Indicators")
print("=" * 70)

engine = DynastyComparisonEngine()

# --- Normal ---
print("\n--- Normal Cases ---")

pagodas = engine.list_pagodas()
assert_test(len(pagodas) == 2, "list_pagodas returns 2 entries")
assert_test(all(p.get('id') and p.get('name') and p.get('country') for p in pagodas),
            "Each pagoda has id/name/country fields")

yx = engine.get_pagoda_model('yingxian')
gj = engine.get_pagoda_model('gojunoto')
assert_test(yx.name == "应县木塔", "Yingxian pagoda name correct")
assert_test(gj.name == "法隆寺五重塔", "Gojunoto pagoda name correct")
assert_test(yx.height > gj.height, "Yingxian taller than Gojunoto (67.3m > 32.5m)")
assert_test(yx.shinbashira == False, "Yingxian has no shinbashira")
assert_test(gj.shinbashira == True, "Gojunoto has shinbashira")
assert_test(yx.floor_count == 5, "Yingxian 5 floors")
assert_test(gj.floor_count == 5, "Gojunoto 5 floors")
assert_test(len(yx.floor_heights) == 5, "Yingxian floor_heights length 5")
assert_test(len(yx.floor_diameters) == 5, "Yingxian floor_diameters length 5")

freq_comp = engine.compare_natural_frequencies('yingxian', 'gojunoto')
fa = freq_comp['frequencies_a']
fb = freq_comp['frequencies_b']
assert_test(len(fa) == 5 and len(fb) == 5, "5 natural frequencies each")
assert_test(fa[0] > 0 and fb[0] > 0, "Fundamental frequencies positive")
assert_test(fa[0] < fa[1], "Yingxian f1 < f2 (ascending)")
assert_test(fb[0] < fb[1], "Gojunoto f1 < f2 (ascending)")
assert_test('ratio_a_to_b' in freq_comp, "ratio_a_to_b present")
assert_test('analysis' in freq_comp, "analysis text present")
assert_test(len(freq_comp['ratio_a_to_b']) == 5, "5 frequency ratios")

phil = engine.compare_seismic_philosophy('yingxian', 'gojunoto')
assert_test(len(phil.get('key_differences', [])) >= 2, "At least 2 key differences")
assert_test(len(phil.get('differences', [])) >= 2, "differences alias exists")
assert_test('quantitative' in phil, "Quantitative comparison present")
assert_test(phil['quantitative']['rotational_stiffness_ratio_a_to_b'] > 0, "Stiffness ratio > 0")
assert_test(phil['quantitative']['yield_moment_ratio_a_to_b'] > 0, "Yield moment ratio > 0")

wind_comp = engine.compare_displacement_under_wind('yingxian', 'gojunoto', 25.0)
assert_test(wind_comp['top_disp_a_mm'] > 0, "Yingxian wind disp > 0")
assert_test(wind_comp['top_disp_b_mm'] > 0, "Gojunoto wind disp > 0")
assert_test(wind_comp['wind_pressure_pa'] > 0, "Wind pressure > 0")
assert_test('ratio_a_to_b' in wind_comp, "Wind displacement ratio present")
assert_test('analysis' in wind_comp, "Wind analysis text present")

energy_comp = engine.compare_energy_dissipation('yingxian', 'gojunoto')
assert_test(energy_comp['pagoda_a']['energy_per_cycle_kj'] > 0, "Yingxian energy > 0")
assert_test(energy_comp['pagoda_b']['energy_per_cycle_kj'] > 0, "Gojunoto energy > 0")
assert_test(energy_comp['pagoda_a']['equivalent_damping_ratio'] > 0, "Yingxian damping > 0")
assert_test(energy_comp['pagoda_b']['equivalent_damping_ratio'] > 0, "Gojunoto damping > 0")

report = engine.generate_comparison_report('yingxian', 'gojunoto')
assert_test('title' in report, "Report has title")
assert_test('seismic_philosophy_comparison' in report, "Report has philosophy")
assert_test('natural_frequency_comparison' in report, "Report has frequency")
assert_test('wind_displacement_comparison' in report, "Report has wind")
assert_test('energy_dissipation_comparison' in report, "Report has energy")

wind_15 = engine.compare_displacement_under_wind('yingxian', 'gojunoto', 15.0)
wind_30 = engine.compare_displacement_under_wind('yingxian', 'gojunoto', 30.0)
assert_test(wind_30['top_disp_a_mm'] > wind_15['top_disp_a_mm'],
            "Wind disp at 30m/s > 15m/s (monotonicity)")

freq_ratio = freq_comp['ratio_a_to_b'][0]
assert_test(0.1 < freq_ratio < 10.0, "Fundamental frequency ratio in reasonable range (0.1,10)")

# --- Boundary ---
print("\n--- Boundary Cases ---")

wind_0 = engine.compare_displacement_under_wind('yingxian', 'gojunoto', 0.0)
assert_test(wind_0['top_disp_a_mm'] == 0.0, "Zero wind speed => zero displacement (Yingxian)")
assert_test(wind_0['top_disp_b_mm'] == 0.0, "Zero wind speed => zero displacement (Gojunoto)")

freq_comp_self = engine.compare_natural_frequencies('yingxian', 'yingxian')
assert_test(all(approx_eq(r, 1.0) for r in freq_comp_self['ratio_a_to_b']),
            "Self-comparison => all frequency ratios = 1.0")

phil_self = engine.compare_seismic_philosophy('yingxian', 'yingxian')
assert_test("相似" in phil_self.get('comparison', ''), "Self-comparison => similar philosophy")

wind_100 = engine.compare_displacement_under_wind('yingxian', 'gojunoto', 100.0)
assert_test(wind_100['top_disp_a_mm'] > 0, "Extreme wind 100m/s => still computes")

freq_yx = engine._compute_natural_frequencies(yx)
for i in range(4):
    assert_test(freq_yx[i] < freq_yx[i + 1], "Higher mode frequency ascending (mode %d<%d)" % (i, i + 1))

# --- Abnormal ---
print("\n--- Abnormal Cases ---")

try:
    engine.get_pagoda_model('nonexistent')
    assert_test(False, "get_pagoda_model('nonexistent') should raise ValueError")
except ValueError:
    assert_test(True, "get_pagoda_model('nonexistent') raises ValueError correctly")

try:
    engine.generate_comparison_report('yingxian', 'nonexistent')
    assert_test(False, "compare with nonexistent should raise ValueError")
except ValueError:
    assert_test(True, "compare with nonexistent raises ValueError correctly")

try:
    engine.compare_natural_frequencies('nonexistent', 'gojunoto')
    assert_test(False, "frequency_compare with nonexistent should raise ValueError")
except ValueError:
    assert_test(True, "frequency_compare with nonexistent raises ValueError")

try:
    engine.compare_displacement_under_wind('yingxian', 'nonexistent', 25.0)
    assert_test(False, "wind_compare with nonexistent should raise ValueError")
except ValueError:
    assert_test(True, "wind_compare with nonexistent raises ValueError")

try:
    engine.compare_energy_dissipation('nonexistent', 'gojunoto')
    assert_test(False, "energy_compare with nonexistent should raise ValueError")
except ValueError:
    assert_test(True, "energy_compare with nonexistent raises ValueError")

wind_neg = engine.compare_displacement_under_wind('yingxian', 'gojunoto', -10.0)
assert_test(isinstance(wind_neg, dict), "Negative wind speed does not crash (returns dict)")


# ============================================================
# MODULE 2: MORTISE TENON
# ============================================================
print("\n" + "=" * 70)
print("MODULE 2: MORTISE TENON -- Joint Stiffness & Hysteresis")
print("=" * 70)

mt = MortiseTenonSimulator()

# --- Normal ---
print("\n--- Normal Cases ---")

jtypes = mt.list_joint_types()
assert_test(len(jtypes) == 6, "6 joint types available")
type_ids = [j['id'] for j in jtypes]
expected_ids = ['straight_tenon', 'dovetail_tenon', 'cross_tenon', 'through_tenon', 'angle_brace_tenon', 'bucket_arch_joint']
assert_test(set(type_ids) == set(expected_ids), "All 6 joint type IDs match")

for jt in jtypes:
    assert_test(jt['elastic_stiffness'] > 0, "%s stiffness > 0" % jt['id'])
    assert_test(jt['yield_moment'] > 0, "%s yield_moment > 0" % jt['id'])
    assert_test(jt['ultimate_moment'] > jt['yield_moment'], "%s Mu > My" % jt['id'])
    assert_test(jt['yield_rotation'] > 0, "%s yield_rotation > 0" % jt['id'])
    assert_test(jt['ultimate_rotation'] > jt['yield_rotation'], "%s ultimate_rotation > yield_rotation" % jt['id'])
    assert_test(jt['ductility_factor'] >= 1.0, "%s ductility >= 1.0" % jt['id'])
    assert_test(0 < jt['pinching_factor'] <= 1.0, "%s pinching in (0,1]" % jt['id'])
    assert_test(0 < jt['damping_ratio'] < 1.0, "%s damping in (0,1)" % jt['id'])

st_props = mt.get_joint_type('straight_tenon')
assert_test(st_props.name == 'straight_tenon', "straight_tenon props name correct")
assert_test(st_props.model_type == 'bilinear', "straight_tenon is bilinear")

dv_props = mt.get_joint_type('dovetail_tenon')
assert_test(dv_props.model_type == 'trilinear', "dovetail_tenon is trilinear")

ab_props = mt.get_joint_type('angle_brace_tenon')
assert_test(ab_props.gap > 0, "angle_brace_tenon has gap > 0")

ba_props = mt.get_joint_type('bucket_arch_joint')
assert_test(ba_props.vertical_load_effect == True, "bucket_arch_joint has vertical load effect")

hyst = mt.simulate_cyclic_loading('straight_tenon', 0.03, 3, 60)
assert_test(hyst['total_steps'] > 0, "Cyclic loading produces steps")
assert_test(len(hyst['rotation_array']) == len(hyst['moment_array']), "Rotation/Moment arrays same length")
assert_test(hyst['final_stiffness_ratio'] < 1.0, "Stiffness degrades after cycling")
assert_test(hyst['final_stiffness_ratio'] >= 0.2, "Stiffness does not degrade below 20%")
assert_test(len(hyst['cycle_energies']) == 3, "3 cycle energies")

energy = mt.compute_energy_dissipation(hyst)
assert_test(energy['total_energy'] > 0, "Total dissipated energy > 0")
assert_test(energy['equivalent_damping_ratio'] > 0, "Equivalent damping ratio > 0")
assert_test(energy['equivalent_damping_ratio'] <= 0.5, "Equivalent damping ratio <= 50% cap")
assert_test(energy['energy_dissipation_ratio'] > 0, "Energy dissipation ratio > 0")

stiff = mt.compute_stiffness_degradation(hyst)
assert_test(len(stiff['secant_stiffnesses']) > 0, "Secant stiffnesses computed")
assert_test(stiff['final_to_initial_ratio'] < 1.0, "Final stiffness < initial")
assert_test(stiff['final_to_initial_ratio'] >= 0.1, "Final stiffness >= 10% of initial")

bb = mt.compute_backbone_curve('straight_tenon')
assert_test(len(bb['rotation_array']) == 100, "Backbone has 100 points")
assert_test('yield_point' in bb, "Backbone has yield_point")
assert_test('ultimate_point' in bb, "Backbone has ultimate_point")
assert_test(bb['yield_point']['moment'] > 0, "Yield moment > 0 in backbone")
assert_test(bb['ultimate_point']['moment'] > bb['yield_point']['moment'], "Ultimate > Yield moment in backbone")
assert_test(bb['ductility_factor'] >= 1.0, "Backbone ductility >= 1")

compare_result = mt.compare_joints(['straight_tenon', 'dovetail_tenon'])
assert_test(len(compare_result) == 2, "Compare returns 2 joints")
assert_test('straight_tenon' in compare_result and 'dovetail_tenon' in compare_result, "Keys match IDs")
for jid, data in compare_result.items():
    assert_test(data['elastic_stiffness'] > 0, "%s stiffness > 0 in compare" % jid)
    assert_test('backbone_curve' in data, "%s has backbone in compare" % jid)

hyst_dv = mt.simulate_cyclic_loading('dovetail_tenon', 0.04, 2, 40)
assert_test(hyst_dv['total_steps'] > 0, "Dovetail cyclic produces steps")
energy_dv = mt.compute_energy_dissipation(hyst_dv)
assert_test(energy_dv['total_energy'] > 0, "Dovetail energy > 0")

hyst_gap = mt.simulate_cyclic_loading('angle_brace_tenon', 0.03, 2, 40)
assert_test(hyst_gap['total_steps'] > 0, "Angle brace (with gap) cyclic produces steps")

# --- Boundary ---
print("\n--- Boundary Cases ---")

hyst_min = mt.simulate_cyclic_loading('straight_tenon', 0.001, 1, 10)
assert_test(hyst_min['total_steps'] > 0, "Minimal rotation (0.001) still produces steps")
energy_min = mt.compute_energy_dissipation(hyst_min)
assert_test(energy_min['equivalent_damping_ratio'] >= 0, "Minimal rotation damping >= 0")

hyst_max_rot = mt.simulate_cyclic_loading('straight_tenon', 0.1, 1, 20)
assert_test(hyst_max_rot['total_steps'] > 0, "Large rotation (0.1) still produces steps")

hyst_many = mt.simulate_cyclic_loading('straight_tenon', 0.02, 10, 20)
assert_test(hyst_many['final_stiffness_ratio'] <= hyst_min['final_stiffness_ratio'],
            "More cycles => more degradation")

moment_at_zero = mt._moment_from_rotation(st_props, 0.0)
assert_test(moment_at_zero == 0.0, "Zero rotation => zero moment")

moment_gap = mt._moment_from_rotation(ab_props, 0.001)
assert_test(moment_gap == 0.0, "Rotation within gap => zero moment (angle_brace)")

moment_past_gap = mt._moment_from_rotation(ab_props, 0.005)
assert_test(moment_past_gap > 0, "Rotation past gap => positive moment")

moment_negative = mt._moment_from_rotation(st_props, -0.01)
assert_test(moment_negative < 0, "Negative rotation => negative moment (symmetry)")

# --- Abnormal ---
print("\n--- Abnormal Cases ---")

try:
    mt.get_joint_type('nonexistent_tenon')
    assert_test(False, "get_joint_type('nonexistent') should raise ValueError")
except ValueError:
    assert_test(True, "get_joint_type('nonexistent') raises ValueError")

try:
    mt.simulate_cyclic_loading('nonexistent', 0.03, 3, 50)
    assert_test(False, "simulate_cyclic_loading with bad joint should raise ValueError")
except ValueError:
    assert_test(True, "simulate_cyclic_loading with bad joint raises ValueError")

try:
    mt.compute_backbone_curve('fake_joint')
    assert_test(False, "compute_backbone_curve with bad joint should raise ValueError")
except ValueError:
    assert_test(True, "compute_backbone_curve with bad joint raises ValueError")

try:
    mt.compare_joints(['straight_tenon', 'nonexistent'])
    assert_test(False, "compare_joints with bad ID should raise ValueError")
except ValueError:
    assert_test(True, "compare_joints with bad ID raises ValueError")

bb_all = mt.compute_backbone_curve('straight_tenon')
moments_bb = np.array(bb_all['moment_array'])
rotations_bb = np.array(bb_all['rotation_array'])
pos_mask = rotations_bb > 0
if np.any(pos_mask):
    pos_moments = moments_bb[pos_mask]
    peak_idx = np.argmax(pos_moments)
    assert_test(np.all(np.diff(pos_moments[:peak_idx + 1]) >= -1e-6),
                "Backbone positive branch non-decreasing up to peak")

neg_mask = rotations_bb < 0
if np.any(neg_mask):
    neg_moments = moments_bb[neg_mask][::-1]
    peak_idx = np.argmin(neg_moments)
    assert_test(np.all(np.diff(neg_moments[:peak_idx + 1]) <= 1e-6),
                "Backbone negative branch non-increasing down to peak")


# ============================================================
# MODULE 3: COLLAPSE SIMULATION
# ============================================================
print("\n" + "=" * 70)
print("MODULE 3: COLLAPSE SIMULATION -- Physical Realism Validation")
print("=" * 70)

cs = CollapseSimulator()

# --- Normal ---
print("\n--- Normal Cases ---")

assert_test(cs.floor_count == 5, "5 floors in default model")
assert_test(len(cs.floor_masses) == 5, "5 floor masses")
assert_test(len(cs.floor_stiffnesses) == 5, "5 floor stiffnesses")
assert_test(all(m > 0 for m in cs.floor_masses), "All floor masses > 0")
assert_test(all(k > 0 for k in cs.floor_stiffnesses), "All floor stiffnesses > 0")
assert_test(cs.column_diameter == 0.6, "Column diameter 0.6m")
assert_test(cs.joint_yield_moment > 0, "Joint yield moment > 0")
assert_test(cs.joint_ultimate_moment > cs.joint_yield_moment, "Mu > My")

for i in range(4):
    assert_test(cs.floor_stiffnesses[i] < cs.floor_stiffnesses[i + 1],
                "Floor stiffness increases with height (floor %d<%d)" % (i, i + 1))

for i in range(4):
    assert_test(cs.floor_masses[i] > cs.floor_masses[i + 1],
                "Floor mass decreases with height (floor %d>%d)" % (i, i + 1))

r_low = cs.run_collapse_simulation(0.1, 10.0, 0.05)
assert_test(r_low['collapse_mode'] == 'no_collapse', "0.1g => no collapse")
assert_test(r_low['max_drift_ratio'] > 0, "0.1g max_drift > 0")
assert_test(r_low['max_drift_ratio'] < 0.01, "0.1g max_drift < 0.01 (OP)")
assert_test(r_low['performance_summary']['performance_level'] == '正常使用 (OP)',
            "0.1g performance level = OP")

r_med = cs.run_collapse_simulation(0.4, 10.0, 0.05)
assert_test(r_med['max_drift_ratio'] > r_low['max_drift_ratio'],
            "0.4g drift > 0.1g drift (PGA monotonicity)")

r_high = cs.run_collapse_simulation(0.6, 10.0, 0.05)
assert_test(r_high['max_drift_ratio'] > r_med['max_drift_ratio'],
            "0.6g drift > 0.4g drift (PGA monotonicity)")

assert_test('time_history' in r_low, "Result has time_history")
assert_test('time_array' in r_low['time_history'], "time_history has time_array")
assert_test('displacement_mm' in r_low['time_history'], "time_history has displacement_mm")
assert_test('drift_ratios' in r_low['time_history'], "time_history has drift_ratios")
assert_test('damage_indices' in r_low['time_history'], "time_history has damage_indices")
assert_test('base_shear' in r_low['time_history'], "time_history has base_shear")

th_disp = np.array(r_low['time_history']['displacement_mm'])
assert_test(th_disp.shape[0] > 0 and th_disp.shape[1] == 5, "Displacement array shape (steps, 5)")

assert_test('failure_sequence' in r_low, "Result has failure_sequence")
assert_test('failure_events' in r_low, "Result has failure_events")
assert_test(r_low['failure_sequence'] == r_low['failure_events'], "failure_sequence = failure_events alias")

assert_test('input_energy' in r_low, "Result has input_energy")
assert_test(r_low['input_energy']['peak_acceleration_g'] == 0.1, "input_energy PGA = 0.1")
assert_test(r_low['input_energy']['arias_intensity'] > 0, "Arias intensity > 0")

assert_test(r_low['max_base_shear'] > 0, "Base shear > 0")
assert_test(r_low['base_shear_kN'] > 0, "Base shear kN > 0")
assert_test(approx_eq(r_low['base_shear_kN'], r_low['max_base_shear'] / 1000, 0.01),
            "base_shear_kN = max_base_shear / 1000")

perf_levels = ['正常使用 (OP)', '立即可用 (IO)', '生命安全 (LS)', '防倒塌 (CP)', '倒塌 (COLLAPSE)']
p_low = r_low['performance_summary']['performance_level']
assert_test(p_low in perf_levels, "Performance level is valid enum value")

cap = cs.evaluate_ultimate_capacity(start_pga=0.1, end_pga=1.5, pga_step=0.1)
assert_test(cap['yield_pga_g'] > 0, "Yield PGA > 0")
assert_test(cap['collapse_pga_g'] >= cap['yield_pga_g'], "Collapse PGA >= Yield PGA")
assert_test(cap['overstrength_factor'] >= 1.0, "Overstrength factor >= 1.0")
assert_test(cap['safety_reserve_ratio'] > 1.0, "Safety reserve > 1.0 (vs 8-degree 0.16g)")
assert_test(len(cap['capacity_curve']) > 0, "Capacity curve has points")
assert_test(len(cap['pushover_curve']) == len(cap['capacity_curve']), "pushover_curve alias = capacity_curve")
assert_test('performance_levels' in cap, "Result has performance_levels")
pl = cap['performance_levels']
assert_test(pl['operational_pga'] < pl['immediate_occupancy_pga'], "OP PGA < IO PGA")
assert_test(pl['immediate_occupancy_pga'] < pl['life_safety_pga'], "IO PGA < LS PGA")
assert_test(pl['life_safety_pga'] < pl['collapse_prevention_pga'], "LS PGA < CP PGA")

cap_curve = cap['capacity_curve']
for i in range(1, len(cap_curve)):
    assert_test(cap_curve[i]['pga'] > cap_curve[i - 1]['pga'],
                "Capacity curve PGA monotonically increasing (point %d)" % i)

t_motion, a_motion = cs.generate_earthquake_motion(0.3, 10.0, 0.01, seed=42)
assert_test(len(t_motion) > 0, "Earthquake motion time array non-empty")
assert_test(len(a_motion) == len(t_motion), "Acceleration array same length as time")
assert_test(approx_eq(np.max(np.abs(a_motion)) / 9.81, 0.3, 0.1),
            "Peak acceleration ~ 0.3g (PGA)")

t2, a2 = cs.generate_earthquake_motion(0.3, 10.0, 0.01, seed=42)
assert_test(np.allclose(a_motion, a2), "Same seed => reproducible earthquake motion")

avg_h = float(np.mean(cs.floor_heights))
yield_d = cs.joint_yield_moment / (cs.joint_stiffness * 0.8 * avg_h)
ult_d = cs.joint_ultimate_moment / (0.3 * cs.joint_stiffness * avg_h)
assert_test(1.0 / 500 < yield_d < 1.0 / 200, "Yield drift in realistic range (1/500~1/200)")
assert_test(1.0 / 100 < ult_d < 1.0 / 50, "Ultimate drift in realistic range (1/100~1/50)")

# --- Boundary ---
print("\n--- Boundary Cases ---")

r_tiny = cs.run_collapse_simulation(0.001, 5.0, 0.05)
assert_test(r_tiny['max_drift_ratio'] < 0.001, "Tiny PGA 0.001g => very small drift")
assert_test(r_tiny['performance_summary']['performance_level'] == '正常使用 (OP)',
            "Tiny PGA => OP level")

r_extreme = cs.run_collapse_simulation(3.0, 10.0, 0.05)
assert_test(r_extreme['max_drift_ratio'] > r_high['max_drift_ratio'],
            "3.0g drift > 0.6g drift")

r_short = cs.run_collapse_simulation(0.3, 5.0, 0.05)
assert_test('time_history' in r_short, "Short duration 5s produces valid result")
th_t = np.array(r_short['time_history']['time_array'])
assert_test(abs(th_t[-1] - 5.0) < 0.5, "Time array ends near duration")

r_long = cs.run_collapse_simulation(0.3, 60.0, 0.1)
assert_test('time_history' in r_long, "Long duration 60s produces valid result")

r_small_dt = cs.run_collapse_simulation(0.3, 10.0, 0.005)
assert_test(r_small_dt['max_drift_ratio'] > 0, "Small dt 0.005 produces valid drift")

r_large_dt = cs.run_collapse_simulation(0.3, 10.0, 0.1)
assert_test(r_large_dt['max_drift_ratio'] > 0, "Large dt 0.1 produces valid drift")

cap_narrow = cs.evaluate_ultimate_capacity(start_pga=0.3, end_pga=0.5, pga_step=0.1)
assert_test(len(cap_narrow['capacity_curve']) >= 2, "Narrow PGA range produces >= 2 points")

t_ramp, a_ramp = cs.generate_earthquake_motion(0.5, 20.0, 0.01, seed=99)
assert_test(a_ramp[0] < np.max(np.abs(a_ramp)) * 0.3, "Motion starts with ramp-up")

n_steps_10 = int(10.0 / 0.01) + 1
n_steps_30 = int(30.0 / 0.01) + 1
t10, _ = cs.generate_earthquake_motion(0.3, 10.0, 0.01)
t30, _ = cs.generate_earthquake_motion(0.3, 30.0, 0.01)
assert_test(len(t10) == n_steps_10, "10s duration => correct step count")
assert_test(len(t30) == n_steps_30, "30s duration => correct step count")

cap_fine = cs.evaluate_ultimate_capacity(start_pga=0.2, end_pga=1.0, pga_step=0.05)
cap_coarse = cs.evaluate_ultimate_capacity(start_pga=0.2, end_pga=1.0, pga_step=0.2)
assert_test(len(cap_fine['capacity_curve']) >= len(cap_coarse['capacity_curve']),
            "Finer step => more capacity curve points")

# --- Abnormal ---
print("\n--- Abnormal Cases ---")

r_zero_pga = cs.run_collapse_simulation(0.0, 10.0, 0.05)
assert_test(isinstance(r_zero_pga, dict), "Zero PGA does not crash (returns dict)")
assert_test(r_zero_pga['max_drift_ratio'] >= 0, "Zero PGA drift >= 0")

r_neg_pga = cs.run_collapse_simulation(-0.1, 10.0, 0.05)
assert_test(isinstance(r_neg_pga, dict), "Negative PGA does not crash")

cs_single = CollapseSimulator(floor_count=1, floor_heights=[6.0], floor_diameters=[20.0])
r_single = cs_single.run_collapse_simulation(0.3, 10.0, 0.05)
assert_test(r_single['max_drift_ratio'] > 0, "Single-floor model still works")

try:
    cs_bad = CollapseSimulator(floor_count=3, floor_heights=[6.0, 5.0], floor_diameters=[20.0, 15.0])
    assert_test(False, "Mismatched floor_count/heights should fail")
except (IndexError, ValueError):
    assert_test(True, "Mismatched floor_count/heights raises error correctly")

cs_very_soft = CollapseSimulator(joint_stiffness=1e4, joint_yield_moment=100, joint_ultimate_moment=200)
r_soft = cs_very_soft.run_collapse_simulation(0.3, 10.0, 0.05)
assert_test(isinstance(r_soft, dict), "Very soft structure does not crash")

cs_very_stiff = CollapseSimulator(joint_stiffness=1e12, joint_yield_moment=1e10, joint_ultimate_moment=2e10)
r_stiff = cs_very_stiff.run_collapse_simulation(0.3, 10.0, 0.05)
assert_test(isinstance(r_stiff, dict), "Very stiff structure does not crash")


# ============================================================
# MODULE 4: VIRTUAL EXPERIENCE
# ============================================================
print("\n" + "=" * 70)
print("MODULE 4: VIRTUAL EXPERIENCE -- Interaction & Immersion")
print("=" * 70)

ve = VirtualExperienceService()
calc = ve.calculator

# --- Normal ---
print("\n--- Normal Cases ---")

paths = ve.paths
assert_test('default' in paths, "Default path exists")
default_path = paths['default']
assert_test(len(default_path.waypoints) == 8, "Default path has 8 waypoints")
assert_test(default_path.total_length > 0, "Total path length > 0")

pos_start = default_path.get_position_at_time(0.0)
assert_test(pos_start['waypoint_name'] == '塔基入口', "Time=0 => starting waypoint")
assert_test(pos_start['progress'] == 0.0, "Time=0 => progress=0%")
assert_test(pos_start['y'] == 0.0, "Time=0 => Y=0")

pos_end = default_path.get_position_at_time(7.0)
assert_test(pos_end['progress'] == 1.0, "Time=7 => progress=100%")
assert_test(pos_end['waypoint_name'] == '塔顶观景台', "Time=7 => top waypoint")

pos_mid = default_path.get_position_at_time(3.5)
assert_test(0 < pos_mid['progress'] < 1.0, "Mid-time => 0<progress<1")
assert_test(0 < pos_mid['y'] < 30.74, "Mid-time => intermediate height")

ses = ve.start_experience(user_id=1)
assert_test('session_id' in ses, "Session has session_id")
assert_test(ses['status'] == 'active', "Session status = active")
assert_test(ses['total_waypoints'] == 8, "Session total_waypoints = 8")
sid = ses['session_id']

update1 = ve.update_experience(sid, time_elapsed=0, wind_speed=5.0, earthquake_pga=0.0)
assert_test(update1.get('active') == True, "Update at t=0 still active")
assert_test('position' in update1, "Update has position")
assert_test('wind_response' in update1, "Update has wind_response")
assert_test('sensory_data' in update1, "Update has sensory_data")
assert_test('floor_description' in update1, "Update has floor_description")

update2 = ve.update_experience(sid, time_elapsed=4, wind_speed=15.0, earthquake_pga=0.02)
pos2 = update2['position']
assert_test(pos2['y'] > 0, "At t=4, height > 0")
wr2 = update2['wind_response']
assert_test(wr2['displacement_x_mm'] > 0, "Wind displacement > 0 at 15m/s")
assert_test(wr2['comfort_level'] in ['无感', '有感', '不适', '难以忍受'],
            "Comfort level is valid enum")

sn2 = update2['sensory_data']
assert_test('visual' in sn2, "Sensory data has visual")
assert_test('auditory' in sn2, "Sensory data has auditory")
assert_test('tactile' in sn2, "Sensory data has tactile")
assert_test('kinesthetic' in sn2, "Sensory data has kinesthetic")
assert_test(sn2['visual']['sway_amplitude_mm'] >= 0, "Visual sway >= 0")
assert_test(sn2['visual']['sway_magnitude_mm'] >= 0, "Visual sway_magnitude alias >= 0")
assert_test(sn2['auditory']['wind_noise_db'] >= 0, "Wind noise dB >= 0")
assert_test(sn2['auditory']['noise_level_db'] >= 0, "Noise level dB alias >= 0")
assert_test(sn2['auditory']['wind_noise_db'] <= 120, "Wind noise dB <= 120")

fd1 = ve.get_floor_description(1)
assert_test('architecture_features' in fd1, "Floor 1 has architecture_features")
assert_test('buddha_info' in fd1, "Floor 1 has buddha_info")
assert_test('view_description' in fd1, "Floor 1 has view_description")

fd3 = ve.get_floor_description(3)
assert_test('结构加固' in fd3['architecture_features'] or '斜撑' in fd3['architecture_features'],
            "Floor 3 is the structural reinforcement floor")

fd5 = ve.get_floor_description(5)
assert_test('明层' in fd5['architecture_features'] or '佛殿' in fd5['architecture_features'],
            "Floor 5 has description referencing top floor")

wr_calm = calc.compute_wind_response(2.0, 10.0, 1)
assert_test(wr_calm['displacement_x_mm'] < 1.0, "Calm wind 2m/s => displacement < 1mm")
assert_test(wr_calm['comfort_level'] == '无感', "Calm wind => comfort = none")

wr_storm = calc.compute_wind_response(30.0, 30.0, 5)
assert_test(wr_storm['displacement_x_mm'] > wr_calm['displacement_x_mm'],
            "Storm wind => more displacement than calm")

wr_low_h = calc.compute_wind_response(15.0, 5.0, 1)
wr_high_h = calc.compute_wind_response(15.0, 40.0, 5)
assert_test(wr_high_h['displacement_x_mm'] > wr_low_h['displacement_x_mm'],
            "Higher position => more wind displacement")

sd_ground = calc.compute_sensory_data(1, 10.0, 0.0)
sd_top = calc.compute_sensory_data(5, 25.0, 0.0)
assert_test(sd_top['tactile']['temperature'] < sd_ground['tactile']['temperature'],
            "Higher floor => lower temperature")

assert_test(sd_ground['kinesthetic']['stair_slope'] > 0, "Interior floors have stairs")
assert_test(sd_ground['kinesthetic']['handrail_force'] >= 0, "Handrail force >= 0")

update_eq = ve.update_experience(sid, time_elapsed=5, wind_speed=5.0, earthquake_pga=0.1)
sn_eq = update_eq['sensory_data']
assert_test(sn_eq['kinesthetic']['floor_tilt_degrees'] > 0,
            "Earthquake PGA > 0 => floor tilt > 0")

wind_disp_low = calc.compute_wind_response(20.0, 10.0, 1)
wind_disp_high = calc.compute_wind_response(20.0, 50.0, 5)
assert_test(wind_disp_high['height_factor'] > wind_disp_low['height_factor'],
            "Higher position => larger height factor")

# --- Boundary ---
print("\n--- Boundary Cases ---")

pos_before = default_path.get_position_at_time(-10.0)
assert_test(pos_before['progress'] == 0.0, "Negative time => progress=0%")

pos_after = default_path.get_position_at_time(100.0)
assert_test(pos_after['progress'] == 1.0, "Very large time => progress=100%")

ses2 = ve.start_experience(user_id=2, path_id='nonexistent')
assert_test(ses2['start_position']['waypoint_name'] == '塔基入口',
            "Nonexistent path falls back to default (start at base)")

update_zero = ve.update_experience(sid, time_elapsed=0, wind_speed=0.0, earthquake_pga=0.0)
assert_test(update_zero['wind_response']['displacement_x_mm'] == 0.0,
            "Zero wind => zero displacement")

wr_zero_h = calc.compute_wind_response(10.0, 0.0, 1)
assert_test(wr_zero_h['displacement_x_mm'] == 0.0, "Zero height => zero displacement")

sd_no_wind = calc.compute_sensory_data(1, 0.0, 0.0)
assert_test(sd_no_wind['visual']['sway_amplitude_mm'] == 0.0, "No wind => no visual sway")

fd_default = ve.get_floor_description(0)
assert_test(fd_default.get('name') == '未知楼层', "Floor 0 returns default description")

fd_over = ve.get_floor_description(10)
assert_test(fd_over.get('name') == '未知楼层', "Floor 10 returns default description")

floor_at = default_path.get_floor_at_position(6.0)
assert_test(floor_at == 1, "Height 6.0m => floor 1")
floor_at_top = default_path.get_floor_at_position(30.0)
assert_test(floor_at_top == 5, "Height 30.0m => floor 5")

update_top = ve.update_experience(sid, time_elapsed=7, wind_speed=10.0, earthquake_pga=0.0)
pos_top = update_top['position']
assert_test(pos_top['floor'] == 5, "At top => floor 5")

wr_huge_wind = calc.compute_wind_response(100.0, 30.0, 5)
assert_test(isinstance(wr_huge_wind['displacement_x_mm'], float), "Extreme wind 100m/s does not crash")

# --- Abnormal ---
print("\n--- Abnormal Cases ---")

result_bad = ve.update_experience('nonexistent-session-id', 5, 10.0, 0.0)
assert_test('error' in result_bad or result_bad.get('active') == False,
            "Update with nonexistent session returns error or inactive")

wr_neg_wind = calc.compute_wind_response(-10.0, 20.0, 3)
assert_test(isinstance(wr_neg_wind, dict), "Negative wind speed does not crash")

sd_neg_pga = calc.compute_sensory_data(2, 10.0, -0.1)
assert_test(isinstance(sd_neg_pga, dict), "Negative PGA does not crash")

sd_floor_0 = calc.compute_sensory_data(0, 10.0, 0.0)
assert_test(isinstance(sd_floor_0, dict), "Floor 0 sensory data does not crash")

sd_floor_99 = calc.compute_sensory_data(99, 10.0, 0.0)
assert_test(isinstance(sd_floor_99, dict), "Floor 99 sensory data does not crash")

wr_neg_height = calc.compute_wind_response(10.0, -5.0, 1)
assert_test(isinstance(wr_neg_height, dict), "Negative height does not crash")

many_sessions = [ve.start_experience(user_id=i) for i in range(10)]
assert_test(len(many_sessions) == 10, "10 concurrent sessions created")
assert_test(len(set(s['session_id'] for s in many_sessions)) == 10, "All session IDs unique")


# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 70)
total = PASS_COUNT + FAIL_COUNT
if FAIL_COUNT == 0:
    print("[PASS] ALL %d TESTS PASSED (0 failures)" % total)
else:
    print("[FAIL] %d/%d tests FAILED" % (FAIL_COUNT, total))
    sys.exit(1)
print("=" * 70)
