import { useState } from 'react';
import { Settings, Database, Shield, Server, Save, X, Check } from 'lucide-react';
import toast from 'react-hot-toast';

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState('general');
  const [isSaving, setIsSaving] = useState(false);
  const [config, setConfig] = useState({
    apiPort: '8000',
    frontendPort: '5173',
    metadataPath: './data/metadata.db',
    warehousePath: './data/warehouse.duckdb',
    corsOrigins: 'http://localhost:5173,http://localhost:3000',
    secretKey: '',
    maxPreviewRows: '100',
    maxQueryRows: '1000',
    logRetention: '30',
    encryptPasswords: true,
    enableScheduler: false,
  });

  const handleSave = async () => {
    setIsSaving(true);
    // Simulação de salvamento
    setTimeout(() => {
      setIsSaving(false);
      toast.success('Configurações salvas com sucesso!');
    }, 1000);
  };

  const tabs = [
    { id: 'general', label: 'Geral', icon: Server },
    { id: 'database', label: 'Banco de Dados', icon: Database },
    { id: 'security', label: 'Segurança', icon: Shield },
  ];

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Configurações</h1>
          <p className="text-gray-600 mt-1">Configure o sistema Dataflow</p>
        </div>
        <button 
          onClick={handleSave}
          disabled={isSaving}
          className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-lg font-medium transition-colors"
        >
          {isSaving ? <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div> : <Save size={18} />}
          {isSaving ? 'Salvando...' : 'Salvar'}
        </button>
      </div>

      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-64 flex-shrink-0">
          <div className="bg-white rounded-lg shadow p-2">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors
                    ${activeTab === tab.id ? 'bg-primary-50 text-primary-700' : 'text-gray-600 hover:bg-gray-50'}
                  `}
                >
                  <Icon size={20} />
                  <span className="font-medium">{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 bg-white rounded-lg shadow p-6">
          {activeTab === 'general' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-gray-900">Configurações Gerais</h2>
              
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Porta da API</label>
                  <input 
                    type="number" 
                    value={config.apiPort}
                    onChange={(e) => setConfig({ ...config, apiPort: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Porta do Frontend</label>
                  <input 
                    type="number" 
                    value={config.frontendPort}
                    onChange={(e) => setConfig({ ...config, frontendPort: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Origens CORS (separadas por vírgula)</label>
                <input 
                  type="text" 
                  value={config.corsOrigins}
                  onChange={(e) => setConfig({ ...config, corsOrigins: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                />
                <p className="text-xs text-gray-500 mt-1">URLs permitidas para acessar a API</p>
              </div>

              <div className="grid grid-cols-3 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Máx. Preview (linhas)</label>
                  <input 
                    type="number" 
                    value={config.maxPreviewRows}
                    onChange={(e) => setConfig({ ...config, maxPreviewRows: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Máx. Query (linhas)</label>
                  <input 
                    type="number" 
                    value={config.maxQueryRows}
                    onChange={(e) => setConfig({ ...config, maxQueryRows: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Retenção de Logs (dias)</label>
                  <input 
                    type="number" 
                    value={config.logRetention}
                    onChange={(e) => setConfig({ ...config, logRetention: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              <div className="flex items-center gap-3">
                <input 
                  type="checkbox" 
                  id="scheduler"
                  checked={config.enableScheduler}
                  onChange={(e) => setConfig({ ...config, enableScheduler: e.target.checked })}
                  className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                />
                <label htmlFor="scheduler" className="text-sm font-medium text-gray-700">
                  Habilitar Agendamento de Tarefas
                </label>
              </div>
            </div>
          )}

          {activeTab === 'database' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-gray-900">Configurações do Banco de Dados</h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Caminho Metadata (SQLite)</label>
                  <input 
                    type="text" 
                    value={config.metadataPath}
                    onChange={(e) => setConfig({ ...config, metadataPath: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">Arquivo SQLite para armazenar configurações</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Caminho Warehouse (DuckDB)</label>
                  <input 
                    type="text" 
                    value={config.warehousePath}
                    onChange={(e) => setConfig({ ...config, warehousePath: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">Arquivo DuckDB para armazenar dados</p>
                </div>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p className="text-sm text-yellow-800">
                  <strong>Atenção:</strong> Alterar estes caminhos pode fazer com que dados existentes não sejam encontrados. 
                  Faça backup antes de alterar.
                </p>
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-gray-900">Configurações de Segurança</h2>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Chave Secreta</label>
                <input 
                  type="password" 
                  value={config.secretKey}
                  onChange={(e) => setConfig({ ...config, secretKey: e.target.value })}
                  placeholder="••••••••••••••••"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                />
                <p className="text-xs text-gray-500 mt-1">Usada para criptografar senhas de conexão</p>
              </div>

              <div className="flex items-center gap-3">
                <input 
                  type="checkbox" 
                  id="encrypt"
                  checked={config.encryptPasswords}
                  onChange={(e) => setConfig({ ...config, encryptPasswords: e.target.checked })}
                  className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                />
                <label htmlFor="encrypt" className="text-sm font-medium text-gray-700">
                  Criptografar senhas de conexão no banco
                </label>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm text-blue-800">
                  <strong>Dica:</strong> Mantenha a chave secreta em um local seguro. 
                  Se perdida, senhas criptografadas não poderão ser recuperadas.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
