import { useMemo, useState } from 'react';
import { GridLayout, useContainerWidth } from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import { GripVertical, Trash2 } from 'lucide-react';
import clsx from 'clsx';
import {
  ComponenteDashboard, ALTURA_PADRAO, LARGURA_PADRAO,
  gerarId, normalizarComponentes, paraGrid
} from './layoutUtils';
import { renderComponente } from './componentRenderer';

const PALETA = [
  { type: 'kpi', label: 'KPI' },
  { type: 'chart_line', label: 'Linha' },
  { type: 'chart_bar', label: 'Barras' },
  { type: 'chart_pie', label: 'Pizza' },
  { type: 'chart_area', label: 'Área' },
  { type: 'table', label: 'Tabela' },
  { type: 'text', label: 'Texto' },
];

interface DashboardEditorProps {
  value: any[];
  onChange: (componentes: ComponenteDashboard[]) => void;
}

function configPadrao(type: string): any {
  switch (type) {
    case 'kpi':
      return { label: 'Novo KPI', value: '0' };
    case 'chart_line':
    case 'chart_bar':
    case 'chart_area':
      return {
        title: 'Gráfico',
        data: [
          { name: 'Jan', value: 400 },
          { name: 'Fev', value: 300 },
          { name: 'Mar', value: 600 },
        ],
      };
    case 'chart_pie':
      return {
        title: 'Distribuição',
        data: [
          { name: 'A', value: 400 },
          { name: 'B', value: 300 },
          { name: 'C', value: 300 },
        ],
      };
    case 'table':
      return {
        title: 'Dados',
        columns: ['Coluna 1', 'Coluna 2'],
        data: [
          { 'Coluna 1': 'A1', 'Coluna 2': 'B1' },
          { 'Coluna 1': 'A2', 'Coluna 2': 'B2' },
        ],
      };
    case 'text':
      return { title: 'Título', content: 'Conteúdo do texto...' };
    default:
      return {};
  }
}

