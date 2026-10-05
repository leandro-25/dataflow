import uuid
import re
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from database import get_db, get_duckdb
import models
import schemas

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


def _build_where(filters: Optional[List[dict]]) -> str:
    if not filters:
        return ""
    clauses = []
    for f in filters:
        col = f.get("column", "")
        op = f.get("operator", "=").upper()
        val = f.get("value")
        if not col:
            continue
        if op in ("IS NULL", "IS NOT NULL"):
            clauses.append(f"{col} {op}")
        elif op in ("IN", "NOT IN"):
            if isinstance(val, list):
                items = ", ".join(f"'{v}'" if isinstance(v, str) else str(v) for v in val)
                clauses.append(f"{col} {op} ({items})")
            else:
                clauses.append(f"{col} {op} ('{val}')")
        elif op == "LIKE":
            clauses.append(f"{col} LIKE '{val}'")
        elif op in (">", "<", ">=", "<="):
            if isinstance(val, str):
                clauses.append(f"CAST({col} AS DOUBLE) {op} '{val}'")
            else:
                clauses.append(f"CAST({col} AS DOUBLE) {op} {val}")
        else:
            if isinstance(val, str):
                clauses.append(f"{col} {op} '{val}'")
            else:
                clauses.append(f"{col} {op} {val}")
    return " WHERE " + " AND ".join(clauses)


def _merge_filters(metric_filters: Optional[list], query_filters: Optional[list]) -> list:
    """Mescla filtros salvos com os da consulta. Filtros enviados na query
    tem prioridade sobre os salvos na metrica para a mesma coluna."""
    merged = []
    seen_cols = set()
    for src in (query_filters, metric_filters):
        if not src:
            continue
        for f in src:
            col = f.get("column", "")
            if col and col in seen_cols:
                continue
            if col:
                seen_cols.add(col)
            merged.append(f)
    return merged

@router.get("", response_model=List[schemas.MetricResponse])
def list_metrics(db: Session = Depends(get_db)):
    return db.query(models.Metric).all()

@router.post("", response_model=schemas.MetricResponse)
def create_metric(metric: schemas.MetricCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Metric).filter(models.Metric.name == metric.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Metric name already exists")
    
    db_metric = models.Metric(
        id=str(uuid.uuid4()),
        name=metric.name,
        label=metric.label,
        description=metric.description,
        fact_table=metric.fact_table,
        aggregation=metric.aggregation,
        column_name=metric.column_name,
        custom_sql=metric.custom_sql,
        filters=metric.filters,
        format=metric.format,
        status=metric.status
    )
    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)
    return db_metric

@router.get("/{metric_id}", response_model=schemas.MetricResponse)
def get_metric(metric_id: str, db: Session = Depends(get_db)):
    metric = db.query(models.Metric).filter(models.Metric.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    return metric

@router.put("/{metric_id}", response_model=schemas.MetricResponse)
def update_metric(metric_id: str, metric_update: schemas.MetricUpdate, db: Session = Depends(get_db)):
    metric = db.query(models.Metric).filter(models.Metric.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    
    if metric_update.name and metric_update.name != metric.name:
        existing = db.query(models.Metric).filter(models.Metric.name == metric_update.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Metric name already exists")
    
    update_data = metric_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(metric, field, value)
    
    db.commit()
    db.refresh(metric)
    return metric

@router.delete("/{metric_id}")
def delete_metric(metric_id: str, db: Session = Depends(get_db)):
    metric = db.query(models.Metric).filter(models.Metric.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    
    db.delete(metric)
    db.commit()
    return {"message": "Metric deleted successfully"}

@router.post("/{metric_id}/query")
def query_metric(metric_id: str, body: dict = Body({}), db: Session = Depends(get_db)):
    metric = db.query(models.Metric).filter(models.Metric.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    
    try:
        duckdb_conn = get_duckdb()
        
        # Merge metric-level filters with query-time filters
        req_filters = body.get("filters") if body else None
        all_filters = _merge_filters(metric.filters, req_filters)
        where_clause = _build_where(all_filters)
        
        # Build aggregation SQL
        if metric.custom_sql:
            sql = metric.custom_sql
            if where_clause:
                if re.search(r'\bWHERE\b', sql, re.IGNORECASE):
                    sql += " AND " + where_clause.replace("WHERE ", "", 1)
                else:
                    sql += where_clause
        else:
            agg_func = metric.aggregation.upper()
            column = metric.column_name or '*'
            if agg_func == 'COUNT_DISTINCT':
                agg_func = 'COUNT(DISTINCT'
                sql = f"SELECT {agg_func} {column}) as value FROM {metric.fact_table}{where_clause}"
            else:
                sql = f"SELECT {agg_func}({column}) as value FROM {metric.fact_table}{where_clause}"
        
        result = duckdb_conn.execute(sql).fetchone()
        value = result[0] if result else 0
        
        # Format value
        formatted = str(value)
        if metric.format:
            if metric.format.get('type') == 'currency':
                formatted = f"R$ {float(value):,.2f}"
            elif metric.format.get('type') == 'percent':
                formatted = f"{float(value) * 100:.1f}%"
            elif metric.format.get('decimals'):
                formatted = f"{float(value):,.{metric.format['decimals']}f}"
        
        return {"value": value, "formatted_value": formatted}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
