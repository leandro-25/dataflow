import pandas as pd
import duckdb
from typing import Dict, Any, List
from .base import BaseConnector


class SQLFileConnector(BaseConnector):
    """Conector para arquivos SQL - extrai resultados de queries armazenadas em arquivos"""
    
    def _get_file_path(self) -> str:
        return self.config.get('file_path', '')
    
    def _get_target_connection(self) -> Dict[str, Any]:
        """Retorna configuração de conexão do banco alvo para executar a query"""
        return {
            'type': self.config.get('target_type', 'duckdb'),
            'host': self.config.get('target_host', ''),
            'port': self.config.get('target_port', ''),
            'database': self.config.get('target_database', ''),
            'username': self.config.get('target_username', ''),
            'password': self.config.get('target_password', ''),
        }
    
    def test_connection(self) -> tuple[bool, str]:
        try:
            import os
            file_path = self._get_file_path()
            
            if not file_path:
                return False, "Caminho do arquivo não configurado"
            
            if not os.path.exists(file_path):
                return False, f"Arquivo não encontrado: {file_path}"
            
            # Read and validate SQL
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            if not sql_content.strip():
                return False, "Arquivo SQL está vazio"
            
            # Check if it's a SELECT statement
            sql_upper = sql_content.strip().upper()
            if not sql_upper.startswith('SELECT'):
                return False, "O arquivo deve conter uma query SELECT"
            
            return True, f"SQL válido: {len(sql_content)} caracteres"
                
        except Exception as e:
            return False, str(e)
    
    def list_tables(self) -> List[str]:
        file_path = self._get_file_path()
        import os
        return [os.path.basename(file_path)] if file_path else []
    
    def get_schema(self, table: str = None) -> List[Dict[str, Any]]:
        # Execute query and get schema from result
        df = self.extract_sample(None, is_query=False, limit=1)
        
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
                'nullable': True
            })
        
        return columns
    
    def extract(self, query_or_table: str = None, is_query: bool = False) -> pd.DataFrame:
        file_path = self._get_file_path()
        
        # Read SQL from file
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_query = f.read()
        
        # Get target connection
        target_config = self._get_target_connection()
        target_type = target_config['type']
        
        if target_type == 'duckdb':
            # Use local DuckDB
            conn = duckdb.connect(':memory:')
            result = conn.execute(sql_query).fetchdf()
            conn.close()
            return result
        elif target_type == 'postgres':
            import psycopg2
            conn_str = f"host={target_config['host']} port={target_config['port']} dbname={target_config['database']} user={target_config['username']} password={target_config['password']}"
            conn = psycopg2.connect(conn_str)
            return pd.read_sql(sql_query, conn)
        elif target_type == 'mysql':
            import pymysql
            conn = pymysql.connect(
                host=target_config['host'],
                port=int(target_config['port'] or 3306),
                database=target_config['database'],
                user=target_config['username'],
                password=target_config['password']
            )
            return pd.read_sql(sql_query, conn)
        else:
            raise ValueError(f"Tipo de conexão alvo não suportado: {target_type}")
