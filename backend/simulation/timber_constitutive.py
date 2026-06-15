import numpy as np
from typing import Dict, Tuple


class TimberOrthotropicConstitutive:
    """
    木材各向异性本构模型
    木材为正交各向异性材料，具有三个互相垂直的弹性对称面：
    - L方向：顺纹方向（纵向）
    - R方向：径向（垂直于年轮）
    - T方向：弦向（平行于年轮）
    """

    def __init__(self, properties: Dict[str, float]):
        """
        初始化木材本构模型

        Args:
            properties: 木材弹性参数字典
                E_L: 顺纹弹性模量 (MPa)
                E_R: 径向弹性模量 (MPa)
                E_T: 弦向弹性模量 (MPa)
                G_LR: LR面剪切模量 (MPa)
                G_LT: LT面剪切模量 (MPa)
                G_RT: RT面剪切模量 (MPa)
                v_LR: LR面泊松比
                v_LT: LT面泊松比
                v_RT: RT面泊松比
                density: 密度 (kg/m³)
        """
        self.E_L = properties.get('E_L', 10000.0)
        self.E_R = properties.get('E_R', 800.0)
        self.E_T = properties.get('E_T', 500.0)
        self.G_LR = properties.get('G_LR', 700.0)
        self.G_LT = properties.get('G_LT', 600.0)
        self.G_RT = properties.get('G_RT', 100.0)
        self.v_LR = properties.get('v_LR', 0.35)
        self.v_LT = properties.get('v_LT', 0.45)
        self.v_RT = properties.get('v_RT', 0.55)
        self.density = properties.get('density', 450.0)

        self._validate_properties()
        self._compute_compliance_matrix()
        self._compute_stiffness_matrix()

    def _validate_properties(self):
        """验证材料参数的物理合理性"""
        assert self.E_L > 0, "顺纹弹性模量必须为正"
        assert self.E_R > 0, "径向弹性模量必须为正"
        assert self.E_T > 0, "弦向弹性模量必须为正"
        assert self.E_L > self.E_R > self.E_T, \
            "弹性模量应满足 E_L > E_R > E_T"
        assert 0 < self.v_LR < 0.5, "泊松比应在(0, 0.5)范围内"
        assert 0 < self.v_LT < 0.5, "泊松比应在(0, 0.5)范围内"
        assert 0 < self.v_RT < 0.5, "泊松比应在(0, 0.5)范围内"

        self.v_RL = self.v_LR * self.E_R / self.E_L
        self.v_TL = self.v_LT * self.E_T / self.E_L
        self.v_TR = self.v_RT * self.E_T / self.E_R

    def _compute_compliance_matrix(self):
        """
        计算柔度矩阵 [S] (6x6)
        应力应变关系: {ε} = [S]{σ}
        """
        S = np.zeros((6, 6))

        S[0, 0] = 1.0 / self.E_L
        S[0, 1] = -self.v_RL / self.E_R
        S[0, 2] = -self.v_TL / self.E_T

        S[1, 0] = -self.v_LR / self.E_L
        S[1, 1] = 1.0 / self.E_R
        S[1, 2] = -self.v_TR / self.E_T

        S[2, 0] = -self.v_LT / self.E_L
        S[2, 1] = -self.v_RT / self.E_R
        S[2, 2] = 1.0 / self.E_T

        S[3, 3] = 1.0 / self.G_RT
        S[4, 4] = 1.0 / self.G_LT
        S[5, 5] = 1.0 / self.G_LR

        self.compliance_matrix = S

    def _compute_stiffness_matrix(self):
        """
        计算刚度矩阵 [C] (6x6)
        应力应变关系: {σ} = [C]{ε}
        [C] = [S]⁻¹
        """
        self.stiffness_matrix = np.linalg.inv(self.compliance_matrix)

    def get_stiffness_matrix(self) -> np.ndarray:
        """获取正交各向异性刚度矩阵"""
        return self.stiffness_matrix.copy()

    def get_compliance_matrix(self) -> np.ndarray:
        """获取正交各向异性柔度矩阵"""
        return self.compliance_matrix.copy()

    def compute_stress(self, strain: np.ndarray) -> np.ndarray:
        """
        由应变计算应力

        Args:
            strain: 应变向量 [ε_L, ε_R, ε_T, γ_RT, γ_LT, γ_LR]

        Returns:
            stress: 应力向量 [σ_L, σ_R, σ_T, τ_RT, τ_LT, τ_LR] (MPa)
        """
        return self.stiffness_matrix @ strain

    def compute_strain(self, stress: np.ndarray) -> np.ndarray:
        """
        由应力计算应变

        Args:
            stress: 应力向量 [σ_L, σ_R, σ_T, τ_RT, τ_LT, τ_LR] (MPa)

        Returns:
            strain: 应变向量 [ε_L, ε_R, ε_T, γ_RT, γ_LT, γ_LR]
        """
        return self.compliance_matrix @ stress

    def get_engineering_constants(self) -> Dict[str, float]:
        """获取所有工程常数"""
        return {
            'E_L': self.E_L,
            'E_R': self.E_R,
            'E_T': self.E_T,
            'G_LR': self.G_LR,
            'G_LT': self.G_LT,
            'G_RT': self.G_RT,
            'v_LR': self.v_LR,
            'v_LT': self.v_LT,
            'v_RT': self.v_RT,
            'v_RL': self.v_RL,
            'v_TL': self.v_TL,
            'v_TR': self.v_TR,
            'density': self.density
        }


