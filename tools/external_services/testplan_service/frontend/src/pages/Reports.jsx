import React, { useState, useEffect } from 'react'
import {
  Row,
  Col,
  Card,
  Select,
  DatePicker,
  Button,
  Table,
  Tag,
  Space,
  Typography,
  Statistic,
  Tabs,
  List,
  Progress,
  Tooltip,
  Dropdown,
  Menu,
} from 'antd'
import {
  DownloadOutlined,
  PrinterOutlined,
  ShareAltOutlined,
  FilterOutlined,
  ReloadOutlined,
  FileExcelOutlined,
  FilePdfOutlined,
  BarChartOutlined,
  PieChartOutlined,
  LineChartOutlined,
} from '@ant-design/icons'
import { Line, Column, Pie, Area, DualAxes } from '@ant-design/charts'
import dayjs from 'dayjs'

const { Title, Text } = Typography
const { Option } = Select
const { RangePicker } = DatePicker
const { TabPane } = Tabs

const Reports = () => {
  const [loading, setLoading] = useState(false)
  const [dateRange, setDateRange] = useState([dayjs().subtract(30, 'day'), dayjs()])
  const [selectedStandard, setSelectedStandard] = useState('all')
  const [reportType, setReportType] = useState('overview')

  // Mock data for reports
  const testExecutionData = [
    { date: '2024-01-01', passed: 85, failed: 12, total: 97 },
    { date: '2024-01-02', passed: 92, failed: 8, total: 100 },
    { date: '2024-01-03', passed: 78, failed: 15, total: 93 },
    { date: '2024-01-04', passed: 95, failed: 5, total: 100 },
    { date: '2024-01-05', passed: 88, failed: 10, total: 98 },
    { date: '2024-01-06', passed: 91, failed: 7, total: 98 },
    { date: '2024-01-07', passed: 83, failed: 14, total: 97 },
  ]

  const testCategoryData = [
    { category: 'Physical Layer', count: 156, percentage: 35, passed: 142, failed: 14 },
    { category: 'MAC Layer', count: 124, percentage: 28, passed: 118, failed: 6 },
    { category: 'RRC Layer', count: 98, percentage: 22, passed: 89, failed: 9 },
    { category: 'NAS', count: 67, percentage: 15, passed: 62, failed: 5 },
  ]

  const performanceData = [
    { time: '00:00', avgDuration: 12.5, testCount: 8 },
    { time: '04:00', avgDuration: 11.8, testCount: 12 },
    { time: '08:00', avgDuration: 15.2, testCount: 25 },
    { time: '12:00', avgDuration: 14.7, testCount: 30 },
    { time: '16:00', avgDuration: 13.9, testCount: 28 },
    { time: '20:00', avgDuration: 12.1, testCount: 15 },
  ]

  const complianceData = [
    { standard: '3GPP TS 38.101-1', total: 245, passed: 232, failed: 13, compliance: 94.7 },
    { standard: '3GPP TS 38.101-2', total: 189, passed: 175, failed: 14, compliance: 92.6 },
    { standard: '3GPP TS 36.523-1', total: 312, passed: 298, failed: 14, compliance: 95.5 },
    { standard: '3GPP TS 34.123-1', total: 156, passed: 148, failed: 8, compliance: 94.9 },
  ]

  const recentReports = [
    {
      id: 'RPT_001',
      name: 'Daily Execution Report - 2024-01-15',
      type: 'Daily',
      generated: '2024-01-15 23:30',
      size: '2.3 MB',
      format: 'PDF',
      status: 'completed',
    },
    {
      id: 'RPT_002',
      name: 'Weekly Compliance Report - Week 2',
      type: 'Weekly',
      generated: '2024-01-14 18:00',
      size: '4.7 MB',
      format: 'Excel',
      status: 'completed',
    },
    {
      id: 'RPT_003',
      name: 'Performance Analysis Report',
      type: 'Custom',
      generated: '2024-01-14 14:22',
      size: '1.8 MB',
      format: 'PDF',
      status: 'completed',
    },
  ]

  const failureAnalysisData = [
    { reason: 'Timeout', count: 45, percentage: 35 },
    { reason: 'Configuration Error', count: 28, percentage: 22 },
    { reason: 'Signal Issue', count: 22, percentage: 17 },
    { reason: 'Protocol Error', count: 18, percentage: 14 },
    { reason: 'Hardware Failure', count: 15, percentage: 12 },
  ]

  // Chart configurations
  const executionTrendConfig = {
    data: testExecutionData,
    xField: 'date',
    yField: 'value',
    seriesField: 'type',
    color: ['#52c41a', '#ff4d4f', '#1890ff'],
    smooth: true,
    animation: {
      appear: {
        animation: 'path-in',
        duration: 2000,
      },
    },
  }

  const categoryDistributionConfig = {
    data: testCategoryData,
    angleField: 'count',
    colorField: 'category',
    radius: 0.8,
    label: {
      type: 'outer',
      content: '{name} ({percentage}%)',
    },
    interactions: [{ type: 'element-active' }],
  }

  const performanceTrendConfig = {
    data: performanceData,
    xField: 'time',
    yField: ['avgDuration', 'testCount'],
    geometryOptions: [
      {
        geometry: 'line',
        color: '#5B8FF9',
      },
      {
        geometry: 'line',
        color: '#5AD8A6',
      },
    ],
  }

  const failureAnalysisConfig = {
    data: failureAnalysisData,
    xField: 'count',
    yField: 'reason',
    seriesField: 'reason',
    color: ['#ff4d4f', '#ff7a45', '#ffa940', '#ffec3d', '#bae637'],
    legend: false,
  }

  const reportColumns = [
    {
      title: 'Report Name',
      dataIndex: 'name',
      key: 'name',
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      render: (type) => <Tag color="blue">{type}</Tag>,
    },
    {
      title: 'Generated',
      dataIndex: 'generated',
      key: 'generated',
    },
    {
      title: 'Size',
      dataIndex: 'size',
      key: 'size',
    },
    {
      title: 'Format',
      dataIndex: 'format',
      key: 'format',
      render: (format) => (
        <Tag color={format === 'PDF' ? 'red' : 'green'}>
          {format === 'PDF' ? <FilePdfOutlined /> : <FileExcelOutlined />}
          {format}
        </Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" icon={<DownloadOutlined />}>
            Download
          </Button>
          <Button type="link" size="small" icon={<ShareAltOutlined />}>
            Share
          </Button>
        </Space>
      ),
    },
  ]

  const handleRefresh = () => {
    setLoading(true)
    setTimeout(() => {
      setLoading(false)
    }, 1000)
  }

  const handleExport = (format) => {
    message.success(`Exporting report in ${format} format...`)
  }

  const exportMenu = (
    <Menu
      items={[
        {
          key: 'pdf',
          label: 'Export as PDF',
          icon: <FilePdfOutlined />,
          onClick: () => handleExport('PDF'),
        },
        {
          key: 'excel',
          label: 'Export as Excel',
          icon: <FileExcelOutlined />,
          onClick: () => handleExport('Excel'),
        },
        {
          key: 'print',
          label: 'Print Report',
          icon: <PrinterOutlined />,
          onClick: () => window.print(),
        },
      ]}
    />
  )

  return (
    <div>
      {/* Page Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={2} style={{ margin: 0 }}>
              Reports & Analytics
            </Title>
            <Text type="secondary">
              Comprehensive test execution reports and analytics
            </Text>
          </div>
          <Space>
            <Button icon={<ReloadOutlined />} loading={loading} onClick={handleRefresh}>
              Refresh
            </Button>
            <Dropdown overlay={exportMenu} trigger={['click']}>
              <Button type="primary" icon={<DownloadOutlined />}>
                Export
              </Button>
            </Dropdown>
          </Space>
        </div>
      </div>

      {/* Filters */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16} align="middle">
          <Col span={6}>
            <Space>
              <Text strong>Date Range:</Text>
              <RangePicker
                value={dateRange}
                onChange={setDateRange}
                format="YYYY-MM-DD"
              />
            </Space>
          </Col>
          <Col span={4}>
            <Space>
              <Text strong>Standard:</Text>
              <Select
                value={selectedStandard}
                onChange={setSelectedStandard}
                style={{ width: 120 }}
              >
                <Option value="all">All</Option>
                <Option value="38.101-1">TS 38.101-1</Option>
                <Option value="38.101-2">TS 38.101-2</Option>
                <Option value="36.523-1">TS 36.523-1</Option>
              </Select>
            </Space>
          </Col>
          <Col span={4}>
            <Space>
              <Text strong>Report Type:</Text>
              <Select
                value={reportType}
                onChange={setReportType}
                style={{ width: 120 }}
              >
                <Option value="overview">Overview</Option>
                <Option value="detailed">Detailed</Option>
                <Option value="summary">Summary</Option>
              </Select>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Report Tabs */}
      <Tabs defaultActiveKey="overview">
        <TabPane tab={<span><BarChartOutlined />Overview</span>} key="overview">
          {/* Summary Statistics */}
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Total Tests Executed"
                  value={1247}
                  suffix="tests"
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Success Rate"
                  value={94.2}
                  suffix="%"
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Average Duration"
                  value={13.7}
                  suffix="min"
                  valueStyle={{ color: '#722ed1' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Reports Generated"
                  value={156}
                  suffix="reports"
                  valueStyle={{ color: '#fa8c16' }}
                />
              </Card>
            </Col>
          </Row>

          {/* Charts */}
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <Card title="Test Execution Trend" extra={<LineChartOutlined />}>
                <Line {...executionTrendConfig} height={300} />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="Test Category Distribution" extra={<PieChartOutlined />}>
                <Pie {...categoryDistributionConfig} height={300} />
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab="Performance Analysis" key="performance">
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <Card title="Performance Metrics Over Time">
                <DualAxes {...performanceTrendConfig} height={400} />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="Failure Analysis">
                <Column {...failureAnalysisConfig} height={300} />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="Test Duration Distribution">
                <List
                  dataSource={[
                    { range: '< 5 min', count: 245, percentage: 35 },
                    { range: '5-15 min', count: 312, percentage: 45 },
                    { range: '15-30 min', count: 98, percentage: 14 },
                    { range: '> 30 min', count: 42, percentage: 6 },
                  ]}
                  renderItem={(item) => (
                    <List.Item>
                      <div style={{ width: '100%' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Text>{item.range}</Text>
                          <Text>{item.count} tests ({item.percentage}%)</Text>
                        </div>
                        <Progress percent={item.percentage} showInfo={false} />
                      </div>
                    </List.Item>
                  )}
                />
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab="Compliance Reports" key="compliance">
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <Card title="Standards Compliance Overview">
                <Table
                  dataSource={complianceData}
                  columns={[
                    {
                      title: 'Standard',
                      dataIndex: 'standard',
                      key: 'standard',
                      render: (text) => <Text strong>{text}</Text>,
                    },
                    {
                      title: 'Total Tests',
                      dataIndex: 'total',
                      key: 'total',
                    },
                    {
                      title: 'Passed',
                      dataIndex: 'passed',
                      key: 'passed',
                      render: (value) => <Text style={{ color: '#52c41a' }}>{value}</Text>,
                    },
                    {
                      title: 'Failed',
                      dataIndex: 'failed',
                      key: 'failed',
                      render: (value) => <Text style={{ color: '#ff4d4f' }}>{value}</Text>,
                    },
                    {
                      title: 'Compliance Rate',
                      dataIndex: 'compliance',
                      key: 'compliance',
                      render: (value) => (
                        <div>
                          <Text strong>{value}%</Text>
                          <Progress
                            percent={value}
                            size="small"
                            status={value >= 95 ? 'success' : value >= 90 ? 'normal' : 'exception'}
                            showInfo={false}
                            style={{ marginTop: 4 }}
                          />
                        </div>
                      ),
                    },
                  ]}
                  pagination={false}
                />
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab="Generated Reports" key="reports">
          <Card title="Report History">
            <Table
              columns={reportColumns}
              dataSource={recentReports}
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `Total ${total} reports`,
              }}
            />
          </Card>
        </TabPane>
      </Tabs>
    </div>
  )
}

export default Reports