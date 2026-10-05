from sqlalchemy import Column, String, DateTime, Integer, Text, JSON, UniqueConstraint, Boolean
from sqlalchemy.sql import func
from database import Base


class Source(Base):
    __tablename__ = "sources"
    
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    type = Column(String, nullable=False)  # postgres, mysql, csv, excel, rest_api, google_sheets, json, xml, parquet, avro, orc, sql_file, delta_lake
    config = Column(JSON, nullable=False, default={})
    status = Column(String, default="valid")  # valid, invalid
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Ingestion(Base):
    __tablename__ = "ingestions"
    
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    source_id = Column(String, nullable=False)
    
    # Configuração básica
    config = Column(JSON, default={})  # modo, query/tabela, tabela destino
    
    # Agendamento
    schedule = Column(String, nullable=True)  # expressão cron
    schedule_enabled = Column(Boolean, default=False)
    schedule_timezone = Column(String, default="America/Sao_Paulo")
    
    # Mapeamento de colunas e tipos
    column_mapping = Column(JSON, default={})  # {source_col: {target_name, target_type, nullable, default_value}}
    
    # Filtros e transformações
    filters = Column(JSON, default=[])  # [{column, operator, value}]
    selected_columns = Column(JSON, default=[])  # colunas a importar (vazio = todas)
    
    # Configuração incremental
    incremental_config = Column(JSON, default={})  # {enabled, control_column, last_value}
    
    # Configurações avançadas por tipo
    advanced_options = Column(JSON, default={})  # batch_size, encoding, delimiter, etc
    
    # Metadados e tags
    tags = Column(JSON, default=[])  # categorização
    description = Column(Text, nullable=True)
    is_favorite = Column(Boolean, default=False)
    
    # Status e execução
    status = Column(String, default="pending")  # pending, valid, invalid, running, error
    validation_status = Column(String, nullable=True)  # success, warning, error
    validation_message = Column(Text, nullable=True)
    
    # Progresso em tempo real (para arquivos grandes)
    current_execution_id = Column(String, nullable=True)  # ID da execução atual
    progress_percent = Column(Integer, nullable=True)  # 0-100
    progress_rows_processed = Column(Integer, nullable=True)
    progress_rows_total = Column(Integer, nullable=True)
    progress_stage = Column(String, nullable=True)  # connecting, reading, transforming, writing, complete
    progress_speed_rows_per_sec = Column(Integer, nullable=True)
    progress_eta_seconds = Column(Integer, nullable=True)
    
    # Métricas de execução
    last_run_at = Column(DateTime, nullable=True)
    last_run_status = Column(String, nullable=True)
    last_run_rows = Column(Integer, nullable=True)
    last_run_duration_ms = Column(Integer, nullable=True)
    last_run_error = Column(Text, nullable=True)
    
    # Estatísticas agregadas
    total_runs = Column(Integer, default=0)
    total_rows_ingested = Column(Integer, default=0)
    avg_rows_per_run = Column(Integer, nullable=True)
    avg_duration_ms = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Staging(Base):
    __tablename__ = "stagings"
    
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    source_table = Column(String, nullable=False)
    target_table = Column(String, nullable=False)
    transforms = Column(JSON, default=[])
    mode = Column(String, default="visual")  # visual, yaml, sql
    custom_sql = Column(Text, nullable=True)
    schedule = Column(String, nullable=True)
    schedule_enabled = Column(Boolean, default=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Dimension(Base):
    __tablename__ = "dimensions"
    
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    source_table = Column(String, nullable=False)
    target_table = Column(String, nullable=False)
    primary_key = Column(String, nullable=False)
    surrogate_key = Column(String, nullable=True)
    attributes = Column(JSON, default=[])
    hierarchies = Column(JSON, nullable=True)
    mode = Column(String, default="visual")
    custom_sql = Column(Text, nullable=True)
    schedule = Column(String, nullable=True)
    schedule_enabled = Column(Boolean, default=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Fact(Base):
    __tablename__ = "facts"
    
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    source_table = Column(String, nullable=False)
    target_table = Column(String, nullable=False)
    grain = Column(String, nullable=False)
    dimension_links = Column(JSON, default=[])
    measures = Column(JSON, default=[])
    mode = Column(String, default="visual")
    custom_sql = Column(Text, nullable=True)
    schedule = Column(String, nullable=True)
    schedule_enabled = Column(Boolean, default=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Metric(Base):
    __tablename__ = "metrics"
    
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    label = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    fact_table = Column(String, nullable=False)
    aggregation = Column(String, nullable=False)  # sum, count, avg, min, max, count_distinct
    column_name = Column(String, nullable=True)
    custom_sql = Column(Text, nullable=True)
    filters = Column(JSON, nullable=True)
    format = Column(JSON, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Dashboard(Base):
    __tablename__ = "dashboards"
    
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    filters = Column(JSON, nullable=True)
    layout = Column(JSON, nullable=False, default={})
    refresh_interval = Column(Integer, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ExecutionLog(Base):
    __tablename__ = "execution_logs"
    
    id = Column(String, primary_key=True)
    execution_id = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)  # ingestion, staging, dimension, fact
    resource_id = Column(String, nullable=False)
    resource_name = Column(String, nullable=False)
    status = Column(String, nullable=False)  # running, success, error, skipped
    started_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    rows_affected = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    sql_executed = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Dependency(Base):
    __tablename__ = "dependencies"
    
    id = Column(String, primary_key=True)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=False)
    depends_on_type = Column(String, nullable=False)
    depends_on_id = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('resource_type', 'resource_id', 'depends_on_type', 'depends_on_id', name='uix_dependency'),
    )


class ExecutionProgress(Base):
    """Real-time execution progress tracking for large file processing"""
    __tablename__ = "execution_progress"
    
    id = Column(String, primary_key=True)
    execution_id = Column(String, nullable=False, index=True)
    resource_id = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    
    # Progress data
    percent_complete = Column(Integer, default=0)  # 0-100
    rows_processed = Column(Integer, default=0)
    rows_total = Column(Integer, nullable=True)
    stage = Column(String, default="connecting")  # connecting, reading, transforming, writing, complete
    speed_rows_per_second = Column(Integer, nullable=True)
    eta_seconds = Column(Integer, nullable=True)
    
    # Batch info for large files
    current_batch = Column(Integer, default=0)
    total_batches = Column(Integer, nullable=True)
    batch_size = Column(Integer, nullable=True)
    
    # Status
    status = Column(String, default="running")  # running, paused, completed, error
    message = Column(Text, nullable=True)  # Current operation description
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('execution_id', name='uix_execution_progress'),
    )


class IngestionOrder(Base):
    """Custom ordering for drag & drop functionality"""
    __tablename__ = "ingestion_orders"
    
    id = Column(String, primary_key=True)
    ingestion_id = Column(String, nullable=False, unique=True)
    user_id = Column(String, default="default")  # For multi-user support in future
    sort_order = Column(Integer, default=0)  # Display order
    folder = Column(String, nullable=True)  # For grouping/folders
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class KeyboardShortcut(Base):
    """User-defined keyboard shortcuts"""
    __tablename__ = "keyboard_shortcuts"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, default="default")
    shortcut_key = Column(String, nullable=False)  # e.g., "ctrl+n"
    action = Column(String, nullable=False)  # e.g., "create_ingestion", "run_all"
    description = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
