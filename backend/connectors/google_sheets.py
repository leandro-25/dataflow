import pandas as pd
from typing import Dict, Any, List
from .base import BaseConnector


class GoogleSheetsConnector(BaseConnector):
    """Conector para Google Sheets"""
    
    def _get_spreadsheet_id(self) -> str:
        return self.config.get('spreadsheet_id', '')
    
    def _get_sheet_name(self) -> str:
        return self.config.get('sheet_name', 'Sheet1')
    
    def _get_credentials(self) -> Dict[str, Any]:
        return self.config.get('credentials', {})
    
    def _get_service(self):
        """Inicializa o serviço do Google Sheets"""
        try:
            from googleapiclient.discovery import build
            from google.oauth2 import service_account
            
            credentials_dict = self._get_credentials()
            
            if not credentials_dict:
                raise ValueError("Credenciais não configuradas")
            
            # Create credentials from dict
            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
            
            service = build('sheets', 'v4', credentials=credentials)
            return service
            
        except ImportError:
            raise ImportError("Bibliotecas do Google não instaladas. Execute: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    
    def test_connection(self) -> tuple[bool, str]:
        try:
            spreadsheet_id = self._get_spreadsheet_id()
            
            if not spreadsheet_id:
                return False, "ID da planilha não configurado"
            
            service = self._get_service()
            
            # Try to get spreadsheet info
            spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            
            sheets = spreadsheet.get('sheets', [])
            sheet_names = [s['properties']['title'] for s in sheets]
            
            return True, f"Google Sheets conectado: {len(sheets)} abas ({', '.join(sheet_names[:3])})"
            
        except Exception as e:
            return False, str(e)
    
    def list_tables(self) -> List[str]:
        """Retorna nomes das abas"""
        spreadsheet_id = self._get_spreadsheet_id()
        service = self._get_service()
        
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = spreadsheet.get('sheets', [])
        
        return [s['properties']['title'] for s in sheets]
    
    def get_schema(self, table: str = None) -> List[Dict[str, Any]]:
        spreadsheet_id = self._get_spreadsheet_id()
        sheet_name = table if table else self._get_sheet_name()
        service = self._get_service()
        
        # Get first 1000 rows to infer schema
        range_name = f"{sheet_name}!A1:Z1000"
        
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if not values or len(values) < 1:
            return []
        
        # First row is header
        headers = values[0]
        
        # Analyze data types from second row onwards
        columns = []
        for idx, header in enumerate(headers):
            col_data = [row[idx] if idx < len(row) else '' for row in values[1:]]
            
            # Infer type
            pg_type = 'text'
            if col_data:
                # Try integer
                try:
                    [int(v) for v in col_data if v]
                    pg_type = 'integer'
                except:
                    # Try float
                    try:
                        [float(v.replace(',', '.')) for v in col_data if v]
                        pg_type = 'decimal'
                    except:
                        pg_type = 'text'
            
            columns.append({
                'name': str(header),
                'type': pg_type,
                'nullable': True  # Sheets don't enforce nulls
            })
        
        return columns
    
    def extract(self, query_or_table: str = None, is_query: bool = False) -> pd.DataFrame:
        spreadsheet_id = self._get_spreadsheet_id()
        sheet_name = query_or_table if query_or_table else self._get_sheet_name()
        service = self._get_service()
        
        # Get all data
        range_name = f"{sheet_name}!A1:ZZ"
        
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            return pd.DataFrame()
        
        # First row is header
        headers = values[0]
        data = values[1:]
        
        # Pad rows to match header length
        padded_data = []
        for row in data:
            padded_row = row + [''] * (len(headers) - len(row))
            padded_data.append(padded_row[:len(headers)])
        
        df = pd.DataFrame(padded_data, columns=headers)
        
        # Try to convert types
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except:
                pass
        
        return df
    
    def extract_sample(self, query_or_table: str = None, is_query: bool = False, limit: int = 100) -> pd.DataFrame:
        df = self.extract(query_or_table, is_query)
        return df.head(limit)
