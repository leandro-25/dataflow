import pandas as pd
from typing import Dict, Any, List
from .base import BaseConnector


class CSVConnector(BaseConnector):
    def _get_file_path(self) -> str:
        return self.config.get('file_path', '')
    
    def _get_pandas_params(self) -> Dict[str, Any]:
        return {
            'delimiter': self.config.get('delimiter', ','),
            'encoding': self.config.get('encoding', 'utf-8'),
            'header': 0 if self.config.get('has_header', True) else None,
            'low_memory': False,
        }
    
    def test_connection(self) -> tuple[bool, str]:
        try:
            import os
            file_path = self._get_file_path()
            
            if not file_path:
                return False, "Caminho do arquivo não configurado"
            
            if file_path.startswith('http://') or file_path.startswith('https://'):
                # Test HTTP connection
                import requests
                response = requests.head(file_path, timeout=10)
                if response.status_code == 200:
                    return True, f"Arquivo acessível: {file_path}"
                else:
                    return False, f"Erro HTTP {response.status_code}"
            else:
                # Local file
                if not os.path.exists(file_path):
                    return False, f"Arquivo não encontrado: {file_path}"
                
                # Try to read first few lines
                df = pd.read_csv(file_path, nrows=5, **self._get_pandas_params())
                return True, f"CSV válido: {len(df.columns)} colunas detectadas"
                
        except Exception as e:
            return False, str(e)
    
    def list_tables(self) -> List[str]:
        # CSV doesn't have tables, return the file name
        file_path = self._get_file_path()
        import os
        return [os.path.basename(file_path)] if file_path else []
    
    def get_schema(self, table: str = None) -> List[Dict[str, Any]]:
        import os
        file_path = self._get_file_path()
        
        if not file_path:
            raise ValueError("Caminho do arquivo não configurado na fonte")
        
        if not os.path.exists(file_path):
            raise ValueError(f"Arquivo não encontrado: {file_path}")
        
        try:
            df = pd.read_csv(file_path, nrows=1000, **self._get_pandas_params())
        except Exception as e:
            raise ValueError(f"Erro ao ler arquivo CSV: {str(e)}")
        
        if len(df.columns) == 0:
            raise ValueError("Arquivo CSV não tem colunas ou está vazio")
        
        columns = []
        for col in df.columns:
            dtype = df[col].dtype
            if pd.api.types.is_integer_dtype(dtype):
                pg_type = 'integer'
            elif pd.api.types.is_float_dtype(dtype):
                pg_type = 'double precision'
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                pg_type = 'timestamp'
            elif pd.api.types.is_bool_dtype(dtype):
                pg_type = 'boolean'
            else:
                pg_type = 'text'
            
            columns.append({
                'name': str(col),
                'type': pg_type,
                'nullable': bool(df[col].isna().any())
            })
        
        return columns
    
    def extract(self, query_or_table: str = None, is_query: bool = False) -> pd.DataFrame:
        file_path = self._get_file_path()
        return pd.read_csv(file_path, **self._get_pandas_params())
