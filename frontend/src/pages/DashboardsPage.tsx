import { useState } from 'react';
import { Plus, LayoutGrid, Trash2, X, Save } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { dashboardsApi } from '../api';
import { Dashboard } from '../types';
import { DashboardViewer } from '../components/dashboards/DashboardViewer';
import { DashboardEditor } from '../components/dashboards/DashboardEditor';
import { ComponenteDashboard, normalizarComponentes, paraLayoutSalvo } from '../components/dashboards/layoutUtils';
import toast from 'react-hot-toast';
import clsx from 'clsx';

const getStatusBadge = (status: string) => {
  const styles = {
    valid: 'bg-green-100 text-green-800',
    pending: 'bg-gray-100 text-gray-800',
  };
  return (
    <span className={clsx('px-2 py-1 rounded-full text-xs font-medium', styles[status as keyof typeof styles] || styles.pending)}>
      {status === 'valid' ? 'Válido' : 'Pendente'}
    </span>
  );
};

interface FormState {
  name: string;
  title: string;
  description: string;
  refresh_interval: number | undefined;
  componentes: ComponenteDashboard[];
}

const FORM_VAZIO: FormState = {
  name: '', title: '', description: '', refresh_interval: undefined, componentes: [],
};

export function DashboardsPage() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [viewModalOpen, setViewModalOpen] = useState(false);
  const [viewingDashboard, setViewingDashboard] = useState<Dashboard | null>(null);
  const [editingDashboard, setEditingDashboard] = useState<Dashboard | null>(null);
  const [form, setForm] = useState<FormState>(FORM_VAZIO);

  const { data: dashboards, isLoading } = useQuery('dashboards', dashboardsApi.list);

  const createMutation = useMutation(dashboardsApi.create, {
    onSuccess: () => { queryClient.invalidateQueries('dashboards'); fecharModal(); toast.success('Dashboard criado!'); },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro ao criar'); },
  });

  const updateMutation = useMutation(({ id, data }: { id: string; data: any }) => dashboardsApi.update(id, data), {
    onSuccess: () => { queryClient.invalidateQueries('dashboards'); fecharModal(); toast.success('Dashboard atualizado!'); },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro ao atualizar'); },
  });

  const deleteMutation = useMutation(dashboardsApi.delete, {
    onSuccess: () => { queryClient.invalidateQueries('dashboards'); toast.success('Removido!'); },
  });

  const fecharModal = () => {
    setIsModalOpen(false);
    setEditingDashboard(null);
    setForm(FORM_VAZIO);
  };

  const abrirNovo = () => {
    setEditingDashboard(null);
    setForm(FORM_VAZIO);
    setIsModalOpen(true);
  };

  const abrirEdicao = (dashboard: Dashboard) => {
    setEditingDashboard(dashboard);
    setForm({
      name: dashboard.name,
      title: dashboard.title,
      description: dashboard.description || '',
      refresh_interval: dashboard.refresh_interval,
      componentes: normalizarComponentes(dashboard.layout),
    });
    setIsModalOpen(true);
  };

  const salvar = (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      name: form.name,
      title: form.title,
      description: form.description,
      refresh_interval: form.refresh_interval,
      layout: paraLayoutSalvo(form.componentes),
    };
    if (editingDashboard) {
      updateMutation.mutate({ id: editingDashboard.id, data: payload });
    } else {
      createMutation.mutate(payload as any);
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboards</h1>
          <p className="text-gray-600 mt-1">Editor no-code: arraste, solte e redimensione os componentes</p>
        </div>
        <button onClick={abrirNovo} className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg font-medium transition-colors">
          <Plus size={20} /> Novo Dashboard
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : dashboards && dashboards.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {dashboards.map((dashboard) => {
            const nComponentes = (dashboard.layout || []).reduce(
              (n: number, item: any) => n + (Array.isArray(item?.components) ? item.components.length : 1), 0
            );
            return (
              <div key={dashboard.id} className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="font-semibold text-gray-900">{dashboard.title}</h3>
                    <p className="text-sm text-gray-600 mt-1">{dashboard.description}</p>
                    <div className="text-xs text-gray-400 mt-2">{nComponentes} componentes</div>
                  </div>
                  {getStatusBadge(dashboard.status)}
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    onClick={() => { setViewingDashboard(dashboard); setViewModalOpen(true); }}
                    className="flex items-center gap-1 px-3 py-1.5 text-primary-600 hover:bg-primary-50 rounded-lg text-sm font-medium"
                  >
                    Visualizar
                  </button>
                  <button
                    onClick={() => abrirEdicao(dashboard)}
                    className="text-gray-600 hover:bg-gray-100 p-1.5 rounded-lg"
                    title="Editar no editor visual"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path></svg>
                  </button>
                  <button
                    onClick={() => { if (confirm(`Remover o dashboard "${dashboard.title}"?`)) deleteMutation.mutate(dashboard.id); }}
                    className="text-red-600 hover:bg-red-50 p-1.5 rounded-lg"
                    title="Remover"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <LayoutGrid className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Nenhum dashboard criado</h3>
          <p className="text-gray-500 text-sm mb-4">Monte painéis arrastando e redimensionando componentes</p>
          <button onClick={abrirNovo} className="text-primary-600 hover:text-primary-700 font-medium">Criar primeiro dashboard</button>
        </div>
      )}

      {/* Editor no-code (tela cheia) */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-white flex flex-col">
          <div className="flex justify-between items-center p-4 border-b shadow-sm">
            <h2 className="text-xl font-bold text-gray-900">
              {editingDashboard ? `Editando: ${editingDashboard.title}` : 'Novo Dashboard'}
            </h2>
            <div className="flex items-center gap-2">
              <button type="button" onClick={fecharModal} className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium text-sm">
                Cancelar
              </button>
              <button
                type="button"
                onClick={salvar}
                disabled={createMutation.isLoading || updateMutation.isLoading}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white rounded-lg font-medium text-sm"
              >
                {(createMutation.isLoading || updateMutation.isLoading)
                  ? <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  : <Save size={16} />}
                {editingDashboard ? 'Salvar alterações' : 'Criar dashboard'}
              </button>
              <button onClick={fecharModal} className="ml-2 text-gray-400 hover:text-gray-600"><X size={22} /></button>
            </div>
          </div>

          <form onSubmit={salvar} className="flex flex-col flex-1 min-h-0">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 p-4 border-b bg-gray-50">
              <div>
                <label className="block text-[11px] font-medium text-gray-500 mb-1">Nome (ID) *</label>
                <input
                  type="text" value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 text-sm"
                  required pattern="[a-zA-Z0-9_]+" placeholder="meu_dashboard"
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-gray-500 mb-1">Título *</label>
                <input
                  type="text" value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 text-sm"
                  required placeholder="Meu Dashboard"
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-gray-500 mb-1">Descrição</label>
                <input
                  type="text" value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 text-sm"
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-gray-500 mb-1">Refresh automático (s)</label>
                <input
                  type="number" value={form.refresh_interval ?? ''}
                  onChange={(e) => setForm({ ...form, refresh_interval: e.target.value ? parseInt(e.target.value) : undefined })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 text-sm"
                  placeholder="Ex: 60" min={5}
                />
              </div>
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto p-4">
              <DashboardEditor
                value={paraLayoutSalvo(form.componentes)}
                onChange={(comps) => setForm((prev) => ({ ...prev, componentes: comps }))}
              />
            </div>
          </form>
        </div>
      )}

      {/* View Modal */}
      {viewModalOpen && viewingDashboard && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-7xl mx-4 max-h-[90vh] overflow-hidden">
            <div className="flex justify-between items-center p-6 border-b">
              <div>
                <h2 className="text-xl font-bold text-gray-900">{viewingDashboard.title}</h2>
                <p className="text-sm text-gray-600">{viewingDashboard.description}</p>
              </div>
              <button onClick={() => setViewModalOpen(false)} className="text-gray-400 hover:text-gray-600"><X size={24} /></button>
            </div>
            <div className="p-6 overflow-auto max-h-[70vh] bg-gray-50">
              <DashboardViewer dashboard={viewingDashboard} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
