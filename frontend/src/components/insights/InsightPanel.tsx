import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, Typography, Spin, Empty, Select, Space, Divider } from 'antd';
import { BulbOutlined } from '@ant-design/icons';
import { getInsights, getKeyDrivers } from '../../api/client';
import InsightCard from './InsightCard';
import type { FieldInfo } from '../../types';

interface Props {
  sessionId: string;
  fields: FieldInfo[];
}

export default function InsightPanel({ sessionId, fields }: Props) {
  const [selectedDriverField, setSelectedDriverField] = useState<string>(
    fields.find(f => f.display_type === 'numeric')?.name || ''
  );

  const insightsQuery = useQuery({
    queryKey: ['insights', sessionId],
    queryFn: () => getInsights(sessionId),
    enabled: !!sessionId,
  });

  const driversQuery = useQuery({
    queryKey: ['drivers', sessionId, selectedDriverField],
    queryFn: () => getKeyDrivers(sessionId, selectedDriverField),
    enabled: !!sessionId && !!selectedDriverField,
  });

  const insights = insightsQuery.data?.data || [];
  const drivers = driversQuery.data?.data || [];
  const numericFields = fields.filter(f => f.display_type === 'numeric' || f.display_type === 'category');

  return (
    <div>
      <Card
        size="small"
        title={<><BulbOutlined style={{ marginRight: 6 }} />AI 洞察</>}
        style={{ marginBottom: 16 }}
      >
        {insightsQuery.isLoading ? (
          <Spin size="small" style={{ display: 'block', margin: '20px auto' }} />
        ) : insights.length === 0 ? (
          <Empty description="暂无洞察" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          insights.slice(0, 10).map((insight, i) => (
            <InsightCard key={i} insight={insight} />
          ))
        )}
      </Card>

      <Card
        size="small"
        title={<Typography.Text style={{ fontSize: 13 }}>关键驱动因素</Typography.Text>}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Select
            size="small"
            value={selectedDriverField}
            onChange={setSelectedDriverField}
            style={{ width: '100%' }}
            options={numericFields.map(f => ({ value: f.name, label: f.name }))}
          />
          {driversQuery.isLoading ? (
            <Spin size="small" style={{ display: 'block', margin: '20px auto' }} />
          ) : drivers.length === 0 ? (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>暂无驱动因素分析</Typography.Text>
          ) : (
            drivers.slice(0, 5).map((d, i) => (
              <div key={i} style={{ fontSize: 12, padding: '4px 0', borderBottom: i < drivers.length - 1 ? '1px solid #f0f0f0' : 'none' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography.Text strong>{d.field}</Typography.Text>
                  <Typography.Text type="secondary">
                    {(d.score * 100).toFixed(0)}%
                  </Typography.Text>
                </div>
                <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                  {d.description}
                </Typography.Text>
              </div>
            ))
          )}
        </Space>
      </Card>
    </div>
  );
}
