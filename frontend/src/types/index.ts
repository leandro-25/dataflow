export interface Source {
  id: string;
  name: string;
  type: 'postgres' | 'mysql' | 'csv' | 'excel' | 'json' | 'xml' | 'parquet' | 'avro' | 'orc' | 'sql_file' | 'delta_lake' | 'rest_api' | 'google_sheets';
  config: Record<string, any>;
  status: 'valid' | 'invalid' | 'pending';
  created_at: string;
  updated_at: string;
}

export interface CreateSourceRequest {
  name: string;
  type: string;
  config: Record<string, any>;
  status?: string;
}

export interface UpdateSourceRequest {
  name?: string;
  type?: string;
  config?: Record<string, any>;
  status?: string;
}

export interface TestConnectionResponse {
  success: boolean;
  message: string;
  tables?: string[];
}

export interface Ingestion {
  id: string;
  name: string;
  source_id: string;
  config: {
    mode: 'table' | 'query';
    table?: string;
    query?: string;
    target_table: string;
  };
  
  // Scheduling
  schedule?: string;
  schedule_enabled?: boolean;
  schedule_timezone?: string;
  
  // Column mapping and transformations
  column_mapping?: Record<string, {
    target_name: string;
    target_type?: string;
    nullable?: boolean;
    default_value?: any;
  }>;
  filters?: Array<{
    column: string;
    operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'contains';
    value: any;
  }>;
  selected_columns?: string[];
  
  // Incremental loading
  incremental_config?: {
    enabled: boolean;
    control_column?: string;
    last_value?: string;
  };
  
  // Advanced options
  advanced_options?: Record<string, any>;
  
  // Metadata
  tags?: string[];
  description?: string;
  is_favorite?: boolean;
  
  // Validation
  status: 'pending' | 'valid' | 'invalid' | 'running' | 'error';
  validation_status?: 'success' | 'warning' | 'error';
  validation_message?: string;
  
  // Execution metrics
  last_run_at?: string;
  last_run_status?: string;
  last_run_rows?: number;
  last_run_duration_ms?: number;
  last_run_error?: string;
  
  total_runs?: number;
  total_rows_ingested?: number;
  avg_rows_per_run?: number;
  avg_duration_ms?: number;
  
  created_at: string;
  updated_at: string;
}

export interface CreateIngestionRequest {
  name: string;
  source_id: string;
  config: {
    mode: 'table' | 'query';
    table?: string;
    query?: string;
    target_table: string;
  };
  schedule?: string;
  schedule_enabled?: boolean;
  schedule_timezone?: string;
  column_mapping?: Record<string, any>;
  filters?: any[];
  selected_columns?: string[];
  incremental_config?: {
    enabled: boolean;
    control_column?: string;
    last_value?: string;
  };
  advanced_options?: Record<string, any>;
  tags?: string[];
  description?: string;
}

export interface UpdateIngestionRequest {
  name?: string;
  source_id?: string;
  config?: {
    mode?: 'table' | 'query';
    table?: string;
    query?: string;
    target_table?: string;
  };
  schedule?: string;
  schedule_enabled?: boolean;
  schedule_timezone?: string;
  column_mapping?: Record<string, any>;
  filters?: any[];
  selected_columns?: string[];
  incremental_config?: {
    enabled: boolean;
    control_column?: string;
    last_value?: string;
  };
  advanced_options?: Record<string, any>;
  tags?: string[];
  description?: string;
  status?: string;
}

export interface PreviewData {
  columns: string[];
  data: Record<string, any>[];
  total_rows: number;
  dtypes?: Record<string, string>;
  null_counts?: Record<string, number>;
}

export interface RunIngestionResponse {
  success: boolean;
  message: string;
  rows_affected: number;
  duration_ms?: number;
  target_table: string;
  execution_id?: string;
}

export interface Transform {
  type: string;
  config: Record<string, any>;
}

export interface TransformType {
  type: string;
  label: string;
  description: string;
  config_schema: Record<string, any>;
}

export interface Staging {
  id: string;
  name: string;
  source_table: string;
  target_table: string;
  transforms: Transform[];
  mode: 'visual' | 'yaml' | 'sql';
  custom_sql?: string;
  status: 'pending' | 'valid' | 'invalid' | 'running' | 'error';
  created_at: string;
  updated_at: string;
}

export interface CreateStagingRequest {
  name: string;
  source_table: string;
  target_table: string;
  transforms?: Transform[];
  mode?: 'visual' | 'yaml' | 'sql';
  custom_sql?: string;
}

export interface UpdateStagingRequest {
  name?: string;
  source_table?: string;
  target_table?: string;
  transforms?: Transform[];
  mode?: 'visual' | 'yaml' | 'sql';
  custom_sql?: string;
  status?: string;
}

