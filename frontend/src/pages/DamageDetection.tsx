import React, { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Button,
  Table,
  Tag,
  Space,
  Statistic,
  Row,
  Col,
  Modal,
  Form,
  InputNumber,
  Select,
  Progress,
  Tooltip,
  message,
  Alert as AntAlert
} from 'antd'
import {
  PlayCircleOutlined,
  SafetyOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  LineChartOutlined,
  ExperimentOutlined
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import PagodaModel from '@/components/PagodaModel/PagodaModel'
import { damageAPI, alertAPI } from '@/services/api'
import { useStore } from '@/store/useStore'
import type { DamageResult, ModalParameter, HealthAssessment } from '@/types'
import './DamageDetection.scss'

const { Option } = Select

const DamageDetection: React.FC = () => {
  const [damageResults, setDamageResults] = useState<DamageResult[]>([])
  const [modalParameters, setModalParameters] = useState<ModalParameter[]>([])
  const [healthAssessment, setHealthAssessment] = useState<HealthAssessment | null>(null)
  const [analyzeModalVisible, setAnalyzeModalVisible] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisHistory, setAnalysisHistory] = useState<any[]>([])
  const [form] = Form.useForm()
  const [selectedFloor, setSelectedFloor] = useState<number | null>(null)
  const [damageMarkers, setDamageMarkers] = useState<Array<{
    floor: number
    position: [number, number, number]
    damageIndex: number
    confidence: number
  }>>([])

  const damageProgress = useStore(state => state.damageProgress)
  const updateDamageProgress = useStore(state => state.updateDamageProgress)

  const floorHeights = [0, 6.59, 12.08, 17.07, 21.66, 25.75]

  useEffect(() => {
    loadData()
    loadAnalysisHistory()
  }, [])

  const loadData = async () => {
    try {
      const [modalRes, healthRes] = await Promise.all([
        damageAPI.getModalParameters(),
        damageAPI.getHealthAssessment()
      ])
      setModalParameters(modalRes.data)
      setHealthAssessment(healthRes.data)
      if (healthRes.data.damaged_floors.length > 0) {
        const latestAnalysis = analysisHistory[0]
        if (latestAnalysis) {
          loadDamageResults(latestAnalysis.id)
        }
      }
    } catch (error) {
      console.error('加载损伤识别数据失败:', error)
    }
  }

  const loadAnalysisHistory = async () => {
    try {
      const res = await damageAPI.getAnalyses({ limit: 10 })
      setAnalysisHistory(res.data)
    } catch (error) {
      console.error('加载分析历史失败:', error)
    }
  }

  const loadDamageResults = async (analysisId: string) => {
    try {
      const res = await damageAPI.getAnalysisResults(analysisId, 0.1)
      setDamageResults(res.data)
      const markers = res.data.map(r => ({
        floor: r.floor_number,
        position: [
          (Math.random() - 0.5) * 10,
          floorHeights[r.floor_number] + 1,
          (Math.random() - 0.5) * 10
        ] as [number, number, number],
        damageIndex: r.damage_index,
        confidence: r.confidence
      }))
      setDamageMarkers(markers)
    } catch (error) {
      console.error('加载损伤结果失败:', error)
    }
  }

  const handleAnalyze = async (values: any) => {
    setAnalyzing(true)
    try {
      const res = await damageAPI.analyze({
        analysis_window: values.analysis_window,
        floor: values.floor
      })
      const analysisId = res.data.analysis_id
      updateDamageProgress(analysisId, { status: 'running', progress: 0 })

      const progressInterval = setInterval(() => {
        const currentProgress = damageProgress[analysisId]
        if (currentProgress) {
          if (currentProgress.status === 'complete' || currentProgress.status === 'error') {
            clearInterval(progressInterval)
            if (currentProgress.status === 'complete') {
              message.success('损伤识别分析完成')
              loadDamageResults(analysisId)
              loadData()
              loadAnalysisHistory()
            }
          }
        }
      }, 2000)

      setAnalyzeModalVisible(false)
      form.resetFields()
    } catch (error) {
      message.error('启动损伤识别失败')
    } finally {
      setAnalyzing(false)
    }
  }

  const getHealthStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      good: '#52c41a',
      attention: '#faad14',
      warning: '#fa8c16',
      critical: '#f5222d',
      unknown: '#91d5ff'
    }
    return colors[status] || colors.unknown
  }

  const getHealthStatusText = (status: string) => {
    const texts: Record<string, string> = {
      good: '健康',
      attention: '需关注',
      warning: '预警',
      critical: '危险',
      unknown: '未知'
    }
    return texts[status] || texts.unknown
  }

  const frequencyChartOption = {
    title: { text: '模态频率变化趋势', left: 'center' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['第1阶', '第2阶', '第3阶', '第4阶'], bottom: 0 },
    xAxis: {
      type: 'category',
      data: modalParameters
        .filter(p => p.mode_order === 1)
        .map(p => new Date(p.measured_at).toLocaleDateString())
    },
    yAxis: { type: 'value', name: '频率(Hz)' },
    series: [1, 2, 3, 4].map(order => ({
      name: `第${order}阶`,
      type: 'line',
      data: modalParameters
        .filter(p => p.mode_order === order)
        .map(p => p.natural_frequency),
      smooth: true,
      markLine: {
        silent: true,
        data: modalParameters.filter(p => p.mode_order === order && p.is_baseline)
          .slice(0, 1)
          .map(p => ({ yAxis: p.natural_frequency, label: { formatter: '基线' } }))
      }
    }))
  }

  const damageSeverityChartOption = {
    title: { text: '各层损伤程度分布', left: 'center' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['1层', '2层', '3层', '4层', '5层'] },
    yAxis: { type: 'value', name: '损伤指数', max: 1 },
    series: [{
      type: 'bar',
      data: [1, 2, 3, 4, 5].map(floor => {
        const floorDamages = damageResults.filter(d => d.floor_number === floor)
        return floorDamages.length > 0
          ? Math.max(...floorDamages.map(d => d.damage_index))
          : 0
      }),
      itemStyle: {
        color: (params: any) => {
          const value = params.value
          if (value > 0.6) return '#f5222d'
          if (value > 0.3) return '#fa8c16'
          if (value > 0.1) return '#faad14'
          return '#52c41a'
        }
      }
    }]
  }

  const damageColumns = [
    {
      title: '楼层',
      dataIndex: 'floor_number',
      key: 'floor_number',
      render: (v: number) => `${v}层`
    },
    {
      title: '单元编号',
      dataIndex: 'element_id',
      key: 'element_id'
    },
    {
      title: '损伤指数',
      dataIndex: 'damage_index',
      key: 'damage_index',
      render: (v: number) => (
        <Progress
          percent={Math.round(v * 100)}
          size="small"
          strokeColor={v > 0.6 ? '#f5222d' : v > 0.3 ? '#fa8c16' : '#faad14'}
        />
      )
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (v: number) => `${(v * 100).toFixed(1)}%`
    },
    {
      title: '频率变化',
      dataIndex: 'frequency_change',
      key: 'frequency_change',
      render: (v?: number) => v ? `${(v * 100).toFixed(2)}%` : '-'
    },
    {
      title: '识别时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (v: string) => new Date(v).toLocaleString()
    }
  ]

  const historyColumns = [
    {
      title: '分析ID',
      dataIndex: 'id',
      key: 'id',
      render: (v: string) => v.slice(0, 8)
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (v: string) => {
        const colors: Record<string, string> = {
          pending: 'default',
          running: 'processing',
          complete: 'success',
          error: 'error'
        }
        return <Tag color={colors[v]}>{v}</Tag>
      }
    },
    {
      title: '损伤位置数',
      dataIndex: 'damage_locations_count',
      key: 'damage_locations_count',
      render: (v: number) => v || 0
    },
    {
      title: '分析时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (v: string) => new Date(v).toLocaleString()
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Button type="link" size="small" onClick={() => loadDamageResults(record.id)}>
          查看详情
        </Button>
      )
    }
  ]

  return (
    <div className="damage-detection">
      <div className="page-header">
        <h2>损伤识别与健康评估</h2>
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          onClick={() => setAnalyzeModalVisible(true)}
        >
          启动损伤识别
        </Button>
      </div>

      {healthAssessment && (
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title={
                  <Space>
                    <SafetyOutlined />
                    整体健康状态
                  </Space>
                }
                value={getHealthStatusText(healthAssessment.health_status)}
                valueStyle={{ color: getHealthStatusColor(healthAssessment.health_status) }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={
                  <Space>
                    <LineChartOutlined />
                    健康指数
                  </Space>
                }
                value={healthAssessment.overall_health_index * 100}
                precision={1}
                suffix="%"
                valueStyle={{ color: healthAssessment.overall_health_index > 0.8 ? '#52c41a' : '#fa8c16' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={
                  <Space>
                    <WarningOutlined />
                    损伤位置数
                  </Space>
                }
                value={healthAssessment.total_damage_locations}
                valueStyle={{ color: healthAssessment.total_damage_locations > 0 ? '#f5222d' : '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={
                  <Space>
                    <InfoCircleOutlined />
                    严重损伤位置
                  </Space>
                }
                value={healthAssessment.critical_locations.length}
                valueStyle={{ color: healthAssessment.critical_locations.length > 0 ? '#f5222d' : '#52c41a' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {healthAssessment?.critical_locations.length! > 0 && (
        <AntAlert
          message="发现严重损伤位置"
          description={
            <div>
              {healthAssessment?.critical_locations.map((loc, idx) => (
                <div key={idx}>
                  {loc.floor}层 单元#{loc.element_id}: 损伤指数 {(loc.damage_index * 100).toFixed(1)}%, 置信度 {(loc.confidence * 100).toFixed(1)}%
                </div>
              ))}
            </div>
          }
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card title="木塔损伤分布三维视图" size="small">
            <PagodaModel
              height={400}
              showVibration={false}
              showDamage={true}
              damageMarkers={damageMarkers}
              onFloorClick={setSelectedFloor}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="模态频率变化趋势" size="small">
            <ReactECharts option={frequencyChartOption} style={{ height: 380 }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="各层损伤程度分布" size="small">
            <ReactECharts option={damageSeverityChartOption} style={{ height: 350 }} />
          </Card>
        </Col>
        <Col span={12}>
          <Card
            title="损伤识别历史"
            size="small"
            extra={<Button type="link" size="small" onClick={loadAnalysisHistory}>刷新</Button>}
          >
            <Table
              dataSource={analysisHistory}
              columns={historyColumns}
              size="small"
              rowKey="id"
              pagination={{ pageSize: 5 }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="损伤识别结果详情"
        size="small"
        style={{ marginTop: 16 }}
        extra={
          <Space>
            <Select
              placeholder="选择楼层"
              style={{ width: 120 }}
              allowClear
              onChange={setSelectedFloor}
            >
              {[1, 2, 3, 4, 5].map(f => (
                <Option key={f} value={f}>{f}层</Option>
              ))}
            </Select>
          </Space>
        }
      >
        <Table
          dataSource={selectedFloor
            ? damageResults.filter(d => d.floor_number === selectedFloor)
            : damageResults
          }
          columns={damageColumns}
          size="small"
          rowKey="id"
          pagination={{ pageSize: 8 }}
          locale={{ emptyText: '暂无损伤识别结果' }}
        />
      </Card>

      <Modal
        title={
          <Space>
            <ExperimentOutlined />
            启动神经网络损伤识别
          </Space>
        }
        open={analyzeModalVisible}
        onCancel={() => setAnalyzeModalVisible(false)}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={handleAnalyze}>
          <Form.Item
            name="analysis_window"
            label="分析时间窗口"
            initialValue={24}
            rules={[{ required: true, message: '请输入分析时间窗口' }]}
          >
            <InputNumber
              min={1}
              max={720}
              addonAfter="小时"
              style={{ width: '100%' }}
            />
          </Form.Item>
          <Form.Item
            name="floor"
            label="分析楼层"
            help="可选，不选则分析全部楼层"
          >
            <Select placeholder="全部楼层" allowClear>
              {[1, 2, 3, 4, 5].map(f => (
                <Option key={f} value={f}>{f}层</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={analyzing} block>
                开始分析
              </Button>
              <Button onClick={() => setAnalyzeModalVisible(false)} block>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
        <AntAlert
          message="分析说明"
          description="系统将使用SSI/FDD方法提取模态参数，输入神经网络进行损伤定位与程度评估。分析过程可能需要1-3分钟。"
          type="info"
          showIcon
        />
      </Modal>
    </div>
  )
}

export default DamageDetection
