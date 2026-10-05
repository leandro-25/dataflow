from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd


class BaseConnector(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """Testa se a conexão funciona. Retorna (sucesso, mensagem)"""
        pass
    
    @abstractmethod
    def list_tables(self) -> List[str]:
        """Lista tabelas/recursos disponíveis"""
        pass
    
    @abstractmethod
    def get_schema(self, table: str) -> List[Dict[str, Any]]:
        """Retorna schema de uma tabela: [{name, type, nullable}]"""
        pass
    
    @abstractmethod
    def extract(self, query_or_table: str, is_query: bool = False) -> pd.DataFrame:
        """Extrai dados e retorna DataFrame"""
        pass
    
    def extract_sample(self, query_or_table: str, is_query: bool = False, limit: int = 100) -> pd.DataFrame:
        """Extrai amostra de dados"""
        if is_query:
            modified_query = f"SELECT * FROM ({query_or_table}) AS t LIMIT {limit}"
            return self.extract(modified_query, True)
        else:
            return self.extract(f"SELECT * FROM {query_or_table} LIMIT {limit}", True)
