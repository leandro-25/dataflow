import pandas as pd
from typing import Dict, Any, List
from .base import BaseConnector


class ExcelConnector(BaseConnector):
    def _get_file_path(self) -> str:
        return self.config.get('file_path', '')
    
    def _get_sheet_name(self) -> str:
        return self.config.get('sheet_name', 0)
    
    def test_connection(self) -> tuple[bool, str]:
        try:
            import os
            file_path = self._get_file_path()
            
            if not file_path:
                return False, "Caminho do arquivo não configurado"
            
            if not os.path.exists(file_path):
                return False, f"Arquivo não encontrado: {file_path}"
            
            # Try to read first few rows
            df = pd.read_excel(file_path, sheet_name=self._get_sheet_name(), nrows=5)
            sheets = pd.ExcelFile(file_path).sheet_names
            return True, f"Excel válido: {len(df.columns)} colunas, {len(sheets)} abas"
            
        except Exception as e:
            return False, str(e)
    
    def list_tables(self) -> List[str]:
        file_path = self._get_file_path()
        xl = pd.ExcelFile(file_path)
        return xl.sheet_names
    
    def get_schema(self, table: str = None) -> List[Dict[str, Any]]:
        file_path = self._get_file_path()
        
        sheet = table if table else self._get_sheet_name()
        # Only treat as sheet name if it exists in the file
        try:
            sheets = pd.ExcelFile(file_path).sheet_names
            if sheet not in sheets:
                sheet = self._get_sheet_name()
        except Exception:
            pass
        
        df = pd.read_excel(file_path, sheet_name=sheet, nrows=1000)
        
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
        sheet = self._get_sheet_name()
        
        if query_or_table and not is_query:
            # Only treat as sheet name if it exists in the file
            try:
                sheets = pd.ExcelFile(file_path).sheet_names
                if query_or_table in sheets:
                    sheet = query_or_table
            except Exception:
                pass
        
        return pd.read_excel(file_path, sheet_name=sheet)
