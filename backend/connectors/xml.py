import pandas as pd
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
from .base import BaseConnector


class XMLConnector(BaseConnector):
    def _get_file_path(self) -> str:
        return self.config.get('file_path', '')
    
    def _get_root_element(self) -> str:
        return self.config.get('root_element', '')
    
    def _get_row_element(self) -> str:
        return self.config.get('row_element', '')
    
    def test_connection(self) -> tuple[bool, str]:
        try:
            import os
            file_path = self._get_file_path()
            
            if not file_path:
                return False, "Caminho do arquivo não configurado"
            
            if file_path.startswith('http://') or file_path.startswith('https://'):
                import requests
                response = requests.get(file_path, timeout=10)
                if response.status_code != 200:
                    return False, f"Erro HTTP {response.status_code}"
                content = response.text
            else:
                if not os.path.exists(file_path):
                    return False, f"Arquivo não encontrado: {file_path}"
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            # Try to parse XML
            root = ET.fromstring(content)
            
            # Count elements
            row_element = self._get_row_element()
            if row_element:
                count = len(root.findall(f'.//{row_element}'))
                return True, f"XML válido: {count} elementos '{row_element}' encontrados"
            else:
                return True, f"XML válido: root tag '{root.tag}'"
                
        except ET.ParseError as e:
            return False, f"XML inválido: {str(e)}"
        except Exception as e:
            return False, str(e)
    
    def list_tables(self) -> List[str]:
        file_path = self._get_file_path()
        import os
        return [os.path.basename(file_path)] if file_path else []
    
    def get_schema(self, table: str = None) -> List[Dict[str, Any]]:
        file_path = self._get_file_path()
        row_element = self._get_row_element()

        if file_path.startswith('http://') or file_path.startswith('https://'):
            import requests
            response = requests.get(file_path)
            root = ET.fromstring(response.content)
        else:
            tree = ET.parse(file_path)
            root = tree.getroot()

        if row_element:
            rows = root.findall(f'.//{row_element}')
        else:
            rows = list(root)

        if not rows:
            return []

        columns_set = {}
        for row in rows:
            for child in row:
                if child.tag not in columns_set:
                    columns_set[child.tag] = type(child.text).__name__ if child.text else 'str'

        columns = []
        for name in columns_set:
            columns.append({
                'name': name,
                'type': 'text',
                'nullable': True
            })

        return columns
        
        return columns
    
    def extract(self, query_or_table: str = None, is_query: bool = False) -> pd.DataFrame:
        file_path = self._get_file_path()
        row_element = self._get_row_element()
        
        # Load XML
        if file_path.startswith('http://') or file_path.startswith('https://'):
            import requests
            response = requests.get(file_path)
            root = ET.fromstring(response.content)
        else:
            tree = ET.parse(file_path)
            root = tree.getroot()
        
        # Find row elements
        if row_element:
            rows = root.findall(f'.//{row_element}')
        else:
            # Use direct children of root
            rows = list(root)
        
        # Convert to dict
        data = []
        for row in rows:
            row_dict = {}
            for child in row:
                # Handle nested elements
                if len(child) > 0:
                    # Convert nested element to string representation
                    row_dict[child.tag] = ET.tostring(child, encoding='unicode', method='text').strip()
                else:
                    row_dict[child.tag] = child.text
            data.append(row_dict)
        
        return pd.DataFrame(data)
