from typing import Dict, Any
from .base import BaseConnector
from .postgres import PostgreSQLConnector
from .mysql import MySQLConnector
from .csv_connector import CSVConnector
from .excel import ExcelConnector
from .json import JSONConnector
from .google_sheets import GoogleSheetsConnector
from .xml import XMLConnector
from .parquet import ParquetConnector
from .avro import AvroConnector
from .orc import ORCConnector
from .sql_file import SQLFileConnector
from .delta_lake import DeltaLakeConnector


def get_connector(source_type: str, config: Dict[str, Any]) -> BaseConnector:
    """Factory para criar conectores baseado no tipo"""
    connectors = {
        'postgres': PostgreSQLConnector,
        'mysql': MySQLConnector,
        'csv': CSVConnector,
        'excel': ExcelConnector,
        'json': JSONConnector,
        'google_sheets': GoogleSheetsConnector,
        'xml': XMLConnector,
        'parquet': ParquetConnector,
        'avro': AvroConnector,
        'orc': ORCConnector,
        'sql_file': SQLFileConnector,
        'delta_lake': DeltaLakeConnector,
    }
    
    connector_class = connectors.get(source_type)
    if connector_class is None:
        raise ValueError(f"Tipo de conector não suportado: {source_type}")
    
    return connector_class(config)
