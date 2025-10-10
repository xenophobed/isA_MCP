import React, { useState, useEffect } from 'react'
import {
  Row,
  Col,
  Card,
  Statistic,
  Progress,
  Table,
  Tag,
  Space,
  Button,
  Typography,
  Divider,
  Timeline,
  Avatar,
  List,
} from 'antd'
import {
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  FileTextOutlined,
  ReloadOutlined,
  EyeOutlined,
  DownloadOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { Line, Column, Pie } from '@ant-design/charts'

const { Title, Text } = Typography

const Dashboard = () => {
  const [loading, setLoading] = useState(false)
  
  // Mock data - replace with real API calls
  const stats = {
    running: 12,
    completed: 156,
    failed: 8,
    total: 176,
  }

  const recentTests = [
    {
      key: '1',
      name: '5G NR PHY Layer Tests',
      status: 'running',
      progress: 75,
      startTime: '2024-01-15 09:30',
      duration: '2h 15m',
    },
    {
      key: '2',
      name: 'LTE RRC Connection Tests',
      status: 'completed',
      progress: 100,
      startTime: '2024-01-15 08:00',
      duration: '1h 45m',
    },
    {
      key: '3',
      name: 'NR SA Handover Tests',
      status: 'failed',
      progress: 45,
      startTime: '2024-01-15 07:30',
      duration: '0h 32m',
    },
    {
      key: '4',
      name: 'VoNR Call Flow Tests',
      status: 'completed',
      progress: 100,
      startTime: '2024-01-14 16:20',
      duration: '3h 10m',
    },
  ]

  const activityData = [
    {
      time: '09:00',
      tests: 12,
      completed: 8,
    },
    {
      time: '10:00',
      tests: 18,
      completed: 15,
    },
    {
      time: '11:00',
      tests: 25,
      completed: 22,
    },
    {
      time: '12:00',
      tests: 30,
      completed: 28,
    },
    {
      time: '13:00',
      tests: 28,
      completed: 25,
    },
    {
      time: '14:00',
      tests: 35,
      completed: 32,
    },
  ]

  const testTypeData = [
    { type: '5G NR', value: 45, percentage: 35 },
    { type: 'LTE', value: 38, percentage: 30 },
    { type: 'VoNR', value: 25, percentage: 20 },
    { type: 'VoLTE', value: 19, percentage: 15 },
  ]

  const recentActivity = [
    {
      action: 'Test Plan Generated',
      description: '5G_NR_PHY_Layer_v2.1 test plan created',
      time: '10 minutes ago',
      type: 'success',
    },
    {
      action: 'PICS File Uploaded',
      description: 'Updated PICS configuration for UE Category 6',
      time: '25 minutes ago',
      type: 'info',
    },
    {
      action: 'Test Execution Failed',
      description: 'NR_SA_Handover_Test_Case_12 failed with timeout error',
      time: '1 hour ago',
      type: 'error',
    },
    {
      action: 'Report Generated',
      description: 'Daily execution report for 2024-01-15',
      time: '2 hours ago',
      type: 'success',
    },
  ]

  const columns = [
    {
      title: 'Test Plan Name',
      dataIndex: 'name',
      key: 'name',
      render: (text) => (
        <Space>
          <FileTextOutlined />
          <Text strong>{text}</Text>
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const statusConfig = {
          running: { color: 'processing', icon: <PlayCircleOutlined />, text: 'Running' },
          completed: { color: 'success', icon: <CheckCircleOutlined />, text: 'Completed' },
          failed: { color: 'error', icon: <CloseCircleOutlined />, text: 'Failed' },
        }
        const config = statusConfig[status]
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        )
      },
    },
    {
      title: 'Progress',
      dataIndex: 'progress',
      key: 'progress',
      render: (progress, record) => (
        <Progress
          percent={progress}
          size="small"
          status={record.status === 'failed' ? 'exception' : 'normal'}
          showInfo={false}
          style={{ width: 100 }}
        />
      ),
    },
    {
      title: 'Start Time',
      dataIndex: 'startTime',
      key: 'startTime',
    },
    {
      title: 'Duration',
      dataIndex: 'duration',
      key: 'duration',
    },
    {
      title: 'Action',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" icon={<EyeOutlined />}>
            View
          </Button>
          {record.status === 'completed' && (
            <Button type="link" size="small" icon={<DownloadOutlined />}>
              Download
            </Button>
          )}
        </Space>
      ),
    },
  ]

  const lineConfig = {
    data: activityData,
    xField: 'time',
    yField: 'tests',
    seriesField: 'type',
    smooth: true,
    animation: {
      appear: {
        animation: 'path-in',
        duration: 2000,
      },
    },
  }

  const columnConfig = {
    data: testTypeData,
    xField: 'type',
    yField: 'value',
    colorField: 'type',
    color: ['#2563EB', '#10B981', '#F59E0B', '#EF4444'],
    animation: {
      appear: {
        animation: 'grow-in-y',
        duration: 1000,
      },
    },
  }

  const handleRefresh = () => {
    setLoading(true)
    setTimeout(() => {
      setLoading(false)
    }, 1000)
  }

  return (
    <div>
      {/* Page Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={2} style={{ margin: 0 }}>
              Dashboard
            </Title>
            <Text type="secondary">
              Overview of test execution status and system metrics
            </Text>
          </div>
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            loading={loading}
            onClick={handleRefresh}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Running Tests"
              value={stats.running}
              prefix={<PlayCircleOutlined style={{ color: '#1890ff' }} />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Completed"
              value={stats.completed}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Failed"
              value={stats.failed}
              prefix={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Tests"
              value={stats.total}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts and Tables */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="Recent Test Executions" style={{ marginBottom: 16 }}>
            <Table
              columns={columns}
              dataSource={recentTests}
              pagination={false}
              size="small"
            />
          </Card>
          
          <Card title="Test Activity Trend">
            <Line {...lineConfig} height={300} />
          </Card>
        </Col>
        
        <Col xs={24} lg={8}>
          <Card title="Test Distribution by Type" style={{ marginBottom: 16 }}>
            <Column {...columnConfig} height={250} />
          </Card>
          
          <Card title="Recent Activity">
            <Timeline
              items={recentActivity.map((item, index) => ({
                color: item.type === 'error' ? 'red' : item.type === 'success' ? 'green' : 'blue',
                children: (
                  <div key={index}>
                    <Text strong>{item.action}</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {item.description}
                    </Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: '11px' }}>
                      <ClockCircleOutlined /> {item.time}
                    </Text>
                  </div>
                ),
              }))}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard