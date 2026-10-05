import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import duckdb
from config import get_settings

settings = get_settings()

# Ensure data directory exists
os.makedirs(os.path.dirname(os.path.abspath(settings.METADATA_DB_PATH)), exist_ok=True)

# SQLite connection for metadata
sqlite_url = f"sqlite:///{settings.METADATA_DB_PATH}"
engine = create_engine(
    sqlite_url,
    connect_args={"check_same_thread": False},
    echo=False
)

# Enable foreign keys for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# DuckDB connection for warehouse
_duckdb_conn = None

def get_duckdb():
    global _duckdb_conn
    if _duckdb_conn is None:
        _duckdb_conn = duckdb.connect(settings.WAREHOUSE_DB_PATH)
        # Aplicar limite de memória se configurado
        memory_limit = settings.DUCKDB_MEMORY_LIMIT
        if memory_limit:
            try:
                _duckdb_conn.execute(f"SET memory_limit='{memory_limit}'")
            except Exception:
                pass  # Ignorar se falhar (limite opcional)
    return _duckdb_conn

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
