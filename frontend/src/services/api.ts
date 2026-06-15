import axios from 'axios'
import type {
  SensorData,
  SensorInfo,
  FloorInfo,
  Alert,
  SimulationResult,
  DamageResult,
  ModalParameter,
  HealthAssessment,
  RealtimeData
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const authAPI = {
  login: (username: string, password: string) => {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    return api.post('/auth/login', formData)
  },
  logout: () => api.post('/auth/logout'),
  getCurrentUser: () => api.get('/auth/me'),
  changePassword: (oldPassword: string, newPassword: string) =>
    api.post('/auth/change-password', null, {
      params: { old_password: oldPassword, new_password: newPassword }
    })
}

export const sensorAPI = {
  getData: (params: {
    floor?: number
    sensor_type?: string
    sensor_id?: string
    start_time: string
    end_time: string
    aggregation?: string
  }) => api.get<SensorData[]>('/sensors/data', { params }),

  getSensors: (params?: { floor?: number; sensor_type?: string; status?: string }) =>
    api.get<SensorInfo[]>('/sensors', { params }),

  getFloors: () => api.get<FloorInfo[]>('/sensors/floors'),

  getRealtimeData: (floor: number) => api.get<RealtimeData>(`/sensors/realtime/${floor}`),

  getStatistics: () => api.get('/sensors/statistics'),

  getDtuDevices: () => api.get('/sensors/dtu-devices')
}

export const alertAPI = {
  getAlerts: (params?: {
    status?: string
    severity?: string
    floor?: number
    alert_type?: string
    start_time?: string
    end_time?: string
    limit?: number
    offset?: number
  }) => api.get<Alert[]>('/alerts', { params }),

  getAlert: (id: string) => api.get<Alert>(`/alerts/${id}`),

  acknowledgeAlert: (id: string, note?: string) =>
    api.put(`/alerts/${id}/acknowledge`, null, { params: { note } }),

  resolveAlert: (id: string, note?: string) =>
    api.put(`/alerts/${id}/resolve`, null, { params: { note } }),

  getStatistics: (hours?: number) =>
    api.get('/alerts/statistics', { params: { hours } }),

  getThresholds: () => api.get('/alerts/thresholds'),

  setThreshold: (config: {
    parameter_name: string
    warning_threshold: number
    critical_threshold: number
    unit?: string
    description?: string
  }) => api.post('/alerts/thresholds', config)
}

export const simulationAPI = {
  runSimulation: (config: {
    simulation_type: string
    timber_properties: {
      E_L: number
      E_R: number
      E_T: number
      G_LR: number
      G_LT: number
      G_RT: number
      v_LR: number
      v_LT: number
      v_RT: number
      density: number
    }
    load_params: {
      wind_speed?: number
      earthquake_level?: number
      duration: number
      time_step: number
    }
    damping_ratio: number
  }) => api.post('/simulation/run', config),

  getSimulations: (params?: {
    status?: string
    simulation_type?: string
    limit?: number
    offset?: number
  }) => api.get('/simulation', { params }),

  getSimulation: (id: string) => api.get(`/simulation/${id}`),

  getSimulationResults: (id: string) =>
    api.get<SimulationResult[]>(`/simulation/${id}/results`),

  getModelInfo: () => api.get('/simulation/model/info'),

  runModalAnalysis: (config: any) =>
    api.post('/simulation/modal-analysis', config)
}

export const damageAPI = {
  analyze: (params: { analysis_window: number; floor?: number }) =>
    api.post('/damage/analyze', params),

  getAnalyses: (params?: { status?: string; limit?: number; offset?: number }) =>
    api.get('/damage', { params }),

  getAnalysis: (id: string) => api.get(`/damage/${id}`),

  getAnalysisResults: (id: string, min_damage_index?: number) =>
    api.get<DamageResult[]>(`/damage/${id}/results`, {
      params: { min_damage_index }
    }),

  getModalParameters: (params?: {
    floor?: number
    is_baseline?: boolean
    start_time?: string
    end_time?: string
    limit?: number
  }) => api.get<ModalParameter[]>('/damage/modal-parameters', { params }),

  setBaselineModalParameters: (params: {
    floor: number
    natural_frequencies: number[]
    mode_shapes?: any[]
  }) => api.post('/damage/modal-parameters/baseline', null, { params }),

  getHealthAssessment: () => api.get<HealthAssessment>('/damage/health/assessment')
}

export default api
