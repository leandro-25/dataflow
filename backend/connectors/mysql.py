import pymysql
import pandas as pd
from typing import Dict, Any, List
from .base import BaseConnector


class MySQLConnector(BaseConnector):
    def _get_connection_params(self) -> Dict[str, Any]:
        return {
            'host': self.config.get('host', 'localhost'),
            'port': self.config.get('port', 3306),
            'database': self.config.get('database'),
            'user': self.config.get('user'),
            'password': self.config.get('password'),
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor,
        }
    
    def test_connection(self) -> tuple[bool, str]:
        try:
            conn = pymysql.connect(**self._get_connection_params())
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            conn.close()
            return True, f"MySQL conectado: {version['VERSION()'] if isinstance(version, dict) else version[0]}"
        except Exception as e:
            return False, str(e)
    
    def list_tables(self) -> List[str]:
        conn = pymysql.connect(**self._get_connection_params())
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [list(row.values())[0] if isinstance(row, dict) else row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    
    def get_schema(self, table: str) -> List[Dict[str, Any]]:
        conn = pymysql.connect(**self._get_connection_params())
        cursor = conn.cursor()
        cursor.execute(f"DESCRIBE {table}")
        columns = []
        for row in cursor.fetchall():
            if isinstance(row, dict):
                columns.append({
                    'name': row['Field'],
                    'type': row['Type'],
                    'nullable': row['Null'] == 'YES'
                })
            else:
                columns.append({
                    'name': row[0],
                    'type': row[1],
                    'nullable': row[2] == 'YES'
                })
        conn.close()
        return columns
    
    def extract(self, query_or_table: str, is_query: bool = False) -> pd.DataFrame:
        conn = pymysql.connect(**self._get_connection_params())
        
        if is_query:
            query = query_or_table
        else:
            query = f"SELECT * FROM {query_or_table}"
        
        df = pd.read_sql(query, conn)
        conn.close()
        return df
