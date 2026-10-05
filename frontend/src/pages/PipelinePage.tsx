import { useState } from 'react';
import { GitBranch, Play, RefreshCw, X, Terminal, Clock, CheckCircle, XCircle } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { executionApi } from '../api';
import toast from 'react-hot-toast';
import clsx from 'clsx';

const getStatusColor = (status: string) => {
  const colors = {
    valid: 'bg-green-500',
    invalid: 'bg-red-500',
    pending: 'bg-gray-400',
    running: 'bg-blue-500 animate-pulse',
    error: 'bg-red-500',
    success: 'bg-green-500',
  };
  return colors[status as keyof typeof colors] || 'bg-gray-400';
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'success': return <CheckCircle size={16} className="text-green-500" />;
    case 'error': return <XCircle size={16} className="text-red-500" />;
    case 'running': return <RefreshCw size={16} className="text-blue-500 animate-spin" />;
    default: return <Clock size={16} className="text-gray-400" />;
  }
};

const getTypeIcon = (type: string) => {
  const icons: Record<string, string> = {
    source: '🗄️',
    ingestion: '📥',
    staging: '🔧',
    dimension: '📦',
    fact: '📊',
  };
  return icons[type] || '📄';
};

export function PipelinePage() {
  const queryClient = useQueryClient();
  const [isRunning, setIsRunning] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  const [selectedExecution, setSelectedExecution] = useState<string | null>(null);

  const { data: dag, isLoading: dagLoading } = useQuery('dag', executionApi.getDag);
  const { data: logs, isLoading: logsLoading } = useQuery('executionLogs', () => executionApi.getLogs(50), {
    enabled: showLogs,
    refetchInterval: showLogs ? 3000 : false
  });
  const { data: executionDetail } = useQuery(
    ['executionDetail', selectedExecution],
    () => executionApi.getExecutionLogs(selectedExecution!),
    { enabled: !!selectedExecution }
  );

  const runPipelineMutation = useMutation(executionApi.runPipeline, {
    onMutate: () => { setIsRunning(true); },
    onSuccess: (data) => {
      toast.success(`Pipeline executado! ${data.results.filter(r => r.status === 'success').length} sucessos`);
      queryClient.invalidateQueries('dag');
      queryClient.invalidateQueries('executionLogs');
      setShowLogs(true);
      setSelectedExecution(data.execution_id);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erro ao executar pipeline');
    },
    onSettled: () => { setIsRunning(false); }
  });

  const handleRunAll = () => {
    if (confirm('Executar pipeline completo?')) {
      runPipelineMutation.mutate();
    }
  };

  // Agrupar logs por execução
  const groupedLogs = logs?.reduce((acc, log) => {
    if (!acc[log.execution_id]) {
      acc[log.execution_id] = [];
    }
    acc[log.execution_id].push(log);
    return acc;
  }, {} as Record<string, typeof logs>);

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pipeline</h1>
          <p className="text-gray-600 mt-1">Visualização e execução do pipeline de dados</p>
        </div>
        <div className="flex gap-3">
          <button 
            onClick={() => setShowLogs(!showLogs)}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors",
              showLogs ? "bg-gray-800 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            )}
          >
            <Terminal size={18} />
            {showLogs ? 'Ocultar Logs' : 'Ver Logs'}
          </button>
          <button 
            onClick={handleRunAll}
            disabled={isRunning}
            className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            {isRunning ? <RefreshCw size={18} className="animate-spin" /> : <Play size={18} />}
            {isRunning ? 'Executando...' : 'Executar Tudo'}
          </button>
        </div>
      </div>

      {/* DAG Visualization */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Fluxo do Pipeline (DAG)</h2>
        {dagLoading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : dag?.nodes && dag.nodes.length > 0 ? (
          <div className="flex flex-wrap gap-4 items-center">
            {dag.nodes.map((node: any, idx: number) => (
              <div key={node.id} className="flex items-center gap-2">
                <div 
                  className={clsx(
                    "px-4 py-3 rounded-lg border-2 flex items-center gap-2 cursor-pointer hover:shadow-md transition-shadow",
                    getStatusColor(node.status)
                  )}
                >
                  <span>{getTypeIcon(node.type)}</span>
                  <div>
                    <div className="font-medium text-white text-sm">{node.name}</div>
                    <div className="text-xs text-white/80 capitalize">{node.type}</div>
                  </div>
                </div>
                {idx < dag.nodes.length - 1 && (
                  <div className="text-gray-400">→</div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            Nenhum recurso configurado no pipeline
          </div>
        )}
        
        <div className="mt-6 pt-6 border-t">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Legenda</h3>
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-green-500"></div>
              <span>Válido</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-blue-500"></div>
              <span>Executando</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-gray-400"></div>
              <span>Pendente</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-red-500"></div>
              <span>Erro</span>
            </div>
          </div>
        </div>
      </div>

      {/* Execution Logs */}
      {showLogs && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Logs de Execução</h2>
            <button onClick={() => setShowLogs(false)} className="text-gray-400 hover:text-gray-600">
              <X size={20} />
            </button>
          </div>
          
          {logsLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : groupedLogs && Object.keys(groupedLogs).length > 0 ? (
            <div className="space-y-4">
              {Object.entries(groupedLogs).slice(0, 5).map(([execId, execLogs]: [string, any]) => {
                const firstLog = execLogs[0];
                const lastLog = execLogs[execLogs.length - 1];
                const hasError = execLogs.some((l: any) => l.status === 'error');
                const allSuccess = execLogs.every((l: any) => l.status === 'success');
                
                return (
                  <div 
                    key={execId} 
                    className={clsx(
                      "border rounded-lg p-4 cursor-pointer transition-colors",
                      selectedExecution === execId ? "border-primary-500 bg-primary-50" : "hover:bg-gray-50",
                      hasError ? "border-red-200" : allSuccess ? "border-green-200" : ""
                    )}
                    onClick={() => setSelectedExecution(selectedExecution === execId ? null : execId)}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-2">
                        {hasError ? <XCircle size={20} className="text-red-500" /> : allSuccess ? <CheckCircle size={20} className="text-green-500" /> : <Clock size={20} className="text-blue-500" />}
                        <span className="font-medium">Execução {execId.slice(0, 8)}</span>
                      </div>
                      <span className="text-sm text-gray-500">
                        {new Date(firstLog.created_at).toLocaleString('pt-BR')}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600">
                      {execLogs.length} recursos • {execLogs.filter((l: any) => l.status === 'success').length} sucessos
                      {hasError && ` • ${execLogs.filter((l: any) => l.status === 'error').length} erros`}
                    </div>
                    
                    {selectedExecution === execId && executionDetail && (
                      <div className="mt-4 bg-gray-900 rounded-lg p-4 font-mono text-sm text-green-400 overflow-auto max-h-64">
                        {executionDetail.map((log: any, idx: number) => (
                          <div key={idx} className="mb-1">
                            <span className="text-gray-500">[{new Date(log.started_at).toLocaleTimeString('pt-BR')}]</span>
                            {' '}
                            {getStatusIcon(log.status)}
                            {' '}
                            <span className="text-white">{log.resource_name}</span>
                            {' '}
                            <span className={log.status === 'success' ? 'text-green-400' : log.status === 'error' ? 'text-red-400' : 'text-blue-400'}>
                              {log.status === 'success' && log.rows_affected !== undefined && `(${log.rows_affected} linhas)`}
                              {log.status === 'error' && `- Erro: ${log.error_message}`}
                              {log.status === 'running' && '- Executando...'}
                            </span>
                            {log.duration_ms && <span className="text-gray-500 ml-2">({log.duration_ms}ms)</span>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              Nenhuma execução registrada
            </div>
          )}
        </div>
      )}
    </div>
  );
}
