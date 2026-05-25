import ReactEChartsCore from 'echarts-for-react';

interface Props {
  categories: string[];
  counts: number[];
  height?: number;
}

const COLORS = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6'];

export default function PieChart({ categories, counts, height = 250 }: Props) {
  const option = {
    tooltip: { trigger: 'item' as const, formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['30%', '60%'],
      data: categories.map((name, i) => ({
        name,
        value: counts[i],
        itemStyle: { color: COLORS[i % COLORS.length] },
      })),
      label: { show: categories.length <= 10, formatter: '{b}' },
    }],
  };

  return <ReactEChartsCore option={option} style={{ height }} />;
}
