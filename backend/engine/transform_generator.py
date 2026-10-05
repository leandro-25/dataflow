from typing import List, Dict, Any
import duckdb


class TransformGenerator:
    """Gera SQL para transformações de staging"""
    
    def __init__(self, duckdb_conn: duckdb.DuckDBPyConnection):
        self.conn = duckdb_conn
    
    def generate_sql(self, source_table: str, target_table: str, transforms: List[Dict[str, Any]]) -> str:
        """Gera SQL completo para staging"""
        # Start with base select
        sql_parts = [f"CREATE OR REPLACE TABLE {target_table} AS"]
        sql_parts.append("SELECT")
        
        # Get current columns
        columns = self._get_columns(source_table)
        current_columns = {col['name']: col['name'] for col in columns}
        
        # Apply transformations in order
        for transform in transforms:
            transform_type = transform.get('type')
            config = transform.get('config', {})
            
            if transform_type == 'rename':
                # { "col_old": "col_new", ... }
                for old_name, new_name in config.items():
                    if old_name in current_columns:
                        current_columns[new_name] = current_columns.pop(old_name)
            
            elif transform_type == 'cast':
                # { "col": "type", ... }
                for col, new_type in config.items():
                    if col in current_columns:
                        current_columns[col] = f"CAST({current_columns[col]} AS {self._map_type(new_type)})"
            
            elif transform_type == 'remove_columns':
                # { "columns": ["col1", "col2"] }
                for col in config.get('columns', []):
                    if col in current_columns:
                        del current_columns[col]
            
            elif transform_type == 'select_columns':
                # { "columns": ["col1", "col2"] }
                new_columns = {}
                for col in config.get('columns', []):
                    if col in current_columns:
                        new_columns[col] = current_columns[col]
                current_columns = new_columns
            
            elif transform_type == 'add_column':
                # { "name": "nova_col", "expression": "col1 + col2" }
                new_col = config.get('name')
                expression = config.get('expression')
                if new_col and expression:
                    current_columns[new_col] = expression
            
            elif transform_type == 'uppercase':
                # { "columns": ["col1", "col2"] }
                for col in config.get('columns', []):
                    if col in current_columns:
                        current_columns[col] = f"UPPER({col})"
            
            elif transform_type == 'lowercase':
                # { "columns": ["col1", "col2"] }
                for col in config.get('columns', []):
                    if col in current_columns:
                        current_columns[col] = f"LOWER({col})"
            
            elif transform_type == 'trim':
                # { "columns": ["col1", "col2"] }
                for col in config.get('columns', []):
                    if col in current_columns:
                        current_columns[col] = f"TRIM({col})"
            
            elif transform_type == 'fill_null':
                # { "column": "x", "value": 0 } ou { "column": "x", "strategy": "forward" }
                col = config.get('column')
                if col and col in current_columns:
                    if 'value' in config:
                        val = config['value']
                        if isinstance(val, str):
                            val = f"'{val}'"
                        current_columns[col] = f"COALESCE({col}, {val})"
                    elif config.get('strategy') == 'forward':
                        current_columns[col] = f"LAST_VALUE({col} IGNORE NULLS) OVER (ORDER BY rowid)"
                    elif config.get('strategy') == 'backward':
                        current_columns[col] = f"FIRST_VALUE({col} IGNORE NULLS) OVER (ORDER BY rowid DESC)"
            
            elif transform_type == 'split':
                # { "column": "nome", "delimiter": " ", "into": ["primeiro", "sobrenome"] }
                col = config.get('column')
                delimiter = config.get('delimiter', ' ')
                into = config.get('into', [])
                if col and col in current_columns and into:
                    # Remove original column
                    del current_columns[col]
                    # Add split columns
                    for i, new_col in enumerate(into):
                        current_columns[new_col] = f"SPLIT_PART({col}, '{delimiter}', {i + 1})"
            
            elif transform_type == 'merge':
                # { "columns": ["col1", "col2"], "into": "nova_col", "separator": " " }
                cols = config.get('columns', [])
                into = config.get('into')
                separator = config.get('separator', ' ')
                if into and cols:
                    # Remove merged columns
                    for col in cols:
                        if col in current_columns:
                            del current_columns[col]
                    # Add merged column
                    concat_expr = " || '{sep}' || ".format(sep=separator).join(cols)
                    current_columns[into] = concat_expr
            
            elif transform_type == 'replace':
                # { "column": "x", "find": "old", "replace": "new" }
                col = config.get('column')
                find = config.get('find')
                replace = config.get('replace')
                if col and col in current_columns and find is not None:
                    current_columns[col] = f"REPLACE({col}, '{find}', '{replace}')"
        
        # Build column list
        column_list = []
        for alias, expr in current_columns.items():
            if expr == alias:
                column_list.append(f'  "{alias}"')
            else:
                column_list.append(f'  {expr} AS "{alias}"')
        
        sql_parts.append(",\n".join(column_list))
        sql_parts.append(f"FROM {source_table}")
        
        # Add WHERE clause for filter transformation
        where_clauses = []
        for transform in transforms:
            if transform.get('type') == 'filter':
                config = transform.get('config', {})
                clause = self._build_filter_clause(config)
                if clause:
                    where_clauses.append(clause)
        
        if where_clauses:
            sql_parts.append("WHERE " + " AND ".join(where_clauses))
        
        # Add deduplication
        for transform in transforms:
            if transform.get('type') == 'deduplicate':
                config = transform.get('config', {})
                keys = config.get('keys', [])
                keep = config.get('keep', 'first')
                if keys:
                    key_str = ", ".join(keys)
                    order = "ASC" if keep == 'first' else "DESC"
                    sql_parts.append(f"QUALIFY ROW_NUMBER() OVER (PARTITION BY {key_str} ORDER BY rowid {order}) = 1")
        
        # Add sort
        for transform in transforms:
            if transform.get('type') == 'sort':
                config = transform.get('config', {})
                col = config.get('column')
                order = config.get('order', 'asc')
                if col:
                    sql_parts.append(f"ORDER BY {col} {order.upper()}")
        
        # Add limit
        for transform in transforms:
            if transform.get('type') == 'limit':
                config = transform.get('config', {})
                rows = config.get('rows')
                if rows:
                    sql_parts.append(f"LIMIT {rows}")
        
        return "\n".join(sql_parts)
    
    def _get_columns(self, table: str) -> List[Dict[str, Any]]:
        """Get columns from DuckDB table"""
        result = self.conn.execute(f"DESCRIBE {table}").fetchall()
        columns = []
        for row in result:
            columns.append({
                'name': row[0],
                'type': row[1],
                'nullable': row[2] == 'YES' if len(row) > 2 else True
            })
        return columns
    
    def _map_type(self, type_name: str) -> str:
        """Map type names to DuckDB types"""
        type_map = {
            'text': 'VARCHAR',
            'string': 'VARCHAR',
            'integer': 'INTEGER',
            'int': 'INTEGER',
            'decimal': 'DECIMAL',
            'float': 'DOUBLE',
            'double': 'DOUBLE',
            'date': 'DATE',
            'timestamp': 'TIMESTAMP',
            'datetime': 'TIMESTAMP',
            'boolean': 'BOOLEAN',
            'bool': 'BOOLEAN',
        }
        return type_map.get(type_name.lower(), 'VARCHAR')
    
    def _build_filter_clause(self, config: Dict[str, Any]) -> str:
        """Build WHERE clause from filter config"""
        column = config.get('column')
        operator = config.get('operator')
        value = config.get('value')
        
        if not column or not operator:
            return ""
        
        if operator == 'is_null':
            return f"{column} IS NULL"
        elif operator == 'is_not_null':
            return f"{column} IS NOT NULL"
        elif operator == 'contains':
            return f"{column} LIKE '%{value}%'"
        elif operator == 'in':
            if isinstance(value, list):
                vals = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in value])
                return f"{column} IN ({vals})"
        elif operator == 'not_in':
            if isinstance(value, list):
                vals = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in value])
                return f"{column} NOT IN ({vals})"
        else:
            if isinstance(value, str):
                value = f"'{value}'"
            return f"{column} {operator} {value}"
        
        return ""
