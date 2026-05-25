import { Table, Tag, Select, Typography } from 'antd';
import type { FieldInfo, FieldType } from '../../types';

const typeColors: Record<FieldType, string> = {
  numeric: '#6366f1',
  text: '#06b6d4',
  datetime: '#10b981',
  boolean: '#ef4444',
  category: '#f59e0b',
};

const typeLabels: Record<FieldType, string> = {
  numeric: '数值',
  text: '文本',
  datetime: '时间',
  boolean: '布尔',
  category: '类别',
};

interface Props {
  fields: FieldInfo[];
  onChange: (updates: { name: string; display_type: FieldType }[]) => void;
}

export default function FieldTypeEditor({ fields, onChange }: Props) {
  const handleTypeChange = (fieldName: string, newType: FieldType) => {
    onChange([{ name: fieldName, display_type: newType }]);
  };

  const columns = [
    {
      title: '字段名', dataIndex: 'name', key: 'name',
      render: (name: string) => <Typography.Text strong>{name}</Typography.Text>,
    },
    {
      title: '推断类型', dataIndex: 'inferred_type', key: 'inferred_type',
      render: (t: FieldType) => <Tag color={typeColors[t]}>{typeLabels[t]}</Tag>,
    },
    {
      title: '实际类型', dataIndex: 'display_type', key: 'display_type',
      render: (t: FieldType, record: FieldInfo) => (
        <Select
          value={t}
          size="small"
          style={{ width: 100 }}
          onChange={(v) => handleTypeChange(record.name, v)}
          options={[
            { value: 'numeric' as FieldType, label: '数值' },
            { value: 'text' as FieldType, label: '文本' },
            { value: 'datetime' as FieldType, label: '时间' },
            { value: 'boolean' as FieldType, label: '布尔' },
            { value: 'category' as FieldType, label: '类别' },
          ]}
        />
      ),
    },
    {
      title: '唯一值', dataIndex: 'unique_count', key: 'unique_count', width: 80,
    },
    {
      title: '缺失', dataIndex: 'missing_count', key: 'missing_count', width: 80,
      render: (v: number) => v > 0 ? <span style={{ color: '#ef4444' }}>{v}</span> : v,
    },
    {
      title: '示例值', dataIndex: 'sample_values', key: 'sample_values',
      render: (vals: string[]) => vals.slice(0, 3).join(', '),
    },
  ];

  return (
    <Table
      dataSource={fields}
      columns={columns}
      rowKey="name"
      pagination={false}
      size="small"
    />
  );
}
