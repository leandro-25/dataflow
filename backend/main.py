from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import get_settings
from database import engine, Base
from api import sources, ingestions, staging, dimensions, facts, metrics, dashboards, execution, catalog, overview, filesystem
from engine.scheduler import scheduler

settings = get_settings()

# Create tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Iniciando scheduler...")
    scheduler.start()
    yield
    # Shutdown
    print("Parando scheduler...")
    scheduler.stop()

app = FastAPI(
    title="Dataflow API",
    description="API for Dataflow - Local Data Pipeline System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sources.router)
app.include_router(ingestions.router)
app.include_router(staging.router)
app.include_router(dimensions.router)
app.include_router(facts.router)
app.include_router(metrics.router)
app.include_router(dashboards.router)
app.include_router(execution.router)
app.include_router(catalog.router)
app.include_router(overview.router)
app.include_router(filesystem.router)

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