class TimberBeamElement:
    """
    铁木辛柯梁单元，考虑木材各向异性
    每个节点6个自由度: ux, uy, uz, θx, θy, θz
    """

    def __init__(self, node_i: np.ndarray, node_j: np.ndarray,
                 constitutive: TimberOrthotropicConstitutive,
                 cross_section: Dict[str, float]):
        """
        初始化梁单元

        Args:
            node_i: 节点i坐标 [x, y, z]
            node_j: 节点j坐标 [x, y, z]
            constitutive: 木材本构模型
            cross_section: 截面参数
                width: 截面宽度 (m)
                height: 截面高度 (m)
                A: 截面积 (m²)
                Ixx: 绕x轴惯性矩 (m⁴)
                Iyy: 绕y轴惯性矩 (m⁴)
                Izz: 绕z轴惯性矩 (m⁴)
                shear_area_y: y向剪切面积 (m²)
                shear_area_z: z向剪切面积 (m²)
        """
        self.node_i = np.array(node_i)
        self.node_j = np.array(node_j)
        self.constitutive = constitutive
        self.cross_section = cross_section

        self._compute_element_properties()
        self._compute_transformation_matrix()
        self._compute_local_stiffness_matrix()
        self._compute_mass_matrix()

    def _compute_element_properties(self):
        """计算单元几何属性"""
        self.vector = self.node_j - self.node_i
        self.length = np.linalg.norm(self.vector)
        assert self.length > 0, "单元长度必须大于0"

        self.direction_cosines = self.vector / self.length

        A = self.cross_section.get('A')
        if A is None:
            w = self.cross_section['width']
            h = self.cross_section['height']
            A = w * h

        self.A = A
        self.Ixx = self.cross_section.get('Ixx', A * (
            self.cross_section.get('width', 0.3) ** 2 +
            self.cross_section.get('height', 0.3) ** 2) / 12)
        self.Iyy = self.cross_section.get('Iyy', A * self.cross_section.get('height', 0.3) ** 2 / 12)
        self.Izz = self.cross_section.get('Izz', A * self.cross_section.get('width', 0.3) ** 2 / 12)

        self.k_sy = self.cross_section.get('shear_factor_y', 5.0 / 6.0)
        self.k_sz = self.cross_section.get('shear_factor_z', 5.0 / 6.0)
        self.A_sy = self.cross_section.get('shear_area_y', self.k_sy * A)
        self.A_sz = self.cross_section.get('shear_area_z', self.k_sz * A)

    def _compute_transformation_matrix(self):
        """
        计算坐标变换矩阵 (12x12)
        将局部坐标系转换到整体坐标系
        """
        cx, cy, cz = self.direction_cosines

        if abs(abs(cz) - 1.0) < 1e-6:
            R = np.array([
                [0, 0, np.sign(cz)],
                [0, 1, 0],
                [-np.sign(cz), 0, 0]
            ])
        else:
            denom = np.sqrt(1 - cz ** 2)
            R = np.array([
                [cx, cy, cz],
                [-cy / denom, cx / denom, 0],
                [-cx * cz / denom, -cy * cz / denom, denom]
            ])

        T = np.zeros((12, 12))
        for i in range(4):
            T[3 * i:3 * i + 3, 3 * i:3 * i + 3] = R

        self.transformation_matrix = T

    def _compute_local_stiffness_matrix(self):
        """
        计算局部坐标系下的单元刚度矩阵 (12x12)
        考虑剪切变形的铁木辛柯梁
        """
        L = self.length
        E_L = self.constitutive.E_L * 1e6  # MPa -> Pa
        G_LR = self.constitutive.G_LR * 1e6
        G_LT = self.constitutive.G_LT * 1e6
        rho = self.constitutive.density

        k_y = 12 * E_L * self.Iyy / (G_LT * self.A_sy * L ** 2)
        k_z = 12 * E_L * self.Izz / (G_LR * self.A_sz * L ** 2)

        phi_y = 1 / (1 + k_y)
        phi_z = 1 / (1 + k_z)

        k_local = np.zeros((12, 12))

        k_local[0, 0] = E_L * self.A / L
        k_local[0, 6] = -E_L * self.A / L
        k_local[6, 0] = -E_L * self.A / L
        k_local[6, 6] = E_L * self.A / L

        k_local[1, 1] = 12 * E_L * self.Izz * phi_z / (L ** 3 * (1 + k_z))
        k_local[1, 5] = 6 * E_L * self.Izz * phi_z / (L ** 2 * (1 + k_z))
        k_local[1, 7] = -12 * E_L * self.Izz * phi_z / (L ** 3 * (1 + k_z))
        k_local[1, 11] = 6 * E_L * self.Izz * phi_z / (L ** 2 * (1 + k_z))

        k_local[2, 2] = 12 * E_L * self.Iyy * phi_y / (L ** 3 * (1 + k_y))
        k_local[2, 4] = -6 * E_L * self.Iyy * phi_y / (L ** 2 * (1 + k_y))
        k_local[2, 8] = -12 * E_L * self.Iyy * phi_y / (L ** 3 * (1 + k_y))
        k_local[2, 10] = -6 * E_L * self.Iyy * phi_y / (L ** 2 * (1 + k_y))

        k_local[3, 3] = G_LR * self.Ixx / L
        k_local[3, 9] = -G_LR * self.Ixx / L

        k_local[4, 2] = -6 * E_L * self.Iyy * phi_y / (L ** 2 * (1 + k_y))
        k_local[4, 4] = (4 + k_y) * E_L * self.Iyy * phi_y / (L * (1 + k_y))
        k_local[4, 8] = 6 * E_L * self.Iyy * phi_y / (L ** 2 * (1 + k_y))
        k_local[4, 10] = (2 - k_y) * E_L * self.Iyy * phi_y / (L * (1 + k_y))

        k_local[5, 1] = 6 * E_L * self.Izz * phi_z / (L ** 2 * (1 + k_z))
        k_local[5, 5] = (4 + k_z) * E_L * self.Izz * phi_z / (L * (1 + k_z))
        k_local[5, 7] = -6 * E_L * self.Izz * phi_z / (L ** 2 * (1 + k_z))
        k_local[5, 11] = (2 - k_z) * E_L * self.Izz * phi_z / (L * (1 + k_z))

        k_local[6, 0] = -E_L * self.A / L
        k_local[6, 6] = E_L * self.A / L

        k_local[7, 1] = -12 * E_L * self.Izz * phi_z / (L ** 3 * (1 + k_z))
        k_local[7, 5] = -6 * E_L * self.Izz * phi_z / (L ** 2 * (1 + k_z))
        k_local[7, 7] = 12 * E_L * self.Izz * phi_z / (L ** 3 * (1 + k_z))
        k_local[7, 11] = -6 * E_L * self.Izz * phi_z / (L ** 2 * (1 + k_z))

        k_local[8, 2] = -12 * E_L * self.Iyy * phi_y / (L ** 3 * (1 + k_y))
        k_local[8, 4] = 6 * E_L * self.Iyy * phi_y / (L ** 2 * (1 + k_y))
        k_local[8, 8] = 12 * E_L * self.Iyy * phi_y / (L ** 3 * (1 + k_y))
        k_local[8, 10] = 6 * E_L * self.Iyy * phi_y / (L ** 2 * (1 + k_y))

        k_local[9, 3] = -G_LR * self.Ixx / L
        k_local[9, 9] = G_LR * self.Ixx / L

        k_local[10, 2] = -6 * E_L * self.Iyy * phi_y / (L ** 2 * (1 + k_y))
        k_local[10, 4] = (2 - k_y) * E_L * self.Iyy * phi_y / (L * (1 + k_y))
        k_local[10, 8] = 6 * E_L * self.Iyy * phi_y / (L ** 2 * (1 + k_y))
        k_local[10, 10] = (4 + k_y) * E_L * self.Iyy * phi_y / (L * (1 + k_y))

        k_local[11, 1] = 6 * E_L * self.Izz * phi_z / (L ** 2 * (1 + k_z))
        k_local[11, 5] = (2 - k_z) * E_L * self.Izz * phi_z / (L * (1 + k_z))
        k_local[11, 7] = -6 * E_L * self.Izz * phi_z / (L ** 2 * (1 + k_z))
        k_local[11, 11] = (4 + k_z) * E_L * self.Izz * phi_z / (L * (1 + k_z))

        for i in range(12):
            for j in range(i + 1, 12):
                k_local[j, i] = k_local[i, j]

        self.local_stiffness = k_local

    def _compute_mass_matrix(self):
        """
        计算一致质量矩阵 (12x12)
        """
        L = self.length
        rho = self.constitutive.density
        A = self.A
        Ixx = self.Ixx
        Iyy = self.Iyy
        Izz = self.Izz

        m_local = np.zeros((12, 12))

        factor = rho * A * L / 420

        m_local[0, 0] = 140 * factor
        m_local[0, 6] = 70 * factor
        m_local[6, 0] = 70 * factor
        m_local[6, 6] = 140 * factor

        m_local[1, 1] = 156 * factor
        m_local[1, 5] = 22 * L * factor
        m_local[1, 7] = 54 * factor
        m_local[1, 11] = -13 * L * factor

        m_local[2, 2] = 156 * factor
        m_local[2, 4] = -22 * L * factor
        m_local[2, 8] = 54 * factor
        m_local[2, 10] = 13 * L * factor

        m_local[3, 3] = 140 * rho * Ixx * L / 420
        m_local[3, 9] = 70 * rho * Ixx * L / 420
        m_local[9, 3] = 70 * rho * Ixx * L / 420
        m_local[9, 9] = 140 * rho * Ixx * L / 420

        m_local[4, 2] = -22 * L * factor
        m_local[4, 4] = 4 * L ** 2 * factor
        m_local[4, 8] = -13 * L * factor
        m_local[4, 10] = -3 * L ** 2 * factor

        m_local[5, 1] = 22 * L * factor
        m_local[5, 5] = 4 * L ** 2 * factor
        m_local[5, 7] = 13 * L * factor
        m_local[5, 11] = -3 * L ** 2 * factor

        m_local[7, 1] = 54 * factor
        m_local[7, 5] = 13 * L * factor
        m_local[7, 7] = 156 * factor
        m_local[7, 11] = -22 * L * factor

        m_local[8, 2] = 54 * factor
        m_local[8, 4] = -13 * L * factor
        m_local[8, 8] = 156 * factor
        m_local[8, 10] = 22 * L * factor

        m_local[10, 2] = 13 * L * factor
        m_local[10, 4] = -3 * L ** 2 * factor
        m_local[10, 8] = 22 * L * factor
        m_local[10, 10] = 4 * L ** 2 * factor

        m_local[11, 1] = -13 * L * factor
        m_local[11, 5] = -3 * L ** 2 * factor
        m_local[11, 7] = -22 * L * factor
        m_local[11, 11] = 4 * L ** 2 * factor

        for i in range(12):
            for j in range(i + 1, 12):
                m_local[j, i] = m_local[i, j]

        self.local_mass = m_local

    def get_global_stiffness(self) -> np.ndarray:
        """获取整体坐标系下的单元刚度矩阵"""
        T = self.transformation_matrix
        return T.T @ self.local_stiffness @ T

    def get_global_mass(self) -> np.ndarray:
        """获取整体坐标系下的单元质量矩阵"""
        T = self.transformation_matrix
        return T.T @ self.local_mass @ T

    def transform_force_to_global(self, local_force: np.ndarray) -> np.ndarray:
        """将局部坐标下的节点力转换到整体坐标"""
        return self.transformation_matrix.T @ local_force
