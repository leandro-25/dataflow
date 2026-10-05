import uuid
import math
import time
import asyncio
from typing import List, Optional, Dict, Any, Generator
from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from database import get_db, get_duckdb
import models
import schemas
from connectors.factory import get_connector
import pandas as pd
import os
import json
from datetime import datetime, timedelta


def _sanitize(records):
    if isinstance(records, list):
        return [_sanitize(r) for r in records]
    if isinstance(records, dict):
        return {k: _sanitize(v) for k, v in records.items()}
    if isinstance(records, float) and (math.isnan(records) or math.isinf(records)):
        return None
    return records


router = APIRouter(prefix="/api/ingestions", tags=["ingestions"])

# ============ LIST & GET ============

@router.get("", response_model=List[schemas.IngestionResponse])
def list_ingestions(
    search: Optional[str] = Query(None, description="Search by name"),
    source_id: Optional[str] = Query(None, description="Filter by source"),
    status: Optional[str] = Query(None, description="Filter by status"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    favorite_only: Optional[bool] = Query(None, description="Show only favorites"),
    folder: Optional[str] = Query(None, description="Filter by folder"),
    sort_by: Optional[str] = Query("sort_order", description="Sort field"),
    sort_order: Optional[str] = Query("asc", description="Sort order: asc or desc"),
    db: Session = Depends(get_db)
):
    """List all ingestions with filtering and sorting options"""
    try:
        # Only join with ingestion_orders when needed to avoid column ambiguity
        needs_join = (sort_by == "sort_order" or folder is not None)
        
        if needs_join:
            query = db.query(models.Ingestion).outerjoin(
                models.IngestionOrder,
                models.Ingestion.id == models.IngestionOrder.ingestion_id
            )
        else:
            query = db.query(models.Ingestion)
        
        if search:
            query = query.filter(models.Ingestion.name.ilike(f"%{search}%"))
        
        if source_id:
            query = query.filter(models.Ingestion.source_id == source_id)
        
        if status:
            query = query.filter(models.Ingestion.status == status)
        
        if favorite_only:
            query = query.filter(models.Ingestion.is_favorite == True)
        
        if tag:
            # Filter by tag in JSON array
            query = query.filter(models.Ingestion.tags.contains([tag]))
        
        if folder:
            query = query.filter(models.IngestionOrder.folder == folder)
        
        # Sorting
        if sort_by == "sort_order":
            # Use a consistent default value that puts un-ordered items at the end
            # regardless of sort direction
            if sort_order == "asc":
                query = query.order_by(func.coalesce(models.IngestionOrder.sort_order, 999999).asc())
            else:
                # For desc, use -1 so NULLs appear at the bottom (after all positive values)
                query = query.order_by(func.coalesce(models.IngestionOrder.sort_order, -1).desc())
        else:
            # Safely get the sort column from Ingestion model only
            if hasattr(models.Ingestion, sort_by):
                sort_column = getattr(models.Ingestion, sort_by)
            else:
                sort_column = models.Ingestion.created_at
            
            # Always use the column from Ingestion model explicitly to avoid ambiguity
            if sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)
        
        return query.all()
    except Exception as e:
        import traceback
        print(f"Error in list_ingestions: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/folders")
def get_folders(db: Session = Depends(get_db)):
    """Get list of folders for grouping"""
    folders = db.query(models.IngestionOrder.folder).distinct().all()
    return [f[0] for f in folders if f[0]]


@router.get("/stats/overview")
def get_ingestion_stats(
    days: int = Query(30, description="Stats for last N days"),
    db: Session = Depends(get_db)
):
    """Get overview statistics for all ingestions"""
    try:
        total = db.query(models.Ingestion).count()
        running = db.query(models.Ingestion).filter(models.Ingestion.status == "running").count()
        error = db.query(models.Ingestion).filter(models.Ingestion.status == "error").count()
        valid = db.query(models.Ingestion).filter(models.Ingestion.status == "valid").count()
        
        total_rows = db.query(func.sum(models.Ingestion.total_rows_ingested)).scalar() or 0
        
        # Today's stats
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        
        today_runs = db.query(func.count(models.ExecutionLog.id)).filter(
            models.ExecutionLog.resource_type == "ingestion",
            models.ExecutionLog.started_at >= today_start
        ).scalar()
        
        today_rows = db.query(func.sum(models.ExecutionLog.rows_affected)).filter(
            models.ExecutionLog.resource_type == "ingestion",
            models.ExecutionLog.started_at >= today_start,
            models.ExecutionLog.status == "success"
        ).scalar() or 0
        
        # Last N days trend
        days_ago = datetime.now() - timedelta(days=days)
        daily_stats = db.query(
            func.date(models.ExecutionLog.started_at).label('date'),
            func.count(models.ExecutionLog.id).label('runs'),
            func.sum(models.ExecutionLog.rows_affected).label('rows')
        ).filter(
            models.ExecutionLog.resource_type == "ingestion",
            models.ExecutionLog.started_at >= days_ago
        ).group_by(func.date(models.ExecutionLog.started_at)).all()
        
        return {
            "total_ingestions": total,
            "running": running,
            "error": error,
            "valid": valid,
            "total_rows_ingested": total_rows,
            "today_runs": today_runs,
            "today_rows_ingested": today_rows,
            "daily_trend": [{"date": str(d.date), "runs": d.runs, "rows": d.rows or 0} for d in daily_stats]
        }
    except Exception as e:
        import traceback
        print(f"Error in get_ingestion_stats: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{ingestion_id}", response_model=schemas.IngestionResponse)
