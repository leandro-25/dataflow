"""
Restaura/popula o Dataflow com os dados de demonstracao (idempotente).

Cria (se nao existirem) e executa:
  - 7 fontes de dados (CSV, JSON, Excel, XML, Parquet, Avro, ORC)
  - 7 ingestoes -> tabelas raw_*
  - stg_vendas (rename+cast+filter+colunas ano/mes)
  - dim_vendedores, fato_vendas
  - 3 metricas e o dashboard_vendas

Uso: python scripts/restaurar_dados_demo.py   (com o backend rodando na porta 8000)
"""
import sys
from pathlib import Path

import httpx

BASE = "http://localhost:8000/api"
ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "exemplo-dados"

try:
    c = httpx.Client(base_url=BASE, timeout=120)
    c.get("/health").raise_for_status()
except Exception:
    print("ERRO: backend nao responde em http://localhost:8000")
    print("Inicie-o primeiro (start_backend.bat ou python backend/main.py)")
    sys.exit(1)


def get_or_create(path, name_key, payload):
    for item in c.get(path).json():
        if item["name"] == payload[name_key]:
            print(f"  [existe] {payload[name_key]}")
            return item
    r = c.post(path, json=payload)
    if r.status_code >= 400:
        print(f"  [ERRO] {r.text}")
        raise SystemExit(1)
    print(f"  [criado] {r.json()['name']}")
    return r.json()


def run(path):
    r = c.post(path)
    ok = r.status_code < 400
    info = r.json() if ok else r.text[:200]
    print(f"    -> {'OK' if ok else 'ERRO'}: {info if isinstance(info, str) else info.get('rows_affected', '')}")
    return ok


print("=== 1. FONTES ===")
fontes = {
    "vendas_csv": ("csv", {"file_path": str(EX / "vendas.csv"), "delimiter": ",", "encoding": "utf-8", "has_header": True}),
    "clientes_json": ("json", {"file_path": str(EX / "clientes.json")}),
    "produtos_xlsx": ("excel", {"file_path": str(EX / "produtos.xlsx")}),
    "clientes_xml": ("xml", {"file_path": str(EX / "clientes.xml"), "row_element": "cliente"}),
    "vendas_parquet": ("parquet", {"file_path": str(EX / "vendas.parquet")}),
    "vendas_avro": ("avro", {"file_path": str(EX / "vendas.avro")}),
    "vendas_orc": ("orc", {"file_path": str(EX / "vendas.orc")}),
}
src_ids = {}
for nome, (tipo, cfg) in fontes.items():
    s = get_or_create("/sources", "name", {"name": nome, "type": tipo, "config": cfg})
    src_ids[nome] = s["id"]
    t = c.post(f"/sources/{s['id']}/test").json()
    print(f"    teste {nome}: {'OK' if t['success'] else 'FALHA'}")

print("\n=== 2. INGESTOES ===")
ingestoes = [
    ("ing_raw_vendas", "vendas_csv", "vendas.csv", "raw_vendas"),
    ("ing_raw_clientes", "clientes_json", "clientes.json", "raw_clientes"),
    ("ing_raw_produtos", "produtos_xlsx", "produtos.xlsx", "raw_produtos"),
    ("ing_raw_clientes_xml", "clientes_xml", "clientes.xml", "raw_clientes_xml"),
    ("ing_raw_vendas_parquet", "vendas_parquet", "vendas.parquet", "raw_vendas_parquet"),
    ("ing_raw_vendas_avro", "vendas_avro", "vendas.avro", "raw_vendas_avro"),
    ("ing_raw_vendas_orc", "vendas_orc", "vendas.orc", "raw_vendas_orc"),
]
for nome, fonte, tabela, destino in ingestoes:
    ing = get_or_create("/ingestions", "name", {
        "name": nome,
        "source_id": src_ids[fonte],
        "config": {"mode": "table", "table": tabela, "target_table": destino},
    })
    run(f"/ingestions/{ing['id']}/run")

