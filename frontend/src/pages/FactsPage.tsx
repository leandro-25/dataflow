import { useState, useEffect } from 'react';
import { Plus, Box, Play, Eye, Trash2, Check, X } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { factsApi, catalogApi } from '../api';
import { Fact } from '../types';
import toast from 'react-hot-toast';
import clsx from 'clsx';

const getStatusBadge = (status: string) => {
  const styles = {
    valid: 'bg-green-100 text-green-800',
    invalid: 'bg-red-100 text-red-800',
    pending: 'bg-gray-100 text-gray-800',
    running: 'bg-blue-100 text-blue-800 animate-pulse',
    error: 'bg-red-100 text-red-800',
  };
  const labels = {
    valid: 'Válido', invalid: 'Inválido', pending: 'Pendente', running: 'Executando', error: 'Erro',
  };
  return (
    <span className={clsx('px-2 py-1 rounded-full text-xs font-medium', styles[status as keyof typeof styles] || styles.pending)}>
      {labels[status as keyof typeof labels] || status}
    </span>
  );
};

export function FactsPage() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewData, setPreviewData] = useState<{ columns: string[], data: any[], total_rows: number } | null>(null);
  const [editingFact, setEditingFact] = useState<Fact | null>(null);
  const [formData, setFormData] = useState({
    name: '', source_table: '', target_table: '', grain: '',
    dimension_links: [] as any[], measures: [] as string[],
    mode: 'visual' as 'visual' | 'sql' | 'yaml', custom_sql: '',
  });
  const [measureInput, setMeasureInput] = useState('');
  const [dimLinkInput, setDimLinkInput] = useState({ dimension_table: '', fact_column: '', dimension_column: '' });

  const { data: facts, isLoading } = useQuery('facts', factsApi.list);

  const { data: catalogTables } = useQuery('catalogTables', () => catalogApi.listTables().then(res => res.tables || []), {
    staleTime: 60000,
  });
  const availableTables = catalogTables ? catalogTables.map(t => t.name) : [];
  const availableDimensionTables = availableTables.filter(t => t.startsWith('dim_'));

  const createMutation = useMutation(factsApi.create, {
    onSuccess: () => { queryClient.invalidateQueries('facts'); setIsModalOpen(false); resetForm(); toast.success('Fato criado!'); },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro'); },
  });

  const updateMutation = useMutation(({ id, data }: { id: string; data: any }) => factsApi.update(id, data), {
    onSuccess: () => { queryClient.invalidateQueries('facts'); setIsModalOpen(false); setEditingFact(null); resetForm(); toast.success('Atualizado!'); },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro'); },
  });

  const deleteMutation = useMutation(factsApi.delete, {
    onSuccess: () => { queryClient.invalidateQueries('facts'); toast.success('Removido!'); },
  });

  const runMutation = useMutation(factsApi.run, {
    onSuccess: (data) => { queryClient.invalidateQueries('facts'); toast.success(`Executado! ${data.rows_affected} linhas`); },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro'); },
  });

  const previewMutation = useMutation(factsApi.preview, {
    onSuccess: (data) => { setPreviewData(data); setPreviewModalOpen(true); },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro no preview'); },
  });

  const resetForm = () => {
    setFormData({ name: '', source_table: '', target_table: '', grain: '', dimension_links: [], measures: [], mode: 'visual', custom_sql: '' });
    setEditingFact(null);
    setMeasureInput('');
    setDimLinkInput({ dimension_table: '', fact_column: '', dimension_column: '' });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingFact) {
      updateMutation.mutate({ id: editingFact.id, data: formData });
    } else {
      createMutation.mutate(formData as any);
    }
  };

  const addMeasure = () => {
    if (measureInput.trim()) {
      setFormData({ ...formData, measures: [...formData.measures, measureInput.trim()] });
      setMeasureInput('');
    }
  };

  const removeMeasure = (index: number) => {
    setFormData({ ...formData, measures: formData.measures.filter((_, i) => i !== index) });
  };

  const addDimensionLink = () => {
    if (dimLinkInput.dimension_table.trim() && dimLinkInput.fact_column.trim()) {
      setFormData({
        ...formData,
        dimension_links: [...formData.dimension_links, {
          dimension_table: dimLinkInput.dimension_table.trim(),
          fact_column: dimLinkInput.fact_column.trim(),
          dimension_column: dimLinkInput.dimension_column.trim() || dimLinkInput.fact_column.trim(),
        }],
      });
      setDimLinkInput({ dimension_table: '', fact_column: '', dimension_column: '' });
    }
  };

  const removeDimensionLink = (index: number) => {
    setFormData({ ...formData, dimension_links: formData.dimension_links.filter((_, i) => i !== index) });
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Fatos</h1>
          <p className="text-gray-600 mt-1">Crie tabelas de fatos para métricas e análises</p>
        </div>
        <button onClick={() => setIsModalOpen(true)} className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg font-medium transition-colors">
          <Plus size={20} /> Novo Fato
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : facts && facts.length > 0 ? (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nome</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Origem</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Destino</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Granularidade</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ações</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {facts.map((fact) => (
                <tr key={fact.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{fact.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600"><code className="bg-gray-100 px-2 py-1 rounded">{fact.source_table}</code></td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600"><code className="bg-gray-100 px-2 py-1 rounded">{fact.target_table}</code></td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600 text-sm">{fact.grain}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{getStatusBadge(fact.status)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <button onClick={() => previewMutation.mutate(fact.id)} className="text-blue-600 hover:text-blue-800 mr-3" title="Preview"><Eye size={18} /></button>
                    <button onClick={() => runMutation.mutate(fact.id)} disabled={runMutation.isLoading} className="text-green-600 hover:text-green-800 mr-3 disabled:opacity-50" title="Executar"><Play size={18} /></button>
                     <button onClick={() => { setEditingFact(fact); setFormData({
                       name: fact.name, source_table: fact.source_table, target_table: fact.target_table,
                       grain: fact.grain, dimension_links: fact.dimension_links || [], measures: fact.measures || [],
                       mode: fact.mode, custom_sql: fact.custom_sql || ''
                     }); setDimLinkInput({ dimension_table: '', fact_column: '', dimension_column: '' }); setIsModalOpen(true); }} className="text-primary-600 hover:text-primary-800 mr-3" title="Editar">
                       <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path></svg>
                     </button>
                    <button onClick={() => deleteMutation.mutate(fact.id)} className="text-red-600 hover:text-red-800" title="Remover"><Trash2 size={18} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <Box className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Nenhum fato configurado</h3>
          <button onClick={() => setIsModalOpen(true)} className="text-primary-600 hover:text-primary-700 font-medium">Criar primeiro fato</button>
        </div>
      )}

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-900">{editingFact ? 'Editar' : 'Novo'} Fato</h2>
              <button onClick={() => { setIsModalOpen(false); resetForm(); }} className="text-gray-400 hover:text-gray-600"><X size={24} /></button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
                  <input type="text" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" required pattern="[a-zA-Z0-9_]+" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Tabela Origem *</label>
                  <select value={formData.source_table} onChange={(e) => setFormData({ ...formData, source_table: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" required>
                    <option value="">Selecione...</option>
                    {availableTables.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tabela Destino *</label>
                <input type="text" value={formData.target_table} onChange={(e) => setFormData({ ...formData, target_table: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" required placeholder="fato_nome" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Granularidade *</label>
                <input type="text" value={formData.grain} onChange={(e) => setFormData({ ...formData, grain: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" required placeholder="ex: Uma linha por venda" />
              </div>
               <div>
                 <label className="block text-sm font-medium text-gray-700 mb-1">Medidas</label>
                 <div className="flex gap-2 mb-2">
                   <input type="text" value={measureInput} onChange={(e) => setMeasureInput(e.target.value)} className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" placeholder="Nome da coluna" />
                   <button type="button" onClick={addMeasure} className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium">Adicionar</button>
                 </div>
                 <div className="flex flex-wrap gap-2">
                   {formData.measures.map((m, i) => (
                     <span key={i} className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                       {m}
                       <button type="button" onClick={() => removeMeasure(i)} className="hover:text-blue-600"><X size={14} /></button>
                     </span>
                   ))}
                 </div>
               </div>
               <div>
                 <label className="block text-sm font-medium text-gray-700 mb-1">Links de Dimensao</label>
                 <div className="grid grid-cols-3 gap-2 mb-3">
                   <select value={dimLinkInput.dimension_table} onChange={(e) => setDimLinkInput({ ...dimLinkInput, dimension_table: e.target.value })} className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" placeholder="Tabela dimensao">
                     <option value="">Dimensao...</option>
                     {availableDimensionTables.map(t => <option key={t} value={t}>{t}</option>)}
                   </select>
                   <input type="text" value={dimLinkInput.fact_column} onChange={(e) => setDimLinkInput({ ...dimLinkInput, fact_column: e.target.value })} className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" placeholder="Coluna do fato" />
                   <input type="text" value={dimLinkInput.dimension_column} onChange={(e) => setDimLinkInput({ ...dimLinkInput, dimension_column: e.target.value })} className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" placeholder="Coluna da dimensao" />
                 </div>
                 <div className="flex gap-2 mb-2">
                   <button type="button" onClick={addDimensionLink} disabled={!dimLinkInput.dimension_table || !dimLinkInput.fact_column} className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium disabled:opacity-50">Adicionar Link</button>
                 </div>
                 <div className="flex flex-col gap-2">
                   {formData.dimension_links.map((link, i) => (
                     <span key={i} className="inline-flex items-center justify-between px-3 py-2 bg-purple-100 text-purple-800 rounded-lg text-sm">
                       <span>
                         {link.dimension_table && <span className="font-medium">{link.dimension_table}</span>}
                         {link.fact_column && <span> . {link.fact_column}</span>}
                         {link.dimension_column && <span>  &#8594;  {link.dimension_column}</span>}
                       </span>
                       <button type="button" onClick={() => removeDimensionLink(i)} className="hover:text-purple-600"><X size={14} /></button>
                     </span>
                   ))}
                 </div>
               </div>
              <div className="pt-4 flex justify-end gap-3">
                <button type="button" onClick={() => { setIsModalOpen(false); resetForm(); }} className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium">Cancelar</button>
                <button type="submit" disabled={createMutation.isLoading || updateMutation.isLoading} className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium disabled:opacity-50">
                  {(createMutation.isLoading || updateMutation.isLoading) ? <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div> : <Check size={18} />}
                  {editingFact ? 'Salvar' : 'Criar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {previewModalOpen && previewData && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl mx-4 max-h-[90vh] overflow-hidden">
            <div className="flex justify-between items-center p-6 border-b">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Preview</h2>
                <p className="text-sm text-gray-600">{previewData.total_rows} linhas</p>
              </div>
              <button onClick={() => setPreviewModalOpen(false)} className="text-gray-400 hover:text-gray-600"><X size={24} /></button>
            </div>
            <div className="overflow-auto max-h-[60vh]">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>{previewData.columns.map((col) => <th key={col} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{col}</th>)}</tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {previewData.data.map((row, idx) => (
                    <tr key={idx}>{previewData.columns.map((col) => <td key={col} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{row[col] === null ? <span className="text-gray-400 italic">null</span> : String(row[col])}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="p-6 border-t flex justify-end">
              <button onClick={() => setPreviewModalOpen(false)} className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium">Fechar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
