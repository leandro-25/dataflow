from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Database - caminhos absolutos ancorados na pasta do backend (imunes ao CWD)
    METADATA_DB_PATH: str = str(_BACKEND_DIR.parent / "data" / "metadata.db")
    WAREHOUSE_DB_PATH: str = str(_BACKEND_DIR.parent / "data" / "warehouse.duckdb")
    DUCKDB_MEMORY_LIMIT: str = "2GB"  # Limite de memória para DuckDB
    
    # Security
    SECRET_KEY: str = "dataflow-secret-key-change-in-production"
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings():
    return Settings()
