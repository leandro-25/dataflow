from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# Ingestion Schemas - Simplified to accept generic Dict/Any types
class IngestionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    source_id: str
    config: Dict[str, Any] = Field(default_factory=dict)  # mode, table/query, target_table
    
    # Scheduling
    schedule: Optional[str] = None
    schedule_enabled: Optional[bool] = False
    schedule_timezone: Optional[str] = "America/Sao_Paulo"
    
    # Column mapping and transformations - simplified to accept any dict structure
    column_mapping: Optional[Dict[str, Any]] = Field(default_factory=dict)
    filters: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    selected_columns: Optional[List[str]] = Field(default_factory=list)
    
    # Incremental loading - simplified to accept any dict structure
    incremental_config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    # Advanced options - simplified to accept any dict structure
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
    
    # Column mapping and transformations - simplified
    column_mapping: Optional[Dict[str, Any]] = None
    filters: Optional[List[Dict[str, Any]]] = None
    selected_columns: Optional[List[str]] = None
    
    # Incremental loading - simplified
    incremental_config: Optional[Dict[str, Any]] = None
    
    # Advanced options - simplified
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


class IngestionStats(BaseModel):
    total_ingestions: int
    running: int
    error: int
    valid: int
    total_rows_ingested: int
    today_runs: int
