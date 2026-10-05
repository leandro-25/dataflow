import pandas as pd
import duckdb
from typing import Dict, Any, List
from .base import BaseConnector


class DeltaLakeConnector(BaseConnector):
    """Conector para Delta Lake usando duckdb-delta"""
    
    def _get_table_path(self) -> str:
        return self.config.get('table_path', '')
    
    def _get_storage_options(self) -> Dict[str, str]:
        """Retorna opções de storage para cloud (S3, Azure, GCS)"""
        options = {}
        
        # AWS S3
        if self.config.get('aws_access_key_id'):
            options['AWS_ACCESS_KEY_ID'] = self.config['aws_access_key_id']
        if self.config.get('aws_secret_access_key'):
            options['AWS_SECRET_ACCESS_KEY'] = self.config['aws_secret_access_key']
        if self.config.get('aws_region'):
            options['AWS_REGION'] = self.config['aws_region']
        
        # Azure
        if self.config.get('azure_storage_account_name'):
            options['AZURE_STORAGE_ACCOUNT_NAME'] = self.config['azure_storage_account_name']
        if self.config.get('azure_storage_account_key'):
            options['AZURE_STORAGE_ACCOUNT_KEY'] = self.config['azure_storage_account_key']
        
        # GCS
        if self.config.get('gcs_credentials'):
            options['GOOGLE_CREDENTIALS'] = self.config['gcs_credentials']
        
        return options
    
    def test_connection(self) -> tuple[bool, str]:
        try:
            import os
            table_path = self._get_table_path()
            
            if not table_path:
                return False, "Caminho da tabela Delta não configurado"
            
            # Initialize DuckDB with delta extension
            conn = duckdb.connect(':memory:')
            conn.execute("INSTALL delta;")
            conn.execute("LOAD delta;")
            
            storage_options = self._get_storage_options()
            
            # Try to read metadata
            try:
                result = conn.execute(f"""
                    SELECT * FROM delta_scan('{table_path}') LIMIT 1
                """).fetchdf()
                
                col_count = len(result.columns)
                return True, f"Delta Lake válido: {col_count} colunas detectadas"
            except Exception as e:
                return False, f"Erro ao ler Delta Lake: {str(e)}"
            finally:
                conn.close()
                
        except Exception as e:
            return False, str(e)
    
    def list_tables(self) -> List[str]:
        table_path = self._get_table_path()
        import os
        return [os.path.basename(table_path)] if table_path else []
    
    def get_schema(self, table: str = None) -> List[Dict[str, Any]]:
        table_path = self._get_table_path()
        
        conn = duckdb.connect(':memory:')
        conn.execute("INSTALL delta;")
        conn.execute("LOAD delta;")
        
        # Get schema information
        result = conn.execute(f"""
            DESCRIBE SELECT * FROM delta_scan('{table_path}')
        """).fetchdf()
        
        conn.close()
        
        columns = []
        for _, row in result.iterrows():
            col_name = row['column_name']
            col_type = row['column_type'].lower()
            
            # Map DuckDB types
            if 'int' in col_type:
                pg_type = 'integer'
            elif 'float' in col_type or 'double' in col_type or 'decimal' in col_type:
                pg_type = 'double precision'
            elif 'timestamp' in col_type or 'date' in col_type:
                pg_type = 'timestamp'
            elif 'boolean' in col_type or 'bool' in col_type:
                pg_type = 'boolean'
            else:
                pg_type = 'text'
            
            columns.append({
                'name': col_name,
                'type': pg_type,
                'nullable': True
            })
        
        return columns
    
    def extract(self, query_or_table: str = None, is_query: bool = False) -> pd.DataFrame:
        table_path = self._get_table_path()
        version = self.config.get('version')
        
        conn = duckdb.connect(':memory:')
        conn.execute("INSTALL delta;")
        conn.execute("LOAD delta;")
        
        # Build query with optional version
        if version:
            query = f"SELECT * FROM delta_scan('{table_path}', version={version})"
        else:
            query = f"SELECT * FROM delta_scan('{table_path}')"
        
        result = conn.execute(query).fetchdf()
        conn.close()
        
        return result
