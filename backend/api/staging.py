import uuid
import math
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, get_duckdb
import models
import schemas
from engine.transform_generator import TransformGenerator


def _sanitize(records):
    if isinstance(records, list):
        return [_sanitize(r) for r in records]
    if isinstance(records, dict):
        return {k: _sanitize(v) for k, v in records.items()}
    if isinstance(records, float) and (math.isnan(records) or math.isinf(records)):
        return None
    return records


router = APIRouter(prefix="/api/staging", tags=["staging"])

# Lista de tipos de transformações disponíveis
TRANSFORM_TYPES = [
    {
        "type": "rename",
        "label": "Renomear Colunas",
        "description": "Renomeia colunas existentes",
        "config_schema": {"type": "object", "additionalProperties": {"type": "string"}}
    },
    {
        "type": "cast",
        "label": "Converter Tipos",
        "description": "Converte tipos de dados das colunas",
        "config_schema": {"type": "object", "additionalProperties": {"type": "string", "enum": ["text", "integer", "decimal", "date", "timestamp", "boolean"]}}
    },
    {
        "type": "filter",
        "label": "Filtrar Linhas",
        "description": "Filtra linhas baseado em condições",
        "config_schema": {
            "type": "object",
            "properties": {
                "column": {"type": "string"},
                "operator": {"type": "string", "enum": ["=", "!=", ">", "<", ">=", "<=", "in", "not_in", "is_null", "is_not_null", "contains"]},
                "value": {}
            },
            "required": ["column", "operator"]
        }
    },
    {
        "type": "deduplicate",
        "label": "Remover Duplicatas",
        "description": "Remove linhas duplicadas baseado em chaves",
        "config_schema": {
            "type": "object",
            "properties": {
                "keys": {"type": "array", "items": {"type": "string"}},
                "keep": {"type": "string", "enum": ["first", "last"], "default": "first"}
            },
            "required": ["keys"]
        }
    },
    {
        "type": "fill_null",
        "label": "Preencher Nulos",
        "description": "Preenche valores nulos",
        "config_schema": {
            "type": "object",
            "properties": {
                "column": {"type": "string"},
                "value": {},
                "strategy": {"type": "string", "enum": ["forward", "backward"]}
            },
            "required": ["column"]
        }
    },
    {
        "type": "sort",
        "label": "Ordenar",
        "description": "Ordena as linhas",
        "config_schema": {
            "type": "object",
            "properties": {
                "column": {"type": "string"},
                "order": {"type": "string", "enum": ["asc", "desc"], "default": "asc"}
            },
            "required": ["column"]
        }
    },
    {
        "type": "limit",
        "label": "Limitar Linhas",
        "description": "Limita número de linhas",
        "config_schema": {
            "type": "object",
            "properties": {
                "rows": {"type": "integer", "minimum": 1}
            },
            "required": ["rows"]
        }
    },
    {
        "type": "add_column",
        "label": "Adicionar Coluna",
        "description": "Adiciona coluna calculada",
        "config_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "expression": {"type": "string"}
            },
            "required": ["name", "expression"]
        }
    },
    {
        "type": "remove_columns",
        "label": "Remover Colunas",
        "description": "Remove colunas selecionadas",
        "config_schema": {
            "type": "object",
            "properties": {
                "columns": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["columns"]
        }
    },
    {
        "type": "select_columns",
        "label": "Selecionar Colunas",
        "description": "Seleciona apenas colunas específicas",
        "config_schema": {
            "type": "object",
            "properties": {
                "columns": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["columns"]
        }
    },
    {
        "type": "uppercase",
        "label": "Maiúsculas",
        "description": "Converte texto para maiúsculas",
        "config_schema": {
            "type": "object",
            "properties": {
                "columns": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["columns"]
        }
    },
    {
        "type": "lowercase",
        "label": "Minúsculas",
        "description": "Converte texto para minúsculas",
        "config_schema": {
            "type": "object",
            "properties": {
                "columns": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["columns"]
        }
    },
    {
        "type": "trim",
        "label": "Remover Espaços",
        "description": "Remove espaços do início e fim",
        "config_schema": {
            "type": "object",
            "properties": {
                "columns": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["columns"]
        }
    },
    {
        "type": "replace",
        "label": "Substituir Valores",
        "description": "Substitui valores em uma coluna",
        "config_schema": {
            "type": "object",
            "properties": {
                "column": {"type": "string"},
                "find": {"type": "string"},
                "replace": {"type": "string"}
            },
            "required": ["column", "find"]
        }
    },
    {
        "type": "split",
        "label": "Dividir Coluna",
        "description": "Divide uma coluna em múltiplas",
        "config_schema": {
            "type": "object",
            "properties": {
                "column": {"type": "string"},
                "delimiter": {"type": "string", "default": " "},
                "into": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["column", "into"]
        }
    },
    {
        "type": "merge",
        "label": "Juntar Colunas",
        "description": "Junta múltiplas colunas em uma",
        "config_schema": {
            "type": "object",
            "properties": {
                "columns": {"type": "array", "items": {"type": "string"}},
                "into": {"type": "string"},
                "separator": {"type": "string", "default": " "}
            },
            "required": ["columns", "into"]
        }
    },
    {
        "type": "custom_sql",
        "label": "SQL Customizado",
        "description": "SQL personalizado",
        "config_schema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string"}
            },
            "required": ["sql"]
        }
    },
]


@router.get("", response_model=List[schemas.StagingResponse])
def list_stagings(db: Session = Depends(get_db)):
    return db.query(models.Staging).all()


@router.post("", response_model=schemas.StagingResponse)
def create_staging(staging: schemas.StagingCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Staging).filter(models.Staging.name == staging.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Staging name already exists")
    
    db_staging = models.Staging(
        id=str(uuid.uuid4()),
        name=staging.name,
        source_table=staging.source_table,
        target_table=staging.target_table,
        transforms=staging.transforms,
        mode=staging.mode,
        custom_sql=staging.custom_sql,
        status=staging.status
    )
    db.add(db_staging)
    db.commit()
    db.refresh(db_staging)
    return db_staging


@router.get("/{staging_id}", response_model=schemas.StagingResponse)
def get_staging(staging_id: str, db: Session = Depends(get_db)):
    staging = db.query(models.Staging).filter(models.Staging.id == staging_id).first()
    if not staging:
        raise HTTPException(status_code=404, detail="Staging not found")
    return staging


@router.put("/{staging_id}", response_model=schemas.StagingResponse)
def update_staging(staging_id: str, staging_update: schemas.StagingUpdate, db: Session = Depends(get_db)):
    staging = db.query(models.Staging).filter(models.Staging.id == staging_id).first()
    if not staging:
        raise HTTPException(status_code=404, detail="Staging not found")
    
    if staging_update.name and staging_update.name != staging.name:
        existing = db.query(models.Staging).filter(models.Staging.name == staging_update.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Staging name already exists")
    
    update_data = staging_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(staging, field, value)
    
    db.commit()
    db.refresh(staging)
    return staging


@router.delete("/{staging_id}")
def delete_staging(staging_id: str, db: Session = Depends(get_db)):
    staging = db.query(models.Staging).filter(models.Staging.id == staging_id).first()
    if not staging:
        raise HTTPException(status_code=404, detail="Staging not found")
    
    db.delete(staging)
    db.commit()
    return {"message": "Staging deleted successfully"}


@router.get("/transforms/types")
def list_transform_types():
    return TRANSFORM_TYPES


@router.post("/dry-run")
def dry_run_staging(payload: dict, db: Session = Depends(get_db)):
    """Amostra antes/depois das transformacoes SEM criar tabela alguma."""
    import re as _re
    source_table = payload.get("source_table", "")
    transforms = payload.get("transforms") or []
    mode = payload.get("mode", "visual")
    custom_sql = payload.get("custom_sql")
    try:
        limit = max(1, min(int(payload.get("limit", 20)), 1000))
    except (TypeError, ValueError):
        limit = 20

    if not _re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", source_table or ""):
        raise HTTPException(status_code=400, detail="Tabela de origem invalida")

    duckdb_conn = get_duckdb()
    try:
        origem_total = duckdb_conn.execute(f"SELECT COUNT(*) FROM {source_table}").fetchone()[0]

        if mode == "sql" and custom_sql:
            inner = custom_sql.replace("_input", source_table)
            exec_sql = f"SELECT * FROM ({inner}) LIMIT {limit}"
        else:
            gerador = TransformGenerator(duckdb_conn)
            sql_core = gerador.generate_sql(source_table, "_dryrun", transforms)
            exec_sql = sql_core.replace("CREATE OR REPLACE TABLE _dryrun AS", "SELECT * FROM (")
            exec_sql = exec_sql + f") LIMIT {limit}"

        resultado = duckdb_conn.execute(exec_sql).fetchdf()
        sql_visivel = exec_sql if mode != "sql" else f"SELECT * FROM ({inner}) LIMIT {limit}"

        return {
            "columns": resultado.columns.tolist(),
            "data": _sanitize(resultado.to_dict("records")),
            "total_rows": len(resultado),
            "source_total_rows": origem_total,
            "sql": sql_visivel,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{staging_id}/preview")
def preview_staging(staging_id: str, db: Session = Depends(get_db)):
    staging = db.query(models.Staging).filter(models.Staging.id == staging_id).first()
    if not staging:
        raise HTTPException(status_code=404, detail="Staging not found")
    
    try:
        duckdb_conn = get_duckdb()
        
        if staging.mode == 'sql' and staging.custom_sql:
            # Use custom SQL
            sql = staging.custom_sql.replace('_input', staging.source_table)
            sql = f"SELECT * FROM ({sql}) LIMIT 10"
        else:
            # Generate SQL from transforms
            generator = TransformGenerator(duckdb_conn)
            sql = generator.generate_sql(staging.source_table, "_preview", staging.transforms)
            sql = sql.replace(f"CREATE OR REPLACE TABLE _preview AS", "SELECT * FROM (")
            sql = sql + ") LIMIT 10"
        
        result = duckdb_conn.execute(sql).fetchdf()
        
        return {
            "columns": result.columns.tolist(),
            "data": _sanitize(result.to_dict('records')),
            "total_rows": len(result)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{staging_id}/run")
def run_staging(staging_id: str, db: Session = Depends(get_db)):
    staging = db.query(models.Staging).filter(models.Staging.id == staging_id).first()
    if not staging:
        raise HTTPException(status_code=404, detail="Staging not found")
    
    try:
        staging.status = "running"
        db.commit()
        
        duckdb_conn = get_duckdb()
        
        if staging.mode == 'sql' and staging.custom_sql:
            sql = staging.custom_sql.replace('_input', staging.source_table)
            duckdb_conn.execute(f"CREATE OR REPLACE TABLE {staging.target_table} AS {sql}")
        else:
            generator = TransformGenerator(duckdb_conn)
            sql = generator.generate_sql(staging.source_table, staging.target_table, staging.transforms)
            duckdb_conn.execute(sql)
        
        result = duckdb_conn.execute(f"SELECT COUNT(*) FROM {staging.target_table}").fetchone()
        rows_affected = result[0] if result else 0
        
        staging.status = "valid"
        db.commit()
        
        return {
            "success": True,
            "message": "Staging completed successfully",
            "rows_affected": rows_affected,
            "target_table": staging.target_table
        }
    except Exception as e:
        staging.status = "error"
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))
