import { List, Tag, Typography } from 'antd';
import type { FieldInfo, FieldType } from '../../types';

const typeColors: Record<FieldType, string> = {
  numeric: '#6366f1',
  text: '#06b6d4',
  datetime: '#10b981',
  boolean: '#ef4444',
  category: '#f59e0b',
};
const typeLabels: Record<FieldType, string> = {
  numeric: '数值', text: '文本', datetime: '时间', boolean: '布尔', category: '类别',
};

interface Props {
  fields: FieldInfo[];
  selectedField?: string;
  onSelect?: (name: string) => void;
}

export default function FieldList({ fields, selectedField, onSelect }: Props) {
  return (
    <div>
      <Typography.Text strong style={{ display: 'block', marginBottom: 8 }}>字段列表</Typography.Text>
      <List
        size="small"
        dataSource={fields}
        renderItem={(field) => (
          <List.Item
            key={field.name}
            onClick={() => onSelect?.(field.name)}
            style={{
              cursor: onSelect ? 'pointer' : undefined,
              background: selectedField === field.name ? '#f0f0ff' : undefined,
              padding: '6px 12px',
              borderRadius: 4,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%' }}>
              <Tag color={typeColors[field.display_type]} style={{ margin: 0, flexShrink: 0 }}>
                {typeLabels[field.display_type]}
              </Tag>
              <Typography.Text ellipsis>{field.name}</Typography.Text>
            </div>
          </List.Item>
        )}
      />
    </div>
  );
}
