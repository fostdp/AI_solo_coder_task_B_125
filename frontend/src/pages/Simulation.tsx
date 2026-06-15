import { useState, useEffect } from 'react'
import {
  Row, Col, Card, Form, InputNumber, Select, Button,
  Space, Table, Progress, Tag, App, Typography, Divider
} from 'antd'
import { ThunderboltOutlined, WindOutlined, RiseOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import dayjs from 'dayjs'
import { simulationAPI } from '@/services/api'
import { useStore } from '@/store/useStore'
import PagodaModel from '@/components/PagodaModel'
import type { SimulationResult } from '@/types'
import './Simulation.scss'

const { Title, Text } = Typography
const { Option } = Select
const { Item } = Form

const SIMULATION_TYPES = [
  { value: 'wind', label: '风荷载仿真', icon: <WindOutlined /> },
  { value: 'earthquake', label: '地震荷载仿真', icon: <ThunderboltOutlined /> }
]

const DEFAULT_TIMBER_PROPS = {
  E_L: 10000,
  E_R: 800,
  E_T: 500,
  G_LR: 700,
  G_LT: 600,
  G_RT: 100,
  v_LR: 0.35,
  v_LT: 0.45,
  v_RT: 0.55,
  density: 450
}

export default function Simulation() {
  const { message } = App.useApp()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [simulations, setSimulations] = useState<any[]>([])
  const [selectedResult, setSelectedResult] = useState<any>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const { simulationProgress } = useStore()

  useEffect(() => {
    loadSimulations()
  }, [])

  const loadSimulations = async () => {
    try {
      const res = await simulationAPI.getSimulations({ limit: 10 })
      setSimulations(res.data)
      
      if (res.data.length > 0 && res.data[0].status === 'completed') {
        loadSimulationResults(res.data[0].id)
      }
    } catch (error) {
      console.error('加载仿真列表失败:', error)
    }
  }

  const loadSimulationResults = async (id: string) => {
    try {
      const res = await simulationAPI.getSimulation(id)
      setSelectedResult(res.data)
      setIsPlaying(true)
    } catch (error) {
      message.error('加载仿真结果失败')
    }
  }

  const handleRunSimulation = async (values: any) => {
    setLoading(true)
    try {
      const res = await simulationAPI.runSimulation({
        simulation_type: values.simulation_type,
        timber_properties: {
          E_L: values.E_L,
          E_R: values.E_R,
          E_T: values.E_T,
          G_LR: values.G_LR,
          G_LT: values.G_LT,
          G_RT: values.G_RT,
          v_LR: values.v_LR,
          v_LT: values.v_LT,
          v_RT: values.v_RT,
          density: values.density
        },
        load_params: {
          wind_speed: values.wind_speed,
          earthquake_level: values.earthquake_level,
          duration: values.duration,
          time_step: values.time_step
        },
        damping_ratio: values.damping_ratio
      })

      message.success(`仿真任务已提交，ID: ${res.data.simulation_id}`)
      
      const checkInterval = setInterval(async () => {
        await loadSimulations()
        const sim = simulations.find(s => s.id === res.data.simulation_id)
        if (sim?.status === 'completed') {
          clearInterval(checkInterval)
          loadSimulationResults(res.data.simulation_id)
        }
      }, 2000)

      setTimeout(() => clearInterval(checkInterval), 60000)

    } catch (error: any) {
      message.error(error.response?.data?.detail || '仿真任务提交失败')
    } finally {
      setLoading(false)
    }
  }

  const getTimeHistoryChart = () => {
    if (!selectedResult?.results?.[0]?.time_history_data) return {}
    
    const data = selectedResult.results[0].time_history_data
    const time = data.time || []
    const displacement = data.displacement || []
    const acceleration = data.acceleration || []

    return {
      tooltip: {
        trigger: 'axis'
      },
      legend: {
        data: ['位移 (mm)', '加速度 (g)']
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        name: '时间 (s)',
        data: time.map((t: number) => t.toFixed(1))
      },
      yAxis: [
        {
          type: 'value',
          name: '位移 (mm)'
        },
        {
          type: 'value',
          name: '加速度 (g)'
        }
      ],
      series: [
        {
          name: '位移 (mm)',
          type: 'line',
          smooth: true,
          symbol: 'none',
          data: displacement,
          itemStyle: { color: '#1677ff' }
        },
        {
          name: '加速度 (g)',
          type: 'line',
          smooth: true,
          symbol: 'none',
          yAxisIndex: 1,
          data: acceleration,
          itemStyle: { color: '#ff4d4f' }
        }
      ]
    }
  }

  const columns = [
    {
      title: '类型',
      dataIndex: 'simulation_type',
      key: 'type',
      render: (type: string) => (
        <Tag color={type === 'wind' ? 'blue' : 'orange'}>
          {type === 'wind' ? '风荷载' : '地震'}
        </Tag>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors: Record<string, string> = {
          pending: 'default',
          running: 'processing',
          completed: 'success',
          failed: 'error'
        }
        const texts: Record<string, string> = {
          pending: '等待中',
          running: '计算中',
          completed: '已完成',
          failed: '失败'
        }
        return <Tag color={colors[status]}>{texts[status]}</Tag>
      }
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created',
      render: (t: string) => dayjs(t).format('MM-DD HH:mm:ss')
    },
    {
      title: '进度',
      key: 'progress',
      render: (_: any, record: any) => {
        const progress = simulationProgress[record.id]
        if (record.status === 'completed') return <Progress percent={100} size="small" />
        if (record.status === 'running') {
          return <Progress percent={progress?.progress || 50} size="small" status="active" />
        }
        return <Progress percent={0} size="small" />
      }
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        record.status === 'completed' && (
          <Button type="link" onClick={() => loadSimulationResults(record.id)}>
            查看结果
          </Button>
        )
      )
    }
  ]

  const maxDisplacement = selectedResult?.results?.reduce(
    (max: number, r: any) => Math.max(max, Math.abs(r.max_displacement_mm || 0)), 0
  )
  const maxStress = selectedResult?.results?.reduce(
    (max: number, r: any) => Math.max(max, Math.abs(r.max_stress_mpa || 0)), 0
  )
  const maxAcceleration = selectedResult?.results?.reduce(
    (max: number, r: any) => Math.max(max, Math.abs(r.max_acceleration_g || 0)), 0
  )

  return (
    <div className="simulation-page">
      <Row gutter={[16, 16]}>
        <Col span={8}>
          <Card title="仿真参数配置" className="config-card">
            <Form
              form={form}
              layout="vertical"
              onFinish={handleRunSimulation}
              initialValues={{
                simulation_type: 'wind',
                ...DEFAULT_TIMBER_PROPS,
                wind_speed: 20,
                earthquake_level: 7,
                duration: 10,
                time_step: 0.01,
                damping_ratio: 0.02
              }}
            >
              <Item name="simulation_type" label="仿真类型">
                <Select>
                  {SIMULATION_TYPES.map(t => (
                    <Option key={t.value} value={t.value}>
                      <Space>{t.icon} {t.label}</Space>
                    </Option>
                  ))}
                </Select>
              </Item>

              <Divider orientation="left">木材材料参数</Divider>
              
              <Row gutter={8}>
                <Col span={12}>
                  <Item name="E_L" label="顺纹弹性模量 (MPa)">
                    <InputNumber style={{ width: '100%' }} min={100} max={20000} />
                  </Item>
                </Col>
                <Col span={12}>
                  <Item name="E_R" label="径向弹性模量 (MPa)">
                    <InputNumber style={{ width: '100%' }} min={50} max={5000} />
                  </Item>
                </Col>
              </Row>
              
              <Row gutter={8}>
                <Col span={12}>
                  <Item name="E_T" label="弦向弹性模量 (MPa)">
                    <InputNumber style={{ width: '100%' }} min={50} max={3000} />
                  </Item>
                </Col>
                <Col span={12}>
                  <Item name="G_LR" label="LR剪切模量 (MPa)">
                    <InputNumber style={{ width: '100%' }} min={50} max={2000} />
                  </Item>
                </Col>
              </Row>
              
              <Row gutter={8}>
                <Col span={12}>
                  <Item name="G_LT" label="LT剪切模量 (MPa)">
                    <InputNumber style={{ width: '100%' }} min={50} max={2000} />
                  </Item>
                </Col>
                <Col span={12}>
                  <Item name="G_RT" label="RT剪切模量 (MPa)">
                    <InputNumber style={{ width: '100%' }} min={50} max={500} />
                  </Item>
                </Col>
              </Row>
              
              <Row gutter={8}>
                <Col span={8}>
                  <Item name="v_LR" label="LR泊松比">
                    <InputNumber style={{ width: '100%' }} min={0.1} max={0.6} step={0.01} />
                  </Item>
                </Col>
                <Col span={8}>
                  <Item name="v_LT" label="LT泊松比">
                    <InputNumber style={{ width: '100%' }} min={0.1} max={0.6} step={0.01} />
                  </Item>
                </Col>
                <Col span={8}>
                  <Item name="v_RT" label="RT泊松比">
                    <InputNumber style={{ width: '100%' }} min={0.1} max={0.6} step={0.01} />
                  </Item>
                </Col>
              </Row>
              
              <Item name="density" label="密度 (kg/m³)">
                <InputNumber style={{ width: '100%' }} min={300} max={800} />
              </Item>

              <Divider orientation="left">荷载参数</Divider>
              
              <Row gutter={8}>
                <Col span={12}>
                  <Item name="wind_speed" label="风速 (m/s)">
                    <InputNumber style={{ width: '100%' }} min={0} max={50} />
                  </Item>
                </Col>
                <Col span={12}>
                  <Item name="earthquake_level" label="地震烈度">
                    <InputNumber style={{ width: '100%' }} min={5} max={11} step={0.5} />
                  </Item>
                </Col>
              </Row>
              
              <Row gutter={8}>
                <Col span={12}>
                  <Item name="duration" label="持时 (s)">
                    <InputNumber style={{ width: '100%' }} min={1} max={60} />
                  </Item>
                </Col>
                <Col span={12}>
                  <Item name="time_step" label="时间步长 (s)">
                    <InputNumber style={{ width: '100%' }} min={0.001} max={0.1} step={0.001} />
                  </Item>
                </Col>
              </Row>
              
              <Item name="damping_ratio" label="阻尼比">
                <InputNumber style={{ width: '100%' }} min={0.001} max={0.1} step={0.001} />
              </Item>

              <Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  block
                  size="large"
                  loading={loading}
                  icon={<ThunderboltOutlined />}
                >
                  运行仿真
                </Button>
              </Item>
            </Form>
          </Card>
        </Col>

        <Col span={16}>
          <Card
            title="仿真模型预览"
            bodyStyle={{ padding: 0, height: 400 }}
            className="model-card"
          >
            <PagodaModel
              showSensors={false}
              showDamage={false}
              vibrationMode={selectedResult ? 1 : 0}
              vibrationAmplitude={isPlaying ? Math.min(maxDisplacement || 0, 10) : 0}
            />
          </Card>

          {selectedResult && (
            <>
              <Card title="仿真结果摘要" style={{ marginTop: 16 }}>
                <Row gutter={[16, 16]}>
                  <Col span={8}>
                    <div className="result-stat">
                      <div className="stat-label">最大位移</div>
                      <div className="stat-value">{maxDisplacement?.toFixed(4)} <span className="unit">mm</span></div>
                      <Progress
                        percent={Math.min((maxDisplacement || 0) / 50 * 100, 100)}
                        strokeColor="#1677ff"
                        showInfo={false}
                      />
                    </div>
                  </Col>
                  <Col span={8}>
                    <div className="result-stat">
                      <div className="stat-label">最大应力</div>
                      <div className="stat-value">{maxStress?.toFixed(4)} <span className="unit">MPa</span></div>
                      <Progress
                        percent={Math.min((maxStress || 0) / 30 * 100, 100)}
                        strokeColor="#faad14"
                        showInfo={false}
                      />
                    </div>
                  </Col>
                  <Col span={8}>
                    <div className="result-stat">
                      <div className="stat-label">最大加速度</div>
                      <div className="stat-value">{maxAcceleration?.toFixed(4)} <span className="unit">g</span></div>
                      <Progress
                        percent={Math.min((maxAcceleration || 0) / 0.5 * 100, 100)}
                        strokeColor="#ff4d4f"
                        showInfo={false}
                      />
                    </div>
                  </Col>
                </Row>
                
                {selectedResult.results && (
                  <Table
                    dataSource={selectedResult.results}
                    rowKey="floor_number"
                    size="small"
                    pagination={false}
                    style={{ marginTop: 16 }}
                  >
                    <Table.Column title="楼层" dataIndex="floor_number" key="floor" render={(v: number) => `第${v}层`} />
                    <Table.Column
                      title="最大位移 (mm)"
                      dataIndex="max_displacement_mm"
                      key="disp"
                      render={(v: number) => v?.toFixed(4)}
                    />
                    <Table.Column
                      title="最大应力 (MPa)"
                      dataIndex="max_stress_mpa"
                      key="stress"
                      render={(v: number) => v?.toFixed(4)}
                    />
                    <Table.Column
                      title="最大加速度 (g)"
                      dataIndex="max_acceleration_g"
                      key="acc"
                      render={(v: number) => v?.toFixed(4)}
                    />
                  </Table>
                )}

                {selectedResult.natural_frequencies && (
                  <div style={{ marginTop: 16 }}>
                    <Text strong>固有频率 (Hz): </Text>
                    {selectedResult.natural_frequencies.map((f: number, i: number) => (
                      <Tag key={i} color="blue">{f.toFixed(4)}</Tag>
                    ))}
                  </div>
                )}
              </Card>

              <Card title="时程响应曲线" style={{ marginTop: 16 }}>
                <ReactECharts option={getTimeHistoryChart()} style={{ height: 300 }} />
              </Card>
            </>
          )}

          <Card title="历史仿真记录" style={{ marginTop: 16 }}>
            <Table
              dataSource={simulations}
              columns={columns}
              rowKey="id"
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