export interface Dimension {
  id: string;
  name: string;
  source_table: string;
  target_table: string;
  primary_key: string;
  surrogate_key?: string;
  attributes: string[];
  hierarchies?: any[];
  mode: 'visual' | 'yaml' | 'sql';
  custom_sql?: string;
  status: 'pending' | 'valid' | 'invalid' | 'running' | 'error';
  created_at: string;
  updated_at: string;
}

export interface CreateDimensionRequest {
  name: string;
  source_table: string;
  target_table: string;
  primary_key: string;
  surrogate_key?: string;
  attributes?: string[];
  hierarchies?: any[];
  mode?: 'visual' | 'yaml' | 'sql';
  custom_sql?: string;
}

export interface UpdateDimensionRequest {
  name?: string;
  source_table?: string;
  target_table?: string;
  primary_key?: string;
  surrogate_key?: string;
  attributes?: string[];
  hierarchies?: any[];
  mode?: 'visual' | 'yaml' | 'sql';
  custom_sql?: string;
  status?: string;
}

export interface Fact {
  id: string;
  name: string;
  source_table: string;
  target_table: string;
  grain: string;
  dimension_links: any[];
  measures: string[];
  mode: 'visual' | 'yaml' | 'sql';
  custom_sql?: string;
  status: 'pending' | 'valid' | 'invalid' | 'running' | 'error';
  created_at: string;
  updated_at: string;
}

export interface CreateFactRequest {
  name: string;
  source_table: string;
  target_table: string;
  grain: string;
  dimension_links?: any[];
  measures?: string[];
  mode?: 'visual' | 'yaml' | 'sql';
  custom_sql?: string;
}

export interface UpdateFactRequest {
  name?: string;
  source_table?: string;
  target_table?: string;
  grain?: string;
  dimension_links?: any[];
  measures?: string[];
  mode?: 'visual' | 'yaml' | 'sql';
  custom_sql?: string;
  status?: string;
}

export interface Metric {
  id: string;
  name: string;
  label: string;
  description?: string;
  fact_table: string;
  aggregation: 'sum' | 'count' | 'avg' | 'min' | 'max' | 'count_distinct';
  column_name?: string;
  custom_sql?: string;
  filters?: any[];
  format?: {
    type?: 'number' | 'currency' | 'percent';
    decimals?: number;
    prefix?: string;
    suffix?: string;
  };
  status: 'pending' | 'valid' | 'invalid';
  created_at: string;
  updated_at: string;
}

export interface CreateMetricRequest {
  name: string;
  label: string;
  description?: string;
  fact_table: string;
  aggregation: 'sum' | 'count' | 'avg' | 'min' | 'max' | 'count_distinct';
  column_name?: string;
  custom_sql?: string;
  filters?: any[];
  format?: {
    type?: 'number' | 'currency' | 'percent';
    decimals?: number;
    prefix?: string;
    suffix?: string;
  };
}

export interface UpdateMetricRequest {
  name?: string;
  label?: string;
  description?: string;
  fact_table?: string;
  aggregation?: 'sum' | 'count' | 'avg' | 'min' | 'max' | 'count_distinct';
  column_name?: string;
  custom_sql?: string;
  filters?: any[];
  format?: {
    type?: 'number' | 'currency' | 'percent';
    decimals?: number;
    prefix?: string;
    suffix?: string;
  };
  status?: string;
}

export interface MetricQueryResponse {
  value: any;
  formatted_value: string;
}

export interface Dashboard {
  id: string;
  name: string;
  title: string;
  description?: string;
  filters?: any[];
  layout: any[];
  refresh_interval?: number;
  status: 'pending' | 'valid' | 'invalid';
  created_at: string;
  updated_at: string;
}

export interface CreateDashboardRequest {
  name: string;
  title: string;
  description?: string;
  filters?: any[];
  layout?: any[];
  refresh_interval?: number;
}

export interface UpdateDashboardRequest {
  name?: string;
  title?: string;
  description?: string;
  filters?: any[];
  layout?: any[];
  refresh_interval?: number;
  status?: string;
}

export interface CatalogTable {
  name: string;
  type: 'raw' | 'staging' | 'dimension' | 'fact' | 'other';
  rows: number;
  columns: number;
}

export interface CatalogTableInfo {
  name: string;
  type: string;
  columns: {
    name: string;
    type: string;
    nullable: boolean;
    default?: string;
    comment?: string;
  }[];
  row_count: number;
}

export interface ExecutionLog {
  id: string;
  execution_id: string;
  resource_type: string;
  resource_id: string;
  resource_name: string;
  status: 'running' | 'success' | 'error' | 'skipped';
  started_at: string;
  finished_at?: string;
  duration_ms?: number;
  rows_affected?: number;
  error_message?: string;
  sql_executed?: string;
  created_at: string;
}
