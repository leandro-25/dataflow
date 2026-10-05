import { useEffect, useMemo, useState } from 'react';
import { useQuery } from 'react-query';
import { X, ChevronLeft, ChevronRight, Sparkles, Check, Wand2, Play } from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';
import { stagingApi, catalogApi } from '../../api';

interface StagingWizardProps {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}

interface Transform {
  type: string;
  config: any;
}

const LABELS: Record<string, string> = {
  rename: 'Renomear', cast: 'Converter Tipo', filter: 'Filtrar', deduplicate: 'Remover Duplicatas',
  fill_null: 'Preencher Nulos', sort: 'Ordenar', limit: 'Limitar', add_column: 'Nova Coluna',
  remove_columns: 'Remover Colunas', select_columns: 'Selecionar Colunas', uppercase: 'MaiÃºsculas',
  lowercase: 'MinÃºsculas', trim: 'Trim', replace: 'Substituir', split: 'Dividir', merge: 'Juntar',
};

const RECEITAS = [
  { id: 'limpar', label: 'ðŸ§¹ Limpar textos (trim em tudo)' },
  { id: 'dedup', label: 'ðŸ“‘ Remover duplicatas' },
  { id: 'topn', label: 'ðŸ” Manter sÃ³ as 100 primeiras linhas' },
];

