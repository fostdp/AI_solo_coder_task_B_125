import numpy as np
from typing import Dict, List, Optional

from .properties import (
    JoineryProperties,
    ExperimentalSource,
    PARAMETER_VALID_RANGES,
)
from .joint_data import build_joint_library


class JoinerySimulator:
    """榫卯节点力学性能模拟器 - 独立模块版本

    提供循环加载模拟、骨架曲线计算、刚度退化、能量耗散等分析能力。
    """

    def __init__(self):
        self.joint_library: Dict[str, JoineryProperties] = build_joint_library()

    @property
    def JOINT_TYPES(self) -> Dict[str, JoineryProperties]:
        return self.joint_library

    def list_joint_types(self) -> List[Dict]:
        return [
            {
                "id": k,
                "name": v.name,
                "chinese_name": v.chinese_name,
                "category": v.category,
                "elastic_stiffness": v.elastic_stiffness,
                "yield_moment": v.yield_moment,
                "ultimate_moment": v.ultimate_moment,
                "yield_rotation": v.yield_rotation,
                "ultimate_rotation": v.ultimate_rotation,
                "damping_ratio": v.damping_ratio,
                "pinching_factor": v.pinching_factor,
                "model_type": v.model_type,
                "ductility": float(v.ultimate_rotation / v.yield_rotation),
                "ductility_factor": float(v.ultimate_rotation / v.yield_rotation)
            }
            for k, v in self.joint_library.items()
        ]

    def get_joint_type(self, joint_type_id: str) -> JoineryProperties:
        props = self.joint_library.get(joint_type_id)
        if not props:
            raise ValueError(f"Unknown joint type: {joint_type_id}")
        return props

    def validate_parameters(self, joint_type_id: Optional[str] = None) -> dict:
        results = {}
        targets = [joint_type_id] if joint_type_id else list(self.joint_library.keys())
        for jid in targets:
            props = self.joint_library[jid]
            checks = []
            ductility = props.ultimate_rotation / props.yield_rotation

            def _chk(cond: bool, name: str, val: float, lo: float, hi: float) -> dict:
                return {
                    "parameter": name,
                    "value": float(val),
                    "range": [lo, hi],
                    "pass": bool(cond),
                }

            checks.append(_chk(
                PARAMETER_VALID_RANGES["elastic_stiffness"][0] <= props.elastic_stiffness <= PARAMETER_VALID_RANGES["elastic_stiffness"][1],
                "elastic_stiffness", props.elastic_stiffness,
                *PARAMETER_VALID_RANGES["elastic_stiffness"]))
            checks.append(_chk(
                PARAMETER_VALID_RANGES["yield_moment"][0] <= props.yield_moment <= PARAMETER_VALID_RANGES["yield_moment"][1],
                "yield_moment", props.yield_moment,
                *PARAMETER_VALID_RANGES["yield_moment"]))
            checks.append(_chk(
                PARAMETER_VALID_RANGES["ultimate_moment"][0] <= props.ultimate_moment <= PARAMETER_VALID_RANGES["ultimate_moment"][1],
                "ultimate_moment", props.ultimate_moment,
                *PARAMETER_VALID_RANGES["ultimate_moment"]))
            checks.append(_chk(
                PARAMETER_VALID_RANGES["yield_rotation"][0] <= props.yield_rotation <= PARAMETER_VALID_RANGES["yield_rotation"][1],
                "yield_rotation", props.yield_rotation,
                *PARAMETER_VALID_RANGES["yield_rotation"]))
            checks.append(_chk(
                PARAMETER_VALID_RANGES["ultimate_rotation"][0] <= props.ultimate_rotation <= PARAMETER_VALID_RANGES["ultimate_rotation"][1],
                "ultimate_rotation", props.ultimate_rotation,
                *PARAMETER_VALID_RANGES["ultimate_rotation"]))
            checks.append(_chk(
                props.ultimate_moment > props.yield_moment,
                "Mu > My", props.ultimate_moment - props.yield_moment, 0, 1e9))
            checks.append(_chk(
                props.ultimate_rotation > props.yield_rotation,
                "theta_u > theta_y", props.ultimate_rotation - props.yield_rotation, 0, 1))
            checks.append(_chk(
                PARAMETER_VALID_RANGES["ductility_factor"][0] <= ductility <= PARAMETER_VALID_RANGES["ductility_factor"][1],
                "ductility_factor", ductility,
                *PARAMETER_VALID_RANGES["ductility_factor"]))
            all_pass = all(c["pass"] for c in checks)
            results[jid] = {
                "chinese_name": props.chinese_name,
                "all_checks_pass": all_pass,
                "validation_status": props.validation_status,
                "calibration_year": props.calibration_year,
                "source_ref": props.experimental_source.paper_ref if props.experimental_source else None,
                "checks": checks,
            }
        return results

    def calibrate_from_experiment(self, joint_type_id: str,
                                   test_data: Dict[str, float],
                                   source_info: Optional[Dict] = None) -> JoineryProperties:
        props = self.get_joint_type(joint_type_id)
        updatable = ["elastic_stiffness", "yield_moment", "ultimate_moment",
                     "yield_rotation", "ultimate_rotation", "damping_ratio",
                     "pinching_factor", "gap", "torsional_stiffness"]
        for k, v in test_data.items():
            if k in updatable and isinstance(v, (int, float)):
                setattr(props, k, float(v))
        if source_info:
            props.experimental_source = ExperimentalSource(
                institution=source_info.get("institution", "Unknown"),
                year=int(source_info.get("year", 2024)),
                sample_count=int(source_info.get("sample_count", 1)),
                timber_species=source_info.get("timber_species", "Unknown"),
                test_method=source_info.get("test_method", "Unknown"),
                paper_ref=source_info.get("paper_ref", ""),
            )
            props.calibration_year = int(source_info.get("year", props.calibration_year or 2024))
        props.validation_status = "experimentally_calibrated"
        self.joint_library[joint_type_id] = props
        return props

    def list_experimental_sources(self) -> dict:
        summary = {}
        for jid, props in self.joint_library.items():
            src = props.experimental_source
            summary[jid] = {
                "chinese_name": props.chinese_name,
                "calibration_year": props.calibration_year,
                "validation_status": props.validation_status,
                "source": {
                    "institution": src.institution if src else None,
                    "year": src.year if src else None,
                    "sample_count": src.sample_count if src else None,
                    "timber_species": src.timber_species if src else None,
                    "test_method": src.test_method if src else None,
                    "paper_ref": src.paper_ref if src else None,
                } if src else None,
                "uncertainty_cvs": {
                    "K": props.uncertainty.stiffness_cv,
                    "My": props.uncertainty.yield_moment_cv,
                    "Mu": props.uncertainty.ultimate_moment_cv,
                    "theta_y": props.uncertainty.yield_rotation_cv,
                    "mu": props.uncertainty.ductility_cv,
                },
            }
        return summary

    def _moment_from_rotation(self, props: JoineryProperties, rotation: float) -> float:
        theta = abs(rotation)
        sign = np.sign(rotation)
        gap = props.gap
        if theta < gap:
            return 0.0
        theta_eff = theta - gap
        My = props.yield_moment
        Mu = props.ultimate_moment
        theta_y = props.yield_rotation
        theta_u = props.ultimate_rotation
        ky = props.elastic_stiffness
        k_post_yield = (Mu - My) / (theta_u - theta_y) if theta_u > theta_y else 0.0
        if theta_eff <= theta_y:
            moment = ky * theta_eff
        elif theta_eff <= theta_u:
            moment = My + k_post_yield * (theta_eff - theta_y)
        else:
            moment = max(0.0, Mu - (theta_eff - theta_u) * ky * 0.05)
        return sign * moment

    def simulate_cyclic_loading(self, joint_type_id: str, max_rotation: float,
                         cycles: int = 3,
                         steps_per_cycle: int = 50) -> Dict:
        props = self.get_joint_type(joint_type_id)
        total_steps = cycles * steps_per_cycle * 4
        rotations = np.zeros(total_steps)
        moments = np.zeros(total_steps)
        cycle_labels = []
        step = 0
        damage = 0.0
        stiffness_degradation = 1.0
        cycle_energy_per_cycle = []
        for cycle in range(cycles):
            max_theta = max_rotation * (1.0 + cycle * 0.15)
            theta_array = np.concatenate([
                np.linspace(0, max_theta, steps_per_cycle),
                np.linspace(max_theta, -max_theta, steps_per_cycle),
                np.linspace(-max_theta, 0, steps_per_cycle)
            ])
            cycle_energy = 0.0
            for i, theta in enumerate(theta_array):
                effective_theta = theta * (1.0 - props.pinching_factor * 0.3 * min(1.0, 1.0 - stiffness_degradation))
                moment = self._moment_from_rotation(props, effective_theta) * stiffness_degradation
                rotations[step] = theta
                moments[step] = moment
                if i > 0:
                    d_theta = theta_array[i] - theta_array[i-1]
                    cycle_energy += 0.5 * (moments[step] + moments[step - 1]) * d_theta
                step += 1
            cycle_energy_per_cycle.append(cycle_energy)
            damage += 0.15 * (cycle + 1)
            stiffness_degradation = max(0.2, 1.0 - damage)
        return {
            "joint_type": joint_type_id,
            "chinese_name": props.chinese_name,
            "max_rotation": max_rotation,
            "cycles": cycles,
            "rotation_array": rotations.tolist(),
            "moment_array": moments.tolist(),
            "cycle_energies": cycle_energy_per_cycle,
            "final_stiffness_ratio": stiffness_degradation,
            "total_steps": step
        }

    def compute_energy_dissipation(self, hysteresis_data: Dict) -> Dict:
        rotations = np.array(hysteresis_data["rotation_array"])
        moments = np.array(hysteresis_data["moment_array"])
        total_energy = 0.0
        positive_energy = 0.0
        negative_energy = 0.0
        n = len(rotations)
        for i in range(1, n):
            d_theta = rotations[i] - rotations[i-1]
            work = 0.5 * (moments[i] + moments[i-1]) * d_theta
            if work > 0:
                positive_energy += work
            else:
                negative_energy += abs(work)
            total_energy += abs(work)
        max_moment = float(np.max(np.abs(moments))) or 1.0
        max_rotation = float(np.max(np.abs(rotations))) or 1.0
        strain_elastic_energy = 0.5 * max_moment * max_rotation
        equivalent_damping = total_energy / (2 * np.pi * strain_elastic_energy) if strain_elastic_energy > 0 else 0.0
        equivalent_damping = min(0.5, equivalent_damping)
        cycle_data = [abs(x) for x in hysteresis_data.get("cycle_energies", [])]
        return {
            "total_energy": float(total_energy),
            "positive_loading_energy": float(positive_energy),
            "unloading_energy": float(negative_energy),
            "equivalent_damping_ratio": float(equivalent_damping),
            "cycle_energies": cycle_data,
            "elastic_strain_energy": float(strain_elastic_energy),
            "energy_dissipation_ratio": float(total_energy / max(strain_elastic_energy, 1e-9))
        }

    def compute_stiffness_degradation(self, hysteresis_data: Dict) -> Dict:
        rotations = np.array(hysteresis_data["rotation_array"])
        moments = np.array(hysteresis_data["moment_array"])
        n = len(rotations)
        cycles = hysteresis_data.get("cycles", 3)
        max_rot = hysteresis_data.get("max_rotation", 0.03)
        cycle_indices = []
        secant_stiffnesses = []
        steps_per_cycle = n // (cycles * 3)
        for c in range(cycles):
            peak_idx = min((c * 3 + 1) * steps_per_cycle - 1, n - 1)
            if peak_idx > 0 and rotations[peak_idx] != 0:
                k_peak = float(moments[peak_idx] / rotations[peak_idx])
                cycle_indices.append(peak_idx)
                secant_stiffnesses.append(abs(k_peak))
        if not secant_stiffnesses:
            fallback_points = [n // (cycles + 1) * (i + 1) for i in range(cycles)]
            cycle_indices = [min(fp, n - 1) for fp in fallback_points]
            for idx in cycle_indices:
                if idx > 0 and rotations[idx] != 0:
                    secant_stiffnesses.append(abs(float(moments[idx] / rotations[idx])))
                else:
                    secant_stiffnesses.append(1.0)
        initial_k = secant_stiffnesses[0] or 1.0
        degradation_ratios = [k / initial_k for k in secant_stiffnesses]
        return {
            "cycle_indices": cycle_indices,
            "secant_stiffnesses": secant_stiffnesses,
            "degradation_ratios": degradation_ratios,
            "final_to_initial_ratio": float(degradation_ratios[-1]) if degradation_ratios else 1.0
        }

    def compute_backbone_curve(self, joint_type_id: str) -> Dict:
        props = self.get_joint_type(joint_type_id)
        n_points = 100
        theta_u = props.ultimate_rotation * 1.2
        rotations = np.linspace(-theta_u, theta_u, n_points)
        moments = np.array([self._moment_from_rotation(props, t) for t in rotations])
        theta_pos = np.linspace(0, theta_u, 50)
        moment_pos = np.array([self._moment_from_rotation(props, t) for t in theta_pos])
        return {
            "joint_type": joint_type_id,
            "chinese_name": props.chinese_name,
            "yield_rotation": props.yield_rotation,
            "yield_moment": props.yield_moment,
            "ultimate_rotation": props.ultimate_rotation,
            "ultimate_moment": props.ultimate_moment,
            "rotations": rotations.tolist(),
            "moments": moments.tolist(),
            "rotation_array": rotations.tolist(),
            "moment_array": moments.tolist(),
            "positive_branch_rotations": theta_pos.tolist(),
            "positive_branch_moments": moment_pos.tolist(),
            "yield_point": {"moment": float(props.yield_moment), "rotation": float(props.yield_rotation)},
            "ultimate_point": {"moment": float(props.ultimate_moment), "rotation": float(props.ultimate_rotation)},
            "ductility_factor": float(props.ultimate_rotation / props.yield_rotation)
        }

    def compare_joints(self, joint_type_ids: List[str]) -> Dict:
        results = {}
        for jid in joint_type_ids:
            props = self.get_joint_type(jid)
            backbone = self.compute_backbone_curve(jid)
            ductility = props.ultimate_rotation / props.yield_rotation
            energy_total = 0.5 * (props.ultimate_moment + props.yield_moment) * (props.ultimate_rotation - props.yield_rotation)
            results[jid] = {
                "chinese_name": props.chinese_name,
                "elastic_stiffness": props.elastic_stiffness,
                "yield_moment": props.yield_moment,
                "ultimate_moment": props.ultimate_moment,
                "yield_rotation": props.yield_rotation,
                "ultimate_rotation": props.ultimate_rotation,
                "ductility_factor": ductility,
                "energy_capacity": energy_total,
                "damping_ratio": props.damping_ratio,
                "pinching_factor": props.pinching_factor,
                "backbone_curve": backbone
            }
        return results


MortiseTenonSimulator = JoinerySimulator
