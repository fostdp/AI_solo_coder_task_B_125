import { Layout, Menu, Avatar, Dropdown, Badge } from 'antd'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  DashboardOutlined,
  MonitorOutlined,
  ThunderboltOutlined,
  AlertOutlined,
  BarChartOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  BellOutlined
} from '@ant-design/icons'
import { useStore } from '@/store/useStore'
import { wsService } from '@/services/websocket'
import type { MenuProps } from 'antd'
import './MainLayout.scss'

const { Header, Sider, Content } = Layout

const menuItems: MenuProps['items'] = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: '总览仪表盘'
  },
  {
    key: '/realtime',
    icon: <MonitorOutlined />,
    label: '实时监测'
  },
  {
    key: '/simulation',
    icon: <ThunderboltOutlined />,
    label: '结构仿真'
  },
  {
    key: '/damage',
    icon: <AlertOutlined />,
    label: '损伤识别'
  },
  {
    key: '/alerts',
    icon: <BellOutlined />,
    label: '告警中心'
  },
  {
    key: '/analysis',
    icon: <BarChartOutlined />,
    label: '数据分析'
  },
  {
    key: '/settings',
    icon: <SettingOutlined />,
    label: '系统设置'
  }
]

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, unreadAlertCount, wsConnectionStatus } = useStore()

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    navigate(key)
  }

  const handleLogout = () => {
    logout()
    wsService.disconnectAll()
    navigate('/login')
  }

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人中心'
    },
    {
      type: 'divider'
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout
    }
  ]

  return (
    <Layout className="main-layout">
      <Sider width={220} theme="dark" className="layout-sider">
        <div className="logo">
          <div className="logo-icon">🏯</div>
          <div className="logo-text">应县木塔监测</div>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout>
        <Header className="layout-header">
          <div className="header-left">
            <div className={`connection-status status-${wsConnectionStatus}`}>
              <span className="status-dot"></span>
              <span>{wsConnectionStatus === 'connected' ? '已连接' : wsConnectionStatus === 'connecting' ? '连接中...' : '已断开'}</span>
            </div>
          </div>
          <div className="header-right">
            <Badge count={unreadAlertCount} size="small">
              <div className="header-icon" onClick={() => navigate('/alerts')}>
                <BellOutlined />
              </div>
            </Badge>
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <div className="user-info">
                <Avatar size="small" icon={<UserOutlined />} />
                <span className="username">{user?.username || '用户'}</span>
              </div>
            </Dropdown>
          </div>
        </Header>
        <Content className="layout-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
