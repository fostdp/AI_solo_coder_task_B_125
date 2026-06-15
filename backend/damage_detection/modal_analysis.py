import numpy as np
from scipy import linalg
from scipy.signal import welch, find_peaks
from typing import Dict, List, Tuple, Optional
import warnings


class SSIModalAnalysis:
    """
    随机子空间识别法 (Stochastic Subspace Identification)
    用于从环境振动响应中识别模态参数
    """

    def __init__(self, fs: float = 100.0, order_max: int = 50):
        """
        初始化SSI分析器

        Args:
            fs: 采样频率 (Hz)
            order_max: 最大系统阶数
        """
        self.fs = fs
        self.dt = 1.0 / fs
        self.order_max = order_max

    def analyze(self, data: np.ndarray, n_modes: int = 10) -> Dict:
        """
        执行SSI模态分析

        Args:
            data: 加速度响应数据 [n_channels, n_samples]
            n_modes: 识别的模态数量

        Returns:
            modal_params: 模态参数字典
        """
        data = self._preprocess_data(data)

        Hankel = self._build_hankel_matrix(data)

        U, S, Vh = linalg.svd(Hankel, full_matrices=False)

        frequencies_all = []
        damping_all = []
        mode_shapes_all = []
        orders = []

        for order in range(2, self.order_max + 1, 2):
            try:
                A, C = self._identify_system(U, S, Vh, order)
                freq, damp, phi = self._extract_modal_params(A, C)

                valid_idx = (freq > 0.1) & (freq < 20.0) & (damp > 0) & (damp < 0.2)

                frequencies_all.extend(freq[valid_idx])
                damping_all.extend(damp[valid_idx])
                mode_shapes_all.extend([phi[:, i] for i in range(len(freq)) if valid_idx[i]])
                orders.extend([order] * np.sum(valid_idx))
            except Exception as e:
                warnings.warn(f"阶数 {order} 识别失败: {e}")
                continue

        frequencies_all = np.array(frequencies_all)
        damping_all = np.array(damping_all)
        mode_shapes_all = np.array(mode_shapes_all).T if mode_shapes_all else np.array([])

        if len(frequencies_all) == 0:
            return self._empty_result()

        modal_params = self._cluster_modes(
            frequencies_all,
            damping_all,
            mode_shapes_all,
            n_modes
        )

        return modal_params

    def _preprocess_data(self, data: np.ndarray) -> np.ndarray:
        """数据预处理"""
        if data.ndim == 1:
            data = data.reshape(1, -1)

        data = data - np.mean(data, axis=1, keepdims=True)

        for i in range(data.shape[0]):
            data[i, :] = data[i, :] * np.hanning(data.shape[1])

        return data

    def _build_hankel_matrix(self, data: np.ndarray) -> np.ndarray:
        """构建Hankel矩阵"""
        n_channels, n_samples = data.shape
        i_block = min(n_samples // 4, 200)

        H = np.zeros((2 * n_channels * i_block, n_samples - 2 * i_block + 1))

        for row in range(2 * i_block):
            for col in range(n_samples - 2 * i_block + 1):
                for ch in range(n_channels):
                    H[row * n_channels + ch, col] = data[ch, row + col]

        return H

    def _identify_system(self, U: np.ndarray, S: np.ndarray, Vh: np.ndarray,
                         order: int) -> Tuple[np.ndarray, np.ndarray]:
        """识别系统矩阵A和C"""
        U1 = U[:, :order]
        S1 = np.diag(np.sqrt(S[:order]))
        V1 = Vh[:order, :]

        O = U1 @ S1
        X = S1 @ V1

        X_p = X[:, :-1]
        X_f = X[:, 1:]

        O_p = O[:-U.shape[0] // 2, :]
        O_f = O[U.shape[0] // 2:, :]

        A = np.linalg.lstsq(X_p.T, X_f.T, rcond=None)[0].T
        C = O_p[:O_f.shape[1] // 2, :] if O_p.shape[0] >= 2 else O_p[:1, :]

        return A, C

    def _extract_modal_params(self, A: np.ndarray, C: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """从系统矩阵提取模态参数"""
        eigenvalues, eigenvectors = linalg.eig(A)

        idx = np.argsort(-np.abs(eigenvalues))
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        lambda_dt = np.log(eigenvalues)
        lambda_c = lambda_dt * self.fs

        omega = np.abs(lambda_c)
        freq = omega / (2 * np.pi)
        damping = -np.real(lambda_c) / omega
        phi = np.real(C @ eigenvectors)

        for i in range(phi.shape[1]):
            max_idx = np.argmax(np.abs(phi[:, i]))
            if phi[max_idx, i] < 0:
                phi[:, i] = -phi[:, i]
            phi[:, i] = phi[:, i] / np.max(np.abs(phi[:, i]))

        return freq, damping, phi

    def _cluster_modes(self, frequencies: np.ndarray, damping: np.ndarray,
                        mode_shapes: np.ndarray, n_modes: int) -> Dict:
        """聚类识别稳定的模态"""
        if len(frequencies) == 0:
            return self._empty_result()

        freq_bins = np.linspace(0.1, 20.0, 200)
        clusters = []

        for bin_idx in range(len(freq_bins) - 1):
            mask = (frequencies >= freq_bins[bin_idx]) & (frequencies < freq_bins[bin_idx + 1])
            if np.sum(mask) > 0:
                clusters.append({
                    'freq_mean': np.mean(frequencies[mask]),
                    'freq_std': np.std(frequencies[mask]),
                    'damping_mean': np.mean(damping[mask]),
                    'damping_std': np.std(damping[mask]),
                    'count': np.sum(mask),
                    'mode_shape': np.mean(mode_shapes[:, mask], axis=1) if mode_shapes.size > 0 else None
                })

        clusters.sort(key=lambda x: x['count'], reverse=True)
        clusters = [c for c in clusters if c['count'] >= 3]

        unique_freqs = []
        for c in clusters:
            if all(abs(c['freq_mean'] - f) > 0.05 for f in unique_freqs):
                unique_freqs.append(c['freq_mean'])
                if len(unique_freqs) >= n_modes:
                    break

        final_modes = []
        for uf in unique_freqs:
            cluster = next(c for c in clusters if abs(c['freq_mean'] - uf) < 1e-6)
            final_modes.append(cluster)

        final_modes.sort(key=lambda x: x['freq_mean'])

        return {
            'frequencies': [m['freq_mean'] for m in final_modes],
            'frequency_std': [m['freq_std'] for m in final_modes],
            'damping_ratios': [m['damping_mean'] for m in final_modes],
            'damping_std': [m['damping_std'] for m in final_modes],
            'mode_shapes': [m['mode_shape'].tolist() if m['mode_shape'] is not None else []
                           for m in final_modes],
            'stability': [m['count'] for m in final_modes],
            'n_modes_identified': len(final_modes)
        }

    def _empty_result(self) -> Dict:
        """返回空结果"""
        return {
            'frequencies': [],
            'frequency_std': [],
            'damping_ratios': [],
            'damping_std': [],
            'mode_shapes': [],
            'stability': [],
            'n_modes_identified': 0
        }


class FrequencyDomainDecomposition:
    """
    频域分解法 (Frequency Domain Decomposition)
    快速模态识别方法
    """

    def __init__(self, fs: float = 100.0):
        """
        初始化FDD分析器

        Args:
            fs: 采样频率 (Hz)
        """
        self.fs = fs

    def analyze(self, data: np.ndarray, n_modes: int = 10) -> Dict:
        """
        执行FDD模态分析

        Args:
            data: 加速度响应数据 [n_channels, n_samples]
            n_modes: 识别的模态数量

        Returns:
            modal_params: 模态参数字典
        """
        if data.ndim == 1:
            data = data.reshape(1, -1)

        data = data - np.mean(data, axis=1, keepdims=True)
        n_channels = data.shape[0]

        f, Pxx = welch(
            data[0, :],
            fs=self.fs,
            nperseg=min(2048, data.shape[1] // 4),
            noverlap=None
        )

        Gyy = np.zeros((len(f), n_channels, n_channels), dtype=complex)
        for i in range(n_channels):
            for j in range(i, n_channels):
                _, Pij = welch(
                    data[i, :],
                    data[j, :],
                    fs=self.fs,
                    nperseg=min(2048, data.shape[1] // 4)
                )
                Gyy[:, i, j] = Pij
                Gyy[:, j, i] = np.conj(Pij)

        singular_values = np.zeros((len(f), n_channels))
        mode_shapes_svd = np.zeros((len(f), n_channels, n_channels), dtype=complex)

        for k in range(len(f)):
            U, S, Vh = linalg.svd(Gyy[k, :, :])
            singular_values[k, :] = S
            mode_shapes_svd[k, :, :] = U

        frequencies = []
        mode_shapes = []

        for ch in range(min(n_channels, 3)):
            sv = singular_values[:, ch]
            peaks, _ = find_peaks(sv, height=np.max(sv) * 0.1, distance=10)

            for peak in peaks:
                freq_hz = f[peak]
                if freq_hz > 0.1 and freq_hz < 20.0:
                    if all(abs(freq_hz - fq) > 0.05 for fq in frequencies):
                        frequencies.append(freq_hz)
                        phi = np.real(mode_shapes_svd[peak, :, ch])
                        phi = phi / np.max(np.abs(phi))
                        if phi[np.argmax(np.abs(phi))] < 0:
                            phi = -phi
                        mode_shapes.append(phi.tolist())

        sorted_idx = np.argsort(frequencies)
        frequencies = np.array(frequencies)[sorted_idx]
        mode_shapes = [mode_shapes[i] for i in sorted_idx]

        damping_ratios = self._estimate_damping(data, frequencies[:n_modes])

        return {
            'frequencies': frequencies[:n_modes].tolist(),
            'damping_ratios': damping_ratios[:n_modes],
            'mode_shapes': mode_shapes[:n_modes],
            'singular_values': singular_values[:, 0].tolist(),
            'frequency_axis': f.tolist(),
            'n_modes_identified': min(len(frequencies), n_modes)
        }

    def _estimate_damping(self, data: np.ndarray, frequencies: List[float]) -> List[float]:
        """使用半功率带宽法估计阻尼比"""
        damping = []
        n_channels = data.shape[0]

        for freq in frequencies:
            try:
                _, Pxx = welch(
                    data[0, :],
                    fs=self.fs,
                    nperseg=min(4096, data.shape[1] // 2),
                    noverlap=min(2048, data.shape[1] // 4)
                )

                peak_idx = np.argmin(np.abs(_ - freq))
                if peak_idx > 0 and peak_idx < len(_) - 1:
                    peak_val = Pxx[peak_idx]
                    half_power = peak_val / np.sqrt(2)

                    left_idx = peak_idx
                    while left_idx > 0 and Pxx[left_idx] > half_power:
                        left_idx -= 1

                    right_idx = peak_idx
                    while right_idx < len(_) - 1 and Pxx[right_idx] > half_power:
                        right_idx += 1

                    if right_idx > left_idx:
                        bandwidth = _[right_idx] - _[left_idx]
                        xi = bandwidth / (2 * freq)
                        damping.append(min(max(xi, 0.005), 0.1))
                    else:
                        damping.append(0.02)
                else:
                    damping.append(0.02)
            except:
                damping.append(0.02)

        return damping
