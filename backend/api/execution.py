import networkx as nx
import uuid
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, get_duckdb
import models
from api import sources as sources_api
from api import ingestions as ingestions_api
from api import staging as staging_api
from api import dimensions as dimensions_api
from api import facts as facts_api

router = APIRouter(prefix="/api/execution", tags=["execution"])

def build_dag(db: Session) -> nx.DiGraph:
    """Constrói o DAG de dependências"""
    G = nx.DiGraph()
    
    # Adicionar nós
    for source in db.query(models.Source).all():
        G.add_node(f"source:{source.id}", type="source", name=source.name, id=source.id, status=source.status)
    
    for ingestion in db.query(models.Ingestion).all():
        G.add_node(f"ingestion:{ingestion.id}", type="ingestion", name=ingestion.name, id=ingestion.id, status=ingestion.status)
        # Ingestion depende da Source
        if ingestion.source_id:
            G.add_edge(f"source:{ingestion.source_id}", f"ingestion:{ingestion.id}")
    
    for staging in db.query(models.Staging).all():
        G.add_node(f"staging:{staging.id}", type="staging", name=staging.name, id=staging.id, status=staging.status)
        # Staging depende da tabela de origem (simplificado)
        source_ingestion = db.query(models.Ingestion).filter(
            models.Ingestion.config['target_table'].as_string() == staging.source_table
        ).first()
        if source_ingestion:
            G.add_edge(f"ingestion:{source_ingestion.id}", f"staging:{staging.id}")
    
    for dimension in db.query(models.Dimension).all():
        G.add_node(f"dimension:{dimension.id}", type="dimension", name=dimension.name, id=dimension.id, status=dimension.status)
        source_staging = db.query(models.Staging).filter(
            models.Staging.target_table == dimension.source_table
        ).first()
        if source_staging:
            G.add_edge(f"staging:{source_staging.id}", f"dimension:{dimension.id}")
    
    for fact in db.query(models.Fact).all():
        G.add_node(f"fact:{fact.id}", type="fact", name=fact.name, id=fact.id, status=fact.status)
        source_staging = db.query(models.Staging).filter(
            models.Staging.target_table == fact.source_table
        ).first()
        if source_staging:
            G.add_edge(f"staging:{source_staging.id}", f"fact:{fact.id}")
    
    return G

@router.get("/dag")
def get_dag(db: Session = Depends(get_db)):
    """Retorna o DAG atual para visualização"""
    try:
        G = build_dag(db)
        
        nodes = []
        for node_id, data in G.nodes(data=True):
            nodes.append({
                "id": node_id,
                "type": data.get("type"),
                "name": data.get("name"),
                "resource_id": data.get("id"),
                "status": data.get("status")
            })
        
        edges = []
        for source, target in G.edges():
            edges.append({"source": source, "target": target})
        
        return {"nodes": nodes, "edges": edges}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/run")
