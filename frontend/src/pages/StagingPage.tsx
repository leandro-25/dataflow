import { useState } from 'react';
import { Plus, Filter, Play, Eye, Trash2, Check, X, GripVertical, Wand2 } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { stagingApi, catalogApi } from '../api';
import { Staging, Transform } from '../types';
import toast from 'react-hot-toast';
import clsx from 'clsx';
import { StagingWizard } from '../components/staging/StagingWizard';

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

const transformLabels: Record<string, string> = {
  rename: 'Renomear', cast: 'Converter Tipo', filter: 'Filtrar', deduplicate: 'Remover Duplicatas',
  fill_null: 'Preencher Nulos', sort: 'Ordenar', limit: 'Limitar', add_column: 'Nova Coluna',
  remove_columns: 'Remover Colunas', select_columns: 'Selecionar Colunas', uppercase: 'Maiúsculas',
  lowercase: 'Minúsculas', trim: 'Trim', replace: 'Substituir', split: 'Dividir', merge: 'Juntar',
};

export function StagingPage() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewData, setPreviewData] = useState<{ columns: string[], data: any[], total_rows: number } | null>(null);
  const [editingStaging, setEditingStaging] = useState<Staging | null>(null);
  const [formData, setFormData] = useState({
    name: '', source_table: '', target_table: '', mode: 'visual' as 'visual' | 'sql' | 'yaml', custom_sql: '',
  });
  const [transforms, setTransforms] = useState<Transform[]>([]);
  const [wizardOpen, setWizardOpen] = useState(false);

  const { data: stagings, isLoading } = useQuery('staging', stagingApi.list);
  const { data: transformTypes } = useQuery('transformTypes', stagingApi.getTransformTypes);
  const { data: catalog } = useQuery('catalog-tables-staging', catalogApi.listTables);

  const availableTables = (catalog?.tables || []).map(t => t.name);

  const createMutation = useMutation(stagingApi.create, {
    onSuccess: () => { queryClient.invalidateQueries('staging'); setIsModalOpen(false); resetForm(); toast.success('Staging criado!'); },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro'); },
  });

  const updateMutation = useMutation(({ id, data }: { id: string; data: any }) => stagingApi.update(id, data), {
    onSuccess: () => { queryClient.invalidateQueries('staging'); setIsModalOpen(false); setEditingStaging(null); resetForm(); toast.success('Atualizado!'); },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro'); },
  });

  const deleteMutation = useMutation(stagingApi.delete, {
    onSuccess: () => { queryClient.invalidateQueries('staging'); toast.success('Removido!'); },
  });

  const runMutation = useMutation(stagingApi.run, {
    onSuccess: (data) => { queryClient.invalidateQueries('staging'); toast.success(`Executado! ${data.rows_affected} linhas`); },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro'); },
  });

  const previewMutation = useMutation(stagingApi.preview, {
    onSuccess: (data) => { setPreviewData(data); setPreviewModalOpen(true); },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro no preview'); },
  });

  const resetForm = () => {
    setFormData({ name: '', source_table: '', target_table: '', mode: 'visual', custom_sql: '' });
    setTransforms([]);
    setEditingStaging(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data = { ...formData, transforms: formData.mode === 'visual' ? transforms : undefined };
    if (editingStaging) {
      updateMutation.mutate({ id: editingStaging.id, data });
    } else {
      createMutation.mutate(data as any);
    }
  };

  const addTransform = (type: string) => {
    const newTransform: Transform = { type, config: {} };
    setTransforms([...transforms, newTransform]);
  };

  const updateTransform = (index: number, config: any) => {
    const updated = [...transforms];
    updated[index] = { ...updated[index], config };
    setTransforms(updated);
  };

  const removeTransform = (index: number) => {
    setTransforms(transforms.filter((_, i) => i !== index));
  };

  // Drag and Drop handlers
  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;
    
    const newTransforms = [...transforms];
    const draggedItem = newTransforms[draggedIndex];
    newTransforms.splice(draggedIndex, 1);
    newTransforms.splice(index, 0, draggedItem);
    setTransforms(newTransforms);
    setDraggedIndex(index);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Staging</h1>
          <p className="text-gray-600 mt-1">Transforme e limpe dados brutos para staging</p>
        </div>
        <button onClick={() => setWizardOpen(true)} className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg font-medium transition-colors">
          <Wand2 size={20} /> Assistente
        </button>
        <button onClick={() => setIsModalOpen(true)} className="flex items-center gap-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 px-4 py-2 rounded-lg font-medium transition-colors">
          <Plus size={20} /> Novo Staging
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : stagings && stagings.length > 0 ? (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nome</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Origem</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Destino</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Transformações</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ações</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {stagings.map((staging) => (
                <tr key={staging.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{staging.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600"><code className="bg-gray-100 px-2 py-1 rounded">{staging.source_table}</code></td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600"><code className="bg-gray-100 px-2 py-1 rounded">{staging.target_table}</code></td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                    {staging.transforms.length} transformação{staging.transforms.length !== 1 ? 's' : ''}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">{getStatusBadge(staging.status)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <button onClick={() => previewMutation.mutate(staging.id)} className="text-blue-600 hover:text-blue-800 mr-3" title="Preview"><Eye size={18} /></button>
                    <button onClick={() => runMutation.mutate(staging.id)} disabled={runMutation.isLoading} className="text-green-600 hover:text-green-800 mr-3 disabled:opacity-50" title="Executar"><Play size={18} /></button>
                    <button onClick={() => { setEditingStaging(staging); setFormData({ name: staging.name, source_table: staging.source_table, target_table: staging.target_table, mode: staging.mode, custom_sql: staging.custom_sql || '' }); setTransforms(staging.transforms); setIsModalOpen(true); }} className="text-primary-600 hover:text-primary-800 mr-3" title="Editar">
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path></svg>
                    </button>
                    <button onClick={() => deleteMutation.mutate(staging.id)} className="text-red-600 hover:text-red-800" title="Remover"><Trash2 size={18} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <Filter className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Nenhum staging configurado</h3>
          <button onClick={() => setIsModalOpen(true)} className="text-primary-600 hover:text-primary-700 font-medium">Criar primeiro staging</button>
        </div>
      )}

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-900">{editingStaging ? 'Editar' : 'Novo'} Staging</h2>
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
                <input type="text" value={formData.target_table} onChange={(e) => setFormData({ ...formData, target_table: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500" required placeholder="stg_nome" />
              </div>

              {formData.source_table && <SchemaDatalist tabela={formData.source_table} />}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Modo</label>
                <div className="flex gap-4">
                  {['visual', 'sql'].map((m) => (
                    <label key={m} className="flex items-center">
                      <input type="radio" value={m} checked={formData.mode === m} onChange={(e) => setFormData({ ...formData, mode: e.target.value as any })} className="mr-2" />
                      {m === 'visual' ? 'Visual' : 'SQL'}
                    </label>
                  ))}
                </div>
              </div>

              {formData.mode === 'visual' ? (
                <div className="border rounded-lg p-4 space-y-4">
                  <div className="flex justify-between items-center">
                    <h3 className="font-medium">Transformações (arraste para reordenar)</h3>
                    <select onChange={(e) => { if (e.target.value) { addTransform(e.target.value); e.target.value = ''; } }} className="text-sm border rounded px-2 py-1">
                      <option value="">+ Adicionar...</option>
                      {transformTypes?.map((t) => <option key={t.type} value={t.type}>{t.label}</option>)}
                    </select>
                  </div>
                  
                  {transforms.map((transform, idx) => (
                    <div 
                      key={idx} 
                      draggable
                      onDragStart={() => handleDragStart(idx)}
                      onDragOver={(e) => handleDragOver(e, idx)}
                      onDragEnd={handleDragEnd}
                      className={clsx(
                        "border rounded p-3 bg-gray-50 cursor-move transition-all",
                        draggedIndex === idx && "opacity-50 border-primary-500"
                      )}
                    >
                      <div className="flex justify-between items-center mb-2">
                        <div className="flex items-center gap-2">
                          <GripVertical size={18} className="text-gray-400" />
                          <span className="font-medium">{transformLabels[transform.type] || transform.type}</span>
                          <span className="text-xs text-gray-400">({idx + 1})</span>
                        </div>
                        <div className="flex gap-1">
                          <button type="button" onClick={() => removeTransform(idx)} className="p-1 hover:bg-red-100 text-red-600 rounded"><X size={16} /></button>
                        </div>
                      </div>
                      <TransformConfig transform={transform} onChange={(config) => updateTransform(idx, config)} />
                    </div>
                  ))}
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">SQL Customizado</label>
                  <textarea value={formData.custom_sql} onChange={(e) => setFormData({ ...formData, custom_sql: e.target.value })} className="w-full px-3 py-2 border rounded-lg font-mono text-sm" rows={6} placeholder="SELECT * FROM _input..." />
                  <p className="text-xs text-gray-500 mt-1">Use _input para referenciar a tabela de origem</p>
                </div>
              )}

              <div className="pt-4 flex justify-end gap-3">
                <button type="button" onClick={() => { setIsModalOpen(false); resetForm(); }} className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium">Cancelar</button>
                <button type="submit" disabled={createMutation.isLoading || updateMutation.isLoading} className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium disabled:opacity-50">
                  {(createMutation.isLoading || updateMutation.isLoading) ? <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div> : <Check size={18} />}
                  {editingStaging ? 'Salvar' : 'Criar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Assistente guiado */}
      <StagingWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        onSaved={() => {
          queryClient.invalidateQueries('staging');
          queryClient.invalidateQueries('catalog-tables-staging');
          queryClient.invalidateQueries('catalog-tables');
        }}
      />

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

// Componente para configurar cada tipo de transformação
function TransformConfig({ transform, onChange, colunas }: { transform: Transform; onChange: (config: any) => void; colunas?: string[] }) {
  const { type, config } = transform;
  const colsLista = (v: string) => v.split(',').map(x => x.trim()).filter(Boolean);

  const CampoCol = ({ valor, onChangeV, placeholder }: any) => (
    <div className="flex-1">
      <input list="stg-colunas-origem" type="text" placeholder={placeholder || 'coluna'} className="w-full px-2 py-1 text-sm border rounded"
        value={valor} onChange={(e) => onChangeV(e.target.value)} />
    </div>
  );

  switch (type) {
    case 'rename':
      return (
        <div className="flex gap-2 items-center">
          <CampoCol valor={Object.keys(config)[0] || ''} onChangeV={(v) => onChange({ [v]: Object.values(config)[0] || '' })} placeholder="coluna_atual" />
          <span className="text-gray-400">→</span>
          <input type="text" placeholder="novo_nome" className="flex-1 px-2 py-1 text-sm border rounded" value={Object.values(config)[0] || ''} onChange={(e) => onChange({ [Object.keys(config)[0] || '']: e.target.value })} />
        </div>
      );
    case 'cast':
      return (
        <div className="flex gap-2 items-center">
          <CampoCol valor={Object.keys(config)[0] || ''} onChangeV={(v) => onChange({ [v]: Object.values(config)[0] || 'text' })} />
          <select className="px-2 py-1 text-sm border rounded" value={Object.values(config)[0] || 'text'} onChange={(e) => onChange({ [Object.keys(config)[0] || 'coluna']: e.target.value })}>
            <option value="text">Texto</option>
            <option value="integer">Inteiro</option>
            <option value="double">Decimal</option>
            <option value="date">Data</option>
            <option value="timestamp">Data e hora</option>
            <option value="boolean">Sim/Não</option>
          </select>
        </div>
      );
    case 'filter':
      return (
        <div className="flex gap-2 items-center flex-wrap">
          <CampoCol valor={config.column || ''} onChangeV={(v) => onChange({ ...config, column: v })} />
          <select className="px-2 py-1 text-sm border rounded" value={config.operator || '='} onChange={(e) => onChange({ ...config, operator: e.target.value })}>
            <option value="=">igual a</option>
            <option value="!=">diferente de</option>
            <option value=">">maior que</option>
            <option value="<">menor que</option>
            <option value=">=">maior ou igual</option>
            <option value="<=">menor ou igual</option>
            <option value="contains">contém texto</option>
            <option value="in">está em (lista)</option>
            <option value="not_in">não está em (lista)</option>
            <option value="is_null">é vazio</option>
            <option value="is_not_null">não é vazio</option>
          </select>
          {!['is_null', 'is_not_null'].includes(config.operator) && (
            <input type="text" placeholder={config.operator === 'in' || config.operator === 'not_in' ? 'a, b, c' : 'valor'}
              className="flex-1 px-2 py-1 text-sm border rounded" value={Array.isArray(config.value) ? config.value.join(', ') : (config.value ?? '')}
              onChange={(e) => {
                const v = e.target.value;
                if (config.operator === 'in' || config.operator === 'not_in') {
                  onChange({ ...config, value: colsLista(v) });
                } else if (['=', '!=', '>', '<', '>=', '<='].includes(config.operator)) {
                  const num = Number(v);
                  onChange({ ...config, value: v !== '' && !isNaN(num) ? num : v });
                } else {
                  onChange({ ...config, value: v });
                }
              }} />
          )}
        </div>
      );
    case 'deduplicate':
      return (
        <div className="flex gap-2 items-center flex-wrap">
          <span className="text-xs text-gray-500">Chaves:</span>
          <CampoCol valor={(config.keys || []).join(', ')} onChangeV={(v) => onChange({ ...config, keys: colsLista(v) })} placeholder="id (ou id, data)" />
          <select className="px-2 py-1 text-sm border rounded" value={config.keep || 'first'} onChange={(e) => onChange({ ...config, keep: e.target.value })}>
            <option value="first">manter primeira</option>
            <option value="last">manter última</option>
          </select>
        </div>
      );
    case 'fill_null':
      return (
        <div className="flex gap-2 items-center flex-wrap">
          <CampoCol valor={config.column || ''} onChangeV={(v) => onChange({ ...config, column: v })} />
          <span className="text-xs text-gray-500">preencher com</span>
          <input type="text" placeholder="valor" className="flex-1 px-2 py-1 text-sm border rounded" value={config.value ?? ''}
            onChange={(e) => { const v = e.target.value; const n = Number(v); onChange({ ...config, value: v !== '' && !isNaN(n) ? n : v }); }} />
          <select className="px-2 py-1 text-xs border rounded" value="" onChange={(e) => e.target.value && onChange({ ...config, strategy: e.target.value, value: undefined })}>
            <option value="">…ou estratégia</option>
            <option value="forward">usar valor anterior</option>
            <option value="backward">usar próximo valor</option>
          </select>
        </div>
      );
    case 'sort':
      return (
        <div className="flex gap-2 items-center">
          <CampoCol valor={config.column || ''} onChangeV={(v) => onChange({ ...config, column: v })} />
          <select className="px-2 py-1 text-sm border rounded" value={config.order || 'asc'} onChange={(e) => onChange({ ...config, order: e.target.value })}>
            <option value="asc">crescente</option>
            <option value="desc">decrescente</option>
          </select>
        </div>
      );
    case 'limit':
      return (
        <div className="flex gap-2 items-center">
          <span className="text-xs text-gray-500">Manter apenas</span>
          <input type="number" min={1} className="w-24 px-2 py-1 text-sm border rounded" value={config.rows || ''} onChange={(e) => onChange({ rows: parseInt(e.target.value) || undefined })} />
          <span className="text-xs text-gray-500">linhas</span>
        </div>
      );
    case 'add_column':
      return (
        <div className="space-y-1">
          <div className="flex gap-2 items-center">
            <input type="text" placeholder="nome da nova coluna" className="flex-1 px-2 py-1 text-sm border rounded" value={config.name || ''} onChange={(e) => onChange({ ...config, name: e.target.value })} />
            <span className="text-gray-400 text-sm">=</span>
            <input type="text" placeholder="expressão SQL (ex: quantidade * preco)" className="flex-1 px-2 py-1 text-sm border rounded font-mono" value={config.expression || ''} onChange={(e) => onChange({ ...config, expression: e.target.value })} />
          </div>
        </div>
      );
    case 'remove_columns':
      return (
        <CampoCol valor={(config.columns || []).join(', ')} onChangeV={(v) => onChange({ columns: colsLista(v) })} placeholder="col1, col2 (a remover)" />
      );
    case 'select_columns':
      return (
        <CampoCol valor={(config.columns || []).join(', ')} onChangeV={(v) => onChange({ columns: colsLista(v) })} placeholder="col1, col2 (a manter)" />
      );
    case 'uppercase':
    case 'lowercase':
    case 'trim':
      return (
        <CampoCol valor={(config.columns || []).join(', ')} onChangeV={(v) => onChange({ columns: colsLista(v) })}
          placeholder={`colunas (${type === 'uppercase' ? 'CAIXA ALTA' : type === 'lowercase' ? 'caixa baixa' : 'sem espaços'})`} />
      );
    case 'replace':
      return (
        <div className="flex gap-2 items-center flex-wrap">
          <CampoCol valor={config.column || ''} onChangeV={(v) => onChange({ ...config, column: v })} />
          <span className="text-xs text-gray-500">trocar</span>
          <input type="text" placeholder="texto antigo" className="flex-1 px-2 py-1 text-sm border rounded" value={config.find ?? ''} onChange={(e) => onChange({ ...config, find: e.target.value })} />
          <span className="text-xs text-gray-500">por</span>
          <input type="text" placeholder="novo texto" className="flex-1 px-2 py-1 text-sm border rounded" value={config.replace ?? ''} onChange={(e) => onChange({ ...config, replace: e.target.value })} />
        </div>
      );
    case 'split':
      return (
        <div className="flex gap-2 items-center flex-wrap">
          <CampoCol valor={config.column || ''} onChangeV={(v) => onChange({ ...config, column: v })} />
          <span className="text-xs text-gray-500">separado por</span>
          <input type="text" placeholder=" " className="w-16 px-2 py-1 text-sm border rounded text-center" value={config.delimiter || ' '} onChange={(e) => onChange({ ...config, delimiter: e.target.value })} />
          <span className="text-xs text-gray-500">em</span>
          <input type="text" placeholder="parte1, parte2" className="flex-1 px-2 py-1 text-sm border rounded" value={(config.into || []).join(', ')}
            onChange={(e) => onChange({ ...config, into: colsLista(e.target.value) })} />
        </div>
      );
    case 'merge':
      return (
        <div className="flex gap-2 items-center flex-wrap">
          <CampoCol valor={(config.columns || []).join(', ')} onChangeV={(v) => onChange({ ...config, columns: colsLista(v) })} placeholder="col1, col2 (a juntar)" />
          <span className="text-xs text-gray-500">em</span>
          <input type="text" placeholder="nova_coluna" className="flex-1 px-2 py-1 text-sm border rounded" value={config.into || ''} onChange={(e) => onChange({ ...config, into: e.target.value })} />
          <span className="text-xs text-gray-500">sep.</span>
          <input type="text" placeholder="-" className="w-14 px-2 py-1 text-sm border rounded text-center" value={config.separator ?? ' '} onChange={(e) => onChange({ ...config, separator: e.target.value })} />
        </div>
      );
    default:
      return <div className="text-sm text-gray-500">Configure este tipo pelo modo SQL ou via assistente.</div>;
  }
}
