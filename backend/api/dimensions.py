import uuid
import math
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


def _build_attrs(pk: str, attributes) -> str:
    """Monta lista de colunas da dimensao garantindo que a PK esteja presente"""
    if not attributes:
        return "*"
    cols = []
    for a in attributes:
        if a not in cols:
            cols.append(a)
    if pk not in cols:
        cols.insert(0, pk)
    return ", ".join(cols)


router = APIRouter(prefix="/api/dimensions", tags=["dimensions"])

@router.get("", response_model=List[schemas.DimensionResponse])
def list_dimensions(db: Session = Depends(get_db)):
    return db.query(models.Dimension).all()

@router.post("", response_model=schemas.DimensionResponse)
def create_dimension(dimension: schemas.DimensionCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Dimension).filter(models.Dimension.name == dimension.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Dimension name already exists")
    
    db_dimension = models.Dimension(
        id=str(uuid.uuid4()),
        name=dimension.name,
        source_table=dimension.source_table,
        target_table=dimension.target_table,
        primary_key=dimension.primary_key,
        surrogate_key=dimension.surrogate_key,
        attributes=dimension.attributes,
        hierarchies=dimension.hierarchies,
        mode=dimension.mode,
        custom_sql=dimension.custom_sql,
        status=dimension.status
    )
    db.add(db_dimension)
    db.commit()
    db.refresh(db_dimension)
    return db_dimension

@router.get("/{dimension_id}", response_model=schemas.DimensionResponse)
def get_dimension(dimension_id: str, db: Session = Depends(get_db)):
    dimension = db.query(models.Dimension).filter(models.Dimension.id == dimension_id).first()
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    return dimension

@router.put("/{dimension_id}", response_model=schemas.DimensionResponse)
def update_dimension(dimension_id: str, dimension_update: schemas.DimensionUpdate, db: Session = Depends(get_db)):
    dimension = db.query(models.Dimension).filter(models.Dimension.id == dimension_id).first()
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    
    if dimension_update.name and dimension_update.name != dimension.name:
        existing = db.query(models.Dimension).filter(models.Dimension.name == dimension_update.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Dimension name already exists")
    
    update_data = dimension_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dimension, field, value)
    
    db.commit()
    db.refresh(dimension)
    return dimension

@router.delete("/{dimension_id}")
def delete_dimension(dimension_id: str, db: Session = Depends(get_db)):
    dimension = db.query(models.Dimension).filter(models.Dimension.id == dimension_id).first()
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    
    db.delete(dimension)
    db.commit()
    return {"message": "Dimension deleted successfully"}

@router.post("/{dimension_id}/preview")
def preview_dimension(dimension_id: str, db: Session = Depends(get_db)):
    dimension = db.query(models.Dimension).filter(models.Dimension.id == dimension_id).first()
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    
    try:
        duckdb_conn = get_duckdb()
        
        if dimension.mode == 'sql' and dimension.custom_sql:
            sql = dimension.custom_sql.replace('_input', dimension.source_table)
            sql = f"SELECT * FROM ({sql}) LIMIT 10"
        else:
            # Build dimension SQL
            attrs = _build_attrs(dimension.primary_key, dimension.attributes)
            pk = dimension.primary_key
            sk = dimension.surrogate_key

            if sk:
                sql = f"""
                    SELECT ROW_NUMBER() OVER (ORDER BY {pk}) as {sk}, {attrs}
                    FROM (SELECT DISTINCT {pk}, {attrs} FROM {dimension.source_table})
                    LIMIT 10
                """
            else:
                sql = f"SELECT DISTINCT {pk}, {attrs} FROM {dimension.source_table} LIMIT 10"
        
        result = duckdb_conn.execute(sql).fetchdf()
        
        return {
            "columns": result.columns.tolist(),
            "data": _sanitize(result.to_dict('records')),
            "total_rows": len(result)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{dimension_id}/run")
def run_dimension(dimension_id: str, db: Session = Depends(get_db)):
    dimension = db.query(models.Dimension).filter(models.Dimension.id == dimension_id).first()
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    
    try:
        dimension.status = "running"
        db.commit()
        
        duckdb_conn = get_duckdb()
        
        if dimension.mode == 'sql' and dimension.custom_sql:
            sql = dimension.custom_sql.replace('_input', dimension.source_table)
            duckdb_conn.execute(f"CREATE OR REPLACE TABLE {dimension.target_table} AS {sql}")
        else:
            pk = dimension.primary_key
            sk = dimension.surrogate_key
            attrs = _build_attrs(pk, dimension.attributes)
            
            if sk:
                sql = f"""
                    CREATE OR REPLACE TABLE {dimension.target_table} AS
                    SELECT ROW_NUMBER() OVER (ORDER BY {pk}) as {sk}, {attrs}
                    FROM (SELECT DISTINCT {pk}, {attrs} FROM {dimension.source_table})
                """
            else:
                sql = f"""
                    CREATE OR REPLACE TABLE {dimension.target_table} AS
                    SELECT DISTINCT {pk}, {attrs} FROM {dimension.source_table}
                """
            duckdb_conn.execute(sql)
        
        result = duckdb_conn.execute(f"SELECT COUNT(*) FROM {dimension.target_table}").fetchone()
        rows_affected = result[0] if result else 0
        
        dimension.status = "valid"
        db.commit()
        
        return {
            "success": True,
            "message": "Dimension created successfully",
            "rows_affected": rows_affected,
            "target_table": dimension.target_table
        }
    except Exception as e:
        dimension.status = "error"
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))
