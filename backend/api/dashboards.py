import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas

router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])

@router.get("", response_model=List[schemas.DashboardResponse])
def list_dashboards(db: Session = Depends(get_db)):
    return db.query(models.Dashboard).all()

@router.post("", response_model=schemas.DashboardResponse)
def create_dashboard(dashboard: schemas.DashboardCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Dashboard).filter(models.Dashboard.name == dashboard.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Dashboard name already exists")
    
    db_dashboard = models.Dashboard(
        id=str(uuid.uuid4()),
        name=dashboard.name,
        title=dashboard.title,
        description=dashboard.description,
        filters=dashboard.filters,
        layout=dashboard.layout,
        refresh_interval=dashboard.refresh_interval,
        status=dashboard.status
    )
    db.add(db_dashboard)
    db.commit()
    db.refresh(db_dashboard)
    return db_dashboard

@router.get("/{dashboard_id}", response_model=schemas.DashboardResponse)
def get_dashboard(dashboard_id: str, db: Session = Depends(get_db)):
    dashboard = db.query(models.Dashboard).filter(models.Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return dashboard

@router.put("/{dashboard_id}", response_model=schemas.DashboardResponse)
def update_dashboard(dashboard_id: str, dashboard_update: schemas.DashboardUpdate, db: Session = Depends(get_db)):
    dashboard = db.query(models.Dashboard).filter(models.Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    if dashboard_update.name and dashboard_update.name != dashboard.name:
        existing = db.query(models.Dashboard).filter(models.Dashboard.name == dashboard_update.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Dashboard name already exists")
    
    update_data = dashboard_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dashboard, field, value)
    
    db.commit()
    db.refresh(dashboard)
    return dashboard

@router.delete("/{dashboard_id}")
def delete_dashboard(dashboard_id: str, db: Session = Depends(get_db)):
    dashboard = db.query(models.Dashboard).filter(models.Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    db.delete(dashboard)
    db.commit()
    return {"message": "Dashboard deleted successfully"}

@router.get("/{dashboard_id}/data")
def get_dashboard_data(dashboard_id: str, db: Session = Depends(get_db)):
    dashboard = db.query(models.Dashboard).filter(models.Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    # Simplified - return layout with component placeholders
    return {"components": dashboard.layout}
