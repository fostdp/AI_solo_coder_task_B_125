import { useState, useEffect } from 'react'
import { Row, Col, Card, Tabs, Select, DatePicker, Button, Space, Switch, Slider, App } from 'antd'
import { PlayCircleOutlined, PauseCircleOutlined, ReloadOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import dayjs from 'dayjs'
import PagodaModel from '@/components/PagodaModel'
import { sensorAPI, damageAPI } from '@/services/api'
import { useStore } from '@/store/useStore'
import type { DamageResult, SensorData } from '@/types'
import './RealtimeMonitor.scss'

const { RangePicker } = DatePicker
const { TabPane } = Tabs

const SENSOR_TYPES = [
  { value: 'displacement_x', label: 'X方向位移 (mm)' },
  { value: 'displacement_y', label: 'Y方向位移 (mm)' },
  { value: 'acceleration_x', label: 'X方向加速度 (m/s²)' },
  { value: 'acceleration_y', label: 'Y方向加速度 (m/s²)' },
  { value: 'temperature', label: '温度 (°C)' },
  { value: 'humidity', label: '湿度 (%)' },
  { value: 'moisture', label: '木材含水率 (%)' },
  { value: 'inclination', label: '倾角 (°)' }
]

const FLOORS = [1, 2, 3, 4, 5]

export default function RealtimeMonitor() {
  const { message } = App.useApp()
  const [selectedFloor, setSelectedFloor] = useState<number>(1)
  const [selectedSensorType, setSelectedSensorType] = useState<string>('displacement_x')
  const [timeRange, setTimeRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().subtract(1, 'hour'),
    dayjs()
  ])
  const [chartData, setChartData] = useState<any>({ timestamps: [], values: [] })
  const [isPlaying, setIsPlaying] = useState(false)
  const [vibrationMode, setVibrationMode] = useState(0)
  const [vibrationAmplitude, setVibrationAmplitude] = useState(0)
  const [showSensors, setShowSensors] = useState(true)
  const [showDamage, setShowDamage] = useState(true)
  const [damageResults, setDamageResults] = useState<DamageResult[]>([])
  const [loading, setLoading] = useState(false)

  const { realtimeDataByFloor, setFloors, setSensors } = useStore()

  useEffect(() => {
    loadInitialData()
  }, [])

  useEffect(() => {
    if (timeRange) {
      loadChartData()
    }
  }, [selectedFloor, selectedSensorType, timeRange])

  useEffect(() => {
    const loadDamageResults = async () => {
      try {
        const res = await damageAPI.getAnalyses({ status: 'completed', limit: 1 })
        if (res.data.length > 0) {
          const resultsRes = await damageAPI.getAnalysisResults(res.data[0].id, 0.05)
          setDamageResults(resultsRes.data)
        }
      } catch (error) {
        console.error('加载损伤结果失败:', error)
      }
    }
    loadDamageResults()
  }, [])

  const loadInitialData = async () => {
    try {
      const [floorsRes, sensorsRes] = await Promise.all([
        sensorAPI.getFloors(),
        sensorAPI.getSensors()
      ])
      setFloors(floorsRes.data)
      setSensors(sensorsRes.data)
    } catch (error) {
      message.error('加载基础数据失败')
    }
  }

  const loadChartData = async () => {
    if (!timeRange) return
    
    setLoading(true)
    try {
      const res = await sensorAPI.getData({
        floor: selectedFloor,
        sensor_type: selectedSensorType,
        start_time: timeRange[0].toISOString(),
        end_time: timeRange[1].toISOString(),
        aggregation: 'raw'
      })
      
      const data: SensorData[] = res.data
      setChartData({
        timestamps: data.map(d => new Date(d.time).toLocaleTimeString('zh-CN')),
        values: data.map(d => d.value)
      })
    } catch (error) {
      message.error('加载历史数据失败')
    } finally {
      setLoading(false)
    }
  }

  const getChartOption = () => ({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const data = params[0]
        return `${data.name}<br/>${SENSOR_TYPES.find(s => s.value === selectedSensorType)?.label.split(' ')[0]}: ${data.value.toFixed(6)}`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: chartData.timestamps
    },
    yAxis: {
      type: 'value',
      name: SENSOR_TYPES.find(s => s.value === selectedSensorType)?.label.split('(')[1]?.replace(')', '')
    },
    series: [{
      name: '测量值',
      type: 'line',
      smooth: true,
      symbol: 'none',
      sampling: 'lttb',
      itemStyle: {
        color: '#1677ff'
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [{
            offset: 0, color: 'rgba(22, 119, 255, 0.3)'
          }, {
            offset: 1, color: 'rgba(22, 119, 255, 0.05)'
          }]
        }
      },
      data: chartData.values
    }]
  })

  const realtimeData = realtimeDataByFloor[selectedFloor]

  return (
    <div className="realtime-monitor-page">
      <Row gutter={[16, 16]}>
        <Col span={16}>
          <Card
            className="model-card"
            bodyStyle={{ padding: 0, height: 500 }}
            title="木塔三维模型"
            extra={
              <Space>
                <span style={{ fontSize: 12, color: '#666' }}>显示传感器</span>
                <Switch
                  checked={showSensors}
                  onChange={setShowSensors}
                  size="small"
                />
                <span style={{ fontSize: 12, color: '#666' }}>显示损伤</span>
                <Switch
                  checked={showDamage}
                  onChange={setShowDamage}
                  size="small"
                />
              </Space>
            }
          >
            <PagodaModel
              showSensors={showSensors}
              showDamage={showDamage}
              vibrationMode={vibrationMode}
              vibrationAmplitude={isPlaying ? vibrationAmplitude : 0}
              damageResults={damageResults}
              selectedFloor={selectedFloor}
              onFloorSelect={setSelectedFloor}
            />
          </Card>

          <Card
            style={{ marginTop: 16 }}
            title="历史数据趋势"
            extra={
              <Button
                icon={<ReloadOutlined />}
                onClick={loadChartData}
                loading={loading}
                size="small"
              >
                刷新
              </Button>
            }
          >
            <Space direction="vertical" style={{ width: '100%' }} size={16}>
              <Space wrap>
                <span style={{ color: '#666' }}>楼层:</span>
                <Select
                  value={selectedFloor}
                  onChange={setSelectedFloor}
                  style={{ width: 120 }}
                >
                  {FLOORS.map(f => (
                    <Select.Option key={f} value={f}>第 {f} 层</Select.Option>
                  ))}
                </Select>
                <span style={{ color: '#666' }}>参数:</span>
                <Select
                  value={selectedSensorType}
                  onChange={setSelectedSensorType}
                  style={{ width: 200 }}
                >
                  {SENSOR_TYPES.map(s => (
                    <Select.Option key={s.value} value={s.value}>{s.label}</Select.Option>
                  ))}
                </Select>
                <RangePicker
                  showTime
                  value={timeRange}
                  onChange={(v) => setTimeRange(v as [dayjs.Dayjs, dayjs.Dayjs])}
                />
              </Space>
              <ReactECharts
                option={getChartOption()}
                style={{ height: 300 }}
                loading={loading}
              />
            </Space>
          </Card>
        </Col>

        <Col span={8}>
          <Card title={`第 ${selectedFloor} 层实时数据`} className="realtime-card">
            {realtimeData ? (
              <div className="sensor-data-list">
                {Object.entries(realtimeData.realtime_data).map(([type, data]) => {
                  const sensorInfo = SENSOR_TYPES.find(s => s.value === type)
                  return (
                    <div key={type} className="sensor-data-item">
                      <div className="sensor-type">
                        {sensorInfo?.label.split('(')[0] || type}
                      </div>
                      <div className="sensor-value">
                        <span className="value">{data.value.toFixed(4)}</span>
                        <span className="unit">{data.unit}</span>
                      </div>
                      <div className="sensor-time">
                        {new Date(data.timestamp).toLocaleTimeString('zh-CN')}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="no-data">暂无实时数据</div>
            )}
          </Card>

          <Card
            title="振动模态动画"
            style={{ marginTop: 16 }}
            className="vibration-control-card"
          >
            <Space direction="vertical" style={{ width: '100%' }} size={16}>
              <div className="control-row">
                <span className="control-label">状态</span>
                <Button
                  type={isPlaying ? 'default' : 'primary'}
                  icon={isPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                  onClick={() => setIsPlaying(!isPlaying)}
                >
                  {isPlaying ? '暂停动画' : '播放动画'}
                </Button>
              </div>
              <div className="control-row">
                <span className="control-label">振型阶次</span>
                <Select
                  value={vibrationMode}
                  onChange={setVibrationMode}
                  style={{ width: 150 }}
                  disabled={!isPlaying}
                >
                  <Select.Option value={0}>无振动</Select.Option>
                  <Select.Option value={1}>第一阶 (横摆)</Select.Option>
                  <Select.Option value={2}>第二阶 (扭转)</Select.Option>
                  <Select.Option value={3}>第三阶 (竖弯)</Select.Option>
                  <Select.Option value={4}>高阶振动</Select.Option>
                </Select>
              </div>
              <div className="control-row">
                <span className="control-label">振幅</span>
                <Slider
                  min={0}
                  max={10}
                  value={vibrationAmplitude}
                  onChange={setVibrationAmplitude}
                  disabled={!isPlaying}
                  style={{ flex: 1 }}
                />
                <span style={{ width: 40, textAlign: 'right' }}>{vibrationAmplitude}</span>
              </div>
              {isPlaying && (
                <div className="vibration-info">
                  <p>当前振型: 第{vibrationMode}阶</p>
                  <p>振动频率: {(vibrationMode * 0.5).toFixed(2)} Hz</p>
                  <p>振幅放大: {vibrationAmplitude}x</p>
                </div>
              )}
            </Space>
          </Card>

          <Card
            title="各层数据概览"
            style={{ marginTop: 16 }}
            className="overview-card"
          >
            <Tabs defaultActiveKey="1" size="small">
              <TabPane tab="位移" key="1">
                {FLOORS.map(floor => {
                  const data = realtimeDataByFloor[floor]
                  return (
                    <div key={floor} className="floor-overview-item">
                      <span className="floor-label">第{floor}层</span>
                      <span className="floor-value">
                        {data?.realtime_data.displacement_x?.value.toFixed(4) || '--'} mm
                      </span>
                    </div>
                  )
                })}
              </TabPane>
              <TabPane tab="温度" key="2">
                {FLOORS.map(floor => {
                  const data = realtimeDataByFloor[floor]
                  return (
                    <div key={floor} className="floor-overview-item">
                      <span className="floor-label">第{floor}层</span>
                      <span className="floor-value">
                        {data?.realtime_data.temperature?.value.toFixed(1) || '--'} °C
                      </span>
                    </div>
                  )
                })}
              </TabPane>
              <TabPane tab="含水率" key="3">
                {FLOORS.map(floor => {
                  const data = realtimeDataByFloor[floor]
                  return (
                    <div key={floor} className="floor-overview-item">
                      <span className="floor-label">第{floor}层</span>
                      <span className="floor-value">
                        {data?.realtime_data.moisture?.value.toFixed(2) || '--'} %
                      </span>
                    </div>
                  )
                })}
              </TabPane>
            </Tabs>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
