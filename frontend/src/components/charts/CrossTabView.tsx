import { Table, Tag, Typography, Statistic, Card, Row, Col, Space } from 'antd';
import type { CrossTabResult } from '../../types';

interface Props {
  data: CrossTabResult;
  height?: number;
}

export default function CrossTabView({ data, height = 300 }: Props) {
  if (data.type === 'error') {
    return <div style={{ color: '#999', textAlign: 'center', padding: 20 }}>{data.message}</div>;
  }

  if (data.type === 'contingency') {
    const columns = [
      { title: data.row_field || '', dataIndex: '_row', key: '_row', fixed: 'left' as const, width: 100 },
      ...(data.col_categories || []).map((cat, i) => ({
        title: cat,
        dataIndex: `col_${i}`,
        key: `col_${i}`,
        width: 80,
      })),
    ];

    const dataSource = (data.row_categories || []).map((rowCat, i) => {
      const row: Record<string, any> = { _row: rowCat, _key: i };
      (data.col_categories || []).forEach((_, j) => {
        row[`col_${j}`] = data.matrix?.[i]?.[j] ?? 0;
      });
      return row;
    });

    return (
      <div>
        <div style={{ marginBottom: 12 }}>
          {data.cramers_v != null && (
            <Space style={{ marginRight: 20 }}>
              <Typography.Text type="secondary">Cramér's V:</Typography.Text>
              <Tag color={data.cramers_v >= 0.3 ? '#6366f1' : '#94a3b8'}>
                {data.cramers_v.toFixed(4)}
              </Tag>
            </Space>
          )}
          {data.p_value != null && (
            <Space>
              <Typography.Text type="secondary">p-value:</Typography.Text>
              <Tag color={data.p_value < 0.05 ? '#10b981' : '#94a3b8'}>
                {data.p_value.toFixed(6)}
              </Tag>
            </Space>
          )}
        </div>
        <Table
          dataSource={dataSource}
          columns={columns}
          rowKey="_key"
          pagination={false}
          size="small"
          scroll={{ x: 'max-content', y: height - 80 }}
        />
      </div>
    );
  }

  if (data.type === 'group_stats') {
    const columns = [
      { title: data.category_field || '', dataIndex: 'category', key: 'category' },
      { title: '数量', dataIndex: 'count', key: 'count' },
      { title: '均值', dataIndex: 'mean', key: 'mean' },
      { title: '标准差', dataIndex: 'std', key: 'std' },
      { title: '最小值', dataIndex: 'min', key: 'min' },
      { title: '最大值', dataIndex: 'max', key: 'max' },
    ];

    return (
      <div>
        <Row gutter={16} style={{ marginBottom: 12 }}>
          <Col span={8}>
            <Card size="small">
              <Statistic
                title="ANOVA F值"
                value={data.anova_f ?? 'N/A'}
                valueStyle={{ color: data.anova_f != null && data.anova_p != null && data.anova_p < 0.05 ? '#10b981' : '#94a3b8' }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <Statistic
                title="p-value"
                value={data.anova_p?.toFixed(6) ?? 'N/A'}
                valueStyle={{ color: data.anova_p != null && data.anova_p < 0.05 ? '#10b981' : '#94a3b8' }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <Statistic
                title="Eta Squared"
                value={data.eta_squared?.toFixed(4) ?? 'N/A'}
                valueStyle={{ color: data.eta_squared != null && data.eta_squared >= 0.06 ? '#6366f1' : '#94a3b8' }}
              />
            </Card>
          </Col>
        </Row>
        <Table
          dataSource={data.groups}
          columns={columns}
          rowKey="category"
          pagination={false}
          size="small"
          scroll={{ y: height - 140 }}
        />
      </div>
    );
  }

  return null;
}
