import FileUploader from '../components/upload/FileUploader';
import HistoryList from '../components/history/HistoryList';

export default function UploadPage() {
  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 64px)', maxWidth: 1200, margin: '0 auto', padding: '24px 16px', gap: 24 }}>
      <div style={{ width: 300, flexShrink: 0, background: '#fff', borderRadius: 8, overflow: 'hidden', border: '1px solid #f0f0f0' }}>
        <HistoryList />
      </div>
      <div style={{ flex: 1 }}>
        <FileUploader />
      </div>
    </div>
  );
}
