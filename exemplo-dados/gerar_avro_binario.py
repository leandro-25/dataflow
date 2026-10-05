"""
Script para gerar arquivos Avro binários com dados.
Execute: python gerar_avro_binario.py
"""

import fastavro
import fastavro.schema
import fastavro.write
import json
import os

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


def gerar_vendas_avro():
    schema = {
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
    
    parsed_schema = fastavro.schema.parse_schema(schema)
    
    with open('vendas.avro', 'wb') as f:
        fastavro.write.writer(f, parsed_schema, dados_vendas)
    
    print("vendas.avro criado com sucesso!")


def gerar_clientes_avro():
    schema = {
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
    
    parsed_schema = fastavro.schema.parse_schema(schema)
    
    with open('clientes.avro', 'wb') as f:
        fastavro.write.writer(f, parsed_schema, dados_clientes)
    
    print("clientes.avro criado com sucesso!")


if __name__ == "__main__":
    print("Gerando arquivos Avro binários...")
    gerar_vendas_avro()
    gerar_clientes_avro()
    print("Concluído!")
