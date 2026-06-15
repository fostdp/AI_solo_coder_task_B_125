import numpy as np
from typing import Dict, Tuple, Optional


class WindLoadGenerator:
    """
    风荷载生成器
    基于风速谱生成脉动风荷载
    """

    def __init__(self, wind_speed: float = 10.0, terrain_roughness: float = 0.12):
        """
        初始化风荷载生成器

        Args:
            wind_speed: 10m高度处的基本风速 (m/s)
            terrain_roughness: 地面粗糙度指数
                0.12: 城市郊区
                0.16: 城市中心
                0.22: 大城市中心
        """
        self.V_ref = wind_speed
        self.alpha = terrain_roughness
        self.rho_air = 1.225  # 空气密度 kg/m³

    def generate_wind_speed_time_history(self, height: float,
                                         duration: float = 10.0,
                                         dt: float = 0.01,
                                         seed: Optional[int] = None) -> np.ndarray:
        """
        生成某高度处的风速时程

        Args:
            height: 高度 (m)
            duration: 持时 (s)
            dt: 时间步长 (s)
            seed: 随机种子

        Returns:
            wind_speed: 风速时程 (m/s)
        """
        if seed is not None:
            np.random.seed(seed)

        N = int(duration / dt)
        t = np.linspace(0, duration, N, endpoint=False)

        V_mean = self.V_ref * (height / 10.0) ** self.alpha

        v_fluctuation = self._generate_fluctuating_wind(height, N, dt)

        wind_speed = V_mean + v_fluctuation
        wind_speed = np.maximum(wind_speed, 0)

        return wind_speed, t

    def _generate_fluctuating_wind(self, height: float, N: int, dt: float) -> np.ndarray:
        """
        基于Davenport谱生成脉动风速

        Args:
            height: 高度 (m)
            N: 时间步数
            dt: 时间步长

        Returns:
            v_fluctuation: 脉动风速时程
        """
        f = np.fft.fftfreq(N, d=dt)
        f_pos = f[f >= 0]

        S_v = self._davenport_spectrum(f_pos, height)

        phase = np.random.uniform(0, 2 * np.pi, len(f_pos))

        amplitude = np.sqrt(2 * S_v / dt)
        v_fft_pos = amplitude * np.exp(1j * phase)

        if N % 2 == 0:
            v_fft = np.concatenate([v_fft_pos, np.conj(v_fft_pos[-2:0:-1])])
        else:
            v_fft = np.concatenate([v_fft_pos, np.conj(v_fft_pos[-1:0:-1])])

        v_fluctuation = np.real(np.fft.ifft(v_fft)) * N

        return v_fluctuation

    def _davenport_spectrum(self, f: np.ndarray, height: float) -> np.ndarray:
        """
        Davenport风速谱

        S_v(f) = 4k V_10^2 x^2 / [f(1 + x^2)^(4/3)]
        x = 1200 f / V_10
        """
        k = 0.001  # 地面粗糙度系数
        V_10 = self.V_ref
        x = 1200 * f / V_10

        denominator = f * (1 + x ** 2) ** (4.0 / 3.0)
        denominator = np.where(denominator == 0, 1e-10, denominator)

        S_v = 4 * k * V_10 ** 2 * x ** 2 / denominator
        S_v[f == 0] = 0

        return S_v

    def compute_wind_force(self, wind_speed: np.ndarray,
                           drag_coefficient: float = 1.3,
                           projected_area: float = 1.0) -> np.ndarray:
        """
        计算风力时程

        F = 0.5 * rho * Cd * A * V^2

        Args:
            wind_speed: 风速时程 (m/s)
            drag_coefficient: 阻力系数
            projected_area: 迎风面积 (m²)

        Returns:
            wind_force: 风力时程 (N)
        """
        return 0.5 * self.rho_air * drag_coefficient * projected_area * wind_speed ** 2

    def generate_distributed_wind_loads(self, heights: np.ndarray,
                                        duration: float = 10.0,
                                        dt: float = 0.01,
                                        drag_coefficient: float = 1.3,
                                        projected_areas: Optional[np.ndarray] = None) -> Tuple[Dict[int, np.ndarray], np.ndarray]:
        """
        生成多个高度处的分布风荷载

        Args:
            heights: 各层高度数组
            duration: 持时
            dt: 时间步长
            drag_coefficient: 阻力系数
            projected_areas: 各层迎风面积

        Returns:
            loads: 各层荷载时程字典
            t: 时间向量
        """
        N = int(duration / dt)
        t = np.linspace(0, duration, N, endpoint=False)

        if projected_areas is None:
            projected_areas = np.ones_like(heights) * 10.0

        loads = {}
        for i, height in enumerate(heights):
            wind_speed, _ = self.generate_wind_speed_time_history(height, duration, dt, seed=i)
            force = self.compute_wind_force(wind_speed, drag_coefficient, projected_areas[i])
            loads[i] = force

        return loads, t


