import React, { useState, useRef } from 'react'
import {
  Row,
  Col,
  Card,
  Steps,
  Form,
  Input,
  Select,
  Button,
  Upload,
  Table,
  Tag,
  Space,
  Typography,
  Divider,
  Collapse,
  Checkbox,
  Progress,
  message,
  Modal,
  Tree,
  Tabs,
} from 'antd'
import {
  InboxOutlined,
  UploadOutlined,
  DownloadOutlined,
  PlayCircleOutlined,
  SettingOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  FolderOutlined,
  FileOutlined,
  EyeOutlined,
  DeleteOutlined,
} from '@ant-design/icons'

const { Title, Text, Paragraph } = Typography
const { Dragger } = Upload
const { Step } = Steps
const { Option } = Select
const { Panel } = Collapse
const { TextArea } = Input
const { TabPane } = Tabs

const TestPlanGeneration = () => {
  const [currentStep, setCurrentStep] = useState(0)
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [generatedTests, setGeneratedTests] = useState([])
  const [selectedTests, setSelectedTests] = useState([])
  const [previewVisible, setPreviewVisible] = useState(false)
  const [previewContent, setPreviewContent] = useState('')

  // Mock data for test categories
  const testCategories = [
    {
      title: 'Physical Layer Tests',
      key: 'phy',
      children: [
        { title: 'Downlink Physical Channels', key: 'phy-dl', selectable: true },
        { title: 'Uplink Physical Channels', key: 'phy-ul', selectable: true },
        { title: 'Physical Signals', key: 'phy-sig', selectable: true },
      ],
    },
    {
      title: 'MAC Layer Tests',
      key: 'mac',
      children: [
        { title: 'Random Access Procedure', key: 'mac-rach', selectable: true },
        { title: 'HARQ Procedures', key: 'mac-harq', selectable: true },
        { title: 'Scheduling Request', key: 'mac-sr', selectable: true },
      ],
    },
    {
      title: 'RRC Tests',
      key: 'rrc',
      children: [
        { title: 'Connection Management', key: 'rrc-conn', selectable: true },
        { title: 'Mobility Procedures', key: 'rrc-mob', selectable: true },
        { title: 'Security Procedures', key: 'rrc-sec', selectable: true },
      ],
    },
  ]

  // Mock generated test cases
  const mockTestCases = [
    {
      key: '1',
      id: 'TC_PHY_DL_001',
      name: 'PDSCH Power Control Test',
      category: 'Physical Layer',
      type: 'Downlink',
      priority: 'High',
      duration: '15 min',
      description: 'Verify PDSCH power control functionality',
      selected: true,
    },
    {
      key: '2',
      id: 'TC_PHY_UL_001',
      name: 'PUSCH Power Control Test',
      category: 'Physical Layer',
      type: 'Uplink',
      priority: 'High',
      duration: '12 min',
      description: 'Verify PUSCH power control functionality',
      selected: true,
    },
    {
      key: '3',
      id: 'TC_MAC_RACH_001',
      name: 'Random Access Procedure Test',
      category: 'MAC Layer',
      type: 'Procedure',
      priority: 'Medium',
      duration: '8 min',
      description: 'Verify random access procedure',
      selected: false,
    },
  ]

  const steps = [
    {
      title: 'Configuration',
      description: 'Set up test plan parameters',
    },
    {
      title: 'File Upload',
      description: 'Upload specification files',
    },
    {
      title: 'Test Selection',
      description: 'Select test cases to include',
    },
    {
      title: 'Generate',
      description: 'Generate and download test plan',
    },
  ]

  const testCaseColumns = [
    {
      title: 'Test ID',
      dataIndex: 'id',
      key: 'id',
      render: (text) => <Text code>{text}</Text>,
    },
    {
      title: 'Test Name',
      dataIndex: 'name',
      key: 'name',
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      render: (text) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
    },
    {
      title: 'Priority',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority) => {
        const color = priority === 'High' ? 'red' : priority === 'Medium' ? 'orange' : 'green'
        return <Tag color={color}>{priority}</Tag>
      },
    },
    {
      title: 'Duration',
      dataIndex: 'duration',
      key: 'duration',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => previewTest(record)}
          >
            Preview
          </Button>
        </Space>
      ),
    },
  ]

  const uploadProps = {
    name: 'file',
    multiple: true,
    accept: '.xlsx,.xls,.doc,.docx,.pdf',
    action: '/api/testplan/upload',
    onChange: (info) => {
      const { status } = info.file
      if (status === 'done') {
        message.success(`${info.file.name} file uploaded successfully.`)
        // Simulate test case generation
        setTimeout(() => {
          setGeneratedTests(mockTestCases)
          message.success('Test cases generated from uploaded files!')
        }, 2000)
      } else if (status === 'error') {
        message.error(`${info.file.name} file upload failed.`)
      }
    },
  }

  const handleNext = () => {
    if (currentStep === 0) {
      form.validateFields().then(() => {
        setCurrentStep(currentStep + 1)
      })
    } else if (currentStep === 1) {
      if (generatedTests.length === 0) {
        message.warning('Please upload specification files first')
        return
      }
      setCurrentStep(currentStep + 1)
    } else {
      setCurrentStep(currentStep + 1)
    }
  }

  const handlePrev = () => {
    setCurrentStep(currentStep - 1)
  }

  const handleGenerate = () => {
    setLoading(true)
    const selected = generatedTests.filter(test => selectedTests.includes(test.key))
    
    setTimeout(() => {
      setLoading(false)
      message.success(`Test plan generated with ${selected.length} test cases!`)
      // Simulate file download
      const element = document.createElement('a')
      const file = new Blob(['Mock test plan content'], { type: 'text/plain' })
      element.href = URL.createObjectURL(file)
      element.download = 'generated_test_plan.txt'
      document.body.appendChild(element)
      element.click()
      document.body.removeChild(element)
    }, 3000)
  }

  const previewTest = (record) => {
    setPreviewContent(`
Test Case ID: ${record.id}
Test Name: ${record.name}
Category: ${record.category}
Type: ${record.type}
Priority: ${record.priority}
Duration: ${record.duration}

Description:
${record.description}

Test Steps:
1. Initialize test environment
2. Configure test parameters
3. Execute test procedure
4. Verify test results
5. Clean up test environment

Expected Results:
- Test should pass within specified duration
- All verification points should be met
- No errors should be reported
    `)
    setPreviewVisible(true)
  }

  const rowSelection = {
    selectedRowKeys: selectedTests,
    onChange: (selectedRowKeys) => {
      setSelectedTests(selectedRowKeys)
    },
    onSelectAll: (selected, selectedRows, changeRows) => {
      if (selected) {
        setSelectedTests(generatedTests.map(test => test.key))
      } else {
        setSelectedTests([])
      }
    },
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <Card title="Test Plan Configuration">
            <Form form={form} layout="vertical">
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="planName"
                    label="Test Plan Name"
                    rules={[{ required: true, message: 'Please enter test plan name' }]}
                  >
                    <Input placeholder="e.g., 5G NR Conformance Test Plan" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="version"
                    label="Version"
                    rules={[{ required: true, message: 'Please enter version' }]}
                  >
                    <Input placeholder="e.g., v1.0.0" />
                  </Form.Item>
                </Col>
              </Row>
              
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="standard"
                    label="3GPP Standard"
                    rules={[{ required: true, message: 'Please select standard' }]}
                  >
                    <Select placeholder="Select 3GPP standard">
                      <Option value="38.101-1">TS 38.101-1 (NR UE radio transmission and reception)</Option>
                      <Option value="38.101-2">TS 38.101-2 (NR UE radio transmission and reception Part 2)</Option>
                      <Option value="36.523-1">TS 36.523-1 (LTE UE conformance specification)</Option>
                      <Option value="34.123-1">TS 34.123-1 (UTRA UE conformance specification)</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="testType"
                    label="Test Type"
                    rules={[{ required: true, message: 'Please select test type' }]}
                  >
                    <Select placeholder="Select test type">
                      <Option value="conformance">Conformance Testing</Option>
                      <Option value="interoperability">Interoperability Testing</Option>
                      <Option value="performance">Performance Testing</Option>
                      <Option value="regression">Regression Testing</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
              
              <Form.Item
                name="description"
                label="Description"
              >
                <TextArea rows={3} placeholder="Describe the purpose and scope of this test plan" />
              </Form.Item>
            </Form>
          </Card>
        )
        
      case 1:
        return (
          <Card title="Upload Specification Files">
            <Dragger {...uploadProps}>
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">
                Click or drag 3GPP specification files to this area to upload
              </p>
              <p className="ant-upload-hint">
                Support for Excel (.xlsx, .xls), Word (.doc, .docx), and PDF files.
                The system will analyze the files and generate relevant test cases.
              </p>
            </Dragger>
            
            {generatedTests.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <Text strong>Generated {generatedTests.length} test cases from uploaded files</Text>
                <Progress percent={100} status="success" />
              </div>
            )}
          </Card>
        )
        
      case 2:
        return (
          <div>
            <Card title="Select Test Cases" extra={
              <Space>
                <Text>Selected: {selectedTests.length}/{generatedTests.length}</Text>
                <Button 
                  size="small" 
                  onClick={() => setSelectedTests(generatedTests.map(test => test.key))}
                >
                  Select All
                </Button>
                <Button 
                  size="small" 
                  onClick={() => setSelectedTests([])}
                >
                  Clear All
                </Button>
              </Space>
            }>
              <Table
                columns={testCaseColumns}
                dataSource={generatedTests}
                rowSelection={rowSelection}
                pagination={false}
                size="small"
              />
            </Card>
            
            <Card title="Test Categories" style={{ marginTop: 16 }}>
              <Collapse>
                {testCategories.map(category => (
                  <Panel header={category.title} key={category.key}>
                    <Checkbox.Group style={{ width: '100%' }}>
                      <Row>
                        {category.children.map(child => (
                          <Col span={8} key={child.key}>
                            <Checkbox value={child.key}>{child.title}</Checkbox>
                          </Col>
                        ))}
                      </Row>
                    </Checkbox.Group>
                  </Panel>
                ))}
              </Collapse>
            </Card>
          </div>
        )
        
      case 3:
        return (
          <Card title="Generate Test Plan">
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <FileTextOutlined style={{ fontSize: '64px', color: '#1890ff', marginBottom: 16 }} />
              <Title level={3}>Ready to Generate Test Plan</Title>
              <Paragraph>
                You have selected {selectedTests.length} test cases for your test plan.
                Click the button below to generate and download your test plan.
              </Paragraph>
              
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <div>
                  <Text strong>Test Plan Summary:</Text>
                  <ul style={{ textAlign: 'left', display: 'inline-block', marginTop: 8 }}>
                    <li>Total Test Cases: {selectedTests.length}</li>
                    <li>Estimated Duration: {selectedTests.length * 10} minutes</li>
                    <li>Categories: Physical Layer, MAC Layer, RRC</li>
                  </ul>
                </div>
                
                <Button
                  type="primary"
                  size="large"
                  icon={<DownloadOutlined />}
                  loading={loading}
                  onClick={handleGenerate}
                >
                  Generate & Download Test Plan
                </Button>
              </Space>
            </div>
          </Card>
        )
        
      default:
        return null
    }
  }

  return (
    <div>
      {/* Page Header */}
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>
          Test Plan Generation
        </Title>
        <Text type="secondary">
          Generate comprehensive test plans from 3GPP specification documents
        </Text>
      </div>

      {/* Steps */}
      <Card style={{ marginBottom: 24 }}>
        <Steps current={currentStep}>
          {steps.map(item => (
            <Step key={item.title} title={item.title} description={item.description} />
          ))}
        </Steps>
      </Card>

      {/* Step Content */}
      <div style={{ marginBottom: 24 }}>
        {renderStepContent()}
      </div>

      {/* Navigation */}
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Button disabled={currentStep === 0} onClick={handlePrev}>
            Previous
          </Button>
          <Button
            type="primary"
            onClick={currentStep === steps.length - 1 ? handleGenerate : handleNext}
            loading={loading && currentStep === steps.length - 1}
          >
            {currentStep === steps.length - 1 ? 'Generate Test Plan' : 'Next'}
          </Button>
        </div>
      </Card>

      {/* Preview Modal */}
      <Modal
        title="Test Case Preview"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            Close
          </Button>
        ]}
        width={800}
      >
        <pre style={{ whiteSpace: 'pre-wrap', backgroundColor: '#f5f5f5', padding: 16 }}>
          {previewContent}
        </pre>
      </Modal>
    </div>
  )
}

export default TestPlanGeneration