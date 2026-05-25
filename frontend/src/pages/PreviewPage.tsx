import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Card, Button, Space, Typography, Spin, Descriptions, message, Alert } from 'antd';
import { getPreview, updateFields, triggerAnalysis } from '../api/client';
import { useSessionStore } from '../stores/sessionStore';
import DataPreview from '../components/preview/DataPreview';
import FieldTypeEditor from '../components/preview/FieldTypeEditor';
import type { FieldType } from '../types';

const { Title, Text } = Typography;

export default function PreviewPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { setSession } = useSessionStore();
  const [analyzing, setAnalyzing] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['preview', sessionId],
    queryFn: () => getPreview(sessionId!),
    enabled: !!sessionId,
  });

  const sessionData = data?.data;

  useEffect(() => {
    if (sessionData) {
      setSession(sessionId!, sessionData.fields);
    }
  }, [sessionData, sessionId, setSession]);

  const updateMutation = useMutation({
    mutationFn: (updates: { name: string; display_type: FieldType }[]) =>
      updateFields(sessionId!, updates),
    onSuccess: () => message.success('字段类型已更新'),
  });

  const handleAnalyze = async () => {
    if (!sessionId) return;
    setAnalyzing(true);
    try {
      await triggerAnalysis(sessionId);
      navigate(`/dashboard/${sessionId}`);
    } catch {
      message.error('启动分析失败');
      setAnalyzing(false);
    }
  };

  if (isLoading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (error || !sessionData) return <Alert type="error" message="加载失败" />;

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={4} style={{ margin: 0 }}>{sessionData.filename}</Title>
            <Space>
              <Button onClick={() => navigate('/')}>重新选择</Button>
              <Button type="primary" size="large" loading={analyzing} onClick={handleAnalyze}>
                开始分析
              </Button>
            </Space>
          </div>
          <Descriptions size="small" column={4}>
            <Descriptions.Item label="行数">{sessionData.row_count?.toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="列数">{sessionData.column_count}</Descriptions.Item>
            <Descriptions.Item label="数值字段">
              {sessionData.fields.filter((f) => f.display_type === 'numeric').length}
            </Descriptions.Item>
            <Descriptions.Item label="类别字段">
              {sessionData.fields.filter((f) => f.display_type === 'category').length}
            </Descriptions.Item>
          </Descriptions>
        </Space>
      </Card>

      <Card title="字段类型配置" style={{ marginBottom: 16 }}>
        <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
          系统已自动推断字段类型，如有误可手动修改：
        </Text>
        <FieldTypeEditor
          fields={sessionData.fields}
          onChange={(updates) => updateMutation.mutate(updates)}
        />
      </Card>

      <Card title="数据预览（前100行）">
        <DataPreview
          columns={sessionData.fields.map((f: any) => f.name)}
          rows={sessionData.preview}
        />
      </Card>
    </div>
  );
}
