import { Form, Input, Button, Card, App } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { authAPI } from '@/services/api'
import { useStore } from '@/store/useStore'
import './Login.scss'

interface LoginForm {
  username: string
  password: string
}

export default function Login() {
  const navigate = useNavigate()
  const { message } = App.useApp()
  const login = useStore(state => state.login)
  const [form] = Form.useForm()

  const handleSubmit = async (values: LoginForm) => {
    try {
      const response = await authAPI.login(values.username, values.password)
      const { access_token } = response.data
      
      localStorage.setItem('access_token', access_token)
      
      const userResponse = await authAPI.getCurrentUser()
      login(userResponse.data)
      
      message.success('登录成功')
      navigate('/')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '登录失败，请检查用户名和密码')
    }
  }

  return (
    <div className="login-container">
      <div className="login-bg"></div>
      <Card className="login-card" bordered={false}>
        <div className="login-header">
          <div className="login-logo">🏯</div>
          <h1 className="login-title">应县木塔</h1>
          <p className="login-subtitle">结构抗风抗震仿真与健康监测系统</p>
        </div>
        
        <Form
          form={form}
          onFinish={handleSubmit}
          layout="vertical"
          size="large"
        >
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="请输入用户名"
              autoComplete="username"
            />
          </Form.Item>
          
          <Form.Item
            name="password"
            label="密码"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="请输入密码"
              autoComplete="current-password"
            />
          </Form.Item>
          
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              block
              size="large"
              className="login-button"
            >
              登 录
            </Button>
          </Form.Item>
        </Form>
        
        <div className="login-footer">
          <p>默认账号: admin / admin123</p>
          <p>© 2024 古建保护研究中心</p>
        </div>
      </Card>
    </div>
  )
}
