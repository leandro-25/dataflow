import uuid
import math
import time
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, get_duckdb
import models
import schemas


def _sanitize(records):
    if isinstance(records, list):
        return [_sanitize(r) for r in records]
    if isinstance(records, dict):
        return {k: _sanitize(v) for k, v in records.items()}
    if isinstance(records, float) and (math.isnan(records) or math.isinf(records)):
        return None
    return records


router = APIRouter(prefix="/api/facts", tags=["facts"])

@router.get("", response_model=List[schemas.FactResponse])
def list_facts(db: Session = Depends(get_db)):
    return db.query(models.Fact).all()

@router.post("", response_model=schemas.FactResponse)
def create_fact(fact: schemas.FactCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Fact).filter(models.Fact.name == fact.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Fact name already exists")
    
    db_fact = models.Fact(
        id=str(uuid.uuid4()),
        name=fact.name,
        source_table=fact.source_table,
        target_table=fact.target_table,
        grain=fact.grain,
        dimension_links=fact.dimension_links,
        measures=fact.measures,
        mode=fact.mode,
        custom_sql=fact.custom_sql,
        status=fact.status
    )
    db.add(db_fact)
    db.commit()
    db.refresh(db_fact)
    return db_fact

@router.get("/{fact_id}", response_model=schemas.FactResponse)
def get_fact(fact_id: str, db: Session = Depends(get_db)):
    fact = db.query(models.Fact).filter(models.Fact.id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    return fact

@router.put("/{fact_id}", response_model=schemas.FactResponse)
def update_fact(fact_id: str, fact_update: schemas.FactUpdate, db: Session = Depends(get_db)):
    fact = db.query(models.Fact).filter(models.Fact.id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    
    if fact_update.name and fact_update.name != fact.name:
        existing = db.query(models.Fact).filter(models.Fact.name == fact_update.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Fact name already exists")
    
    update_data = fact_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(fact, field, value)
    
    db.commit()
    db.refresh(fact)
    return fact

@router.delete("/{fact_id}")
def delete_fact(fact_id: str, db: Session = Depends(get_db)):
    fact = db.query(models.Fact).filter(models.Fact.id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    
    db.delete(fact)
    db.commit()
    return {"message": "Fact deleted successfully"}

@router.post("/{fact_id}/preview")
def preview_fact(fact_id: str, db: Session = Depends(get_db)):
    fact = db.query(models.Fact).filter(models.Fact.id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    
    try:
        duckdb_conn = get_duckdb()
        
        if fact.mode == 'sql' and fact.custom_sql:
            sql = fact.custom_sql.replace('_input', fact.source_table)
            sql = f"SELECT * FROM ({sql}) LIMIT 10"
        else:
            # Simplified preview
            measures = ', '.join(fact.measures) if fact.measures else '*'
            sql = f"SELECT {measures} FROM {fact.source_table} LIMIT 10"
        
        result = duckdb_conn.execute(sql).fetchdf()
        
        return {
            "columns": result.columns.tolist(),
            "data": _sanitize(result.to_dict('records')),
            "total_rows": len(result)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{fact_id}/run")
def run_fact(fact_id: str, db: Session = Depends(get_db)):
    fact = db.query(models.Fact).filter(models.Fact.id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    
    execution_id = str(uuid.uuid4())
    log = models.ExecutionLog(
        id=str(uuid.uuid4()),
        execution_id=execution_id,
        resource_type="fact",
        resource_id=fact_id,
        resource_name=fact.name,
        status="running"
    )
    db.add(log)
    db.commit()
    
    start_time = time.time()
    executed_sql = ""
    
    try:
        fact.status = "running"
        db.commit()
        
        duckdb_conn = get_duckdb()
        
        if fact.mode == 'sql' and fact.custom_sql:
            sql = fact.custom_sql.replace('_input', fact.source_table)
            executed_sql = f"CREATE OR REPLACE TABLE {fact.target_table} AS {sql}"
            duckdb_conn.execute(executed_sql)
        else:
            # Build fact table with dimension joins
            measures = ', '.join(fact.measures) if fact.measures else '*'
            executed_sql = f"CREATE OR REPLACE TABLE {fact.target_table} AS SELECT {measures} FROM {fact.source_table}"
            duckdb_conn.execute(executed_sql)
        
        result = duckdb_conn.execute(f"SELECT COUNT(*) FROM {fact.target_table}").fetchone()
        rows_affected = result[0] if result else 0
        
        fact.status = "valid"
        db.commit()
        
        duration = int((time.time() - start_time) * 1000)
        log.status = "success"
        log.finished_at = datetime.now()
        log.duration_ms = duration
        log.rows_affected = rows_affected
        log.sql_executed = executed_sql
        db.commit()
        
        return {
            "success": True,
            "message": "Fact table created successfully",
            "rows_affected": rows_affected,
            "target_table": fact.target_table,
            "execution_id": execution_id
        }
    except Exception as e:
        duration = int((time.time() - start_time) * 1000)
        
        fact.status = "error"
        db.commit()
        
        log.status = "error"
        log.finished_at = datetime.now()
        log.duration_ms = duration
        log.error_message = str(e)
        log.sql_executed = executed_sql
        db.commit()
        
        raise HTTPException(status_code=400, detail=str(e))
