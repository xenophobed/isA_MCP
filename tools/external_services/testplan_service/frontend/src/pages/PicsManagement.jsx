import React, { useState, useRef } from 'react'
import {
  Row,
  Col,
  Card,
  Upload,
  Button,
  Table,
  Tag,
  Space,
  Typography,
  message,
  Modal,
  Form,
  Input,
  Select,
  Descriptions,
  Progress,
  Tooltip,
  Popconfirm,
} from 'antd'
import {
  InboxOutlined,
  UploadOutlined,
  DownloadOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'

const { Title, Text } = Typography
const { Dragger } = Upload
const { TextArea } = Input
const { Option } = Select

const PicsManagement = () => {
  const [loading, setLoading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [isModalVisible, setIsModalVisible] = useState(false)
  const [selectedPics, setSelectedPics] = useState(null)
  const [form] = Form.useForm()
  const fileInputRef = useRef(null)

  // Mock PICS data
  const [picsData, setPicsData] = useState([
    {
      key: '1',
      id: 'PICS_5G_NR_001',
      name: '5G NR UE PICS Configuration',
      version: 'v2.1.0',
      standard: '3GPP TS 38.101-1',
      uploadDate: '2024-01-15',
      status: 'active',
      fileSize: '2.3 MB',
      capabilities: 156,
      description: 'PICS configuration for 5G NR UE conformance testing',
    },
    {
      key: '2',
      id: 'PICS_LTE_002',
      name: 'LTE UE PICS Configuration',
      version: 'v1.8.5',
      standard: '3GPP TS 36.523-1',
      uploadDate: '2024-01-12',
      status: 'active',
      fileSize: '1.8 MB',
      capabilities: 124,
      description: 'PICS configuration for LTE UE conformance testing',
    },
    {
      key: '3',
      id: 'PICS_VoNR_003',
      name: 'VoNR PICS Configuration',
      version: 'v1.2.0',
      standard: '3GPP TS 26.114',
      uploadDate: '2024-01-10',
      status: 'draft',
      fileSize: '0.9 MB',
      capabilities: 78,
      description: 'PICS configuration for Voice over New Radio testing',
    },
  ])

  const handleUpload = (info) => {
    const { status } = info.file
    if (status === 'uploading') {
      setUploadProgress(Math.floor(Math.random() * 100))
    } else if (status === 'done') {
      message.success(`${info.file.name} file uploaded successfully.`)
      setUploadProgress(100)
      
      // Add new PICS to the list (mock)
      const newPics = {
        key: Date.now().toString(),
        id: `PICS_NEW_${Date.now()}`,
        name: info.file.name.replace('.xlsx', ''),
        version: 'v1.0.0',
        standard: 'Auto-detected',
        uploadDate: new Date().toISOString().split('T')[0],
        status: 'processing',
        fileSize: `${(info.file.size / 1024 / 1024).toFixed(1)} MB`,
        capabilities: Math.floor(Math.random() * 200),
        description: 'Newly uploaded PICS configuration',
      }
      setPicsData([newPics, ...picsData])
      
      setTimeout(() => {
        setUploadProgress(0)
      }, 2000)
    } else if (status === 'error') {
      message.error(`${info.file.name} file upload failed.`)
      setUploadProgress(0)
    }
  }

  const uploadProps = {
    name: 'file',
    multiple: true,
    accept: '.xlsx,.xls,.json,.xml',
    action: '/api/pics/upload',
    onChange: handleUpload,
    beforeUpload: (file) => {
      const isValidType = file.name.endsWith('.xlsx') || file.name.endsWith('.xls') || 
                         file.name.endsWith('.json') || file.name.endsWith('.xml')
      if (!isValidType) {
        message.error('You can only upload XLSX, XLS, JSON, or XML files!')
        return false
      }
      const isLt10M = file.size / 1024 / 1024 < 10
      if (!isLt10M) {
        message.error('File must be smaller than 10MB!')
        return false
      }
      return true
    },
  }

  const columns = [
    {
      title: 'PICS ID',
      dataIndex: 'id',
      key: 'id',
      render: (text) => (
        <Space>
          <FileTextOutlined />
          <Text strong>{text}</Text>
        </Space>
      ),
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Version',
      dataIndex: 'version',
      key: 'version',
      render: (text) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: 'Standard',
      dataIndex: 'standard',
      key: 'standard',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const statusConfig = {
          active: { color: 'success', text: 'Active' },
          draft: { color: 'warning', text: 'Draft' },
          processing: { color: 'processing', text: 'Processing' },
          archived: { color: 'default', text: 'Archived' },
        }
        const config = statusConfig[status] || statusConfig.draft
        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
    {
      title: 'Capabilities',
      dataIndex: 'capabilities',
      key: 'capabilities',
      render: (count) => `${count} items`,
    },
    {
      title: 'Upload Date',
      dataIndex: 'uploadDate',
      key: 'uploadDate',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title="View Details">
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => viewPics(record)}
            />
          </Tooltip>
          <Tooltip title="Edit">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => editPics(record)}
            />
          </Tooltip>
          <Tooltip title="Download">
            <Button
              type="link"
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => downloadPics(record)}
            />
          </Tooltip>
          <Popconfirm
            title="Are you sure to delete this PICS?"
            onConfirm={() => deletePics(record.key)}
            okText="Yes"
            cancelText="No"
          >
            <Tooltip title="Delete">
              <Button
                type="link"
                size="small"
                icon={<DeleteOutlined />}
                danger
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const viewPics = (record) => {
    setSelectedPics(record)
    setIsModalVisible(true)
  }

  const editPics = (record) => {
    form.setFieldsValue(record)
    setSelectedPics(record)
    setIsModalVisible(true)
  }

  const downloadPics = (record) => {
    message.success(`Downloading ${record.name}...`)
  }

  const deletePics = (key) => {
    setPicsData(picsData.filter(item => item.key !== key))
    message.success('PICS deleted successfully')
  }

  const handleModalOk = () => {
    form.validateFields().then(values => {
      if (selectedPics) {
        setPicsData(picsData.map(item => 
          item.key === selectedPics.key ? { ...item, ...values } : item
        ))
        message.success('PICS updated successfully')
      }
      setIsModalVisible(false)
      setSelectedPics(null)
      form.resetFields()
    })
  }

  const handleModalCancel = () => {
    setIsModalVisible(false)
    setSelectedPics(null)
    form.resetFields()
  }

  const handleRefresh = () => {
    setLoading(true)
    setTimeout(() => {
      setLoading(false)
      message.success('PICS data refreshed')
    }, 1000)
  }

  return (
    <div>
      {/* Page Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={2} style={{ margin: 0 }}>
              PICS Management
            </Title>
            <Text type="secondary">
              Manage Protocol Implementation Conformance Statements
            </Text>
          </div>
          <Space>
            <Button
              icon={<ReloadOutlined />}
              loading={loading}
              onClick={handleRefresh}
            >
              Refresh
            </Button>
            <Button
              type="primary"
              icon={<UploadOutlined />}
              onClick={() => fileInputRef.current?.click()}
            >
              Upload PICS
            </Button>
          </Space>
        </div>
      </div>

      {/* Upload Section */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card title="Upload PICS Files">
            <Dragger {...uploadProps} style={{ marginBottom: 16 }}>
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">
                Click or drag PICS files to this area to upload
              </p>
              <p className="ant-upload-hint">
                Support for Excel (.xlsx, .xls), JSON, and XML formats. 
                Maximum file size: 10MB. Multiple files supported.
              </p>
            </Dragger>
            
            {uploadProgress > 0 && (
              <Progress
                percent={uploadProgress}
                status={uploadProgress === 100 ? 'success' : 'active'}
                showInfo={true}
              />
            )}
          </Card>
        </Col>
      </Row>

      {/* PICS Table */}
      <Card title="PICS Repository">
        <Table
          columns={columns}
          dataSource={picsData}
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `Total ${total} items`,
          }}
          scroll={{ x: 800 }}
        />
      </Card>

      {/* View/Edit Modal */}
      <Modal
        title={selectedPics ? `PICS Details - ${selectedPics.name}` : 'PICS Details'}
        open={isModalVisible}
        onOk={handleModalOk}
        onCancel={handleModalCancel}
        width={800}
        okText="Save"
        cancelText="Cancel"
      >
        {selectedPics && (
          <>
            <Descriptions column={2} bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="PICS ID">{selectedPics.id}</Descriptions.Item>
              <Descriptions.Item label="File Size">{selectedPics.fileSize}</Descriptions.Item>
              <Descriptions.Item label="Standard">{selectedPics.standard}</Descriptions.Item>
              <Descriptions.Item label="Capabilities">{selectedPics.capabilities} items</Descriptions.Item>
              <Descriptions.Item label="Upload Date">{selectedPics.uploadDate}</Descriptions.Item>
              <Descriptions.Item label="Status">{selectedPics.status}</Descriptions.Item>
            </Descriptions>
            
            <Form form={form} layout="vertical">
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="name"
                    label="PICS Name"
                    rules={[{ required: true, message: 'Please enter PICS name' }]}
                  >
                    <Input />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="version"
                    label="Version"
                    rules={[{ required: true, message: 'Please enter version' }]}
                  >
                    <Input />
                  </Form.Item>
                </Col>
              </Row>
              
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="standard"
                    label="Standard"
                    rules={[{ required: true, message: 'Please enter standard' }]}
                  >
                    <Input />
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
                      <Option value="draft">Draft</Option>
                      <Option value="archived">Archived</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
              
              <Form.Item
                name="description"
                label="Description"
              >
                <TextArea rows={3} />
              </Form.Item>
            </Form>
          </>
        )}
      </Modal>

      {/* Hidden file input for manual upload */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".xlsx,.xls,.json,.xml"
        style={{ display: 'none' }}
        onChange={(e) => {
          // Handle manual file selection
          if (e.target.files.length > 0) {
            message.info('Files selected for upload')
          }
        }}
      />
    </div>
  )
}

export default PicsManagement