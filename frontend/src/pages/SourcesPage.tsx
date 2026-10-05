import { useEffect, useState } from 'react';
import {
  Plus, Database, FileSpreadsheet, FileText, FileCode, FileJson, Table,
  Pencil, Trash2, Check, X, TestTube, FileBox, FolderOpen, Copy,
  ChevronLeft, ChevronRight, Sparkles, Wand2, ShieldCheck, AlertTriangle
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { sourcesApi, ingestionsApi, filesystemApi } from '../api';
import { Source } from '../types';
import toast from 'react-hot-toast';
import clsx from 'clsx';
import { FileBrowserModal } from '../components/FileBrowserModal';

const sourceTypes = [
  { value: 'csv', label: 'CSV', icon: FileText, color: 'text-green-600', categoria: 'arquivo', desc: 'Texto separado por vírgula ou outro delimitador' },
  { value: 'excel', label: 'Excel', icon: FileSpreadsheet, color: 'text-green-700', categoria: 'arquivo', desc: 'Planilhas .xlsx / .xls' },
  { value: 'json', label: 'JSON', icon: FileJson, color: 'text-yellow-600', categoria: 'arquivo', desc: 'Listas ou objetos estruturados' },
  { value: 'xml', label: 'XML', icon: FileCode, color: 'text-orange-500', categoria: 'arquivo', desc: 'Dados em tags hierárquicas' },
  { value: 'parquet', label: 'Parquet', icon: FileBox, color: 'text-blue-500', categoria: 'arquivo', desc: 'Colunar otimizado para analytics' },
  { value: 'avro', label: 'Avro', icon: FileBox, color: 'text-purple-500', categoria: 'arquivo', desc: 'Formato binário com schema embutido' },
  { value: 'orc', label: 'ORC', icon: FileBox, color: 'text-indigo-500', categoria: 'arquivo', desc: 'Colunar usado no ecossistema Hadoop' },
  { value: 'sql_file', label: 'Arquivo SQL', icon: FileCode, color: 'text-gray-600', categoria: 'arquivo', desc: 'Resultado de uma query SELECT salva em arquivo .sql' },
  { value: 'postgres', label: 'PostgreSQL', icon: Database, color: 'text-blue-600', categoria: 'banco', desc: 'Banco relacional PostgreSQL' },
  { value: 'mysql', label: 'MySQL', icon: Database, color: 'text-orange-600', categoria: 'banco', desc: 'Banco relacional MySQL/MariaDB' },
  { value: 'google_sheets', label: 'Google Sheets', icon: Table, color: 'text-green-500', categoria: 'servico', desc: 'Planilha online do Google' },
  { value: 'delta_lake', label: 'Delta Lake', icon: Database, color: 'text-cyan-600', categoria: 'servico', desc: 'Tabelas Delta locais ou na nuvem (S3/Azure/GCS)' },
];

const CATEGORIAS = [
  { id: 'arquivo', titulo: 'Arquivos' },
  { id: 'banco', titulo: 'Bancos de dados' },
  { id: 'servico', titulo: 'Serviços e nuvem' },
];

const EXEMPLO_ARQUIVOS: Record<string, string> = {
  csv: 'vendas.csv',
  excel: 'produtos.xlsx',
  json: 'clientes.json',
  xml: 'clientes.xml',
  parquet: 'vendas.parquet',
  avro: 'vendas.avro',
  orc: 'vendas.orc',
};

const MASCARA = '__MASKED__';

interface FormConfig {
  name: string;
  type: string;
  host?: string;
  port?: string;
  database?: string;
  user?: string;
  password?: string;
  file_path?: string;
  delimiter?: string;
  encoding?: string;
  has_header?: boolean;
  sheet_name?: string;
  json_path?: string;
  root_element?: string;
  row_element?: string;
  columns?: string;
  target_type?: string;
  target_host?: string;
  target_port?: string;
  target_database?: string;
  target_username?: string;
  target_password?: string;
  table_path?: string;
  version?: string;
  aws_access_key_id?: string;
  aws_secret_access_key?: string;
  aws_region?: string;
  spreadsheet_id?: string;
  credentials?: string;
}

const FORM_INICIAL: FormConfig = {
  name: '', type: '', host: 'localhost', port: '5432', database: '', user: '', password: '',
  file_path: '', delimiter: ',', encoding: 'utf-8', has_header: true, sheet_name: '',
  json_path: '', root_element: '', row_element: '', columns: '',
  target_type: 'duckdb', target_host: '', target_port: '', target_database: '',
  target_username: '', target_password: '',
  table_path: '', version: '', aws_access_key_id: '', aws_secret_access_key: '', aws_region: '',
  spreadsheet_id: '', credentials: '',
};

const getStatusBadge = (status: string) => {
  const styles = { valid: 'bg-green-100 text-green-800', invalid: 'bg-red-100 text-red-800', pending: 'bg-gray-100 text-gray-800' };
  const labels = { valid: 'Válido', invalid: 'Inválido', pending: 'Pendente' };
  return (
    <span className={clsx('px-2 py-1 rounded-full text-xs font-medium', styles[status as keyof typeof styles] || styles.pending)}>
      {labels[status as keyof typeof labels] || status}
    </span>
  );
};

export function SourcesPage() {
  const queryClient = useQueryClient();
  const [modo, setModo] = useState<'guiado' | 'avancado'>('guiado');
  const [etapa, setEtapa] = useState(1);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isTestModalOpen, setIsTestModalOpen] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; tables?: string[] } | null>(null);
  const [testingSource, setTestingSource] = useState<string | null>(null);
  const [editingSource, setEditingSource] = useState<Source | null>(null);
  const [browser, setBrowser] = useState<BrowserState | null>(null);
  const [validando, setValidando] = useState(false);
  const [validacaoLocal, setValidacaoLocal] = useState<{ success: boolean; message: string; tables?: string[] } | null>(null);
  const [detectando, setDetectando] = useState(false);
  const [exemploBase, setExemploBase] = useState<string | null>(null);

  const [formData, setFormData] = useState<FormConfig>({ ...FORM_INICIAL, type: '' });

  const { data: sources, isLoading } = useQuery('sources', sourcesApi.list);
  const { data: todasIngestoes } = useQuery('ingestions-light', () => ingestionsApi.list());

  useEffect(() => {
    if (exemploBase || !isModalOpen) return;
    filesystemApi.list().then((d) => {
      const atalho = d.shortcuts?.find((s) => s.name === 'Dados de Exemplo');
      if (atalho) setExemploBase(atalho.path);
    }).catch(() => { });
  }, [isModalOpen, exemploBase]);

  const createMutation = useMutation(sourcesApi.create, {
    onSuccess: (data) => {
      queryClient.invalidateQueries('sources');
      setIsModalOpen(false);
      resetForm();
      toast.success('Fonte criada com sucesso!');
      testMutation.mutate(data.id);
    },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro ao criar fonte'); },
  });

  const updateMutation = useMutation(
    ({ id, data }: { id: string; data: any }) => sourcesApi.update(id, data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('sources');
        setIsModalOpen(false);
        setEditingSource(null);
        resetForm();
        toast.success('Fonte atualizada com sucesso!');
      },
      onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro ao atualizar fonte'); },
    }
  );

  const deleteMutation = useMutation(sourcesApi.delete, {
    onSuccess: () => { queryClient.invalidateQueries(['sources']); toast.success('Fonte removida!'); },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro ao remover fonte'); },
  });

  const testMutation = useMutation((id: string) => sourcesApi.testConnection(id), {
    onSuccess: (data) => { setTestResult(data); setTestingSource(null); setIsTestModalOpen(true); },
    onError: (error: any) => {
      setTestResult({ success: false, message: error.response?.data?.detail || 'Erro no teste' });
      setTestingSource(null); setIsTestModalOpen(true);
    },
  });

  const resetForm = () => {
    setFormData({ ...FORM_INICIAL, type: '' });
    setEditingSource(null);
    setEtapa(1);
    setValidacaoLocal(null);
  };

  const getConfigFromForm = () => {
    const { type } = formData;
    if (type === 'postgres' || type === 'mysql') {
      return {
        host: formData.host, port: parseInt(formData.port || (type === 'postgres' ? '5432' : '3306')),
        database: formData.database, user: formData.user, password: formData.password,
      };
    }
    if (type === 'csv') return { file_path: formData.file_path, delimiter: formData.delimiter, encoding: formData.encoding, has_header: formData.has_header };
    if (type === 'excel') return { file_path: formData.file_path, sheet_name: formData.sheet_name || undefined };
    if (type === 'json') return { file_path: formData.file_path, json_path: formData.json_path || undefined };
    if (type === 'xml') return { file_path: formData.file_path, root_element: formData.root_element || undefined, row_element: formData.row_element || undefined };
    if (type === 'parquet' || type === 'orc') return { file_path: formData.file_path, columns: formData.columns || undefined };
    if (type === 'avro') return { file_path: formData.file_path };
    if (type === 'sql_file') return {
      file_path: formData.file_path, target_type: formData.target_type || 'duckdb',
      target_host: formData.target_host, target_port: formData.target_port,
      target_database: formData.target_database, target_username: formData.target_username,
      target_password: formData.target_password,
    };
    if (type === 'delta_lake') return {
      table_path: formData.table_path, version: formData.version || undefined,
      aws_access_key_id: formData.aws_access_key_id, aws_secret_access_key: formData.aws_secret_access_key,
      aws_region: formData.aws_region,
    };
    if (type === 'google_sheets') return {
      spreadsheet_id: formData.spreadsheet_id, sheet_name: formData.sheet_name || 'Sheet1',
      credentials: formData.credentials && formData.credentials !== MASCARA ? JSON.parse(formData.credentials) : undefined,
    };
    return {};
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const config = getConfigFromForm();
    if (!formData.type) { toast.error('Escolha o tipo da fonte'); return; }
    if (editingSource) {
      updateMutation.mutate({ id: editingSource.id, data: { name: formData.name, type: formData.type, config } });
    } else {
      createMutation.mutate({ name: formData.name, type: formData.type, config });
    }
  };

  const validarAgora = async () => {
    if (!formData.type) { toast.error('Escolha o tipo da fonte primeiro'); return; }
    setValidando(true);
    setValidacaoLocal(null);
    try {
      const res = await sourcesApi.validate({ type: formData.type, config: getConfigFromForm() });
      setValidacaoLocal(res);
    } catch (err: any) {
      setValidacaoLocal({ success: false, message: err.response?.data?.detail || 'Erro na validação' });
    } finally {
      setValidando(false);
    }
  };

  const sugerirNomeDeArquivo = (caminho: string) => {
    if (!caminho || editingSource) return;
    const nome = caminho.split(/[\\/]/).pop() || '';
    const base = nome.replace(/\.[^.]+$/, '').replace(/[^a-zA-Z0-9_]/g, '_').toLowerCase();
    if (base && /^[a-z_]/.test(base)) setFormData((p) => ({ ...p, name: p.name ? p.name : base }));
  };

  const usarExemplo = () => {
    const arquivo = EXEMPLO_ARQUIVOS[formData.type];
    if (!arquivo || !exemploBase) { toast.error('Exemplos disponíveis apenas para tipos de arquivo'); return; }
    const caminho = `${exemploBase}${exemploBase.endsWith('\\') ? '' : '\\'}${arquivo}`;
    setFormData((p) => ({ ...p, file_path: caminho }));
    sugerirNomeDeArquivo(caminho);
    detectar(caminho);
  };

  const detectar = async (caminhoOverride?: string) => {
    const caminho = caminhoOverride ?? formData.file_path;
    if (!caminho) { toast.error('Informe o caminho do arquivo primeiro'); return; }
    setDetectando(true);
    try {
      if (formData.type === 'csv') {
        const d = await ingestionsApi.detectFileFormat(caminho);
        setFormData((p) => ({ ...p, delimiter: d.delimiter, encoding: d.encoding, has_header: d.has_header }));
        toast.success(`Detectado: delimitador "${d.delimiter}", encoding ${d.encoding}`);
      } else if (formData.type === 'xml') {
        const d = await ingestionsApi.analyzeXmlStructure(caminho);
        const sugestao = d.potential_row_elements?.[0]?.tag;
        if (sugestao) { setFormData((p) => ({ ...p, row_element: sugestao })); toast.success(`Elemento de linha sugerido: "${sugestao}" (${d.unique_tags} tags únicas)`); }
        else toast.error('Nenhum elemento de linha repetido encontrado');
      } else if (formData.type === 'json') {
        const d = await ingestionsApi.analyzeJsonStructure(caminho);
        const sugestao = d.suggested_data_paths?.[0]?.path;
        if (sugestao) { setFormData((p) => ({ ...p, json_path: sugestao })); toast.success(`Caminho de dados sugerido: "${sugestao}"`); }
        else toast.success(`JSON simples: ${d.array_length ?? '-'} registros no nível raiz`);
      } else {
        toast.error('Detecção automática disponível para CSV, XML e JSON');
      }
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Não foi possível analisar o arquivo');
    } finally {
      setDetectando(false);
    }
  };

  const duplicar = (source: Source) => {
    const novoNome = `${source.name}_copia`.slice(0, 100).replace(/[^a-zA-Z0-9_]/g, '_');
    setEditingSource(null);
    setModo('avancado');
    setEtapa(2);
    handleLoadForm(source, novoNome);
    setIsModalOpen(true);
    toast.success('Configuração copiada — ajuste o nome e salve');
  };

  const handleLoadForm = (source: Source, nomeOverride?: string) => {
    const cfg = source.config || {};
    setFormData({
      name: nomeOverride ?? source.name,
      type: source.type,
      host: cfg.host || 'localhost',
      port: String(cfg.port || (source.type === 'postgres' ? '5432' : '3306')),
      database: cfg.database || '',
      user: cfg.user || '',
      password: cfg.password ? MASCARA : '',
      file_path: cfg.file_path || '',
      delimiter: cfg.delimiter || ',',
      encoding: cfg.encoding || 'utf-8',
      has_header: cfg.has_header !== false,
      sheet_name: cfg.sheet_name || '',
      json_path: cfg.json_path || '',
      root_element: cfg.root_element || '',
      row_element: cfg.row_element || '',
      columns: cfg.columns || '',
      target_type: cfg.target_type || 'duckdb',
      target_host: cfg.target_host || '',
      target_port: String(cfg.target_port || ''),
      target_database: cfg.target_database || '',
      target_username: cfg.target_username || '',
      target_password: cfg.target_password ? MASCARA : '',
      table_path: cfg.table_path || '',
      version: String(cfg.version || ''),
      aws_access_key_id: cfg.aws_access_key_id || '',
      aws_secret_access_key: cfg.aws_secret_access_key ? MASCARA : '',
      aws_region: cfg.aws_region || '',
      spreadsheet_id: cfg.spreadsheet_id || '',
      credentials: cfg.credentials ? MASCARA : '',
    });
  };

  const handleEdit = (source: Source) => {
    setEditingSource(source);
    setEtapa(2);
    handleLoadForm(source);
    setIsModalOpen(true);
  };

  const handleDelete = (source: Source) => {
    const dependentes = (todasIngestoes || []).filter((i) => i.source_id === source.id).length;
    let msg = `Tem certeza que deseja remover a fonte "${source.name}"?`;
    if (dependentes > 0) msg = `⚠️ ${dependentes} ingestão(ões) usam esta fonte e serão órfãs!\n\n` + msg;
    if (confirm(msg)) deleteMutation.mutate(source.id);
  };

  const abrirNovo = () => { resetForm(); setModo('guiado'); setIsModalOpen(true); };
  const abrirNovoAvancado = () => { resetForm(); setModo('avancado'); setEtapa(2); setIsModalOpen(true); };

  const handleDeleteLegacy = (id: string) => {
    const src = (sources || []).find((s) => s.id === id);
    if (src) handleDelete(src);
  };

  const isDatabase = ['postgres', 'mysql'].includes(formData.type);
  const isFile = ['csv', 'excel', 'json', 'xml', 'parquet', 'avro', 'orc'].includes(formData.type);
  const podeAvancar = etapa === 1 ? !!formData.type : true;

  /* ---------- renderizadores de campos (compartilhados entre modos) ---------- */

  const botaoProcurar = (field: 'file_path' | 'table_path', accept?: string[], directory?: boolean) => (
    <button
      type="button"
      onClick={() => setBrowser({ field, accept, directory })}
      className="flex items-center justify-center px-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors shrink-0"
      title="Procurar no computador"
    >
      <FolderOpen size={18} className="text-gray-600" />
    </button>
  );

  const campoCaminho = (label: string, placeholder: string, accept: string[]) => (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label} *</label>
      <div className="flex gap-2">
        <input
          type="text" value={formData.file_path}
          onChange={(e) => setFormData({ ...formData, file_path: e.target.value })}
          onBlur={(e) => sugerirNomeDeArquivo(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          placeholder={placeholder} required
        />
        {botaoProcurar('file_path', accept)}
      </div>
    </div>
  );

  const botoesFerramentas = () =>
    (isFile || formData.type === 'sql_file') && (
      <div className="flex flex-wrap gap-2">
        {EXEMPLO_ARQUIVOS[formData.type] && exemploBase && (
          <button type="button" onClick={usarExemplo}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 rounded-lg">
            <Wand2 size={13} /> Usar dado de exemplo ({EXEMPLO_ARQUIVOS[formData.type]})
          </button>
        )}
        {(formData.type === 'csv' || formData.type === 'xml' || formData.type === 'json') && (
          <button type="button" disabled={detectando} onClick={() => detectar()}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100 rounded-lg disabled:opacity-50">
            <Sparkles size={13} /> {detectando ? 'Analisando...' : '✨ Detectar automaticamente'}
          </button>
        )}
      </div>
    );

  const camposTipo = () => (
    <>
      {(isFile || formData.type === 'sql_file') && (
        <div className="space-y-4">
          {campoCaminho(
            formData.type === 'sql_file' ? 'Caminho do Arquivo SQL' : 'Caminho do Arquivo',
            `/caminho/para/arquivo${formData.type === 'csv' ? '.csv' : formData.type === 'json' ? '.json' : formData.type === 'xml' ? '.xml' : formData.type === 'sql_file' ? '.sql' : ''}`,
            [`.${formData.type === 'excel' ? 'xlsx' : formData.type}`]
          )}
          {botoesFerramentas()}

          {formData.type === 'csv' && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Delimitador</label>
                <select value={formData.delimiter} onChange={(e) => setFormData({ ...formData, delimiter: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500">
                  <option value=",">Vírgula (,)</option>
                  <option value=";">Ponto e vírgula (;)</option>
                  <option value="\t">Tab</option>
                  <option value="|">Pipe (|)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Encoding</label>
                <select value={formData.encoding} onChange={(e) => setFormData({ ...formData, encoding: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500">
                  <option value="utf-8">UTF-8</option>
                  <option value="latin1">Latin-1</option>
                  <option value="iso-8859-1">ISO-8859-1</option>
                </select>
              </div>
              <label className="flex items-center gap-2 col-span-2 text-sm text-gray-700">
                <input type="checkbox" checked={formData.has_header} onChange={(e) => setFormData({ ...formData, has_header: e.target.checked })} className="rounded" />
                A primeira linha contém os nomes das colunas
              </label>
            </div>
          )}

          {formData.type === 'excel' && (
            <Campo label="Nome da Aba (opcional)" valor={formData.sheet_name} onChange={(v) => setFormData({ ...formData, sheet_name: v })} placeholder="Vazio = primeira aba" />
          )}

          {formData.type === 'json' && (
            <Campo label="Caminho dentro do JSON (opcional)" valor={formData.json_path} onChange={(v) => setFormData({ ...formData, json_path: v })} placeholder="ex: data.items — vazio = raiz" dica="Use quando a lista de registros estiver aninhada dentro do objeto." />
          )}

          {formData.type === 'xml' && (
            <>
              <Campo label="Elemento Raiz (opcional)" valor={formData.root_element} onChange={(v) => setFormData({ ...formData, root_element: v })} placeholder="ex: clientes" />
              <Campo label="Elemento de Linha" valor={formData.row_element} onChange={(v) => setFormData({ ...formData, row_element: v })} placeholder="ex: cliente" dica="Nome da tag que representa cada registro." />
            </>
          )}

          {(formData.type === 'parquet' || formData.type === 'orc') && (
            <Campo label="Colunas (opcional)" valor={formData.columns} onChange={(v) => setFormData({ ...formData, columns: v })} placeholder="col1, col2 — vazio = todas" />
          )}

          {formData.type === 'sql_file' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Onde executar a query</label>
                <select value={formData.target_type} onChange={(e) => setFormData({ ...formData, target_type: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500">
                  <option value="duckdb">DuckDB (local)</option>
                  <option value="postgres">PostgreSQL</option>
                  <option value="mysql">MySQL</option>
                </select>
              </div>
              {formData.target_type !== 'duckdb' && (
                <div className="grid grid-cols-2 gap-4">
                  <Campo label="Host" valor={formData.target_host} onChange={(v) => setFormData({ ...formData, target_host: v })} placeholder="localhost" />
                  <Campo label="Porta" valor={formData.target_port} onChange={(v) => setFormData({ ...formData, target_port: v })} placeholder={formData.target_type === 'postgres' ? '5432' : '3306'} tipo="number" />
                  <Campo label="Banco" valor={formData.target_database} onChange={(v) => setFormData({ ...formData, target_database: v })} />
                  <Campo label="Usuário" valor={formData.target_username} onChange={(v) => setFormData({ ...formData, target_username: v })} />
                  <Senha label="Senha" valor={formData.target_password} onChange={(v) => setFormData({ ...formData, target_password: v })} />
                </div>
              )}
            </>
          )}
        </div>
      )}

      {isDatabase && (
        <div className="grid grid-cols-2 gap-4">
          <Campo label="Host" valor={formData.host} onChange={(v) => setFormData({ ...formData, host: v })} placeholder="localhost" />
          <Campo label="Porta" valor={formData.port} onChange={(v) => setFormData({ ...formData, port: v })} placeholder={formData.type === 'postgres' ? '5432' : '3306'} tipo="number" />
          <Campo label="Banco *" valor={formData.database} onChange={(v) => setFormData({ ...formData, database: v })} required />
          <Campo label="Usuário *" valor={formData.user} onChange={(v) => setFormData({ ...formData, user: v })} required />
          <Senha label="Senha *" valor={formData.password} onChange={(v) => setFormData({ ...formData, password: v })} required={!editingSource} />
        </div>
      )}

      {formData.type === 'google_sheets' && (
        <>
          <Campo label="ID da Planilha *" valor={formData.spreadsheet_id} onChange={(v) => setFormData({ ...formData, spreadsheet_id: v })} placeholder="cole o ID da URL da planilha" required />
          <Campo label="Nome da Aba" valor={formData.sheet_name} onChange={(v) => setFormData({ ...formData, sheet_name: v })} placeholder="Sheet1" />
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Credenciais JSON * {editingSource && formData.credentials === MASCARA && <span className="text-xs text-gray-400">(salvas — deixe como está para manter)</span>}</label>
            <textarea rows={5} value={formData.credentials} onChange={(e) => setFormData({ ...formData, credentials: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg font-mono text-xs" placeholder='{"type": "service_account", ...}' required={formData.credentials !== MASCARA} />
          </div>
        </>
      )}

      {formData.type === 'delta_lake' && (
        <>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Caminho da Tabela *</label>
            <div className="flex gap-2">
              <input type="text" value={formData.table_path} onChange={(e) => setFormData({ ...formData, table_path: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg" placeholder="local ou s3://bucket/caminho" required />
              {botaoProcurar('table_path', undefined, true)}
            </div>
          </div>
          <Campo label="Versão (opcional — time travel)" valor={formData.version} onChange={(v) => setFormData({ ...formData, version: v })} placeholder="0, 1, 2..." />
          <details className="border rounded-lg p-3">
            <summary className="cursor-pointer text-sm font-medium text-gray-600">Credenciais de nuvem (opcional)</summary>
            <div className="grid grid-cols-2 gap-4 mt-3">
              <Campo label="AWS Access Key" valor={formData.aws_access_key_id} onChange={(v) => setFormData({ ...formData, aws_access_key_id: v })} />
              <Senha label="AWS Secret Key" valor={formData.aws_secret_access_key} onChange={(v) => setFormData({ ...formData, aws_secret_access_key: v })} />
              <Campo label="Região AWS" valor={formData.aws_region} onChange={(v) => setFormData({ ...formData, aws_region: v })} placeholder="us-east-1" />
            </div>
          </details>
        </>
      )}
    </>
  );

  return (
    <div>
      {/* Cabeçalho */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Fontes de Dados</h1>
          <p className="text-gray-600 mt-1">Configure conexões com arquivos, bancos e serviços</p>
        </div>
        <div className="flex gap-2">
          <button onClick={abrirNovo} className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg font-medium transition-colors">
            <Plus size={20} /> Nova Fonte
          </button>
        </div>
      </div>

      {/* Lista */}
      {isLoading ? (
        <div className="flex justify-center items-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div></div>
      ) : sources && sources.length > 0 ? (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {['Nome', 'Tipo', 'Status'].map((h) => (
                  <th key={h} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{h}</th>
                ))}
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {sources.map((source) => {
                const info = sourceTypes.find((t) => t.value === source.type);
                const Icon = info?.icon || Database;
                const deps = (todasIngestoes || []).filter((i) => i.source_id === source.id).length;
                return (
                  <tr key={source.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <Icon className={clsx('w-5 h-5 mr-3', info?.color || 'text-gray-400')} />
                        <span className="font-medium text-gray-900">{source.name}</span>
                        {deps > 0 && <span className="ml-2 text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{deps} ing.</span>}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-600">{info?.label || source.type}</td>
                    <td className="px-6 py-4 whitespace-nowrap">{getStatusBadge(source.status)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <button onClick={() => { setTestingSource(source.id); testMutation.mutate(source.id); }} disabled={testingSource === source.id}
                        className="text-green-600 hover:text-green-800 mr-3 disabled:opacity-50" title="Testar Conexão">
                        {testingSource === source.id ? <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-green-600"></div> : <TestTube size={18} />}
                      </button>
                      <button onClick={() => handleEdit(source)} className="text-primary-600 hover:text-primary-800 mr-3" title="Editar"><Pencil size={18} /></button>
                      <button onClick={() => duplicar(source)} className="text-gray-500 hover:text-gray-800 mr-3" title="Duplicar"><Copy size={18} /></button>
                      <button onClick={() => handleDelete(source)} className="text-red-600 hover:text-red-800" title="Remover"><Trash2 size={18} /></button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <Database className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Nenhuma fonte configurada</h3>
          <div className="flex justify-center gap-3 mt-4">
            <button onClick={abrirNovo} className="text-primary-600 hover:text-primary-700 font-medium">🧭 Assistente guiado</button>
            <span className="text-gray-300">|</span>
            <button onClick={abrirNovoAvancado} className="text-gray-600 hover:text-gray-800 font-medium">⚡ Modo avançado</button>
          </div>
        </div>
      )}

      {/* Modal criar/editar */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl mx-4 max-h-[92vh] overflow-y-auto">
            <form onSubmit={handleSubmit}>
              <div className="flex justify-between items-center p-6 border-b sticky top-0 bg-white z-10">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">{editingSource ? 'Editar Fonte' : modo === 'guiado' ? 'Nova Fonte — Assistente' : 'Nova Fonte — Avançado'}</h2>
                  {modo === 'guiado' && !editingSource && (
                    <div className="flex items-center gap-2 mt-2">
                      {[1, 2, 3].map((n) => (
                        <div key={n} className={clsx('w-8 h-1.5 rounded-full', n <= etapa ? 'bg-primary-600' : 'bg-gray-200')} />
                      ))}
                      <span className="text-xs text-gray-500 ml-1">
                        {etapa === 1 ? '1. Tipo' : etapa === 2 ? '2. Configuração' : '3. Revisão'}
                      </span>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button type="button"
                    onClick={() => { setModo(modo === 'guiado' ? 'avancado' : 'guiado'); if (modo === 'guiado') setEtapa(2); }}
                    className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
                    title="Alternar entre assistente e formulário completo">
                    {modo === 'guiado' ? '⚡ Modo avançado' : '🧭 Modo guiado'}
                  </button>
                  <button type="button" onClick={() => { setIsModalOpen(false); resetForm(); }} className="text-gray-400 hover:text-gray-600"><X size={24} /></button>
                </div>
              </div>

              <div className="p-6 space-y-4">
                {(modo === 'guiado' && etapa === 1 && !editingSource) && (
                  <>
                    {CATEGORIAS.map((cat) => (
                      <div key={cat.id}>
                        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">{cat.titulo}</h3>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                          {sourceTypes.filter((t) => t.categoria === cat.id).map((t) => {
                            const Icon = t.icon;
                            const ativo = formData.type === t.value;
                            return (
                              <button key={t.value} type="button"
                                onClick={() => { setFormData({ ...FORM_INICIAL, type: t.value }); setValidacaoLocal(null); }}
                                className={clsx('text-left p-3 rounded-xl border-2 transition-all', ativo ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-primary-300')}>
                                <Icon className={clsx('w-5 h-5 mb-1', t.color)} />
                                <div className="font-semibold text-sm text-gray-900">{t.label}</div>
                                <div className="text-[11px] text-gray-500 leading-snug">{t.desc}</div>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </>
                )}

                {(modo === 'avancado' || etapa >= 2 || editingSource) && (
                  <>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
                        <input type="text" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                          className="w-full px-3 py-2 border rounded-lg" required pattern="[a-zA-Z0-9_]+" title="Apenas letras, números e underscore" placeholder="ex: vendas_csv" />
                        <p className="text-xs text-gray-400 mt-1">Letras, números e _ (usado nas tabelas)</p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Tipo *</label>
                        <select value={formData.type} onChange={(e) => { setFormData({ ...FORM_INICIAL, name: formData.name, type: e.target.value }); setValidacaoLocal(null); }} className="w-full px-3 py-2 border rounded-lg" required>
                          <option value="" disabled>Selecione...</option>
                          {sourceTypes.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                        </select>
                      </div>
                    </div>

                    {formData.type && (
                      <div className="border-t pt-4 space-y-4">
                        <h3 className="font-medium text-gray-900">
                          Configuração — {sourceTypes.find((t) => t.value === formData.type)?.label}
                        </h3>
                        {camposTipo()}
                      </div>
                    )}
                  </>
                )}

                {(modo === 'guiado' && etapa === 3) && (
                  <div className="border rounded-lg p-4 bg-gray-50 space-y-2 text-sm">
                    <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2"><ShieldCheck size={16} className="text-green-600" /> Revisão antes de salvar</h3>
                    <LinhaResumo rotulo="Nome" valor={formData.name} />
                    <LinhaResumo rotulo="Tipo" valor={sourceTypes.find((t) => t.value === formData.type)?.label || ''} />
                    {formData.file_path && <LinhaResumo rotulo="Arquivo" valor={formData.file_path} />}
                    {formData.host && <LinhaResumo rotulo="Servidor" valor={`${formData.host}:${formData.port}/${formData.database}`} />}
                    {formData.spreadsheet_id && <LinhaResumo rotulo="Planilha" valor={formData.spreadsheet_id} />}
                    {formData.table_path && <LinhaResumo rotulo="Tabela Delta" valor={formData.table_path} />}
                    {validacaoLocal && (
                      <div className={clsx('mt-3 p-3 rounded-lg text-sm', validacaoLocal.success ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800')}>
                        <strong>{validacaoLocal.success ? '✅ Conexão validada!' : '❌ Falhou:'}</strong> {validacaoLocal.message}
                      </div>
                    )}
                  </div>
                )}

                {validacaoLocal && modo === 'avancado' && (
                  <div className={clsx('p-3 rounded-lg text-sm', validacaoLocal.success ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800')}>
                    <strong>{validacaoLocal.success ? '✅ Conexão validada!' : '❌ Falhou:'}</strong> {validacaoLocal.message}
                  </div>
                )}

                {!editingSource && (
                  <div className="flex items-start gap-2 text-xs text-gray-400 pt-1">
                    <ShieldCheck size={14} className="mt-0.5 shrink-0" />
                    Senhas e credenciais são armazenadas com segurança e nunca retornam abertas pela API.
                    Ao editar uma fonte, deixe o campo em branco para manter o segredo atual.
                  </div>
                )}
              </div>

              <div className={clsx('px-6 py-4 border-t flex justify-between gap-3 sticky bottom-0 bg-white')}>
                <div className="flex gap-2">
                  {modo === 'guiado' && etapa > 1 && (
                    <button type="button" onClick={() => setEtapa(etapa - 1)}
                      className="flex items-center gap-1 px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium text-sm">
                      <ChevronLeft size={16} /> Voltar
                    </button>
                  )}
                  {validacaoLocal?.success && etapa === 2 && modo === 'guiado' && (
                    <button type="button" onClick={() => setEtapa(3)}
                      className="flex items-center gap-1 px-4 py-2 text-green-700 bg-green-50 border border-green-200 rounded-lg font-medium text-sm">
                      Ir para revisão <ChevronRight size={16} />
                    </button>
                  )}
                </div>
                <div className="flex gap-2">
                  <button type="button" onClick={() => { setIsModalOpen(false); resetForm(); }}
                    className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium text-sm">
                    Cancelar
                  </button>
                  {(!editingSource && modo === 'guiado' && etapa < 2) ? (
                    <button type="button" disabled={!podeAvancar} onClick={() => setEtapa(2)}
                      className="flex items-center gap-1 px-4 py-2 bg-primary-600 text-white rounded-lg font-medium text-sm disabled:opacity-40">
                      Continuar <ChevronRight size={16} />
                    </button>
                  ) : (
                    <div className="flex gap-2">
                      <button type="button" disabled={validando || !formData.type} onClick={validarAgora}
                        className="flex items-center gap-1 px-3 py-2 border border-green-300 text-green-700 hover:bg-green-50 rounded-lg font-medium text-sm disabled:opacity-40"
                        title="Testa a conexão sem salvar nada">
                        <Sparkles size={15} /> {validando ? 'Testando...' : 'Testar antes de salvar'}
                      </button>
                      <button type="submit" disabled={createMutation.isLoading || updateMutation.isLoading}
                        className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium text-sm disabled:opacity-50">
                        <Check size={16} />
                        {editingSource ? 'Salvar' : 'Criar e testar'}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Browser de arquivos */}
      <FileBrowserModal
        open={!!browser}
        title={browser?.directory ? 'Selecione a pasta da tabela Delta' : 'Selecione um arquivo'}
        acceptExtensions={browser?.accept}
        selectDirectory={browser?.directory}
        onClose={() => setBrowser(null)}
        onSelect={(path) => {
          if (browser) {
            setFormData((prev) => {
              const novo = { ...prev, [browser.field]: path } as FormConfig;
              return novo;
            });
            if (browser.field === 'file_path') sugerirNomeDeArquivo(path);
          }
          setBrowser(null);
        }}
      />

      {/* Test modal */}
      {isTestModalOpen && testResult && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-900">Teste de Conexão</h2>
              <button onClick={() => setIsTestModalOpen(false)} className="text-gray-400 hover:text-gray-600"><X size={24} /></button>
            </div>
            <div className="p-6">
              <div className={clsx('flex items-center gap-3 p-4 rounded-lg', testResult.success ? 'bg-green-50' : 'bg-red-50')}>
                {testResult.success ? <Check size={24} className="text-green-600" /> : <AlertTriangle size={24} className="text-red-600" />}
                <div>
                  <h3 className={clsx('font-medium', testResult.success ? 'text-green-800' : 'text-red-800')}>
                    {testResult.success ? 'Conexão bem-sucedida!' : 'Falha na conexão'}
                  </h3>
                  <p className={clsx('text-sm mt-1', testResult.success ? 'text-green-600' : 'text-red-600')}>{testResult.message}</p>
                </div>
              </div>
              {testResult.tables && testResult.tables.length > 0 && (
                <div className="mt-4">
                  <h4 className="font-medium text-gray-700 mb-2">Tabelas/Recursos encontrados:</h4>
                  <div className="max-h-48 overflow-y-auto bg-gray-50 rounded-lg p-3">
                    <ul className="space-y-1">
                      {testResult.tables.map((t, idx) => <li key={idx} className="text-sm text-gray-600 font-mono">{t}</li>)}
                    </ul>
                  </div>
                </div>
              )}
            </div>
            <div className="p-6 border-t">
              <button onClick={() => setIsTestModalOpen(false)} className="w-full px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium">Fechar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Campo({ label, valor, onChange, placeholder, dica, tipo = 'text', required }: {
  label: string; valor?: string; onChange: (v: string) => void; placeholder?: string; dica?: string; tipo?: string; required?: boolean;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && '*'}
      </label>
      <input
        type={tipo} value={valor ?? ''} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} required={required}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
      />
      {dica && <p className="text-xs text-gray-400 mt-1">{dica}</p>}
    </div>
  );
}

function Senha({ label, valor, onChange, required }: { label: string; valor?: string; onChange: (v: string) => void; required?: boolean }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && '*'}
        {valor === MASCARA && <span className="ml-2 text-[11px] text-gray-400 normal-case">(protegida — deixe como está)</span>}
      </label>
      <input
        type="password" value={valor ?? ''} onChange={(e) => onChange(e.target.value)} required={required && valor !== MASCARA}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
        placeholder={valor === MASCARA ? '••••••••' : ''}
      />
    </div>
  );
}

function LinhaResumo({ rotulo, valor }: { rotulo: string; valor?: string }) {
  if (!valor) return null;
  return (
    <div className="flex gap-2">
      <span className="text-gray-500 w-28 shrink-0">{rotulo}:</span>
      <span className="font-mono text-gray-800 break-all">{valor}</span>
    </div>
  );
}

interface BrowserState {
  field: 'file_path' | 'table_path';
  accept?: string[];
  directory?: boolean;
}
