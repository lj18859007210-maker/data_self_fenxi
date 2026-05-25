import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Spin, Typography, Space, Button, Layout, Progress, Tag, Alert } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { getOverview, getProgress, getCharts } from '../api/client';
import { useSessionStore } from '../stores/sessionStore';
import KpiCards from '../components/dashboard/KpiCards';
import FieldList from '../components/dashboard/FieldList';
import DraggableGrid from '../components/dashboard/DraggableGrid';
import { useFilterStore } from '../hooks/useFilterLink';
import type { DashboardOverview, ChartConfig } from '../types';
import InsightPanel from '../components/insights/InsightPanel';
import ExportButton from '../components/dashboard/ExportButton';

const { Sider, Content } = Layout;

export default function DashboardPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const fields = useSessionStore((s) => s.fields);
  const [selectedField, setSelectedField] = useState<string>();
  const [progress, setProgress] = useState(0);
  const [analyzing, setAnalyzing] = useState(true);

  // Poll analysis progress
  useEffect(() => {
    if (!sessionId) return;
    const interval = setInterval(async () => {
      const res = await getProgress(sessionId);
      setProgress(res.data.progress);
      if (res.data.state === 'complete' || res.data.state === 'error') {
        setAnalyzing(false);
        clearInterval(interval);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [sessionId]);

  const overviewQuery = useQuery({
    queryKey: ['overview', sessionId],
    queryFn: () => getOverview(sessionId!),
    enabled: !!sessionId && !analyzing,
  });

  const chartsQuery = useQuery({
    queryKey: ['charts', sessionId],
    queryFn: () => getCharts(sessionId!),
    enabled: !!sessionId && !analyzing,
  });

  const overview = overviewQuery.data?.data as DashboardOverview | undefined;
  const charts = chartsQuery.data?.data as ChartConfig[] | undefined;
  const { filters, clearFilters } = useFilterStore();
  const activeFilters = Object.entries(filters).filter(([, v]) => v !== null);

  if (analyzing) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Progress type="circle" percent={Math.round(progress * 100)} />
        <Typography.Title level={4} style={{ marginTop: 24 }}>正在分析数据...</Typography.Title>
        <Typography.Text type="secondary">系统正在自动计算各字段的统计量和关联关系</Typography.Text>
      </div>
    );
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>返回</Button>
        <ExportButton />
      </Space>
      <div id="dashboard-content">
      {overview && <KpiCards overview={overview} />}
      {activeFilters.length > 0 && (
        <Alert
          type="info"
          showIcon
          message={
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <span>当前筛选：</span>
              {activeFilters.map(([field, value]) => (
                <Tag key={field} closable onClose={() => useFilterStore.getState().setFilter(field, null)}>
                  {field}: {value}
                </Tag>
              ))}
              <a onClick={clearFilters} style={{ marginLeft: 8 }}>清除全部</a>
            </div>
          }
          style={{ marginBottom: 16 }}
        />
      )}
      <Layout style={{ background: 'transparent', marginTop: 16 }}>
        <Sider width={180} style={{ background: '#fff', padding: 12, borderRadius: 8, marginRight: 16 }}>
          <FieldList fields={fields} selectedField={selectedField} onSelect={setSelectedField} />
        </Sider>
        <Content style={{ flex: 1, minWidth: 0 }}>
          {charts && !chartsQuery.isLoading && <DraggableGrid charts={charts} />}
          {chartsQuery.isLoading && <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />}
        </Content>
        <Sider width={280} style={{ background: 'transparent', marginLeft: 16 }}>
          <InsightPanel sessionId={sessionId!} fields={fields} />
        </Sider>
      </Layout>
    </div>
    </div>
  );
}
