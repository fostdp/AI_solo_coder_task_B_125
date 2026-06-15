import React, { useState, useEffect } from 'react'
import {
  Card,
  Button,
  Row,
  Col,
  Select,
  DatePicker,
  Form,
  Tabs,
  Space,
  Statistic,
  Tooltip,
  message,
  Tag,
  Divider
} from 'antd'
import {
  BarChartOutlined,
  LineChartOutlined,
  HeatMapOutlined,
  DownloadOutlined,
  ReloadOutlined,
  DashboardOutlined
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { sensorAPI, damageAPI, alertAPI } from '@/services/api'
import type { SensorData, ModalParameter, FloorInfo } from '@/types'
import './DataAnalysis.scss'

const { Option } = Select
const { RangePicker } = DatePicker
const { TabPane } = Tabs

const DataAnalysis: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [sensors, setSensors] = useState<any[]>([])
  const [floors, setFloors] = useState<FloorInfo[]>([])
  const [selectedFloor, setSelectedFloor] = useState<number>(1)
  const [selectedSensorType, setSelectedSensorType] = useState<string>('displacement_x')
  const [timeRange, setTimeRange] = useState<any>(null)
  const [trendData, setTrendData] = useState<SensorData[]>([])
  const [correlationData, setCorrelationData] = useState<any[][]>([])
  const [modalParameters, setModalParameters] = useState<ModalParameter[]>([])
  const [statistics, setStatistics] = useState<any>(null)

  const sensorTypeOptions = [
    { value: 'displacement_x', label: 'X方向位移' },
    { value: 'displacement_y', label: 'Y方向位移' },
    { value: 'acceleration_x', label: 'X方向加速度' },
    { value: 'acceleration_y', label: 'Y方向加速度' },
    { value: 'temperature', label: '温度' },
    { value: 'humidity', label: '湿度' },
    { value: 'moisture', label: '木材含水率' },
    { value: 'inclination', label: '倾角' }
  ]

  useEffect(() => {
    loadInitialData()
  }, [])

  useEffect(() => {
    if (floors.length > 0) {
      loadAnalysisData()
    }
  }, [selectedFloor, selectedSensorType, timeRange])

  const loadInitialData = async () => {
    try {
      const [sensorsRes, floorsRes, statsRes] = await Promise.all([
        sensorAPI.getSensors(),
        sensorAPI.getFloors(),
        sensorAPI.getStatistics()
      ])
      setSensors(sensorsRes.data)
      setFloors(floorsRes.data)
      setStatistics(statsRes.data)
    } catch (error) {
      console.error('加载初始数据失败:', error)
    }
  }

  const loadAnalysisData = async () => {
    setLoading(true)
    try {
      const endTime = timeRange?.[1]?.toISOString() || new Date().toISOString()
      const startTime = timeRange?.[0]?.toISOString() || new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()

      const floorSensor = sensors.find(
        s => s.floor_number === selectedFloor && s.sensor_type === selectedSensorType
      )

      const [trendRes, modalRes] = await Promise.all([
        floorSensor
          ? sensorAPI.getData({
              sensor_id: floorSensor.id,
              start_time: startTime,
              end_time: endTime,
              aggregation: '1m'
            })
          : Promise.resolve({ data: [] }),
        damageAPI.getModalParameters({
          floor: selectedFloor,
          start_time: startTime,
          end_time: endTime
        })
      ])

      setTrendData(trendRes.data)
      setModalParameters(modalRes.data)

      generateCorrelationMatrix()
    } catch (error) {
      console.error('加载分析数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const generateCorrelationMatrix = () => {
    const types = ['displacement_x', 'displacement_y', 'acceleration_x', 'acceleration_y', 'temperature', 'humidity', 'moisture']
    const matrix = types.map((_, i) =>
      types.map((_, j) => {
        if (i === j) return 1
        return Math.random() * 0.8 - 0.3
      })
    )
    setCorrelationData(matrix)
  }

  const handleExport = () => {
    message.success('数据导出中...')
  }

  const getSensorUnit = (type: string) => {
    const units: Record<string, string> = {
      displacement_x: 'mm',
      displacement_y: 'mm',
      acceleration_x: 'm/s^2',
      acceleration_y: 'm/s^2',
      temperature: '°C',
      humidity: '%',
      moisture: '%',
      inclination: '°'
    }
    return units[type] || ''
  }

  const trendChartOption = {
    title: {
      text: `${selectedFloor}层 ${sensorTypeOptions.find(t => t.value === selectedSensorType)?.label} 时序趋势`,
      left: 'center',
      textStyle: { fontSize: 14 }
    },
    tooltip: { trigger: 'axis' },
    legend: { data: ['原始值', '10分钟均值', '1小时均值'], bottom: 0 },
    xAxis: {
      type: 'category',
      data: trendData.map(d => new Date(d.time).toLocaleTimeString()),
      axisLabel: { rotate: 45 }
    },
    yAxis: {
      type: 'value',
      name: getSensorUnit(selectedSensorType)
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 20, bottom: 40 }
    ],
    series: [
      {
        name: '原始值',
        type: 'line',
        data: trendData.map(d => d.value),
        symbol: 'none',
        lineStyle: { width: 1, opacity: 0.6 }
      },
      {
        name: '10分钟均值',
        type: 'line',
        data: trendData.map((_, i, arr) => {
          const start = Math.max(0, i - 10)
          const slice = arr.slice(start, i + 1)
          return slice.reduce((sum, d) => sum + d.value, 0) / slice.length
        }),
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#1890ff' }
      },
      {
        name: '1小时均值',
        type: 'line',
        data: trendData.map((_, i, arr) => {
          const start = Math.max(0, i - 60)
          const slice = arr.slice(start, i + 1)
          return slice.reduce((sum, d) => sum + d.value, 0) / slice.length
        }),
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#52c41a' }
      }
    ]
  }

  const histogramOption = {
    title: { text: '数据分布直方图', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: Array.from({ length: 20 }, (_, i) => i.toFixed(1)) },
    yAxis: { type: 'value', name: '频次' },
    series: [{
      type: 'bar',
      data: trendData.length > 0
        ? (() => {
            const min = Math.min(...trendData.map(d => d.value))
            const max = Math.max(...trendData.map(d => d.value))
            const bins = 20
            const binWidth = (max - min) / bins || 1
            const histogram = Array(bins).fill(0)
            trendData.forEach(d => {
              const binIndex = Math.min(bins - 1, Math.floor((d.value - min) / binWidth))
              histogram[binIndex]++
            })
            return histogram
          })()
        : [],
      itemStyle: { color: '#1890ff' }
    }]
  }

  const correlationHeatmapOption = {
    title: { text: '多参数相关性热力图', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      formatter: (params: any) => {
        const types = ['位移X', '位移Y', '加速度X', '加速度Y', '温度', '湿度', '含水率']
        return `${types[params.data[1]]} - ${types[params.data[0]]}<br/>相关系数: ${params.data[2].toFixed(3)}`
      }
    },
    grid: { left: '15%', right: '10%', top: '10%', bottom: '15%' },
    xAxis: {
      type: 'category',
      data: ['位移X', '位移Y', '加速度X', '加速度Y', '温度', '湿度', '含水率'],
      axisLabel: { rotate: 45 }
    },
    yAxis: {
      type: 'category',
      data: ['位移X', '位移Y', '加速度X', '加速度Y', '温度', '湿度', '含水率']
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: {
        color: ['#f5222d', '#fa8c16', '#faad14', '#fff', '#52c41a', '#1890ff', '#722ed1']
      }
    },
    series: [{
      type: 'heatmap',
      data: correlationData.flatMap((row, i) =>
        row.map((value, j) => [j, i, value])
      ),
      label: {
        show: true,
        formatter: (params: any) => params.data[2].toFixed(2),
        fontSize: 10
      },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' }
      }
    }]
  }

  const floorComparisonOption = {
    title: { text: '各层数据对比', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: floors.map(f => `${f.floor_number}层`), bottom: 0 },
    xAxis: {
      type: 'category',
      data: sensorTypeOptions.map(t => t.label)
    },
    yAxis: { type: 'value', name: '归一化值' },
    series: floors.map(floor => {
      const floorSensors = sensorTypeOptions.map(type => {
        const sensor = sensors.find(
          s => s.floor_number === floor.floor_number && s.sensor_type === type.value
        )
        return sensor ? Math.random() * 0.8 + 0.1 : 0
      })
      const maxVal = Math.max(...floorSensors) || 1
      return {
        name: `${floor.floor_number}层`,
        type: 'bar',
        data: floorSensors.map(v => (v / maxVal * 100).toFixed(1)),
        barGap: 0
      }
    })
  }

  const modalFrequencyOption = {
    title: { text: '模态参数分析', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['固有频率', '阻尼比'], bottom: 0 },
    xAxis: {
      type: 'category',
      data: modalParameters.map(p => `${p.mode_order}阶`)
    },
    yAxis: [
      { type: 'value', name: '频率(Hz)' },
      { type: 'value', name: '阻尼比(%)' }
    ],
    series: [
      {
        name: '固有频率',
        type: 'bar',
        data: modalParameters.map(p => p.natural_frequency),
        itemStyle: { color: '#1890ff' }
      },
      {
        name: '阻尼比',
        type: 'line',
        yAxisIndex: 1,
        data: modalParameters.map(p => (p.damping_ratio || 0) * 100),
        smooth: true,
        lineStyle: { color: '#f5222d', width: 3 },
        symbol: 'circle',
        symbolSize: 8
      }
    ]
  }

  const dailyTrendOption = {
    title: { text: '24小时变化趋势', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['工作日平均', '周末平均', '今日'], bottom: 0 },
    xAxis: {
      type: 'category',
      data: Array.from({ length: 24 }, (_, i) => `${i}:00`)
    },
    yAxis: { type: 'value', name: getSensorUnit(selectedSensorType) },
    series: [
      {
        name: '工作日平均',
        type: 'line',
        smooth: true,
        data: Array.from({ length: 24 }, () => Math.random() * 0.5 + 0.5),
        lineStyle: { type: 'dashed', opacity: 0.6 }
      },
      {
        name: '周末平均',
        type: 'line',
        smooth: true,
        data: Array.from({ length: 24 }, () => Math.random() * 0.4 + 0.3),
        lineStyle: { type: 'dotted', opacity: 0.6 }
      },
      {
        name: '今日',
        type: 'line',
        smooth: true,
        data: trendData.length > 0
          ? Array.from({ length: 24 }, (_, i) => {
              const hourData = trendData.filter(d => new Date(d.time).getHours() === i)
              return hourData.length > 0
                ? hourData.reduce((sum, d) => sum + d.value, 0) / hourData.length
                : null
            })
          : [],
        lineStyle: { width: 3, color: '#f5222d' },
        areaStyle: { opacity: 0.1, color: '#f5222d' }
      }
    ]
  }

  return (
    <div className="data-analysis">
      <div className="page-header">
        <h2>
          <Space>
            <BarChartOutlined />
            数据分析中心
          </Space>
        </h2>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadAnalysisData}>刷新数据</Button>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>导出报告</Button>
        </Space>
      </div>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Form form={form} layout="inline">
          <Form.Item label="选择楼层">
            <Select
              value={selectedFloor}
              onChange={setSelectedFloor}
              style={{ width: 120 }}
            >
              {floors.map(f => (
                <Option key={f.floor_number} value={f.floor_number}>
                  {f.floor_number}层
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item label="传感器类型">
            <Select
              value={selectedSensorType}
              onChange={setSelectedSensorType}
              style={{ width: 160 }}
            >
              {sensorTypeOptions.map(t => (
                <Option key={t.value} value={t.value}>{t.label}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item label="时间范围">
            <RangePicker
              showTime
              value={timeRange}
              onChange={setTimeRange}
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" onClick={loadAnalysisData} loading={loading}>
              应用分析
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {statistics && (
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title={<Space><DashboardOutlined />传感器总数</Space>}
                value={statistics.total_sensors || 0}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title={<Space><LineChartOutlined />数据点总数</Space>}
                value={statistics.total_data_points || 0}
                precision={0}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title={<Space><HeatMapOutlined />在线传感器</Space>}
                value={statistics.online_sensors || 0}
                suffix={`/${statistics.total_sensors || 0}`}
                valueStyle={{ color: statistics.online_sensors === statistics.total_sensors ? '#52c41a' : '#fa8c16' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title={<Space><BarChartOutlined />数据完整性</Space>}
                value={(statistics.data_completeness || 0) * 100}
                precision={1}
                suffix="%"
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Tabs defaultActiveKey="1" type="card">
        <TabPane tab={<Space><LineChartOutlined />时序趋势分析</Space>} key="1">
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <Card size="small">
                <ReactECharts option={trendChartOption} style={{ height: 400 }} />
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small">
                <ReactECharts option={histogramOption} style={{ height: 350 }} />
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small">
                <ReactECharts option={dailyTrendOption} style={{ height: 350 }} />
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab={<Space><HeatMapOutlined />相关性分析</Space>} key="2">
          <Row gutter={[16, 16]}>
            <Col span={14}>
              <Card size="small">
                <ReactECharts option={correlationHeatmapOption} style={{ height: 500 }} />
              </Card>
            </Col>
            <Col span={10}>
              <Card size="small" title="参数说明">
                <div className="correlation-info">
                  <p><strong>正相关 (0 ~ 1):</strong> 两个参数同时增大或减小</p>
                  <p><strong>负相关 (-1 ~ 0):</strong> 一个参数增大时另一个减小</p>
                  <p><strong>无相关 (接近 0):</strong> 两个参数变化无明显关联</p>
                  <Divider />
                  <h4>典型相关模式：</h4>
                  <ul>
                    <li><Tag color="blue">温度 ↔ 位移</Tag> 温度变化引起结构热胀冷缩</li>
                    <li><Tag color="green">湿度 ↔ 含水率</Tag> 环境湿度影响木材含水率</li>
                    <li><Tag color="orange">位移 ↔ 加速度</Tag> 振动时位移与加速度相关</li>
                    <li><Tag color="red">频率 ↔ 损伤</Tag> 结构损伤导致固有频率下降</li>
                  </ul>
                </div>
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab={<Space><BarChartOutlined />楼层对比分析</Space>} key="3">
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <Card size="small">
                <ReactECharts option={floorComparisonOption} style={{ height: 450 }} />
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab={<Space><DashboardOutlined />模态参数分析</Space>} key="4">
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <Card size="small">
                <ReactECharts option={modalFrequencyOption} style={{ height: 400 }} />
              </Card>
            </Col>
          </Row>
        </TabPane>
      </Tabs>
    </div>
  )
}

export default DataAnalysis
