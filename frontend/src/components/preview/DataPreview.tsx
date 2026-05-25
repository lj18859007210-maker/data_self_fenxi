import { Table } from 'antd';

interface Props {
  columns: string[];
  rows: Record<string, unknown>[];
}

export default function DataPreview({ columns, rows }: Props) {
  const tableColumns = columns.map((col) => ({
    title: col,
    dataIndex: col,
    key: col,
    ellipsis: true,
    width: 150,
  }));

  return (
    <Table
      dataSource={rows.map((r, i) => ({ ...r, _key: i }))}
      columns={tableColumns}
      rowKey="_key"
      scroll={{ x: 'max-content', y: 400 }}
      pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 行` }}
      size="small"
    />
  );
}
