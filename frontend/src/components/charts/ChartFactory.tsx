import { lazy, Suspense } from 'react';
import { Card, Spin } from 'antd';
import type { ChartConfig } from '../../types';

const HistogramChart = lazy(() => import('./HistogramChart'));
const BarChart = lazy(() => import('./BarChart'));
const PieChart = lazy(() => import('./PieChart'));
const CorrelationHeatmap = lazy(() => import('./CorrelationHeatmap'));
const BoxPlotChart = lazy(() => import('./BoxPlotChart'));
const CrossTabView = lazy(() => import('./CrossTabView'));
const ScatterChart = lazy(() => import('./ScatterChart'));
const TimeSeriesChart = lazy(() => import('./TimeSeriesChart'));

interface Props {
  chart: ChartConfig;
}

function ChartFallback() {
  return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}><Spin /></div>;
}

export default function ChartFactory({ chart }: Props) {
  const renderChart = () => {
    switch (chart.type) {
      case 'histogram': {
        const d = chart.data as { bins: number[]; counts: number[] };
        return <HistogramChart bins={d.bins} counts={d.counts} />;
      }
      case 'bar': {
        const d = chart.data as { categories: string[]; counts: number[] };
        return <BarChart categories={d.categories} counts={d.counts} />;
      }
      case 'pie': {
        const d = chart.data as { categories: string[]; counts: number[] };
        return <PieChart categories={d.categories} counts={d.counts} />;
      }
      case 'heatmap': {
        const d = chart.data as { fields: string[]; matrix: (number | null)[][] };
        return <CorrelationHeatmap fields={d.fields} matrix={d.matrix} />;
      }
      case 'boxplot': {
        return <BoxPlotChart fieldName={chart.field} boxplot={chart.data as any} />;
      }
      case 'crosstab': {
        return <CrossTabView data={chart.data as any} />;
      }
      case 'scatter': {
        return <ScatterChart pairs={(chart.data as any)?.pairs || []} />;
      }
      case 'timeseries': {
        return <TimeSeriesChart data={chart.data as any} />;
      }
      default:
        return <div>不支持的图表类型</div>;
    }
  };

  return (
    <Card title={<div className="drag-handle" style={{ cursor: 'grab' }}>⣿ {chart.title}</div>} size="small" style={{ height: '100%' }}>
      <Suspense fallback={<ChartFallback />}>
        {renderChart()}
      </Suspense>
    </Card>
  );
}
