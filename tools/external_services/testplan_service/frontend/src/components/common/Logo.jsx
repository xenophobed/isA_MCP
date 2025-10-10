import React from 'react'
import { Space, Typography } from 'antd'

const { Title, Text } = Typography

const Logo = ({ collapsed = false }) => {
  return (
    <Space align="center" size="middle">
      <div
        style={{
          width: 32,
          height: 32,
          background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
          borderRadius: 8,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path 
            d="M12 2L17 7L12 12L7 7L12 2Z" 
            fill="white" 
            opacity="0.9"
          />
          <path 
            d="M2 12L7 17L12 12L7 7L2 12Z" 
            fill="white" 
            opacity="0.7"
          />
          <path 
            d="M12 12L17 17L22 12L17 7L12 12Z" 
            fill="white" 
            opacity="0.5"
          />
        </svg>
      </div>
      
      {!collapsed && (
        <div>
          <Title level={4} style={{ margin: 0, color: '#1f2937' }}>
            TestPlan
          </Title>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            Management Platform
          </Text>
        </div>
      )}
    </Space>
  )
}

export default Logo