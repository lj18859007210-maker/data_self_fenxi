import ReactEChartsCore from 'echarts-for-react';

interface ScatterPoint {
  x_field: string;
  y_field: string;
  points: [number, number][];
}

interface Props {
  pairs: ScatterPoint[];
  height?: number;
}

export default function ScatterChart({ pairs, height = 300 }: Props) {
  if (!pairs.length) return <div style={{ color: '#999', textAlign: 'center', padding: 20 }}>无数据</div>;

  const option = {
    tooltip: {
      trigger: 'item' as const,
      formatter: (p: any) => `${p.seriesName}<br/>${p.value[0]}, ${p.value[1]}`,
    },
    grid: { left: 60, right: 20, top: 20, bottom: 50 },
    legend: { show: pairs.length <= 8 },
    xAxis: { type: 'value' as const, name: pairs[0]?.x_field || '' },
    yAxis: { type: 'value' as const, name: pairs[0]?.y_field || '' },
    series: pairs.slice(0, 6).map((pair, i) => ({
      name: `${pair.x_field} / ${pair.y_field}`,
      type: 'scatter' as const,
      data: pair.points.slice(0, 3000), // Limit points per pair
      symbolSize: 4,
      itemStyle: { color: ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'][i] },
    })),
    dataZoom: [
      { type: 'inside' as const },
      { type: 'slider' as const, bottom: 10 },
    ],
  };

  return <ReactEChartsCore option={option} style={{ height }} />;
}
