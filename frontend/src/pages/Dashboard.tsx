import { useState, useEffect } from 'react'
import { Row, Col, Card, Statistic, Progress, Tag, List } from 'antd'
import {
  ThunderboltOutlined,
  AlertOutlined,
  RiseOutlined,
  DashboardOutlined,
  WarningOutlined,
  CheckCircleOutlined
} from '@ant-design/icons'
import { useStore } from '@/store/useStore'
import { damageAPI, alertAPI, sensorAPI } from '@/services/api'
import PagodaModel from '@/components/PagodaModel'
import type { DamageResult, Alert, HealthAssessment } from '@/types'
import './Dashboard.scss'

export default function Dashboard() {
  const [healthAssessment, setHealthAssessment] = useState<HealthAssessment | null>(null)
  const [damageResults, setDamageResults] = useState<DamageResult[]>([])
  const [recentAlerts, setRecentAlerts] = useState<Alert[]>([])
  const [sensorStats, setSensorStats] = useState<any>(null)
  const [alertStats, setAlertStats] = useState<any>(null)
  const { realtimeDataByFloor } = useStore()

  useEffect(() => {
    loadDashboardData()
    const interval = setInterval(loadDashboardData, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadDashboardData = async () => {
    try {
      const [healthRes, alertsRes, statsRes, alertStatsRes] = await Promise.all([
        damageAPI.getHealthAssessment(),
        alertAPI.getAlerts({ status: 'pending', limit: 5 }),
        sensorAPI.getStatistics(),
        alertAPI.getStatistics(24)
      ])
      
      setHealthAssessment(healthRes.data)
      setRecentAlerts(alertsRes.data)
      setSensorStats(statsRes.data)
      setAlertStats(alertStatsRes.data)
    } catch (error) {
      console.error('加载仪表盘数据失败:', error)
    }
  }

  useEffect(() => {
    const loadDamageResults = async () => {
      try {
        const res = await damageAPI.getAnalyses({ status: 'completed', limit: 1 })
        if (res.data.length > 0) {
          const resultsRes = await damageAPI.getAnalysisResults(res.data[0].id, 0.1)
          setDamageResults(resultsRes.data)
        }
      } catch (error) {
        console.error('加载损伤结果失败:', error)
      }
    }
    loadDamageResults()
  }, [])

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'good': return '#52c41a'
      case 'attention': return '#faad14'
      case 'warning': return '#fa8c16'
      case 'critical': return '#ff4d4f'
      default: return '#bfbfbf'
    }
  }

  const getHealthText = (status: string) => {
    switch (status) {
      case 'good': return '良好'
      case 'attention': return '注意'
      case 'warning': return '警告'
      case 'critical': return '危险'
      default: return '未知'
    }
  }

  return (
    <div className="dashboard-page">
      <Row gutter={[16, 16]}>
        <Col span={18}>
          <Card className="model-card" bodyStyle={{ padding: 0, height: 500 }}>
            <PagodaModel
              showSensors={true}
              showDamage={true}
              damageResults={damageResults}
              vibrationMode={0}
              vibrationAmplitude={0}
            />
          </Card>
        </Col>
        
        <Col span={6}>
          <Card className="health-card">
            <div className="health-title">
              <CheckCircleOutlined />
              <span>结构健康状态</span>
            </div>
            {healthAssessment && (
              <div className="health-content">
                <div
                  className="health-status"
                  style={{ color: getHealthColor(healthAssessment.health_status) }}
                >
                  {getHealthText(healthAssessment.health_status)}
                </div>
                <Progress
                  type="dashboard"
                  percent={Math.round(healthAssessment.overall_health_index * 100)}
                  strokeColor={getHealthColor(healthAssessment.health_status)}
                  size={120}
                />
                <div className="health-details">
                  <div className="detail-item">
                    <span>最大损伤指数</span>
                    <span className="value">{(healthAssessment.max_damage_index || 0).toFixed(4)}</span>
                  </div>
                  <div className="detail-item">
                    <span>损伤位置</span>
                    <span className="value">{healthAssessment.total_damage_locations}处</span>
                  </div>
                  {healthAssessment.damaged_floors.length > 0 && (
                    <div className="detail-item">
                      <span>涉及楼层</span>
                      <span className="value">
                        {healthAssessment.damaged_floors.map(f => `${f}层`).join(', ')}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </Card>

          <Card className="stats-card" style={{ marginTop: 16 }}>
            <Row gutter={[8, 8]}>
              <Col span={12}>
                <Statistic
                  title="在线传感器"
                  value={sensorStats?.reporting_sensors || 0}
                  suffix={`/${sensorStats?.active_sensors || 40}`}
                  prefix={<DashboardOutlined />}
                  valueStyle={{ fontSize: 20 }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="今日告警"
                  value={alertStats?.total_alerts || 0}
                  prefix={<WarningOutlined />}
                  valueStyle={{ fontSize: 20, color: alertStats?.critical_alerts > 0 ? '#ff4d4f' : undefined }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="待处理告警"
                  value={alertStats?.pending_alerts || 0}
                  prefix={<AlertOutlined />}
                  valueStyle={{ fontSize: 20, color: '#faad14' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="数据总量"
                  value={sensorStats?.total_records || 0}
                  precision={0}
                  prefix={<RiseOutlined />}
                  valueStyle={{ fontSize: 20 }}
                />
              </Col>
            </Row>
          </Card>
        </Col>

        <Col span={8}>
          <Card
            title="实时监测数据"
            className="realtime-card"
            extra={<Tag color="green">实时更新</Tag>}
          >
            <div className="floor-data-list">
              {[1, 2, 3, 4, 5].map(floor => {
                const data = realtimeDataByFloor[floor]
                return (
                  <div key={floor} className="floor-data-item">
                    <div className="floor-label">第 {floor} 层</div>
                    <div className="floor-data">
                      {data ? (
                        <>
                          <span>X位移: {data.realtime_data.displacement_x?.value.toFixed(3) || '--'} mm</span>
                          <span>温度: {data.realtime_data.temperature?.value.toFixed(1) || '--'}°C</span>
                        </>
                      ) : (
                        <span className="no-data">暂无数据</span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </Card>
        </Col>

        <Col span={8}>
          <Card
            title="最近告警"
            className="alerts-card"
            extra={alertStats?.pending_alerts > 0 && (
              <Tag color="red">{alertStats.pending_alerts}条待处理</Tag>
            )}
          >
            <List
              dataSource={recentAlerts}
              renderItem={(alert) => (
                <List.Item className="alert-item">
                  <div className="alert-header">
                    <Tag color={alert.severity === 'critical' ? 'red' : 'orange'}>
                      {alert.severity === 'critical' ? '严重' : '警告'}
                    </Tag>
                    <span className="alert-type">{alert.alert_type}</span>
                    {alert.floor_number && (
                      <span className="alert-floor">第{alert.floor_number}层</span>
                    )}
                  </div>
                  <div className="alert-content">
                    当前值: <b>{alert.actual_value.toFixed(4)}</b>,
                    阈值: {alert.threshold_value}
                  </div>
                  <div className="alert-time">
                    {new Date(alert.created_at).toLocaleString('zh-CN')}
                  </div>
                </List.Item>
              )}
            />
            {recentAlerts.length === 0 && (
              <div className="no-alerts">
                <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 32 }} />
                <p>暂无告警</p>
              </div>
            )}
          </Card>
        </Col>

        <Col span={8}>
          <Card
            title="告警分布(24小时)"
            className="alert-distribution-card"
          >
            {alertStats && (
              <div className="distribution-list">
                <div className="distribution-item">
                  <span className="type">位移告警</span>
                  <Progress percent={(alertStats.alerts_by_type?.['displacement'] || 0) / Math.max(alertStats.total_alerts, 1) * 100} showInfo={false} />
                  <span className="count">{alertStats.alerts_by_type?.['displacement'] || 0}</span>
                </div>
                <div className="distribution-item">
                  <span className="type">加速度告警</span>
                  <Progress percent={(alertStats.alerts_by_type?.['acceleration'] || 0) / Math.max(alertStats.total_alerts, 1) * 100} showInfo={false} />
                  <span className="count">{alertStats.alerts_by_type?.['acceleration'] || 0}</span>
                </div>
                <div className="distribution-item">
                  <span className="type">温度告警</span>
                  <Progress percent={(alertStats.alerts_by_type?.['temperature'] || 0) / Math.max(alertStats.total_alerts, 1) * 100} showInfo={false} />
                  <span className="count">{alertStats.alerts_by_type?.['temperature'] || 0}</span>
                </div>
                <div className="distribution-item">
                  <span className="type">含水率告警</span>
                  <Progress percent={(alertStats.alerts_by_type?.['moisture'] || 0) / Math.max(alertStats.total_alerts, 1) * 100} showInfo={false} />
                  <span className="count">{alertStats.alerts_by_type?.['moisture'] || 0}</span>
                </div>
                <div className="distribution-item">
                  <span className="type">层间位移角</span>
                  <Progress percent={(alertStats.alerts_by_type?.['story_drift'] || 0) / Math.max(alertStats.total_alerts, 1) * 100} showInfo={false} />
                  <span className="count">{alertStats.alerts_by_type?.['story_drift'] || 0}</span>
                </div>
                <div className="distribution-item">
                  <span className="type">频率异常</span>
                  <Progress percent={(alertStats.alerts_by_type?.['frequency'] || 0) / Math.max(alertStats.total_alerts, 1) * 100} showInfo={false} />
                  <span className="count">{alertStats.alerts_by_type?.['frequency'] || 0}</span>
                </div>
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
