import { Row, Col, Spin, Empty, Alert } from 'antd';
import ChartFactory from '../charts/ChartFactory';
import type { ChartConfig } from '../../types';

interface Props {
  charts: ChartConfig[];
  loading: boolean;
}

export default function ChartGrid({ charts, loading }: Props) {
  if (loading) return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />;
  if (!charts.length) return <Empty description="暂无图表数据" />;

  return (
    <Row gutter={[16, 16]}>
      {charts.map((chart) => (
        <Col key={chart.id} xs={24} sm={12} lg={chart.type === 'heatmap' ? 24 : 12}>
          <ChartFactory chart={chart} />
        </Col>
      ))}
    </Row>
  );
}