def run_pipeline(db: Session = Depends(get_db)):
    """Executa o pipeline completo em ordem topológica"""
    try:
        G = build_dag(db)
        
        # Verificar ciclos
        if not nx.is_directed_acyclic_graph(G):
            raise HTTPException(status_code=400, detail="Ciclo detectado no pipeline")
        
        # Ordenação topológica
        execution_order = list(nx.topological_sort(G))
        
        # Gerar ID único para esta execução
        execution_id = str(uuid.uuid4())
        
        results = []
        for node_id in execution_order:
            node_data = G.nodes[node_id]
            node_type = node_data.get("type")
            resource_id = node_data.get("id")
            resource_name = node_data.get("name")
            
            # Criar log de início
            log = models.ExecutionLog(
                id=str(uuid.uuid4()),
                execution_id=execution_id,
                resource_type=node_type,
                resource_id=resource_id,
                resource_name=resource_name,
                status="running"
            )
            db.add(log)
            db.commit()
            
            start_time = time.time()
            
            try:
                result = None
                if node_type == "ingestion":
                    result = ingestions_api.run_ingestion(resource_id, db)
                elif node_type == "staging":
                    result = staging_api.run_staging(resource_id, db)
                elif node_type == "dimension":
                    result = dimensions_api.run_dimension(resource_id, db)
                elif node_type == "fact":
                    result = facts_api.run_fact(resource_id, db)
                
                duration = int((time.time() - start_time) * 1000)
                
                # Atualizar log com sucesso
                log.status = "success"
                log.finished_at = datetime.now()
                log.duration_ms = duration
                log.rows_affected = result.get("rows_affected") if result else None
                db.commit()
                
                results.append({"node": node_id, "status": "success", "rows_affected": result.get("rows_affected") if result else None})
            except Exception as e:
                duration = int((time.time() - start_time) * 1000)
                
                # Atualizar log com erro
                log.status = "error"
                log.finished_at = datetime.now()
                log.duration_ms = duration
                log.error_message = str(e)
                db.commit()
                
                results.append({"node": node_id, "status": "error", "error": str(e)})
                break
        
        return {"success": True, "execution_id": execution_id, "results": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/run/{resource_type}/{resource_id}")
def run_from_resource(resource_type: str, resource_id: str, with_deps: bool = False, db: Session = Depends(get_db)):
    """Executa a partir de um recurso específico"""
    try:
        G = build_dag(db)
        
        if not nx.is_directed_acyclic_graph(G):
            raise HTTPException(status_code=400, detail="Ciclo detectado no pipeline")
        
        node_id = f"{resource_type}:{resource_id}"
        
        if node_id not in G:
            raise HTTPException(status_code=404, detail="Recurso não encontrado no DAG")
        
        execution_id = str(uuid.uuid4())
        
        if with_deps:
            # Incluir dependências e dependentes
            all_nodes = set()
            all_nodes.add(node_id)
            
            # Adicionar predecessores (dependências)
            for pred in nx.ancestors(G, node_id):
                all_nodes.add(pred)
            
            # Adicionar sucessores (dependentes)
            for succ in nx.descendants(G, node_id):
                all_nodes.add(succ)
            
            # Criar subgrafo
            subG = G.subgraph(all_nodes)
            execution_order = list(nx.topological_sort(subG))
        else:
            # Apenas o nó e seus dependentes
            execution_order = [node_id] + list(nx.descendants(G, node_id))
        
        results = []
        for exec_node_id in execution_order:
            node_data = G.nodes[exec_node_id]
            node_type = node_data.get("type")
            res_id = node_data.get("id")
            res_name = node_data.get("name")
            
            log = models.ExecutionLog(
                id=str(uuid.uuid4()),
                execution_id=execution_id,
                resource_type=node_type,
                resource_id=res_id,
                resource_name=res_name,
                status="running"
            )
            db.add(log)
            db.commit()
            
            start_time = time.time()
            
            try:
                result = None
                if node_type == "ingestion":
                    result = ingestions_api.run_ingestion(res_id, db)
                elif node_type == "staging":
                    result = staging_api.run_staging(res_id, db)
                elif node_type == "dimension":
                    result = dimensions_api.run_dimension(res_id, db)
                elif node_type == "fact":
                    result = facts_api.run_fact(res_id, db)
                
                duration = int((time.time() - start_time) * 1000)
                
                log.status = "success"
                log.finished_at = datetime.now()
                log.duration_ms = duration
                log.rows_affected = result.get("rows_affected") if result else None
                db.commit()
                
                results.append({"node": exec_node_id, "status": "success"})
            except Exception as e:
                duration = int((time.time() - start_time) * 1000)
                
                log.status = "error"
                log.finished_at = datetime.now()
                log.duration_ms = duration
                log.error_message = str(e)
                db.commit()
                
                results.append({"node": exec_node_id, "status": "error", "error": str(e)})
                break
        
        return {"success": True, "execution_id": execution_id, "results": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/logs")
def get_execution_logs(limit: int = 100, db: Session = Depends(get_db)):
    """Retorna logs de execução"""
    logs = db.query(models.ExecutionLog).order_by(models.ExecutionLog.created_at.desc()).limit(limit).all()
    return logs

@router.get("/logs/{execution_id}")
def get_execution_log(execution_id: str, db: Session = Depends(get_db)):
    """Retorna logs de uma execução específica"""
    logs = db.query(models.ExecutionLog).filter(models.ExecutionLog.execution_id == execution_id).order_by(models.ExecutionLog.started_at).all()
    if not logs:
        raise HTTPException(status_code=404, detail="Execution not found")
    return logs

@router.get("/status")
def get_execution_status(db: Session = Depends(get_db)):
    """Retorna status atual das execuções"""
    running = db.query(models.ExecutionLog).filter(models.ExecutionLog.status == "running").count()
    last_execution = db.query(models.ExecutionLog).order_by(models.ExecutionLog.created_at.desc()).first()
    
    return {
        "running_executions": running,
        "last_execution": {
            "id": last_execution.execution_id if last_execution else None,
            "started_at": last_execution.started_at if last_execution else None,
            "status": last_execution.status if last_execution else None
        } if last_execution else None
    }