print("\n=== 3. STAGING ===")
stg = get_or_create("/staging", "name", {
    "name": "stg_vendas",
    "source_table": "raw_vendas",
    "target_table": "stg_vendas",
    "mode": "visual",
    "transforms": [
        {"type": "rename", "config": {"data": "data_venda"}},
        {"type": "cast", "config": {"data_venda": "date"}},
        {"type": "filter", "config": {"column": "quantidade", "operator": ">", "value": 0}},
        {"type": "add_column", "config": {"name": "ano", "expression": "EXTRACT(YEAR FROM data_venda)"}},
        {"type": "add_column", "config": {"name": "mes", "expression": "EXTRACT(MONTH FROM data_venda)"}},
    ],
})
run(f"/staging/{stg['id']}/run")

# Staging para as demais fontes
clientes_transforms = [
    {"type": "trim", "config": {"columns": ["nome", "cidade"]}},
    {"type": "uppercase", "config": {"columns": ["estado"]}},
    {"type": "cast", "config": {"data_cadastro": "date", "limite_credito": "double"}},
]
produtos_transforms = [
    {"type": "trim", "config": {"columns": ["nome", "fornecedor"]}},
    {"type": "cast", "config": {"preco_custo": "double", "preco_venda": "double", "estoque": "integer", "data_cadastro": "date"}},
]
vendas_binarias_transforms = [
    {"type": "trim", "config": {"columns": ["forma_pagamento", "status"]}},
    {"type": "cast", "config": {"data_venda": "date", "valor_total": "double"}},
]

outros_stagings = [
    ("stg_clientes", "raw_clientes", clientes_transforms),
    ("stg_clientes_xml", "raw_clientes_xml", clientes_transforms),
    ("stg_produtos", "raw_produtos", produtos_transforms),
    ("stg_vendas_parquet", "raw_vendas_parquet", vendas_binarias_transforms),
    ("stg_vendas_avro", "raw_vendas_avro", vendas_binarias_transforms),
    ("stg_vendas_orc", "raw_vendas_orc", vendas_binarias_transforms),
]
for nome, fonte, transforms in outros_stagings:
    s = get_or_create("/staging", "name", {
        "name": nome,
        "source_table": fonte,
        "target_table": nome,
        "mode": "visual",
        "transforms": transforms,
    })
    run(f"/staging/{s['id']}/run")

print("\n=== 4. DIMENSAO ===")
dim = get_or_create("/dimensions", "name", {
    "name": "dim_vendedores",
    "source_table": "stg_vendas",
    "target_table": "dim_vendedores",
    "primary_key": "vendedor",
    "surrogate_key": "sk_vendedor",
    "attributes": ["vendedor"],
    "mode": "visual",
})
run(f"/dimensions/{dim['id']}/run")

# Dimensoes para as demais fontes
outras_dims = [
    ("dim_clientes", "stg_clientes", "id", "sk_cliente", ["nome", "segmento", "cidade", "estado"]),
    ("dim_clientes_xml", "stg_clientes_xml", "id", "sk_cliente_xml", ["nome", "segmento", "cidade"]),
    ("dim_produtos", "stg_produtos", "id", "sk_produto", ["nome", "categoria"]),
    ("dim_vendas_parquet", "stg_vendas_parquet", "id", "sk_venda_pq", ["forma_pagamento", "status"]),
    ("dim_vendas_avro", "stg_vendas_avro", "id", "sk_venda_av", ["forma_pagamento", "status"]),
    ("dim_vendas_orc", "stg_vendas_orc", "id", "sk_venda_orc", ["forma_pagamento", "status"]),
]
for nome, fonte, pk, sk, attrs in outras_dims:
    d = get_or_create("/dimensions", "name", {
        "name": nome,
        "source_table": fonte,
        "target_table": nome,
        "primary_key": pk,
        "surrogate_key": sk,
        "attributes": attrs,
        "mode": "visual",
    })
    run(f"/dimensions/{d['id']}/run")

