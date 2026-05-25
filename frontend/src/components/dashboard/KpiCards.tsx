import { Row, Col, Card, Statistic } from 'antd';
import { TableOutlined, ColumnHeightOutlined, WarningOutlined, InfoCircleOutlined } from '@ant-design/icons';

interface Props {
  overview: {
    filename: string;
    row_count: number;
    column_count: number;
    numeric_count: number;
    text_count: number;
    total_missing: number;
    total_outliers: number;
  };
}

export default function KpiCards({ overview }: Props) {
  return (
    <Row gutter={16}>
      <Col span={6}>
        <Card size="small">
          <Statistic title="数据总量" value={overview.row_count} suffix="行" prefix={<TableOutlined />} />
        </Card>
      </Col>
      <Col span={6}>
        <Card size="small">
          <Statistic title="字段总数" value={overview.column_count} prefix={<ColumnHeightOutlined />}
            suffix={`(${overview.numeric_count} 数值 / ${overview.text_count} 类别)`} />
        </Card>
      </Col>
      <Col span={6}>
        <Card size="small">
          <Statistic title="缺失值" value={overview.total_missing} prefix={<WarningOutlined />}
            valueStyle={{ color: overview.total_missing > 0 ? '#faad14' : undefined }} />
        </Card>
      </Col>
      <Col span={6}>
        <Card size="small">
          <Statistic title="异常值" value={overview.total_outliers} prefix={<InfoCircleOutlined />}
            valueStyle={{ color: overview.total_outliers > 0 ? '#ff4d4f' : undefined }} />
        </Card>
      </Col>
    </Row>
  );
}
