import copy
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
from connectors.factory import get_connector

router = APIRouter(prefix="/api/sources", tags=["sources"])

# Campos com segredo que nunca devem voltar abertos nas respostas da API
CAMPOS_SECRETOS = ("password", "target_password", "credentials")
MASCARA = "__MASKED__"


def _mascarar_config(config: dict) -> dict:
    """Copia a config substituindo segredos pela mascara."""
    cfg = copy.deepcopy(config or {})
    for k in CAMPOS_SECRETOS:
        if cfg.get(k):
            cfg[k] = MASCARA
    return cfg


def _resposta(source: models.Source) -> schemas.SourceResponse:
    """Serializa a source com credenciais mascaradas."""
    resp = schemas.SourceResponse.model_validate(source)
    resp.config = _mascarar_config(resp.config)
    return resp


def _mesclar_segredos(nova_config: dict, atual_config: dict | None) -> dict:
    """Ao atualizar, preserva o segredo salvo quando chega vazio ou mascarado."""
    cfg = copy.deepcopy(nova_config or {})
    for k in CAMPOS_SECRETOS:
        valor = cfg.get(k)
        veio_vazio = valor is None or valor == "" or valor == MASCARA or valor == {}
        if veio_vazio and atual_config and atual_config.get(k):
            cfg[k] = atual_config[k]
    return cfg


@router.get("", response_model=List[schemas.SourceResponse])
def list_sources(db: Session = Depends(get_db)):
    sources = db.query(models.Source).all()
    return [_resposta(s) for s in sources]


@router.post("/validate", response_model=schemas.SourceTestConnection)
def validate_source(payload: dict, db: Session = Depends(get_db)):
    """Testa uma conexao ANTES de salvar (dry-run, nao persiste nada)."""
    tipo = payload.get("type")
    config = payload.get("config") or {}
    try:
        connector = get_connector(tipo, config)
        sucesso, msg = connector.test_connection()
        tabelas = []
        if sucesso:
            try:
                tabelas = connector.list_tables()
            except Exception:
                pass
        return schemas.SourceTestConnection(success=sucesso, message=msg, tables=tabelas)
    except HTTPException:
        raise
    except ValueError as e:
        return schemas.SourceTestConnection(success=False, message=str(e), tables=[])
    except Exception as e:
        return schemas.SourceTestConnection(success=False, message=str(e), tables=[])


@router.post("", response_model=schemas.SourceResponse)
def create_source(source: schemas.SourceCreate, db: Session = Depends(get_db)):
    # Check if name already exists
    existing = db.query(models.Source).filter(models.Source.name == source.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Source name already exists")

    db_source = models.Source(
        id=str(uuid.uuid4()),
        name=source.name,
        type=source.type,
        config=source.config,
        status=source.status or "valid"
    )
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return _resposta(db_source)


@router.get("/{source_id}", response_model=schemas.SourceResponse)
def get_source(source_id: str, db: Session = Depends(get_db)):
    source = db.query(models.Source).filter(models.Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return _resposta(source)


@router.put("/{source_id}", response_model=schemas.SourceResponse)
def update_source(source_id: str, source_update: schemas.SourceUpdate, db: Session = Depends(get_db)):
    source = db.query(models.Source).filter(models.Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Check name uniqueness if updating name
    if source_update.name and source_update.name != source.name:
        existing = db.query(models.Source).filter(models.Source.name == source_update.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Source name already exists")

    # Update fields
    update_data = source_update.model_dump(exclude_unset=True)

    if "config" in update_data and update_data["config"] is not None:
        update_data["config"] = _mesclar_segredos(update_data["config"], source.config)

    for field, value in update_data.items():
        setattr(source, field, value)

    db.commit()
    db.refresh(source)
    return _resposta(source)


@router.delete("/{source_id}")
def delete_source(source_id: str, db: Session = Depends(get_db)):
    source = db.query(models.Source).filter(models.Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    dependentes = db.query(models.Ingestion).filter(models.Ingestion.source_id == source_id).count()
    if dependentes > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Esta fonte possui {dependentes} ingestao(oes) vinculada(s). Remova-as primeiro."
        )

    db.delete(source)
    db.commit()
    return {"message": "Source deleted successfully"}


@router.post("/{source_id}/test", response_model=schemas.SourceTestConnection)
def test_connection(source_id: str, db: Session = Depends(get_db)):
    source = db.query(models.Source).filter(models.Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    try:
        connector = get_connector(source.type, source.config)
        success, message = connector.test_connection()

        tables = []
        if success:
            try:
                tables = connector.list_tables()
            except Exception:
                pass

        return schemas.SourceTestConnection(
            success=success,
            message=message,
            tables=tables
        )
    except Exception as e:
        return schemas.SourceTestConnection(
            success=False,
            message=str(e),
            tables=[]
        )


@router.get("/{source_id}/tables")
def list_tables(source_id: str, db: Session = Depends(get_db)):
    source = db.query(models.Source).filter(models.Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    try:
        connector = get_connector(source.type, source.config)
        tables = connector.list_tables()
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{source_id}/schema/{table}")
def get_schema(source_id: str, table: str, db: Session = Depends(get_db)):
    source = db.query(models.Source).filter(models.Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    print(f"Getting schema for source {source_id} (type: {source.type}), table: {table}")

    try:
        connector = get_connector(source.type, source.config)
        schema = connector.get_schema(table)
        return {"schema": schema}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))
