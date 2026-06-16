import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Callable
from functools import lru_cache
import time

try:
    import cupy as cp
    _HAS_CUPY = True
except ImportError:
    cp = np
    _HAS_CUPY = False


def _to_numpy(arr):
    if _HAS_CUPY and hasattr(arr, 'get'):
        return cp.asnumpy(arr)
    return np.asarray(arr)


@dataclass
class AcceleratorInfo:
    use_gpu: bool = False
    device_name: str = "CPU (NumPy)"
    memory_used_mb: float = 0.0
    vectorization_enabled: bool = True
    cache_hit_rate: float = 0.0


@dataclass
class CollapseState:
    floor: int
    drift_ratio: float
    damage_index: float
    is_collapsed: bool
    collapse_time: float = 0.0


class CollapseSimulator:
    _capacity_cache: Dict[Tuple, Dict] = {}

    def __init__(self,
                 floor_count: int = 5,
                 floor_heights: List[float] = None,
                 floor_diameters: List[float] = None,
                 column_count: int = 32,
                 timber_E: float = 10000.0,
                 timber_density: float = 500.0,
                 joint_yield_moment: float = 5.0e6,
                 joint_ultimate_moment: float = 1.0e7,
                 joint_stiffness: float = 5.0e8,
                 use_gpu: Optional[bool] = None):
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
        self.use_gpu = bool(use_gpu) if use_gpu is not None else _HAS_CUPY
        self.xp = cp if self.use_gpu else np
        self.cumulative_heights = np.cumsum([0.0] + self.floor_heights)
        self.floor_masses = np.array([self._compute_floor_mass(i) for i in range(floor_count)])
        self.floor_stiffnesses = np.array([self._compute_floor_stiffness(i) for i in range(floor_count)])
        self._accelerator_info = AcceleratorInfo(
            use_gpu=self.use_gpu,
            device_name="CUDA (CuPy)" if self.use_gpu else "CPU (NumPy)",
            vectorization_enabled=True,
        )
        self._cache_hit = 0
        self._cache_miss = 0

    def get_accelerator_info(self) -> dict:
        self._accelerator_info.cache_hit_rate = (
            self._cache_hit / max(self._cache_hit + self._cache_miss, 1)
        )
        return {
            "accelerator": self._accelerator_info.device_name,
            "use_gpu": self._accelerator_info.use_gpu,
            "cupy_available": _HAS_CUPY,
            "vectorization": "enabled (batch numpy ops)" if self._accelerator_info.vectorization_enabled else "disabled",
            "capacity_cache_size": len(self._capacity_cache),
            "capacity_cache_hit_rate": float(self._accelerator_info.cache_hit_rate),
        }

    def clear_cache(self):
        self._capacity_cache.clear()
        self._cache_hit = 0
        self._cache_miss = 0

    def generate_earthquake_motion(self, pga: float, duration: float,
                                   time_step: float, seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
        xp = self.xp
        xp.random.seed(seed)
        n_steps = int(duration / time_step) + 1
        t = xp.linspace(0, duration, n_steps)
        freqs = xp.array([0.5, 1.0, 2.0, 3.0, 5.0, 8.0])
        amps = xp.array([0.3, 1.0, 0.8, 0.5, 0.2, 0.1])
        phases = xp.random.uniform(0, 2 * xp.pi, len(freqs))
        omega = 2 * xp.pi * freqs[:, None]
        t_bc = t[None, :]
        raw = xp.sum(amps[:, None] * xp.sin(omega * t_bc + phases[:, None]), axis=0)
        max_raw = xp.max(xp.abs(raw)) or 1.0
        accel = raw / max_raw * pga * self.g
        ramp_end = int(0.15 * n_steps)
        ramp_idx = xp.arange(ramp_end)
        accel[:ramp_end] *= (ramp_idx / max(ramp_end, 1))
        decay_start = int(0.65 * n_steps)
        decay_idx = xp.arange(decay_start, n_steps)
        decay = xp.exp(-3.0 * (decay_idx - decay_start) / max((n_steps - decay_start), 1))
        accel[decay_start:] *= decay
        return _to_numpy(t).astype(float), _to_numpy(accel).astype(float)

    def run_collapse_simulation(self, earthquake_pga: float, duration: float = 30.0,
                                time_step: float = 0.01,
                                progress_callback: Optional[Callable[[int, int], None]] = None) -> Dict:
        _t0 = time.time()
        t, accel = self.generate_earthquake_motion(earthquake_pga, duration, time_step)
        n_steps = len(t)
        n_floors = self.floor_count
        xp = self.xp

        accel_gpu = xp.asarray(accel, dtype=xp.float64)

        displacements = xp.zeros((n_steps, n_floors), dtype=xp.float64)
        velocities = xp.zeros((n_steps, n_floors), dtype=xp.float64)
        accelerations_arr = xp.zeros((n_steps, n_floors), dtype=xp.float64)
        drift_ratios = xp.zeros((n_steps, n_floors), dtype=xp.float64)
        damage_indices = xp.zeros((n_steps, n_floors), dtype=xp.float64)
        shear_forces = xp.zeros(n_steps, dtype=xp.float64)

        M_vec = xp.asarray(self.floor_masses, dtype=xp.float64)
        K_diag = xp.asarray(self.floor_stiffnesses, dtype=xp.float64)
        floor_h_arr = xp.asarray(self.floor_heights, dtype=xp.float64)
        H_total = float(self.cumulative_heights[-1])
        height_fracs = xp.asarray(self.cumulative_heights[1:] / H_total, dtype=xp.float64)
        mode1 = xp.sin(xp.pi / 2.0 * height_fracs)
        gamma_num = float(xp.sum(M_vec * mode1))
        gamma_den = float(xp.sum(M_vec * mode1 * mode1))
        gamma1 = gamma_num / max(gamma_den, 1e-9)
        Meq = gamma1 ** 2 * gamma_den
        Keq = float(xp.sum(K_diag * mode1 * mode1))
        omega_eq = xp.sqrt(Keq / max(Meq, 1e-9))
        T1 = 2 * xp.pi / max(omega_eq, 1e-9)
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
        V_base = alpha * gamma1 * float(xp.sum(M_vec * self.g))
        m_phi = M_vec * mode1
        sum_m_phi = float(xp.sum(m_phi))
        forces_eq = V_base * (m_phi / max(sum_m_phi, 1e-9))

        K_full = xp.zeros((n_floors, n_floors), dtype=xp.float64)
        idx = xp.arange(n_floors)
        K_full[idx, idx] = K_diag
        K_full[idx[:-1], idx[:-1]] += K_diag[1:]
        K_full[idx[1:], idx[:-1]] = -K_diag[1:]
        K_full[idx[:-1], idx[1:]] = -K_diag[1:]
        try:
            u_static = xp.linalg.solve(K_full, forces_eq)
        except xp.linalg.LinAlgError:
            u_static = mode1 * 0.1

        avg_floor_h = float(xp.mean(floor_h_arr))
        yield_drifts = self.joint_yield_moment / (self.joint_stiffness * floor_h_arr * 0.8)
        ult_drifts = self.joint_ultimate_moment / (0.3 * self.joint_stiffness * floor_h_arr)

        u_cumdiff = xp.zeros(n_floors)
        u_cumdiff[0] = xp.abs(u_static[0])
        u_cumdiff[1:] = xp.abs(xp.diff(u_static))
        u_static_drifts = u_cumdiff / floor_h_arr

        dyn_amp_elastic = min(4.0, max(2.5, 3.0))
        udrift_pos = u_static_drifts > 0
        if xp.any(udrift_pos):
            sf_yield = yield_drifts / xp.maximum(u_static_drifts * dyn_amp_elastic, 1e-9)
            min_yield_sf = float(xp.min(sf_yield[udrift_pos]))
            sf_ult = ult_drifts / xp.maximum(u_static_drifts * dyn_amp_elastic, 1e-9)
            min_ult_sf = float(xp.min(sf_ult[udrift_pos]))
        else:
            min_yield_sf = 99.0
            min_ult_sf = 99.0
        yield_sf = min_yield_sf if min_yield_sf < 10.0 else 99.0
        ult_sf = min_ult_sf if min_ult_sf < 10.0 else 99.0
        collapse_sf_val = 0.05 / max(float(xp.max(u_static_drifts) * dyn_amp_elastic), 1e-9)
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
        u_peak = u_static * scale_envelope

        strong_start_idx = int(n_steps * 0.15)
        strong_end_idx = int(n_steps * 0.55)
        step_idx = xp.arange(n_steps)
        envelope = xp.zeros(n_steps, dtype=xp.float64)
        pre_mask = step_idx < strong_start_idx
        envelope[pre_mask] = (step_idx[pre_mask] / max(strong_start_idx, 1)) ** 1.5
        mid_mask = (step_idx >= strong_start_idx) & (step_idx < strong_end_idx)
        mid_frac = (step_idx[mid_mask] - strong_start_idx) / max(strong_end_idx - strong_start_idx, 1)
        envelope[mid_mask] = 0.6 + 0.4 * xp.sin(xp.pi * mid_frac)
        post_mask = step_idx >= strong_end_idx
        envelope[post_mask] = xp.exp(-2.0 * (step_idx[post_mask] - strong_end_idx) / max(n_steps - strong_end_idx, 1))
        env_max = xp.max(envelope) or 1.0
        envelope /= env_max

        collapse_threshold = 1.0 / 20.0
        MIN_DRIFT_DENOM = 5
        failure_sequence = []
        floor_states = [
            CollapseState(floor=f, drift_ratio=0.0, damage_index=0.0, is_collapsed=False)
            for f in range(n_floors)
        ]
        collapse_mode = None
        collapse_time = None
        collapse_floor = None
        max_drift = 0.0

        u_peak_np = _to_numpy(u_peak).astype(float)
        floor_h_np = self.floor_heights
        env_np = _to_numpy(envelope).astype(float)
        K_soft_factor = 1.0
        yield_drifts_np = _to_numpy(yield_drifts).astype(float)
        ult_drifts_np = _to_numpy(ult_drifts).astype(float)
        M_vec_np = _to_numpy(M_vec).astype(float)
        forces_eq_np = _to_numpy(forces_eq).astype(float)

        REPORT_EVERY = max(1, n_steps // 20)
        for step in range(n_steps):
            env = env_np[step]
            if step > 0:
                dmg_prev_np = _to_numpy(damage_indices[step - 1]).astype(float)
            else:
                dmg_prev_np = np.zeros(n_floors)
            K_soft_factor = max(0.15, 1.0 - 0.75 * float(np.max(dmg_prev_np)))
            u_curr_np = u_peak_np * env * K_soft_factor
            if step == 0:
                v_curr_np = np.zeros(n_floors)
                a_curr_np = np.zeros(n_floors)
            else:
                prev_disp_np = _to_numpy(displacements[step - 1]).astype(float)
                prev_vel_np = _to_numpy(velocities[step - 1]).astype(float)
                v_curr_np = (u_curr_np - prev_disp_np) / max(time_step, 1e-9)
                a_curr_np = (v_curr_np - prev_vel_np) / max(time_step, 1e-9)
            displacements[step] = xp.asarray(u_curr_np, dtype=xp.float64)
            velocities[step] = xp.asarray(v_curr_np, dtype=xp.float64)
            accelerations_arr[step] = xp.asarray(a_curr_np, dtype=xp.float64)

            for f in range(n_floors):
                floor_h = floor_h_np[f]
                if f == 0:
                    drift = abs(u_curr_np[f]) / floor_h
                else:
                    drift = abs(u_curr_np[f] - u_curr_np[f - 1]) / floor_h
                if drift > 1.0 / MIN_DRIFT_DENOM:
                    drift = 1.0 / MIN_DRIFT_DENOM
                drift_ratios[step, f] = drift
                if drift > max_drift:
                    max_drift = drift
                yield_d = float(yield_drifts_np[f])
                ult_d = float(ult_drifts_np[f])
                if drift <= yield_d:
                    dmg = 0.0
                elif drift <= ult_d:
                    dmg = min(1.0, (drift - yield_d) / max(ult_d - yield_d, 1e-9))
                else:
                    dmg = 1.0
                damage_indices[step, f] = dmg
                fs = floor_states[f]
                fs.drift_ratio = drift
                fs.damage_index = float(dmg)
                prev_ev = float(damage_indices[step - 1, f]) if step > 0 else 0.0
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
            V_force_np = forces_eq_np * env * K_soft_factor
            accel_step_val = float(accel[step])
            shear_forces[step] = float(np.sum(M_vec_np * (a_curr_np + accel_step_val * 0.3)) + float(np.sum(V_force_np)))
            if progress_callback and (step + 1) % REPORT_EVERY == 0:
                progress_callback(step + 1, n_steps)

        if progress_callback:
            progress_callback(n_steps, n_steps)

        base_shear = float(xp.max(xp.abs(shear_forces[0:min(n_steps, int(n_steps * 0.7))])))
        total_weight = float(xp.sum(M_vec) * self.g)
        overstrength = base_shear / max(total_weight * earthquake_pga, 1e-6)
        yield_disp = self.joint_yield_moment / (self.joint_stiffness * 0.8) * avg_floor_h
        max_disp = float(xp.max(xp.abs(displacements[:, -1])))
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

        compute_ms = (time.time() - _t0) * 1000.0
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
            "compute_time_ms": round(compute_ms, 2),
            "accelerator": self._accelerator_info.device_name,
            "time_history": {
                "time_array": _to_numpy(t).tolist(),
                "displacement_mm": (_to_numpy(displacements) * 1000).tolist(),
                "drift_ratios": _to_numpy(drift_ratios).tolist(),
                "damage_indices": _to_numpy(damage_indices).tolist(),
                "base_shear": _to_numpy(shear_forces).tolist()
            },
            "failure_sequence": failure_sequence,
            "failure_events": failure_sequence,
            "input_energy": {
                "peak_acceleration_g": earthquake_pga,
                "input_impulse": float(np.trapezoid(_to_numpy(accel), _to_numpy(t))),
                "arias_intensity": float(0.5 * np.pi * np.trapezoid(_to_numpy(accel) ** 2, _to_numpy(t)))
            }
        }

    def evaluate_ultimate_capacity(self, start_pga: float = 0.05,
                                   end_pga: float = 2.0,
                                   pga_step: float = 0.05,
                                   early_stop: bool = True,
                                   progress_callback: Optional[Callable[[int, int, float], None]] = None) -> Dict:
        cache_key = (self.floor_count, tuple(self.floor_heights), tuple(self.floor_diameters),
                     float(self.joint_yield_moment), float(self.joint_ultimate_moment),
                     float(self.joint_stiffness), float(start_pga), float(end_pga), float(pga_step))
        if cache_key in self._capacity_cache:
            self._cache_hit += 1
            return dict(self._capacity_cache[cache_key])
        self._cache_miss += 1

        pga_levels = np.arange(start_pga, end_pga + pga_step, pga_step)
        capacity_curve = []
        ultimate_pga = None
        yield_pga = None
        design_pga = 0.16
        n_total = len(pga_levels)
        for i, pga in enumerate(pga_levels):
            if progress_callback:
                progress_callback(i, n_total, float(pga))
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
                if early_stop:
                    if progress_callback:
                        progress_callback(n_total, n_total, float(pga))
                    break
        if progress_callback:
            progress_callback(n_total, n_total, float(end_pga))
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
        final_result = {
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
            "performance_levels": performance_levels,
            "evaluated_points": len(capacity_curve),
            "early_stopped": len(capacity_curve) < len(pga_levels),
        }
        self._capacity_cache[cache_key] = dict(final_result)
        return final_result

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
