import { useState, useEffect, Fragment } from 'react';
import { 
  Plus, Download, Play, Eye, Trash2, Check, X, Database, Search, Star, Clock, Settings, 
  AlertTriangle, CheckCircle2, FileText, FileSpreadsheet, Table, FileCode, FileJson, 
  FileBox, ChevronDown, ChevronUp, History, TrendingUp, BarChart3, Edit3, Zap, Layers, 
  Wand2, Loader2, Info, XCircle, Database as DatabaseIcon, ArrowUpDown, Columns, Filter as FilterIcon
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { ingestionsApi, sourcesApi } from '../api';
import { Ingestion } from '../types';
import toast from 'react-hot-toast';
import clsx from 'clsx';
import { format, formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { IngestionWizard } from '../components/ingestions/IngestionWizard';

// ============ TYPES ============

interface ValidationResult {
  valid: boolean;
  status: string;
  message: string;
  warnings: string[];
  errors: string[];
}

interface MetadataInfo {
  source_type: string;
  source_name: string;
  schema: Array<{ name: string; type: string; nullable: boolean }>;
  tables?: string[];
  estimated_rows?: string;
  file_info?: {
    path: string;
    size_bytes: number;
    size_mb: number;
    modified: string;
  };
}

interface PreviewData {
  columns: string[];
  data: any[];
  total_rows: number;
  dtypes?: Record<string, string>;
  null_counts?: Record<string, number>;
}

interface FilterConfig {
  column: string;
  operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'contains';
  value: any;
}

interface ColumnMapping {
  target_name: string;
  target_type?: string;
  nullable?: boolean;
  default_value?: any;
}

interface AdvancedOptions {
  batch_size?: number;
  encoding?: string;
  delimiter?: string;
  skip_lines?: number;
  sheet_name?: string;
  json_path?: string;
}

interface IncrementalConfig {
  enabled: boolean;
  control_column?: string;
  last_value?: string;
}

// ============ CONSTANTS ============

const sourceTypeIcons: Record<string, any> = {
  postgres: Database,
  mysql: Database,
  csv: FileText,
  excel: FileSpreadsheet,
  json: FileJson,
  xml: FileCode,
  parquet: FileBox,
  avro: FileBox,
  orc: FileBox,
  sql_file: FileCode,
  delta_lake: Database,
  google_sheets: Table,
};

const sourceTypeColors: Record<string, string> = {
  postgres: 'text-blue-600 bg-blue-50',
  mysql: 'text-orange-600 bg-orange-50',
  csv: 'text-green-600 bg-green-50',
  excel: 'text-green-700 bg-green-50',
  json: 'text-yellow-600 bg-yellow-50',
  xml: 'text-orange-500 bg-orange-50',
  parquet: 'text-blue-500 bg-blue-50',
  avro: 'text-purple-500 bg-purple-50',
  orc: 'text-indigo-500 bg-indigo-50',
  sql_file: 'text-gray-600 bg-gray-50',
  delta_lake: 'text-cyan-600 bg-cyan-50',
  google_sheets: 'text-green-500 bg-green-50',
};

const operatorLabels: Record<string, string> = {
  eq: '=',
  ne: '≠',
  gt: '>',
  gte: '≥',
  lt: '<',
  lte: '≤',
  contains: 'contém',
};

// ============ COMPONENTS ============

const StatusBadge = ({ status, validationStatus }: { status: string; validationStatus?: string }) => {
  const styles = {
    valid: 'bg-green-100 text-green-800 border-green-200',
    invalid: 'bg-red-100 text-red-800 border-red-200',
    pending: 'bg-gray-100 text-gray-800 border-gray-200',
    running: 'bg-blue-100 text-blue-800 border-blue-200 animate-pulse',
    error: 'bg-red-100 text-red-800 border-red-200',
  };
  
  const labels = {
    valid: 'Válido',
    invalid: 'Inválido',
    pending: 'Pendente',
    running: 'Executando',
    error: 'Erro',
  };

  // Add validation indicator
  const validationIcon = validationStatus === 'error' ? <XCircle size={12} className="ml-1" /> :
                         validationStatus === 'warning' ? <AlertTriangle size={12} className="ml-1" /> :
                         validationStatus === 'success' ? <CheckCircle2 size={12} className="ml-1" /> : null;

  return (
    <span className={clsx('px-2 py-1 rounded-full text-xs font-medium border flex items-center gap-1', styles[status as keyof typeof styles] || styles.pending)}>
      {labels[status as keyof typeof labels] || status}
      {validationIcon}
    </span>
  );
};

const SourceTypeBadge = ({ type }: { type: string }) => {
  const Icon = sourceTypeIcons[type] || Database;
  const colorClass = sourceTypeColors[type] || 'text-gray-600 bg-gray-50';
  
  return (
    <span className={clsx('px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1', colorClass)}>
      <Icon size={12} />
      {type.replace('_', ' ').toUpperCase()}
    </span>
  );
};

const ValidationPanel = ({ validation }: { validation: ValidationResult | null }) => {
  if (!validation) return null;

  return (
    <div className={clsx(
      'p-4 rounded-lg border',
      validation.status === 'success' ? 'bg-green-50 border-green-200' :
      validation.status === 'warning' ? 'bg-yellow-50 border-yellow-200' :
      'bg-red-50 border-red-200'
    )}>
      <div className="flex items-center gap-2 mb-2">
        {validation.status === 'success' ? <CheckCircle2 className="text-green-600" size={20} /> :
         validation.status === 'warning' ? <AlertTriangle className="text-yellow-600" size={20} /> :
         <XCircle className="text-red-600" size={20} />}
        <span className={clsx('font-medium',
          validation.status === 'success' ? 'text-green-800' :
          validation.status === 'warning' ? 'text-yellow-800' :
          'text-red-800'
        )}>
          {validation.valid ? 'Validação concluída' : 'Problemas encontrados'}
        </span>
      </div>
      
      <p className={clsx('text-sm mb-3',
        validation.status === 'success' ? 'text-green-700' :
        validation.status === 'warning' ? 'text-yellow-700' :
        'text-red-700'
      )}>
        {validation.message}
      </p>

      {validation.warnings.length > 0 && (
        <div className="mb-2">
          <p className="text-xs font-medium text-yellow-800 mb-1">Avisos:</p>
          <ul className="text-xs text-yellow-700 space-y-1">
            {validation.warnings.map((w, i) => (
              <li key={i} className="flex items-start gap-1">
                <AlertTriangle size={12} className="mt-0.5 flex-shrink-0" />
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {validation.errors.length > 0 && (
        <div>
          <p className="text-xs font-medium text-red-800 mb-1">Erros:</p>
          <ul className="text-xs text-red-700 space-y-1">
            {validation.errors.map((e, i) => (
              <li key={i} className="flex items-start gap-1">
                <XCircle size={12} className="mt-0.5 flex-shrink-0" />
                {e}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

const MetadataPanel = ({ metadata }: { metadata: MetadataInfo | null }) => {
  if (!metadata) return null;

  return (
    <div className="bg-gray-50 rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-gray-900">Metadados da Fonte</h4>
        <SourceTypeBadge type={metadata.source_type} />
      </div>

      {metadata.file_info && (
        <div className="text-sm space-y-1">
          <p className="text-gray-600"><span className="font-medium">Arquivo:</span> {metadata.file_info.path}</p>
          <p className="text-gray-600"><span className="font-medium">Tamanho:</span> {metadata.file_info.size_mb.toFixed(2)} MB</p>
          <p className="text-gray-600"><span className="font-medium">Modificado:</span> {format(new Date(metadata.file_info.modified), 'dd/MM/yyyy HH:mm')}</p>
        </div>
      )}

      {metadata.estimated_rows && (
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <BarChart3 size={16} />
          <span><span className="font-medium">Linhas estimadas:</span> {metadata.estimated_rows}</span>
        </div>
      )}

      {metadata.schema && metadata.schema.length > 0 && (
        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">Schema ({metadata.schema.length} colunas):</p>
          <div className="max-h-48 overflow-y-auto bg-white rounded border border-gray-200">
            <table className="min-w-full text-xs">
              <thead className="bg-gray-100 sticky top-0">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Coluna</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Tipo</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Nullable</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {metadata.schema.map((col, i) => (
                  <tr key={i}>
                    <td className="px-3 py-2 font-mono text-gray-900">{col.name}</td>
                    <td className="px-3 py-2 text-gray-600">{col.type}</td>
                    <td className="px-3 py-2">
                      {col.nullable ? 
                        <span className="text-yellow-600">Sim</span> : 
                        <span className="text-green-600">Não</span>
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

// ============ MAIN PAGE ============

export function IngestionsPage() {
  const queryClient = useQueryClient();
  
  // Filters and search state
  const [searchQuery, setSearchQuery] = useState('');
  const [filterSource, setFilterSource] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  
  // Modal states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [isBulkModalOpen, setIsBulkModalOpen] = useState(false);
  const [isPreviewModalOpen, setIsPreviewModalOpen] = useState(false);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [isMetadataModalOpen, setIsMetadataModalOpen] = useState(false);
  
  // Selection states
  const [selectedIngestions, setSelectedIngestions] = useState<Set<string>>(new Set());
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  
  // Form states
  const [editingIngestion, setEditingIngestion] = useState<Ingestion | null>(null);
  const [activeTab, setActiveTab] = useState<'basic' | 'columns' | 'filters' | 'advanced'>('basic');
  
  // Data states
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [metadata, setMetadata] = useState<MetadataInfo | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  
  // Form data with all new fields
  const [formData, setFormData] = useState({
    // Basic
    name: '',
    source_id: '',
    mode: 'table' as 'table' | 'query',
    table: '',
    query: '',
    target_table: '',
    description: '',
    tags: [] as string[],
    
    // Scheduling
    schedule_enabled: false,
    schedule: '',
    schedule_timezone: 'America/Sao_Paulo',
    
    // Column mapping
    column_mapping: {} as Record<string, ColumnMapping>,
    selected_columns: [] as string[],
    
    // Filters
    filters: [] as FilterConfig[],
    
    // Incremental
    incremental_config: { enabled: false } as IncrementalConfig,
    
    // Advanced
    advanced_options: {} as AdvancedOptions,
  });
  
  // Temp states for forms
  const [newTag, setNewTag] = useState('');
  const [newFilter, setNewFilter] = useState<FilterConfig>({ column: '', operator: 'eq', value: '' });
  const [availableTables, setAvailableTables] = useState<string[]>([]);
  const [availableColumns, setAvailableColumns] = useState<string[]>([]);
  
  // Bulk creation state
  const [bulkSourceId, setBulkSourceId] = useState('');
  const [bulkTables, setBulkTables] = useState<string[]>([]);
  const [bulkNamingPattern, setBulkNamingPattern] = useState('raw_{name}');

  // Queries
  const { data: sources } = useQuery('sources', sourcesApi.list);
  const { data: stats } = useQuery('ingestion-stats', ingestionsApi.getStats);
  const { data: ingestions, isLoading } = useQuery(
    ['ingestions', searchQuery, filterSource, filterStatus, showFavoritesOnly, sortBy, sortOrder],
    () => ingestionsApi.list({
      search: searchQuery || undefined,
      source_id: filterSource || undefined,
      status: filterStatus || undefined,
      favorite_only: showFavoritesOnly || undefined,
      sort_by: sortBy,
      sort_order: sortOrder,
    })
  );

  // Mutations
  const createMutation = useMutation(ingestionsApi.create, {
    onSuccess: () => {
      queryClient.invalidateQueries('ingestions');
      setIsModalOpen(false);
      resetForm();
      toast.success('Ingestão criada com sucesso!');
    },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro ao criar ingestão'); },
  });

  const updateMutation = useMutation(({ id, data }: { id: string; data: any }) => ingestionsApi.update(id, data), {
    onSuccess: () => {
      queryClient.invalidateQueries('ingestions');
      setIsModalOpen(false);
      resetForm();
      toast.success('Ingestão atualizada com sucesso!');
    },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro ao atualizar ingestão'); },
  });

  const deleteMutation = useMutation(ingestionsApi.delete, {
    onSuccess: () => {
      queryClient.invalidateQueries('ingestions');
      toast.success('Ingestão removida com sucesso!');
    },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro ao remover'); },
  });

  const bulkDeleteMutation = useMutation(ingestionsApi.bulkDelete, {
    onSuccess: (result: any) => {
      queryClient.invalidateQueries('ingestions');
      setSelectedIngestions(new Set());
      toast.success(`${result.deleted} ingestões removidas!`);
    },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro ao remover'); },
  });

  const runMutation = useMutation(ingestionsApi.run, {
    onSuccess: (data: any) => {
      queryClient.invalidateQueries('ingestions');
      queryClient.invalidateQueries('ingestion-stats');
      toast.success(`Ingestão executada! ${data.rows_affected} linhas importadas`);
    },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro ao executar ingestão'); },
  });

  const validateMutation = useMutation(ingestionsApi.validate, {
    onSuccess: (data: any) => {
      setValidation(data);
      if (data.valid && data.warnings.length === 0) {
        toast.success('Validação concluída! Tudo certo.');
      } else if (data.valid) {
        toast.success(`Validação concluída com ${data.warnings.length} avisos`);
      } else {
        toast.error(`Validação falhou com ${data.errors.length} erros`);
      }
    },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro na validação'); },
  });

  const favoriteMutation = useMutation(ingestionsApi.toggleFavorite, {
    onSuccess: () => queryClient.invalidateQueries('ingestions'),
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro'); },
  });

  const bulkCreateMutation = useMutation(ingestionsApi.bulkCreate, {
    onSuccess: (result: any) => {
      queryClient.invalidateQueries('ingestions');
      setIsBulkModalOpen(false);
      toast.success(`${result.success} ingestões criadas!`);
      if (result.errors.length > 0) {
        result.errors.forEach((e: string) => toast.error(e));
      }
    },
    onError: (error: any) => { toast.error(error.response?.data?.detail || 'Erro ao criar em massa'); },
  });

  // Load templates on mount
  useEffect(() => {
    ingestionsApi.getTemplates().then(setTemplates);
  }, []);

  // Load available tables when source changes
  useEffect(() => {
    if (formData.source_id && formData.mode === 'table') {
      const source = sources?.find(s => s.id === formData.source_id);
      if (source && ['postgres', 'mysql'].includes(source.type)) {
        sourcesApi.listTables(formData.source_id)
          .then(data => setAvailableTables(data.tables))
          .catch(() => setAvailableTables([]));
      } else if (source) {
        // For file sources, show the file name as the "table"
        const fileName = source.config.file_path?.split(/[\\/]/).pop() || source.name;
        setAvailableTables([fileName]);
      }
    }
  }, [formData.source_id, formData.mode, sources]);

  // Auto-set table for file sources
  useEffect(() => {
    if (formData.source_id && formData.mode === 'table' && availableTables.length > 0) {
      const source = sources?.find(s => s.id === formData.source_id);
      if (source && ['csv', 'excel', 'json', 'xml', 'parquet', 'avro', 'orc', 'sql_file'].includes(source.type)) {
        // For file sources, automatically set the table to the filename
        if (!formData.table || formData.table !== availableTables[0]) {
          setFormData(prev => ({ ...prev, table: availableTables[0] }));
        }
      }
    }
  }, [formData.source_id, formData.mode, availableTables, sources, formData.table]);

  // Load bulk tables when bulk source changes
  useEffect(() => {
    if (bulkSourceId) {
      const source = sources?.find(s => s.id === bulkSourceId);
      if (source && ['postgres', 'mysql'].includes(source.type)) {
        sourcesApi.listTables(bulkSourceId)
          .then(data => setBulkTables(data.tables))
          .catch(() => setBulkTables([]));
      }
    }
  }, [bulkSourceId, sources]);

  const resetForm = () => {
    setFormData({
      name: '',
      source_id: '',
      mode: 'table',
      table: '',
      query: '',
      target_table: '',
      description: '',
      tags: [],
      schedule_enabled: false,
      schedule: '',
      schedule_timezone: 'America/Sao_Paulo',
      column_mapping: {},
      selected_columns: [],
      filters: [],
      incremental_config: { enabled: false },
      advanced_options: {},
    });
    setEditingIngestion(null);
    setActiveTab('basic');
    setValidation(null);
    setMetadata(null);
    setAvailableTables([]);
    setAvailableColumns([]);
  };

  const handleEdit = (ingestion: Ingestion) => {
    setEditingIngestion(ingestion);
    setFormData({
      name: ingestion.name,
      source_id: ingestion.source_id,
      mode: ingestion.config?.mode || 'table',
      table: ingestion.config?.table || '',
      query: ingestion.config?.query || '',
      target_table: ingestion.config?.target_table || '',
      description: ingestion.description || '',
      tags: ingestion.tags || [],
      schedule_enabled: ingestion.schedule_enabled || false,
      schedule: ingestion.schedule || '',
      schedule_timezone: ingestion.schedule_timezone || 'America/Sao_Paulo',
      column_mapping: ingestion.column_mapping || {},
      selected_columns: ingestion.selected_columns || [],
      filters: ingestion.filters || [],
      incremental_config: ingestion.incremental_config || { enabled: false },
      advanced_options: ingestion.advanced_options || {},
    });
    setIsModalOpen(true);
    setActiveTab('basic');
  };

  const handleSubmit = () => {
    const data = {
      name: formData.name,
      source_id: formData.source_id,
      config: {
        mode: formData.mode,
        target_table: formData.target_table || `raw_${formData.name}`,
        ...(formData.mode === 'table' ? { table: formData.table } : { query: formData.query }),
      },
      description: formData.description,
      tags: formData.tags,
      schedule: formData.schedule,
      schedule_enabled: formData.schedule_enabled,
      schedule_timezone: formData.schedule_timezone,
      column_mapping: formData.column_mapping,
      selected_columns: formData.selected_columns,
      filters: formData.filters,
      incremental_config: formData.incremental_config,
      advanced_options: formData.advanced_options,
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if (editingIngestion) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      updateMutation.mutate({ id: editingIngestion.id, data });
    } else {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      createMutation.mutate(data);
    }
  };

  const handleValidate = async (ingestionId?: string) => {
    const id = ingestionId || editingIngestion?.id;
    if (!id) return;
    
    toast.loading('Validando...', { id: 'validate' });
    try {
      await validateMutation.mutateAsync(id);
    } finally {
      toast.dismiss('validate');
    }
  };

  const handlePreview = async (ingestion: Ingestion, options?: { limit?: number }) => {
    setPreviewData(null);
    setIsPreviewModalOpen(true);
    try {
      const data = await ingestionsApi.preview(ingestion.id, options);
      setPreviewData(data);
      setAvailableColumns(data.columns);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao carregar preview');
      setIsPreviewModalOpen(false);
    }
  };

  // Robust function to load columns from any source type
  const loadColumnsFromSource = async () => {
    if (!currentSource || !formData.source_id) {
      toast.error('Selecione uma fonte de dados primeiro');
      return;
    }
    
    console.log('Loading columns for source:', currentSource.type, currentSource.name);
    console.log('Source config:', currentSource.config);
    
    try {
      toast.loading('Carregando colunas...', { id: 'load-columns' });
      
      let columns: string[] = [];
      let tableName = formData.table || '';
      
      // For file sources (CSV, Excel, etc.), the "table" is the filename
      if (isFileSource && !tableName && currentSource.config.file_path) {
        // Extract filename from path
        const pathParts = currentSource.config.file_path.split(/[\\/]/);
        tableName = pathParts[pathParts.length - 1];
        console.log('Using filename as table:', tableName);
      }
      
      // For file sources, also try to get columns from the file directly
      if (isFileSource) {
        try {
          console.log('Trying to get schema for file source...');
          const sourceData = await sourcesApi.getSchema(formData.source_id, tableName || 'default');
          console.log('Schema response:', sourceData);
          
          if (sourceData.schema && sourceData.schema.length > 0) {
            columns = sourceData.schema.map((col: any) => col.name || col);
            console.log('Columns from schema:', columns);
          }
        } catch (schemaError) {
          console.log('Schema endpoint failed, trying alternative...', schemaError);
        }
      }
      
      // If no columns yet, try the tables endpoint and get schema from first table
      if (columns.length === 0 && isDatabaseSource) {
        try {
          console.log('Trying to list tables...');
          const tablesData = await sourcesApi.listTables(formData.source_id);
          console.log('Tables:', tablesData);
          
          if (tablesData.tables && tablesData.tables.length > 0) {
            const firstTable = formData.table || tablesData.tables[0];
            console.log('Getting schema for table:', firstTable);
            
            const sourceData = await sourcesApi.getSchema(formData.source_id, firstTable);
            if (sourceData.schema && sourceData.schema.length > 0) {
              columns = sourceData.schema.map((col: any) => col.name || col);
            }
          }
        } catch (e) {
          console.log('Tables/schema failed:', e);
        }
      }
      
      // Last resort: if editing, try to use preview
      if (columns.length === 0 && editingIngestion) {
        try {
          console.log('Trying preview for existing ingestion...');
          const data = await ingestionsApi.preview(editingIngestion.id, { limit: 1 });
          columns = data.columns || [];
          console.log('Columns from preview:', columns);
        } catch (e) {
          console.log('Preview failed:', e);
        }
      }
      
      console.log('Final columns:', columns);
      setAvailableColumns(columns);
      
      if (columns.length > 0) {
        toast.success(`${columns.length} colunas carregadas!`, { id: 'load-columns' });
      } else {
        toast.error('Não foi possível detectar colunas automaticamente. Verifique se a fonte está configurada corretamente ou tente fazer um preview primeiro.', { id: 'load-columns' });
      }
    } catch (error: any) {
      console.error('Error loading columns:', error);
      toast.error(error.response?.data?.detail || error.message || 'Erro ao carregar colunas. Tente fazer um preview primeiro.', { id: 'load-columns' });
    }
  };

  const handleMetadata = async (ingestion: Ingestion) => {
    setMetadata(null);
    setIsMetadataModalOpen(true);
    try {
      const data = await ingestionsApi.getMetadata(ingestion.id);
      setMetadata(data);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao carregar metadados');
    }
  };

  const handleHistory = async (ingestion: Ingestion) => {
    setHistory([]);
    setIsHistoryModalOpen(true);
    try {
      const data = await ingestionsApi.getHistory(ingestion.id, 10);
      setHistory(data);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao carregar histórico');
    }
  };

  const toggleRowExpansion = (id: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  const toggleSelection = (id: string) => {
    const newSelected = new Set(selectedIngestions);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIngestions(newSelected);
  };

  const selectAll = () => {
    if (ingestions) {
      if (selectedIngestions.size === ingestions.length) {
        setSelectedIngestions(new Set());
      } else {
        setSelectedIngestions(new Set(ingestions.map(i => i.id)));
      }
    }
  };

  const getSourceType = (sourceId: string) => {
    return sources?.find(s => s.id === sourceId)?.type || 'unknown';
  };

  const getSourceName = (sourceId: string) => {
    return sources?.find(s => s.id === sourceId)?.name || sourceId;
  };

  const currentSource = sources?.find(s => s.id === formData.source_id);
  const isDatabaseSource = currentSource && ['postgres', 'mysql'].includes(currentSource.type);
  const isFileSource = currentSource && ['csv', 'excel', 'json', 'xml', 'parquet', 'avro', 'orc', 'sql_file'].includes(currentSource.type);

  return (
    <div className="space-y-6">
      {/* Header with Stats */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Ingestões</h1>
          <p className="text-gray-600 mt-1">Configure extração de dados de fontes para o warehouse</p>
        </div>
        
        {/* Stats Cards */}
        <div className="flex gap-3">
          {stats && (
            <>
              <div className="bg-white rounded-lg shadow px-4 py-2 flex items-center gap-2">
                <DatabaseIcon className="text-blue-600" size={20} />
                <div>
                  <p className="text-xs text-gray-500">Total</p>
                  <p className="text-lg font-bold text-gray-900">{stats.total_ingestions}</p>
                </div>
              </div>
              <div className="bg-white rounded-lg shadow px-4 py-2 flex items-center gap-2">
                <CheckCircle2 className="text-green-600" size={20} />
                <div>
                  <p className="text-xs text-gray-500">Válidas</p>
                  <p className="text-lg font-bold text-gray-900">{stats.valid}</p>
                </div>
              </div>
              <div className="bg-white rounded-lg shadow px-4 py-2 flex items-center gap-2">
                <TrendingUp className="text-purple-600" size={20} />
                <div>
                  <p className="text-xs text-gray-500">Linhas</p>
                  <p className="text-lg font-bold text-gray-900">{(stats.total_rows_ingested / 1000000).toFixed(1)}M</p>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Search and Filters Toolbar */}
      <div className="bg-white rounded-lg shadow p-4 space-y-4">
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="Buscar ingestões..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
          
          {/* Filters */}
          <div className="flex gap-2 flex-wrap">
            <select
              value={filterSource}
              onChange={(e) => setFilterSource(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Todas as fontes</option>
              {sources?.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
            
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Todos os status</option>
              <option value="valid">Válido</option>
              <option value="error">Erro</option>
              <option value="running">Executando</option>
              <option value="pending">Pendente</option>
            </select>
            
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            >
              <option value="created_at">Data de criação</option>
              <option value="name">Nome</option>
              <option value="last_run_at">Última execução</option>
              <option value="status">Status</option>
            </select>
            
            <button
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              className="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              title={sortOrder === 'asc' ? 'Ordem crescente' : 'Ordem decrescente'}
            >
              <ArrowUpDown size={18} className={sortOrder === 'desc' ? 'rotate-180' : ''} />
            </button>
            
            <button
              onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
              className={clsx(
                'px-3 py-2 rounded-lg border flex items-center gap-2',
                showFavoritesOnly ? 'bg-yellow-50 border-yellow-300 text-yellow-700' : 'border-gray-300 hover:bg-gray-50'
              )}
            >
              <Star size={18} className={showFavoritesOnly ? 'fill-current' : ''} />
              {showFavoritesOnly && 'Favoritos'}
            </button>
          </div>
        </div>

        {/* Bulk Actions */}
        {selectedIngestions.size > 0 && (
          <div className="flex items-center gap-2 pt-4 border-t">
            <span className="text-sm text-gray-600">
              {selectedIngestions.size} selecionado(s)
            </span>
            <button
              onClick={() => bulkDeleteMutation.mutate(Array.from(selectedIngestions))}
              className="px-3 py-1.5 bg-red-100 text-red-700 rounded-lg text-sm hover:bg-red-200 flex items-center gap-2"
            >
              <Trash2 size={16} />
              Remover
            </button>
            <button
              onClick={() => setSelectedIngestions(new Set())}
              className="px-3 py-1.5 text-gray-600 hover:text-gray-800 text-sm"
            >
              Limpar seleção
            </button>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex justify-between items-center">
        <div className="flex gap-2">
          <button
            onClick={() => setWizardOpen(true)}
            className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            <Wand2 size={20} />
            Assistente
          </button>

          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 px-4 py-2 rounded-lg font-medium transition-colors"
          >
            <Plus size={20} />
            Nova Ingestão
          </button>
          
          <button
            onClick={() => setIsBulkModalOpen(true)}
            className="flex items-center gap-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 px-4 py-2 rounded-lg font-medium transition-colors"
          >
            <Layers size={20} />
            Bulk Create
          </button>
        </div>
        
        {ingestions && (
          <p className="text-sm text-gray-500">
            {ingestions.length} ingestão(ões) encontrada(s)
          </p>
        )}
      </div>

      {/* Ingestions List */}
      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : ingestions && ingestions.length > 0 ? (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-3 w-10">
                  <input
                    type="checkbox"
                    checked={ingestions.length > 0 && selectedIngestions.size === ingestions.length}
                    onChange={selectAll}
                    className="rounded border-gray-300"
                  />
                </th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ingestão</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fonte</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Destino</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Última Execução</th>
                <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Ações</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {ingestions.map((ingestion) => (
                <Fragment key={ingestion.id}>
                  <tr key={ingestion.id} className={clsx('hover:bg-gray-50', expandedRows.has(ingestion.id) && 'bg-blue-50')}>
                    <td className="px-3 py-4">
                      <input
                        type="checkbox"
                        checked={selectedIngestions.has(ingestion.id)}
                        onChange={() => toggleSelection(ingestion.id)}
                        className="rounded border-gray-300"
                      />
                    </td>
                    <td className="px-3 py-4">
                      <div className="flex items-center">
                        <button
                          onClick={() => favoriteMutation.mutate(ingestion.id)}
                          className={clsx('mr-2', ingestion.is_favorite ? 'text-yellow-500' : 'text-gray-300 hover:text-yellow-500')}
                        >
                          <Star size={16} className={ingestion.is_favorite ? 'fill-current' : ''} />
                        </button>
                        <Download className="w-5 h-5 text-gray-400 mr-2" />
                        <div>
                          <span className="font-medium text-gray-900">{ingestion.name}</span>
                          {ingestion.description && (
                            <p className="text-xs text-gray-500 mt-0.5">{ingestion.description}</p>
                          )}
                          {ingestion.tags && ingestion.tags.length > 0 && (
                            <div className="flex gap-1 mt-1">
                              {ingestion.tags.map((tag, i) => (
                                <span key={i} className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-4">
                      <div className="space-y-1">
                        <p className="text-sm text-gray-900">{getSourceName(ingestion.source_id)}</p>
                        <SourceTypeBadge type={getSourceType(ingestion.source_id)} />
                      </div>
                    </td>
                    <td className="px-3 py-4">
                      <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono">
                        {ingestion.config?.target_table}
                      </code>
                    </td>
                    <td className="px-3 py-4">
                      <StatusBadge status={ingestion.status} validationStatus={ingestion.validation_status} />
                    </td>
                    <td className="px-3 py-4">
                      <div className="text-sm text-gray-600">
                        {ingestion.last_run_at ? (
                          <>
                            <p>{format(new Date(ingestion.last_run_at), 'dd/MM/yyyy HH:mm')}</p>
                            <p className="text-xs text-gray-400">
                              {formatDistanceToNow(new Date(ingestion.last_run_at), { addSuffix: true, locale: ptBR })}
                            </p>
                          </>
                        ) : (
                          'Nunca executada'
                        )}
                        {ingestion.last_run_rows !== undefined && (
                          <p className="text-xs text-gray-500 mt-1">
                            {ingestion.last_run_rows?.toLocaleString() || '0'} linhas
                            {ingestion.last_run_duration_ms && (
                              <span className="text-gray-400"> • {(ingestion.last_run_duration_ms / 1000).toFixed(1)}s</span>
                            )}
                          </p>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => toggleRowExpansion(ingestion.id)}
                          className="p-1.5 text-gray-400 hover:text-gray-600"
                          title={expandedRows.has(ingestion.id) ? 'Recolher' : 'Expandir'}
                        >
                          {expandedRows.has(ingestion.id) ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                        
                        <button
                          onClick={() => handlePreview(ingestion)}
                          className="p-1.5 text-blue-600 hover:text-blue-800"
                          title="Preview"
                        >
                          <Eye size={18} />
                        </button>
                        
                        <button
                          onClick={() => handleMetadata(ingestion)}
                          className="p-1.5 text-purple-600 hover:text-purple-800"
                          title="Metadados"
                        >
                          <Info size={18} />
                        </button>
                        
                        <button
                          onClick={() => handleValidate(ingestion.id)}
                          className="p-1.5 text-yellow-600 hover:text-yellow-800"
                          title="Validar"
                        >
                          <CheckCircle2 size={18} />
                        </button>
                        
                        <button
                          onClick={() => runMutation.mutate(ingestion.id)}
                          disabled={runMutation.isLoading || ingestion.status === 'running'}
                          className="p-1.5 text-green-600 hover:text-green-800 disabled:opacity-50"
                          title="Executar"
                        >
                          <Play size={18} />
                        </button>
                        
                        <button
                          onClick={() => handleEdit(ingestion)}
                          className="p-1.5 text-primary-600 hover:text-primary-800"
                          title="Editar"
                        >
                          <Edit3 size={18} />
                        </button>
                        
                        <button
                          onClick={() => deleteMutation.mutate(ingestion.id)}
                          className="p-1.5 text-red-600 hover:text-red-800"
                          title="Remover"
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </td>
                  </tr>
                  
                  {/* Expanded Row Details */}
                  {expandedRows.has(ingestion.id) && (
                    <tr className="bg-blue-50">
                      <td colSpan={7} className="px-6 py-4">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                          {/* Execution Stats */}
                          <div className="space-y-2">
                            <h5 className="font-medium text-gray-900 flex items-center gap-2">
                              <BarChart3 size={16} />
                              Estatísticas
                            </h5>
                            <div className="space-y-1 text-gray-600">
                              <p>Total de execuções: <span className="font-medium">{ingestion.total_runs || 0}</span></p>
                              <p>Total de linhas: <span className="font-medium">{(ingestion.total_rows_ingested || 0).toLocaleString()}</span></p>
                              {ingestion.avg_duration_ms && (
                                <p>Tempo médio: <span className="font-medium">{(ingestion.avg_duration_ms / 1000).toFixed(1)}s</span></p>
                              )}
                              {ingestion.avg_rows_per_run && (
                                <p>Linhas/média: <span className="font-medium">{ingestion.avg_rows_per_run?.toLocaleString() || '0'}</span></p>
                              )}
                            </div>
                            <button
                              onClick={() => handleHistory(ingestion)}
                              className="text-primary-600 hover:text-primary-800 flex items-center gap-1 text-xs"
                            >
                              <History size={14} />
                              Ver histórico completo
                            </button>
                          </div>
                          
                          {/* Configuration Summary */}
                          <div className="space-y-2">
                            <h5 className="font-medium text-gray-900 flex items-center gap-2">
                              <Settings size={16} />
                              Configuração
                            </h5>
                            <div className="space-y-1 text-gray-600">
                              <p>Modo: <span className="font-medium">{ingestion.config?.mode === 'table' ? 'Tabela' : 'Query'}</span></p>
                              {ingestion.incremental_config?.enabled && (
                                <p className="text-green-600 flex items-center gap-1">
                                  <Zap size={14} />
                                  Carga incremental ativa
                                </p>
                              )}
                              {ingestion.schedule_enabled && (
                                <p className="text-blue-600 flex items-center gap-1">
                                  <Clock size={14} />
                                  Agendado: {ingestion.schedule}
                                </p>
                              )}
                              {ingestion.selected_columns && ingestion.selected_columns.length > 0 && (
                                <p>{ingestion.selected_columns.length} colunas selecionadas</p>
                              )}
                              {ingestion.filters && ingestion.filters.length > 0 && (
                                <p>{ingestion.filters.length} filtros aplicados</p>
                              )}
                            </div>
                          </div>
                          
                          {/* Quick Actions */}
                          <div className="space-y-2">
                            <h5 className="font-medium text-gray-900">Ações Rápidas</h5>
                            <div className="flex flex-wrap gap-2">
                              <button
                                onClick={() => handlePreview(ingestion, { limit: 100 })}
                                className="px-2 py-1 bg-white border border-gray-300 rounded text-xs hover:bg-gray-50"
                              >
                                Preview (100)
                              </button>
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <Download className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Nenhuma ingestão encontrada</h3>
          <p className="text-gray-600 mb-4">
            {searchQuery || filterSource || filterStatus 
              ? 'Tente ajustar os filtros de busca'
              : 'Configure uma ingestão para extrair dados'}
          </p>
          {!searchQuery && !filterSource && !filterStatus && (
            <button
              onClick={() => setIsModalOpen(true)}
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              Criar primeira ingestão
            </button>
          )}
        </div>
      )}

      {/* Create/Edit Modal - Wizard */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4 my-8 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex justify-between items-center p-6 border-b sticky top-0 bg-white">
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  {editingIngestion ? 'Editar Ingestão' : 'Nova Ingestão'}
                </h2>
                <p className="text-sm text-gray-500">
                  {activeTab === 'basic' && 'Informações básicas'}
                  {activeTab === 'columns' && 'Seleção e mapeamento de colunas'}
                  {activeTab === 'filters' && 'Filtros de dados'}
                  {activeTab === 'advanced' && 'Agendamento e opções avançadas'}
                </p>
              </div>
              <button onClick={() => { setIsModalOpen(false); resetForm(); }} className="text-gray-400 hover:text-gray-600">
                <X size={24} />
              </button>
            </div>
            
            {/* Tabs Navigation */}
            <div className="border-b border-gray-200">
              <nav className="flex -mb-px">
                <button
                  onClick={() => setActiveTab('basic')}
                  className={clsx(
                    'py-3 px-4 text-sm font-medium border-b-2 whitespace-nowrap',
                    activeTab === 'basic'
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  )}
                >
                  <span className="flex items-center gap-2">
                    <Settings size={16} />
                    Básico
                  </span>
                </button>
                <button
                  onClick={() => setActiveTab('columns')}
                  className={clsx(
                    'py-3 px-4 text-sm font-medium border-b-2 whitespace-nowrap',
                    activeTab === 'columns'
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  )}
                >
                  <span className="flex items-center gap-2">
                    <Columns size={16} />
                    Colunas
                  </span>
                </button>
                <button
                  onClick={() => setActiveTab('filters')}
                  className={clsx(
                    'py-3 px-4 text-sm font-medium border-b-2 whitespace-nowrap',
                    activeTab === 'filters'
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  )}
                >
                  <span className="flex items-center gap-2">
                    <FilterIcon size={16} />
                    Filtros
                  </span>
                </button>
                <button
                  onClick={() => setActiveTab('advanced')}
                  className={clsx(
                    'py-3 px-4 text-sm font-medium border-b-2 whitespace-nowrap',
                    activeTab === 'advanced'
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  )}
                >
                  <span className="flex items-center gap-2">
                    <Zap size={16} />
                    Avançado
                  </span>
                </button>
              </nav>
            </div>
            
            {/* Form Content */}
            <div className="p-6">
              {/* Tab: Basic Info */}
              {activeTab === 'basic' && (
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                      placeholder="ex: ingestao_vendas"
                      required
                      pattern="[a-zA-Z0-9_]+"
                    />
                    <p className="text-xs text-gray-500 mt-1">Apenas letras, números e underscore</p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Descrição</label>
                    <textarea
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                      rows={2}
                      placeholder="Descreva o propósito desta ingestão..."
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Tags</label>
                    <div className="flex gap-2 mb-2">
                      <input
                        type="text"
                        value={newTag}
                        onChange={(e) => setNewTag(e.target.value)}
                        onKeyPress={(e) => {
                          if (e.key === 'Enter' && newTag.trim()) {
                            setFormData({ ...formData, tags: [...formData.tags, newTag.trim()] });
                            setNewTag('');
                          }
                        }}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                        placeholder="Adicionar tag..."
                      />
                      <button
                        onClick={() => {
                          if (newTag.trim()) {
                            setFormData({ ...formData, tags: [...formData.tags, newTag.trim()] });
                            setNewTag('');
                          }
                        }}
                        className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg"
                      >
                        <Plus size={18} />
                      </button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {formData.tags.map((tag, i) => (
                        <span key={i} className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
                          {tag}
                          <button
                            onClick={() => setFormData({ ...formData, tags: formData.tags.filter((_, idx) => idx !== i) })}
                            className="hover:text-blue-900"
                          >
                            <X size={14} />
                          </button>
                        </span>
                      ))}
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Fonte de Dados *</label>
                    <select
                      value={formData.source_id}
                      onChange={(e) => setFormData({ ...formData, source_id: e.target.value, table: '', query: '' })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                      required
                    >
                      <option value="">Selecione uma fonte</option>
                      {sources?.map((source) => (
                        <option key={source.id} value={source.id}>
                          {source.name} ({source.type})
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  {/* Smart Selection by Source Type */}
                  {currentSource && (
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-3">
                        {(() => {
                          const Icon = sourceTypeIcons[currentSource.type] || Database;
                          return <Icon className={sourceTypeColors[currentSource.type]} size={24} />;
                        })()}
                        <span className="font-medium text-gray-900">{currentSource.name}</span>
                        <SourceTypeBadge type={currentSource.type} />
                      </div>
                      
                      {/* Database Sources */}
                      {isDatabaseSource && (
                        <div className="space-y-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Modo de Extração</label>
                            <div className="flex gap-4">
                              <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                  type="radio"
                                  value="table"
                                  checked={formData.mode === 'table'}
                                  onChange={() => setFormData({ ...formData, mode: 'table', query: '' })}
                                  className="text-primary-600"
                                />
                                <span className="text-sm">Tabela completa</span>
                              </label>
                              <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                  type="radio"
                                  value="query"
                                  checked={formData.mode === 'query'}
                                  onChange={() => setFormData({ ...formData, mode: 'query', table: '' })}
                                  className="text-primary-600"
                                />
                                <span className="text-sm">Query SQL</span>
                              </label>
                            </div>
                          </div>
                          
                          {formData.mode === 'table' ? (
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">Tabela *</label>
                              <select
                                value={formData.table}
                                onChange={(e) => setFormData({ ...formData, table: e.target.value })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                                required={formData.mode === 'table'}
                              >
                                <option value="">Selecione uma tabela</option>
                                {availableTables.map((table) => (
                                  <option key={table} value={table}>{table}</option>
                                ))}
                              </select>
                            </div>
                          ) : (
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">Query SQL *</label>
                              <textarea
                                value={formData.query}
                                onChange={(e) => setFormData({ ...formData, query: e.target.value })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 font-mono text-sm"
                                rows={6}
                                placeholder="SELECT * FROM tabela WHERE ..."
                                required={formData.mode === 'query'}
                              />
                            </div>
                          )}
                        </div>
                      )}
                      
                      {/* File Sources */}
                      {isFileSource && (
                        <div className="space-y-3">
                          <p className="text-sm text-gray-600">
                            <span className="font-medium">Arquivo:</span> {currentSource.config.file_path}
                          </p>
                          <p className="text-xs text-gray-500 bg-yellow-50 p-2 rounded">
                            Fontes de arquivo usam o arquivo diretamente. Configure opções avançadas no próximo passo.
                          </p>
                          {formData.mode === 'table' && availableTables.length > 0 && (
                            <input 
                              type="hidden" 
                              value={availableTables[0]} 
                              onChange={() => {}}
                            />
                          )}
                        </div>
                      )}
                      
                      {/* Delta Lake */}
                      {currentSource.type === 'delta_lake' && (
                        <div className="space-y-3">
                          <p className="text-sm text-gray-600">
                            <span className="font-medium">Tabela:</span> {currentSource.config.table_path}
                          </p>
                          <div className="p-3 bg-cyan-50 rounded border border-cyan-200">
                            <p className="text-sm text-cyan-800 flex items-center gap-2">
                              <Info size={16} />
                              Time travel disponível. Configure versão específica nas opções avançadas.
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Tabela de Destino *</label>
                    <input
                      type="text"
                      value={formData.target_table}
                      onChange={(e) => setFormData({ ...formData, target_table: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                      placeholder={`ex: raw_${formData.name || 'dados'}`}
                      required
                    />
                    <p className="text-xs text-gray-500 mt-1">Nome da tabela no DuckDB (convenção: raw_*)</p>
                  </div>
                </div>
              )}
              
              {/* Tab: Columns - Column Selection & Mapping */}
              {activeTab === 'columns' && (
                <div className="space-y-6">
                  {/* Column Selection & Mapping */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Columns className="text-purple-600" size={20} />
                      <h3 className="font-medium text-gray-900">Seleção e Mapeamento de Colunas</h3>
                    </div>
                    
                    <div className="space-y-3">
                      <p className="text-sm text-gray-600">
                        Deixe vazio para importar todas as colunas, ou selecione específicas:
                      </p>
                      
                      {availableColumns.length > 0 ? (
                        <div className="max-h-48 overflow-y-auto bg-white rounded border border-gray-200 p-2">
                          <div className="flex items-center gap-2 mb-2 pb-2 border-b">
                            <input
                              type="checkbox"
                              checked={formData.selected_columns.length === availableColumns.length}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setFormData({ ...formData, selected_columns: availableColumns });
                                } else {
                                  setFormData({ ...formData, selected_columns: [] });
                                }
                              }}
                              className="rounded border-gray-300"
                            />
                            <span className="text-sm font-medium">Selecionar todas</span>
                          </div>
                          {availableColumns.map((col) => (
                            <label key={col} className="flex items-center gap-2 py-1 hover:bg-gray-50">
                              <input
                                type="checkbox"
                                checked={formData.selected_columns.includes(col)}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setFormData({ ...formData, selected_columns: [...formData.selected_columns, col] });
                                  } else {
                                    setFormData({ ...formData, selected_columns: formData.selected_columns.filter(c => c !== col) });
                                  }
                                }}
                                className="rounded border-gray-300"
                              />
                              <span className="text-sm font-mono">{col}</span>
                            </label>
                          ))}
                        </div>
                      ) : (
                        <div className="text-center py-6 bg-gray-50 rounded-lg">
                          <Columns className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                          <p className="text-sm text-gray-500 mb-3">
                            Nenhuma coluna carregada
                          </p>
                          <button
                            onClick={loadColumnsFromSource}
                            disabled={!currentSource}
                            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-300 text-white rounded-lg text-sm font-medium transition-colors"
                          >
                            {currentSource ? 'Detectar Colunas' : 'Selecione uma fonte primeiro'}
                          </button>
                          <p className="text-xs text-gray-400 mt-2">
                            Ou faça um preview da ingestão para carregar automaticamente
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Tab: Filters */}
              {activeTab === 'filters' && (
                <div className="space-y-6">
                  {/* Filters */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <FilterIcon className="text-blue-600" size={20} />
                      <h3 className="font-medium text-gray-900">Filtros</h3>
                    </div>
                    
                    <div className="space-y-3">
                      {formData.filters.map((filter, idx) => (
                        <div key={idx} className="flex items-center gap-2 bg-white p-2 rounded border">
                          <span className="text-sm font-mono">{filter.column}</span>
                          <span className="text-sm text-gray-500">{operatorLabels[filter.operator]}</span>
                          <span className="text-sm font-medium">{filter.value}</span>
                          <button
                            onClick={() => setFormData({
                              ...formData,
                              filters: formData.filters.filter((_, i) => i !== idx)
                            })}
                            className="ml-auto text-red-500 hover:text-red-700"
                          >
                            <X size={16} />
                          </button>
                        </div>
                      ))}
                      
                      {availableColumns.length === 0 && (
                        <div className="text-center py-4 bg-yellow-50 rounded-lg">
                          <FilterIcon className="w-6 h-6 text-yellow-600 mx-auto mb-2" />
                          <p className="text-sm text-yellow-700 mb-2">
                            Carregue as colunas primeiro para adicionar filtros
                          </p>
                          <button
                            onClick={() => setActiveTab('columns')}
                            className="text-sm text-primary-600 hover:text-primary-800 underline"
                          >
                            Ir para aba Colunas
                          </button>
                        </div>
                      )}
                      
                      <div className={clsx("flex gap-2", availableColumns.length === 0 && "opacity-50 pointer-events-none")}>
                        <select
                          value={newFilter.column}
                          onChange={(e) => setNewFilter({ ...newFilter, column: e.target.value })}
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
                        >
                          <option value="">Coluna...</option>
                          {availableColumns.map(col => (
                            <option key={col} value={col}>{col}</option>
                          ))}
                        </select>
                        <select
                          value={newFilter.operator}
                          onChange={(e) => setNewFilter({ ...newFilter, operator: e.target.value as any })}
                          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
                        >
                          {Object.entries(operatorLabels).map(([key, label]) => (
                            <option key={key} value={key}>{label}</option>
                          ))}
                        </select>
                        <input
                          type="text"
                          value={newFilter.value}
                          onChange={(e) => setNewFilter({ ...newFilter, value: e.target.value })}
                          placeholder="Valor"
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
                        />
                        <button
                          onClick={() => {
                            if (newFilter.column && newFilter.value) {
                              setFormData({ ...formData, filters: [...formData.filters, newFilter] });
                              setNewFilter({ column: '', operator: 'eq', value: '' });
                            }
                          }}
                          className="px-3 py-2 bg-primary-600 text-white rounded-lg text-sm"
                        >
                          <Plus size={16} />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab: Advanced - Incremental + Scheduling + Templates + Validation */}
              {activeTab === 'advanced' && (
                <div className="space-y-6">
                  {/* Incremental Loading */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Zap className="text-yellow-600" size={20} />
                      <h3 className="font-medium text-gray-900">Carga Incremental</h3>
                    </div>
                    
                    <div className="flex items-center gap-3 mb-4">
                      <input
                        type="checkbox"
                        id="incremental_enabled"
                        checked={formData.incremental_config.enabled}
                        onChange={(e) => setFormData({
                          ...formData,
                          incremental_config: { ...formData.incremental_config, enabled: e.target.checked }
                        })}
                        className="w-4 h-4 text-primary-600 rounded"
                      />
                      <label htmlFor="incremental_enabled" className="text-sm font-medium text-gray-700">
                        Ativar carga incremental
                      </label>
                    </div>
                    
                    {formData.incremental_config.enabled && (
                      <div className="space-y-3 pl-7">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Coluna de Controle</label>
                          {availableColumns.length > 0 ? (
                            <select
                              value={formData.incremental_config.control_column || ''}
                              onChange={(e) => setFormData({
                                ...formData,
                                incremental_config: { ...formData.incremental_config, control_column: e.target.value }
                              })}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                            >
                              <option value="">Selecione uma coluna...</option>
                              {availableColumns.map(col => (
                                <option key={col} value={col}>{col}</option>
                              ))}
                            </select>
                          ) : (
                            <>
                              <input
                                type="text"
                                value={formData.incremental_config.control_column || ''}
                                onChange={(e) => setFormData({
                                  ...formData,
                                  incremental_config: { ...formData.incremental_config, control_column: e.target.value }
                                })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                                placeholder="ex: updated_at, id"
                              />
                              <p className="text-xs text-yellow-600 mt-1">
                                💡 Dica: Carregue as colunas na aba "Colunas" para ver opções disponíveis
                              </p>
                            </>
                          )}
                          <p className="text-xs text-gray-500 mt-1">Coluna para rastrear novos registros (timestamp ou ID incremental)</p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Scheduling */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Clock className="text-blue-600" size={20} />
                      <h3 className="font-medium text-gray-900">Agendamento</h3>
                    </div>
                    
                    <div className="flex items-center gap-3 mb-4">
                      <input
                        type="checkbox"
                        id="schedule_enabled"
                        checked={formData.schedule_enabled}
                        onChange={(e) => setFormData({ ...formData, schedule_enabled: e.target.checked })}
                        className="w-4 h-4 text-primary-600 rounded"
                      />
                      <label htmlFor="schedule_enabled" className="text-sm font-medium text-gray-700">
                        Ativar agendamento
                      </label>
                    </div>
                    
                    {formData.schedule_enabled && (
                      <div className="space-y-3 pl-7">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Expressão Cron</label>
                          <input
                            type="text"
                            value={formData.schedule}
                            onChange={(e) => setFormData({ ...formData, schedule: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 font-mono"
                            placeholder="0 */6 * * *"
                          />
                          <p className="text-xs text-gray-500 mt-1">
                            Exemplos: <code className="bg-gray-200 px-1 rounded">0 * * * *</code> (hora em hora), 
                            <code className="bg-gray-200 px-1 rounded">0 2 * * *</code> (2am diário)
                          </p>
                        </div>
                        
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
                          <select
                            value={formData.schedule_timezone}
                            onChange={(e) => setFormData({ ...formData, schedule_timezone: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                          >
                            <option value="America/Sao_Paulo">América/São Paulo</option>
                            <option value="America/New_York">América/New York</option>
                            <option value="Europe/London">Europa/Londres</option>
                            <option value="UTC">UTC</option>
                          </select>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {/* Templates */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Wand2 className="text-purple-600" size={20} />
                      <h3 className="font-medium text-gray-900">Templates</h3>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {templates.map((template) => (
                        <button
                          key={template.id}
                          onClick={() => {
                            // Apply template values to form
                            if (template.config.incremental_config) {
                              setFormData({
                                ...formData,
                                incremental_config: { ...formData.incremental_config, ...template.config.incremental_config }
                              });
                            }
                            if (template.config.advanced_options) {
                              setFormData({
                                ...formData,
                                advanced_options: { ...formData.advanced_options, ...template.config.advanced_options }
                              });
                            }
                            toast.success(`Template "${template.name}" aplicado!`);
                          }}
                          className="p-3 bg-white border border-gray-200 rounded-lg hover:border-primary-500 hover:shadow-sm text-left transition-all"
                        >
                          <p className="font-medium text-gray-900 text-sm">{template.name}</p>
                          <p className="text-xs text-gray-500 mt-1">{template.description}</p>
                          <p className="text-xs text-primary-600 mt-1">
                            Para: {template.applies_to.join(', ')}
                          </p>
                        </button>
                      ))}
                    </div>
                  </div>
                  
                  {/* Validation */}
                  <div>
                    <button
                      onClick={() => handleValidate()}
                      disabled={!editingIngestion || validateMutation.isLoading}
                      className="w-full py-2 bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center justify-center gap-2 text-sm font-medium text-gray-700 disabled:opacity-50"
                    >
                      {validateMutation.isLoading ? (
                        <Loader2 className="animate-spin" size={18} />
                      ) : (
                        <CheckCircle2 size={18} />
                      )}
                      Validar Configuração
                    </button>
                    
                    {validation && (
                      <div className="mt-3">
                        <ValidationPanel validation={validation} />
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
            
            {/* Modal Footer */}
            <div className="p-6 border-t bg-gray-50 flex justify-end items-center gap-2">
              <button
                onClick={() => { setIsModalOpen(false); resetForm(); }}
                className="px-4 py-2 text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 rounded-lg font-medium transition-colors"
              >
                Cancelar
              </button>
              
              <button
                onClick={handleSubmit}
                disabled={createMutation.isLoading || updateMutation.isLoading}
                className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {(createMutation.isLoading || updateMutation.isLoading) ? (
                  <Loader2 className="animate-spin" size={18} />
                ) : (
                  <Check size={18} />
                )}
                {editingIngestion ? 'Salvar' : 'Criar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bulk Create Modal */}
      {isBulkModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-900">Criar Múltiplas Ingestões</h2>
              <button onClick={() => setIsBulkModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X size={24} />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Fonte de Dados *</label>
                <select
                  value={bulkSourceId}
                  onChange={(e) => setBulkSourceId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">Selecione uma fonte</option>
                  {sources?.filter(s => ['postgres', 'mysql'].includes(s.type)).map((source) => (
                    <option key={source.id} value={source.id}>{source.name} ({source.type})</option>
                  ))}
                </select>
              </div>
              
              {bulkSourceId && bulkTables.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Tabelas *</label>
                  <div className="max-h-48 overflow-y-auto bg-gray-50 rounded-lg p-3 border border-gray-200">
                    <div className="mb-2 pb-2 border-b">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={bulkTables.length > 0 && bulkTables.every(t => selectedIngestions.has(t))}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedIngestions(new Set(bulkTables));
                            } else {
                              setSelectedIngestions(new Set());
                            }
                          }}
                          className="rounded border-gray-300"
                        />
                        <span className="text-sm font-medium">Selecionar todas</span>
                      </label>
                    </div>
                    {bulkTables.map((table) => (
                      <label key={table} className="flex items-center gap-2 py-1 cursor-pointer hover:bg-gray-100 rounded px-2">
                        <input
                          type="checkbox"
                          checked={selectedIngestions.has(table)}
                          onChange={(e) => {
                            const newSelected = new Set(selectedIngestions);
                            if (e.target.checked) {
                              newSelected.add(table);
                            } else {
                              newSelected.delete(table);
                            }
                            setSelectedIngestions(newSelected);
                          }}
                          className="rounded border-gray-300"
                        />
                        <span className="text-sm font-mono">{table}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Padrão de Nomenclatura</label>
                <input
                  type="text"
                  value={bulkNamingPattern}
                  onChange={(e) => setBulkNamingPattern(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  placeholder="raw_{name}"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Use <code className="bg-gray-200 px-1 rounded">{'{name}'}</code> para o nome da tabela
                </p>
              </div>
            </div>
            
            <div className="p-6 border-t bg-gray-50 flex justify-end gap-2">
              <button
                onClick={() => setIsBulkModalOpen(false)}
                className="px-4 py-2 text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 rounded-lg font-medium transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={() => bulkCreateMutation.mutate({
                  source_id: bulkSourceId,
                  tables: Array.from(selectedIngestions),
                  naming_pattern: bulkNamingPattern,
                })}
                disabled={!bulkSourceId || selectedIngestions.size === 0 || bulkCreateMutation.isLoading}
                className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                {bulkCreateMutation.isLoading ? (
                  <Loader2 className="animate-spin inline mr-2" size={18} />
                ) : null}
                Criar {selectedIngestions.size} Ingestão(ões)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {isPreviewModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl mx-4 max-h-[90vh] overflow-hidden">
            <div className="flex justify-between items-center p-6 border-b">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Preview dos Dados</h2>
                  {previewData && (
                    <p className="text-sm text-gray-600">
                      {(previewData.total_rows || 0).toLocaleString()} linhas • {previewData.columns.length} colunas
                    </p>
                  )}
              </div>
              <button onClick={() => setIsPreviewModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X size={24} />
              </button>
            </div>
            
            <div className="overflow-auto max-h-[60vh]">
              {previewData ? (
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      {previewData.columns.map((col) => (
                        <th 
                          key={col} 
                          className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                        >
                          <div>
                            <span className="font-mono">{col}</span>
                            {previewData.dtypes?.[col] && (
                              <p className="text-gray-400 font-normal normal-case">
                                {previewData.dtypes[col]}
                              </p>
                            )}
                            {(previewData.null_counts?.[col] ?? 0) > 0 && (
                              <p className="text-yellow-600 font-normal normal-case text-xs">
                                {previewData.null_counts?.[col]} nulos
                              </p>
                            )}
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {previewData.data.map((row, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        {previewData.columns.map((col) => (
                          <td key={col} className="px-4 py-3 text-sm text-gray-900 font-mono">
                            {row[col] === null ? (
                              <span className="text-gray-400 italic">null</span>
                            ) : typeof row[col] === 'object' ? (
                              <span className="text-blue-600">{JSON.stringify(row[col])}</span>
                            ) : (
                              String(row[col])
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="flex justify-center items-center h-64">
                  <Loader2 className="animate-spin h-8 w-8 text-primary-600" />
                </div>
              )}
            </div>
            
            <div className="p-6 border-t flex justify-between items-center">
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    if (previewData && expandedRows.size > 0) {
                      const ingestionId = Array.from(expandedRows)[0];
                      const ingestion = ingestions?.find(i => i.id === ingestionId);
                      if (ingestion) handlePreview(ingestion, { limit: 100 });
                    }
                  }}
                  className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium text-sm"
                >
                  Carregar 100 linhas
                </button>
              </div>
              <button
                onClick={() => setIsPreviewModalOpen(false)}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* History Modal */}
      {isHistoryModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl mx-4 max-h-[80vh] overflow-hidden">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-900">Histórico de Execuções</h2>
              <button onClick={() => setIsHistoryModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X size={24} />
              </button>
            </div>
            
            <div className="overflow-auto max-h-[60vh]">
              {history.length > 0 ? (
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Início</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duração</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Linhas</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Erro</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {history.map((log) => (
                      <tr key={log.id}>
                        <td className="px-6 py-4 text-sm text-gray-900">
                          {format(new Date(log.started_at), 'dd/MM/yyyy HH:mm:ss')}
                        </td>
                        <td className="px-6 py-4">
                          <span className={clsx(
                            'px-2 py-1 rounded-full text-xs font-medium',
                            log.status === 'success' ? 'bg-green-100 text-green-800' :
                            log.status === 'error' ? 'bg-red-100 text-red-800' :
                            'bg-blue-100 text-blue-800'
                          )}>
                            {log.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">
                          {log.duration_ms ? `${(log.duration_ms / 1000).toFixed(1)}s` : '-'}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">
                          {log.rows_affected?.toLocaleString() || '-'}
                        </td>
                        <td className="px-6 py-4 text-sm text-red-600 max-w-xs truncate" title={log.error_message}>
                          {log.error_message || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="p-12 text-center text-gray-500">
                  <History className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Nenhum histórico disponível</p>
                </div>
              )}
            </div>
            
            <div className="p-6 border-t">
              <button
                onClick={() => setIsHistoryModalOpen(false)}
                className="w-full px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Metadata Modal */}
      {isMetadataModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[80vh] overflow-hidden">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-900">Metadados</h2>
              <button onClick={() => setIsMetadataModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X size={24} />
              </button>
            </div>
            
            <div className="overflow-auto max-h-[60vh] p-6">
              <MetadataPanel metadata={metadata} />
            </div>
            
            <div className="p-6 border-t">
              <button
                onClick={() => setIsMetadataModalOpen(false)}
                className="w-full px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Assistente guiado de nova ingestao */}
      <IngestionWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        onCreated={() => {
          queryClient.invalidateQueries('ingestions');
          queryClient.invalidateQueries('catalog');
        }}
      />
    </div>
  );
}