class EarthquakeLoadGenerator:
    """
    地震荷载生成器
    基于设计反应谱生成人工地震波
    """

    def __init__(self, magnitude: float = 7.0, peak_acceleration: float = 0.1):
        """
        初始化地震荷载生成器

        Args:
            magnitude: 震级
            peak_acceleration: 峰值加速度 (g)
        """
        self.M = magnitude
        self.PGA = peak_acceleration * 9.81  # m/s²

    def generate_artificial_ground_motion(self, duration: float = 20.0,
                                           dt: float = 0.01,
                                           seed: Optional[int] = None,
                                           direction: str = 'x') -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        生成人工地震动 (基于三角函数叠加法)

        Args:
            duration: 持时 (s)
            dt: 时间步长 (s)
            seed: 随机种子
            direction: 'x' 或 'y'

        Returns:
            t: 时间向量
            a_g: 加速度时程 (m/s²)
            v_g: 速度时程 (m/s)
            d_g: 位移时程 (m)
        """
        if seed is not None:
            np.random.seed(seed)

        N = int(duration / dt)
        t = np.linspace(0, duration, N, endpoint=False)

        f_min = 0.1
        f_max = 25.0
        df = 1.0 / duration
        freqs = np.arange(f_min, f_max, df)

        S_a = self._design_response_spectrum(freqs)

        phase = np.random.uniform(0, 2 * np.pi, len(freqs))

        a_g = np.zeros(N)
        for i, f in enumerate(freqs):
            omega = 2 * np.pi * f
            amplitude = np.sqrt(S_a[i] * df * 2)
            a_g += amplitude * np.sin(omega * t + phase[i])

        a_g = a_g * (self.PGA / np.max(np.abs(a_g)))

        envelope = self._envelope_function(t, duration)
        a_g = a_g * envelope

        v_g = np.cumsum(a_g) * dt
        d_g = np.cumsum(v_g) * dt

        v_g = v_g - np.mean(v_g)
        d_g = d_g - np.mean(d_g)

        return t, a_g, v_g, d_g

    def _design_response_spectrum(self, freqs: np.ndarray) -> np.ndarray:
        """
        中国建筑抗震设计规范(GB50011)设计反应谱

        Args:
            freqs: 频率数组 (Hz)

        Returns:
            S_a: 加速度反应谱 (m/s²)
        """
        periods = 1.0 / freqs

        alpha_max = self.PGA / 9.81
        T_g = 0.45  # 特征周期

        S_a = np.zeros_like(periods)

        mask1 = periods <= 0.1
        S_a[mask1] = alpha_max * (0.45 + 5.5 * periods[mask1]) * 9.81

        mask2 = (periods > 0.1) & (periods <= T_g)
        S_a[mask2] = alpha_max * 9.81

        mask3 = (periods > T_g) & (periods <= 5 * T_g)
        S_a[mask3] = alpha_max * (T_g / periods[mask3]) ** 0.9 * 9.81

        mask4 = periods > 5 * T_g
        S_a[mask4] = alpha_max * (0.2 ** 0.9 - 0.02 * (periods[mask4] - 5 * T_g)) * 9.81

        return S_a

    def _envelope_function(self, t: np.ndarray, duration: float) -> np.ndarray:
        """
        地震动包络函数 (三段式)

        Args:
            t: 时间向量
            duration: 总持时

        Returns:
            envelope: 包络函数值
        """
        t1 = 0.15 * duration
        t2 = 0.65 * duration

        envelope = np.zeros_like(t)

        rising = t <= t1
        envelope[rising] = (t[rising] / t1) ** 2

        strong = (t > t1) & (t <= t2)
        envelope[strong] = 1.0

        decaying = t > t2
        envelope[decaying] = np.exp(-0.15 * (t[decaying] - t2))

        return envelope

    def generate_elcentro_wave(self, duration: float = 30.0,
                                dt: float = 0.02) -> Tuple[np.ndarray, np.ndarray]:
        """
        生成El Centro地震波 (简化版)

        Args:
            duration: 持时
            dt: 时间步长

        Returns:
            t: 时间向量
            a_g: 加速度时程
        """
        N = int(duration / dt)
        t = np.linspace(0, duration, N, endpoint=False)

        main_freq = np.array([1.25, 2.4, 3.8, 5.2, 7.5])
        amplitudes = np.array([0.35, 0.25, 0.18, 0.12, 0.10])
        phases = np.random.uniform(0, 2 * np.pi, len(main_freq))

        a_g = np.zeros(N)
        for f, A, phi in zip(main_freq, amplitudes, phases):
            omega = 2 * np.pi * f
            a_g += A * 9.81 * np.sin(omega * t + phi)

        envelope = self._envelope_function(t, duration)
        a_g = a_g * envelope

        return t, a_g

    def compute_inertia_forces(self, mass: np.ndarray,
                                ground_acceleration: np.ndarray) -> np.ndarray:
        """
        计算各层惯性力

        F_i = -m_i * a_g(t)

        Args:
            mass: 各层质量数组 (kg)
            ground_acceleration: 地面加速度时程 (m/s²)

        Returns:
            inertia_forces: 各层惯性力时程 [n_floors, n_timesteps]
        """
        return -np.outer(mass, ground_acceleration)
