import React, { useState, useEffect } from 'react'
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
  Input,
  InputNumber,
  Select,
  DatePicker,
  message,
  Tooltip,
  Popconfirm,
  Drawer,
  Descriptions,
  Divider
} from 'antd'
import {
  BellOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  SettingOutlined,
  FilterOutlined,
  ReloadOutlined,
  EyeOutlined
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { alertAPI, damageAPI } from '@/services/api'
import { useStore } from '@/store/useStore'
import type { Alert } from '@/types'
import './AlertCenter.scss'

const { Option } = Select
const { RangePicker } = DatePicker
const { TextArea } = Input

const AlertCenter: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [statistics, setStatistics] = useState<any>(null)
  const [thresholds, setThresholds] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [detailVisible, setDetailVisible] = useState(false)
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null)
  const [thresholdModalVisible, setThresholdModalVisible] = useState(false)
  const [filterForm] = Form.useForm()
  const [thresholdForm] = Form.useForm()
  const [filters, setFilters] = useState<any>({})
  const [total, setTotal] = useState(0)

  const alertsStore = useStore(state => state.alerts)
  const setAlertsStore = useStore(state => state.setAlerts)
  const unreadAlertCount = useStore(state => state.unreadAlertCount)

  const alertTypeMap: Record<string, { label: string; icon: React.ReactNode }> = {
    displacement: { label: '位移超限', icon: <WarningOutlined /> },
    acceleration: { label: '加速度超限', icon: <WarningOutlined /> },
    temperature: { label: '温度异常', icon: <WarningOutlined /> },
    humidity: { label: '湿度异常', icon: <WarningOutlined /> },
    moisture: { label: '含水率异常', icon: <WarningOutlined /> },
    interstory_drift: { label: '层间位移角超限', icon: <ExclamationCircleOutlined /> },
    frequency_change: { label: '固有频率异常', icon: <ExclamationCircleOutlined /> }
  }

  useEffect(() => {
    loadData()
    loadThresholds()
  }, [])

  useEffect(() => {
    if (alertsStore.length > 0) {
      setAlerts(alertsStore)
    }
  }, [alertsStore])

  const loadData = async (page = 1, pageSize = 10) => {
    setLoading(true)
    try {
      const params: any = {
        offset: (page - 1) * pageSize,
        limit: pageSize,
        ...filters
      }
      const [alertsRes, statsRes] = await Promise.all([
        alertAPI.getAlerts(params),
        alertAPI.getStatistics(24)
      ])
      setAlerts(alertsRes.data)
      setAlertsStore(alertsRes.data)
      setTotal(alertsRes.data.length > 0 ? (page - 1) * pageSize + alertsRes.data.length + 50 : 0)
      setStatistics(statsRes.data)
    } catch (error) {
      console.error('加载告警数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadThresholds = async () => {
    try {
      const res = await alertAPI.getThresholds()
      setThresholds(res.data)
    } catch (error) {
      console.error('加载阈值配置失败:', error)
    }
  }

  const handleAcknowledge = async (alert: Alert, note?: string) => {
    try {
      await alertAPI.acknowledgeAlert(alert.id, note)
      message.success('告警已确认')
      loadData()
    } catch (error) {
      message.error('确认失败')
    }
  }

  const handleResolve = async (alert: Alert, note?: string) => {
    try {
      await alertAPI.resolveAlert(alert.id, note)
      message.success('告警已处理')
      loadData()
    } catch (error) {
      message.error('处理失败')
    }
  }

  const handleSetThreshold = async (values: any) => {
    try {
      await alertAPI.setThreshold(values)
      message.success('阈值配置已更新')
      setThresholdModalVisible(false)
      thresholdForm.resetFields()
      loadThresholds()
    } catch (error) {
      message.error('配置失败')
    }
  }

  const handleFilter = (values: any) => {
    const filters: any = {}
    if (values.status) filters.status = values.status
    if (values.severity) filters.severity = values.severity
    if (values.alert_type) filters.alert_type = values.alert_type
    if (values.floor) filters.floor = values.floor
    if (values.time_range) {
      filters.start_time = values.time_range[0].toISOString()
      filters.end_time = values.time_range[1].toISOString()
    }
    setFilters(filters)
    loadData()
  }

  const handleResetFilter = () => {
    filterForm.resetFields()
    setFilters({})
    loadData()
  }

  const openDetail = (alert: Alert) => {
    setSelectedAlert(alert)
    setDetailVisible(true)
    if (alert.status === 'pending') {
      handleAcknowledge(alert)
    }
  }

  const alertTypeTrendOption = {
    title: { text: '告警类型分布(24小时)', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: statistics?.by_type?.map((item: any) => ({
        name: alertTypeMap[item.type]?.label || item.type,
        value: item.count
      })) || [],
      label: { show: true, formatter: '{b}: {c}' }
    }]
  }

  const alertTimelineOption = {
    title: { text: '告警时间分布(24小时)', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: statistics?.timeline?.map((item: any) => item.hour) || []
    },
    yAxis: { type: 'value', name: '数量' },
    series: [{
      type: 'bar',
      data: statistics?.timeline?.map((item: any) => item.count) || [],
      itemStyle: {
        color: (params: any) => {
          const value = params.value
          if (value > 10) return '#f5222d'
          if (value > 5) return '#fa8c16'
          return '#1890ff'
        }
      }
    }]
  }

  const columns = [
    {
      title: '告警类型',
      dataIndex: 'alert_type',
      key: 'alert_type',
      width: 150,
      render: (v: string) => {
        const type = alertTypeMap[v] || { label: v, icon: <WarningOutlined /> }
        return (
          <Space>
            {type.icon}
            {type.label}
          </Space>
        )
      }
    },
    {
      title: '楼层',
      dataIndex: 'floor_number',
      key: 'floor_number',
      width: 80,
      render: (v?: number) => v ? `${v}层` : '-'
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (v: string) => (
        <Tag color={v === 'critical' ? 'red' : 'orange'}>
          {v === 'critical' ? '严重' : '警告'}
        </Tag>
      )
    },
    {
      title: '阈值',
      dataIndex: 'threshold_value',
      key: 'threshold_value',
      width: 120,
      render: (v: number, record: Alert) => (
        <span>
          {v} {record.alert_type.includes('frequency') ? 'Hz' : record.alert_type.includes('drift') ? 'rad' : 'mm'}
        </span>
      )
    },
    {
      title: '实际值',
      dataIndex: 'actual_value',
      key: 'actual_value',
      width: 120,
      render: (v: number, record: Alert) => (
        <span style={{ color: record.actual_value > record.threshold_value ? '#f5222d' : 'inherit' }}>
          {v.toFixed(4)}
        </span>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (v: string) => {
        const colors: Record<string, string> = {
          pending: 'red',
          acknowledged: 'orange',
          resolved: 'green'
        }
        const texts: Record<string, string> = {
          pending: '待处理',
          acknowledged: '已确认',
          resolved: '已处理'
        }
        return <Tag color={colors[v]}>{texts[v]}</Tag>
      }
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (v: string) => new Date(v).toLocaleString()
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: any, record: Alert) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => openDetail(record)}>
            详情
          </Button>
          {record.status === 'pending' && (
            <Button type="link" size="small" icon={<CheckCircleOutlined />} onClick={() => handleAcknowledge(record)}>
              确认
            </Button>
          )}
          {record.status !== 'resolved' && (
            <Popconfirm
              title="标记为已处理？"
              onConfirm={() => handleResolve(record)}
              okText="是"
              cancelText="否"
            >
              <Button type="link" size="small" danger>
                处理
              </Button>
            </Popconfirm>
          )}
        </Space>
      )
    }
  ]

  const thresholdColumns = [
    {
      title: '参数名称',
      dataIndex: 'parameter_name',
      key: 'parameter_name',
      render: (v: string) => alertTypeMap[v]?.label || v
    },
    {
      title: '单位',
      dataIndex: 'unit',
      key: 'unit'
    },
    {
      title: '预警阈值',
      dataIndex: 'warning_threshold',
      key: 'warning_threshold',
      render: (v: number) => <Tag color="orange">{v}</Tag>
    },
    {
      title: '严重阈值',
      dataIndex: 'critical_threshold',
      key: 'critical_threshold',
      render: (v: number) => <Tag color="red">{v}</Tag>
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description'
    }
  ]

  return (
    <div className="alert-center">
      <div className="page-header">
        <h2>
          <Space>
            <BellOutlined />
            告警中心
            {unreadAlertCount > 0 && (
              <Tag color="red" style={{ marginLeft: 8 }}>
                {unreadAlertCount} 条未读
              </Tag>
            )}
          </Space>
        </h2>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => loadData()}>刷新</Button>
          <Button
            type="primary"
            icon={<SettingOutlined />}
            onClick={() => setThresholdModalVisible(true)}
          >
            阈值配置
          </Button>
        </Space>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title={<Space><ClockCircleOutlined />待处理告警</Space>}
              value={statistics?.pending_count || 0}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title={<Space><WarningOutlined />24小时告警总数</Space>}
              value={statistics?.total_count || 0}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title={<Space><ExclamationCircleOutlined />严重告警</Space>}
              value={statistics?.critical_count || 0}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title={<Space><CheckCircleOutlined />已处理</Space>}
              value={statistics?.resolved_count || 0}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card size="small" title="告警筛选" extra={<Button type="link" size="small" onClick={handleResetFilter}>重置</Button>}>
            <Form form={filterForm} layout="inline" onFinish={handleFilter}>
              <Form.Item name="status" label="状态">
                <Select placeholder="全部" allowClear style={{ width: 100 }}>
                  <Option value="pending">待处理</Option>
                  <Option value="acknowledged">已确认</Option>
                  <Option value="resolved">已处理</Option>
                </Select>
              </Form.Item>
              <Form.Item name="severity" label="严重程度">
                <Select placeholder="全部" allowClear style={{ width: 100 }}>
                  <Option value="warning">警告</Option>
                  <Option value="critical">严重</Option>
                </Select>
              </Form.Item>
              <Form.Item name="alert_type" label="类型">
                <Select placeholder="全部" allowClear style={{ width: 140 }}>
                  {Object.entries(alertTypeMap).map(([key, value]) => (
                    <Option key={key} value={key}>{value.label}</Option>
                  ))}
                </Select>
              </Form.Item>
              <Form.Item name="floor" label="楼层">
                <Select placeholder="全部" allowClear style={{ width: 80 }}>
                  {[1, 2, 3, 4, 5].map(f => (
                    <Option key={f} value={f}>{f}层</Option>
                  ))}
                </Select>
              </Form.Item>
              <Form.Item name="time_range" label="时间">
                <RangePicker showTime />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" icon={<FilterOutlined />}>筛选</Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <ReactECharts option={alertTypeTrendOption} style={{ height: 220 }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <ReactECharts option={alertTimelineOption} style={{ height: 220 }} />
          </Card>
        </Col>
      </Row>

      <Card
        title="告警列表"
        size="small"
        extra={<span>共 {total} 条记录</span>}
      >
        <Table
          dataSource={alerts}
          columns={columns}
          size="small"
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (page, pageSize) => loadData(page, pageSize)
          }}
        />
      </Card>

      <Card
        title="告警阈值配置"
        size="small"
        style={{ marginTop: 16 }}
      >
        <Table
          dataSource={thresholds}
          columns={thresholdColumns}
          size="small"
          rowKey="parameter_name"
          pagination={false}
        />
      </Card>

      <Drawer
        title="告警详情"
        placement="right"
        width={600}
        open={detailVisible}
        onClose={() => setDetailVisible(false)}
      >
        {selectedAlert && (
          <>
            <Descriptions title="基本信息" bordered column={1} size="small">
              <Descriptions.Item label="告警ID">{selectedAlert.id}</Descriptions.Item>
              <Descriptions.Item label="告警类型">
                {alertTypeMap[selectedAlert.alert_type]?.label || selectedAlert.alert_type}
              </Descriptions.Item>
              <Descriptions.Item label="楼层">{selectedAlert.floor_number ? `${selectedAlert.floor_number}层` : '-'}</Descriptions.Item>
              <Descriptions.Item label="严重程度">
                <Tag color={selectedAlert.severity === 'critical' ? 'red' : 'orange'}>
                  {selectedAlert.severity === 'critical' ? '严重' : '警告'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={selectedAlert.status === 'pending' ? 'red' : selectedAlert.status === 'acknowledged' ? 'orange' : 'green'}>
                  {selectedAlert.status === 'pending' ? '待处理' : selectedAlert.status === 'acknowledged' ? '已确认' : '已处理'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="阈值">
                {selectedAlert.threshold_value} {selectedAlert.alert_type.includes('frequency') ? 'Hz' : 'mm'}
              </Descriptions.Item>
              <Descriptions.Item label="实际值" contentStyle={{ color: '#f5222d' }}>
                {selectedAlert.actual_value.toFixed(4)}
              </Descriptions.Item>
              <Descriptions.Item label="触发时间">
                {new Date(selectedAlert.created_at).toLocaleString()}
              </Descriptions.Item>
              {selectedAlert.note && (
                <Descriptions.Item label="备注">{selectedAlert.note}</Descriptions.Item>
              )}
            </Descriptions>

            <Divider />

            <div style={{ textAlign: 'center' }}>
              <Space>
                {selectedAlert.status === 'pending' && (
                  <Button type="primary" onClick={() => {
                    handleAcknowledge(selectedAlert)
                    setDetailVisible(false)
                  }}>
                    确认告警
                  </Button>
                )}
                {selectedAlert.status !== 'resolved' && (
                  <Button type="primary" danger onClick={() => {
                    handleResolve(selectedAlert)
                    setDetailVisible(false)
                  }}>
                    标记为已处理
                  </Button>
                )}
                <Button onClick={() => setDetailVisible(false)}>关闭</Button>
              </Space>
            </div>
          </>
        )}
      </Drawer>

      <Modal
        title={
          <Space>
            <SettingOutlined />
            设置告警阈值
          </Space>
        }
        open={thresholdModalVisible}
        onCancel={() => setThresholdModalVisible(false)}
        footer={null}
        width={500}
      >
        <Form form={thresholdForm} layout="vertical" onFinish={handleSetThreshold}>
          <Form.Item
            name="parameter_name"
            label="参数类型"
            rules={[{ required: true, message: '请选择参数类型' }]}
          >
            <Select placeholder="请选择">
              {Object.entries(alertTypeMap).map(([key, value]) => (
                <Option key={key} value={key}>{value.label}</Option>
              ))}
            </Select>
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="warning_threshold"
                label="预警阈值"
                rules={[{ required: true, message: '请输入预警阈值' }]}
              >
                <InputNumber style={{ width: '100%' }} step="0.001" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="critical_threshold"
                label="严重阈值"
                rules={[{ required: true, message: '请输入严重阈值' }]}
              >
                <InputNumber style={{ width: '100%' }} step="0.001" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            name="unit"
            label="单位"
          >
            <Select placeholder="请选择单位">
              <Option value="mm">mm</Option>
              <Option value="m/s^2">m/s^2</Option>
              <Option value="°C">°C</Option>
              <Option value="%">%</Option>
              <Option value="Hz">Hz</Option>
              <Option value="rad">rad</Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="description"
            label="描述"
          >
            <TextArea rows={3} placeholder="可选，输入阈值说明" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" block>保存配置</Button>
              <Button onClick={() => setThresholdModalVisible(false)} block>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default AlertCenter
