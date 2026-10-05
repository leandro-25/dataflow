#!/usr/bin/env python3
"""
Servidor REST API de exemplo para testar o conector REST API do Dataflow
Execute: python rest_api_server.py
A API estará disponível em: http://localhost:8001
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional
import uvicorn
import random

app = FastAPI(title="API de Exemplo Dataflow", version="1.0.0")

# Habilitar CORS para permitir requisições do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos de dados
class Cliente(BaseModel):
    id: int
    nome: str
    email: str
    telefone: str
    cidade: str
    estado: str
    data_cadastro: datetime
    limite_credito: float
    status: str

class Produto(BaseModel):
    id: int
    nome: str
    categoria: str
    preco_custo: float
    preco_venda: float
    estoque: int
    fornecedor: str
    data_cadastro: date

class Venda(BaseModel):
    id: int
    cliente_id: int
    data_venda: datetime
    produto: str
    quantidade: int
    valor_unitario: float
    total: float
    vendedor: str
    status: str

# Dados de exemplo
clientes_db = [
    {"id": 1, "nome": "João Silva", "email": "joao@exemplo.com", "telefone": "(11) 98765-4321", "cidade": "São Paulo", "estado": "SP", "data_cadastro": datetime(2024, 1, 1), "limite_credito": 50000.00, "status": "ativo"},
    {"id": 2, "nome": "Maria Santos", "email": "maria@exemplo.com", "telefone": "(21) 98765-4322", "cidade": "Rio de Janeiro", "estado": "RJ", "data_cadastro": datetime(2024, 1, 5), "limite_credito": 30000.00, "status": "ativo"},
    {"id": 3, "nome": "Carlos Oliveira", "email": "carlos@exemplo.com", "telefone": "(31) 98765-4323", "cidade": "Belo Horizonte", "estado": "MG", "data_cadastro": datetime(2024, 1, 10), "limite_credito": 75000.00, "status": "ativo"},
    {"id": 4, "nome": "Ana Costa", "email": "ana@exemplo.com", "telefone": "(51) 98765-4324", "cidade": "Porto Alegre", "estado": "RS", "data_cadastro": datetime(2024, 1, 15), "limite_credito": 25000.00, "status": "ativo"},
    {"id": 5, "nome": "Pedro Martins", "email": "pedro@exemplo.com", "telefone": "(41) 98765-4325", "cidade": "Curitiba", "estado": "PR", "data_cadastro": datetime(2024, 1, 20), "limite_credito": 40000.00, "status": "pendente"},
]

produtos_db = [
    {"id": 1, "nome": "Notebook Dell Inspiron", "categoria": "Informática", "preco_custo": 2800.00, "preco_venda": 3500.00, "estoque": 15, "fornecedor": "Dell Brasil", "data_cadastro": date(2024, 1, 1)},
    {"id": 2, "nome": "Mouse Logitech MX Master", "categoria": "Informática", "preco_custo": 65.00, "preco_venda": 89.90, "estoque": 50, "fornecedor": "Logitech", "data_cadastro": date(2024, 1, 1)},
    {"id": 3, "nome": "Teclado Mecânico Redragon", "categoria": "Informática", "preco_custo": 220.00, "preco_venda": 299.00, "estoque": 25, "fornecedor": "Redragon", "data_cadastro": date(2024, 1, 2)},
    {"id": 4, "nome": "Monitor LG 27 UltraWide", "categoria": "Informática", "preco_custo": 950.00, "preco_venda": 1200.00, "estoque": 8, "fornecedor": "LG Electronics", "data_cadastro": date(2024, 1, 2)},
    {"id": 5, "nome": "Webcam Full HD", "categoria": "Informática", "preco_custo": 110.00, "preco_venda": 150.00, "estoque": 30, "fornecedor": "Generic", "data_cadastro": date(2024, 1, 3)},
]

vendas_db = [
    {"id": 1, "cliente_id": 1, "data_venda": datetime(2024, 1, 15, 10, 30), "produto": "Notebook Dell Inspiron", "quantidade": 1, "valor_unitario": 3500.00, "total": 3500.00, "vendedor": "João Vendedor", "status": "concluida"},
    {"id": 2, "cliente_id": 2, "data_venda": datetime(2024, 1, 16, 14, 20), "produto": "Mouse Logitech MX Master", "quantidade": 5, "valor_unitario": 89.90, "total": 449.50, "vendedor": "Maria Vendedora", "status": "concluida"},
    {"id": 3, "cliente_id": 1, "data_venda": datetime(2024, 1, 17, 9, 15), "produto": "Teclado Mecânico Redragon", "quantidade": 2, "valor_unitario": 299.00, "total": 598.00, "vendedor": "João Vendedor", "status": "concluida"},
    {"id": 4, "cliente_id": 3, "data_venda": datetime(2024, 1, 18, 16, 45), "produto": "Monitor LG 27 UltraWide", "quantidade": 1, "valor_unitario": 1200.00, "total": 1200.00, "vendedor": "Carlos Vendedor", "status": "concluida"},
    {"id": 5, "cliente_id": 2, "data_venda": datetime(2024, 1, 19, 11, 30), "produto": "Webcam Full HD", "quantidade": 3, "valor_unitario": 150.00, "total": 450.00, "vendedor": "Maria Vendedora", "status": "concluida"},
]

# Endpoints da API
@app.get("/")
async def root():
    return {"message": "API de Exemplo para Dataflow", "version": "1.0.0", "endpoints": ["/clientes", "/produtos", "/vendas"]}

@app.get("/clientes", response_model=List[Cliente])
async def get_clientes():
    """Retorna todos os clientes"""
    return clientes_db

@app.get("/clientes/{cliente_id}", response_model=Cliente)
async def get_cliente(cliente_id: int):
    """Retorna um cliente específico"""
    cliente = next((c for c in clientes_db if c["id"] == cliente_id), None)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return cliente

@app.get("/produtos", response_model=List[Produto])
async def get_produtos():
    """Retorna todos os produtos"""
    return produtos_db

@app.get("/produtos/{produto_id}", response_model=Produto)
async def get_produto(produto_id: int):
    """Retorna um produto específico"""
    produto = next((p for p in produtos_db if p["id"] == produto_id), None)
    if produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return produto

@app.get("/vendas", response_model=List[Venda])
async def get_vendas():
    """Retorna todas as vendas"""
    return vendas_db

@app.get("/vendas/{venda_id}", response_model=Venda)
async def get_venda(venda_id: int):
    """Retorna uma venda específica"""
    venda = next((v for v in vendas_db if v["id"] == venda_id), None)
    if venda is None:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    return venda

@app.get("/vendas/cliente/{cliente_id}", response_model=List[Venda])
async def get_vendas_por_cliente(cliente_id: int):
    """Retorna vendas de um cliente específico"""
    return [v for v in vendas_db if v["cliente_id"] == cliente_id]

@app.get("/estatisticas")
async def get_estatisticas():
    """Retorna estatísticas gerais"""
    total_clientes = len(clientes_db)
    total_produtos = len(produtos_db)
    total_vendas = len(vendas_db)
    valor_total_vendas = sum(v["total"] for v in vendas_db)
    
    return {
        "total_clientes": total_clientes,
        "total_produtos": total_produtos,
        "total_vendas": total_vendas,
        "valor_total_vendas": valor_total_vendas,
        "ticket_medio": valor_total_vendas / total_vendas if total_vendas > 0 else 0
    }

@app.post("/clientes", response_model=Cliente)
async def create_cliente(cliente: Cliente):
    """Cria um novo cliente"""
    new_id = max(c["id"] for c in clientes_db) + 1
    cliente.id = new_id
    clientes_db.append(cliente.dict())
    return cliente

if __name__ == "__main__":
    print("🚀 Iniciando API de Exemplo para Dataflow...")
    print("📍 API disponível em: http://localhost:8001")
    print("📖 Documentação disponível em: http://localhost:8001/docs")
    print("🔍 Endpoints disponíveis:")
    print("   GET  /clientes - Lista todos os clientes")
    print("   GET  /clientes/{id} - Retorna cliente específico")
    print("   GET  /produtos - Lista todos os produtos")
    print("   GET  /produtos/{id} - Retorna produto específico")
    print("   GET  /vendas - Lista todas as vendas")
    print("   GET  /vendas/{id} - Retorna venda específica")
    print("   GET  /estatisticas - Retorna estatísticas gerais")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
