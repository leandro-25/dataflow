import { useEffect, useMemo, useState } from 'react';
import { useQuery } from 'react-query';
import { X, ChevronLeft, ChevronRight, Sparkles, Check, Wand2, Clock } from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';
import { sourcesApi, ingestionsApi, Source } from '../../api';

interface IngestionWizardProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

const AGENDAMENTOS = [
  { id: 'manual', label: 'Manual', desc: 'Executar somente quando eu clicar', cron: '', habilitado: false },
  { id: 'hourly', label: 'A cada hora', desc: 'No minuto 0 de cada hora', cron: '0 * * * *', habilitado: true },
  { id: 'daily', label: 'Diário às 8h', desc: 'Todos os dias às 08:00', cron: '0 8 * * *', habilitado: true },
  { id: 'weekly', label: 'Semanal (segunda 8h)', desc: 'Toda segunda-feira às 08:00', cron: '0 8 * * 1', habilitado: true },
  { id: 'custom', label: 'Personalizado (cron)', desc: 'Expressão cron avançada', cron: '', habilitado: true },
];

export function IngestionWizard({ open, onClose, onCreated }: IngestionWizardProps) {
  const [etapa, setEtapa] = useState(1);
  const [fonteId, setFonteId] = useState<string>('');
  const [tabela, setTabela] = useState<string>('');
  const [nome, setNome] = useState('');
  const [templateId, setTemplateId] = useState<string>('');
  const [agendamento, setAgendamento] = useState('manual');
  const [cronCustom, setCronCustom] = useState('*/30 * * * *');
  const [incrementalOn, setIncrementalOn] = useState(false);
  const [colunaControle, setColunaControle] = useState('');
  const [testando, setTestando] = useState(false);
  const [amostra, setAmostra] = useState<{ columns: string[]; data: any[]; total_rows: number } | null>(null);

  const { data: sources } = useQuery('sources', sourcesApi.list, { enabled: open });
  const { data: templates } = useQuery('templates-wizard', ingestionsApi.getTemplates, { enabled: open });
  const { data: existentes } = useQuery('ingestions-light-wiz', () => ingestionsApi.list(), { enabled: open });

  const fonte: Source | undefined = useMemo(
    () => (sources || []).find((s) => s.id === fonteId),
    [sources, fonteId]
  );

  const { data: tabelasResp } = useQuery(
    ['wizard-tables', fonteId],
    () => sourcesApi.listTables(fonteId!),
    { enabled: !!fonteId && etapa >= 2 }
  );
  const tabelas: string[] | undefined = Array.isArray(tabelasResp)
    ? (tabelasResp as unknown as string[])
    : ((tabelasResp as any)?.tables);

  useEffect(() => {
    if (!open) {
      setEtapa(1); setFonteId(''); setTabela(''); setNome(''); setTemplateId('');
      setAgendamento('manual'); setIncrementalOn(false); setColunaControle(''); setAmostra(null);
    }
  }, [open]);

  const sugerirNome = (tabelaOuArquivo: string) => {
    const base = (tabelaOuArquivo.split(/[\\/]/).pop() || '')
      .replace(/\.[^.]+$/, '')
      .replace(/[^a-zA-Z0-9_]/g, '_')
      .toLowerCase();
    if (!base) return '';
    let candidato = `raw_${base}`;
    let n = 2;
    const usados = new Set((existentes || []).map((i) => i.name));
    while (usados.has(candidato)) { candidato = `raw_${base}_${n}`; n += 1; }
    return candidato;
  };

  useEffect(() => {
    if (etapa >= 3 && tabela && !nome) setNome(sugerirNome(tabela));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [etapa, tabela]);

  const analisarArquivo = async () => {
    if (!fonte) return;
    const caminho = fonte.config?.file_path as string | undefined;
    if (!caminho) { toast.error('Fonte sem caminho de arquivo'); return; }
    try {
      if (fonte.type === 'csv') {
        const d = await ingestionsApi.detectFileFormat(caminho);
        toast.success(`CSV: delimitador "${d.delimiter}" · ${d.encoding}`);
      } else if (fonte.type === 'xml') {
        const d = await ingestionsApi.analyzeXmlStructure(caminho);
        const tag = d.potential_row_elements?.[0]?.tag;
        toast.success(tag ? `XML: elemento de linha "${tag}"` : `XML: ${d.unique_tags} tags únicas`);
      } else if (fonte.type === 'json') {
        const d = await ingestionsApi.analyzeJsonStructure(caminho);
        toast.success(`JSON: ${d.array_length ?? '?'} registros no nível raiz`);
      } else {
        toast.info('Análise automática disponível para CSV, XML e JSON');
      }
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Falha na análise do arquivo');
    }
  };

  const testarExtracao = async () => {
    setTestando(true);
    setAmostra(null);
    try {
      const res = await ingestionsApi.dryRun({
        source_id: fonteId,
        config: { mode: 'table', table: tabela },
        limit: 5,
      });
      setAmostra(res);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Falha no teste de extração');
    } finally {
      setTestando(false);
    }
  };

  const salvar = async () => {
    const preset = AGENDAMENTOS.find((a) => a.id === agendamento)!;
    const cronFinal = agendamento === 'custom' ? cronCustom.trim() : preset.cron;
    try {
      await ingestionsApi.create({
        name: nome,
        source_id: fonteId,
        config: { mode: 'table', table: tabela, target_table: nome },
        schedule: cronFinal || undefined,
        schedule_enabled: !!cronFinal,
        incremental_config: incrementalOn && colunaControle
          ? { enabled: true, control_column: colunaControle } : {},
        tags: ['assistente'],
      });
      toast.success(`Ingestão "${nome}" criada${cronFinal ? ' e agendada' : ''}!`);
      onCreated();
      onClose();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Erro ao criar ingestão');
    }
  };

  if (!open) return null;

  const podeAvancar =
    etapa === 1 ? !!fonteId :
    etapa === 2 ? !!tabela :
    etapa === 3 ? /^[a-zA-Z0-9_]+$/.test(nome) :
    etapa === 4 ? (agendamento !== 'custom' || /^[0-9*/,-]+$/.test(cronCustom.replace(/\s/g, ''))) : true;

  return (
    <div className="fixed inset-0 z-[70] bg-black bg-opacity-50 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl mx-4 max-h-[92vh] flex flex-col">
        {/* Cabeçalho */}
        <div className="flex justify-between items-center p-5 border-b">
          <div>
            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <Wand2 size={18} className="text-primary-600" /> Nova Ingestão — Assistente
            </h2>
            <div className="flex items-center gap-1.5 mt-2">
              {[1, 2, 3, 4, 5].map((n) => (
                <div key={n} className={clsx('w-7 h-1.5 rounded-full', n <= etapa ? 'bg-primary-600' : 'bg-gray-200')} />
              ))}
              <span className="text-xs text-gray-500 ml-1">
                {['Fonte', 'O quê importar', 'Destino', 'Agendamento', 'Revisão'][etapa - 1]}
              </span>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X size={22} /></button>
        </div>

        {/* Conteúdo */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {etapa === 1 && (
            <>
              <p className="text-sm text-gray-600">De onde vêm os dados?</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {(sources || []).map((s) => (
                  <button key={s.id} type="button"
                    onClick={() => { setFonteId(s.id); setTabela(''); setNome(''); }}
                    className={clsx('text-left p-3 rounded-xl border-2 transition-all',
                      fonteId === s.id ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-primary-300')}>
                    <div className="font-semibold text-sm">{s.name}</div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {s.type} · <span className={s.status === 'valid' ? 'text-green-600' : 'text-red-500'}>
                        {s.status === 'valid' ? 'conexão ok' : s.status}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </>
          )}

          {etapa === 2 && (
            <>
              <p className="text-sm text-gray-600">Qual tabela/recurso da fonte <b>{fonte?.name}</b> você quer importar?</p>
              {fonte?.type === 'csv' || fonte?.type === 'xml' || fonte?.type === 'json' ? (
                <button type="button" onClick={analisarArquivo}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100 rounded-lg">
                  <Sparkles size={13} /> ✨ Analisar o arquivo primeiro
                </button>
              ) : null}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {(tabelas || []).map((t) => (
                  <button key={t} type="button"
                    onClick={() => { setTabela(t); setNome(''); }}
                    className={clsx('px-3 py-2 rounded-lg border-2 text-left text-sm font-mono transition-all truncate',
                      tabela === t ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-primary-300')}>
                    📄 {t}
                  </button>
                ))}
                {!tabelas && <p className="text-sm text-gray-400">Carregando recursos...</p>}
                {tabelas && tabelas.length === 0 && <p className="text-sm text-gray-400">Nenhum recurso listado — digite manualmente abaixo.</p>}
              </div>
              {tabelas && tabelas.length === 0 && (
                <input value={tabela} onChange={(e) => setTabela(e.target.value)} placeholder="nome do recurso"
                  className="w-full px-3 py-2 border rounded-lg text-sm" />
              )}
            </>
          )}

          {etapa === 3 && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome da ingestão / tabela de destino *</label>
                <input value={nome} onChange={(e) => setNome(e.target.value)}
                  className={clsx('w-full px-3 py-2 border rounded-lg font-mono text-sm',
                    nome && !/^[a-zA-Z0-9_]+$/.test(nome) ? 'border-red-400' : '')}
                  placeholder="raw_exemplo" />
                <p className="text-xs text-gray-400 mt-1">Será criada a tabela <b>{nome || '…'}</b> no warehouse.</p>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Começar de um modelo (opcional)</label>
                <select value={templateId} onChange={(e) => setTemplateId(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm">
                  <option value="">Nenhum</option>
                  {(templates || []).map((t: any) => (
                    <option key={t.id} value={t.id}>{t.name} — {t.description}</option>
                  ))}
                </select>
              </div>
            </>
          )}

          {etapa === 4 && (
            <>
              <p className="text-sm text-gray-600 flex items-center gap-2"><Clock size={15} /> Quando os dados devem ser atualizados?</p>
              <div className="space-y-2">
                {AGENDAMENTOS.map((a) => (
                  <button key={a.id} type="button"
                    onClick={() => setAgendamento(a.id)}
                    className={clsx('w-full text-left px-3 py-2.5 rounded-lg border-2 transition-all',
                      agendamento === a.id ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-primary-300')}>
                    <div className="font-medium text-sm">{a.label}</div>
                    <div className="text-xs text-gray-500">{a.desc}</div>
                  </button>
                ))}
              </div>
              {agendamento === 'custom' && (
                <input value={cronCustom} onChange={(e) => setCronCustom(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg font-mono text-sm" placeholder="*/30 * * * *" />
              )}
              <div className="border-t pt-3 space-y-2">
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input type="checkbox" checked={incrementalOn} onChange={(e) => setIncrementalOn(e.target.checked)} className="rounded" />
                  Importar somente registros novos (carga incremental)
                </label>
                {incrementalOn && (
                  <input value={colunaControle} onChange={(e) => setColunaControle(e.target.value)}
                    placeholder="coluna de controle (ex: data_atualizacao)"
                    className="w-full px-3 py-2 border rounded-lg text-sm" />
                )}
              </div>
            </>
          )}

          {etapa === 5 && (
            <>
              <div className="border rounded-lg p-4 bg-gray-50 space-y-1.5 text-sm">
                <Resumo r="Fonte" v={`${fonte?.name} (${fonte?.type})`} />
                <Resumo r="Recurso" v={tabela} />
                <Resumo r="Destino" v={`tabela ${nome}`} />
                <Resumo r="Agendamento" v={
                  agendamento === 'manual' ? 'Manual'
                  : agendamento === 'custom' ? `Cron: ${cronCustom}`
                  : AGENDAMENTOS.find((a) => a.id === agendamento)?.label || ''
                } />
                {incrementalOn && <Resumo r="Incremental" v={`por ${colunaControle || '(coluna a definir)'}`} />}
                {templateId && <Resumo r="Template" v={templates?.find((t: any) => t.id === templateId)?.name || ''} />}
              </div>

              <div className="flex items-center gap-2">
                <button type="button" onClick={testarExtracao} disabled={testando}
                  className="flex items-center gap-1 px-3 py-2 text-sm font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100 rounded-lg disabled:opacity-50">
                  <Sparkles size={14} /> {testando ? 'Testando...' : 'Testar extração agora (sem salvar)'}
                </button>
                {amostra && <span className="text-xs text-green-600">✓ {amostra.total_rows} linhas de amostra</span>}
              </div>

              {amostra && (
                <div className="border rounded-lg overflow-auto max-h-56">
                  <table className="min-w-full text-xs divide-y divide-gray-200">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>{amostra.columns.map((c) => <th key={c} className="px-2 py-1.5 text-left font-semibold text-gray-600 whitespace-nowrap">{c}</th>)}</tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {amostra.data.map((row, i) => (
                        <tr key={i}>{amostra.columns.map((c) => <td key={c} className="px-2 py-1 text-gray-700 whitespace-nowrap max-w-[180px] truncate">{String(row[c] ?? '')}</td>)}</tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>

        {/* Rodapé */}
        <div className="px-5 py-4 border-t flex justify-between bg-white rounded-b-xl">
          <button type="button" disabled={etapa === 1} onClick={() => setEtapa(etapa - 1)}
            className="flex items-center gap-1 px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium text-sm disabled:opacity-40">
            <ChevronLeft size={16} /> Voltar
          </button>
          {etapa < 5 ? (
            <button type="button" disabled={!podeAvancar} onClick={() => setEtapa(etapa + 1)}
              className="flex items-center gap-1 px-4 py-2 bg-primary-600 text-white rounded-lg font-medium text-sm disabled:opacity-40">
              Continuar <ChevronRight size={16} />
            </button>
          ) : (
            <button type="button" onClick={salvar} disabled={!nome || !fonteId || !tabela}
              className="flex items-center gap-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium text-sm disabled:opacity-40">
              <Check size={16} /> Criar ingestão{agendamento !== 'manual' ? ' agendada' : ''}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function Resumo({ r, v }: { r: string; v?: string }) {
  return (
    <div className="flex gap-2">
      <span className="text-gray-500 w-28 shrink-0">{r}:</span>
      <span className="font-medium text-gray-800 break-all">{v || '—'}</span>
    </div>
  );
}
