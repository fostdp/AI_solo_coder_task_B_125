import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useStore } from '@/store/useStore'
import { wsService } from '@/services/websocket'
import Login from '@/pages/Login'
import MainLayout from '@/layouts/MainLayout'
import Dashboard from '@/pages/Dashboard'
import RealtimeMonitor from '@/pages/RealtimeMonitor'
import Simulation from '@/pages/Simulation'
import DamageDetection from '@/pages/DamageDetection'
import AlertCenter from '@/pages/AlertCenter'
import DataAnalysis from '@/pages/DataAnalysis'
import SystemSettings from '@/pages/SystemSettings'

function App() {
  const isAuthenticated = useStore(state => state.isAuthenticated)

  useEffect(() => {
    if (isAuthenticated) {
      wsService.connect('monitoring')
      wsService.connect('alerts')
      wsService.connect('simulation')
      wsService.connect('damage')
    }
    
    return () => {
      wsService.disconnectAll()
    }
  }, [isAuthenticated])

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={
        isAuthenticated ? <MainLayout /> : <Navigate to="/login" replace />
      }>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="realtime" element={<RealtimeMonitor />} />
        <Route path="simulation" element={<Simulation />} />
        <Route path="damage" element={<DamageDetection />} />
        <Route path="alerts" element={<AlertCenter />} />
        <Route path="analysis" element={<DataAnalysis />} />
        <Route path="settings" element={<SystemSettings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
