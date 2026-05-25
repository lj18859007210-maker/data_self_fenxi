import ReactEChartsCore from 'echarts-for-react';

interface Props {
  bins: number[];
  counts: number[];
  height?: number;
}

export default function HistogramChart({ bins, counts, height = 250 }: Props) {
  const labels = bins.slice(0, -1).map((v, i) =>
    `${v.toFixed(1)}-${bins[i + 1].toFixed(1)}`
  );

  const option = {
    tooltip: { trigger: 'axis' as const },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category' as const,
      data: labels,
      axisLabel: { rotate: 45, fontSize: 10, interval: Math.max(Math.floor(labels.length / 20), 1) },
    },
    yAxis: { type: 'value' as const },
    series: [{
      type: 'bar',
      data: counts,
      itemStyle: { color: '#6366f1' },
    }],
  };

  return <ReactEChartsCore option={option} style={{ height }} />;
}