print("\n=== 5. FATO ===")
fato = get_or_create("/facts", "name", {
    "name": "fato_vendas",
    "source_table": "stg_vendas",
    "target_table": "fato_vendas",
    "grain": "uma_linha_por_venda",
    "dimension_links": [{"dimension": "dim_vendedores", "natural_key": "vendedor", "surrogate_key": "sk_vendedor"}],
    "measures": ["quantidade", "total"],
    "mode": "sql",
    "custom_sql": "SELECT s.*, d.sk_vendedor FROM _input s JOIN dim_vendedores d ON s.vendedor = d.vendedor",
})
run(f"/facts/{fato['id']}/run")

# Fatos para as demais fontes (modo SQL com join nas dimensoes)
outras_fatos = [
    ("fato_vendas_parquet", "stg_vendas_parquet", "dim_vendas_parquet", "sk_venda_pq"),
    ("fato_vendas_avro", "stg_vendas_avro", "dim_vendas_avro", "sk_venda_av"),
    ("fato_vendas_orc", "stg_vendas_orc", "dim_vendas_orc", "sk_venda_orc"),
    ("fato_produtos", "stg_produtos", "dim_produtos", "sk_produto"),
    ("fato_clientes", "stg_clientes", "dim_clientes", "sk_cliente"),
    ("fato_clientes_xml", "stg_clientes_xml", "dim_clientes_xml", "sk_cliente_xml"),
]
for nome, fonte, dim, sk in outras_fatos:
    f = get_or_create("/facts", "name", {
        "name": nome,
        "source_table": fonte,
        "target_table": nome,
        "grain": "uma_linha_por_registro",
        "dimension_links": [{"dimension": dim, "join_on": "id"}],
        "measures": [],
        "mode": "sql",
        "custom_sql": f"SELECT s.*, d.{sk} FROM _input s JOIN {dim} d ON s.id = d.id",
    })
    run(f"/facts/{f['id']}/run")

print("\n=== 6. METRICAS ===")
for m in [
    {"name": "total_vendas", "label": "Total de Vendas", "fact_table": "fato_vendas",
     "aggregation": "sum", "column_name": "total", "format": {"type": "currency"},
     "description": "Soma do valor total das vendas"},
    {"name": "quantidade_total", "label": "Quantidade Vendida", "fact_table": "fato_vendas",
     "aggregation": "sum", "column_name": "quantidade", "format": {"type": "number"},
     "description": "Total de itens vendidos"},
    {"name": "ticket_medio", "label": "Ticket Medio", "fact_table": "fato_vendas",
     "aggregation": "avg", "column_name": "total", "format": {"type": "currency"},
     "description": "Valor medio por venda"},
]:
    met = get_or_create("/metrics", "name", m)
    q = c.post(f"/metrics/{met['id']}/query", json={}).json()
    print(f"    valor atual: {q.get('formatted_value', q)}")

# Metricas para as demais fontes
outras_metricas = [
    ("met_total_vendas_parquet", "Total Vendas Parquet", "fato_vendas_parquet", "sum", "valor_total"),
    ("met_total_vendas_avro", "Total Vendas Avro", "fato_vendas_avro", "sum", "valor_total"),
    ("met_total_vendas_orc", "Total Vendas ORC", "fato_vendas_orc", "sum", "valor_total"),
    ("met_preco_medio_produtos", "Preco Medio Produtos", "fato_produtos", "avg", "preco_venda"),
    ("met_qtd_clientes", "Qtd Clientes", "fato_clientes", "count", None),
    ("met_segmentos_clientes_xml", "Segmentos Clientes XML", "fato_clientes_xml", "count_distinct", "segmento"),
]
for nome, label, fato, agg, col in outras_metricas:
    payload = {"name": nome, "label": label, "fact_table": fato, "aggregation": agg,
               "format": {"decimals": 2}}
    if col is not None:
        payload["column_name"] = col
    met = get_or_create("/metrics", "name", payload)
    q = c.post(f"/metrics/{met['id']}/query", json={}).json()
    print(f"    valor atual: {q.get('formatted_value', q)}")