export function DashboardEditor({ value, onChange }: DashboardEditorProps) {
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const { width, containerRef } = useContainerWidth();

  const componentes = useMemo(
    () => normalizarComponentes(value),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [JSON.stringify(value)]
  );

  const emitir = (novos: ComponenteDashboard[]) => onChange(novos);

  const adicionar = (type: string) => {
    const maxY = componentes.reduce((mx, c) => Math.max(mx, c.y + c.h), 0);
    const novo: ComponenteDashboard = {
      id: gerarId(),
      type,
      config: configPadrao(type),
      x: 0,
      y: maxY,
      w: LARGURA_PADRAO,
      h: ALTURA_PADRAO,
      width: LARGURA_PADRAO,
    };
    setSelecionado(novo.id);
    emitir([...componentes, novo]);
  };

  const remover = (id: string) => {
    if (selecionado === id) setSelecionado(null);
    emitir(componentes.filter((c) => c.id !== id));
  };

  const atualizarConfig = (id: string, patch: Record<string, any>) => {
    emitir(componentes.map((c) => (c.id === id ? { ...c, config: { ...c.config, ...patch } } : c)));
  };

  const aoMudarLayout = (layout: any[]) => {
    const map = new Map(layout.map((l) => [l.i, l]));
    emitir(
      componentes.map((c) => {
        const l = map.get(c.id);
        if (!l) return c;
        return { ...c, x: Math.round(l.x), y: Math.round(l.y), w: Math.round(l.w), h: Math.round(l.h), width: Math.round(l.w) };
      })
    );
  };

  const sel = componentes.find((c) => c.id === selecionado) || null;

  return (
    <div className="flex gap-4 items-start">
      {/* Paleta */}
      <div className="w-40 shrink-0 space-y-2">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Componentes</h4>
        <div className="grid grid-cols-2 gap-2">
          {PALETA.map((p) => (
            <button
              key={p.type}
              type="button"
              onClick={() => adicionar(p.type)}
              className="px-2 py-2 text-xs font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:border-primary-400 hover:text-primary-700 transition-colors"
            >
              {p.label}
            </button>
          ))}
        </div>
        <p className="text-[11px] text-gray-400 leading-snug">
          Clique para adicionar. Arraste pelo cabeçalho e redimensione pelos cantos.
        </p>
      </div>

      {/* Canvas */}
      <div className="flex-1 min-w-0">
        <div ref={containerRef}>
          {componentes.length === 0 ? (
            <div className="dash-canvas rounded-xl py-20 text-center text-gray-500 border border-gray-300">
              Adicione componentes pela paleta à esquerda
            </div>
          ) : (
            <GridLayout
              width={width || 900}
              layout={paraGrid(componentes)}
              cols={12}
              rowHeight={60}
              margin={[12, 12]}
              containerPadding={[8, 8]}
              onLayoutChange={aoMudarLayout}
              dragConfig={{ handle: '.dash-drag-handle' }}
              className="dash-canvas rounded-xl"
            >
              {componentes.map((c) => (
                <div
                  key={c.id}
                  onClick={() => setSelecionado(c.id)}
                  className={clsx(
                    'flex flex-col h-full dash-card rounded-lg overflow-hidden',
                    selecionado === c.id ? 'ring-2 ring-primary-500' : ''
                  )}
                >
                  <div
                    className={clsx(
                      'dash-drag-handle flex items-center justify-between px-2 py-1 cursor-move select-none',
                      selecionado === c.id ? 'bg-primary-600 text-white' : 'bg-slate-700 text-slate-100'
                    )}
                  >
                    <span className="flex items-center gap-1 text-[11px] font-medium">
                      <GripVertical size={12} />
                      {PALETA.find((p) => p.type === c.type)?.label || c.type}
                    </span>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); remover(c.id); }}
                      className="hover:text-red-400"
                      title="Remover"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                  <div className="flex-1 min-h-0 bg-gray-100/40" style={{ minHeight: 0 }}>
                    {renderComponente(c, 0)}
                  </div>
                </div>
              ))}
            </GridLayout>
          )}
        </div>
      </div>

      {/* Painel de propriedades */}
      <div className="w-64 shrink-0 border border-gray-200 rounded-lg p-3 space-y-3 bg-gray-50 max-h-[70vh] overflow-y-auto">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Propriedades</h4>
        {!sel && <p className="text-xs text-gray-400">Selecione um componente no canvas para editar.</p>}
        {sel && (
          <>
            <div>
              <label className="block text-[11px] font-medium text-gray-500 mb-1">Tipo</label>
              <input disabled value={sel.type} className="w-full px-2 py-1 border rounded text-xs bg-gray-100" />
            </div>
            {(sel.type === 'kpi') && (
              <>
                <CampoTexto label="Rótulo" valor={sel.config.label} onChange={(v) => atualizarConfig(sel.id, { label: v })} />
                <CampoTexto label="Valor" valor={sel.config.value} onChange={(v) => atualizarConfig(sel.id, { value: v })} />
                <CampoTexto label="Variação (%)" valor={String(sel.config.change ?? '')} onChange={(v) => atualizarConfig(sel.id, { change: v === '' ? undefined : Number(v) })} />
              </>
            )}
            {(sel.type.startsWith('chart') || sel.type === 'table' || sel.type === 'text') && (
              <CampoTexto label="Título" valor={sel.config.title} onChange={(v) => atualizarConfig(sel.id, { title: v })} />
            )}
            {sel.type === 'text' && (
              <div>
                <label className="block text-[11px] font-medium text-gray-500 mb-1">Conteúdo</label>
                <textarea
                  rows={4}
                  value={sel.config.content}
                  onChange={(e) => atualizarConfig(sel.id, { content: e.target.value })}
                  className="w-full px-2 py-1 border rounded text-xs"
                />
              </div>
            )}
            {(sel.type.startsWith('chart')) && (
              <>
                <div>
                  <label className="block text-[11px] font-medium text-gray-500 mb-1">Dados JSON ([{'{name,value}'}])</label>
                  <textarea
                    rows={5}
                    className="w-full px-2 py-1 border rounded text-[11px] font-mono"
                    value={JSON.stringify(sel.config.data || [], null, 1)}
                    onChange={(e) => {
                      try { atualizarConfig(sel.id, { data: JSON.parse(e.target.value) }); } catch { /* ignora json parcial */ }
                    }}
                  />
                </div>
                <label className="flex items-center gap-2 text-xs text-gray-700">
                  <input
                    type="checkbox"
                    checked={sel.config.mostrar_legenda !== false}
                    onChange={(e) => atualizarConfig(sel.id, { mostrar_legenda: e.target.checked })}
                    className="rounded"
                  />
                  Mostrar legenda
                </label>
                {sel.type === 'chart_pie' && (
                  <label className="flex items-center gap-2 text-xs text-gray-700">
                    <input
                      type="checkbox"
                      checked={sel.config.mostrar_rotulos !== false}
                      onChange={(e) => atualizarConfig(sel.id, { mostrar_rotulos: e.target.checked })}
                      className="rounded"
                    />
                    Rótulos nas fatias
                  </label>
                )}
                <CampoTexto
                  label="Máx. de itens (vazio = todos; excesso vira 'Outros')"
                  valor={String(sel.config.limite_itens ?? '')}
                  onChange={(v) => atualizarConfig(sel.id, { limite_itens: v === '' ? undefined : Math.max(0, parseInt(v) || 0) })}
                />
              </>
            )}
            {sel.type === 'table' && (
              <>
                <CampoTexto label="Colunas (vírgula)" valor={(sel.config.columns || []).join(', ')} onChange={(v) => atualizarConfig(sel.id, { columns: v.split(',').map((x: string) => x.trim()).filter(Boolean) })} />
                <div>
                  <label className="block text-[11px] font-medium text-gray-500 mb-1">Linhas JSON</label>
                  <textarea
                    rows={5}
                    className="w-full px-2 py-1 border rounded text-[11px] font-mono"
                    value={JSON.stringify(sel.config.data || [], null, 1)}
                    onChange={(e) => {
                      try { atualizarConfig(sel.id, { data: JSON.parse(e.target.value) }); } catch { /* ignora json parcial */ }
                    }}
                  />
                </div>
              </>
            )}
            <div className="pt-2 border-t">
              <button
                type="button"
                onClick={() => remover(sel.id)}
                className="text-xs text-red-600 hover:text-red-800 font-medium"
              >
                Remover componente
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function CampoTexto({ label, valor, onChange }: { label: string; valor: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="block text-[11px] font-medium text-gray-500 mb-1">{label}</label>
      <input
        type="text"
        value={valor ?? ''}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-2 py-1 border rounded text-xs"
      />
    </div>
  );
}
