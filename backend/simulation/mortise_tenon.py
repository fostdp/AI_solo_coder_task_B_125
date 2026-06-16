import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class MortiseTenonProperties:
    name: str
    chinese_name: str
    category: str
    elastic_stiffness: float
    yield_moment: float
    ultimate_moment: float
    yield_rotation: float
    ultimate_rotation: float
    damping_ratio: float
    pinching_factor: float
    model_type: str
    gap: float = 0.0
    torsional_stiffness: float = 0.0
    vertical_load_effect: bool = False


class MortiseTenonSimulator:
    JOINT_TYPES: Dict[str, MortiseTenonProperties] = {}

    def __init__(self):
        self.JOINT_TYPES = {
            "straight_tenon": MortiseTenonProperties(
                name="straight_tenon",
                chinese_name="直榫",
                category="beam_column",
                elastic_stiffness=1.0e8,
                yield_moment=80000.0,
                ultimate_moment=120000.0,
                yield_rotation=0.005,
                ultimate_rotation=0.03,
                damping_ratio=0.05,
                pinching_factor=0.3,
                model_type="bilinear"
            ),
            "dovetail_tenon": MortiseTenonProperties(
                name="dovetail_tenon",
                chinese_name="燕尾榫",
                category="beam_column",
                elastic_stiffness=1.5e8,
                yield_moment=100000.0,
                ultimate_moment=160000.0,
                yield_rotation=0.004,
                ultimate_rotation=0.025,
                damping_ratio=0.06,
                pinching_factor=0.25,
                model_type="trilinear"
            ),
            "cross_tenon": MortiseTenonProperties(
                name="cross_tenon",
                chinese_name="十字榫",
                category="cross_joint",
                elastic_stiffness=8.0e7,
                yield_moment=60000.0,
                ultimate_moment=90000.0,
                yield_rotation=0.006,
                ultimate_rotation=0.035,
                damping_ratio=0.07,
                pinching_factor=0.35,
                model_type="bilinear",
                torsional_stiffness=5.0e7
            ),
            "through_tenon": MortiseTenonProperties(
                name="through_tenon",
                chinese_name="透榫",
                category="through_beam",
                elastic_stiffness=1.2e8,
                yield_moment=95000.0,
                ultimate_moment=150000.0,
                yield_rotation=0.0045,
                ultimate_rotation=0.028,
                damping_ratio=0.055,
                pinching_factor=0.2,
                model_type="trilinear"
            ),
            "angle_brace_tenon": MortiseTenonProperties(
                name="angle_brace_tenon",
                chinese_name="斜撑榫",
                category="bracing",
                elastic_stiffness=6.0e7,
                yield_moment=45000.0,
                ultimate_moment=70000.0,
                yield_rotation=0.007,
                ultimate_rotation=0.04,
                damping_ratio=0.08,
                pinching_factor=0.4,
                model_type="bilinear_with_gap",
                gap=0.002
            ),
            "bucket_arch_joint": MortiseTenonProperties(
                name="bucket_arch_joint",
                chinese_name="斗拱节点",
                category="bracket_set",
                elastic_stiffness=2.0e8,
                yield_moment=130000.0,
                ultimate_moment=200000.0,
                yield_rotation=0.003,
                ultimate_rotation=0.02,
                damping_ratio=0.04,
                pinching_factor=0.15,
                model_type="multi_linear",
                vertical_load_effect=True
            )
        }

    def get_joint_type(self, joint_type_id: str) -> MortiseTenonProperties:
        props = self.JOINT_TYPES.get(joint_type_id)
        if not props:
            raise ValueError(f"Unknown joint type: {joint_type_id}")
        return props

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
            for k, v in self.JOINT_TYPES.items()
        ]

    def _moment_from_rotation(self, props: MortiseTenonProperties, rotation: float) -> float:
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