def query(sql_text):
    r = c.post("/catalog/query", json={"sql": sql_text}).json()
    return r.get("data", [])


print("\n=== 7. DASHBOARD ===")
por_vendedor = query("SELECT vendedor AS name, SUM(total) AS value FROM fato_vendas GROUP BY vendedor ORDER BY value DESC")
por_produto = query("SELECT produto AS name, SUM(total) AS value FROM fato_vendas GROUP BY produto ORDER BY value DESC")
tot_q = query("SELECT SUM(total) AS v, SUM(quantidade) AS q FROM fato_vendas")
tot = float(tot_q[0]["v"]) if tot_q and tot_q[0]["v"] else 0.0
qtde = int(tot_q[0]["q"]) if tot_q and tot_q[0]["q"] else 0
tick = tot / qtde if qtde else 0
detalhes = query("SELECT data_venda, vendedor, produto, quantidade, total FROM fato_vendas ORDER BY data_venda")

layout = [
    {"id": "kpi-total", "type": "kpi", "width": 4, "x": 0, "y": 0, "w": 4, "h": 2,
     "config": {"label": "Total de Vendas", "value": f"R$ {tot:,.2f}"}},
    {"id": "kpi-itens", "type": "kpi", "width": 4, "x": 4, "y": 0, "w": 4, "h": 2,
     "config": {"label": "Itens Vendidos", "value": str(qtde)}},
    {"id": "kpi-ticket", "type": "kpi", "width": 4, "x": 8, "y": 0, "w": 4, "h": 2,
     "config": {"label": "Ticket Medio", "value": f"R$ {tick:,.2f}"}},
    {"id": "graf-vendedor", "type": "chart_bar", "width": 6, "x": 0, "y": 2, "w": 6, "h": 4,
     "config": {"title": "Vendas por Vendedor", "data": por_vendedor}},
    {"id": "graf-produto", "type": "chart_pie", "width": 6, "x": 6, "y": 2, "w": 6, "h": 4,
     "config": {"title": "Vendas por Produto", "data": por_produto}},
    {"id": "tabela-detalhes", "type": "table", "width": 12, "x": 0, "y": 6, "w": 12, "h": 5,
     "config": {"title": "Detalhes das Vendas",
        "columns": ["data_venda", "vendedor", "produto", "quantidade", "total"], "data": detalhes}},
]

dash_existente = next((d for d in c.get("/dashboards").json() if d["name"] == "dashboard_vendas"), None)
if dash_existente:
    c.put(f"/dashboards/{dash_existente['id']}", json={"layout": layout})
    print("  [atualizado] dashboard_vendas")
else:
    c.post("/dashboards", json={
        "name": "dashboard_vendas",
        "title": "Dashboard de Vendas",
        "description": "Pipeline completo: arquivos -> Staging -> Dimensao/Fato -> Metricas",
        "layout": layout,
    })
    print("  [criado] dashboard_vendas")

print("\n=== VERIFICACAO FINAL ===")
tables = c.get("/catalog/tables").json()["tables"]
principais = ["raw_vendas", "raw_clientes", "raw_produtos", "raw_clientes_xml",
              "raw_vendas_parquet", "raw_vendas_avro", "raw_vendas_orc",
              "stg_vendas", "stg_clientes", "stg_clientes_xml", "stg_produtos",
              "stg_vendas_parquet", "stg_vendas_avro", "stg_vendas_orc",
              "dim_vendedores", "fato_vendas"]
faltando = [t for t in principais if t not in {x["name"] for x in tables}]
if faltando:
    print(f"AVISO: tabelas ausentes: {faltando}")
    sys.exit(1)
for t in tables:
    if t["name"] in principais:
        print(f"  - {t['name']}: {t.get('row_count', t.get('rows'))} linhas")
print("\nCONCLUIDO! Dados de demonstracao prontos para uso.")
