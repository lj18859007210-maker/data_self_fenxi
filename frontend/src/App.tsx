import { Routes, Route, Navigate } from 'react-router-dom'
import UploadPage from './pages/UploadPage'
import PreviewPage from './pages/PreviewPage'
import DashboardPage from './pages/DashboardPage'
import AppLayout from './components/layout/AppLayout'

export default function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/preview/:sessionId" element={<PreviewPage />} />
        <Route path="/dashboard/:sessionId" element={<DashboardPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppLayout>
  )
}
