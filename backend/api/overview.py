from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db, get_duckdb
import models

router = APIRouter(prefix="/api/overview", tags=["overview"])

@router.get("")
def get_overview(db: Session = Depends(get_db)):
    """Retorna visão geral do sistema com estatísticas de todos os módulos"""
    try:
        # Sources stats
        total_sources = db.query(models.Source).count()
        valid_sources = db.query(models.Source).filter(models.Source.status == "valid").count()
        invalid_sources = db.query(models.Source).filter(models.Source.status == "invalid").count()
        
        # Ingestions stats
        total_ingestions = db.query(models.Ingestion).count()
        running_ingestions = db.query(models.Ingestion).filter(models.Ingestion.status == "running").count()
        error_ingestions = db.query(models.Ingestion).filter(models.Ingestion.status == "error").count()
        valid_ingestions = db.query(models.Ingestion).filter(models.Ingestion.status == "valid").count()
        total_rows_ingested = db.query(func.sum(models.Ingestion.total_rows_ingested)).scalar() or 0
        
        # Staging stats
        total_stagings = db.query(models.Staging).count()
        running_stagings = db.query(models.Staging).filter(models.Staging.status == "running").count()
        error_stagings = db.query(models.Staging).filter(models.Staging.status == "error").count()
        valid_stagings = db.query(models.Staging).filter(models.Staging.status == "valid").count()
        
        # Dimensions stats
        total_dimensions = db.query(models.Dimension).count()
        running_dimensions = db.query(models.Dimension).filter(models.Dimension.status == "running").count()
        error_dimensions = db.query(models.Dimension).filter(models.Dimension.status == "error").count()
        valid_dimensions = db.query(models.Dimension).filter(models.Dimension.status == "valid").count()
        
        # Facts stats
        total_facts = db.query(models.Fact).count()
        running_facts = db.query(models.Fact).filter(models.Fact.status == "running").count()
        error_facts = db.query(models.Fact).filter(models.Fact.status == "error").count()
        valid_facts = db.query(models.Fact).filter(models.Fact.status == "valid").count()
        
        # Metrics stats
        total_metrics = db.query(models.Metric).count()
        valid_metrics = db.query(models.Metric).filter(models.Metric.status == "valid").count()
        
        # Dashboards stats
        total_dashboards = db.query(models.Dashboard).count()
        
        # Warehouse stats (DuckDB)
        warehouse_stats = {"tables": 0, "total_rows": 0, "by_type": {}}
        try:
            duckdb_conn = get_duckdb()
            result = duckdb_conn.execute("SHOW TABLES").fetchall()
            warehouse_stats["tables"] = len(result)
            
            by_type = {"raw": 0, "staging": 0, "dimension": 0, "fact": 0, "other": 0}
            total_rows = 0
            
            for row in result:
                table_name = row[0]
                try:
                    count_result = duckdb_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
                    row_count = count_result[0] if count_result else 0
                    total_rows += row_count
                    
                    if table_name.startswith('raw_'):
                        by_type["raw"] += 1
                    elif table_name.startswith('stg_'):
                        by_type["staging"] += 1
                    elif table_name.startswith('dim_'):
                        by_type["dimension"] += 1
                    elif table_name.startswith('fato_'):
                        by_type["fact"] += 1
                    else:
                        by_type["other"] += 1
                except:
                    pass
            
            warehouse_stats["total_rows"] = total_rows
            warehouse_stats["by_type"] = by_type
        except:
            pass
        
        # Recent executions
        recent_executions = db.query(models.ExecutionLog).order_by(
            models.ExecutionLog.created_at.desc()
        ).limit(10).all()
        
        recent = []
        for exec_log in recent_executions:
            recent.append({
                "id": exec_log.id,
                "execution_id": exec_log.execution_id,
                "resource_type": exec_log.resource_type,
                "resource_name": exec_log.resource_name,
                "status": exec_log.status,
                "started_at": exec_log.started_at.isoformat() if exec_log.started_at else None,
                "duration_ms": exec_log.duration_ms,
                "rows_affected": exec_log.rows_affected,
                "error_message": exec_log.error_message
            })
        
        return {
            "sources": {
                "total": total_sources,
                "valid": valid_sources,
                "invalid": invalid_sources
            },
            "ingestions": {
                "total": total_ingestions,
                "running": running_ingestions,
                "error": error_ingestions,
                "valid": valid_ingestions,
                "total_rows_ingested": total_rows_ingested
            },
            "stagings": {
                "total": total_stagings,
                "running": running_stagings,
                "error": error_stagings,
                "valid": valid_stagings
            },
            "dimensions": {
                "total": total_dimensions,
                "running": running_dimensions,
                "error": error_dimensions,
                "valid": valid_dimensions
            },
            "facts": {
                "total": total_facts,
                "running": running_facts,
                "error": error_facts,
                "valid": valid_facts
            },
            "metrics": {
                "total": total_metrics,
                "valid": valid_metrics
            },
            "dashboards": {
                "total": total_dashboards
            },
            "warehouse": warehouse_stats,
            "recent_executions": recent
        }
    except Exception as e:
        import traceback
        print(f"Error in get_overview: {str(e)}")
        print(traceback.format_exc())
        return {
            "sources": {"total": 0, "valid": 0, "invalid": 0},
            "ingestions": {"total": 0, "running": 0, "error": 0, "valid": 0, "total_rows_ingested": 0},
            "stagings": {"total": 0, "running": 0, "error": 0, "valid": 0},
            "dimensions": {"total": 0, "running": 0, "error": 0, "valid": 0},
            "facts": {"total": 0, "running": 0, "error": 0, "valid": 0},
            "metrics": {"total": 0, "valid": 0},
            "dashboards": {"total": 0},
            "warehouse": {"tables": 0, "total_rows": 0, "by_type": {}},
            "recent_executions": []
        }