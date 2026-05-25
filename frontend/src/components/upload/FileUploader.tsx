import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { Upload, message, Card, Button, Space, Typography, Spin } from 'antd';
import { InboxOutlined, DatabaseOutlined } from '@ant-design/icons';
import { uploadFile, loadSample } from '../../api/client';
import { useSessionStore } from '../../stores/sessionStore';

const { Dragger } = Upload;
const { Title, Text, Paragraph } = Typography;

export default function FileUploader() {
  const navigate = useNavigate();
  const setSession = useSessionStore((s) => s.setSession);
  const [uploading, setUploading] = useState(false);

  const uploadMutation = useMutation({
    mutationFn: uploadFile,
    onSuccess: (res) => {
      if (res.success) {
        setSession(res.data.session_id, res.data.fields);
        navigate(`/preview/${res.data.session_id}`);
      } else {
        message.error(res.error || '上传失败');
      }
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail || err?.message || '上传失败，请检查文件格式';
      message.error(String(detail));
    },
    onSettled: () => setUploading(false),
  });

  const loadSampleMutation = useMutation({
    mutationFn: loadSample,
    onSuccess: (res) => {
      if (res.success) {
        setSession(res.data.session_id, res.data.fields);
        navigate(`/preview/${res.data.session_id}`);
      }
    },
  });

  const handleUpload = useCallback((file: File) => {
    setUploading(true);
    uploadMutation.mutate(file);
    return false;
  }, [uploadMutation]);

  return (
    <div style={{ maxWidth: 700, margin: '40px auto' }}>
      <Card>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={3}>上传你的数据文件</Title>
          <Text type="secondary">支持 CSV、Excel 格式</Text>
        </div>

        <Dragger
          accept=".csv,.xlsx,.xls"
          disabled={uploading}
          beforeUpload={handleUpload}
          showUploadList={false}
        >
          {uploading ? (
            <Spin tip="正在上传并分析..." />
          ) : (
            <>
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p className="ant-upload-text">点击或拖拽文件到此区域</p>
              <p className="ant-upload-hint">支持 CSV、Excel 文件，最大 500MB</p>
            </>
          )}
        </Dragger>
      </Card>

      <Card style={{ marginTop: 24 }}>
        <div style={{ textAlign: 'center' }}>
          <Space direction="vertical" size="middle">
            <DatabaseOutlined style={{ fontSize: 32, color: '#6366f1' }} />
            <div>
              <Title level={4} style={{ margin: 0 }}>还没有数据？</Title>
              <Paragraph type="secondary" style={{ marginTop: 8 }}>
                加载示例数据集，立即体验分析功能
              </Paragraph>
            </div>
            <Button
              type="primary"
              size="large"
              loading={loadSampleMutation.isPending}
              onClick={() => loadSampleMutation.mutate('sales_data')}
            >
              加载示例数据
            </Button>
          </Space>
        </div>
      </Card>
    </div>
  );
}
