import React, { useState } from 'react'
import {
  Row,
  Col,
  Card,
  Form,
  Input,
  Switch,
  Button,
  Select,
  Upload,
  Avatar,
  Divider,
  Typography,
  Space,
  Tabs,
  Table,
  Tag,
  Modal,
  message,
  Alert,
  Progress,
  List,
  Tooltip,
} from 'antd'
import {
  UserOutlined,
  UploadOutlined,
  SaveOutlined,
  ReloadOutlined,
  SecurityScanOutlined,
  SettingOutlined,
  BellOutlined,
  DatabaseOutlined,
  CloudOutlined,
  KeyOutlined,
  TeamOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
} from '@ant-design/icons'

const { Title, Text, Paragraph } = Typography
const { Option } = Select
const { TextArea } = Input
const { TabPane } = Tabs

const Settings = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [userModalVisible, setUserModalVisible] = useState(false)
  const [selectedUser, setSelectedUser] = useState(null)
  const [systemStatus, setSystemStatus] = useState({
    database: 'connected',
    storage: 'healthy',
    api: 'active',
    services: 'running',
  })

  // Mock data for users
  const [users, setUsers] = useState([
    {
      key: '1',
      id: 'USR001',
      name: 'John Doe',
      email: 'john.doe@company.com',
      role: 'Administrator',
      status: 'active',
      lastLogin: '2024-01-15 14:30',
    },
    {
      key: '2',
      id: 'USR002',
      name: 'Jane Smith',
      email: 'jane.smith@company.com',
      role: 'Test Engineer',
      status: 'active',
      lastLogin: '2024-01-15 13:45',
    },
    {
      key: '3',
      id: 'USR003',
      name: 'Bob Wilson',
      email: 'bob.wilson@company.com',
      role: 'Viewer',
      status: 'inactive',
      lastLogin: '2024-01-12 09:15',
    },
  ])

  const handleSaveProfile = (values) => {
    setLoading(true)
    setTimeout(() => {
      setLoading(false)
      message.success('Profile updated successfully')
    }, 1000)
  }

  const handleSaveSystem = (values) => {
    setLoading(true)
    setTimeout(() => {
      setLoading(false)
      message.success('System settings updated successfully')
    }, 1000)
  }

  const handleTestConnection = () => {
    setLoading(true)
    setTimeout(() => {
      setLoading(false)
      message.success('Database connection test successful')
    }, 2000)
  }

  const userColumns = [
    {
      title: 'User ID',
      dataIndex: 'id',
      key: 'id',
      render: (text) => <Text code>{text}</Text>,
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: 'Role',
      dataIndex: 'role',
      key: 'role',
      render: (role) => {
        const color = role === 'Administrator' ? 'red' : role === 'Test Engineer' ? 'blue' : 'green'
        return <Tag color={color}>{role}</Tag>
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'active' ? 'success' : 'default'}>
          {status.charAt(0).toUpperCase() + status.slice(1)}
        </Tag>
      ),
    },
    {
      title: 'Last Login',
      dataIndex: 'lastLogin',
      key: 'lastLogin',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title="Edit User">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => {
                setSelectedUser(record)
                setUserModalVisible(true)
              }}
            />
          </Tooltip>
          <Tooltip title="Delete User">
            <Button
              type="link"
              size="small"
              icon={<DeleteOutlined />}
              danger
              onClick={() => {
                Modal.confirm({
                  title: 'Delete User',
                  content: `Are you sure you want to delete user ${record.name}?`,
                  onOk: () => {
                    setUsers(users.filter(user => user.key !== record.key))
                    message.success('User deleted successfully')
                  },
                })
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
  ]

  const systemHealthItems = [
    {
      title: 'Database Connection',
      status: systemStatus.database,
      icon: <DatabaseOutlined />,
      description: 'PostgreSQL connection status',
    },
    {
      title: 'File Storage',
      status: systemStatus.storage,
      icon: <CloudOutlined />,
      description: 'File upload and storage system',
    },
    {
      title: 'API Services',
      status: systemStatus.api,
      icon: <SettingOutlined />,
      description: 'REST API endpoints availability',
    },
    {
      title: 'Background Services',
      status: systemStatus.services,
      icon: <SecurityScanOutlined />,
      description: 'Test execution and processing services',
    },
  ]

  return (
    <div>
      {/* Page Header */}
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>
          Settings
        </Title>
        <Text type="secondary">
          Configure system settings and user preferences
        </Text>
      </div>

      <Tabs defaultActiveKey="profile">
        {/* Profile Settings */}
        <TabPane tab={<span><UserOutlined />Profile</span>} key="profile">
          <Row gutter={24}>
            <Col xs={24} lg={8}>
              <Card title="Profile Picture">
                <div style={{ textAlign: 'center' }}>
                  <Avatar size={120} icon={<UserOutlined />} style={{ marginBottom: 16 }} />
                  <br />
                  <Upload
                    name="avatar"
                    showUploadList={false}
                    beforeUpload={() => false}
                    onChange={(info) => {
                      message.success('Avatar updated successfully')
                    }}
                  >
                    <Button icon={<UploadOutlined />}>Change Avatar</Button>
                  </Upload>
                </div>
              </Card>
            </Col>
            <Col xs={24} lg={16}>
              <Card title="Personal Information">
                <Form
                  form={form}
                  layout="vertical"
                  onFinish={handleSaveProfile}
                  initialValues={{
                    name: 'Admin User',
                    email: 'admin@testplan.com',
                    role: 'Administrator',
                    department: 'Test Engineering',
                    phone: '+1 (555) 123-4567',
                    timezone: 'UTC-5',
                    language: 'en',
                  }}
                >
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="name"
                        label="Full Name"
                        rules={[{ required: true, message: 'Please enter your name' }]}
                      >
                        <Input />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name="email"
                        label="Email Address"
                        rules={[
                          { required: true, message: 'Please enter your email' },
                          { type: 'email', message: 'Please enter a valid email' },
                        ]}
                      >
                        <Input />
                      </Form.Item>
                    </Col>
                  </Row>
                  
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="role" label="Role">
                        <Select disabled>
                          <Option value="Administrator">Administrator</Option>
                          <Option value="Test Engineer">Test Engineer</Option>
                          <Option value="Viewer">Viewer</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="department" label="Department">
                        <Input />
                      </Form.Item>
                    </Col>
                  </Row>
                  
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="phone" label="Phone Number">
                        <Input />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="timezone" label="Timezone">
                        <Select>
                          <Option value="UTC-8">UTC-8 (PST)</Option>
                          <Option value="UTC-5">UTC-5 (EST)</Option>
                          <Option value="UTC+0">UTC+0 (GMT)</Option>
                          <Option value="UTC+8">UTC+8 (CST)</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                  </Row>
                  
                  <Form.Item name="language" label="Language">
                    <Select>
                      <Option value="en">English</Option>
                      <Option value="zh">中文</Option>
                      <Option value="ja">日本語</Option>
                    </Select>
                  </Form.Item>
                  
                  <Form.Item>
                    <Button type="primary" htmlType="submit" loading={loading} icon={<SaveOutlined />}>
                      Save Profile
                    </Button>
                  </Form.Item>
                </Form>
              </Card>
            </Col>
          </Row>
        </TabPane>

        {/* System Settings */}
        <TabPane tab={<span><SettingOutlined />System</span>} key="system">
          <Row gutter={24}>
            <Col xs={24} lg={12}>
              <Card title="Database Configuration">
                <Form layout="vertical" onFinish={handleSaveSystem}>
                  <Form.Item name="dbHost" label="Database Host" initialValue="localhost">
                    <Input />
                  </Form.Item>
                  <Form.Item name="dbPort" label="Port" initialValue="5432">
                    <Input />
                  </Form.Item>
                  <Form.Item name="dbName" label="Database Name" initialValue="testplan_db">
                    <Input />
                  </Form.Item>
                  <Form.Item name="dbUsername" label="Username" initialValue="postgres">
                    <Input />
                  </Form.Item>
                  <Form.Item name="dbPassword" label="Password">
                    <Input.Password placeholder="Enter password" />
                  </Form.Item>
                  <Form.Item>
                    <Space>
                      <Button type="primary" htmlType="submit" loading={loading}>
                        Save Configuration
                      </Button>
                      <Button onClick={handleTestConnection} loading={loading}>
                        Test Connection
                      </Button>
                    </Space>
                  </Form.Item>
                </Form>
              </Card>
            </Col>
            
            <Col xs={24} lg={12}>
              <Card title="System Health">
                <List
                  dataSource={systemHealthItems}
                  renderItem={(item) => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={item.icon}
                        title={
                          <Space>
                            {item.title}
                            <Tag color={
                              item.status === 'connected' || item.status === 'healthy' || 
                              item.status === 'active' || item.status === 'running' 
                                ? 'success' : 'error'
                            }>
                              {item.status}
                            </Tag>
                          </Space>
                        }
                        description={item.description}
                      />
                    </List.Item>
                  )}
                />
              </Card>
              
              <Card title="Storage Usage" style={{ marginTop: 16 }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <Text>Test Plans: 2.4 GB / 10 GB</Text>
                    <Progress percent={24} />
                  </div>
                  <div>
                    <Text>PICS Files: 1.8 GB / 5 GB</Text>
                    <Progress percent={36} />
                  </div>
                  <div>
                    <Text>Reports: 0.9 GB / 3 GB</Text>
                    <Progress percent={30} />
                  </div>
                  <div>
                    <Text>Logs: 0.5 GB / 2 GB</Text>
                    <Progress percent={25} />
                  </div>
                </Space>
              </Card>
            </Col>
          </Row>
        </TabPane>

        {/* User Management */}
        <TabPane tab={<span><TeamOutlined />Users</span>} key="users">
          <Card
            title="User Management"
            extra={
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setSelectedUser(null)
                  setUserModalVisible(true)
                }}
              >
                Add User
              </Button>
            }
          >
            <Table
              columns={userColumns}
              dataSource={users}
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `Total ${total} users`,
              }}
            />
          </Card>
        </TabPane>

        {/* Notifications */}
        <TabPane tab={<span><BellOutlined />Notifications</span>} key="notifications">
          <Row gutter={24}>
            <Col span={24}>
              <Card title="Notification Settings">
                <Form layout="vertical">
                  <Title level={4}>Email Notifications</Title>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="emailTestComplete" valuePropName="checked" initialValue={true}>
                        <Space>
                          <Switch />
                          <Text>Test execution completed</Text>
                        </Space>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="emailTestFailed" valuePropName="checked" initialValue={true}>
                        <Space>
                          <Switch />
                          <Text>Test execution failed</Text>
                        </Space>
                      </Form.Item>
                    </Col>
                  </Row>
                  
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="emailReportGenerated" valuePropName="checked" initialValue={false}>
                        <Space>
                          <Switch />
                          <Text>Report generated</Text>
                        </Space>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="emailSystemAlert" valuePropName="checked" initialValue={true}>
                        <Space>
                          <Switch />
                          <Text>System alerts</Text>
                        </Space>
                      </Form.Item>
                    </Col>
                  </Row>
                  
                  <Divider />
                  
                  <Title level={4}>System Notifications</Title>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="browserNotifications" valuePropName="checked" initialValue={true}>
                        <Space>
                          <Switch />
                          <Text>Browser notifications</Text>
                        </Space>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="soundAlerts" valuePropName="checked" initialValue={false}>
                        <Space>
                          <Switch />
                          <Text>Sound alerts</Text>
                        </Space>
                      </Form.Item>
                    </Col>
                  </Row>
                  
                  <Form.Item>
                    <Button type="primary" icon={<SaveOutlined />}>
                      Save Notification Settings
                    </Button>
                  </Form.Item>
                </Form>
              </Card>
            </Col>
          </Row>
        </TabPane>

        {/* Security */}
        <TabPane tab={<span><SecurityScanOutlined />Security</span>} key="security">
          <Row gutter={24}>
            <Col xs={24} lg={12}>
              <Card title="Change Password">
                <Form layout="vertical">
                  <Form.Item
                    name="currentPassword"
                    label="Current Password"
                    rules={[{ required: true, message: 'Please enter current password' }]}
                  >
                    <Input.Password />
                  </Form.Item>
                  <Form.Item
                    name="newPassword"
                    label="New Password"
                    rules={[
                      { required: true, message: 'Please enter new password' },
                      { min: 8, message: 'Password must be at least 8 characters' },
                    ]}
                  >
                    <Input.Password />
                  </Form.Item>
                  <Form.Item
                    name="confirmPassword"
                    label="Confirm New Password"
                    dependencies={['newPassword']}
                    rules={[
                      { required: true, message: 'Please confirm new password' },
                      ({ getFieldValue }) => ({
                        validator(_, value) {
                          if (!value || getFieldValue('newPassword') === value) {
                            return Promise.resolve()
                          }
                          return Promise.reject(new Error('Passwords do not match'))
                        },
                      }),
                    ]}
                  >
                    <Input.Password />
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary" htmlType="submit">
                      Change Password
                    </Button>
                  </Form.Item>
                </Form>
              </Card>
            </Col>
            
            <Col xs={24} lg={12}>
              <Card title="Security Settings">
                <Form layout="vertical">
                  <Form.Item name="twoFactor" valuePropName="checked" initialValue={false}>
                    <Space>
                      <Switch />
                      <Text>Enable Two-Factor Authentication</Text>
                    </Space>
                  </Form.Item>
                  
                  <Form.Item name="sessionTimeout" label="Session Timeout" initialValue="60">
                    <Select>
                      <Option value="30">30 minutes</Option>
                      <Option value="60">1 hour</Option>
                      <Option value="120">2 hours</Option>
                      <Option value="480">8 hours</Option>
                    </Select>
                  </Form.Item>
                  
                  <Form.Item name="ipRestriction" valuePropName="checked" initialValue={false}>
                    <Space>
                      <Switch />
                      <Text>Enable IP Address Restriction</Text>
                    </Space>
                  </Form.Item>
                  
                  <Form.Item>
                    <Button type="primary">
                      Save Security Settings
                    </Button>
                  </Form.Item>
                </Form>
              </Card>
              
              <Alert
                message="Security Recommendations"
                description={
                  <ul>
                    <li>Use a strong password with at least 8 characters</li>
                    <li>Enable two-factor authentication for better security</li>
                    <li>Regularly review user access and permissions</li>
                    <li>Keep the system updated with latest security patches</li>
                  </ul>
                }
                type="info"
                showIcon
                style={{ marginTop: 16 }}
              />
            </Col>
          </Row>
        </TabPane>
      </Tabs>

      {/* User Modal */}
      <Modal
        title={selectedUser ? 'Edit User' : 'Add New User'}
        open={userModalVisible}
        onCancel={() => setUserModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          layout="vertical"
          initialValues={selectedUser}
          onFinish={(values) => {
            if (selectedUser) {
              setUsers(users.map(user => 
                user.key === selectedUser.key ? { ...user, ...values } : user
              ))
              message.success('User updated successfully')
            } else {
              const newUser = {
                ...values,
                key: Date.now().toString(),
                id: `USR${String(users.length + 1).padStart(3, '0')}`,
                lastLogin: 'Never',
              }
              setUsers([...users, newUser])
              message.success('User added successfully')
            }
            setUserModalVisible(false)
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="Full Name"
                rules={[{ required: true, message: 'Please enter user name' }]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="email"
                label="Email Address"
                rules={[
                  { required: true, message: 'Please enter email' },
                  { type: 'email', message: 'Please enter valid email' },
                ]}
              >
                <Input />
              </Form.Item>
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="role"
                label="Role"
                rules={[{ required: true, message: 'Please select role' }]}
              >
                <Select>
                  <Option value="Administrator">Administrator</Option>
                  <Option value="Test Engineer">Test Engineer</Option>
                  <Option value="Viewer">Viewer</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="status"
                label="Status"
                rules={[{ required: true, message: 'Please select status' }]}
              >
                <Select>
                  <Option value="active">Active</Option>
                  <Option value="inactive">Inactive</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {selectedUser ? 'Update User' : 'Add User'}
              </Button>
              <Button onClick={() => setUserModalVisible(false)}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Settings