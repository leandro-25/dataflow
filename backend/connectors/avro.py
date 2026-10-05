import pandas as pd
import fastavro
from typing import Dict, Any, List
from .base import BaseConnector


class AvroConnector(BaseConnector):
    def _get_file_path(self) -> str:
        return self.config.get('file_path', '')
    
    def test_connection(self) -> tuple[bool, str]:
        try:
            import os
            file_path = self._get_file_path()
            
            if not file_path:
                return False, "Caminho do arquivo não configurado"
            
            if file_path.startswith('http://') or file_path.startswith('https://'):
                return False, "URLs HTTP não suportadas para Avro"
            
            if not os.path.exists(file_path):
                return False, f"Arquivo não encontrado: {file_path}"
            
            # Read schema only
            with open(file_path, 'rb') as f:
                avro_reader = fastavro.reader(f)
                schema = avro_reader.schema
                # Count records
                count = sum(1 for _ in fastavro.reader(open(file_path, 'rb')))
            
            fields = schema.get('fields', [])
            return True, f"Avro válido: {len(fields)} campos, {count} registros"
                
        except Exception as e:
            return False, str(e)
    
    def list_tables(self) -> List[str]:
        file_path = self._get_file_path()
        import os
        return [os.path.basename(file_path)] if file_path else []
    
    def get_schema(self, table: str = None) -> List[Dict[str, Any]]:
        file_path = self._get_file_path()
        
        with open(file_path, 'rb') as f:
            avro_reader = fastavro.reader(f)
            schema = avro_reader.schema
        
        columns = []
        for field in schema.get('fields', []):
            field_type = field['type']
            
            # Handle union types (e.g., ["null", "string"])
            if isinstance(field_type, list):
                # Remove null from union
                non_null_types = [t for t in field_type if t != 'null']
                if non_null_types:
                    field_type = non_null_types[0]
                else:
                    field_type = 'null'
            
            # Map Avro types
            type_mapping = {
                'null': 'text',
                'boolean': 'boolean',
                'int': 'integer',
                'long': 'bigint',
                'float': 'float',
                'double': 'double precision',
                'bytes': 'bytea',
                'string': 'text',
            }
            
            pg_type = type_mapping.get(field_type, 'text')
            
            columns.append({
                'name': field['name'],
                'type': pg_type,
                'nullable': True  # Avro fields are nullable by default
            })
        
        return columns
    
    def extract(self, query_or_table: str = None, is_query: bool = False) -> pd.DataFrame:
        file_path = self._get_file_path()
        
        records = []
        with open(file_path, 'rb') as f:
            avro_reader = fastavro.reader(f)
            for record in avro_reader:
                records.append(record)
        
        return pd.DataFrame(records)
