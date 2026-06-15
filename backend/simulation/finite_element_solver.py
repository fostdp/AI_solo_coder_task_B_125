import numpy as np
from scipy.linalg import eigh, cholesky, solve
from scipy.sparse import lil_matrix, csr_matrix
from scipy.sparse.linalg import spsolve
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass
from .timber_constitutive import TimberOrthotropicConstitutive, TimberBeamElement


@dataclass
class NonlinearSpringProperties:
    """非线性弹簧单元参数 - 模拟榫卯节点"""
    k_initial: float = 1e8           # 初始刚度 (N/m)
    k_softening: float = 1e7         # 软化段刚度 (N/m)
    yield_force: float = 1e5         # 屈服力 (N)
    hardening_factor: float = 0.1    # 硬化系数
    gap: float = 0.001               # 初始间隙 (m)
    damping_ratio: float = 0.05      # 阻尼比


class NonlinearRotationalSpring:
    """
    非线性转动弹簧单元 - 模拟榫卯节点的半刚性连接
    采用三折线模型：弹性段 -> 屈服段 -> 软化段
    """

    def __init__(self, node_i: int, node_j: int,
                 properties: NonlinearSpringProperties,
                 axis: str = 'x'):
        """
        Args:
            node_i, node_j: 连接的两个节点
            properties: 弹簧参数
            axis: 弹簧作用轴 'x', 'y', 'z'
        """
        self.node_i = node_i
        self.node_j = node_j
        self.properties = properties
        self.axis = axis

        self.history_deformation = 0.0
        self.history_force = 0.0
        self.unloading_stiffness = properties.k_initial
        self.yielded = False
        self.damage_index = 0.0

    def compute_tangent_stiffness(self, deformation: float) -> float:
        """
        计算切线刚度（考虑非线性）

        三折线本构模型:
        F
        ^
        |       k2
        |     /----
        |    /
        |   / k1
        |  /
        | /
        +--------> δ
              δ_y

        Args:
            deformation: 当前变形量 (rad)

        Returns:
            k_t: 切线刚度
        """
        d_abs = abs(deformation)
        sign = np.sign(deformation)

        if d_abs < self.properties.gap:
            return 0.0

        d_eff = d_abs - self.properties.gap
        d_y = self.properties.yield_force / self.properties.k_initial

        if d_eff <= d_y:
            return self.properties.k_initial
        elif d_eff <= 3 * d_y:
            return self.properties.k_softening
        else:
            return self.properties.k_softening * self.properties.hardening_factor

    def compute_force(self, deformation: float, velocity: float = 0.0) -> Tuple[float, float]:
        """
        计算弹簧力（考虑阻尼和加载历史）

        Args:
            deformation: 当前变形
            velocity: 变形速度

        Returns:
            force: 弹簧力
            stiffness: 割线刚度
        """
        d_abs = abs(deformation)
        sign = np.sign(deformation) if deformation != 0 else 1.0

        if d_abs < self.properties.gap:
            return 0.0, 0.0

        d_eff = d_abs - self.properties.gap
        d_y = self.properties.yield_force / self.properties.k_initial

        if d_eff <= d_y:
            force_mag = self.properties.k_initial * d_eff
            stiffness = self.properties.k_initial
        elif d_eff <= 3 * d_y:
            force_mag = self.properties.yield_force + \
                       self.properties.k_softening * (d_eff - d_y)
            stiffness = self.properties.k_softening
            if not self.yielded:
                self.yielded = True
                self.unloading_stiffness = \
                    (force_mag - self.history_force) / (d_eff - self.history_deformation + 1e-10)
        else:
            force_mag = self.properties.yield_force + \
                       self.properties.k_softening * 2 * d_y + \
                       self.properties.k_softening * self.properties.hardening_factor * (d_eff - 3 * d_y)
            stiffness = self.properties.k_softening * self.properties.hardening_factor

        damping_force = self.properties.damping_ratio * \
                        2 * np.sqrt(self.properties.k_initial * 1.0) * velocity

        total_force = sign * force_mag + damping_force

        self.history_deformation = d_eff
        self.history_force = force_mag

        if d_eff > 3 * d_y:
            self.damage_index = min(1.0, (d_eff - 3 * d_y) / (3 * d_y) * 0.5)

        return total_force, stiffness

    def get_element_stiffness_matrix(self, deformation: float = 0.0) -> np.ndarray:
        """
        获取单元刚度矩阵（12x12，对应两个节点的6个自由度）

        转动弹簧仅在指定轴上产生刚度
        """
        k = self.compute_tangent_stiffness(deformation)
        k_e = np.zeros((12, 12))

        rot_idx = {'x': 3, 'y': 4, 'z': 5}[self.axis]

        k_e[rot_idx, rot_idx] = k
        k_e[rot_idx, rot_idx + 6] = -k
        k_e[rot_idx + 6, rot_idx] = -k
        k_e[rot_idx + 6, rot_idx + 6] = k

        return k_e

    def reset(self):
        """重置弹簧状态"""
        self.history_deformation = 0.0
        self.history_force = 0.0
        self.unloading_stiffness = self.properties.k_initial
        self.yielded = False
        self.damage_index = 0.0


