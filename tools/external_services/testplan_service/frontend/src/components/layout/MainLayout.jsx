import React, { useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  Layout,
  Menu,
  Button,
  Badge,
  Dropdown,
  Avatar,
  Space,
  Typography,
  Drawer,
  List,
  Card,
} from 'antd'
import {
  DashboardOutlined,
  FileImageOutlined,
  FileTextOutlined,
  BarChartOutlined,
  SettingOutlined,
  BellOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons'
import { useAppStore } from '../../store/appStore'
import Logo from '../common/Logo'

const { Header, Sider, Content } = Layout
const { Text } = Typography

const menuItems = [
  {
    key: 'dashboard',
    icon: <DashboardOutlined />,
    label: 'Dashboard',
    path: '/dashboard',
  },
  {
    key: 'pics',
    icon: <FileImageOutlined />,
    label: 'PICS Management',
    path: '/pics',
  },
  {
    key: 'testplan',
    icon: <FileTextOutlined />,
    label: 'Test Plan Generation',
    path: '/testplan',
  },
  {
    key: 'reports',
    icon: <BarChartOutlined />,
    label: 'Reports',
    path: '/reports',
  },
  {
    key: 'settings',
    icon: <SettingOutlined />,
    label: 'Settings',
    path: '/settings',
  },
]

const MainLayout = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const [notificationDrawer, setNotificationDrawer] = useState(false)
  
  const {
    sidebarCollapsed,
    toggleSidebar,
    user,
    notifications,
    markNotificationAsRead,
    removeNotification,
  } = useAppStore()

  const selectedKey = menuItems.find(item => location.pathname.includes(item.key))?.key || 'dashboard'
  const unreadCount = notifications.filter(n => !n.read).length

  const handleMenuClick = ({ key }) => {
    const item = menuItems.find(item => item.key === key)
    if (item) {
      navigate(item.path)
    }
  }

  const handleNotificationClick = (notification) => {
    if (!notification.read) {
      markNotificationAsRead(notification.id)
    }
  }

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'Profile',
    },
    {
      key: 'help',
      icon: <QuestionCircleOutlined />,
      label: 'Help & Support',
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Logout',
    },
  ]

  const handleUserMenuClick = ({ key }) => {
    switch (key) {
      case 'logout':
        // Handle logout
        console.log('Logout clicked')
        break
      case 'profile':
        navigate('/settings')
        break
      default:
        break
    }
  }

  return (
    <Layout style={{ minHeight: '100vh' }} hasSider>
      <Sider
        trigger={null}
        collapsible
        collapsed={sidebarCollapsed}
        width={260}
        collapsedWidth={80}
        style={{
          background: '#fff',
          boxShadow: '2px 0 8px rgba(0,0,0,0.1)',
          zIndex: 100,
        }}
      >
        <div style={{ padding: '16px', borderBottom: '1px solid #f0f0f0' }}>
          <Logo collapsed={sidebarCollapsed} />
        </div>
        
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{
            border: 'none',
            height: 'calc(100vh - 80px)',
            overflow: 'auto',
          }}
        />
      </Sider>
      
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 1px 4px rgba(0,21,41,.08)',
            zIndex: 99,
          }}
        >
          <Button
            type="text"
            icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={toggleSidebar}
            style={{
              fontSize: '16px',
              width: 40,
              height: 40,
            }}
          />
          
          <Space size="middle">
            <Badge count={unreadCount} size="small">
              <Button
                type="text"
                icon={<BellOutlined />}
                onClick={() => setNotificationDrawer(true)}
                style={{
                  fontSize: '16px',
                  width: 40,
                  height: 40,
                }}
              />
            </Badge>
            
            <Dropdown
              menu={{
                items: userMenuItems,
                onClick: handleUserMenuClick,
              }}
              placement="bottomRight"
              trigger={['click']}
            >
              <Space style={{ cursor: 'pointer' }}>
                <Avatar size="small" icon={<UserOutlined />} />
                <Text>{user.name}</Text>
              </Space>
            </Dropdown>
          </Space>
        </Header>
        
        <Content
          style={{
            padding: '24px',
            background: '#f5f5f5',
            minHeight: 'calc(100vh - 88px)',
            overflow: 'auto',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
      
      {/* Notification Drawer */}
      <Drawer
        title="Notifications"
        placement="right"
        onClose={() => setNotificationDrawer(false)}
        open={notificationDrawer}
        width={400}
      >
        <List
          dataSource={notifications}
          renderItem={(notification) => (
            <List.Item
              style={{
                padding: 0,
                marginBottom: 12,
              }}
            >
              <Card
                size="small"
                style={{
                  width: '100%',
                  cursor: 'pointer',
                  opacity: notification.read ? 0.7 : 1,
                }}
                onClick={() => handleNotificationClick(notification)}
                actions={[
                  <Button
                    type="link"
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation()
                      removeNotification(notification.id)
                    }}
                  >
                    Dismiss
                  </Button>
                ]}
              >
                <Card.Meta
                  title={
                    <Space>
                      <Text strong>{notification.title}</Text>
                      {!notification.read && (
                        <Badge status="processing" />
                      )}
                    </Space>
                  }
                  description={
                    <>
                      <Text>{notification.message}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {new Date(notification.timestamp).toLocaleString()}
                      </Text>
                    </>
                  }
                />
              </Card>
            </List.Item>
          )}
        />
      </Drawer>
    </Layout>
  )
}

export default MainLayout