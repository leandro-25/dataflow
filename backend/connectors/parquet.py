import pandas as pd
import pyarrow.types as pa_types
from typing import Dict, Any, List
from .base import BaseConnector


class ParquetConnector(BaseConnector):
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
                return False, "URLs HTTP não suportadas para Parquet"

            if not os.path.exists(file_path):
                return False, f"Arquivo não encontrado: {file_path}"

            import pyarrow.parquet as pq
            pf = pq.ParquetFile(file_path)
            schema = pf.schema_arrow
            num_rows = pf.metadata.num_rows

            return True, f"Parquet válido: {len(schema.names)} colunas, {num_rows} linhas"

        except Exception as e:
            return False, str(e)

    def list_tables(self) -> List[str]:
        file_path = self._get_file_path()
        import os
        return [os.path.basename(file_path)] if file_path else []

    def get_schema(self, table: str = None) -> List[Dict[str, Any]]:
        file_path = self._get_file_path()

        import pyarrow.parquet as pq
        pf = pq.ParquetFile(file_path)
        schema = pf.schema_arrow

        columns = []
        for i in range(len(schema)):
            field = schema.field(i)
            pa_type = field.type

            if pa_types.is_integer(pa_type):
                pg_type = 'integer'
            elif pa_types.is_floating(pa_type):
                pg_type = 'double precision'
            elif pa_types.is_timestamp(pa_type):
                pg_type = 'timestamp'
            elif pa_types.is_boolean(pa_type):
                pg_type = 'boolean'
            else:
                pg_type = 'text'

            columns.append({
                'name': field.name,
                'type': pg_type,
                'nullable': field.nullable
            })

        return columns

    def extract(self, query_or_table: str = None, is_query: bool = False) -> pd.DataFrame:
        file_path = self._get_file_path()
        columns = self._get_columns()

        return pd.read_parquet(file_path, columns=columns)