def get_ingestion(ingestion_id: str, db: Session = Depends(get_db)):
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    return ingestion


@router.get("/{ingestion_id}/history")
def get_ingestion_history(
    ingestion_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get execution history for an ingestion"""
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    
    logs = db.query(models.ExecutionLog).filter(
        models.ExecutionLog.resource_id == ingestion_id,
        models.ExecutionLog.resource_type == "ingestion"
    ).order_by(desc(models.ExecutionLog.started_at)).offset(offset).limit(limit).all()
    
    total = db.query(func.count(models.ExecutionLog.id)).filter(
        models.ExecutionLog.resource_id == ingestion_id,
        models.ExecutionLog.resource_type == "ingestion"
    ).scalar()

    # Retorna lista direta (formato consumido pelo frontend)
    return [
            {
                "id": log.id,
                "execution_id": log.execution_id,
                "status": log.status,
                "started_at": log.started_at,
                "finished_at": log.finished_at,
                "duration_ms": log.duration_ms,
                "rows_affected": log.rows_affected,
                "error_message": log.error_message
            }
            for log in logs
        ]


@router.get("/{ingestion_id}/progress")
def get_ingestion_progress(ingestion_id: str, db: Session = Depends(get_db)):
    """Get real-time progress for running ingestion"""
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    
    if ingestion.status != "running" or not ingestion.current_execution_id:
        return {
            "status": ingestion.status,
            "progress": None,
            "message": "Ingestion is not running"
        }
    
    progress = db.query(models.ExecutionProgress).filter(
        models.ExecutionProgress.execution_id == ingestion.current_execution_id
    ).first()
    
    if not progress:
        return {
            "status": ingestion.status,
            "progress": None,
            "message": "No progress data available"
        }
    
    return {
        "status": progress.status,
        "progress": {
            "percent": progress.percent_complete,
            "rows_processed": progress.rows_processed,
            "rows_total": progress.rows_total,
            "stage": progress.stage,
            "speed": progress.speed_rows_per_second,
            "eta_seconds": progress.eta_seconds,
            "current_batch": progress.current_batch,
            "total_batches": progress.total_batches,
            "message": progress.message
        }
    }


# ============ CREATE & UPDATE ============

@router.post("", response_model=schemas.IngestionResponse)
def create_ingestion(ingestion: schemas.IngestionCreate, db: Session = Depends(get_db)):
    try:
        # Check if name already exists
        existing = db.query(models.Ingestion).filter(models.Ingestion.name == ingestion.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ingestion name already exists")
        
        # Verify source exists
        source = db.query(models.Source).filter(models.Source.id == ingestion.source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        db_ingestion = models.Ingestion(
            id=str(uuid.uuid4()),
            name=ingestion.name,
            source_id=ingestion.source_id,
            config=ingestion.config,
            schedule=ingestion.schedule,
            schedule_enabled=ingestion.schedule_enabled if hasattr(ingestion, 'schedule_enabled') else False,
            schedule_timezone=ingestion.schedule_timezone if hasattr(ingestion, 'schedule_timezone') else "America/Sao_Paulo",
            column_mapping=ingestion.column_mapping if hasattr(ingestion, 'column_mapping') else {},
            filters=ingestion.filters if hasattr(ingestion, 'filters') else [],
            selected_columns=ingestion.selected_columns if hasattr(ingestion, 'selected_columns') else [],
            incremental_config=ingestion.incremental_config if hasattr(ingestion, 'incremental_config') else {},
            advanced_options=ingestion.advanced_options if hasattr(ingestion, 'advanced_options') else {},
            tags=ingestion.tags if hasattr(ingestion, 'tags') else [],
            description=ingestion.description if hasattr(ingestion, 'description') else None,
            is_favorite=ingestion.is_favorite if hasattr(ingestion, 'is_favorite') else False,
            status="pending"
        )
        db.add(db_ingestion)
        db.commit()
        db.refresh(db_ingestion)
        return db_ingestion
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error in create_ingestion: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.put("/{ingestion_id}", response_model=schemas.IngestionResponse)
def update_ingestion(ingestion_id: str, ingestion_update: schemas.IngestionUpdate, db: Session = Depends(get_db)):
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    
    # Check name uniqueness if updating name
    if ingestion_update.name and ingestion_update.name != ingestion.name:
        existing = db.query(models.Ingestion).filter(models.Ingestion.name == ingestion_update.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ingestion name already exists")
    
    # Update fields
    update_data = ingestion_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ingestion, field, value)
    
    db.commit()
    db.refresh(ingestion)
    return ingestion


@router.patch("/{ingestion_id}/favorite")
def toggle_favorite(ingestion_id: str, db: Session = Depends(get_db)):
    """Toggle favorite status"""
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    
    ingestion.is_favorite = not ingestion.is_favorite
    db.commit()
    
    return {"is_favorite": ingestion.is_favorite}


@router.delete("/{ingestion_id}")
def delete_ingestion(ingestion_id: str, db: Session = Depends(get_db)):
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    
    db.delete(ingestion)
    db.commit()
    return {"message": "Ingestion deleted successfully"}


# ============ DRAG & DROP REORDERING ============

@router.post("/reorder")
def reorder_ingestions(
    orders: List[Dict[str, Any]] = Body(...),
    db: Session = Depends(get_db)
):
    """Update sort order for multiple ingestions (drag & drop)"""
    for order_data in orders:
        ingestion_id = order_data.get("ingestion_id")
        sort_order = order_data.get("sort_order")
        folder = order_data.get("folder")
        
        existing = db.query(models.IngestionOrder).filter(
            models.IngestionOrder.ingestion_id == ingestion_id
        ).first()
        
        if existing:
            existing.sort_order = sort_order
            if folder is not None:
                existing.folder = folder
        else:
            new_order = models.IngestionOrder(
                id=str(uuid.uuid4()),
                ingestion_id=ingestion_id,
                sort_order=sort_order,
                folder=folder
            )
            db.add(new_order)
    
    db.commit()
    return {"success": True}


@router.put("/{ingestion_id}/folder")
def set_ingestion_folder(
    ingestion_id: str,
    folder: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """Set folder for an ingestion"""
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    
    order = db.query(models.IngestionOrder).filter(
        models.IngestionOrder.ingestion_id == ingestion_id
    ).first()
    
    if order:
        order.folder = folder
    else:
        order = models.IngestionOrder(
            id=str(uuid.uuid4()),
            ingestion_id=ingestion_id,
            folder=folder,
            sort_order=0
        )
        db.add(order)
    
    db.commit()
    return {"success": True, "folder": folder}


# ============ KEYBOARD SHORTCUTS ============

@router.get("/shortcuts/list")
def get_keyboard_shortcuts(db: Session = Depends(get_db)):
    """Get all keyboard shortcuts"""
    shortcuts = db.query(models.KeyboardShortcut).filter(
        models.KeyboardShortcut.enabled == True
    ).all()
    
    return [
        {
            "id": s.id,
            "key": s.shortcut_key,
            "action": s.action,
            "description": s.description
        }
        for s in shortcuts
    ]


@router.post("/shortcuts/create")
def create_shortcut(
    shortcut: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Create or update a keyboard shortcut"""
    existing = db.query(models.KeyboardShortcut).filter(
        models.KeyboardShortcut.shortcut_key == shortcut.get("key")
    ).first()
    
    if existing:
        existing.action = shortcut.get("action")
        existing.description = shortcut.get("description")
        existing.enabled = shortcut.get("enabled", True)
    else:
        new_shortcut = models.KeyboardShortcut(
            id=str(uuid.uuid4()),
            shortcut_key=shortcut.get("key"),
            action=shortcut.get("action"),
            description=shortcut.get("description"),
            enabled=shortcut.get("enabled", True)
        )
        db.add(new_shortcut)
    
    db.commit()
    return {"success": True}


# ============ TYPE MAPPING & SCHEMA ============

@router.post("/dry-run")
def dry_run_ingestion(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Testa a extracao com filtros/mapeamento informados SEM salvar nada."""
    source_id = payload.get("source_id")
    config = payload.get("config") or {}
    filters = payload.get("filters") or []
    column_mapping = payload.get("column_mapping") or {}
    try:
        limit = max(1, int(payload.get("limit", 20)))
    except (TypeError, ValueError):
        limit = 20

    source = db.query(models.Source).filter(models.Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    try:
        connector = get_connector(source.type, source.config)
        mode = config.get("mode", "table")

        if mode == "query":
            query_text = config.get("query")
            if not query_text:
                raise HTTPException(status_code=400, detail="Query nao especificada")
            df = connector.extract_sample(query_text, is_query=True, limit=limit)
        else:
            tabela = config.get("table")
            if not tabela:
                raise HTTPException(status_code=400, detail="Tabela nao especificada")
            try:
                disponiveis = connector.list_tables()
                caminho_fonte = str(source.config.get("file_path") or source.config.get("table_path") or "")
                nomes_aceitos = {caminho_fonte}
                if caminho_fonte:
                    nomes_aceitos.add(os.path.basename(caminho_fonte))
                if disponiveis and tabela not in disponiveis and tabela not in nomes_aceitos:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Recurso '{tabela}' nao encontrado na fonte. Disponiveis: {', '.join(map(str, disponiveis[:8]))}"
                    )
            except HTTPException:
                raise
            except Exception:
                pass
            df = connector.extract_sample(tabela, is_query=False, limit=max(limit * 5, 50))

        for src_col, mapping in (column_mapping or {}).items():
            alvo = mapping.get("target_name") if isinstance(mapping, dict) else mapping
            if src_col in df.columns and alvo:
                df = df.rename(columns={src_col: alvo})

        for f in filters or []:
            col = f.get("column")
            op = f.get("operator")
            val = f.get("value")
            if not col or col not in df.columns or val is None:
                continue
            if op == "eq":
                df = df[df[col] == val]
            elif op == "ne":
                df = df[df[col] != val]
            elif op == "gt":
                df = df[df[col] > val]
            elif op == "gte":
                df = df[df[col] >= val]
            elif op == "lt":
                df = df[df[col] < val]
            elif op == "lte":
                df = df[df[col] <= val]
            elif op == "contains":
                df = df[df[col].astype(str).str.contains(str(val), na=False)]

        df = df.head(limit)
        return {
            "columns": df.columns.tolist(),
            "data": _sanitize(df.to_dict("records")),
            "total_rows": len(df),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{ingestion_id}/type-mapping")
def get_type_mapping(ingestion_id: str, db: Session = Depends(get_db)):
    """Get current type mapping with auto-detected suggestions"""
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    
    source = db.query(models.Source).filter(models.Source.id == ingestion.source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    try:
        connector = get_connector(source.type, source.config)
        
        # Get schema
        schema = []
        config = ingestion.config
        mode = config.get('mode', 'table')
        
        if mode == 'table':
            table = config.get('table')
            if table:
                schema = connector.get_schema(table)
        else:
            query = config.get('query')
            if query:
                df_sample = connector.extract_sample(query, is_query=True, limit=10)
                schema = [
                    {"name": col, "type": str(df_sample[col].dtype), "nullable": True}
                    for col in df_sample.columns
                ]
        
        # Get current mappings
        current_mappings = ingestion.column_mapping or {}
        
        # Generate suggestions
        type_suggestions = {}
        for col in schema:
            col_name = col['name']
            source_type = col['type']
            
            # Suggest DuckDB types
            if 'int' in source_type.lower():
                suggested = 'INTEGER'
            elif 'float' in source_type.lower() or 'double' in source_type.lower():
                suggested = 'DOUBLE'
            elif 'bool' in source_type.lower():
                suggested = 'BOOLEAN'
            elif 'date' in source_type.lower() or 'time' in source_type.lower():
                suggested = 'TIMESTAMP'
            else:
                suggested = 'VARCHAR'
            
            current = current_mappings.get(col_name, {})
            type_suggestions[col_name] = {
                "source_type": source_type,
                "suggested_type": suggested,
                "current_mapping": current.get('target_type') or suggested,
                "current_name": current.get('target_name') or col_name,
                "nullable": current.get('nullable', True),
                "default_value": current.get('default_value')
            }
        
        return {
            "schema": schema,
            "type_suggestions": type_suggestions,
            "current_mappings": current_mappings
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{ingestion_id}/type-mapping")
def update_type_mapping(
    ingestion_id: str,
    mappings: Dict[str, Dict[str, Any]] = Body(...),
    db: Session = Depends(get_db)
):
    """Update type mappings for columns"""
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    
    ingestion.column_mapping = mappings
    db.commit()
    
    return {"success": True, "mappings": mappings}


# ============ AUTO-DETECTION ============

@router.post("/detect-file-format")
def detect_file_format(file_path: str = Body(..., embed=True)):
    """Auto-detect encoding and delimiter for CSV files"""
    try:
        import chardet
        
        # Detect encoding
        with open(file_path, 'rb') as f:
            raw_data = f.read(100000)  # Read first 100KB
            encoding_result = chardet.detect(raw_data)
            encoding = encoding_result.get('encoding', 'utf-8')
            confidence = encoding_result.get('confidence', 0)
        
        # Detect delimiter for CSV
        delimiters = [',', ';', '\t', '|']
        delimiter_counts = {}
        
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            first_lines = [f.readline() for _ in range(5)]
            
            for delim in delimiters:
                counts = [line.count(delim) for line in first_lines if line.strip()]
                if counts and min(counts) > 0 and max(counts) == min(counts):
                    delimiter_counts[delim] = min(counts)
        
        # Most consistent delimiter
        detected_delimiter = max(delimiter_counts.items(), key=lambda x: x[1])[0] if delimiter_counts else ','
        
        # Detect if has header
        with open(file_path, 'r', encoding=encoding) as f:
            first_line = f.readline().strip()
            has_header = not any(c.isdigit() for c in first_line.split(detected_delimiter)[0])
        
        return {
            "encoding": encoding,
            "encoding_confidence": confidence,
            "delimiter": detected_delimiter,
            "has_header": has_header,
            "first_line_preview": first_line[:200]
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analyze-json-structure")
def analyze_json_structure(file_path: str = Body(..., embed=True)):
    """Analyze JSON structure and suggest paths"""
    try:
        import json
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        def analyze_structure(obj, path="", depth=0, max_depth=5):
            """Recursively analyze JSON structure"""
            if depth > max_depth:
                return []
            
            paths = []
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    paths.append({
                        "path": current_path,
                        "type": type(value).__name__,
                        "depth": depth,
                        "is_array": isinstance(value, list),
                        "sample": str(value)[:50] if not isinstance(value, (dict, list)) else None
                    })
                    
                    if isinstance(value, (dict, list)) and depth < max_depth:
                        paths.extend(analyze_structure(value, current_path, depth + 1, max_depth))
                        
            elif isinstance(obj, list) and len(obj) > 0:
                paths.append({
                    "path": path or "root",
                    "type": "array",
                    "depth": depth,
                    "is_array": True,
                    "item_count": len(obj),
                    "item_type": type(obj[0]).__name__ if obj else None
                })
                
                # Analyze first item if it's a dict
                if obj and isinstance(obj[0], dict):
                    paths.extend(analyze_structure(obj[0], path, depth + 1, max_depth))
            
            return paths
        
        structure = analyze_structure(data)
        
        # Find likely data paths (arrays of objects)
        data_paths = [s for s in structure if s.get('is_array') and s.get('item_type') == 'dict']
        
        return {
            "structure": structure[:50],  # Limit to first 50 paths
            "suggested_data_paths": data_paths,
            "root_type": type(data).__name__,
            "is_array": isinstance(data, list),
            "array_length": len(data) if isinstance(data, list) else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analyze-xml-structure")
def analyze_xml_structure(file_path: str = Body(..., embed=True)):
    """Analyze XML structure and suggest row elements"""
    try:
        import xml.etree.ElementTree as ET
        
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        def analyze_element(element, path="", depth=0, max_depth=4):
            """Recursively analyze XML structure"""
            if depth > max_depth:
                return []
            
            current_path = f"{path}/{element.tag}" if path else element.tag
            
            info = {
                "tag": element.tag,
                "path": current_path,
                "depth": depth,
                "attributes": list(element.attrib.keys()),
                "child_count": len(element),
                "text_preview": (element.text or "")[:50].strip()
            }
            
            results = [info]
            
            # Analyze children
            for child in element:
                results.extend(analyze_element(child, current_path, depth + 1, max_depth))
            
            return results
        
        structure = analyze_element(root)
        
        # Find potential row elements (elements with multiple similar children)
        from collections import Counter
        tag_counts = Counter(e['tag'] for e in structure if e['depth'] > 0)
        potential_rows = [
            {"tag": tag, "count": count, "path": next(e['path'] for e in structure if e['tag'] == tag and e['depth'] > 0)}
            for tag, count in tag_counts.most_common(10) if count > 1
        ]
        
        return {
            "root_tag": root.tag,
            "structure": structure[:50],
            "potential_row_elements": potential_rows,
            "unique_tags": len(tag_counts)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ VALIDATION & METADATA ============

@router.post("/{ingestion_id}/validate")
def validate_ingestion(ingestion_id: str, db: Session = Depends(get_db)):
    """Validate source connection and configuration before creating/updating"""
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    
    source = db.query(models.Source).filter(models.Source.id == ingestion.source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    warnings = []
    errors = []
    
    try:
        # Test connection
        connector = get_connector(source.type, source.config)
        success, message = connector.test_connection()
        
        if not success:
            errors.append(f"Connection failed: {message}")
        
        # Validate specific configuration
        config = ingestion.config
        mode = config.get('mode', 'table')
        
        if mode == 'table':
            table = config.get('table')
            if not table:
                errors.append("Table not specified")
            elif source.type in ['postgres', 'mysql']:
                try:
                    # Check if table exists
                    tables = connector.list_tables()
                    if table not in tables:
                        errors.append(f"Table '{table}' not found in source")
                except Exception as e:
                    warnings.append(f"Could not validate table: {str(e)}")
            else:
                # File-based source: validate the file itself and the table/file match
                file_path = source.config.get('file_path', '')
                if file_path and not file_path.startswith('http'):
                    if not os.path.exists(file_path):
                        errors.append(f"File not found: {file_path}")
                    elif table not in (os.path.basename(file_path), file_path):
                        try:
                            tables = connector.list_tables()
                            if table not in tables:
                                errors.append(f"Table '{table}' not found in source")
                        except Exception as e:
                            warnings.append(f"Could not validate table: {str(e)}")
        
        elif mode == 'query':
            query = config.get('query')
            if not query:
                errors.append("Query not specified")
            elif not query.strip().upper().startswith('SELECT'):
                errors.append("Query must start with SELECT")
        
        # Check for large files (for file sources)
        if source.type in ['csv', 'excel', 'json', 'xml', 'parquet', 'avro', 'orc']:
            file_path = source.config.get('file_path', '')
            if file_path and not file_path.startswith('http'):
                try:
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    if size_mb > 100:
                        warnings.append(f"Large file detected ({size_mb:.1f} MB). Consider using batch processing.")
                except:
                    pass
        
        # Set validation status
        if errors:
            ingestion.validation_status = "error"
            ingestion.validation_message = "; ".join(errors)
        elif warnings:
            ingestion.validation_status = "warning"
            ingestion.validation_message = "; ".join(warnings)
        else:
            ingestion.validation_status = "success"
            ingestion.validation_message = "Validation passed"
        
        db.commit()
        
        return {
            "valid": len(errors) == 0,
            "status": ingestion.validation_status,
            "message": ingestion.validation_message,
            "warnings": warnings,
            "errors": errors
        }
        
    except Exception as e:
        ingestion.validation_status = "error"
        ingestion.validation_message = str(e)
        db.commit()
        
        return {
            "valid": False,
            "status": "error",
            "message": str(e),
            "warnings": [],
            "errors": [str(e)]
        }


@router.get("/{ingestion_id}/metadata")
def get_ingestion_metadata(ingestion_id: str, db: Session = Depends(get_db)):
    """Get detailed metadata about the source"""
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    
    source = db.query(models.Source).filter(models.Source.id == ingestion.source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    try:
        connector = get_connector(source.type, source.config)
        
        metadata = {
            "source_type": source.type,
            "source_name": source.name,
            "schema": [],
            "tables": [],
            "estimated_rows": None,
            "file_info": {}
        }
        
        # Get schema if configured
        config = ingestion.config
        mode = config.get('mode', 'table')
        
        if mode == 'table':
            table = config.get('table')
            if table:
                try:
                    metadata["schema"] = connector.get_schema(table)
                    
                    # Try to get row count estimate
                    df_sample = connector.extract_sample(table, is_query=False, limit=1000)
                    metadata["estimated_rows"] = "1000+" if len(df_sample) == 1000 else len(df_sample)
                except Exception as e:
                    metadata["schema_error"] = str(e)
        
        elif mode == 'query':
            query = config.get('query')
            if query:
                try:
                    df_sample = connector.extract_sample(query, is_query=True, limit=10)
                    metadata["schema"] = [
                        {"name": col, "type": str(df_sample[col].dtype), "nullable": df_sample[col].isna().any()}
                        for col in df_sample.columns
                    ]
                except Exception as e:
                    metadata["schema_error"] = str(e)
        
        # File-specific metadata
        if source.type in ['csv', 'excel', 'json', 'xml', 'parquet', 'avro', 'orc', 'sql_file']:
            file_path = source.config.get('file_path', '')
            if file_path and not file_path.startswith('http'):
                try:
                    stat = os.stat(file_path)
                    metadata["file_info"] = {
                        "path": file_path,
                        "size_bytes": stat.st_size,
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                        "modified": pd.to_datetime(stat.st_mtime, unit='s').isoformat()
                    }
                except:
                    pass
        
        # Database-specific
        if source.type in ['postgres', 'mysql']:
            try:
                metadata["tables"] = connector.list_tables()
            except:
                pass
        
        return metadata
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ PREVIEW ============

@router.post("/{ingestion_id}/preview")
def preview_ingestion(
    ingestion_id: str,
    options: Optional[Dict[str, Any]] = Body(None),
    db: Session = Depends(get_db)
):
    """Preview data with filtering and column selection"""
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    
    source = db.query(models.Source).filter(models.Source.id == ingestion.source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    try:
        connector = get_connector(source.type, source.config)
        
        config = ingestion.config
        mode = config.get('mode', 'table')
        
        # Get data
        if mode == 'table':
            table = config.get('table')
            if not table:
                raise HTTPException(status_code=400, detail="Table not specified")
            df = connector.extract_sample(table, is_query=False, limit=100)
        else:  # query mode
            query = config.get('query')
            if not query:
                raise HTTPException(status_code=400, detail="Query not specified")
            df = connector.extract_sample(query, is_query=True, limit=100)
        
        # Apply column selection if specified
        selected_columns = ingestion.selected_columns or []
        if selected_columns and len(selected_columns) > 0:
            available_cols = [c for c in selected_columns if c in df.columns]
            if available_cols:
                df = df[available_cols]
        
        # Apply filters if specified
        filters = ingestion.filters or []
        for filter_config in filters:
            col = filter_config.get('column')
            operator = filter_config.get('operator')
            value = filter_config.get('value')
            
            if col and col in df.columns and operator and value is not None:
                if operator == 'eq':
                    df = df[df[col] == value]
                elif operator == 'ne':
                    df = df[df[col] != value]
                elif operator == 'gt':
                    df = df[df[col] > value]
                elif operator == 'gte':
                    df = df[df[col] >= value]
                elif operator == 'lt':
                    df = df[df[col] < value]
                elif operator == 'lte':
                    df = df[df[col] <= value]
                elif operator == 'contains':
                    df = df[df[col].astype(str).str.contains(str(value), na=False)]
        
        # Get formatted preview
        preview_limit = options.get('limit', 10) if options else 10
        
        return {
            "columns": df.columns.tolist(),
            "data": _sanitize(df.head(preview_limit).to_dict('records')),
            "total_rows": len(df),
            "dtypes": {col: str(df[col].dtype) for col in df.columns},
            "null_counts": {col: int(df[col].isna().sum()) for col in df.columns}
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ RUN & EXECUTE ============

@router.post("/{ingestion_id}/run")
def run_ingestion(ingestion_id: str, db: Session = Depends(get_db)):
    """Execute ingestion with all configurations"""
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    
    source = db.query(models.Source).filter(models.Source.id == ingestion.source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    start_time = time.time()
    execution_id = str(uuid.uuid4())
    
    # Create execution log
    execution_log = models.ExecutionLog(
        id=str(uuid.uuid4()),
        execution_id=execution_id,
        resource_type="ingestion",
        resource_id=ingestion_id,
        resource_name=ingestion.name,
        status="running"
    )
    db.add(execution_log)
    
    # Update ingestion status
    ingestion.status = "running"
    ingestion.current_execution_id = execution_id
    db.commit()
    
    try:
        # Get connector and extract data
        connector = get_connector(source.type, source.config)
        
        config = ingestion.config
        mode = config.get('mode', 'table')
        target_table = config.get('target_table')
        chunk_size = ingestion.advanced_options.get('chunk_size', 50000) if ingestion.advanced_options else 50000
        
        if not target_table:
            raise HTTPException(status_code=400, detail="Target table not specified")
        
        # Extract and load in chunks for large datasets
        rows_affected = 0
        
        if mode == 'table':
            table = config.get('table')
            if not table:
                raise HTTPException(status_code=400, detail="Table not specified")
            rows_affected = _extract_chunk_and_load(
                connector=connector,
                table=table,
                target_table=target_table,
                chunk_size=chunk_size,
                column_mapping=ingestion.column_mapping or {},
                filters=ingestion.filters or [],
                incremental_config=ingestion.incremental_config or {},
                ingestion=ingestion,
                db=db
            )
        else:  # query mode
            query = config.get('query')
            if not query:
                raise HTTPException(status_code=400, detail="Query not specified")
            rows_affected = _extract_chunk_and_load(
                connector=connector,
                table=query,
                target_table=target_table,
                chunk_size=chunk_size,
                column_mapping=ingestion.column_mapping or {},
                filters=ingestion.filters or [],
                incremental_config=ingestion.incremental_config or {},
                ingestion=ingestion,
                db=db,
                is_query=True
            )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Update execution log
        execution_log.status = "success"
        execution_log.finished_at = func.now()
        execution_log.duration_ms = duration_ms
        execution_log.rows_affected = rows_affected
        
        # Update ingestion stats
        ingestion.status = "valid"
        ingestion.current_execution_id = None
        ingestion.last_run_at = func.now()
        ingestion.last_run_status = "success"
        ingestion.last_run_rows = rows_affected
        ingestion.last_run_duration_ms = duration_ms
        ingestion.total_runs = (ingestion.total_runs or 0) + 1
        ingestion.total_rows_ingested = (ingestion.total_rows_ingested or 0) + rows_affected
        
        # Update averages
        if ingestion.total_runs > 0:
            ingestion.avg_rows_per_run = ingestion.total_rows_ingested // ingestion.total_runs
            # Recalculate total duration properly
            total_duration = (ingestion.avg_duration_ms or 0) * (ingestion.total_runs - 1) + duration_ms
            ingestion.avg_duration_ms = total_duration // ingestion.total_runs
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Ingestion completed successfully",
            "rows_affected": rows_affected,
            "duration_ms": duration_ms,
            "target_table": target_table,
            "execution_id": execution_id,
            "chunk_processing": True if chunk_size < 100000 else "batch_mode"
        }
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Update execution log with error
        execution_log.status = "error"
        execution_log.finished_at = func.now()
        execution_log.duration_ms = duration_ms
        execution_log.error_message = str(e)
        
        # Update ingestion status
        ingestion.status = "error"
        ingestion.current_execution_id = None
        ingestion.last_run_status = "error"
        ingestion.last_run_error = str(e)
        ingestion.last_run_duration_ms = duration_ms
        
        db.commit()
        
        raise HTTPException(status_code=400, detail=str(e))


def _extract_chunk_and_load(
    connector,
    table: str,
    target_table: str,
    chunk_size: int,
    column_mapping: Dict[str, Any],
    filters: List[Dict[str, Any]],
    incremental_config: Dict[str, Any],
    ingestion,
    db: Session,
    is_query: bool = False
) -> int:
    """Extract data in chunks and load to DuckDB efficiently"""
    import pandas as pd
    from database import get_duckdb
    
    total_rows = 0
    duckdb_conn = get_duckdb()
    
    # Strategy: Use DuckDB native SQL for maximum performance
    # For file sources, use extract with limit; for DB sources, use SQL directly
    
    # Check if we can use SQL-based approach (most efficient)
    # Apply transformations via SQL push-down using TransformGenerator
    from engine.transform_generator import TransformGenerator
    
    # Build the base extraction SQL with transformations
    # This pushes filters, renames, casts etc. to the database level
    
    try:
        # Extract all data once - file connectors don't support pagination
        full_df = connector.extract(table, is_query=is_query)
        
        offset = 0
        first_chunk = True
        
        while True:
            # Slice the next chunk from the extracted data
            df = full_df.iloc[offset:offset + chunk_size].copy()
            
            if df.empty:
                break
            
            rows_in_chunk = len(df)
            total_rows += rows_in_chunk
            
            # Apply column mapping (renaming) on chunk - after extract
            # This is necessary since we extracted before rename
            column_mapping_local = column_mapping or {}
            for source_col, mapping in column_mapping_local.items():
                if source_col in df.columns:
                    target_name = mapping.get('target_name')
                    if target_name and target_name != source_col:
                        df = df.rename(columns={source_col: target_name})
            
            # Apply filters on chunk
            for filter_config in filters:
                col = filter_config.get('column')
                operator = filter_config.get('operator')
                value = filter_config.get('value')
                
                if col and col in df.columns and operator and value is not None:
                    if operator == 'eq':
                        df = df[df[col] == value]
                    elif operator == 'ne':
                        df = df[df[col] != value]
                    elif operator == 'gt':
                        df = df[df[col] > value]
                    elif operator == 'gte':
                        df = df[df[col] >= value]
                    elif operator == 'lt':
                        df = df[df[col] < value]
                    elif operator == 'lte':
                        df = df[df[col] <= value]
                    elif operator == 'contains':
                        df = df[df[col].astype(str).str.contains(str(value), na=False)]
            
            # Handle incremental loading per chunk
            inc_config = incremental_config or {}
            if inc_config.get('enabled'):
                control_column = inc_config.get('control_column')
                last_value = inc_config.get('last_value')
                
                if control_column and control_column in df.columns and last_value is not None:
                    df = df[df[control_column] > last_value]
                    
                    # Update last_value for next chunk
                    if len(df) > 0:
                        new_max = df[control_column].max()
                        inc_config['last_value'] = str(new_max)
                        incremental_config['last_value'] = str(new_max)
            
            # Load chunk to DuckDB using efficient method
            if first_chunk:
                # First chunk: create table with schema + data
                # Use DuckDB's CREATE TABLE AS SELECT for efficiency
                # Convert pandas df to DuckDB relation
                duckdb_conn.register(f"_chunk_{offset}", df)
                duckdb_conn.execute(f"""
                    CREATE OR REPLACE TABLE {target_table} AS 
                    SELECT * FROM _chunk_{offset}
                """)
                duckdb_conn.unregister(f"_chunk_{offset}")
                first_chunk = False
            else:
                # Subsequent chunks: INSERT ONLY the new data
                duckdb_conn.register(f"_chunk_{offset}", df)
                duckdb_conn.execute(f"""
                    INSERT INTO {target_table} 
                    SELECT * FROM _chunk_{offset}
                """)
                duckdb_conn.unregister(f"_chunk_{offset}")
            
            offset += chunk_size
            
            # Stop if we got less than chunk_size rows - likely end of data
            if rows_in_chunk < chunk_size:
                break
        
        # Return final row count
        final_count = duckdb_conn.execute(f"SELECT COUNT(*) FROM {target_table}").fetchone()[0]
        return final_count if final_count > 0 else total_rows
        
    except Exception as e:
        # If SQL approach fails, fall back to original method
        # But for now, re-raise
        raise e


@router.post("/{ingestion_id}/run-async")
def run_ingestion_async(ingestion_id: str, db: Session = Depends(get_db)):
    """Queue ingestion for async execution"""
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    
    if ingestion.status == "running":
        raise HTTPException(status_code=400, detail="Ingestion is already running")
    
    # Set status to queued (scheduler will pick it up)
    ingestion.status = "queued"
    db.commit()
    
    return {
        "success": True,
        "message": "Ingestion queued for execution",
        "ingestion_id": ingestion_id
    }


# ============ BULK OPERATIONS ============

class BulkCreateRequest(BaseModel):
    source_id: str
    tables: List[str]
    naming_pattern: str = "raw_{name}"
    config_template: Optional[Dict[str, Any]] = None


@router.post("/bulk/create")
def bulk_create_ingestions(payload: BulkCreateRequest, db: Session = Depends(get_db)):
    """Create multiple ingestions at once"""
    source_id = payload.source_id
    tables = payload.tables
    naming_pattern = payload.naming_pattern
    config_template = payload.config_template

    source = db.query(models.Source).filter(models.Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    created = []
    errors = []

    for table in tables:
        try:
            name = naming_pattern.replace("{name}", table.lower().replace(" ", "_"))
            name = "".join(ch for ch in name if ch.isalnum() or ch == "_")
            
            # Check if name exists
            existing = db.query(models.Ingestion).filter(models.Ingestion.name == name).first()
            if existing:
                errors.append(f"Name '{name}' already exists for table '{table}'")
                continue
            
            config = config_template or {}
            config.update({
                "mode": "table",
                "table": table,
                "target_table": name
            })
            
            ingestion = models.Ingestion(
                id=str(uuid.uuid4()),
                name=name,
                source_id=source_id,
                config=config,
                status="pending"
            )
            db.add(ingestion)
            created.append({"name": name, "table": table})
            
        except Exception as e:
            errors.append(f"Error creating ingestion for '{table}': {str(e)}")
    
    db.commit()
    
    return {
        "created": created,
        "errors": errors,
        "total": len(tables),
        "success": len(created)
    }


@router.post("/bulk/delete")
def bulk_delete_ingestions(ingestion_ids: List[str], db: Session = Depends(get_db)):
    """Delete multiple ingestions"""
    deleted = 0
    errors = []
    
    for ingestion_id in ingestion_ids:
        ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
        if ingestion:
            db.delete(ingestion)
            deleted += 1
        else:
            errors.append(f"Ingestion {ingestion_id} not found")
    
    db.commit()
    
    return {
        "deleted": deleted,
        "errors": errors
    }


@router.post("/{ingestion_id}/duplicate")
def duplicate_ingestion(ingestion_id: str, new_name: str, db: Session = Depends(get_db)):
    """Duplicate an ingestion with a new name"""
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    
    # Check new name
    existing = db.query(models.Ingestion).filter(models.Ingestion.name == new_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Name already exists")
    
    new_ingestion = models.Ingestion(
        id=str(uuid.uuid4()),
        name=new_name,
        source_id=ingestion.source_id,
        config=ingestion.config,
        schedule=ingestion.schedule,
        schedule_enabled=False,  # Don't enable schedule by default
        column_mapping=ingestion.column_mapping,
        filters=ingestion.filters,
        selected_columns=ingestion.selected_columns,
        incremental_config=ingestion.incremental_config,
        advanced_options=ingestion.advanced_options,
        tags=ingestion.tags,
        description=ingestion.description,
        status="pending"
    )
    
    db.add(new_ingestion)
    db.commit()
    db.refresh(new_ingestion)
    
    return new_ingestion


# ============ TEMPLATES ============

@router.get("/templates/list")
def list_templates():
    """List available ingestion templates"""
    templates = [
        {
            "id": "csv_standard",
            "name": "CSV Padrão",
            "description": "Configuração otimizada para arquivos CSV",
            "config": {
                "advanced_options": {
                    "encoding": "utf-8",
                    "delimiter": ",",
                    "has_header": True
                }
            },
            "applies_to": ["csv"]
        },
        {
            "id": "postgres_incremental",
            "name": "PostgreSQL Incremental",
            "description": "Configuração para carga incremental do PostgreSQL",
            "config": {
                "incremental_config": {
                    "enabled": True,
                    "control_column": "updated_at"
                }
            },
            "applies_to": ["postgres"]
        },
        {
            "id": "excel_multi_sheet",
            "name": "Excel Múltiplas Abas",
            "description": "Configuração para importar várias abas do Excel",
            "config": {
                "advanced_options": {
                    "import_all_sheets": False
                }
            },
            "applies_to": ["excel"]
        },
        {
            "id": "api_pagination",
            "name": "API com Paginação",
            "description": "Configuração para APIs REST com paginação",
            "config": {
                "advanced_options": {
                    "pagination": True,
                    "page_size": 100
                }
            },
            "applies_to": ["rest_api"]
        }
    ]
    
    return templates


@router.post("/{ingestion_id}/apply-template")
def apply_template(
    ingestion_id: str,
    template_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = Body(None),
    db: Session = Depends(get_db)
):
    """Apply a template configuration to an ingestion"""
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Ingestion not found")

    # Aceita template_id via query string ou via body JSON (formato do frontend)
    template_id = template_id or (payload or {}).get("template_id")
    if not template_id:
        raise HTTPException(status_code=400, detail="template_id not specified")

    # Get template
    templates = list_templates()
    template = next((t for t in templates if t["id"] == template_id), None)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Apply template config (merge with existing)
    import copy
    current_config = copy.deepcopy(ingestion.config or {})
    template_config = template["config"]

    for key, value in template_config.items():
        if key not in current_config or current_config[key] is None:
            current_config[key] = value
        elif isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if sub_key not in current_config.get(key, {}):
                    if key not in current_config:
                        current_config[key] = {}
                    current_config[key][sub_key] = sub_value

    # Reatribuir novo objeto para o SQLAlchemy detectar a mudanca na coluna JSON
    ingestion.config = current_config
    db.commit()

    return {"success": True, "template_applied": template_id}
