import { useState } from 'react';
import { Plus, Box, Play, Eye, Trash2, Check, X } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { dimensionsApi } from '../api';
import { Dimension } from '../types';
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

export function DimensionsPage() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewData, setPreviewData] = useState<{ columns: string[], data: any[], total_rows: number } | null>(null);
  const [editingDimension, setEditingDimension] = useState<Dimension | null>(null);
  const [formData, setFormData] = useState({
    name: '', source_table: '', target_table: '', primary_key: '', surrogate_key: '',
    attributes: [] as string[], mode: 'visual' as 'visual' | 'sql' | 'yaml', custom_sql: '',
  });
  const [availableTables, setAvailableTables] = useState<string[]>([]);

  const { data: dimensions, isLoading } = useQuery('dimensions', dimensionsApi.list);

  // Simulação de tabelas disponíveis
  useState(() => {
    setAvailableTables(['stg_clientes', 'stg_produtos', 'stg_vendas']);
  });

  const createMutation = useMutation(dimensionsApi.create, {
    onSuccess: () => { queryClient.invalidateQueries('dimensions'); setIsModalOpen(false); resetForm(); toast.success('Dimensão criada!'); },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro'); },
  });

  const updateMutation = useMutation(({ id, data }: { id: string; data: any }) => dimensionsApi.update(id, data), {
    onSuccess: () => { queryClient.invalidateQueries('dimensions'); setIsModalOpen(false); setEditingDimension(null); resetForm(); toast.success('Atualizada!'); },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro'); },
  });

  const deleteMutation = useMutation(dimensionsApi.delete, {
    onSuccess: () => { queryClient.invalidateQueries('dimensions'); toast.success('Removida!'); },
  });

  const runMutation = useMutation(dimensionsApi.run, {
    onSuccess: (data) => { queryClient.invalidateQueries('dimensions'); toast.success(`Executada! ${data.rows_affected} linhas`); },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro'); },
  });

  const previewMutation = useMutation(dimensionsApi.preview, {
    onSuccess: (data) => { setPreviewData(data); setPreviewModalOpen(true); },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro no preview'); },
  });

  const resetForm = () => {
    setFormData({ name: '', source_table: '', target_table: '', primary_key: '', surrogate_key: '', attributes: [], mode: 'visual', custom_sql: '' });
    setEditingDimension(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingDimension) {
      updateMutation.mutate({ id: editingDimension.id, data: formData });
    } else {
      createMutation.mutate(formData as any);
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dimensões</h1>
          <p className="text-gray-600 mt-1">Crie dimensões para análise (clientes, produtos, datas, etc)</p>
        </div>
        <button onClick={() => setIsModalOpen(true)} className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg font-medium transition-colors">
          <Plus size={20} /> Nova Dimensão
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : dimensions && dimensions.length > 0 ? (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nome</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Origem</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Destino</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Chave</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ações</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {dimensions.map((dimension) => (
                <tr key={dimension.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{dimension.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600"><code className="bg-gray-100 px-2 py-1 rounded">{dimension.source_table}</code></td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600"><code className="bg-gray-100 px-2 py-1 rounded">{dimension.target_table}</code></td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                    {dimension.primary_key}
                    {dimension.surrogate_key && <span className="text-xs text-gray-400 ml-1">({dimension.surrogate_key})</span>}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">{getStatusBadge(dimension.status)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <button onClick={() => previewMutation.mutate(dimension.id)} className="text-blue-600 hover:text-blue-800 mr-3" title="Preview"><Eye size={18} /></button>
                    <button onClick={() => runMutation.mutate(dimension.id)} disabled={runMutation.isLoading} className="text-green-600 hover:text-green-800 mr-3 disabled:opacity-50" title="Executar"><Play size={18} /></button>
                    <button onClick={() => { setEditingDimension(dimension); setFormData({
                      name: dimension.name, source_table: dimension.source_table, target_table: dimension.target_table,
                      primary_key: dimension.primary_key, surrogate_key: dimension.surrogate_key || '',
                      attributes: dimension.attributes, mode: dimension.mode, custom_sql: dimension.custom_sql || ''
                    }); setIsModalOpen(true); }} className="text-primary-600 hover:text-primary-800 mr-3" title="Editar">
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path></svg>
                    </button>
                    <button onClick={() => deleteMutation.mutate(dimension.id)} className="text-red-600 hover:text-red-800" title="Remover"><Trash2 size={18} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <Box className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Nenhuma dimensão configurada</h3>
          <button onClick={() => setIsModalOpen(true)} className="text-primary-600 hover:text-primary-700 font-medium">Criar primeira dimensão</button>
        </div>
      )}

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-900">{editingDimension ? 'Editar' : 'Nova'} Dimensão</h2>
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
                <input type="text" value={formData.target_table} onChange={(e) => setFormData({ ...formData, target_table: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" required placeholder="dim_nome" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Chave Primária *</label>
                  <input type="text" value={formData.primary_key} onChange={(e) => setFormData({ ...formData, primary_key: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" required placeholder="ex: id_cliente" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Surrogate Key (opcional)</label>
                  <input type="text" value={formData.surrogate_key} onChange={(e) => setFormData({ ...formData, surrogate_key: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" placeholder="ex: sk_cliente" />
                </div>
              </div>
              <div className="pt-4 flex justify-end gap-3">
                <button type="button" onClick={() => { setIsModalOpen(false); resetForm(); }} className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium">Cancelar</button>
                <button type="submit" disabled={createMutation.isLoading || updateMutation.isLoading} className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium disabled:opacity-50">
                  {(createMutation.isLoading || updateMutation.isLoading) ? <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div> : <Check size={18} />}
                  {editingDimension ? 'Salvar' : 'Criar'}
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
