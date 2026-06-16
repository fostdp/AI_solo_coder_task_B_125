import numpy as np
from typing import Dict, List

from .models import PagodaModel, PagodaUncertainty
from .pagoda_data import build_pagoda_models


class PagodaDesignComparator:
    CANTILEVER_LAMBDAS = np.array([1.875, 4.694, 7.855, 10.996, 14.137])
    AIR_DENSITY = 1.225

    def __init__(self):
        self.pagoda_models: Dict[str, PagodaModel] = build_pagoda_models()

    def list_pagodas(self) -> List[dict]:
        result = []
        for k, v in self.pagoda_models.items():
            display_id = "gojunoto" if k == "gojunoto_horyuji" else k
            result.append({
                "id": display_id,
                "internal_id": k,
                "name": v.name,
                "dynasty": v.dynasty,
                "country": v.country,
                "height": v.height,
                "floor_count": v.floor_count,
                "structural_type": v.structural_type,
                "has_shinbashira": v.shinbashira,
                "seismic_philosophy": v.seismic_philosophy,
                "calibration_year": v.calibration_year,
                "data_source_count": len(v.data_sources),
            })
        return result

    def get_pagoda_model(self, pagoda_id: str) -> PagodaModel:
        if pagoda_id == "gojunoto":
            pagoda_id = "gojunoto_horyuji"
        if pagoda_id not in self.pagoda_models:
            raise ValueError(f"未找到木塔模型：{pagoda_id}")
        return self.pagoda_models[pagoda_id]

    def list_available_data_sources(self, pagoda_id: str) -> dict:
        pagoda = self.get_pagoda_model(pagoda_id)
        return {
            "pagoda_id": pagoda_id,
            "pagoda_name": pagoda.name,
            "calibration_year": pagoda.calibration_year,
            "data_sources": pagoda.data_sources,
            "uncertainty_bounds": {
                "height_uncertainty_pct": pagoda.uncertainty.height_uncertainty_pct,
                "diameter_uncertainty_pct": pagoda.uncertainty.diameter_uncertainty_pct,
                "E_uncertainty_pct": pagoda.uncertainty.E_uncertainty_pct,
                "joint_k_uncertainty_pct": pagoda.uncertainty.joint_k_uncertainty_pct,
            },
        }

    def _compute_section_properties(self, pagoda: PagodaModel):
        outer_radii = np.array(pagoda.floor_diameters) / 2.0
        inner_radii = np.array(pagoda.inner_diameters) / 2.0
        heights = np.array(pagoda.floor_heights)
        total_height = pagoda.height

        areas = np.pi * (outer_radii**2 - inner_radii**2)
        moments = np.pi / 4.0 * (outer_radii**4 - inner_radii**4)

        weights = heights / np.sum(heights)
        avg_area = np.sum(areas * weights)
        avg_moment = np.sum(moments * weights)

        E = pagoda.timber_properties["E_L"] * 1e6
        rho = pagoda.timber_properties["density"]

        return E, avg_moment, avg_area, rho, total_height

    def compare_seismic_philosophy(self, pagoda_a_id: str, pagoda_b_id: str) -> dict:
        pagoda_a = self.get_pagoda_model(pagoda_a_id)
        pagoda_b = self.get_pagoda_model(pagoda_b_id)

        philosophy_diff = {
            "pagoda_a": {
                "name": pagoda_a.name,
                "country": pagoda_a.country,
                "philosophy": pagoda_a.seismic_philosophy,
            },
            "pagoda_b": {
                "name": pagoda_b.name,
                "country": pagoda_b.country,
                "philosophy": pagoda_b.seismic_philosophy,
            },
            "comparison": "",
            "key_differences": [],
            "differences": [],
        }

        if pagoda_a.shinbashira and not pagoda_b.shinbashira:
            philosophy_diff["comparison"] = (
                f"{pagoda_a.name}采用心柱结构提供恢复力，"
                f"{pagoda_b.name}依赖榫卯节点半刚性耗能"
            )
            philosophy_diff["key_differences"] = [
                "心柱vs无心柱：结构恢复力机制根本不同",
                f"{pagoda_a.name}通过层间大变形和心柱摆动消耗地震能量",
                f"{pagoda_b.name}通过榫卯节点的转动变形和摩擦滑移耗能",
                "日本塔更注重整体柔性与回复，中国塔更注重节点耗能",
            ]
        elif not pagoda_a.shinbashira and pagoda_b.shinbashira:
            philosophy_diff["comparison"] = (
                f"{pagoda_a.name}依赖榫卯节点半刚性耗能，"
                f"{pagoda_b.name}采用心柱结构提供恢复力"
            )
            philosophy_diff["key_differences"] = [
                "榫卯节点vs心柱：耗能机制根本不同",
                f"{pagoda_a.name}通过榫卯节点的转动变形和摩擦滑移耗能",
                f"{pagoda_b.name}通过层间大变形和心柱摆动消耗地震能量",
                "中国塔更注重节点耗能，日本塔更注重整体柔性与回复",
            ]
        else:
            philosophy_diff["comparison"] = "两塔抗震哲学相似"
            philosophy_diff["key_differences"] = ["结构体系相近，耗能机制类似"]

        philosophy_diff["differences"] = philosophy_diff["key_differences"]

        stiffness_ratio = (
            pagoda_a.joint_properties["rotational_stiffness"]
            / pagoda_b.joint_properties["rotational_stiffness"]
        )
        yield_ratio = (
            pagoda_a.joint_properties["yield_moment"]
            / pagoda_b.joint_properties["yield_moment"]
        )
        philosophy_diff["quantitative"] = {
            "rotational_stiffness_ratio_a_to_b": float(stiffness_ratio),
            "yield_moment_ratio_a_to_b": float(yield_ratio),
        }

        return philosophy_diff

    def compare_natural_frequencies(self, pagoda_a_id: str, pagoda_b_id: str) -> dict:
        pagoda_a = self.get_pagoda_model(pagoda_a_id)
        pagoda_b = self.get_pagoda_model(pagoda_b_id)

        freq_a = self._compute_natural_frequencies(pagoda_a)
        freq_b = self._compute_natural_frequencies(pagoda_b)

        ratio = freq_a / freq_b

        return {
            "pagoda_a": {
                "name": pagoda_a.name,
                "frequencies_hz": freq_a.tolist(),
            },
            "pagoda_b": {
                "name": pagoda_b.name,
                "frequencies_hz": freq_b.tolist(),
            },
            "frequencies_a": freq_a.tolist(),
            "frequencies_b": freq_b.tolist(),
            "ratio_a_to_b": ratio.tolist(),
            "analysis": (
                f"基频比 {pagoda_a.name}/{pagoda_b.name} = {ratio[0]:.3f}，"
                f"{'中国塔刚度更大' if ratio[0] > 1 else '日本塔相对刚度更大'}"
            ),
        }

    def _compute_natural_frequencies(self, pagoda: PagodaModel) -> np.ndarray:
        E, I, A, rho, L = self._compute_section_properties(pagoda)
        freqs = np.zeros(5)
        for i in range(5):
            lam = self.CANTILEVER_LAMBDAS[i]
            freqs[i] = (lam**2 / (2.0 * np.pi * L**2)) * np.sqrt(E * I / (rho * A))
        return freqs

    def compare_displacement_under_wind(
        self, pagoda_a_id: str, pagoda_b_id: str, wind_speed: float
    ) -> dict:
        pagoda_a = self.get_pagoda_model(pagoda_a_id)
        pagoda_b = self.get_pagoda_model(pagoda_b_id)

        disp_a = self._compute_wind_displacement(pagoda_a, wind_speed)
        disp_b = self._compute_wind_displacement(pagoda_b, wind_speed)

        avg_diam_a = np.mean(pagoda_a.floor_diameters)
        avg_diam_b = np.mean(pagoda_b.floor_diameters)

        wind_pressure = 0.5 * self.AIR_DENSITY * wind_speed**2

        return {
            "wind_speed_ms": wind_speed,
            "wind_pressure_pa": float(wind_pressure),
            "pagoda_a": {
                "name": pagoda_a.name,
                "top_displacement_m": float(disp_a),
                "top_disp_mm": float(disp_a * 1000),
                "height_to_displacement_ratio": float(pagoda_a.height / disp_a) if disp_a > 0 else float("inf"),
            },
            "pagoda_b": {
                "name": pagoda_b.name,
                "top_displacement_m": float(disp_b),
                "top_disp_mm": float(disp_b * 1000),
                "height_to_displacement_ratio": float(pagoda_b.height / disp_b) if disp_b > 0 else float("inf"),
            },
            "top_disp_a_mm": float(disp_a * 1000),
            "top_disp_b_mm": float(disp_b * 1000),
            "ratio_a_to_b": float(disp_a / disp_b) if disp_b > 0 else float("inf"),
            "analysis": (
                f"风速{wind_speed}m/s下，{pagoda_a.name}顶点位移{disp_a:.4f}m，"
                f"{pagoda_b.name}顶点位移{disp_b:.4f}m，"
                f"{'中国塔抗风刚度更大' if disp_a < disp_b else '日本塔抗风刚度更大'}"
            ),
        }

    def _compute_wind_displacement(self, pagoda: PagodaModel, wind_speed: float) -> float:
        E, I, A, rho, L = self._compute_section_properties(pagoda)
        avg_diameter = np.mean(pagoda.floor_diameters)
        wind_load_per_length = 0.5 * self.AIR_DENSITY * wind_speed**2 * avg_diameter
        displacement = wind_load_per_length * L**4 / (8.0 * E * I)
        return displacement

    def compare_energy_dissipation(self, pagoda_a_id: str, pagoda_b_id: str) -> dict:
        pagoda_a = self.get_pagoda_model(pagoda_a_id)
        pagoda_b = self.get_pagoda_model(pagoda_b_id)

        ed_a = self._compute_energy_dissipation(pagoda_a)
        ed_b = self._compute_energy_dissipation(pagoda_b)

        return {
            "pagoda_a": {
                "name": pagoda_a.name,
                "joint_count": pagoda_a.floor_count,
                "rotational_stiffness": pagoda_a.joint_properties["rotational_stiffness"],
                "yield_moment": pagoda_a.joint_properties["yield_moment"],
                "energy_per_cycle_kj": float(ed_a["energy_per_cycle"]),
                "equivalent_damping_ratio": float(ed_a["equivalent_damping_ratio"]),
                "has_shinbashira": pagoda_a.shinbashira,
            },
            "pagoda_b": {
                "name": pagoda_b.name,
                "joint_count": pagoda_b.floor_count,
                "rotational_stiffness": pagoda_b.joint_properties["rotational_stiffness"],
                "yield_moment": pagoda_b.joint_properties["yield_moment"],
                "energy_per_cycle_kj": float(ed_b["energy_per_cycle"]),
                "equivalent_damping_ratio": float(ed_b["equivalent_damping_ratio"]),
                "has_shinbashira": pagoda_b.shinbashira,
            },
            "ratio_a_to_b": {
                "energy_per_cycle": float(ed_a["energy_per_cycle"] / ed_b["energy_per_cycle"]) if ed_b["energy_per_cycle"] > 0 else float("inf"),
                "damping_ratio": float(ed_a["equivalent_damping_ratio"] / ed_b["equivalent_damping_ratio"]) if ed_b["equivalent_damping_ratio"] > 0 else float("inf"),
            },
            "analysis": (
                f"{pagoda_a.name}单循环耗能{ed_a['energy_per_cycle']:.2f}kJ，"
                f"等效阻尼比{ed_a['equivalent_damping_ratio']:.4f}；"
                f"{pagoda_b.name}单循环耗能{ed_b['energy_per_cycle']:.2f}kJ，"
                f"等效阻尼比{ed_b['equivalent_damping_ratio']:.4f}；"
                f"{'中国塔节点耗能能力更强' if ed_a['energy_per_cycle'] > ed_b['energy_per_cycle'] else '日本塔节点耗能能力更强'}"
            ),
        }

    def _compute_energy_dissipation(self, pagoda: PagodaModel) -> dict:
        k_r = pagoda.joint_properties["rotational_stiffness"]
        m_y = pagoda.joint_properties["yield_moment"]
        theta_y = m_y / k_r
        theta_max = 4.0 * theta_y

        energy_elastic = 0.5 * m_y * theta_y
        energy_plastic = m_y * (theta_max - theta_y)
        energy_per_joint_cycle = 4.0 * (energy_elastic + energy_plastic)
        total_energy = energy_per_joint_cycle * pagoda.floor_count
        total_energy_kj = total_energy / 1000.0

        E, I, A, rho, L = self._compute_section_properties(pagoda)
        total_mass = rho * A * L
        total_stiffness = 3.0 * E * I / L**3
        omega = np.sqrt(total_stiffness / total_mass)

        strain_energy = 0.5 * total_stiffness * (0.01 * L) ** 2
        if strain_energy > 0:
            eq_damping = total_energy / (4.0 * np.pi * strain_energy)
        else:
            eq_damping = 0.0

        shinbashira_extra = 0.0
        if pagoda.shinbashira and pagoda.shinbashira_diameter > 0:
            r_s = pagoda.shinbashira_diameter / 2.0
            I_s = np.pi * r_s**4 / 4.0
            E_s = pagoda.timber_properties["E_L"] * 1e6
            k_s = 3.0 * E_s * I_s / L**3
            shinbashira_extra = 0.05 * k_s * (0.01 * L) ** 2 / 1000.0

        total_energy_kj += shinbashira_extra

        return {
            "energy_per_cycle": total_energy_kj,
            "equivalent_damping_ratio": eq_damping,
        }

    def generate_comparison_report(self, pagoda_a_id: str, pagoda_b_id: str) -> dict:
        pagoda_a = self.get_pagoda_model(pagoda_a_id)
        pagoda_b = self.get_pagoda_model(pagoda_b_id)

        report = {
            "title": f"{pagoda_a.name} vs {pagoda_b.name} 古代木塔结构对比分析报告",
            "pagoda_a_summary": {
                "name": pagoda_a.name,
                "dynasty": pagoda_a.dynasty,
                "country": pagoda_a.country,
                "height_m": pagoda_a.height,
                "floor_count": pagoda_a.floor_count,
                "structural_type": pagoda_a.structural_type,
                "shinbashira": pagoda_a.shinbashira,
            },
            "pagoda_b_summary": {
                "name": pagoda_b.name,
                "dynasty": pagoda_b.dynasty,
                "country": pagoda_b.country,
                "height_m": pagoda_b.height,
                "floor_count": pagoda_b.floor_count,
                "structural_type": pagoda_b.structural_type,
                "shinbashira": pagoda_b.shinbashira,
            },
            "seismic_philosophy_comparison": self.compare_seismic_philosophy(
                pagoda_a_id, pagoda_b_id
            ),
            "natural_frequency_comparison": self.compare_natural_frequencies(
                pagoda_a_id, pagoda_b_id
            ),
            "wind_displacement_comparison": self.compare_displacement_under_wind(
                pagoda_a_id, pagoda_b_id, wind_speed=25.0
            ),
            "energy_dissipation_comparison": self.compare_energy_dissipation(
                pagoda_a_id, pagoda_b_id
            ),
        }

        return report


DynastyComparisonEngine = PagodaDesignComparator
