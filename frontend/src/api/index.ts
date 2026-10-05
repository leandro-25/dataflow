import axios from 'axios';
import { 
  Source, 
  CreateSourceRequest, 
  UpdateSourceRequest, 
  TestConnectionResponse,
  Ingestion,
  CreateIngestionRequest,
  UpdateIngestionRequest,
  PreviewData,
  RunIngestionResponse,
  Staging,
  CreateStagingRequest,
  UpdateStagingRequest,
  TransformType,
  Dimension,
  CreateDimensionRequest,
  UpdateDimensionRequest,
  Fact,
  CreateFactRequest,
  UpdateFactRequest,
  Metric,
  CreateMetricRequest,
  UpdateMetricRequest,
  MetricQueryResponse,
  Dashboard,
  CreateDashboardRequest,
  UpdateDashboardRequest,
  CatalogTable,
  CatalogTableInfo,
  ExecutionLog
} from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Sources API
export const sourcesApi = {
  list: () => api.get<Source[]>('/sources').then(res => res.data),
  get: (id: string) => api.get<Source>(`/sources/${id}`).then(res => res.data),
  create: (data: CreateSourceRequest) => api.post<Source>('/sources', data).then(res => res.data),
  update: (id: string, data: UpdateSourceRequest) => api.put<Source>(`/sources/${id}`, data).then(res => res.data),
  delete: (id: string) => api.delete(`/sources/${id}`).then(res => res.data),
  testConnection: (id: string) => api.post<TestConnectionResponse>(`/sources/${id}/test`).then(res => res.data),
  listTables: (id: string) => api.get<{ tables: string[] }>(`/sources/${id}/tables`).then(res => res.data),
  getSchema: (id: string, table: string) => api.get<{ schema: any[] }>(`/sources/${id}/schema/${table}`).then(res => res.data),
  validate: (data: { type: string; config: any }) =>
    api.post<TestConnectionResponse>('/sources/validate', data).then(res => res.data),
};

