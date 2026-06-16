import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class DynastyPagodaModel:
    name: str
    dynasty: str
    country: str
    height: float
    floor_count: int
    structural_type: str
    floor_heights: List[float]
    floor_diameters: List[float]
    inner_diameters: List[float]
    wall_thickness: List[float]
    timber_properties: Dict[str, float]
    joint_properties: Dict[str, float]
    seismic_philosophy: str
    shinbashira: bool = False
    shinbashira_diameter: float = 0.0


class DynastyComparisonEngine:
    CANTILEVER_LAMBDAS = np.array([1.875, 4.694, 7.855, 10.996, 14.137])
    AIR_DENSITY = 1.225

    def __init__(self):
        self.PAGODA_MODELS = {
            "yingxian": DynastyPagodaModel(
                name="应县木塔",
                dynasty="辽代",
                country="中国",
                height=67.31,
                floor_count=5,
                structural_type="楼阁式木塔",
                floor_heights=[6.59, 5.49, 4.99, 4.59, 4.09],
                floor_diameters=[30.27, 22.65, 18.46, 15.28, 12.10],
                inner_diameters=[15.2, 12.0, 10.0, 8.5, 7.0],
                wall_thickness=[2.0, 1.8, 1.6, 1.4, 1.2],
                timber_properties={
                    "E_L": 10000.0,
                    "E_R": 800.0,
                    "E_T": 500.0,
                    "density": 500.0,
                },
                joint_properties={
                    "rotational_stiffness": 1e8,
                    "yield_moment": 1e5,
                },
                seismic_philosophy="以柔克刚：榫卯半刚性连接吸收地震能量",
                shinbashira=False,
                shinbashira_diameter=0.0,
            ),
            "gojunoto": DynastyPagodaModel(
                name="法隆寺五重塔",
                dynasty="飞鸟时代",
                country="日本",
                height=32.45,
                floor_count=5,
                structural_type="多重塔",
                floor_heights=[8.50, 6.60, 5.40, 4.20, 3.75],
                floor_diameters=[10.80, 9.20, 7.80, 6.50, 5.20],
                inner_diameters=[3.5, 3.0, 2.5, 2.0, 1.5],
                wall_thickness=[0.8, 0.7, 0.6, 0.5, 0.4],
                timber_properties={
                    "E_L": 9000.0,
                    "E_R": 600.0,
                    "E_T": 400.0,
                    "density": 450.0,
                },
                joint_properties={
                    "rotational_stiffness": 5e7,
                    "yield_moment": 5e4,
                },
                seismic_philosophy="柔性屈服：层间大变形+心柱恢复力",
                shinbashira=True,
                shinbashira_diameter=0.6,
            ),
        }

    def get_pagoda_model(self, pagoda_id: str) -> DynastyPagodaModel:
        if pagoda_id not in self.PAGODA_MODELS:
            raise ValueError(f"未找到木塔模型：{pagoda_id}")
        return self.PAGODA_MODELS[pagoda_id]

    def list_pagodas(self) -> list:
        result = []
        for k, v in self.PAGODA_MODELS.items():
            result.append({
                "id": k,
                "name": v.name,
                "dynasty": v.dynasty,
                "country": v.country,
                "height": v.height,
                "floor_count": v.floor_count,
                "structural_type": v.structural_type,
                "has_shinbashira": v.shinbashira,
                "seismic_philosophy": v.seismic_philosophy,
            })
        return result

    def _compute_section_properties(self, pagoda: DynastyPagodaModel):
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

    def _compute_natural_frequencies(self, pagoda: DynastyPagodaModel) -> np.ndarray:
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

    def _compute_wind_displacement(self, pagoda: DynastyPagodaModel, wind_speed: float) -> float:
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

    def _compute_energy_dissipation(self, pagoda: DynastyPagodaModel) -> dict:
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
