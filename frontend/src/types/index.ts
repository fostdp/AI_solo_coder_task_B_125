export interface SensorData {
  time: string
  sensor_id: string
  value: number
  unit?: string
}

export interface SensorInfo {
  id: string
  device_id: string
  floor_number: number
  sensor_type: string
  x_position?: number
  y_position?: number
  z_position?: number
  status: string
  dtu_id?: string
}

export interface FloorInfo {
  floor_number: number
  height: number
  diameter: number
  beam_count: number
  column_count: number
  description?: string
}

export interface Alert {
  id: string
  alert_type: string
  floor_number?: number
  threshold_value: number
  actual_value: number
  severity: 'warning' | 'critical'
  status: 'pending' | 'acknowledged' | 'resolved'
  created_at: string
  note?: string
}

export interface SimulationResult {
  id: string
  simulation_id: string
  floor_number?: number
  max_displacement?: number
  max_stress?: number
  max_acceleration?: number
  natural_frequencies?: number[]
  time_history_data?: Record<string, any>
  created_at: string
}

export interface DamageResult {
  id: string
  analysis_id: string
  floor_number: number
  element_id: number
  damage_index: number
  natural_frequency?: number
  frequency_change?: number
  confidence: number
  created_at: string
}

export interface ModalParameter {
  id: string
  floor_number: number
  mode_order: number
  natural_frequency: number
  damping_ratio?: number
  is_baseline: boolean
  measured_at: string
  description?: string
}

export interface HealthAssessment {
  health_status: 'unknown' | 'good' | 'attention' | 'warning' | 'critical'
  overall_health_index: number
  max_damage_index?: number
  avg_damage_index?: number
  damaged_floors: number[]
  last_analysis_time?: string
  total_damage_locations: number
  critical_locations: Array<{
    floor: number
    element_id: number
    damage_index: number
    confidence: number
  }>
}

export interface RealtimeData {
  floor: number
  realtime_data: Record<string, {
    value: number
    unit: string
    timestamp: string
    sensor_id: string
    device_id: string
  }>
  sensor_count: number
}

export interface WebSocketMessage {
  type: string
  [key: string]: any
}
