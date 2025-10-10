import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout, Spin } from 'antd'
import MainLayout from './components/layout/MainLayout'
import Dashboard from './pages/Dashboard'
import PicsManagement from './pages/PicsManagement'
import TestPlanGeneration from './pages/TestPlanGeneration'
import Reports from './pages/Reports'
import Settings from './pages/Settings'
import { useAppStore } from './store/appStore'

const { Content } = Layout

function App() {
  const { loading } = useAppStore()

  return (
    <div className="app">
      <Spin spinning={loading} tip="Loading..." size="large">
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="pics" element={<PicsManagement />} />
            <Route path="testplan" element={<TestPlanGeneration />} />
            <Route path="reports" element={<Reports />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </Spin>
    </div>
  )
}

export default App