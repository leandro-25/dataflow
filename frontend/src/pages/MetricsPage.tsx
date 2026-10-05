import { useState } from 'react';
import { Plus, BarChart3, Play, Trash2, Check, X, Eye } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { metricsApi } from '../api';
import { Metric } from '../types';
import toast from 'react-hot-toast';
import clsx from 'clsx';

const getStatusBadge = (status: string) => {
  const styles = {
    valid: 'bg-green-100 text-green-800',
    invalid: 'bg-red-100 text-red-800',
    pending: 'bg-gray-100 text-gray-800',
  };
  const labels = {
    valid: 'Válido', invalid: 'Inválido', pending: 'Pendente',
  };
  return (
    <span className={clsx('px-2 py-1 rounded-full text-xs font-medium', styles[status as keyof typeof styles] || styles.pending)}>
      {labels[status as keyof typeof labels] || status}
    </span>
  );
};

const aggregationLabels: Record<string, string> = {
  sum: 'Soma', count: 'Contagem', avg: 'Média', min: 'Mínimo', max: 'Máximo', count_distinct: 'Contagem Distinta'
};

export function MetricsPage() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [queryModalOpen, setQueryModalOpen] = useState(false);
  const [queryResult, setQueryResult] = useState<{ value: any; formatted_value: string } | null>(null);
  const [editingMetric, setEditingMetric] = useState<Metric | null>(null);
  const [formData, setFormData] = useState({
    name: '', label: '', description: '', fact_table: '',
    aggregation: 'sum' as const, column_name: '',
    format: { type: 'number' as const, decimals: 2, prefix: '', suffix: '' }
  });
  const [availableTables, setAvailableTables] = useState<string[]>([]);

  const { data: metrics, isLoading } = useQuery('metrics', metricsApi.list);

  useState(() => {
    setAvailableTables(['fato_vendas', 'fato_pedidos', 'fato_transacoes']);
  });

  const createMutation = useMutation(metricsApi.create, {
    onSuccess: () => { queryClient.invalidateQueries('metrics'); setIsModalOpen(false); resetForm(); toast.success('Métrica criada!'); },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro'); },
  });

  const updateMutation = useMutation(({ id, data }: { id: string; data: any }) => metricsApi.update(id, data), {
    onSuccess: () => { queryClient.invalidateQueries('metrics'); setIsModalOpen(false); setEditingMetric(null); resetForm(); toast.success('Atualizada!'); },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro'); },
  });

  const deleteMutation = useMutation(metricsApi.delete, {
    onSuccess: () => { queryClient.invalidateQueries('metrics'); toast.success('Removida!'); },
  });

  const queryMutation = useMutation((id: string) => metricsApi.query(id), {
    onSuccess: (data) => { setQueryResult(data); setQueryModalOpen(true); },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro na consulta'); },
  });

  const resetForm = () => {
    setFormData({ name: '', label: '', description: '', fact_table: '', aggregation: 'sum', column_name: '', format: { type: 'number', decimals: 2, prefix: '', suffix: '' } });
    setEditingMetric(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingMetric) {
      updateMutation.mutate({ id: editingMetric.id, data: formData });
    } else {
      createMutation.mutate(formData as any);
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Métricas</h1>
          <p className="text-gray-600 mt-1">Defina métricas reutilizáveis para dashboards</p>
        </div>
        <button onClick={() => setIsModalOpen(true)} className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg font-medium transition-colors">
          <Plus size={20} /> Nova Métrica
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : metrics && metrics.length > 0 ? (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nome</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Label</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fato</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Agregação</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ações</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {metrics.map((metric) => (
                <tr key={metric.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{metric.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600">{metric.label}</td>
                  <td className="px-6 py-4 whitespace-nowrap"><code className="bg-gray-100 px-2 py-1 rounded">{metric.fact_table}</code></td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="uppercase text-xs font-medium bg-blue-100 text-blue-800 px-2 py-1 rounded">
                      {aggregationLabels[metric.aggregation] || metric.aggregation}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">{getStatusBadge(metric.status)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <button onClick={() => queryMutation.mutate(metric.id)} className="text-green-600 hover:text-green-800 mr-3" title="Executar">
                      <Play size={18} />
                    </button>
                    <button onClick={() => { setEditingMetric(metric); setFormData({
                      name: metric.name, label: metric.label, description: metric.description || '',
                      fact_table: metric.fact_table, aggregation: metric.aggregation,
                      column_name: metric.column_name || '', format: metric.format || { type: 'number', decimals: 2, prefix: '', suffix: '' }
                    }); setIsModalOpen(true); }} className="text-primary-600 hover:text-primary-800 mr-3" title="Editar">
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path></svg>
                    </button>
                    <button onClick={() => deleteMutation.mutate(metric.id)} className="text-red-600 hover:text-red-800" title="Remover"><Trash2 size={18} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <BarChart3 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Nenhuma métrica configurada</h3>
          <button onClick={() => setIsModalOpen(true)} className="text-primary-600 hover:text-primary-700 font-medium">Criar primeira métrica</button>
        </div>
      )}

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-900">{editingMetric ? 'Editar' : 'Nova'} Métrica</h2>
              <button onClick={() => { setIsModalOpen(false); resetForm(); }} className="text-gray-400 hover:text-gray-600"><X size={24} /></button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nome (ID) *</label>
                  <input type="text" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" required pattern="[a-zA-Z0-9_]+" placeholder="receita_total" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Label *</label>
                  <input type="text" value={formData.label} onChange={(e) => setFormData({ ...formData, label: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" required placeholder="Receita Total" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Descrição</label>
                <textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" rows={2} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Tabela Fato *</label>
                  <select value={formData.fact_table} onChange={(e) => setFormData({ ...formData, fact_table: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" required>
                    <option value="">Selecione...</option>
                    {availableTables.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Agregação *</label>
                  <select value={formData.aggregation} onChange={(e) => setFormData({ ...formData, aggregation: e.target.value as any })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" required>
                    <option value="sum">Soma (SUM)</option>
                    <option value="count">Contagem (COUNT)</option>
                    <option value="avg">Média (AVG)</option>
                    <option value="min">Mínimo (MIN)</option>
                    <option value="max">Máximo (MAX)</option>
                    <option value="count_distinct">Contagem Distinta</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Coluna</label>
                <input type="text" value={formData.column_name} onChange={(e) => setFormData({ ...formData, column_name: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" placeholder="Nome da coluna (deixe vazio para COUNT *)" />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Formato</label>
                  <select value={formData.format.type} onChange={(e) => setFormData({ ...formData, format: { ...formData.format, type: e.target.value as any } })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500">
                    <option value="number">Número</option>
                    <option value="currency">Moeda</option>
                    <option value="percent">Percentual</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Decimais</label>
                  <input type="number" value={formData.format.decimals} onChange={(e) => setFormData({ ...formData, format: { ...formData.format, decimals: parseInt(e.target.value) } })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" min={0} max={10} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Prefixo</label>
                  <input type="text" value={formData.format.prefix} onChange={(e) => setFormData({ ...formData, format: { ...formData.format, prefix: e.target.value } })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" placeholder="R$" />
                </div>
              </div>
              <div className="pt-4 flex justify-end gap-3">
                <button type="button" onClick={() => { setIsModalOpen(false); resetForm(); }} className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium">Cancelar</button>
                <button type="submit" disabled={createMutation.isLoading || updateMutation.isLoading} className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium disabled:opacity-50">
                  {(createMutation.isLoading || updateMutation.isLoading) ? <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div> : <Check size={18} />}
                  {editingMetric ? 'Salvar' : 'Criar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Query Result Modal */}
      {queryModalOpen && queryResult && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-900">Resultado da Métrica</h2>
              <button onClick={() => setQueryModalOpen(false)} className="text-gray-400 hover:text-gray-600"><X size={24} /></button>
            </div>
            <div className="p-6">
              <div className="text-center">
                <div className="text-4xl font-bold text-primary-600 mb-2">{queryResult.formatted_value}</div>
                <div className="text-sm text-gray-500">Valor bruto: {queryResult.value}</div>
              </div>
            </div>
            <div className="p-6 border-t flex justify-end">
              <button onClick={() => setQueryModalOpen(false)} className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium">Fechar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
