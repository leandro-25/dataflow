import { useQuery } from 'react-query';
import { LayoutGrid, Database, ArrowRight, Table, Cylinder, BarChart2, TrendingUp, Clock } from 'lucide-react';
import { Link } from 'react-router-dom';
import { overviewApi } from '../api';
import clsx from 'clsx';

interface StatCard {
  label: string;
  value: number;
  valid?: number;
  invalid?: number;
  running?: number;
  error?: number;
  rows?: number;
  icon: any;
  color: string;
  bg: string;
}

interface OverviewData {
  sources: { total: number; valid: number; invalid: number };
  ingestions: { total: number; running: number; error: number; valid: number; total_rows_ingested: number };
  stagings: { total: number; running: number; error: number; valid: number };
  dimensions: { total: number; running: number; error: number; valid: number };
  facts: { total: number; running: number; error: number; valid: number };
  metrics: { total: number; valid: number };
  dashboards: { total: number };
  warehouse: { tables: number; total_rows: number; by_type: Record<string, number> };
  recent_executions: Array<{
    id: string;
    execution_id: string;
    resource_type: string;
    resource_name: string;
    status: string;
    started_at: string;
    duration_ms: number;
    rows_affected: number;
    error_message: string;
  }>;
}

export function HomePage() {
  const { data: overview, isLoading, refetch } = useQuery<OverviewData>('overview', overviewApi.get, {
    refetchInterval: 30000,
  });

  // Default values when loading
  const o = overview || {
    sources: { total: 0, valid: 0, invalid: 0 },
    ingestions: { total: 0, running: 0, error: 0, valid: 0, total_rows_ingested: 0 },
    stagings: { total: 0, running: 0, error: 0, valid: 0 },
    dimensions: { total: 0, running: 0, error: 0, valid: 0 },
    facts: { total: 0, running: 0, error: 0, valid: 0 },
    metrics: { total: 0, valid: 0 },
    dashboards: { total: 0 },
    warehouse: { tables: 0, total_rows: 0, by_type: {} },
    recent_executions: []
  };

  const quickLinks: { label: string; icon: any; path: string; color: string; count: number }[] = [
    { label: 'Fontes de Dados', icon: Database, path: '/sources', color: 'bg-blue-100 text-blue-600', count: o.sources.total },
    { label: 'Ingestões', icon: ArrowRight, path: '/ingestions', color: 'bg-green-100 text-green-600', count: o.ingestions.total },
    { label: 'Dashboards', icon: LayoutGrid, path: '/dashboards', color: 'bg-purple-100 text-purple-600', count: o.dashboards.total },
  ];

  const statsCards: StatCard[] = [
    { label: 'Fontes', value: o.sources.total, valid: o.sources.valid, invalid: o.sources.invalid, icon: Database, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Ingestões', value: o.ingestions.total, running: o.ingestions.running, error: o.ingestions.error, valid: o.ingestions.valid, icon: ArrowRight, color: 'text-green-600', bg: 'bg-green-50' },
    { label: 'Staging', value: o.stagings.total, running: o.stagings.running, error: o.stagings.error, valid: o.stagings.valid, icon: Table, color: 'text-yellow-600', bg: 'bg-yellow-50' },
    { label: 'Dimensões', value: o.dimensions.total, running: o.dimensions.running, error: o.dimensions.error, valid: o.dimensions.valid, icon: Cylinder, color: 'text-purple-600', bg: 'bg-purple-50' },
    { label: 'Fatos', value: o.facts.total, running: o.facts.running, error: o.facts.error, valid: o.facts.valid, icon: BarChart2, color: 'text-orange-600', bg: 'bg-orange-50' },
    { label: 'Métricas', value: o.metrics.total, valid: o.metrics.valid, icon: TrendingUp, color: 'text-pink-600', bg: 'bg-pink-50' },
    { label: 'Dashboards', value: o.dashboards.total, icon: LayoutGrid, color: 'text-indigo-600', bg: 'bg-indigo-50' },
    { label: 'Tabelas no Warehouse', value: o.warehouse.tables, rows: o.warehouse.total_rows, icon: Cylinder, color: 'text-gray-600', bg: 'bg-gray-50' },
  ];

  const getStatusColor = (status: string) => {
    const colors = {
      success: 'bg-green-100 text-green-800',
      error: 'bg-red-100 text-red-800',
      running: 'bg-blue-100 text-blue-800 animate-pulse',
      skipped: 'bg-gray-100 text-gray-800',
    };
    return colors[status as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  const getStatusLabel = (status: string) => {
    const labels = { success: 'Sucesso', error: 'Erro', running: 'Executando', skipped: 'Pulado' };
    return labels[status as keyof typeof labels] || status;
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Bem-vindo ao Dataflow</h1>
          <p className="text-gray-600 mt-1">
            Sistema de pipeline de dados local. Conecte fontes, transforme dados e crie dashboards.
          </p>
        </div>
        <button 
          onClick={() => refetch()} 
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium transition-colors disabled:opacity-50"
        >
          <Clock size={18} className={isLoading ? 'animate-spin' : ''} />
          Atualizar
        </button>
      </div>

      {/* Quick Access Links */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {quickLinks.map((link) => {
          const Icon = link.icon;
          return (
            <Link
              key={link.path}
              to={link.path}
              className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow border-l-4 border-primary-500"
            >
              <div className="flex items-center justify-between mb-4">
                <div className={`w-12 h-12 rounded-lg ${link.color} flex items-center justify-center`}>
                  <Icon size={24} />
                </div>
                <span className="text-2xl font-bold text-gray-900">{link.count}</span>
              </div>
              <h3 className="font-semibold text-gray-900">{link.label}</h3>
            </Link>
          );
        })}
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 mb-8">
        {statsCards.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="bg-white rounded-lg shadow p-5 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-2">
                <div className={`w-10 h-10 rounded-lg ${stat.bg} flex items-center justify-center`}>
                  <Icon size={20} className={stat.color} />
                </div>
                <span className="text-2xl font-bold text-gray-900">{stat.value}</span>
              </div>
              <p className="text-sm font-medium text-gray-700">{stat.label}</p>
              {stat.valid !== undefined && stat.invalid !== undefined && (
                <div className="flex gap-2 mt-2 text-xs">
                  {stat.valid > 0 && <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded">Válidos: {stat.valid}</span>}
                  {stat.invalid > 0 && <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded">Inválidos: {stat.invalid}</span>}
                  {stat.running !== undefined && stat.running > 0 && <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded animate-pulse">Executando: {stat.running}</span>}
                  {stat.error !== undefined && stat.error > 0 && <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded">Erros: {stat.error}</span>}
                </div>
              )}
              {stat.rows !== undefined && (
                <div className="mt-2 text-xs text-gray-500">
                  {stat.rows.toLocaleString()} linhas
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* System Flow */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <LayoutGrid size={20} className="text-primary-600" />
          Fluxo do Sistema
        </h2>
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <div className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg">
            <Database size={16} />
            <span>Fontes</span>
            <span className="text-xs text-gray-500">({o.sources.total})</span>
          </div>
          <ArrowRight size={16} className="text-gray-400" />
          <div className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg">
            <span className="text-gray-600">raw_*</span>
            <span>Ingestão</span>
            <span className="text-xs text-gray-500">({o.ingestions.total})</span>
          </div>
          <ArrowRight size={16} className="text-gray-400" />
          <div className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg">
            <span className="text-gray-600">stg_*</span>
            <span>Staging</span>
            <span className="text-xs text-gray-500">({o.stagings.total})</span>
          </div>
          <ArrowRight size={16} className="text-gray-400" />
          <div className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg">
            <span className="text-gray-600">dim_* / fato_*</span>
            <span>Modelagem</span>
            <span className="text-xs text-gray-500">({(o.dimensions.total || 0) + (o.facts.total || 0)})</span>
          </div>
          <ArrowRight size={16} className="text-gray-400" />
          <div className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg">
            <LayoutGrid size={16} />
            <span>Dashboards</span>
            <span className="text-xs text-gray-500">({o.dashboards.total})</span>
          </div>
        </div>
      </div>

      {/* Recent Executions */}
      {o.recent_executions && o.recent_executions.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Clock size={20} className="text-primary-600" />
              Execuções Recentes
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Recurso</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Início</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duração</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Linhas</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {o.recent_executions.slice(0, 10).map((exec) => (
                  <tr key={exec.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{exec.resource_name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-600 capitalize">{exec.resource_type}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={clsx('px-2 py-1 rounded-full text-xs font-medium', getStatusColor(exec.status))}>
                        {getStatusLabel(exec.status)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-600 text-sm">
                      {exec.started_at ? new Date(exec.started_at).toLocaleString('pt-BR') : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-600 text-sm">
                      {exec.duration_ms ? `${(exec.duration_ms / 1000).toFixed(1)}s` : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-600 text-sm">
                      {exec.rows_affected ? exec.rows_affected.toLocaleString() : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="p-4 border-t flex justify-end">
            <Link to="/pipeline" className="text-primary-600 hover:text-primary-700 font-medium text-sm">
              Ver todas as execuções →
            </Link>
          </div>
        </div>
      )}

      {/* Warehouse Summary */}
      {o.warehouse && o.warehouse.tables > 0 && (
        <div className="bg-white rounded-lg shadow mt-8">
          <div className="p-6 border-b">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Cylinder size={20} className="text-primary-600" />
              Warehouse (DuckDB)
            </h2>
          </div>
          <div className="p-6 grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-3xl font-bold text-gray-900">{o.warehouse.tables}</p>
              <p className="text-sm text-gray-600">Total de Tabelas</p>
            </div>
            <div className="bg-blue-50 rounded-lg p-4">
              <p className="text-3xl font-bold text-blue-700">{o.warehouse.by_type?.raw || 0}</p>
              <p className="text-sm text-gray-600">Raw (raw_*)</p>
            </div>
            <div className="bg-yellow-50 rounded-lg p-4">
              <p className="text-3xl font-bold text-yellow-700">{o.warehouse.by_type?.staging || 0}</p>
              <p className="text-sm text-gray-600">Staging (stg_*)</p>
            </div>
            <div className="bg-purple-50 rounded-lg p-4">
              <p className="text-3xl font-bold text-purple-700">{o.warehouse.by_type?.dimension || 0}</p>
              <p className="text-sm text-gray-600">Dimensões (dim_*)</p>
            </div>
            <div className="bg-orange-50 rounded-lg p-4">
              <p className="text-3xl font-bold text-orange-700">{o.warehouse.by_type?.fact || 0}</p>
              <p className="text-sm text-gray-600">Fatos (fato_*)</p>
            </div>
            {o.warehouse.total_rows > 0 && (
              <div className="md:col-span-5 bg-green-50 rounded-lg p-4">
                <p className="text-sm text-gray-600">Total de linhas no warehouse:</p>
                <p className="text-2xl font-bold text-green-700">{o.warehouse.total_rows.toLocaleString()}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}