class PagodaFEAModel:
    """
    应县木塔有限元模型
    简化的多层框架模型，考虑木材各向异性
    """

    def __init__(self, timber_properties: Dict[str, float],
                 use_mortise_tenon: bool = True,
                 spring_properties: Optional[NonlinearSpringProperties] = None):
        """
        初始化有限元模型

        Args:
            timber_properties: 木材材料参数
            use_mortise_tenon: 是否启用榫卯节点非线性弹簧
            spring_properties: 榫卯弹簧参数
        """
        self.constitutive = TimberOrthotropicConstitutive(timber_properties)
        self.nodes: List[np.ndarray] = []
        self.elements: List[TimberBeamElement] = []
        self.springs: List[NonlinearRotationalSpring] = []
        self.node_dof_map: Dict[int, np.ndarray] = {}
        self.n_dofs: int = 0
        self.boundary_conditions: Dict[int, np.ndarray] = {}
        self.K: Optional[np.ndarray] = None
        self.M: Optional[np.ndarray] = None
        self.C: Optional[np.ndarray] = None
        self.natural_frequencies: Optional[np.ndarray] = None
        self.mode_shapes: Optional[np.ndarray] = None
        self.floor_heights: np.ndarray = np.array([9.23, 17.73, 25.53, 32.73, 39.23])
        self.floor_diameters: np.ndarray = np.array([30.27, 25.80, 22.50, 19.80, 17.50])
        self.n_floors = 5
        self.columns_per_floor = 24
        self.beams_per_floor = 48
        self.use_mortise_tenon = use_mortise_tenon
        self.spring_properties = spring_properties or NonlinearSpringProperties(
            k_initial=5e7,
            k_softening=5e6,
            yield_force=5e4,
            hardening_factor=0.1,
            gap=0.0005,
            damping_ratio=0.03
        )
        self.mortise_tenon_locations: List[Dict] = []

    def build_model(self):
        """构建木塔有限元模型"""
        self._create_nodes()
        self._create_column_elements()
        self._create_beam_elements()
        if self.use_mortise_tenon:
            self._create_mortise_tenon_springs()
        self._assemble_global_matrices()
        self._apply_boundary_conditions()

    def _create_mortise_tenon_springs(self):
        """
        创建榫卯节点非线性弹簧
        在梁-柱节点处添加X、Y、Z三个方向的转动弹簧
        每个梁柱节点连接点放置3个弹簧
        """
        spring_props = self.spring_properties
        floor_spring_props = [
            NonlinearSpringProperties(
                k_initial=spring_props.k_initial * (0.8 + i * 0.05),
                k_softening=spring_props.k_softening * (0.8 + i * 0.05),
                yield_force=spring_props.yield_force * (0.7 + i * 0.075),
                hardening_factor=spring_props.hardening_factor,
                gap=spring_props.gap * (1 + i * 0.2),
                damping_ratio=spring_props.damping_ratio
            )
            for i in range(self.n_floors)
        ]

        for floor_idx in range(self.n_floors):
            floor_props = floor_spring_props[floor_idx]
            for col_idx in range(self.columns_per_floor):
                node_lower = floor_idx * self.columns_per_floor + col_idx
                node_upper = (floor_idx + 1) * self.columns_per_floor + col_idx

                for axis in ['x', 'y', 'z']:
                    spring = NonlinearRotationalSpring(
                        node_lower,
                        node_upper,
                        floor_props,
                        axis
                    )
                    self.springs.append(spring)
                    self.mortise_tenon_locations.append({
                        'floor': floor_idx + 1,
                        'column': col_idx,
                        'axis': axis,
                        'node_lower': node_lower,
                        'node_upper': node_upper,
                        'spring_id': len(self.springs) - 1
                    })

    def _assemble_spring_stiffness(self, K: lil_matrix,
                                   deformations: Optional[np.ndarray] = None) -> None:
        """
        组装弹簧单元刚度矩阵

        Args:
            K: 整体刚度矩阵
            deformations: 当前各节点变形向量，用于计算非线性刚度
        """
        for spring in self.springs:
            deformation = 0.0
            if deformations is not None:
                dofs_i = self.node_dof_map[spring.node_i]
                dofs_j = self.node_dof_map[spring.node_j]
                rot_idx = {'x': 3, 'y': 4, 'z': 5}[spring.axis]
                deformation = deformations[dofs_j[rot_idx]] - deformations[dofs_i[rot_idx]]

            k_e = spring.get_element_stiffness_matrix(deformation)

            nodes = [spring.node_i, spring.node_j]
            dofs = []
            for node in nodes:
                dofs.extend(self.node_dof_map[node].tolist())

            for i, di in enumerate(dofs):
                for j, dj in enumerate(dofs):
                    K[di, dj] += k_e[i, j]

    def _create_nodes(self):
        """创建节点 - 每层创建24个柱节点"""
        node_id = 0

        for floor_idx in range(self.n_floors + 1):
            z = 0 if floor_idx == 0 else self.floor_heights[floor_idx - 1]
            radius = 15.0 if floor_idx == 0 else self.floor_diameters[floor_idx - 1] / 2

            for i in range(self.columns_per_floor):
                angle = 2 * np.pi * i / self.columns_per_floor
                x = radius * np.cos(angle)
                y = radius * np.sin(angle)

                self.nodes.append(np.array([x, y, z]))
                self.node_dof_map[node_id] = np.arange(node_id * 6, (node_id + 1) * 6)
                node_id += 1

        self.n_nodes = node_id
        self.n_dofs = self.n_nodes * 6

    def _create_column_elements(self):
        """创建柱单元"""
        column_section = {
            'width': 0.6,
            'height': 0.6,
            'A': 0.6 * 0.6,
            'Ixx': 0.6 * 0.6 ** 3 / 12,
            'Iyy': 0.6 * 0.6 ** 3 / 12,
            'Izz': 0.6 * 0.6 ** 3 / 12
        }

        for floor_idx in range(self.n_floors):
            for col_idx in range(self.columns_per_floor):
                node_i = floor_idx * self.columns_per_floor + col_idx
                node_j = (floor_idx + 1) * self.columns_per_floor + col_idx

                element = TimberBeamElement(
                    self.nodes[node_i],
                    self.nodes[node_j],
                    self.constitutive,
                    column_section
                )
                self.elements.append(element)

    def _create_beam_elements(self):
        """创建梁单元 - 每层创建内外两圈梁"""
        beam_section = {
            'width': 0.4,
            'height': 0.8,
            'A': 0.4 * 0.8,
            'Ixx': 0.4 * 0.8 ** 3 / 12,
            'Iyy': 0.8 * 0.4 ** 3 / 12,
            'Izz': 0.4 * 0.8 ** 3 / 12
        }

        for floor_idx in range(1, self.n_floors + 1):
            base_node = floor_idx * self.columns_per_floor

            for i in range(self.columns_per_floor):
                node_i = base_node + i
                node_j = base_node + (i + 1) % self.columns_per_floor

                element = TimberBeamElement(
                    self.nodes[node_i],
                    self.nodes[node_j],
                    self.constitutive,
                    beam_section
                )
                self.elements.append(element)

            for i in range(0, self.columns_per_floor, 2):
                node_i = base_node + i
                node_j = base_node + (i + self.columns_per_floor // 2) % self.columns_per_floor

                element = TimberBeamElement(
                    self.nodes[node_i],
                    self.nodes[node_j],
                    self.constitutive,
                    beam_section
                )
                self.elements.append(element)

    def _assemble_global_matrices(self):
        """组装整体刚度矩阵和质量矩阵"""
        K = lil_matrix((self.n_dofs, self.n_dofs))
        M = lil_matrix((self.n_dofs, self.n_dofs))

        for element in self.elements:
            k_e = element.get_global_stiffness()
            m_e = element.get_global_mass()

            nodes = [self.nodes.index(element.node_i), self.nodes.index(element.node_j)]
            dofs = []
            for node in nodes:
                dofs.extend(self.node_dof_map[node].tolist())

            for i, di in enumerate(dofs):
                for j, dj in enumerate(dofs):
                    K[di, dj] += k_e[i, j]
                    M[di, dj] += m_e[i, j]

        if self.use_mortise_tenon:
            self._assemble_spring_stiffness(K)

        self.K = K.tocsr()
        self.M = M.tocsr()

    def _update_tangent_stiffness(self, u: np.ndarray) -> csr_matrix:
        """
        更新切线刚度矩阵（考虑榫卯弹簧的非线性）

        Args:
            u: 当前位移向量

        Returns:
            K_t: 更新后的切线刚度矩阵
        """
        if not self.use_mortise_tenon:
            return self.K

        K = lil_matrix((self.n_dofs, self.n_dofs))

        for element in self.elements:
            k_e = element.get_global_stiffness()
            nodes = [self.nodes.index(element.node_i), self.nodes.index(element.node_j)]
            dofs = []
            for node in nodes:
                dofs.extend(self.node_dof_map[node].tolist())

            for i, di in enumerate(dofs):
                for j, dj in enumerate(dofs):
                    K[di, dj] += k_e[i, j]

        self._assemble_spring_stiffness(K, u)

        return K.tocsr()

    def _compute_spring_internal_forces(self, u: np.ndarray, v: np.ndarray) -> np.ndarray:
        """
        计算弹簧的内力向量

        Args:
            u: 位移向量
            v: 速度向量

        Returns:
            F_int: 内力向量
        """
        F_int = np.zeros(self.n_dofs)

        for spring in self.springs:
            dofs_i = self.node_dof_map[spring.node_i]
            dofs_j = self.node_dof_map[spring.node_j]
            rot_idx = {'x': 3, 'y': 4, 'z': 5}[spring.axis]

            deformation = u[dofs_j[rot_idx]] - u[dofs_i[rot_idx]]
            velocity = v[dofs_j[rot_idx]] - v[dofs_i[rot_idx]]

            force, _ = spring.compute_force(deformation, velocity)

            F_int[dofs_i[rot_idx]] += force
            F_int[dofs_j[rot_idx]] -= force

        return F_int

    def get_mortise_tenon_damage(self) -> List[Dict]:
        """获取榫卯节点的损伤状态"""
        damage_list = []
        for loc, spring in zip(self.mortise_tenon_locations, self.springs):
            if spring.damage_index > 0.01:
                damage_list.append({
                    'floor': loc['floor'],
                    'column': loc['column'],
                    'axis': loc['axis'],
                    'damage_index': spring.damage_index,
                    'yielded': spring.yielded,
                    'history_deformation': spring.history_deformation,
                    'history_force': spring.history_force
                })
        return damage_list

    def _apply_boundary_conditions(self):
        """施加边界条件 - 底部固定"""
        for node_id in range(self.columns_per_floor):
            dofs = self.node_dof_map[node_id]
            self.boundary_conditions[node_id] = dofs

        fixed_dofs = []
        for dofs in self.boundary_conditions.values():
            fixed_dofs.extend(dofs.tolist())

        self.fixed_dofs = np.array(fixed_dofs)
        self.free_dofs = np.setdiff1d(np.arange(self.n_dofs), self.fixed_dofs)

    def compute_modal_analysis(self, n_modes: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """
        模态分析

        Args:
            n_modes: 计算的模态阶数

        Returns:
            natural_frequencies: 固有频率 (Hz)
            mode_shapes: 振型矩阵
        """
        K_ff = self.K[self.free_dofs, :][:, self.free_dofs]
        M_ff = self.M[self.free_dofs, :][:, self.free_dofs]

        K_dense = K_ff.toarray()
        M_dense = M_ff.toarray()

        eigenvalues, eigenvectors = eigh(K_dense, M_dense, subset_by_index=[0, n_modes - 1])

        omega = np.sqrt(np.maximum(eigenvalues, 0))
        frequencies = omega / (2 * np.pi)

        mode_shapes_full = np.zeros((self.n_dofs, n_modes))
        mode_shapes_full[self.free_dofs, :] = eigenvectors

        for i in range(n_modes):
            max_val = np.max(np.abs(mode_shapes_full[:, i]))
            if max_val > 0:
                mode_shapes_full[:, i] /= max_val

        self.natural_frequencies = frequencies
        self.mode_shapes = mode_shapes_full

        return frequencies, mode_shapes_full

    def build_damping_matrix(self, damping_ratio: float = 0.02) -> np.ndarray:
        """
        构建瑞利阻尼矩阵

        C = alpha * M + beta * K

        Args:
            damping_ratio: 阻尼比

        Returns:
            C: 阻尼矩阵
        """
        if self.natural_frequencies is None:
            self.compute_modal_analysis()

        omega1 = 2 * np.pi * self.natural_frequencies[0]
        omega2 = 2 * np.pi * self.natural_frequencies[min(2, len(self.natural_frequencies) - 1)]

        alpha = 2 * damping_ratio * omega1 * omega2 / (omega1 + omega2)
        beta = 2 * damping_ratio / (omega1 + omega2)

        self.C = alpha * self.M + beta * self.K

        return self.C

    def _newmark_beta_solve(self, F: np.ndarray, dt: float,
                             u0: Optional[np.ndarray] = None,
                             v0: Optional[np.ndarray] = None,
                             gamma: float = 0.5,
                             beta: float = 0.25,
                             max_iterations: int = 20,
                             tolerance: float = 1e-6) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Newmark-beta法求解动力时程（考虑非线性，牛顿-拉夫逊迭代）

        Args:
            F: 荷载矩阵 [n_dofs, n_timesteps]
            dt: 时间步长
            u0: 初始位移
            v0: 初始速度
            gamma, beta: Newmark参数
            max_iterations: 最大迭代次数
            tolerance: 收敛容差

        Returns:
            u: 位移时程
            v: 速度时程
            a: 加速度时程
        """
        n_steps = F.shape[1]

        if u0 is None:
            u0 = np.zeros(self.n_dofs)
        if v0 is None:
            v0 = np.zeros(self.n_dofs)

        u = np.zeros((self.n_dofs, n_steps))
        v = np.zeros((self.n_dofs, n_steps))
        a = np.zeros((self.n_dofs, n_steps))

        u[:, 0] = u0
        v[:, 0] = v0

        for spring in self.springs:
            spring.reset()

        K_ff = self.K[self.free_dofs, :][:, self.free_dofs]
        M_ff = self.M[self.free_dofs, :][:, self.free_dofs]
        C_ff = self.C[self.free_dofs, :][:, self.free_dofs]
        F_ff = F[self.free_dofs, :]

        a0_ff = spsolve(K_ff, F_ff[:, 0])

        u_ff = np.zeros((len(self.free_dofs), n_steps))
        v_ff = np.zeros((len(self.free_dofs), n_steps))
        a_ff = np.zeros((len(self.free_dofs), n_steps))

        u_ff[:, 0] = u0[self.free_dofs]
        v_ff[:, 0] = v0[self.free_dofs]
        a_ff[:, 0] = a0_ff

        K_hat = K_ff + gamma / (beta * dt) * C_ff + 1 / (beta * dt ** 2) * M_ff

        for step in range(n_steps - 1):
            u_pred = u_ff[:, step] + dt * v_ff[:, step] + (dt ** 2 / 2) * (1 - 2 * beta) * a_ff[:, step]
            v_pred = v_ff[:, step] + dt * (1 - gamma) * a_ff[:, step]

            u_full = np.zeros(self.n_dofs)
            u_full[self.free_dofs] = u_pred
            v_full = np.zeros(self.n_dofs)
            v_full[self.free_dofs] = v_pred

            if self.use_mortise_tenon:
                F_int_full = self._compute_spring_internal_forces(u_full, v_full)
                F_int_ff = F_int_full[self.free_dofs]
            else:
                F_int_ff = np.zeros_like(u_pred)

            F_hat = F_ff[:, step + 1] - C_ff @ v_pred - K_ff @ u_pred - F_int_ff

            delta_u = spsolve(K_hat, F_hat)

            if self.use_mortise_tenon:
                u_iter = u_pred.copy()
                v_iter = v_pred.copy()
                a_iter = a_ff[:, step].copy()

                for iteration in range(max_iterations):
                    u_full_iter = np.zeros(self.n_dofs)
                    u_full_iter[self.free_dofs] = u_iter + delta_u
                    v_full_iter = np.zeros(self.n_dofs)
                    v_full_iter[self.free_dofs] = v_iter + gamma / (beta * dt) * delta_u

                    K_t_full = self._update_tangent_stiffness(u_full_iter)
                    K_t_ff = K_t_full[self.free_dofs, :][:, self.free_dofs]

                    F_int_full_iter = self._compute_spring_internal_forces(
                        u_full_iter, v_full_iter
                    )
                    F_int_ff_iter = F_int_full_iter[self.free_dofs]

                    v_new = v_pred + gamma / (beta * dt) * delta_u
                    a_new = (delta_u - dt * v_pred - dt ** 2 / 2 * (1 - 2 * beta) * a_iter) / (beta * dt ** 2)

                    residual = F_ff[:, step + 1] - \
                               M_ff @ a_new - \
                               C_ff @ v_new - \
                               K_t_ff @ (u_iter + delta_u) - \
                               F_int_ff_iter

                    residual_norm = np.linalg.norm(residual)
                    if residual_norm < tolerance:
                        break

                    K_hat_iter = K_t_ff + gamma / (beta * dt) * C_ff + 1 / (beta * dt ** 2) * M_ff
                    delta_u_correction = spsolve(K_hat_iter, residual)
                    delta_u += delta_u_correction

                    if np.linalg.norm(delta_u_correction) < tolerance * np.linalg.norm(delta_u):
                        break

            delta_v = gamma / (beta * dt) * delta_u - gamma / beta * v_ff[:, step] + dt * (1 - gamma / (2 * beta)) * a_ff[:, step]
            delta_a = 1 / (beta * dt ** 2) * delta_u - 1 / (beta * dt) * v_ff[:, step] - 1 / (2 * beta) * a_ff[:, step]

            u_ff[:, step + 1] = u_pred + delta_u
            v_ff[:, step + 1] = v_pred + delta_v
            a_ff[:, step + 1] = a_ff[:, step] + delta_a

        u[self.free_dofs, :] = u_ff
        v[self.free_dofs, :] = v_ff
        a[self.free_dofs, :] = a_ff

        return u, v, a

    def _modal_superposition(self, F: np.ndarray, dt: float,
                              n_modes: int = 10) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        模态叠加法求解动力时程

        Args:
            F: 荷载矩阵 [n_dofs, n_timesteps]
            dt: 时间步长
            n_modes: 使用的模态阶数

        Returns:
            u: 位移时程
            v: 速度时程
            a: 加速度时程
        """
        if self.natural_frequencies is None:
            self.compute_modal_analysis(n_modes)

        n_steps = F.shape[1]
        omega = 2 * np.pi * self.natural_frequencies[:n_modes]
        modes = self.mode_shapes[:, :n_modes]

        M_modal = np.diag(modes.T @ self.M @ modes)
        K_modal = np.diag(modes.T @ self.K @ modes)
        C_modal = np.diag(modes.T @ self.C @ modes)

        F_modal = modes.T @ F

        xi_modal = C_modal / (2 * omega * M_modal)

        u_modal = np.zeros((n_modes, n_steps))
        v_modal = np.zeros((n_modes, n_steps))
        a_modal = np.zeros((n_modes, n_steps))

        for i in range(n_modes):
            omega_i = omega[i]
            xi_i = xi_modal[i]
            F_i = F_modal[i, :] / M_modal[i]

            omega_d = omega_i * np.sqrt(1 - xi_i ** 2)

            for step in range(1, n_steps):
                t = step * dt
                f_prev = F_i[step - 1]
                f_curr = F_i[step]

                u_prev = u_modal[i, step - 1]
                v_prev = v_modal[i, step - 1]

                A = (f_curr - f_prev) / dt
                B = f_prev - A * (t - dt)

                u_p = (A * t + B - 2 * xi_i * A / omega_i) / omega_i ** 2
                u_p_prev = (A * (t - dt) + B - 2 * xi_i * A / omega_i) / omega_i ** 2

                C = u_prev - u_p_prev
                D = (v_prev + xi_i * omega_i * C - A / omega_i ** 2) / omega_d

                e_term = np.exp(-xi_i * omega_i * dt)
                cos_term = np.cos(omega_d * dt)
                sin_term = np.sin(omega_d * dt)

                u_modal[i, step] = e_term * (C * cos_term + D * sin_term) + u_p
                v_modal[i, step] = -xi_i * omega_i * u_modal[i, step] + \
                                   e_term * omega_d * (-C * sin_term + D * cos_term) + A / omega_i ** 2

            a_modal[i, :] = F_i - 2 * xi_i * omega_i * v_modal[i, :] - omega_i ** 2 * u_modal[i, :]

        u = modes @ u_modal
        v = modes @ v_modal
        a = modes @ a_modal

        return u, v, a

    def solve_dynamic_response(self, loads: Dict[int, np.ndarray],
                                t: np.ndarray,
                                damping_ratio: float = 0.02,
                                method: str = 'newmark') -> Dict:
        """
        求解结构动力响应

        Args:
            loads: 各节点荷载 {node_id: force_time_history}
            t: 时间向量
            damping_ratio: 阻尼比
            method: 'newmark' 或 'modal'

        Returns:
            results: 计算结果字典
        """
        self.build_damping_matrix(damping_ratio)

        dt = t[1] - t[0]
        n_steps = len(t)

        F = np.zeros((self.n_dofs, n_steps))

        for node_id, force in loads.items():
            dofs = self.node_dof_map[node_id]
            if len(force) == n_steps:
                F[dofs[0], :] = force
            elif len(force.shape) == 2 and force.shape[0] == 3:
                for i in range(3):
                    F[dofs[i], :] = force[i, :]

        if method == 'newmark':
            u, v, a = self._newmark_beta_solve(F, dt)
        else:
            u, v, a = self._modal_superposition(F, dt)

        floor_displacements = self._extract_floor_displacements(u)
        floor_accelerations = self._extract_floor_accelerations(a)
        element_stresses = self._compute_element_stresses(u)

        mortise_tenon_damage = self.get_mortise_tenon_damage() if self.use_mortise_tenon else []

        results = {
            'time': t,
            'displacement': u,
            'velocity': v,
            'acceleration': a,
            'floor_displacements': floor_displacements,
            'floor_accelerations': floor_accelerations,
            'element_stresses': element_stresses,
            'natural_frequencies': self.natural_frequencies,
            'mode_shapes': self.mode_shapes.tolist() if self.mode_shapes is not None else None,
            'mortise_tenon_damage': mortise_tenon_damage,
            'use_mortise_tenon': self.use_mortise_tenon,
            'spring_count': len(self.springs)
        }

        return results

    def _extract_floor_displacements(self, u: np.ndarray) -> Dict[int, Dict[str, np.ndarray]]:
        """提取各层位移"""
        floor_disp = {}

        for floor_idx in range(self.n_floors):
            base_node = (floor_idx + 1) * self.columns_per_floor

            disp_x = []
            disp_y = []
            disp_z = []

            for col_idx in range(self.columns_per_floor):
                node_id = base_node + col_idx
                dofs = self.node_dof_map[node_id]
                disp_x.append(u[dofs[0], :])
                disp_y.append(u[dofs[1], :])
                disp_z.append(u[dofs[2], :])

            floor_disp[floor_idx + 1] = {
                'x': np.mean(np.array(disp_x), axis=0),
                'y': np.mean(np.array(disp_y), axis=0),
                'z': np.mean(np.array(disp_z), axis=0),
                'max_x': np.max(np.array(disp_x), axis=0),
                'max_y': np.max(np.array(disp_y), axis=0),
                'max_z': np.max(np.array(disp_z), axis=0)
            }

        return floor_disp

    def _extract_floor_accelerations(self, a: np.ndarray) -> Dict[int, Dict[str, np.ndarray]]:
        """提取各层加速度"""
        floor_acc = {}

        for floor_idx in range(self.n_floors):
            base_node = (floor_idx + 1) * self.columns_per_floor

            acc_x = []
            acc_y = []

            for col_idx in range(self.columns_per_floor):
                node_id = base_node + col_idx
                dofs = self.node_dof_map[node_id]
                acc_x.append(a[dofs[0], :])
                acc_y.append(a[dofs[1], :])

            floor_acc[floor_idx + 1] = {
                'x': np.mean(np.array(acc_x), axis=0),
                'y': np.mean(np.array(acc_y), axis=0),
                'max_x': np.max(np.array(acc_x), axis=0),
                'max_y': np.max(np.array(acc_y), axis=0)
            }

        return floor_acc

    def _compute_element_stresses(self, u: np.ndarray) -> List[Dict]:
        """计算单元应力"""
        element_stresses = []

        for elem_idx, element in enumerate(self.elements):
            node_i = self.nodes.index(element.node_i)
            node_j = self.nodes.index(element.node_j)

            dofs = []
            for node in [node_i, node_j]:
                dofs.extend(self.node_dof_map[node].tolist())

            u_e = u[dofs, :]

            u_local = element.transformation_matrix @ u_e

            n_steps = u.shape[1]
            max_stress = 0

            for step in range(n_steps):
                du_local = u_local[:, step]

                strain = np.zeros(6)
                strain[0] = (du_local[6] - du_local[0]) / element.length

                stress = self.constitutive.compute_stress(strain)
                max_stress = max(max_stress, np.max(np.abs(stress)))

            element_stresses.append({
                'element_id': elem_idx,
                'max_stress': max_stress / 1e6,
                'node_i': node_i,
                'node_j': node_j,
                'floor': int(node_i / self.columns_per_floor)
            })

        return element_stresses
