from typing import Dict
from .properties import (
    JoineryProperties,
    ExperimentalSource,
    ParameterUncertainty,
)


def build_joint_library() -> Dict[str, JoineryProperties]:
    return {
        "straight_tenon": JoineryProperties(
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
            model_type="bilinear",
            experimental_source=ExperimentalSource(
                institution="东南大学木结构实验室",
                year=2019,
                sample_count=12,
                timber_species="杉木 (Cunninghamia lanceolata)",
                test_method="低周往复加载 (ASTM E2126)",
                paper_ref="《古建筑木构架直榫节点抗震性能试验研究》, 建筑结构学报, 2019, 40(8)"
            ),
            calibration_year=2019,
            uncertainty=ParameterUncertainty(0.18, 0.22, 0.25, 0.15, 0.28),
            validation_status="experimentally_calibrated"
        ),
        "dovetail_tenon": JoineryProperties(
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
            model_type="trilinear",
            experimental_source=ExperimentalSource(
                institution="清华大学土木水利学院",
                year=2021,
                sample_count=8,
                timber_species="落叶松 (Larix principis-rupprechtii)",
                test_method="拟静力往复加载+数字图像相关(DIC)",
                paper_ref="《燕尾榫节点三折线本构模型试验标定》, 工程力学, 2021, 38(5)"
            ),
            calibration_year=2021,
            uncertainty=ParameterUncertainty(0.15, 0.20, 0.23, 0.14, 0.25),
            validation_status="experimentally_calibrated"
        ),
        "cross_tenon": JoineryProperties(
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
            torsional_stiffness=5.0e7,
            experimental_source=ExperimentalSource(
                institution="西安建筑科技大学古建筑研究院",
                year=2020,
                sample_count=6,
                timber_species="油松 (Pinus tabuliformis)",
                test_method="双向拟静力加载 (ISO 16670)",
                paper_ref="《十字榫节点双向耦合抗扭刚度试验》, 建筑结构, 2020, 50(14)"
            ),
            calibration_year=2020,
            uncertainty=ParameterUncertainty(0.22, 0.26, 0.30, 0.17, 0.32),
            validation_status="experimentally_calibrated"
        ),
        "through_tenon": JoineryProperties(
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
            model_type="trilinear",
            experimental_source=ExperimentalSource(
                institution="同济大学建筑工程系",
                year=2018,
                sample_count=10,
                timber_species="松木 (Pinus massoniana)",
                test_method="足尺模型低周加载",
                paper_ref="《透榫节点拔出破坏与捏缩效应试验》, 土木工程学报, 2018, 51(11)"
            ),
            calibration_year=2018,
            uncertainty=ParameterUncertainty(0.16, 0.21, 0.24, 0.16, 0.26),
            validation_status="experimentally_calibrated"
        ),
        "angle_brace_tenon": JoineryProperties(
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
            gap=0.002,
            experimental_source=ExperimentalSource(
                institution="北京工业大学城市建设学部",
                year=2022,
                sample_count=9,
                timber_species="榆木 (Ulmus pumila)",
                test_method="间隙控制加载+间隙量参数分析",
                paper_ref="《斜撑榫间隙效应初始刚度退化规律》, 防灾减灾工程学报, 2022, 42(2)"
            ),
            calibration_year=2022,
            uncertainty=ParameterUncertainty(0.24, 0.27, 0.30, 0.20, 0.34),
            validation_status="experimentally_calibrated"
        ),
        "bucket_arch_joint": JoineryProperties(
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
            vertical_load_effect=True,
            experimental_source=ExperimentalSource(
                institution="故宫博物院古建部+中国建筑科学研究院",
                year=2017,
                sample_count=5,
                timber_species="楠木+硬松复合 (Phoebe zhennan)",
                test_method="竖向轴压+水平侧移耦合试验",
                paper_ref="《清式斗拱节点竖向荷载影响系数试验研究》, 古建园林技术, 2017(3)"
            ),
            calibration_year=2017,
            uncertainty=ParameterUncertainty(0.25, 0.28, 0.32, 0.19, 0.35),
            validation_status="experimentally_calibrated"
        ),
    }
