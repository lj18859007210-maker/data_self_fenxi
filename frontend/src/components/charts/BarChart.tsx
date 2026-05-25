import ReactEChartsCore from 'echarts-for-react';

interface Props {
  categories: string[];
  counts: number[];
  height?: number;
}

export default function BarChart({ categories, counts, height = 250 }: Props) {
  const option = {
    tooltip: { trigger: 'axis' as const },
    grid: { left: 60, right: 20, top: 20, bottom: 50 },
    xAxis: {
      type: 'category' as const,
      data: categories,
      axisLabel: { rotate: 45, fontSize: 10 },
    },
    yAxis: { type: 'value' as const },
    series: [{
      type: 'bar',
      data: counts,
      itemStyle: { color: '#06b6d4' },
    }],
  };

  return <ReactEChartsCore option={option} style={{ height }} />;
}
