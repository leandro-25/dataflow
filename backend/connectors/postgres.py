import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from typing import Dict, Any, List
from .base import BaseConnector


class PostgreSQLConnector(BaseConnector):
    def _get_connection_params(self) -> Dict[str, Any]:
        return {
            'host': self.config.get('host', 'localhost'),
            'port': self.config.get('port', 5432),
            'database': self.config.get('database'),
            'user': self.config.get('user'),
            'password': self.config.get('password'),
            'sslmode': self.config.get('ssl', 'prefer'),
        }
    
    def test_connection(self) -> tuple[bool, str]:
        try:
            conn = psycopg2.connect(**self._get_connection_params())
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()
            conn.close()
            return True, f"PostgreSQL conectado: {version[0]}"
        except Exception as e:
            return False, str(e)
    
    def list_tables(self) -> List[str]:
        conn = psycopg2.connect(**self._get_connection_params())
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_type = 'BASE TABLE' 
            AND table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name
        """)
        tables = [f"{row[0]}.{row[1]}" for row in cursor.fetchall()]
        conn.close()
        return tables
    
    def get_schema(self, table: str) -> List[Dict[str, Any]]:
        conn = psycopg2.connect(**self._get_connection_params())
        cursor = conn.cursor()
        
        # Handle schema.table format
        if '.' in table:
            schema, table_name = table.split('.')
        else:
            schema, table_name = 'public', table
        
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, (schema, table_name))
        
        columns = [
            {
                'name': row[0],
                'type': row[1],
                'nullable': row[2] == 'YES'
            }
            for row in cursor.fetchall()
        ]
        conn.close()
        return columns
    
    def extract(self, query_or_table: str, is_query: bool = False) -> pd.DataFrame:
        conn = psycopg2.connect(**self._get_connection_params())
        
        if is_query:
            query = query_or_table
        else:
            query = f"SELECT * FROM {query_or_table}"
        
        df = pd.read_sql(query, conn)
        conn.close()
        return df
