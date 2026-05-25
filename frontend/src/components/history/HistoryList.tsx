import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { List, Button, Typography, Popconfirm, message, Tag, Space } from 'antd';
import { DeleteOutlined, HistoryOutlined, FileTextOutlined } from '@ant-design/icons';
import { getHistory, deleteSession } from '../../api/client';

const { Text } = Typography;

const stateColors: Record<string, string> = {
  uploaded: 'blue',
  preview: 'cyan',
  analyzing: 'processing',
  complete: 'green',
  error: 'red',
};

const stateLabels: Record<string, string> = {
  uploaded: '已上传',
  preview: '预览',
  analyzing: '分析中',
  complete: '完成',
  error: '错误',
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function HistoryList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['history'],
    queryFn: getHistory,
    refetchOnMount: true,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSession,
    onSuccess: () => {
      message.success('已删除');
      queryClient.invalidateQueries({ queryKey: ['history'] });
    },
  });

  const sessions = data?.data ?? [];

  return (
    <div>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #f0f0f0' }}>
        <Space>
          <HistoryOutlined />
          <Text strong>历史记录</Text>
        </Space>
      </div>
      <List
        loading={isLoading}
        dataSource={sessions}
        locale={{ emptyText: '暂无历史记录' }}
        renderItem={(item) => (
          <List.Item
            style={{ padding: '8px 16px', cursor: 'pointer' }}
            onClick={() => {
              if (item.state === 'complete') {
                navigate(`/dashboard/${item.id}`);
              } else if (item.state === 'preview') {
                navigate(`/preview/${item.id}`);
              }
            }}
            actions={[
              <Popconfirm
                key="delete"
                title="确定删除这条记录？"
                onConfirm={(e) => {
                  e?.stopPropagation();
                  deleteMutation.mutate(item.id);
                }}
                onCancel={(e) => e?.stopPropagation()}
              >
                <Button
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={(e) => e.stopPropagation()}
                />
              </Popconfirm>,
            ]}
          >
            <List.Item.Meta
              avatar={<FileTextOutlined style={{ fontSize: 18, color: '#6366f1' }} />}
              title={
                <Space>
                  <Text style={{ fontSize: 13 }}>{item.filename}</Text>
                  <Tag color={stateColors[item.state] || 'default'} style={{ fontSize: 11 }}>
                    {stateLabels[item.state] || item.state}
                  </Tag>
                </Space>
              }
              description={
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {item.row_count} 行 x {item.column_count} 列
                  {item.file_size > 0 && ` · ${formatSize(item.file_size)}`}
                </Text>
              }
            />
          </List.Item>
        )}
      />
    </div>
  );
}
