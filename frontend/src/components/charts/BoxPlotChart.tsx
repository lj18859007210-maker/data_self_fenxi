import ReactEChartsCore from 'echarts-for-react';

interface BoxPlotData {
  min: number | null;
  q1: number | null;
  median: number | null;
  q3: number | null;
  max: number | null;
  outlier_values: number[];
  outlier_count: number;
}

interface Props {
  fieldName: string;
  boxplot: BoxPlotData;
  height?: number;
}

export default function BoxPlotChart({ fieldName, boxplot, height = 250 }: Props) {
  if (boxplot.min === null) {
    return (
      <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
        数据不足（至少需要 4 个非空值）
      </div>
    );
  }

  const scatterData = boxplot.outlier_values.map(v => [0, v]);

  const option = {
    tooltip: {
      trigger: 'item' as const,
      formatter: (p: any) => {
        if (p.seriesIndex === 0) {
          return `${fieldName}<br/>最小值: ${boxplot.min}<br/>Q1: ${boxplot.q1}<br/>中位数: ${boxplot.median}<br/>Q3: ${boxplot.q3}<br/>最大值: ${boxplot.max}`;
        }
        return `异常值: ${p.value[1]}`;
      },
    },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category' as const, data: [fieldName], axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value' as const },
    series: [
      {
        name: '箱线图',
        type: 'boxplot',
        data: [[boxplot.min, boxplot.q1, boxplot.median, boxplot.q3, boxplot.max]],
        itemStyle: { color: '#6366f1' },
      },
      {
        name: '异常值',
        type: 'scatter',
        data: scatterData,
        symbolSize: 6,
        itemStyle: { color: '#ef4444' },
      },
    ],
  };

  return <ReactEChartsCore option={option} style={{ height }} />;
}
