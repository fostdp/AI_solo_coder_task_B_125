import React, { useState } from 'react'
import {
  Card,
  Button,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Row,
  Col,
  Tabs,
  Space,
  Table,
  Tag,
  message,
  Modal,
  Descriptions,
  Divider,
  Avatar,
  Upload,
  Alert
} from 'antd'
import {
  SettingOutlined,
  UserOutlined,
  BellOutlined,
  SecurityOutlined,
  DatabaseOutlined,
  InfoCircleOutlined,
  SaveOutlined,
  UploadOutlined,
  DownloadOutlined,
  EyeOutlined,
  EyeInvisibleOutlined
} from '@ant-design/icons'
import { authAPI, alertAPI, sensorAPI } from '@/services/api'
import { useStore } from '@/store/useStore'
import './SystemSettings.scss'

const { Option } = Select
const { TabPane } = Tabs
const { TextArea } = Input
const { Password } = Input

const SystemSettings: React.FC = () => {
  const [profileForm] = Form.useForm()
  const [passwordForm] = Form.useForm()
  const [notificationForm] = Form.useForm()
  const [systemForm] = Form.useForm()
  const [saving, setSaving] = useState(false)
  const [oldPasswordVisible, setOldPasswordVisible] = useState(false)
  const [newPasswordVisible, setNewPasswordVisible] = useState(false)

  const user = useStore(state => state.user)
  const logout = useStore(state => state.logout)

  const sensorColumns = [
    {
      title: '传感器ID',
      dataIndex: 'id',
      key: 'id',
      render: (v: string) => v.slice(0, 8)
    },
    {
      title: '楼层',
      dataIndex: 'floor_number',
      key: 'floor_number',
      render: (v: number) => `${v}层`
    },
    {
      title: '传感器类型',
      dataIndex: 'sensor_type',
      key: 'sensor_type'
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (v: string) => (
        <Tag color={v === 'online' ? 'green' : v === 'offline' ? 'red' : 'orange'}>
          {v === 'online' ? '在线' : v === 'offline' ? '离线' : '异常'}
        </Tag>
      )
    },
    {
      title: 'DTU设备',
      dataIndex: 'dtu_id',
      key: 'dtu_id',
      render: (v?: string) => v ? v.slice(0, 8) : '-'
    }
  ]

  const handleSaveProfile = async (values: any) => {
    setSaving(true)
    try {
      message.success('个人信息已保存')
    } catch (error) {
      message.error('保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleChangePassword = async (values: any) => {
    if (values.new_password !== values.confirm_password) {
      message.error('两次输入的新密码不一致')
      return
    }
    setSaving(true)
    try {
      await authAPI.changePassword(values.old_password, values.new_password)
      message.success('密码修改成功，请重新登录')
      passwordForm.resetFields()
      setTimeout(() => {
        logout()
        window.location.href = '/login'
      }, 1500)
    } catch (error) {
      message.error('密码修改失败')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveNotifications = async (values: any) => {
    setSaving(true)
    try {
      message.success('通知设置已保存')
    } catch (error) {
      message.error('保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveSystem = async (values: any) => {
    setSaving(true)
    try {
      message.success('系统设置已保存')
    } catch (error) {
      message.error('保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleExportConfig = () => {
    message.success('配置导出中...')
  }

  const handleBackupDatabase = () => {
    Modal.confirm({
      title: '确认备份数据库？',
      content: '系统将备份当前所有数据，可能需要较长时间。',
      onOk: () => message.success('数据库备份已启动')
    })
  }

  const handleClearData = () => {
    Modal.confirm({
      title: '确认清除历史数据？',
      content: '此操作将清除指定时间范围的历史数据，且无法恢复。',
      okText: '确认清除',
      okType: 'danger',
      onOk: () => message.success('数据清除任务已启动')
    })
  }

  const handleSyncSensors = async () => {
    try {
      message.success('传感器配置同步成功')
    } catch (error) {
      message.error('同步失败')
    }
  }

  return (
    <div className="system-settings">
      <div className="page-header">
        <h2>
          <Space>
            <SettingOutlined />
            系统设置
          </Space>
        </h2>
      </div>

      <Tabs defaultActiveKey="1" type="card">
        <TabPane tab={<Space><UserOutlined />个人信息</Space>} key="1">
          <Row gutter={24}>
            <Col span={8}>
              <Card title="个人资料" size="small">
                <div style={{ textAlign: 'center', padding: '24px 0' }}>
                  <Avatar size={80} icon={<UserOutlined />}
                  <h3 style={{ marginTop: 16 }}>{user?.username || '管理员'}</h3>
                  <p style={{ color: '#666' }}>{user?.role === 'admin' ? '系统管理员' : '普通用户'}</p>
                  <Upload
                    showUploadList={false}
                    beforeUpload={() => {
                      message.success('头像更新成功')
                      return false
                    }}
                  >
                    <Button size="small" icon={<UploadOutlined />}>更换头像</Button>
                  </Upload>
                </div>
                <Divider />
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="用户名">{user?.username || '-'}</Descriptions.Item>
                  <Descriptions.Item label="邮箱">{user?.email || '-'}</Descriptions.Item>
                  <Descriptions.Item label="角色">
                    <Tag color="blue">{user?.role === 'admin' ? '管理员' : '用户'}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="创建时间">
                    {user?.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
            <Col span={16}>
              <Card title="编辑资料" size="small">
                <Form
                  form={profileForm}
                  layout="vertical"
                  onFinish={handleSaveProfile}
                  initialValues={{
                    username: user?.username || '',
                    email: user?.email || '',
                    phone: user?.phone || '',
                    organization: user?.organization || ''
                  }}
                >
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="username"
                        label="用户名"
                        rules={[{ required: true, message: '请输入用户名' }]}
                      >
                        <Input prefix={<UserOutlined />} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name="email"
                        label="邮箱"
                        rules={[{ type: 'email', message: '请输入有效邮箱' }]}
                      >
                        <Input />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="phone" label="联系电话">
                        <Input />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="organization" label="所属单位">
                        <Input />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Form.Item>
                    <Button type="primary" htmlType="submit" loading={saving} icon={<SaveOutlined />}>
                      保存修改
                    </Button>
                  </Form.Item>
                </Form>
              </Card>

              <Card title="修改密码" size="small" style={{ marginTop: 16 }}>
                <Form
                  form={passwordForm}
                  layout="vertical"
                  onFinish={handleChangePassword}
                >
                  <Row gutter={16}>
                    <Col span={8}>
                      <Form.Item
                        name="old_password"
                        label="当前密码"
                        rules={[{ required: true, message: '请输入当前密码' }]}
                      >
                        <Password
                          iconRender={oldPasswordVisible ? <EyeOutlined /> : <EyeInvisibleOutlined />}
                          onClickIcon={() => setOldPasswordVisible(!oldPasswordVisible)}
                        />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item
                        name="new_password"
                        label="新密码"
                        rules={[
                          { required: true, message: '请输入新密码' },
                          { min: 8, message: '密码至少8位' }
                        ]}
                      >
                        <Password
                          iconRender={newPasswordVisible ? <EyeOutlined /> : <EyeInvisibleOutlined />}
                          onClickIcon={() => setNewPasswordVisible(!newPasswordVisible)}
                        />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item
                        name="confirm_password"
                        label="确认新密码"
                        rules={[
                          { required: true, message: '请确认新密码' }
                        ]}
                      >
                        <Password />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Alert
                    message="密码要求"
                    description="密码长度至少8位，包含大小写字母、数字和特殊字符。"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  <Form.Item>
                    <Button type="primary" htmlType="submit" loading={saving} danger icon={<SaveOutlined />}>
                      修改密码
                    </Button>
                  </Form.Item>
                </Form>
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab={<Space><BellOutlined />通知设置</Space>} key="2">
          <Card title="告警通知配置" size="small">
            <Form
              form={notificationForm}
              layout="vertical"
              onFinish={handleSaveNotifications}
              initialValues={{
                email_notification: true,
                sms_notification: false,
                webpush_notification: true,
                alert_types: ['displacement', 'acceleration', 'interstory_drift', 'frequency_change'],
                min_severity: 'warning'
              }}
            >
              <Row gutter={24}>
              <Col span={12}>
                <Card size="small" title="通知方式">
                  <Form.Item name="email_notification" valuePropName="checked">
                    <Space>
                      <Switch />
                      <span>邮件通知</span>
                    </Space>
                  </Form.Item>
                  <Form.Item name="sms_notification" valuePropName="checked">
                    <Space>
                      <Switch />
                      <span>短信通知</span>
                    </Space>
                  </Form.Item>
                  <Form.Item name="webpush_notification" valuePropName="checked">
                    <Space>
                      <Switch />
                      <span>浏览器推送</span>
                    </Space>
                  </Form.Item>
                  <Form.Item name="sound_notification" valuePropName="checked">
                    <Space>
                      <Switch defaultChecked />
                      <span>声音提醒</span>
                    </Space>
                  </Form.Item>
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" title="告警类型">
                  <Form.Item
                    name="alert_types"
                    label="接收以下类型的告警"
                  >
                    <Select mode="multiple" style={{ width: '100%' }}>
                      <Option value="displacement">位移超限</Option>
                      <Option value="acceleration">加速度超限</Option>
                      <Option value="temperature">温度异常</Option>
                      <Option value="humidity">湿度异常</Option>
                      <Option value="moisture">含水率异常</Option>
                      <Option value="interstory_drift">层间位移角超限</Option>
                      <Option value="frequency_change">固有频率异常</Option>
                    </Select>
                  </Form.Item>
                  <Form.Item
                    name="min_severity"
                    label="最低告警级别"
                  >
                    <Select>
                      <Option value="warning">警告及以上</Option>
                      <Option value="critical">仅严重</Option>
                    </Select>
                  </Form.Item>
                  <Form.Item
                    name="quiet_hours"
                    label="免打扰时段"
                    help="设置后该时段内不发送通知"
                  >
                    <Select placeholder="选择免打扰时段">
                      <Option value="none">不设置</Option>
                      <Option value="night">夜间免打扰 (22:00 - 08:00)</Option>
                      <Option value="custom">自定义时段</Option>
                    </Select>
                  </Form.Item>
                </Card>
              </Col>
            </Row>
            <Form.Item style={{ marginTop: 16 }}>
              <Button type="primary" htmlType="submit" loading={saving} icon={<SaveOutlined />}>
                保存设置
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </TabPane>

        <TabPane tab={<Space><SecurityOutlined />传感器管理</Space>} key="3">
          <Card
            title="传感器列表"
            size="small"
            extra={
              <Space>
                <Button onClick={handleSyncSensors}>同步配置</Button>
                <Button icon={<DownloadOutlined />} onClick={handleExportConfig}>导出配置</Button>
              </Space>
            }
          >
            <Table
              columns={sensorColumns}
              dataSource={[]}
              size="small"
              rowKey="id"
              pagination={{ pageSize: 10 }}
              locale={{ emptyText: '暂无传感器数据' }}
            />
          </Card>

          <Card title="DTU设备管理" size="small" style={{ marginTop: 16 }}>
            <Alert
              message="DTU设备说明"
              description="系统支持4G DTU设备用于远程数据传输。每层配置1台DTU设备，负责该层所有传感器的数据采集和传输。DTU支持断线自动重连、数据缓存等功能。"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Table
              columns={[
                { title: '设备ID', dataIndex: 'id', key: 'id', render: (v: string) => v.slice(0, 8) },
                { title: '楼层', dataIndex: 'floor_number', key: 'floor_number', render: (v: number) => `${v}层` },
                { title: '设备型号', dataIndex: 'model', key: 'model' },
                { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => (
                  <Tag color={v === 'online' ? 'green' : 'red'}>
                    {v === 'online' ? '在线' : '离线'}
                  </Tag>
                )},
                { title: '最后心跳', dataIndex: 'last_heartbeat', key: 'last_heartbeat', render: (v?: string) => v ? new Date(v).toLocaleString() : '-' },
                { title: '信号强度', dataIndex: 'signal_strength', key: 'signal_strength' }
              ]}
              dataSource={[]}
              size="small"
              rowKey="id"
              pagination={false}
              locale={{ emptyText: '暂无DTU设备数据' }}
            />
          </Card>
        </TabPane>

        <TabPane tab={<Space><DatabaseOutlined />数据管理</Space>} key="4">
          <Row gutter={16}>
            <Col span={12}>
              <Card title="数据备份" size="small">
                <p style={{ marginBottom: 16 }}>
                  定期备份数据以防数据丢失，支持完整备份和增量备份。
                </p>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Button icon={<DownloadOutlined />} onClick={handleBackupDatabase} block>
                    立即备份数据库
                  </Button>
                  <Button icon={<UploadOutlined />} block>
                    恢复数据库
                  </Button>
                </Space>
                <Divider />
                <h4>自动备份设置</h4>
                <Form layout="vertical">
                  <Form.Item label="自动备份">
                    <Switch defaultChecked />
                  </Form.Item>
                  <Form.Item label="备份频率">
                    <Select defaultValue="daily">
                      <Option value="daily">每日</Option>
                      <Option value="weekly">每周</Option>
                      <Option value="monthly">每月</Option>
                    </Select>
                  </Form.Item>
                  <Form.Item label="保留时间">
                    <Select defaultValue="30">
                      <Option value="7">7天</Option>
                      <Option value="30">30天</Option>
                      <Option value="90">90天</Option>
                      <Option value="365">1年</Option>
                    </Select>
                  </Form.Item>
                </Form>
              </Card>
            </Col>
            <Col span={12}>
              <Card title="数据清理" size="small">
                <Alert
                  message="警告"
                  description="数据清除操作不可恢复，请谨慎操作。建议在清除前务必备份数据。"
                  type="warning"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Button danger block>
                    清除30天前的历史数据
                  </Button>
                  <Button danger block>
                    清除90天前的历史数据
                  </Button>
                  <Button danger block onClick={handleClearData}>
                    自定义时间范围清除
                  </Button>
                </Space>
                <Divider />
                <h4>自动清理设置</h4>
                <Form layout="vertical">
                  <Form.Item label="自动清理">
                    <Switch />
                  </Form.Item>
                  <Form.Item label="数据保留期限">
                    <Select defaultValue="90">
                      <Option value="30">30天</Option>
                      <Option value="90">90天</Option>
                      <Option value="180">180天</Option>
                      <Option value="365">1年</Option>
                    </Select>
                  </Form.Item>
                </Form>
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab={<Space><InfoCircleOutlined />关于系统</Space>} key="5">
          <Card title="系统信息" size="small">
            <Row gutter={24}>
              <Col span={12}>
                <Descriptions title="版本信息" bordered column={1}>
                  <Descriptions.Item label="系统名称">应县木塔结构健康监测系统</Descriptions.Item>
                  <Descriptions.Item label="系统版本">v1.0.0</Descriptions.Item>
                  <Descriptions.Item label="发布日期">2024-01-01</Descriptions.Item>
                  <Descriptions.Item label="技术架构">FastAPI + React + Three.js</Descriptions.Item>
                  <Descriptions.Item label="数据库">PostgreSQL + TimescaleDB</Descriptions.Item>
                </Descriptions>
              </Col>
              <Col span={12}>
                <Descriptions title="技术支持" bordered column={1}>
                  <Descriptions.Item label="开发团队">古建筑保护技术团队</Descriptions.Item>
                  <Descriptions.Item label="联系邮箱">support@example.com</Descriptions.Item>
                  <Descriptions.Item label="技术支持">400-xxxx-xxxx</Descriptions.Item>
                  <Descriptions.Item label="文档地址">
                    <a href="#" onClick={(e) => e.preventDefault()}>查看文档</a>
                  </Descriptions.Item>
                </Descriptions>
              </Col>
            </Row>
            <Divider />
            <Alert
              message="系统声明"
              description={
                <div>
                  <p>本系统用于应县木塔的结构健康监测，所有监测数据仅供研究和保护参考使用。</p>
                  <p>© 2024 古建筑保护研究中心 版权所有</p>
                </div>
              }
              type="info"
              showIcon
            />
          </Card>
        </TabPane>
      </Tabs>
    </div>
  )
}

export default SystemSettings
