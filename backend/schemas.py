from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# Source Schemas
class SourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    type: str
    config: Dict[str, Any]
    status: Optional[str] = "valid"


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class SourceResponse(SourceBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SourceTestConnection(BaseModel):
    success: bool
    message: str
    tables: Optional[List[str]] = None


# Ingestion Schemas - ATUALIZADO para suportar todos os campos do frontend
class IngestionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    source_id: str
    config: Dict[str, Any] = Field(default_factory=dict)
    
    # Scheduling
    schedule: Optional[str] = None
    schedule_enabled: Optional[bool] = False
    schedule_timezone: Optional[str] = "America/Sao_Paulo"
    
    # Column mapping and transformations - aceita qualquer estrutura
    column_mapping: Optional[Dict[str, Any]] = Field(default_factory=dict)
    filters: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    selected_columns: Optional[List[str]] = Field(default_factory=list)
    
    # Incremental loading - aceita qualquer estrutura
    incremental_config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    # Advanced options - aceita qualquer estrutura
    advanced_options: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    # Metadata
    tags: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = None
    is_favorite: Optional[bool] = False
    
    status: Optional[str] = "pending"


class IngestionCreate(IngestionBase):
    pass


class IngestionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    source_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    
    # Scheduling
    schedule: Optional[str] = None
    schedule_enabled: Optional[bool] = None
    schedule_timezone: Optional[str] = None
    
    # Column mapping and transformations
    column_mapping: Optional[Dict[str, Any]] = None
    filters: Optional[List[Dict[str, Any]]] = None
    selected_columns: Optional[List[str]] = None
    
    # Incremental loading
    incremental_config: Optional[Dict[str, Any]] = None
    
    # Advanced options
    advanced_options: Optional[Dict[str, Any]] = None
    
    # Metadata
    tags: Optional[List[str]] = None
    description: Optional[str] = None
    is_favorite: Optional[bool] = None
    
    status: Optional[str] = None


class IngestionResponse(BaseModel):
    id: str
    name: str
    source_id: str
    config: Dict[str, Any]
    
    # Scheduling
    schedule: Optional[str] = None
    schedule_enabled: Optional[bool] = False
    schedule_timezone: Optional[str] = "America/Sao_Paulo"
    
    # Column mapping and transformations
    column_mapping: Optional[Dict[str, Any]] = None
    filters: Optional[List[Dict[str, Any]]] = None
    selected_columns: Optional[List[str]] = None
    
    # Incremental loading
    incremental_config: Optional[Dict[str, Any]] = None
    
    # Advanced options
    advanced_options: Optional[Dict[str, Any]] = None
    
    # Metadata
    tags: Optional[List[str]] = None
    description: Optional[str] = None
    is_favorite: Optional[bool] = False
    
    # Validation
    status: str
    validation_status: Optional[str] = None
    validation_message: Optional[str] = None
    
    # Execution metrics
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_run_rows: Optional[int] = None
    last_run_duration_ms: Optional[int] = None
    last_run_error: Optional[str] = None
    
    total_runs: Optional[int] = 0
    total_rows_ingested: Optional[int] = 0
    avg_rows_per_run: Optional[int] = None
    avg_duration_ms: Optional[int] = None
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PreviewResponse(BaseModel):
    columns: List[str]
    data: List[Dict[str, Any]]
    total_rows: int
    dtypes: Optional[Dict[str, str]] = None
    null_counts: Optional[Dict[str, int]] = None


class ValidationResponse(BaseModel):
    valid: bool
    status: str
    message: str
    warnings: List[str]
    errors: List[str]


class MetadataResponse(BaseModel):
    source_type: str
    source_name: str
    schema: List[Dict[str, Any]]
    tables: Optional[List[str]] = None
    estimated_rows: Optional[str] = None
    file_info: Optional[Dict[str, Any]] = None


# Staging Schemas
class StagingBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    source_table: str
    target_table: str
    transforms: List[Dict[str, Any]] = Field(default_factory=list)
    mode: str = "visual"  # visual, yaml, sql
    custom_sql: Optional[str] = None
    status: Optional[str] = "pending"


class StagingCreate(StagingBase):
    pass


class StagingUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    source_table: Optional[str] = None
    target_table: Optional[str] = None
    transforms: Optional[List[Dict[str, Any]]] = None
    mode: Optional[str] = None
    custom_sql: Optional[str] = None
    status: Optional[str] = None


class StagingResponse(StagingBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TransformType(BaseModel):
    type: str
    label: str
    description: str
    config_schema: Dict[str, Any]


# Dimension Schemas
class DimensionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    source_table: str
    target_table: str
    primary_key: str
    surrogate_key: Optional[str] = None
    attributes: List[str] = Field(default_factory=list)
    hierarchies: Optional[List[Dict[str, Any]]] = None
    mode: str = "visual"
    custom_sql: Optional[str] = None
    status: Optional[str] = "pending"


class DimensionCreate(DimensionBase):
    pass


class DimensionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    source_table: Optional[str] = None
    target_table: Optional[str] = None
    primary_key: Optional[str] = None
    surrogate_key: Optional[str] = None
    attributes: Optional[List[str]] = None
    hierarchies: Optional[List[Dict[str, Any]]] = None
    mode: Optional[str] = None
    custom_sql: Optional[str] = None
    status: Optional[str] = None


class DimensionResponse(DimensionBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Fact Schemas
class FactBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    source_table: str
    target_table: str
    grain: str
    dimension_links: List[Dict[str, Any]] = Field(default_factory=list)
    measures: List[str] = Field(default_factory=list)
    mode: str = "visual"
    custom_sql: Optional[str] = None
    status: Optional[str] = "pending"


class FactCreate(FactBase):
    pass


class FactUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    source_table: Optional[str] = None
    target_table: Optional[str] = None
    grain: Optional[str] = None
    dimension_links: Optional[List[Dict[str, Any]]] = None
    measures: Optional[List[str]] = None
    mode: Optional[str] = None
    custom_sql: Optional[str] = None
    status: Optional[str] = None


class FactResponse(FactBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Metric Schemas
class MetricBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    label: str
    description: Optional[str] = None
    fact_table: str
    aggregation: str = Field(..., pattern=r"^(sum|count|avg|min|max|count_distinct)$")
    column_name: Optional[str] = None
    custom_sql: Optional[str] = None
    filters: Optional[List[Dict[str, Any]]] = None
    format: Optional[Dict[str, Any]] = None
    status: Optional[str] = "pending"


class MetricCreate(MetricBase):
    pass


class MetricUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    label: Optional[str] = None
    description: Optional[str] = None
    fact_table: Optional[str] = None
    aggregation: Optional[str] = None
    column_name: Optional[str] = None
    custom_sql: Optional[str] = None
    filters: Optional[List[Dict[str, Any]]] = None
    format: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class MetricResponse(MetricBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MetricQueryRequest(BaseModel):
    filters: Optional[List[Dict[str, Any]]] = None


class MetricQueryResponse(BaseModel):
    value: Any
    formatted_value: str


# Dashboard Schemas
class DashboardBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    title: str
    description: Optional[str] = None
    filters: Optional[List[Dict[str, Any]]] = None
    layout: List[Dict[str, Any]] = Field(default_factory=list)
    refresh_interval: Optional[int] = None
    status: Optional[str] = "pending"


class DashboardCreate(DashboardBase):
    pass


class DashboardUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    title: Optional[str] = None
    description: Optional[str] = None
    filters: Optional[List[Dict[str, Any]]] = None
    layout: Optional[List[Dict[str, Any]]] = None
    refresh_interval: Optional[int] = None
    status: Optional[str] = None


class DashboardResponse(DashboardBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DashboardDataResponse(BaseModel):
    components: List[Dict[str, Any]]
