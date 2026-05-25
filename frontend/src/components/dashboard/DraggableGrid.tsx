import { useCallback, useRef, useEffect, useState } from 'react';
import GridLayout, { verticalCompactor } from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import ChartFactory from '../charts/ChartFactory';
import type { Layout, LayoutItem } from 'react-grid-layout';
import type { ChartConfig } from '../../types';

interface Props {
  charts: ChartConfig[];
  onLayoutChange?: (layout: Layout) => void;
}

export default function DraggableGrid({ charts, onLayoutChange }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(1200);

  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.offsetWidth);
      }
    };
    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, []);

  const defaultLayout: Layout = charts.map((chart, i) => ({
    i: chart.id,
    x: (i % 2) * 6,
    y: Math.floor(i / 2) * 4,
    w: chart.type === 'heatmap' || chart.type === 'scatter' || chart.type === 'timeseries' ? 12 : 6,
    h: chart.type === 'heatmap' || chart.type === 'scatter' ? 5 : 4,
    minW: 3,
    minH: 3,
  } as LayoutItem));

  const [layout, setLayout] = useState<Layout>(defaultLayout);

  const handleLayoutChange = useCallback((newLayout: Layout) => {
    setLayout(newLayout);
    onLayoutChange?.(newLayout);
  }, [onLayoutChange]);

  return (
    <div ref={containerRef}>
      <GridLayout
        className="layout"
        layout={layout}
        width={containerWidth}
        onLayoutChange={handleLayoutChange}
        gridConfig={{ cols: 12, rowHeight: 80 }}
        dragConfig={{ handle: '.drag-handle' }}
        compactor={verticalCompactor}
      >
        {charts.map((chart) => (
          <div key={chart.id} style={{ overflow: 'hidden' }}>
            <ChartFactory chart={chart} />
          </div>
        ))}
      </GridLayout>
    </div>
  );
}
