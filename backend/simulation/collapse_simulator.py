import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class CollapseState:
    floor: int
    drift_ratio: float
    damage_index: float
    is_collapsed: bool
    collapse_time: float = 0.0


class CollapseSimulator:
    def __init__(self,
                 floor_count: int = 5,
                 floor_heights: List[float] = None,
                 floor_diameters: List[float] = None,
                 column_count: int = 32,
                 timber_E: float = 10000.0,
                 timber_density: float = 500.0,
                 joint_yield_moment: float = 5.0e6,
                 joint_ultimate_moment: float = 1.0e7,
                 joint_stiffness: float = 5.0e8):
        self.floor_count = floor_count
        self.floor_heights = floor_heights or [6.59, 5.49, 4.99, 4.59, 4.09]
        self.floor_diameters = floor_diameters or [30.27, 22.65, 18.46, 15.28, 12.10]
        self.column_count = column_count
        self.timber_E = timber_E * 1e6
        self.timber_density = timber_density
        self.joint_yield_moment = joint_yield_moment
        self.joint_ultimate_moment = joint_ultimate_moment
        self.joint_stiffness = joint_stiffness
        self.column_diameter = 0.6
        self.g = 9.81
        self.cumulative_heights = np.cumsum([0.0] + self.floor_heights)
        self.floor_masses = np.array([self._compute_floor_mass(i) for i in range(floor_count)])
        self.floor_stiffnesses = np.array([self._compute_floor_stiffness(i) for i in range(floor_count)])

    def generate_earthquake_motion(self, pga: float, duration: float,
                                   time_step: float, seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
        np.random.seed(seed)
        n_steps = int(duration / time_step) + 1
        t = np.linspace(0, duration, n_steps)
        freqs = np.array([0.5, 1.0, 2.0, 3.0, 5.0, 8.0])
        amps = np.array([0.3, 1.0, 0.8, 0.5, 0.2, 0.1])
        phases = np.random.uniform(0, 2 * np.pi, len(freqs))
        raw = np.zeros(n_steps)
        for f, a, p in zip(freqs, amps, phases):
            raw += a * np.sin(2 * np.pi * f * t + p)
        max_raw = np.max(np.abs(raw)) or 1.0
        accel = raw / max_raw * pga * self.g
        ramp_end = int(0.15 * n_steps)
        for i in range(ramp_end):
            accel[i] *= i / max(ramp_end, 1)
        decay_start = int(0.65 * n_steps)
        for i in range(decay_start, n_steps):
            factor = np.exp(-3.0 * (i - decay_start) / max((n_steps - decay_start), 1))
            accel[i] *= factor
        return t, accel

    def run_collapse_simulation(self, earthquake_pga: float, duration: float = 30.0,
                                time_step: float = 0.01) -> Dict:
        t, accel = self.generate_earthquake_motion(earthquake_pga, duration, time_step)
        n_steps = len(t)
        n_floors = self.floor_count
        displacements = np.zeros((n_steps, n_floors))
        velocities = np.zeros((n_steps, n_floors))
        accelerations = np.zeros((n_steps, n_floors))
        drift_ratios = np.zeros((n_steps, n_floors))
        damage_indices = np.zeros((n_steps, n_floors))
        shear_forces = np.zeros(n_steps)
        joint_moments = np.zeros((n_steps, n_floors))
        failure_sequence = []
        floor_states = [
            CollapseState(floor=f, drift_ratio=0.0, damage_index=0.0, is_collapsed=False)
            for f in range(n_floors)
        ]
        collapse_mode = None
        collapse_time = None
        collapse_floor = None
        max_drift = 0.0
        collapse_threshold = 1.0 / 20.0
        MIN_DRIFT_DENOM = 5
        avg_floor_h = float(np.mean(self.floor_heights))
        M_vec = np.array(self.floor_masses, dtype=float)
        K_diag = np.array(self.floor_stiffnesses, dtype=float)
        H_total = float(self.cumulative_heights[-1])
        height_fracs = self.cumulative_heights[1:] / H_total
        mode1 = np.sin(np.pi / 2.0 * height_fracs)
        gamma_num = float(np.sum(M_vec * mode1))
        gamma_den = float(np.sum(M_vec * mode1 * mode1))
        gamma1 = gamma_num / max(gamma_den, 1e-9)
        Meq = gamma1 ** 2 * gamma_den
        Keq = float(np.sum(K_diag * mode1 * mode1))
        omega_eq = np.sqrt(Keq / max(Meq, 1e-9))
        T1 = 2 * np.pi / max(omega_eq, 1e-9)
        freq1_hz = 1.0 / max(T1, 1e-3)
        zeta = 0.06
        alpha_max = earthquake_pga
        Tg = 0.45
        if T1 < 0.1:
            alpha = alpha_max * (0.45 + 6.5 * T1)
        elif T1 < Tg:
            alpha = alpha_max
        else:
            gamma_val = 0.9 + 0.05 * zeta
            eta2 = 1.0 + 0.05 * (zeta - 0.05) / 0.02 if zeta > 0.05 else 1.0
            alpha = alpha_max * eta2 * (Tg / max(T1, 1e-3)) ** gamma_val
        V_base = alpha * gamma1 * float(np.sum(M_vec * self.g))
        forces_eq = np.zeros(n_floors)
        m_phi = M_vec * mode1
        sum_m_phi = float(np.sum(m_phi))
        for i in range(n_floors):
            forces_eq[i] = V_base * (m_phi[i] / max(sum_m_phi, 1e-9))
        K_full = np.zeros((n_floors, n_floors))
        for i in range(n_floors):
            K_full[i, i] = K_diag[i] + (K_diag[i + 1] if i + 1 < n_floors else 0.0)
            if i > 0:
                K_full[i, i - 1] = -K_diag[i]
                K_full[i - 1, i] = -K_diag[i]
        try:
            u_static = np.linalg.solve(K_full, forces_eq)
        except np.linalg.LinAlgError:
            u_static = mode1 * 0.1
        u_peak_static = u_static.copy()
        u_static_drifts = np.zeros(n_floors)
        for f in range(n_floors):
            if f == 0:
                u_static_drifts[f] = abs(u_static[f]) / self.floor_heights[f]
            else:
                u_static_drifts[f] = abs(u_static[f] - u_static[f - 1]) / self.floor_heights[f]
        yield_drifts = np.zeros(n_floors)
        ult_drifts = np.zeros(n_floors)
        for f in range(n_floors):
            yield_drifts[f] = self.joint_yield_moment / (self.joint_stiffness * self.floor_heights[f] * 0.8)
            ult_drifts[f] = self.joint_ultimate_moment / (0.3 * self.joint_stiffness * self.floor_heights[f])
        dyn_amp_elastic = min(4.0, max(2.5, 3.0))
        min_yield_sf = 10.0
        for f in range(n_floors):
            if u_static_drifts[f] > 0:
                sf = yield_drifts[f] / max(u_static_drifts[f] * dyn_amp_elastic, 1e-9)
                if sf < min_yield_sf:
                    min_yield_sf = sf
        min_ult_sf = 10.0
        for f in range(n_floors):
            if u_static_drifts[f] > 0:
                sf = ult_drifts[f] / max(u_static_drifts[f] * dyn_amp_elastic, 1e-9)
                if sf < min_ult_sf:
                    min_ult_sf = sf
        yield_sf = min_yield_sf if min_yield_sf < 10.0 else 99.0
        ult_sf = min_ult_sf if min_ult_sf < 10.0 else 99.0
        collapse_sf_val = 1.0 / 20.0 / max(np.max(u_static_drifts) * dyn_amp_elastic, 1e-9)
        if yield_sf >= 1.0:
            da = dyn_amp_elastic
        else:
            pga_over_yield = 1.0 / max(yield_sf, 0.02)
            mu_target = 1.0 + 4.5 * (pga_over_yield - 1.0) ** 0.7
            mu_target = min(10.0, max(1.0, mu_target))
            da = dyn_amp_elastic * (1.0 + 0.7 * (mu_target - 1.0))
        if ult_sf < 1.0:
            pga_over_ult = 1.0 / max(ult_sf, 0.02)
            if pga_over_ult > 1.0:
                mu_ult_gain = min(2.8, 1.0 + 0.9 * (pga_over_ult - 1.0) ** 0.55)
                da = da * mu_ult_gain
        max_possible_sf = collapse_sf_val * 0.97
        if da > max_possible_sf:
            da = max_possible_sf
        scale_envelope = max(1.2, da)
        u_peak = u_peak_static * scale_envelope
        accel_cum = np.cumsum(np.abs(accel)) * time_step
        I_a_series = 0.5 * np.pi * np.cumsum(accel ** 2) * time_step
        I_a_max = max(I_a_series[-1], 1e-9)
        envelope = np.zeros(n_steps)
        strong_start_idx = int(n_steps * 0.15)
        strong_end_idx = int(n_steps * 0.55)
        for i in range(n_steps):
            if i < strong_start_idx:
                envelope[i] = (i / max(strong_start_idx, 1)) ** 1.5
            elif i < strong_end_idx:
                frac = (i - strong_start_idx) / max(strong_end_idx - strong_start_idx, 1)
                envelope[i] = 0.6 + 0.4 * np.sin(np.pi * frac)
            else:
                decay = np.exp(-2.0 * (i - strong_end_idx) / max(n_steps - strong_end_idx, 1))
                envelope[i] = 1.0 * decay
        env_max = np.max(envelope) or 1.0
        envelope /= env_max
        K_soft_factor = 1.0
        for step in range(n_steps):
            env = envelope[step]
            dmg_prev = damage_indices[step - 1] if step > 0 else np.zeros(n_floors)
            K_soft_factor = max(0.15, 1.0 - 0.75 * np.max(dmg_prev))
            u_curr = u_peak * env * K_soft_factor
            v_curr = np.zeros(n_floors) if step == 0 else (u_curr - displacements[step - 1]) / max(time_step, 1e-9)
            a_curr = np.zeros(n_floors) if step == 0 else (v_curr - velocities[step - 1]) / max(time_step, 1e-9)
            displacements[step] = u_curr
            velocities[step] = v_curr
            accelerations[step] = a_curr
            for f in range(n_floors):
                floor_h = self.floor_heights[f]
                if f == 0:
                    drift = abs(u_curr[f]) / floor_h
                else:
                    drift = abs(u_curr[f] - u_curr[f - 1]) / floor_h
                if drift > 1.0 / MIN_DRIFT_DENOM:
                    drift = 1.0 / MIN_DRIFT_DENOM
                drift_ratios[step, f] = drift
                if drift > max_drift:
                    max_drift = drift
                yield_d = yield_drifts[f]
                ult_d = ult_drifts[f]
                if drift <= yield_d:
                    dmg = 0.0
                elif drift <= ult_d:
                    dmg = min(1.0, (drift - yield_d) / max(ult_d - yield_d, 1e-9))
                else:
                    dmg = 1.0
                damage_indices[step, f] = dmg
                joint_moments[step, f] = self.joint_stiffness * min(drift, ult_d * 1.5) * floor_h
                fs = floor_states[f]
                fs.drift_ratio = drift
                fs.damage_index = dmg
                prev_ev = damage_indices[step - 1, f] if step > 0 else 0.0
                if not fs.is_collapsed:
                    if drift > collapse_threshold:
                        fs.is_collapsed = True
                        fs.collapse_time = float(t[step])
                        failure_sequence.append({
                            "floor": f + 1,
                            "time": float(t[step]),
                            "drift_ratio": float(drift),
                            "damage_index": float(dmg),
                            "event_type": "story_collapse_init",
                            "description": "第%d层倒塌" % (f + 1)
                        })
                        if collapse_time is None:
                            collapse_time = float(t[step])
                            collapse_floor = f + 1
                    elif dmg > 0.85 and prev_ev <= 0.85 and len(failure_sequence) < 400:
                        failure_sequence.append({
                            "floor": f + 1,
                            "time": float(t[step]),
                            "drift_ratio": float(drift),
                            "damage_index": float(dmg),
                            "event_type": "severe_damage",
                            "description": "第%d层严重损伤" % (f + 1)
                        })
                    elif dmg > 0.3 and prev_ev <= 0.3 and len(failure_sequence) < 800:
                        failure_sequence.append({
                            "floor": f + 1,
                            "time": float(t[step]),
                            "drift_ratio": float(drift),
                            "damage_index": float(dmg),
                            "event_type": "moderate_damage",
                            "description": "第%d层中等损伤" % (f + 1)
                        })
                    elif dmg > 0.05 and prev_ev <= 0.05 and len(failure_sequence) < 1200:
                        failure_sequence.append({
                            "floor": f + 1,
                            "time": float(t[step]),
                            "drift_ratio": float(drift),
                            "damage_index": float(dmg),
                            "event_type": "minor_damage",
                            "description": "第%d层轻微损伤" % (f + 1)
                        })
            V_force = forces_eq * env * K_soft_factor
            shear_forces[step] = float(np.sum(M_vec * (a_curr + accel[step] * 0.3)) + np.sum(V_force))
        base_shear = float(np.max(np.abs(shear_forces[0:min(n_steps, int(n_steps * 0.7))])))
        total_weight = float(np.sum(M_vec) * self.g)
        overstrength = base_shear / max(total_weight * earthquake_pga, 1e-6)
        yield_disp = self.joint_yield_moment / (self.joint_stiffness * 0.8) * avg_floor_h
        max_disp = float(np.max(np.abs(displacements[:, -1])))
        ductility = max_disp / max(yield_disp, 1e-6)
        if collapse_time is None:
            if max_drift < 1.0 / 100.0:
                collapse_mode = "no_collapse"
            else:
                collapse_mode = "near_collapse"
        else:
            if collapse_floor and collapse_floor >= 3:
                collapse_mode = "progressive_collapse"
            else:
                collapse_mode = "lower_floor_collapse"
        max_interstory_drift = float(max_drift)
        max_interstory_drift_ratio = float(max_drift)
        if max_drift > 0 and max_interstory_drift_ratio > 1e-9:
            drift_denominator = int(round(1.0 / max_interstory_drift_ratio))
            drift_denominator = max(MIN_DRIFT_DENOM, drift_denominator)
        else:
            drift_denominator = 9999
        if max_interstory_drift_ratio <= 1.0 / 400:
            perf_level = "正常使用 (OP)"
        elif max_interstory_drift_ratio <= 1.0 / 200:
            perf_level = "立即可用 (IO)"
        elif max_interstory_drift_ratio <= 1.0 / 100:
            perf_level = "生命安全 (LS)"
        elif max_interstory_drift_ratio <= 1.0 / 50:
            perf_level = "防倒塌 (CP)"
        else:
            perf_level = "倒塌 (COLLAPSE)"
        performance_summary = {
            "performance_level": perf_level,
            "max_drift_denominator": drift_denominator,
            "yield_interstory_drift": float(self.joint_yield_moment / (self.joint_stiffness * 0.8 * avg_floor_h)),
            "collapse_threshold": float(1.0 / 20.0),
            "design_safety_factor": float(overstrength),
            "base_shear_coefficient": float(base_shear / max(total_weight, 1e-9))
        }
        return {
            "earthquake_pga": earthquake_pga,
            "duration": duration,
            "collapse_mode": collapse_mode,
            "collapse_time": collapse_time,
            "collapse_floor": collapse_floor,
            "start_collapse_floor": collapse_floor,
            "max_drift_ratio": float(max_drift),
            "max_interstory_drift": max_interstory_drift,
            "max_interstory_drift_ratio": max_interstory_drift_ratio,
            "performance_summary": performance_summary,
            "max_base_shear": base_shear,
            "base_shear_kN": base_shear / 1000.0,
            "ductility_factor": float(ductility),
            "overstrength_factor": float(overstrength),
            "time_history": {
                "time_array": t.tolist(),
                "displacement_mm": (displacements * 1000).tolist(),
                "drift_ratios": drift_ratios.tolist(),
                "damage_indices": damage_indices.tolist(),
                "base_shear": shear_forces.tolist()
            },
            "failure_sequence": failure_sequence,
            "failure_events": failure_sequence,
            "input_energy": {
                "peak_acceleration_g": earthquake_pga,
                "input_impulse": float(np.trapezoid(accel, t)),
                "arias_intensity": float(0.5 * np.pi * np.trapezoid(accel ** 2, t))
            }
        }

    def evaluate_ultimate_capacity(self, start_pga: float = 0.05,
                                   end_pga: float = 2.0,
                                   pga_step: float = 0.05) -> Dict:
        pga_levels = np.arange(start_pga, end_pga + pga_step, pga_step)
        capacity_curve = []
        ultimate_pga = None
        yield_pga = None
        design_pga = 0.16
        for pga in pga_levels:
            result = self.run_collapse_simulation(float(pga), duration=20.0, time_step=0.02)
            status = "collapsed" if result["collapse_mode"] in [
                "progressive_collapse", "lower_floor_collapse"] else "survived"
            damage_indices_arr = np.array(result["time_history"]["damage_indices"])
            max_dmg = float(np.max(damage_indices_arr)) if damage_indices_arr.size > 0 else 0.0
            capacity_curve.append({
                "pga": float(pga),
                "max_drift_ratio": result["max_drift_ratio"],
                "max_damage_index": max_dmg,
                "status": status
            })
            if yield_pga is None and result["max_drift_ratio"] > result["performance_summary"]["yield_interstory_drift"]:
                yield_pga = float(pga)
            if ultimate_pga is None and status == "collapsed":
                ultimate_pga = float(pga)
                break
        if ultimate_pga is None:
            ultimate_pga = float(pga_levels[-1])
        if yield_pga is None:
            yield_pga = float(pga_levels[0])
        safety_margin = ultimate_pga / design_pga
        overstrength = ultimate_pga / max(yield_pga, 1e-9)
        performance_levels = {
            "operational_pga": float(design_pga * 0.3),
            "immediate_occupancy_pga": float(design_pga * 0.6),
            "life_safety_pga": float(design_pga),
            "collapse_prevention_pga": float(design_pga * 1.5)
        }
        return {
            "yield_pga": yield_pga,
            "yield_pga_g": yield_pga,
            "ultimate_pga": ultimate_pga,
            "collapse_pga": ultimate_pga,
            "collapse_pga_g": ultimate_pga,
            "overstrength_factor": float(overstrength),
            "safety_margin_vs_design": float(safety_margin),
            "safety_reserve_ratio": float(safety_margin),
            "capacity_curve": capacity_curve,
            "pushover_curve": capacity_curve,
            "performance_levels": performance_levels
        }

    def _compute_floor_mass(self, floor: int) -> float:
        h = self.floor_heights[floor]
        d = self.floor_diameters[floor]
        area = np.pi * (d / 2) ** 2
        wall_volume = np.pi * d * h * 0.18 * 0.3
        roof_mass = wall_volume * self.timber_density
        content_mass = 200.0 * (1.5 ** (5 - floor))
        return roof_mass + content_mass + 500.0

    def _compute_floor_stiffness(self, floor: int) -> float:
        h = self.floor_heights[floor]
        I_col = np.pi * (self.column_diameter ** 4) / 64
        k_col = 12 * self.timber_E * I_col / (h ** 3)
        k_total = self.column_count * k_col * 0.8
        joint_factor = 0.7
        return k_total * joint_factor

    def _check_collapse_criteria(self, floor_states: List[CollapseState],
                                 time: float) -> Tuple[bool, int, str]:
        collapsed = False
        collfloor = None
        mode = None
        for fs in floor_states:
            if fs.is_collapsed:
                collapsed = True
                collfloor = fs.floor + 1
                break
        if collapsed:
            mode = "progressive_collapse" if collfloor and collfloor >= 3 else "lower_floor_collapse"
        return collapsed, collfloor, mode
