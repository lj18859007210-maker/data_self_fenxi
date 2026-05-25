import { useState } from 'react';
import { Button, Dropdown, message } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

export default function ExportButton() {
  const [exporting, setExporting] = useState(false);

  const handleExport = async (format: 'png' | 'pdf') => {
    setExporting(true);
    try {
      const el = document.getElementById('dashboard-content');
      if (!el) {
        message.error('未找到可导出的内容');
        return;
      }

      const canvas = await html2canvas(el, {
        useCORS: true,
        scale: 2,
        backgroundColor: '#f5f5f5',
      });

      if (format === 'png') {
        const link = document.createElement('a');
        link.download = `analysis-report-${Date.now()}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
        message.success('PNG 导出成功');
      } else {
        const imgData = canvas.toDataURL('image/png');
        const pdf = new jsPDF({
          orientation: canvas.width > canvas.height ? 'landscape' : 'portrait',
          unit: 'px',
          format: [canvas.width, canvas.height],
        });
        pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height);
        pdf.save(`analysis-report-${Date.now()}.pdf`);
        message.success('PDF 导出成功');
      }
    } catch {
      message.error('导出失败');
    } finally {
      setExporting(false);
    }
  };

  const items = [
    { key: 'png', label: '导出为 PNG', onClick: () => handleExport('png') },
    { key: 'pdf', label: '导出为 PDF', onClick: () => handleExport('pdf') },
  ];

  return (
    <Dropdown menu={{ items }} placement="bottomRight">
      <Button icon={<DownloadOutlined />} loading={exporting}>
        导出报告
      </Button>
    </Dropdown>
  );
}
