import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from croniter import croniter
from sqlalchemy.orm import Session
from database import get_db, SessionLocal, get_duckdb
import models
from api import ingestions as ingestions_api
from api import staging as staging_api
from api import dimensions as dimensions_api
from api import facts as facts_api

class Scheduler:
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.running = False
    
    def start(self):
        """Inicia o scheduler"""
        if not self.running:
            self.running = True
            asyncio.create_task(self._run_scheduler())
    
    def stop(self):
        """Para o scheduler"""
        self.running = False
        for task in self.tasks.values():
            task.cancel()
        self.tasks.clear()
    
    async def _run_scheduler(self):
        """Loop principal do scheduler"""
        while self.running:
            try:
                db = SessionLocal()
                await self._check_schedules(db)
                db.close()
                await asyncio.sleep(10)  # Verifica a cada 10 segundos
            except Exception as e:
                print(f"Erro no scheduler: {e}")
                await asyncio.sleep(10)
    
    async def _check_schedules(self, db: Session):
        """Verifica e executa tarefas agendadas"""
        now = datetime.now()

        # Executa ingestões enfileiradas via run-async
        queued = db.query(models.Ingestion).filter(
            models.Ingestion.status == 'queued'
        ).all()

        for ingestion in queued:
            ingestion.status = 'running'
            db.commit()
            asyncio.create_task(self._run_ingestion_with_tracking(ingestion.id))

        # Verifica ingestões agendadas
        ingestions = db.query(models.Ingestion).filter(
            models.Ingestion.schedule.isnot(None),
            models.Ingestion.status != 'running'
        ).all()
        
        for ingestion in ingestions:
            if self._should_run(ingestion.schedule, now):
                # Verificar se há transformações complexas que requerem SQL push-down
                has_transforms = bool(ingestion.filters or (ingestion.column_mapping or {}))
                asyncio.create_task(self._run_ingestion_with_tracking(ingestion.id, has_transforms=has_transforms))
        
        # Verifica stagings
        stagings = db.query(models.Staging).filter(
            models.Staging.schedule.isnot(None),
            models.Staging.status != 'running'
        ).all()
        
        for staging in stagings:
            if self._should_run(staging.schedule, now):
                asyncio.create_task(self._run_staging_with_tracking(staging.id))
    
    def _should_run(self, schedule: str, now: datetime) -> bool:
        """Verifica se uma tarefa deve ser executada baseada no cron"""
        try:
            itr = croniter(schedule, now - timedelta(minutes=1))
            next_run = itr.get_next(datetime)
            return now >= next_run and now < next_run + timedelta(minutes=1)
        except:
            return False
    
    async def _run_ingestion_with_tracking(self, ingestion_id: str, has_transforms: bool = False):
        """Executa uma ingestão com tracking de progresso aprimorado"""
        db = SessionLocal()
        ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
        if not ingestion:
            return
        ingestion.status = "running"
        ingestion.current_execution_id = str(uuid.uuid4())
        db.commit()
        
        try:
            # run_ingestion é síncrona - executar em thread para não bloquear o loop
            await asyncio.to_thread(ingestions_api.run_ingestion, ingestion_id, db)
        except Exception as e:
            print(f"Erro ao executar ingestão {ingestion_id}: {e}")
            # Marcar como error no banco
            inv = db.query(models.Ingestion).filter(models.Ingestion.id == ingestion_id).first()
            if inv:
                inv.status = "error"
                db.commit()
        finally:
            db.close()
    
    async def _run_staging_with_tracking(self, staging_id: str):
        """Executa um staging com tracking de progresso"""
        db = SessionLocal()
        try:
            await asyncio.to_thread(staging_api.run_staging, staging_id, db)
        except Exception as e:
            print(f"Erro ao executar staging {staging_id}: {e}")
        finally:
            db.close()
    
    def add_job(self, job_id: str, schedule: str):
        """Adiciona um novo job ao scheduler"""
        pass  # Os jobs são lidos do banco automaticamente
    
    def remove_job(self, job_id: str):
        """Remove um job do scheduler"""
        pass  # Os jobs são lidos do banco automaticamente

# Instância global do scheduler
scheduler = Scheduler()
