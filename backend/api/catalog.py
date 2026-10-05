import math
import re
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_duckdb


def _sanitize(records):
    if isinstance(records, list):
        return [_sanitize(r) for r in records]
    if isinstance(records, dict):
        return {k: _sanitize(v) for k, v in records.items()}
    if isinstance(records, float) and (math.isnan(records) or math.isinf(records)):
        return None
    return records


router = APIRouter(prefix="/api/catalog", tags=["catalog"])

_NOME_TABELA_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _exigir_nome_valido(table_name: str):
    if not _NOME_TABELA_RE.match(table_name or ""):
        raise HTTPException(status_code=400, detail="Nome de tabela invalido")


def _validar_select(sql: str) -> str:
    """Garante que apenas uma unica statement SELECT/WITH seja executada"""
    limpo = (sql or "").strip().rstrip(";").strip()
    if not limpo:
        raise HTTPException(status_code=400, detail="Query vazia")
    primeira_palavra = limpo.split(None, 1)[0].upper()
    if primeira_palavra not in ("SELECT", "WITH"):
        raise HTTPException(status_code=400, detail="Apenas queries SELECT sao permitidas")
    if ";" in limpo:
        raise HTTPException(status_code=400, detail="Multiplas statements nao sao permitidas")
    return limpo


def get_table_type(table_name: str) -> str:
    """Determina o tipo da tabela baseado no prefixo"""
    if table_name.startswith('raw_'):
        return 'raw'
    elif table_name.startswith('stg_'):
        return 'staging'
    elif table_name.startswith('dim_'):
        return 'dimension'
    elif table_name.startswith('fato_'):
        return 'fact'
    else:
        return 'other'

@router.get("/tables")
def list_tables():
    """Lista todas as tabelas no warehouse"""
    try:
        duckdb_conn = get_duckdb()
        result = duckdb_conn.execute("SHOW TABLES").fetchall()
        
        tables = []
        for row in result:
            table_name = row[0]
            
            # Get row count
            count_result = duckdb_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            row_count = count_result[0] if count_result else 0
            
            # Get column count
            schema_result = duckdb_conn.execute(f"DESCRIBE {table_name}").fetchall()
            column_count = len(schema_result)
            
            tables.append({
                "name": table_name,
                "type": get_table_type(table_name),
                "rows": row_count,
                "columns": column_count
            })
        
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/tables/{table_name}")
def delete_table(table_name: str):
    """Remove uma tabela do warehouse"""
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table_name):
        raise HTTPException(status_code=400, detail="Nome de tabela invalido")

    try:
        duckdb_conn = get_duckdb()
        obj = duckdb_conn.execute(
            "SELECT table_type FROM information_schema.tables WHERE table_name = ?", [table_name]
        ).fetchone()
        if not obj:
            raise HTTPException(status_code=404, detail=f"Tabela nao encontrada: {table_name}")

        if obj[0] == "VIEW":
            duckdb_conn.execute(f'DROP VIEW "{table_name}"')
        else:
            duckdb_conn.execute(f'DROP TABLE "{table_name}"')
        return {"message": f"Tabela {table_name} removida", "deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tables/{table_name}")
def get_table_info(table_name: str):
    """Retorna informações de uma tabela"""
    _exigir_nome_valido(table_name)
    try:
        duckdb_conn = get_duckdb()
        
        # Get schema
        schema_result = duckdb_conn.execute(f"DESCRIBE {table_name}").fetchall()
        columns = []
        for row in schema_result:
            columns.append({
                "name": row[0],
                "type": row[1],
                "nullable": row[2] == 'YES' if len(row) > 2 else True
            })
        
        # Get row count
        count_result = duckdb_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        row_count = count_result[0] if count_result else 0
        
        return {
            "name": table_name,
            "type": get_table_type(table_name),
            "columns": columns,
            "row_count": row_count
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tables/{table_name}/data")
def get_table_data(
    table_name: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Retorna dados de uma tabela com paginação"""
    _exigir_nome_valido(table_name)
    try:
        duckdb_conn = get_duckdb()
        
        # Get total count
        count_result = duckdb_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        total = count_result[0] if count_result else 0
        
        # Get data
        result = duckdb_conn.execute(f"SELECT * FROM {table_name} LIMIT {limit} OFFSET {offset}").fetchdf()
        
        return {
            "columns": result.columns.tolist(),
            "data": _sanitize(result.to_dict('records')),
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tables/{table_name}/schema")
def get_table_schema(table_name: str):
    """Retorna schema de uma tabela"""
    _exigir_nome_valido(table_name)
    try:
        duckdb_conn = get_duckdb()
        result = duckdb_conn.execute(f"DESCRIBE {table_name}").fetchall()
        
        columns = []
        for row in result:
            columns.append({
                "name": row[0],
                "type": row[1],
                "nullable": row[2] == 'YES' if len(row) > 2 else True,
                "default": row[3] if len(row) > 3 else None,
                "comment": row[4] if len(row) > 4 else None
            })
        
        return {"schema": columns}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/query")
def execute_query(query: dict):
    """Executa uma query SQL (apenas SELECT permitido)"""
    try:
        sql = _validar_select(query.get('sql', ''))

        duckdb_conn = get_duckdb()
        result = duckdb_conn.execute(sql).fetchdf()
        
        # Limit results
        if len(result) > 1000:
            result = result.head(1000)
        
        return {
            "columns": result.columns.tolist(),
            "data": _sanitize(result.to_dict('records')),
            "row_count": len(result)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
