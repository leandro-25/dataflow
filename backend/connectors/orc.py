import pandas as pd
from typing import Dict, Any, List
from .base import BaseConnector


class ORCConnector(BaseConnector):
    def _get_file_path(self) -> str:
        return self.config.get('file_path', '')
    
    def _get_columns(self) -> List[str]:
        cols = self.config.get('columns', '')
        if cols:
            return [c.strip() for c in cols.split(',')]
        return None
    
    def test_connection(self) -> tuple[bool, str]:
        try:
            import os
            file_path = self._get_file_path()
            
            if not file_path:
                return False, "Caminho do arquivo não configurado"
            
            if file_path.startswith('http://') or file_path.startswith('https://'):
                return False, "URLs HTTP não suportadas para ORC"
            
            if not os.path.exists(file_path):
                return False, f"Arquivo não encontrado: {file_path}"
            
            # Read metadata
            import pyarrow.orc as orc
            orc_file = orc.ORCFile(file_path)
            nrows = orc_file.nrows
            schema = orc_file.schema
            
            return True, f"ORC válido: {len(schema.names)} colunas, {nrows} linhas"
                
        except Exception as e:
            return False, str(e)
    
    def list_tables(self) -> List[str]:
        file_path = self._get_file_path()
        import os
        return [os.path.basename(file_path)] if file_path else []
    
    def get_schema(self, table: str = None) -> List[Dict[str, Any]]:
        file_path = self._get_file_path()
        
        import pyarrow.orc as orc
        orc_file = orc.ORCFile(file_path)
        schema = orc_file.schema
        
        columns = []
        for i, name in enumerate(schema.names):
            field = schema.field(i)
            pa_type = field.type
            
            # Map pyarrow types
            import pyarrow as pa
            if pa.types.is_integer(pa_type):
                pg_type = 'integer'
            elif pa.types.is_floating(pa_type):
                pg_type = 'double precision'
            elif pa.types.is_timestamp(pa_type):
                pg_type = 'timestamp'
            elif pa.types.is_boolean(pa_type):
                pg_type = 'boolean'
            else:
                pg_type = 'text'
            
            columns.append({
                'name': name,
                'type': pg_type,
                'nullable': True
            })
        
        return columns
    
    def extract(self, query_or_table: str = None, is_query: bool = False) -> pd.DataFrame:
        file_path = self._get_file_path()
        columns = self._get_columns()
        
        import pyarrow.orc as orc
        orc_file = orc.ORCFile(file_path)
        table = orc_file.read()
        df = table.to_pandas()
        
        if columns:
            df = df[columns]
        
        return df
