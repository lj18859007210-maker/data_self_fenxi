import { ReactNode } from 'react'
import { Layout, Typography } from 'antd'
import { BarChartOutlined } from '@ant-design/icons'

const { Header, Content } = Layout

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#1e293b', display: 'flex', alignItems: 'center', padding: '0 24px' }}>
        <BarChartOutlined style={{ fontSize: 22, color: '#6366f1', marginRight: 10 }} />
        <Typography.Title level={4} style={{ color: '#fff', margin: 0 }}>数据自分析平台</Typography.Title>
      </Header>
      <Content style={{ padding: 24, background: '#f5f5f5' }}>
        {children}
      </Content>
    </Layout>
  )
}
