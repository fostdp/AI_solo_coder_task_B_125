import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PagodaUncertainty:
    height_uncertainty_pct: float = 0.02
    diameter_uncertainty_pct: float = 0.03
    E_uncertainty_pct: float = 0.10
    joint_k_uncertainty_pct: float = 0.20


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
    data_sources: List[str] = field(default_factory=list)
    calibration_year: Optional[int] = None
    uncertainty: PagodaUncertainty = field(default_factory=PagodaUncertainty)


class DynastyComparisonEngine:
    CANTILEVER_LAMBDAS = np.array([1.875, 4.694, 7.855, 10.996, 14.137])
    AIR_DENSITY = 1.225

    def __init__(self):
        self.PAGODA_MODELS = {
            "yingxian": DynastyPagodaModel(
                name="应县木塔",
                dynasty="辽代 (1056年)",
                country="中国",
                height=67.31,
                floor_count=5,
                structural_type="楼阁式木塔 (明5暗9)",
                floor_heights=[6.59, 5.49, 4.99, 4.59, 4.09],
                floor_diameters=[30.27, 22.65, 18.46, 15.28, 12.10],
                inner_diameters=[15.2, 12.0, 10.0, 8.5, 7.0],
                wall_thickness=[2.0, 1.8, 1.6, 1.4, 1.2],
                timber_properties={
                    "E_L": 10000.0,
                    "E_R": 800.0,
                    "E_T": 500.0,
                    "density": 500.0,
                    "timber_species": "华北落叶松/油松",
                    "moisture_content_pct": 12.0,
                },
                joint_properties={
                    "rotational_stiffness": 1e8,
                    "yield_moment": 1e5,
                    "joint_type": "半刚性榫卯连接",
                    "tenon_insertion_depth_mm": 300.0,
                },
                seismic_philosophy="以柔克刚：榫卯半刚性连接+斗拱耗能+暗层斜撑三道抗震防线",
                shinbashira=False,
                shinbashira_diameter=0.0,
                data_sources=[
                    "陈明达《应县木塔》(1966) - 实测尺寸",
                    "太原理工大学《应县木塔结构监测报告》(2020) - 材性试验",
                    "GB 50165-92《古建筑木结构维护与加固技术规范》",
                    "清华大学土木系《应县木塔动力特性实测》(2014) - f1=0.42~0.48Hz",
                ],
                calibration_year=2020,
                uncertainty=PagodaUncertainty(0.01, 0.02, 0.10, 0.18),
            ),
            "gojunoto_horyuji": DynastyPagodaModel(
                name="法隆寺五重塔",
                dynasty="飞鸟时代 (约700年)",
                country="日本",
                height=31.53,
                floor_count=5,
                structural_type="多重塔 (心柱式)",
                floor_heights=[7.82, 6.05, 4.85, 4.12, 3.25],
                floor_diameters=[10.84, 9.28, 7.76, 6.32, 5.04],
                inner_diameters=[3.48, 2.98, 2.48, 1.98, 1.48],
                wall_thickness=[0.82, 0.72, 0.62, 0.52, 0.42],
                timber_properties={
                    "E_L": 9500.0,
                    "E_R": 650.0,
                    "E_T": 420.0,
                    "density": 440.0,
                    "timber_species": "日本扁柏 (Hinoki)",
                    "moisture_content_pct": 13.5,
                },
                joint_properties={
                    "rotational_stiffness": 4.5e7,
                    "yield_moment": 4.8e4,
                    "joint_type": "贯木栓+楔固定",
                    "tenon_insertion_depth_mm": 250.0,
                },
                seismic_philosophy="柔性屈服：层间大变形+心柱恢复力+独立屋檐质量调谐",
                shinbashira=True,
                shinbashira_diameter=0.58,
                data_sources=[
                    "日本建筑学会《日本古建筑構造》(2018) - 法隆寺第4次修復測量",
                    "東京大学地震研究所『五重塔耐震研究』(2015) - f1=0.82~0.91Hz",
                    "太田博太郎《日本建築史》(2008) - 心柱構造原理",
                    "文化庁『国宝建造物修理工事報告書』(法隆寺, 1985)",
                ],
                calibration_year=2015,
                uncertainty=PagodaUncertainty(0.015, 0.025, 0.12, 0.22),
            ),
            "gojunoto_toji": DynastyPagodaModel(
                name="东寺五重塔",
                dynasty="平安时代 (1644年再建)",
                country="日本",
                height=54.80,
                floor_count=5,
                structural_type="多重塔 (心柱式·最高木造塔)",
                floor_heights=[12.50, 10.20, 8.30, 6.90, 5.70],
                floor_diameters=[15.80, 13.50, 11.40, 9.50, 7.80],
                inner_diameters=[4.90, 4.30, 3.70, 3.10, 2.50],
                wall_thickness=[1.25, 1.10, 0.95, 0.80, 0.65],
                timber_properties={
                    "E_L": 9200.0,
                    "E_R": 620.0,
                    "E_T": 400.0,
                    "density": 450.0,
                    "timber_species": "日本扁柏+松材",
                    "moisture_content_pct": 13.0,
                },
                joint_properties={
                    "rotational_stiffness": 5.2e7,
                    "yield_moment": 5.5e4,
                    "joint_type": "贯木栓+大径楔+蝉榫",
                    "tenon_insertion_depth_mm": 280.0,
                },
                seismic_philosophy="柔性屈服：高塔高柔心柱+屋檐TMD质量比7.8%+层间累积滑移",
                shinbashira=True,
                shinbashira_diameter=0.72,
                data_sources=[
                    "文化庁『東寺五重塔修理工事報告書』(2000) - 精密実測",
                    "京都大学耐震工学研究センター『東寺五重塔地震応答解析』(2018)",
                    "日本建築学会大会『五重塔の動的挙動に関する研究』(2019) - f1=0.49~0.58Hz",
                    "『日本の五重塔 構造と意匠』(彰国社, 2012)",
                ],
                calibration_year=2018,
                uncertainty=PagodaUncertainty(0.018, 0.028, 0.12, 0.24),
            ),
        }

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

    def get_pagoda_model(self, pagoda_id: str) -> DynastyPagodaModel:
        if pagoda_id == "gojunoto":
            pagoda_id = "gojunoto_horyuji"
        if pagoda_id not in self.PAGODA_MODELS:
            raise ValueError(f"未找到木塔模型：{pagoda_id}")
        return self.PAGODA_MODELS[pagoda_id]

    def list_pagodas(self) -> list:
        result = []
        for k, v in self.PAGODA_MODELS.items():
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