// Ingestions API
export const ingestionsApi = {
  list: (params?: { 
    search?: string; 
    source_id?: string; 
    status?: string; 
    tag?: string;
    favorite_only?: boolean;
    sort_by?: string;
    sort_order?: string;
  }) => api.get<Ingestion[]>('/ingestions', { params }).then(res => res.data),
  get: (id: string) => api.get<Ingestion>(`/ingestions/${id}`).then(res => res.data),
  create: (data: CreateIngestionRequest) => api.post<Ingestion>('/ingestions', data).then(res => res.data),
  update: (id: string, data: UpdateIngestionRequest) => api.put<Ingestion>(`/ingestions/${id}`, data).then(res => res.data),
  delete: (id: string) => api.delete(`/ingestions/${id}`).then(res => res.data),
  preview: (id: string, options?: { limit?: number }) => api.post<PreviewData>(`/ingestions/${id}/preview`, options).then(res => res.data),
  run: (id: string) => api.post<RunIngestionResponse>(`/ingestions/${id}/run`).then(res => res.data),
  
  // New endpoints
  getStats: () => api.get<{
    total_ingestions: number;
    running: number;
    error: number;
    valid: number;
    total_rows_ingested: number;
    today_runs: number;
  }>('/ingestions/stats/overview').then(res => res.data),
  getHistory: (id: string, limit?: number) => api.get<any[]>(`/ingestions/${id}/history`, { params: { limit } }).then(res => res.data),
  validate: (id: string) => api.post<{ valid: boolean; status: string; message: string; warnings: string[]; errors: string[] }>(`/ingestions/${id}/validate`).then(res => res.data),
  getMetadata: (id: string) => api.get<any>(`/ingestions/${id}/metadata`).then(res => res.data),
  toggleFavorite: (id: string) => api.patch<{ is_favorite: boolean }>(`/ingestions/${id}/favorite`).then(res => res.data),
  runAsync: (id: string) => api.post<{ success: boolean; message: string; ingestion_id: string }>(`/ingestions/${id}/run-async`).then(res => res.data),
  
  // Bulk operations
  bulkCreate: (data: { source_id: string; tables: string[]; naming_pattern?: string; config_template?: any }) => 
    api.post<{ created: any[]; errors: string[]; total: number; success: number }>('/ingestions/bulk/create', data).then(res => res.data),
  bulkDelete: (ids: string[]) => api.post<{ deleted: number; errors: string[] }>('/ingestions/bulk/delete', ids).then(res => res.data),
  duplicate: (id: string, new_name: string) => api.post<Ingestion>(`/ingestions/${id}/duplicate`, null, { params: { new_name } }).then(res => res.data),
  
  // Templates
  getTemplates: () => api.get<any[]>('/ingestions/templates/list').then(res => res.data),
  applyTemplate: (id: string, template_id: string) => api.post<{ success: boolean; template_applied: string }>(`/ingestions/${id}/apply-template`, { template_id }).then(res => res.data),
  
  // Progress Tracking
  getProgress: (id: string) => api.get<{
    status: string;
    progress: {
      percent: number;
      rows_processed: number;
      rows_total: number;
      stage: string;
      speed: number;
      eta_seconds: number;
      current_batch: number;
      total_batches: number;
      message: string;
    } | null;
    message: string;
  }>(`/ingestions/${id}/progress`).then(res => res.data),
  
  // Drag & Drop Reordering
  reorder: (orders: Array<{ ingestion_id: string; sort_order: number; folder?: string }>) => 
    api.post('/ingestions/reorder', orders).then(res => res.data),
  setFolder: (id: string, folder: string) => 
    api.put(`/ingestions/${id}/folder`, { folder }).then(res => res.data),
  getFolders: () => api.get<string[]>('/ingestions/folders').then(res => res.data),
  
  // Type Mapping
  getTypeMapping: (id: string) => api.get<{
    schema: any[];
    type_suggestions: Record<string, any>;
    current_mappings: Record<string, any>;
  }>(`/ingestions/${id}/type-mapping`).then(res => res.data),
  updateTypeMapping: (id: string, mappings: Record<string, any>) => 
    api.post(`/ingestions/${id}/type-mapping`, mappings).then(res => res.data),
  
  // Auto-Detection
  detectFileFormat: (file_path: string) => api.post<{
    encoding: string;
    encoding_confidence: number;
    delimiter: string;
    has_header: boolean;
    first_line_preview: string;
  }>('/ingestions/detect-file-format', { file_path }).then(res => res.data),
  analyzeJsonStructure: (file_path: string) => api.post<{
    structure: any[];
    suggested_data_paths: any[];
    root_type: string;
    is_array: boolean;
    array_length: number | null;
  }>('/ingestions/analyze-json-structure', { file_path }).then(res => res.data),
  analyzeXmlStructure: (file_path: string) => api.post<{
    root_tag: string;
    structure: any[];
    potential_row_elements: any[];
    unique_tags: number;
  }>('/ingestions/analyze-xml-structure', { file_path }).then(res => res.data),
  
  // Keyboard Shortcuts
  getShortcuts: () => api.get<Array<{ id: string; key: string; action: string; description: string }>>('/ingestions/shortcuts/list').then(res => res.data),
  createShortcut: (shortcut: { key: string; action: string; description?: string; enabled?: boolean }) => 
    api.post('/ingestions/shortcuts/create', shortcut).then(res => res.data),

  // Dry-run (testar extracao sem salvar)
  dryRun: (data: { source_id: string; config: any; filters?: any[]; column_mapping?: any; limit?: number }) =>
    api.post<{ columns: string[]; data: any[]; total_rows: number }>('/ingestions/dry-run', data).then(res => res.data),
};

// Staging API
export const stagingApi = {
  list: () => api.get<Staging[]>('/staging').then(res => res.data),
  get: (id: string) => api.get<Staging>(`/staging/${id}`).then(res => res.data),
  create: (data: CreateStagingRequest) => api.post<Staging>('/staging', data).then(res => res.data),
  update: (id: string, data: UpdateStagingRequest) => api.put<Staging>(`/staging/${id}`, data).then(res => res.data),
  delete: (id: string) => api.delete(`/staging/${id}`).then(res => res.data),
  getTransformTypes: () => api.get<TransformType[]>('/staging/transforms/types').then(res => res.data),
  preview: (id: string) => api.post<PreviewData>(`/staging/${id}/preview`).then(res => res.data),
  run: (id: string) => api.post<RunIngestionResponse>(`/staging/${id}/run`).then(res => res.data),
  dryRun: (data: { source_table: string; transforms?: any[]; mode?: string; custom_sql?: string; limit?: number }) =>
    api.post<{ columns: string[]; data: any[]; total_rows: number; source_total_rows: number; sql: string }>(
      '/staging/dry-run', data
    ).then(res => res.data),
};

