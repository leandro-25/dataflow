import json
import pandas as pd
from typing import Dict, Any, List
from .base import BaseConnector


class JSONConnector(BaseConnector):
    """Conector para arquivos JSON"""
    
    def _get_file_path(self) -> str:
        return self.config.get('file_path', '')
    
    def _get_orientation(self) -> str:
        """Orientação dos dados: records (array de objetos) ou columns (objeto com arrays)"""
        return self.config.get('orientation', 'records')
    
    def _get_json_path(self) -> str:
        """Caminho dentro do JSON para extrair dados (ex: data.items)"""
        return self.config.get('json_path', '')
    
    def test_connection(self) -> tuple[bool, str]:
        try:
            import os
            file_path = self._get_file_path()
            
            if not file_path:
                return False, "Caminho do arquivo não configurado"
            
            if not os.path.exists(file_path):
                return False, f"Arquivo não encontrado: {file_path}"
            
            # Try to parse JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate it's a list or dict
            if not isinstance(data, (list, dict)):
                return False, "JSON deve ser um array ou objeto"
            
            # If it's a list, check if it has objects
            if isinstance(data, list) and len(data) > 0:
                if not isinstance(data[0], dict):
                    return False, "Array JSON deve conter objetos"
                return True, f"JSON válido: {len(data)} registros, {len(data[0])} campos"
            
            return True, f"JSON válido: objeto com {len(data)} campos"
            
        except json.JSONDecodeError as e:
            return False, f"JSON inválido: {str(e)}"
        except Exception as e:
            return False, str(e)
    
    def list_tables(self) -> List[str]:
        """JSON não tem tabelas, retorna o nome do arquivo"""
        import os
        file_path = self._get_file_path()
        return [os.path.basename(file_path)]
    
    def _extract_data(self, data: Any, path: str = '') -> Any:
        """Extrai dados de um caminho específico no JSON"""
        if not path:
            return data
        
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, list) and key.isdigit():
                idx = int(key)
                if idx < len(current):
                    current = current[idx]
                else:
                    return None
            else:
                return None
        
        return current
    
    def get_schema(self, table: str = None) -> List[Dict[str, Any]]:
        file_path = self._get_file_path()
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract data from path if configured
        json_path = self._get_json_path()
        if json_path:
            data = self._extract_data(data, json_path)
        
        # Normalize to DataFrame
        if isinstance(data, list) and len(data) > 0:
            df = pd.json_normalize(data)
        elif isinstance(data, dict):
            # Try to convert dict to DataFrame
            df = pd.json_normalize([data])
        else:
            return []
        
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
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract data from path if configured
        json_path = self._get_json_path()
        if json_path:
            data = self._extract_data(data, json_path)
        
        # Convert to DataFrame
        if isinstance(data, list):
            return pd.json_normalize(data)
        elif isinstance(data, dict):
            return pd.json_normalize([data])
        else:
            return pd.DataFrame()
    
    def extract_sample(self, query_or_table: str = None, is_query: bool = False, limit: int = 100) -> pd.DataFrame:
        df = self.extract(query_or_table, is_query)
        return df.head(limit)
