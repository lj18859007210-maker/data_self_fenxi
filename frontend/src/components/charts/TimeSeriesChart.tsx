import ReactEChartsCore from 'echarts-for-react';

interface TimeSeriesData {
  time_field: string;
  value_field: string;
  dates: string[];
  original: (number | null)[];
  trend?: (number | null)[];
  seasonal?: (number | null)[];
  residual?: (number | null)[];
  period?: number;
}

interface Props {
  data: TimeSeriesData;
  height?: number;
}

export default function TimeSeriesChart({ data, height = 250 }: Props) {
  const option = {
    tooltip: {
      trigger: 'axis' as const,
      formatter: (params: any[]) => {
        const date = params[0]?.axisValue || '';
        let html = `<strong>${date}</strong><br/>`;
        params.forEach((p: any) => {
          if (p.value !== null && p.value !== undefined) {
            html += `${p.marker} ${p.seriesName}: ${p.value}<br/>`;
          }
        });
        return html;
      },
    },
    legend: {
      data: ['原始值', '趋势', '季节', '残差'].filter((_, i) =>
        i === 0 || (i === 1 && data.trend) || (i === 2 && data.seasonal) || (i === 3 && data.residual)
      ),
      bottom: 0,
    },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category' as const,
      data: data.dates,
      axisLabel: { rotate: 45, fontSize: 10, interval: Math.max(Math.floor(data.dates.length / 20), 1) },
    },
    yAxis: { type: 'value' as const },
    dataZoom: [
      { type: 'inside' as const },
      { type: 'slider' as const, bottom: 30, height: 20 },
    ],
    series: [
      {
        name: '原始值',
        type: 'line',
        data: data.original,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#94a3b8', width: 1 },
      },
      ...(data.trend ? [{
        name: '趋势',
        type: 'line',
        data: data.trend,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#6366f1', width: 2 },
      }] : []),
      ...(data.seasonal ? [{
        name: '季节',
        type: 'line',
        data: data.seasonal,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#10b981', width: 1 },
      }] : []),
      ...(data.residual ? [{
        name: '残差',
        type: 'line',
        data: data.residual,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#f59e0b', width: 1 },
      }] : []),
    ],
  };

  return <ReactEChartsCore option={option} style={{ height }} />;
}