// Dimensions API
export const dimensionsApi = {
  list: () => api.get<Dimension[]>('/dimensions').then(res => res.data),
  get: (id: string) => api.get<Dimension>(`/dimensions/${id}`).then(res => res.data),
  create: (data: CreateDimensionRequest) => api.post<Dimension>('/dimensions', data).then(res => res.data),
  update: (id: string, data: UpdateDimensionRequest) => api.put<Dimension>(`/dimensions/${id}`, data).then(res => res.data),
  delete: (id: string) => api.delete(`/dimensions/${id}`).then(res => res.data),
  preview: (id: string) => api.post<PreviewData>(`/dimensions/${id}/preview`).then(res => res.data),
  run: (id: string) => api.post<RunIngestionResponse>(`/dimensions/${id}/run`).then(res => res.data),
};

// Facts API
export const factsApi = {
  list: () => api.get<Fact[]>('/facts').then(res => res.data),
  get: (id: string) => api.get<Fact>(`/facts/${id}`).then(res => res.data),
  create: (data: CreateFactRequest) => api.post<Fact>('/facts', data).then(res => res.data),
  update: (id: string, data: UpdateFactRequest) => api.put<Fact>(`/facts/${id}`, data).then(res => res.data),
  delete: (id: string) => api.delete(`/facts/${id}`).then(res => res.data),
  preview: (id: string) => api.post<PreviewData>(`/facts/${id}/preview`).then(res => res.data),
  run: (id: string) => api.post<RunIngestionResponse>(`/facts/${id}/run`).then(res => res.data),
};

// Metrics API
export const metricsApi = {
  list: () => api.get<Metric[]>('/metrics').then(res => res.data),
  get: (id: string) => api.get<Metric>(`/metrics/${id}`).then(res => res.data),
  create: (data: CreateMetricRequest) => api.post<Metric>('/metrics', data).then(res => res.data),
  update: (id: string, data: UpdateMetricRequest) => api.put<Metric>(`/metrics/${id}`, data).then(res => res.data),
  delete: (id: string) => api.delete(`/metrics/${id}`).then(res => res.data),
  query: (id: string, filters?: any) => api.post<MetricQueryResponse>(`/metrics/${id}/query`, { filters }).then(res => res.data),
};

// Dashboards API
export const dashboardsApi = {
  list: () => api.get<Dashboard[]>('/dashboards').then(res => res.data),
  get: (id: string) => api.get<Dashboard>(`/dashboards/${id}`).then(res => res.data),
  create: (data: CreateDashboardRequest) => api.post<Dashboard>('/dashboards', data).then(res => res.data),
  update: (id: string, data: UpdateDashboardRequest) => api.put<Dashboard>(`/dashboards/${id}`, data).then(res => res.data),
  delete: (id: string) => api.delete(`/dashboards/${id}`).then(res => res.data),
  getData: (id: string) => api.get<{ components: any[] }>(`/dashboards/${id}/data`).then(res => res.data),
};

// Catalog API
export const catalogApi = {
  listTables: () => api.get<{ tables: CatalogTable[] }>('/catalog/tables').then(res => res.data),
  getTableInfo: (name: string) => api.get<CatalogTableInfo>(`/catalog/tables/${name}`).then(res => res.data),
  getTableData: (name: string, limit = 100, offset = 0) => 
    api.get<{ columns: string[], data: any[], total: number, limit: number, offset: number }>(`/catalog/tables/${name}/data?limit=${limit}&offset=${offset}`).then(res => res.data),
  getTableSchema: (name: string) => api.get<{ schema: any[] }>(`/catalog/tables/${name}/schema`).then(res => res.data),
  executeQuery: (sql: string) => api.post<{ columns: string[], data: any[], row_count: number }>('/catalog/query', { sql }).then(res => res.data),
};

// Execution API
export const executionApi = {
  getDag: () => api.get<{ nodes: any[], edges: any[] }>('/execution/dag').then(res => res.data),
  runPipeline: () => api.post<{ success: boolean, results: any[] }>('/execution/run').then(res => res.data),
  getLogs: (limit = 100) => api.get<ExecutionLog[]>(`/execution/logs?limit=${limit}`).then(res => res.data),
  getExecutionLogs: (executionId: string) => api.get<ExecutionLog[]>(`/execution/logs/${executionId}`).then(res => res.data),
};

// Overview API
export const overviewApi = {
  get: () => api.get<{
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
  }>('/overview').then(res => res.data),
};

// Filesystem API
export interface FileSystemEntry {
  name: string;
  path: string;
  is_dir: boolean;
  size: number | null;
  modified: string | null;
}

export const filesystemApi = {
  list: (path?: string) => api.get<{
    path: string;
    parent: string | null;
    entries: FileSystemEntry[];
    shortcuts: { name: string; path: string }[];
  }>('/filesystem/list', { params: { path } }).then(res => res.data),
};

export default api;