export function StagingWizard({ open, onClose, onSaved }: StagingWizardProps) {
  const [etapa, setEtapa] = useState(1);
  const [origem, setOrigem] = useState('');
  const [nomeDestino, setNomeDestino] = useState('');
  const [transforms, setTransforms] = useState<Transform[]>([]);
  const [novoTipo, setNovoTipo] = useState('');
  const [amostra, setAmostra] = useState<any | null>(null);
  const [testando, setTestando] = useState(false);
  const [executarAgora, setExecutarAgora] = useState(true);

  const { data: catalog } = useQuery('catalog-tables-wiz', catalogApi.listTables, { enabled: open });
  const tabelas = (catalog?.tables || []).filter((t: any) => t.rows > 0);

  const { data: schemaResp } = useQuery(
    ['stgw-schema', origem],
    () => catalogApi.getTableSchema(origem),
    { enabled: !!origem && etapa >= 2 }
  );
  const schema: any[] = useMemo(() => (schemaResp as any)?.schema || [], [schemaResp]);
  const colunasTexto = useMemo(() => schema.filter((c: any) => /VARCHAR|TEXT/i.test(c.type)).map((c: any) => c.name), [schema]);

  const sugestoesCasts = useMemo(() => {
    return schema
      .filter((c: any) => /VARCHAR|TEXT/i.test(c.type))
      .map((c: any): Transform | null => {
        if (/^(data|dt_)|_data$|_at$/i.test(c.name)) return { type: 'cast', config: { [c.name]: 'date' } };
        if (/valor|preco|total|limite|salario/i.test(c.name)) return { type: 'cast', config: { [c.name]: 'double' } };
        if (/quantidade|qtd|estoque|idade/i.test(c.name)) return { type: 'cast', config: { [c.name]: 'integer' } };
        return null;
      })
      .filter(Boolean) as Transform[];
  }, [schema]);

  const sugestoesPendentes = sugestoesCasts.filter(
    (s) => !transforms.some((t) => t.type === 'cast' && Object.keys(t.config)[0] === Object.keys(s.config)[0])
  );

  useEffect(() => {
    if (!open) {
      setEtapa(1); setOrigem(''); setNomeDestino(''); setTransforms([]); setAmostra(null); setExecutarAgora(true);
    }
  }, [open]);

  useEffect(() => {
    if (etapa >= 3 && origem && !nomeDestino) {
      const sufixo = origem.replace(/^(raw_|stg_)/i, '');
      setNomeDestino(`stg_${sufixo}`.replace(/[^a-zA-Z0-9_]/g, '_'));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [etapa, origem]);

  const adicionarReceita = (id: string) => {
    if (id === 'limpar') {
      if (colunasTexto.length === 0) { toast.error('Nenhuma coluna de texto nesta origem'); return; }
      setTransforms((prev) => [...prev, { type: 'trim', config: { columns: colunasTexto } }]);
      toast.success('Trim aplicado a todas as colunas de texto');
    } else if (id === 'dedup') {
      const primeira = schema[0]?.name || '';
      setTransforms((prev) => [...prev, { type: 'deduplicate', config: { keys: [primeira], keep: 'first' } }]);
      toast.success('DeduplicaÃ§Ã£o adicionada â€” ajuste a chave se precisar');
    } else if (id === 'topn') {
      setTransforms((prev) => [...prev, { type: 'limit', config: { rows: 100 } }]);
    }
  };

  const aplicarSugestoes = () => {
    setTransforms((prev) => [...prev.filter((t) => !(t.type === 'cast' && sugestoesPendentes.some((s) => Object.keys(s.config)[0] === Object.keys(t.config)[0]))), ...sugestoesPendentes]);
    toast.success(`${sugestoesPendentes.length} conversÃ£o(Ãµes) sugerida(s) aplicada(s)`);
  };

  const testar = async () => {
    setTestando(true);
    try {
      const res = await stagingApi.dryRun({ source_table: origem, transforms, limit: 20 });
      setAmostra(res);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Falha no teste');
      setAmostra(null);
    } finally {
      setTestando(false);
    }
  };

  const salvar = async () => {
    try {
      const criado = await stagingApi.create({
        name: nomeDestino,
        source_table: origem,
        target_table: nomeDestino,
        mode: 'visual',
        transforms,
      });
      if (executarAgora) {
        await stagingApi.run(criado.id);
        toast.success('Staging criado e executado!');
      } else {
        toast.success('Staging criado!');
      }
      onSaved();
      onClose();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Erro ao salvar');
    }
  };

  if (!open) return null;

  const podeAvancar =
    etapa === 1 ? !!origem :
    etapa === 2 ? transforms.length > 0 :
    /^[a-zA-Z0-9_]+$/.test(nomeDestino);

  return (
    <div className="fixed inset-0 z-[70] bg-black bg-opacity-50 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl mx-4 max-h-[92vh] flex flex-col">
        <div className="flex justify-between items-center p-5 border-b">
          <div>
            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <Wand2 size={18} className="text-primary-600" /> Novo Staging â€” Assistente
            </h2>
            <div className="flex items-center gap-1.5 mt-2">
              {[1, 2, 3, 4].map((n) => (
                <div key={n} className={clsx('w-8 h-1.5 rounded-full', n <= etapa ? 'bg-primary-600' : 'bg-gray-200')} />
              ))}
              <span className="text-xs text-gray-500 ml-1">{['Origem', 'TransformaÃ§Ãµes', 'Destino & Teste', 'Concluir'][etapa - 1]}</span>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X size={22} /></button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {etapa === 1 && (
            <>
              <p className="text-sm text-gray-600">Qual tabela do warehouse vocÃª quer transformar?</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-80 overflow-y-auto">
                {tabelas.map((t: any) => (
                  <button key={t.name} type="button"
                    onClick={() => { setOrigem(t.name); setNomeDestino(''); }}
                    className={clsx('px-3 py-2.5 rounded-lg border-2 text-left transition-all',
                      origem === t.name ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-primary-300')}>
                    <div className="font-mono text-sm font-medium truncate">ðŸ“„ {t.name}</div>
                    <div className="text-xs text-gray-500">{t.rows} linhas Â· {t.type}</div>
                  </button>
                ))}
              </div>
            </>
          )}

          {etapa === 2 && (
            <>
              <datalist id="wiz-colunas">
                {schema.map((c: any) => <option key={c.name} value={c.name} />)}
              </datalist>
              {/* Receitas prontas */}
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Receitas prontas</h4>
                <div className="flex flex-wrap gap-2">
                  {RECEITAS.map((r) => (
                    <button key={r.id} type="button" onClick={() => adicionarReceita(r.id)}
                      className="px-3 py-1.5 text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 rounded-lg">
                      {r.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* SugestÃµes automÃ¡ticas */}
              {sugestoesPendentes.length > 0 && (
                <div className="border border-indigo-200 bg-indigo-50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="flex items-center gap-1 text-sm font-medium text-indigo-800">
                      <Sparkles size={14} /> ConversÃµes de tipo sugeridas ({sugestoesPendentes.length})
                    </span>
                    <button type="button" onClick={aplicarSugestoes}
                      className="text-xs px-3 py-1 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
                      Aplicar todas
                    </button>
                  </div>
                  <ul className="text-xs text-indigo-700 space-y-0.5">
                    {sugestoesPendentes.map((s, i) => (
                      <li key={i}>â€¢ <b>{Object.keys(s.config)[0]}</b> â†’ {Object.values(s.config)[0] === 'date' ? 'Data' : Object.values(s.config)[0] === 'double' ? 'Decimal' : 'Inteiro'}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Adicionar manualmente */}
              <div className="flex gap-2 items-center">
                <select value={novoTipo} onChange={(e) => {
                  if (e.target.value) { setTransforms([...transforms, { type: e.target.value, config: {} }]); setNovoTipo(''); }
                }} className="text-sm border rounded px-2 py-1.5">
                  <option value="">+ Adicionar transformaÃ§Ã£o...</option>
                  {Object.entries(LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
                <span className="text-xs text-gray-400">arraste para reordenar</span>
              </div>

              {/* Lista ordenÃ¡vel com mini-forms */}
              {transforms.length === 0 && (
                <p className="text-sm text-gray-400 py-6 text-center border-2 border-dashed border-gray-200 rounded-xl">
                  Nenhuma transformaÃ§Ã£o â€” use receitas, sugestÃµes ou adicione acima
                </p>
              )}
              <div className="space-y-2">
                {transforms.map((tr, idx) => (
                  <div key={idx} draggable
                    onDragStart={(e) => e.dataTransfer.setData('text/plain', String(idx))}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => {
                      const from = Number(e.dataTransfer.getData('text/plain'));
                      if (isNaN(from) || from === idx) return;
                      const arr = [...transforms];
                      const [movido] = arr.splice(from, 1);
                      arr.splice(idx, 0, movido);
                      setTransforms(arr);
                    }}
                    className='border rounded p-2.5 bg-white cursor-move transition-all'>
                    <MiniForm tr={tr} idx={idx}
                      onChangeConfig={(config) => setTransforms(transforms.map((t, i) => i === idx ? { ...t, config } : t))}
                      onRemover={() => setTransforms(transforms.filter((_, i) => i !== idx))}
                      onMover={(dir) => {
                        const alvo = idx + dir;
                        if (alvo < 0 || alvo >= transforms.length) return;
                        const arr = [...transforms];
                        [arr[idx], arr[alvo]] = [arr[alvo], arr[idx]];
                        setTransforms(arr);
                      }} />
                  </div>
                ))}
              </div>
            </>
          )}

          {etapa === 3 && (
            <>
              <Resumo r="Origem" v={`${origem}`} />
              <Resumo r="Destino" v={`tabela ${nomeDestino}`} />
              <Resumo r="TransformaÃ§Ãµes" v={`${transforms.length}`} />
              <div className="flex items-center gap-2 pt-1">
                <button type="button" onClick={testar} disabled={testando}
                  className="flex items-center gap-1 px-3 py-2 text-sm font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100 rounded-lg disabled:opacity-50">
                  <Sparkles size={14} /> {testando ? 'Testando...' : 'Testar resultado (sem salvar)'}
                </button>
                {amostra && (
                  <span className={clsx('text-xs font-medium', amostra.total_rows !== amostra.source_total_rows ? 'text-amber-600' : 'text-green-600')}>
                    {amostra.source_total_rows} â†’ {amostra.total_rows} linhas na amostra de 20
                  </span>
                )}
              </div>

              {amostra && (
                <>
                  <details className="border rounded-lg p-3">
                    <summary className="cursor-pointer text-xs font-medium text-gray-600">Ver SQL gerado</summary>
                    <pre className="mt-2 text-[11px] font-mono bg-gray-900 text-green-300 p-3 rounded overflow-x-auto whitespace-pre-wrap">{amostra.sql}</pre>
                  </details>
                  <div className="border rounded-lg overflow-auto max-h-56">
                    <table className="min-w-full text-xs divide-y divide-gray-200">
                      <thead className="bg-gray-50 sticky top-0">
                        <tr>{amostra.columns.map((col: string) => <th key={col} className="px-2 py-1.5 text-left font-semibold text-gray-600 whitespace-nowrap">{col}</th>)}</tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {amostra.data.map((row: any, i: number) => (
                          <tr key={i}>{amostra.columns.map((col: string) => (
                            <td key={col} className="px-2 py-1 text-gray-700 whitespace-nowrap max-w-[180px] truncate">{row[col] === null ? <i className="text-gray-400">null</i> : String(row[col])}</td>
                          ))}</tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </>
          )}

          {etapa === 4 && (
            <div className="space-y-3">
              <div className="border rounded-lg p-4 bg-gray-50 space-y-1.5 text-sm">
                <Resumo r="Origem" v={origem} />
                <Resumo r="Destino" v={`tabela ${nomeDestino}`} />
                <Resumo r="TransformaÃ§Ãµes" v={`${transforms.length}: ${transforms.map((t) => LABELS[t.type] || t.type).join(' â†’ ')}`} />
              </div>
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input type="checkbox" checked={executarAgora} onChange={(e) => setExecutarAgora(e.target.checked)} className="rounded" />
                Executar agora apÃ³s criar (gera a tabela destino imediatamente)
              </label>
            </div>
          )}
        </div>

        <div className="px-5 py-4 border-t flex justify-between bg-white rounded-b-xl">
          <button type="button" disabled={etapa === 1} onClick={() => setEtapa(etapa - 1)}
            className="flex items-center gap-1 px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium text-sm disabled:opacity-40">
            <ChevronLeft size={16} /> Voltar
          </button>
          {etapa < 4 ? (
            <button type="button" disabled={!podeAvancar} onClick={() => setEtapa(etapa + 1)}
              className="flex items-center gap-1 px-4 py-2 bg-primary-600 text-white rounded-lg font-medium text-sm disabled:opacity-40">
              Continuar <ChevronRight size={16} />
            </button>
          ) : (
            <button type="button" onClick={salvar}
              className="flex items-center gap-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium text-sm">
              {executarAgora ? <Play size={15} /> : <Check size={15} />}
              Criar{executarAgora ? ' e executar' : ''}
            </button>
          )}
        </div>
      </div>
    </div>
  );

}

function MiniForm({ tr, idx, onChangeConfig, onRemover, onMover }: {
  tr: Transform; idx: number;
  onChangeConfig: (config: any) => void;
  onRemover: () => void; onMover: (dir: number) => void;
}) {
  const { type, config } = tr;
  const cols = (v: string) => v.split(',').map((x) => x.trim()).filter(Boolean);
  const inputCls = 'px-2 py-1 text-sm border rounded';

  const Par = ({ k, v, onK, onV, ph }: any) => (
    <div className="flex gap-2 items-center">
      <input list="wiz-colunas" className={clsx(inputCls, 'flex-1')} placeholder={ph?.[0]} value={k} onChange={(e) => onK(e.target.value)} />
      <span className="text-gray-400 text-sm">â†’</span>
      <input className={clsx(inputCls, 'flex-1')} placeholder={ph?.[1]} value={v} onChange={(e) => onV(e.target.value)} />
    </div>
  );

  switch (type) {
    case 'rename': {
      const k = Object.keys(config)[0] || '', v = Object.values(config)[0] || '';
      return <Par k={k} v={String(v)} onK={(nv) => onChangeConfig({ [nv]: v })} onV={(nv) => onChangeConfig({ [k]: nv })} ph={['coluna_atual', 'novo_nome']} />;
    }
    case 'cast': {
      const k = Object.keys(config)[0] || '', v = Object.values(config)[0] || 'date';
      return (
        <div className="flex gap-2 items-center">
          <input list="wiz-colunas" className={clsx(inputCls, 'flex-1')} placeholder="coluna" value={k} onChange={(e) => onChangeConfig({ [e.target.value]: v })} />
          <select className={inputCls} value={v} onChange={(e) => onChangeConfig({ [k]: e.target.value })}>
            <option value="date">Data</option><option value="double">Decimal</option>
            <option value="integer">Inteiro</option><option value="text">Texto</option>
          </select>
        </div>
      );
    }
    case 'filter':
      return (
        <div className="flex gap-2 items-center flex-wrap">
          <input list="wiz-colunas" className={inputCls} placeholder="coluna" value={config.column || ''} onChange={(e) => onChangeConfig({ ...config, column: e.target.value })} />
          <select className={inputCls} value={config.operator || '>'} onChange={(e) => onChangeConfig({ ...config, operator: e.target.value })}>
            <option value=">">maior que</option><option value="<">menor que</option>
            <option value=">=">maior ou igual</option><option value="<=">menor ou igual</option>
            <option value="!=">diferente de</option><option value="contains">contÃ©m</option>
          </select>
          <input className={clsx(inputCls, 'flex-1')} placeholder="valor" value={config.value ?? ''}
            onChange={(e) => { const n = Number(e.target.value); onChangeConfig({ ...config, value: e.target.value !== '' && !isNaN(n) ? n : e.target.value }); }} />
        </div>
      );
    case 'deduplicate':
      return (
        <div className="flex gap-2 items-center">
          <span className="text-xs text-gray-500">chave:</span>
          <input list="wiz-colunas" className={clsx(inputCls, 'flex-1')} placeholder="coluna-chave" value={(config.keys || []).join(', ')} onChange={(e) => onChangeConfig({ keys: cols(e.target.value) })} />
        </div>
      );
    case 'trim':
      return <input list="wiz-colunas" className={clsx(inputCls, 'w-full')} placeholder="colunas de texto (vÃ­rgula)" value={(config.columns || []).join(', ')} onChange={(e) => onChangeConfig({ columns: cols(e.target.value) })} />;
    case 'limit':
      return (
        <div className="flex gap-2 items-center">
          <span className="text-xs text-gray-500">manter</span>
          <input type="number" min={1} className={clsx(inputCls, 'w-24')} value={config.rows || ''} onChange={(e) => onChangeConfig({ rows: parseInt(e.target.value) || undefined })} />
          <span className="text-xs text-gray-500">linhas</span>
        </div>
      );
    default:
      return (
        <textarea rows={2} className={clsx(inputCls, 'w-full font-mono text-[11px]')}
          placeholder='{"campo": "valor"}'
          value={JSON.stringify(config)}
          onChange={(e) => { try { onChangeConfig(JSON.parse(e.target.value)); } catch { /* parcial */ } }} />
      );
  }
}

function Resumo({ r, v }: { r: string; v?: string }) {
  return (
    <div className="flex gap-2">
      <span className="text-gray-500 w-28 shrink-0">{r}:</span>
      <span className="font-medium text-gray-800 break-all">{v || 'â€”'}</span>
    </div>
  );
}

