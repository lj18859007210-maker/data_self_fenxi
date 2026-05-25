import { Card, Tag, Typography } from 'antd';
import {
  ThunderboltOutlined,
  WarningOutlined,
  LinkOutlined,
  BarChartOutlined,
  PieChartOutlined,
  DatabaseOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import type { Insight } from '../../types';

const typeConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  distribution: { color: '#6366f1', icon: <BarChartOutlined />, label: '分布' },
  outlier: { color: '#ef4444', icon: <WarningOutlined />, label: '异常' },
  missing: { color: '#f59e0b', icon: <DatabaseOutlined />, label: '缺失' },
  correlation: { color: '#10b981', icon: <LinkOutlined />, label: '关联' },
  imbalance: { color: '#ec4899', icon: <PieChartOutlined />, label: '不平衡' },
  comparison: { color: '#06b6d4', icon: <ThunderboltOutlined />, label: '对比' },
  cardinality: { color: '#94a3b8', icon: <QuestionCircleOutlined />, label: '基数' },
};

interface Props {
  insight: Insight;
}

export default function InsightCard({ insight }: Props) {
  const cfg = typeConfig[insight.type] || { color: '#94a3b8', icon: <QuestionCircleOutlined />, label: insight.type };

  return (
    <Card
      size="small"
      style={{ marginBottom: 8, borderLeft: `3px solid ${cfg.color}` }}
    >
      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
        <span style={{ color: cfg.color, fontSize: 16, marginTop: 2 }}>{cfg.icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
            <Typography.Text strong style={{ fontSize: 13 }}>{insight.title}</Typography.Text>
            <Tag color={cfg.color} style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px' }}>
              {cfg.label}
            </Tag>
          </div>
          <Typography.Paragraph
            type="secondary"
            style={{ fontSize: 12, marginBottom: 0 }}
            ellipsis={{ rows: 2, expandable: true, symbol: '更多' }}
          >
            {insight.description}
          </Typography.Paragraph>
          <div style={{ marginTop: 4 }}>
            <Typography.Text style={{ fontSize: 11, color: '#94a3b8' }}>
              重要性: {(insight.score * 100).toFixed(0)}%
            </Typography.Text>
          </div>
        </div>
      </div>
    </Card>
  );
}
