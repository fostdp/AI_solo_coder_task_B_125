import { create } from 'zustand'
import type {
  Alert,
  RealtimeData,
  SensorInfo,
  FloorInfo,
  HealthAssessment,
  WebSocketMessage
} from '@/types'

interface AppState {
  user: any | null
  isAuthenticated: boolean
  alerts: Alert[]
  unreadAlertCount: number
  realtimeDataByFloor: Record<number, RealtimeData>
  sensors: SensorInfo[]
  floors: FloorInfo[]
  healthAssessment: HealthAssessment | null
  simulationProgress: Record<string, any>
  damageProgress: Record<string, any>
  wsConnectionStatus: 'connecting' | 'connected' | 'disconnected'

  login: (user: any) => void
  logout: () => void
  addAlert: (alert: Alert) => void
  updateAlert: (alert: Alert) => void
  setAlerts: (alerts: Alert[]) => void
  clearAlerts: () => void
  updateRealtimeData: (floor: number, data: RealtimeData) => void
  setSensors: (sensors: SensorInfo[]) => void
  setFloors: (floors: FloorInfo[]) => void
  setHealthAssessment: (assessment: HealthAssessment) => void
  updateSimulationProgress: (simulationId: string, progress: any) => void
  updateDamageProgress: (analysisId: string, progress: any) => void
  setWsConnectionStatus: (status: 'connecting' | 'connected' | 'disconnected') => void
  handleWebSocketMessage: (message: WebSocketMessage) => void
}

export const useStore = create<AppState>((set, get) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  alerts: [],
  unreadAlertCount: 0,
  realtimeDataByFloor: {},
  sensors: [],
  floors: [],
  healthAssessment: null,
  simulationProgress: {},
  damageProgress: {},
  wsConnectionStatus: 'disconnected',

  login: (user: any) => set({ user, isAuthenticated: true }),
  logout: () => {
    localStorage.removeItem('access_token')
    set({ user: null, isAuthenticated: false })
  },

  addAlert: (alert: Alert) => set((state) => ({
    alerts: [alert, ...state.alerts],
    unreadAlertCount: state.unreadAlertCount + 1
  })),

  updateAlert: (alert: Alert) => set((state) => ({
    alerts: state.alerts.map(a => a.id === alert.id ? alert : a)
  })),

  setAlerts: (alerts: Alert[]) => set({
    alerts,
    unreadAlertCount: alerts.filter(a => a.status === 'pending').length
  }),

  clearAlerts: () => set({ alerts: [], unreadAlertCount: 0 }),

  updateRealtimeData: (floor: number, data: RealtimeData) => set((state) => ({
    realtimeDataByFloor: {
      ...state.realtimeDataByFloor,
      [floor]: data
    }
  })),

  setSensors: (sensors: SensorInfo[]) => set({ sensors }),
  setFloors: (floors: FloorInfo[]) => set({ floors }),

  setHealthAssessment: (assessment: HealthAssessment) => set({ healthAssessment: assessment }),

  updateSimulationProgress: (simulationId: string, progress: any) => set((state) => ({
    simulationProgress: {
      ...state.simulationProgress,
      [simulationId]: progress
    }
  })),

  updateDamageProgress: (analysisId: string, progress: any) => set((state) => ({
    damageProgress: {
      ...state.damageProgress,
      [analysisId]: progress
    }
  })),

  setWsConnectionStatus: (status) => set({ wsConnectionStatus: status }),

  handleWebSocketMessage: (message: WebSocketMessage) => {
    const { type } = message

    if (type === 'sensor_data') {
      const floor = message.floor
      const existingData = get().realtimeDataByFloor[floor]
      if (existingData) {
        const updatedData = {
          ...existingData,
          realtime_data: {
            ...existingData.realtime_data,
            [message.sensor_type]: {
              value: message.value,
              unit: message.unit,
              timestamp: message.timestamp,
              sensor_id: message.sensor_id,
              device_id: message.device_id
            }
          }
        }
        get().updateRealtimeData(floor, updatedData)
      }
    } else if (type === 'alert') {
      const alert: Alert = {
        id: message.id,
        alert_type: message.alert_type,
        floor_number: message.floor,
        threshold_value: message.threshold_value,
        actual_value: message.actual_value,
        severity: message.severity,
        status: 'pending',
        created_at: message.timestamp
      }
      get().addAlert(alert)
    } else if (type === 'simulation_update' || type === 'simulation_complete' || type === 'simulation_error') {
      get().updateSimulationProgress(message.simulation_id, message)
    } else if (type === 'damage_update' || type === 'damage_complete' || type === 'damage_error') {
      get().updateDamageProgress(message.analysis_id, message)
    }
  }
}))
