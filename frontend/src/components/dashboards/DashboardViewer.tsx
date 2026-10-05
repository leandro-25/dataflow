import { GridLayout, useContainerWidth } from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import { Dashboard } from '../../types';
import { normalizarComponentes, paraGrid } from './layoutUtils';
import { renderComponente } from './componentRenderer';

interface DashboardViewerProps {
  dashboard: Dashboard;
}

export function DashboardViewer({ dashboard }: DashboardViewerProps) {
  const { width, containerRef } = useContainerWidth();
  const componentes = normalizarComponentes(dashboard.layout);

  if (componentes.length === 0) {
    return (
      <div className="text-center py-16 bg-white rounded-lg border border-dashed border-gray-300">
        <p className="text-gray-400">Nenhum componente neste dashboard.</p>
      </div>
    );
  }

  return (
    <div ref={containerRef}>
      <GridLayout
        width={width || 1100}
        layout={paraGrid(componentes)}
        cols={12}
        rowHeight={70}
        margin={[12, 12]}
        containerPadding={[0, 0]}
        isDraggable={false}
        isResizable={false}
      >
        {componentes.map((c) => (
          <div key={c.id} className="overflow-hidden rounded-lg" style={{ height: '100%' }}>
            {renderComponente(c, 0)}
          </div>
        ))}
      </GridLayout>
    </div>
  );
}
