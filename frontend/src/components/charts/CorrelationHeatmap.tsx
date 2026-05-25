import ReactEChartsCore from 'echarts-for-react';

interface Props {
  fields: string[];
  matrix: (number | null)[][];
  height?: number;
}

export default function CorrelationHeatmap({ fields = [], matrix = [], height = 300 }: Props) {
  if (!fields.length || !matrix.length) {
    return <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>暂无相关性数据</div>;
  }
  const data: [number, number, number][] = [];
  for (let i = 0; i < fields.length; i++) {
    for (let j = 0; j < fields.length; j++) {
      if (matrix[i]?.[j] !== null && matrix[i]?.[j] !== undefined) {
        data.push([j, i, matrix[i][j] as number]);
      }
    }
  }

  const option = {
    tooltip: {
      position: 'top' as const,
      formatter: (p: { value: [number, number, number] }) =>
        `${fields[p.value[1]]} ~ ${fields[p.value[0]]}: ${p.value[2].toFixed(4)}`,
    },
    grid: { left: 80, right: 40, top: 20, bottom: 80 },
    xAxis: {
      type: 'category' as const,
      data: fields,
      axisLabel: { rotate: 45, fontSize: 10 },
      splitArea: { show: true },
    },
    yAxis: {
      type: 'category' as const,
      data: fields,
      axisLabel: { fontSize: 10 },
      splitArea: { show: true },
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['#ef4444', '#f5f5f5', '#6366f1'] },
    },
    series: [{
      type: 'heatmap',
      data,
      label: {
        show: fields.length <= 8,
        formatter: (p: { value: [number, number, number] }) => p.value[2].toFixed(2),
        fontSize: 11,
      },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.15)' },
      },
    }],
  };

  return <ReactEChartsCore option={option} style={{ height }} />;
}
