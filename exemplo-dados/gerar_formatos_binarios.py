"""
Script para gerar arquivos de exemplo em formatos binários:
- Parquet
- Avro (dados)
- ORC
- Delta Lake

Execute: python gerar_formatos_binarios.py

Requisitos:
pip install pandas pyarrow fastavro sqlalchemy deltalake
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.orc as orc
import json
from datetime import datetime, date
from decimal import Decimal

dados_vendas = [
    {"id": 1, "cliente_id": 1, "data_venda": "2024-01-15 10:30:00", "valor_total": 3500.00, "forma_pagamento": "cartao_credito", "status": "concluida", "observacoes": "Venda via site"},
    {"id": 2, "cliente_id": 2, "data_venda": "2024-01-16 14:20:00", "valor_total": 449.50, "forma_pagamento": "debito", "status": "concluida", "observacoes": None},
    {"id": 3, "cliente_id": 1, "data_venda": "2024-01-17 09:15:00", "valor_total": 598.00, "forma_pagamento": "pix", "status": "concluida", "observacoes": "Pagamento instantâneo"},
    {"id": 4, "cliente_id": 3, "data_venda": "2024-01-18 16:45:00", "valor_total": 1200.00, "forma_pagamento": "cartao_credito", "status": "concluida", "observacoes": None},
    {"id": 5, "cliente_id": 2, "data_venda": "2024-01-19 11:30:00", "valor_total": 450.00, "forma_pagamento": "dinheiro", "status": "concluida", "observacoes": None},
    {"id": 6, "cliente_id": 4, "data_venda": "2024-01-20 15:00:00", "valor_total": 299.00, "forma_pagamento": "pix", "status": "concluida", "observacoes": "Desconto promocional"},
    {"id": 7, "cliente_id": 5, "data_venda": "2024-01-21 10:00:00", "valor_total": 249.90, "forma_pagamento": "cartao_credito", "status": "concluida", "observacoes": None},
    {"id": 8, "cliente_id": 1, "data_venda": "2024-01-22 13:30:00", "valor_total": 179.90, "forma_pagamento": "debito", "status": "concluida", "observacoes": None},
    {"id": 9, "cliente_id": 3, "data_venda": "2024-01-23 16:00:00", "valor_total": 5999.00, "forma_pagamento": "cartao_credito", "status": "concluida", "observacoes": "Produto de alto valor"},
    {"id": 10, "cliente_id": 2, "data_venda": "2024-01-24 11:45:00", "valor_total": 149.90, "forma_pagamento": "pix", "status": "concluida", "observacoes": None},
]

dados_clientes = [
    {"id": 1, "nome": "Empresa ABC Ltda", "cnpj": "12.345.678/0001-90", "segmento": "Tecnologia", "cidade": "São Paulo", "estado": "SP", "data_cadastro": "2024-01-01", "status": "ativo", "limite_credito": 50000.00},
    {"id": 2, "nome": "Comércio XYZ S/A", "cnpj": "98.765.432/0001-10", "segmento": "Varejo", "cidade": "Rio de Janeiro", "estado": "RJ", "data_cadastro": "2024-01-05", "status": "ativo", "limite_credito": 30000.00},
    {"id": 3, "nome": "Indústria 123 Ltda", "cnpj": "45.678.901/0001-23", "segmento": "Manufatura", "cidade": "Belo Horizonte", "estado": "MG", "data_cadastro": "2024-01-10", "status": "ativo", "limite_credito": 75000.00},
    {"id": 4, "nome": "Serviços Tech ME", "cnpj": "87.654.321/0001-45", "segmento": "Consultoria", "cidade": "Porto Alegre", "estado": "RS", "data_cadastro": "2024-01-15", "status": "ativo", "limite_credito": 25000.00},
    {"id": 5, "nome": "Distribuidora Central", "cnpj": "54.321.987/0001-67", "segmento": "Logística", "cidade": "Curitiba", "estado": "PR", "data_cadastro": "2024-01-20", "status": "pendente", "limite_credito": 100000.00},
    {"id": 6, "nome": "Loja Virtual E-commerce", "cnpj": "76.543.210/0001-89", "segmento": "E-commerce", "cidade": "Salvador", "estado": "BA", "data_cadastro": "2024-01-25", "status": "ativo", "limite_credito": 15000.00},
    {"id": 7, "nome": "Restaurante Sabores", "cnpj": "23.456.789/0001-01", "segmento": "Alimentação", "cidade": "Recife", "estado": "PE", "data_cadastro": "2024-02-01", "status": "ativo", "limite_credito": 10000.00},
    {"id": 8, "nome": "Construção Civil Ltda", "cnpj": "67.890.123/0001-34", "segmento": "Construção", "cidade": "Fortaleza", "estado": "CE", "data_cadastro": "2024-02-05", "status": "ativo", "limite_credito": 200000.00},
]

dados_produtos = [
    {"id": 1, "nome": "Notebook Dell Inspiron", "categoria": "Informática", "preco_custo": 2800.00, "preco_venda": 3500.00, "estoque": 15, "sku": "NOTE-DELL-001"},
    {"id": 2, "nome": "Mouse Logitech MX Master", "categoria": "Informática", "preco_custo": 65.00, "preco_venda": 89.90, "estoque": 50, "sku": "MOUSE-LOG-001"},
    {"id": 3, "nome": "Teclado Mecânico Redragon", "categoria": "Informática", "preco_custo": 220.00, "preco_venda": 299.00, "estoque": 25, "sku": "TECL-RED-001"},
    {"id": 4, "nome": "Monitor LG 27 UltraWide", "categoria": "Eletrônicos", "preco_custo": 950.00, "preco_venda": 1200.00, "estoque": 8, "sku": "MON-LG-001"},
    {"id": 5, "nome": "Fone Bluetooth JBL", "categoria": "Áudio", "preco_custo": 150.00, "preco_venda": 199.00, "estoque": 40, "sku": "FONE-JBL-001"},
]


def gerar_parquet():
    """Gera arquivos Parquet"""
    print("Gerando arquivos Parquet...")
    
    df_vendas = pd.DataFrame(dados_vendas)
    df_vendas.to_parquet('vendas.parquet', index=False)
    print("  - vendas.parquet criado")
    
    df_clientes = pd.DataFrame(dados_clientes)
    df_clientes.to_parquet('clientes.parquet', index=False)
    print("  - clientes.parquet criado")
    
    df_produtos = pd.DataFrame(dados_produtos)
    df_produtos.to_parquet('produtos.parquet', index=False)
    print("  - produtos.parquet criado")


def gerar_avro():
    """Gera arquivos Avro (dados)"""
    print("Gerando arquivos Avro...")
    
    try:
        import fastavro.schema
        import fastavro.parse
        import fastavro.writer
        import io
        
        schema_vendas = {
            "type": "record",
            "name": "vendas",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "cliente_id", "type": "int"},
                {"name": "data_venda", "type": "string"},
                {"name": "valor_total", "type": "double"},
                {"name": "forma_pagamento", "type": "string"},
                {"name": "status", "type": "string"},
                {"name": "observacoes", "type": ["null", "string"], "default": None}
            ]
        }
        
        parsed = fastavro.parse.parse_schema(schema_vendas)
        
        with open('vendas.avro', 'wb') as f:
            fastavro.writer.dump(f, parsed, dados_vendas)
        print("  - vendas.avro criado")
        
        schema_clientes = {
            "type": "record",
            "name": "clientes",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "nome", "type": "string"},
                {"name": "cnpj", "type": "string"},
                {"name": "segmento", "type": "string"},
                {"name": "cidade", "type": "string"},
                {"name": "estado", "type": "string"},
                {"name": "data_cadastro", "type": "string"},
                {"name": "status", "type": "string"},
                {"name": "limite_credito", "type": "double"}
            ]
        }
        
        parsed_clientes = fastavro.parse.parse_schema(schema_clientes)
        
        with open('clientes.avro', 'wb') as f:
            fastavro.writer.dump(f, parsed_clientes, dados_clientes)
        print("  - clientes.avro criado")
        
    except ImportError:
        print("  [AVISO] fastavro não instalado. Execute: pip install fastavro")
        print("  Criando arquivo JSON alternativo para dados Avro...")
        
        with open('vendas_avro.json', 'w', encoding='utf-8') as f:
            json.dump(dados_vendas, f, indent=2, ensure_ascii=False)
        print("  - vendas_avro.json criado (formato JSON alternativo)")
        
        with open('clientes_avro.json', 'w', encoding='utf-8') as f:
            json.dump(dados_clientes, f, indent=2, ensure_ascii=False)
        print("  - clientes_avro.json criado (formato JSON alternativo)")


def gerar_orc():
    """Gera arquivos ORC"""
    print("Gerando arquivos ORC...")
    
    df_vendas = pd.DataFrame(dados_vendas)
    table_vendas = pa.Table.from_pandas(df_vendas)
    orc.write_table(table_vendas, 'vendas.orc')
    print("  - vendas.orc criado")
    
    df_clientes = pd.DataFrame(dados_clientes)
    table_clientes = pa.Table.from_pandas(df_clientes)
    orc.write_table(table_clientes, 'clientes.orc')
    print("  - clientes.orc criado")


def gerar_delta_lake():
    """Gera tabela Delta Lake"""
    print("Gerando Delta Lake...")
    
    try:
        import deltalake
        
        df_vendas = pd.DataFrame(dados_vendas)
        deltalake.write_deltalake('delta_vendas', df_vendas, mode='overwrite')
        print("  - delta_vendas/ criado")
        
        df_clientes = pd.DataFrame(dados_clientes)
        deltalake.write_deltalake('delta_clientes', df_clientes, mode='overwrite')
        print("  - delta_clientes/ criado")
        
    except ImportError:
        print("  [AVISO] deltalake não instalado. Execute: pip install deltalake")
        print("  Criando arquivos Parquet compatíveis com Delta Lake...")
        
        df_vendas = pd.DataFrame(dados_vendas)
        df_vendas.to_parquet('delta_vendas.parquet', index=False)
        print("  - delta_vendas.parquet criado (importe no Delta Lake)")
        
        df_clientes = pd.DataFrame(dados_clientes)
        df_clientes.to_parquet('delta_clientes.parquet', index=False)
        print("  - delta_clientes.parquet criado (importe no Delta Lake)")


def main():
    print("=" * 50)
    print("Gerador de Arquivos de Exemplo - Dataflow")
    print("=" * 50)
    print()
    
    importar_pandas()
    gerar_parquet()
    gerar_orc()
    gerar_avro()
    gerar_delta_lake()
    
    print()
    print("=" * 50)
    print("Concluído! Arquivos gerados no diretório atual.")
    print("=" * 50)


def importar_pandas():
    print("Verificando dependências...")
    try:
        import pandas
        print("  - pandas OK")
    except ImportError:
        print("  [ERRO] pandas não instalado")
        raise


if __name__ == "__main__":
    main()
