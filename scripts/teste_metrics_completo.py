import httpx

BASE = "http://localhost:8000/api"
c = httpx.Client(base_url=BASE, timeout=120)

resultados = []


def check(nome, cond, detalhe=""):
    resultados.append((nome, bool(cond), str(detalhe)[:130]))
    print(f"  [{'PASS' if cond else 'FAIL'}] {nome}" + (f" | {str(detalhe)[:110]}" if not cond else ""))


def exp_sql(query):
    """Valor esperado calculado diretamente no warehouse"""
    r = c.post("/catalog/query", json={"sql": query}).json()
    row = r.get("data", [{}])[0]
    return list(row.values())[0] if row else None


def criar(nome, label, fato, agg, coluna=None, fmt=None, filtros=None, custom=None):
    payload = {"name": nome, "label": label, "fact_table": fato, "aggregation": agg}
    if coluna is not None:
        payload["column_name"] = coluna
    if fmt is not None:
        payload["format"] = fmt
    if filtros is not None:
        payload["filters"] = filtros
    if custom is not None:
        payload["custom_sql"] = custom
    r = c.post("/metrics", json=payload)
    if r.status_code >= 400:
        return None, r
    m = r.json()
    if nome.startswith("tstm_"):
        ids_cleanup.append(m["id"])
    return m, r


ids_cleanup = []


def get_or_create(nome, **kw):
    existente = next((x for x in c.get("/metrics").json() if x["name"] == nome), None)
    if existente:
        print(f"    [existe] {nome}")
        return existente
    m, r = criar(nome, **kw)
    print(f"    [{'' if m else 'ERRO'}{'criado' if m else ''}] {nome}")
    if m is None:
        print("      ", r.text[:150])
    return m


def valor(metric_id, filtros=None):
    body = {"filters": filtros} if filtros is not None else {}
    r = c.post(f"/metrics/{metric_id}/query", json=body)
    return r


# limpeza inicial de residuos de teste
for m in c.get("/metrics").json():
    if m["name"].startswith("tstm_"):
        c.delete(f"/metrics/{m['id']}")

print("=" * 78)
print("TESTE EXAUSTIVO - SESSAO METRICS")
print("=" * 78)

# ---------- A. CRUD ----------
print("\n[A] CRUD")
m, r = criar("tstm_base", "Metrica Base", "fato_vendas", "sum", coluna="total",
             fmt={"type": "currency"}, filtros=[{"column": "quantidade", "operator": ">", "value": 0}])
check("POST cria metrica", m is not None, r.text[:100])
r2 = c.post("/metrics", json={"name": "tstm_base", "label": "dup", "fact_table": "fato_vendas", "aggregation": "count"})
check("POST nome duplicado -> 400", r2.status_code == 400)

g = c.get(f"/metrics/{m['id']}")
check("GET retorna config completa",
      g.status_code == 200 and g.json()["aggregation"] == "sum"
      and g.json()["format"]["type"] == "currency" and len(g.json()["filters"]) == 1)

up = c.put(f"/metrics/{m['id']}", json={"description": "atualizada"})
check("PUT atualiza descricao", up.status_code == 200 and up.json()["description"] == "atualizada")
m_outro, _ = criar("tstm_outro", "Outro", "fato_vendas", "count")
up2 = c.put(f"/metrics/{m['id']}", json={"name": "tstm_outro"})
check("PUT conflito de nome -> 400", up2.status_code == 400)
check("DELETE + 404 posterior",
      c.delete(f"/metrics/{m_outro['id']}").status_code == 200 and c.get(f"/metrics/{m_outro['id']}").status_code == 404)
check("GET inexistente -> 404", c.get("/metrics/id-falso").status_code == 404)

# ---------- B. agregacoes ----------
print("\n[B] AGREGACOES (sobre fato_vendas)")
casos_agg = [
    ("sum", "total", 25193.50),
    ("count", None, 15),
    ("avg", "total", round(25193.50 / 15, 6)),
    ("min", "quantidade", 1),
    ("max", "quantidade", 10),
    ("count_distinct", "vendedor", 4),
]
for agg, col, esperado in casos_agg:
    mm, rr = criar(f"tstm_{agg}", f"Teste {agg}", "fato_vendas", agg, coluna=col)
    if mm is None:
        check(f"agg {agg}", False, rr.text[:100])
        continue
    q = valor(mm["id"])
    v = q.json().get("value") if q.status_code < 400 else None
    okv = v is not None and abs(float(v) - float(esperado)) < 0.01
    check(f"agregacao {agg}" + (f" de {col}" if col else ""), q.status_code < 400 and okv,
          f"obtido={v} esperado={esperado} | {q.text[:80]}")

# validacao do padrao de agregacao
r422 = c.post("/metrics", json={"name": "tstm_agginvalida", "label": "x", "fact_table": "fato_vendas", "aggregation": "median"})
check("agregacao fora do padrao -> 422", r422.status_code == 422)

# ---------- C. formatos ----------
print("\n[C] FORMATACAO")
mf, _ = criar("tstm_fmt_currency", "Fmt Currency", "fato_vendas", "sum", coluna="total", fmt={"type": "currency"})
q = valor(mf["id"]).json()
check("format currency (R$)", q["formatted_value"] == "R$ 25,193.50", q["formatted_value"])

mp, _ = criar("tstm_fmt_percent", "Fmt Percent", "fato_vendas", "sum", coluna="quantidade", fmt={"type": "percent"})
q = valor(mp["id"]).json()
check("format percent (x100)", q["formatted_value"] == "4300.0%", q["formatted_value"])

md, _ = criar("tstm_fmt_decimals", "Fmt Decimals", "fato_vendas", "avg", coluna="total", fmt={"decimals": 3})
q = valor(md["id"]).json()
check("format decimals=3", q["formatted_value"] == "1,679.567", q["formatted_value"])

mn, _ = criar("tstm_fmt_none", "Fmt Nenhum", "fato_vendas", "count")
q = valor(mn["id"]).json()
check("sem formato retorna cru", q["formatted_value"] == "15", str(q))

# ---------- D. filtros ----------
print("\n[D] FILTROS")


def teste_filtro(nome_slug, filtros_metrica, filtros_query, sql_esperado):
    mm, rr = criar(f"tstm_flt_{nome_slug}", f"Filtro {nome_slug}", "fato_vendas", "sum",
                   coluna="total", filtros=filtros_metrica)
    body = {"filters": filtros_query} if filtros_query is not None else {}
    q = c.post(f"/metrics/{mm['id']}/query", json=body)
    obtido = q.json().get("value") if q.status_code < 400 else None
    esp = exp_sql(sql_esperado)
    ok = obtido is not None and esp is not None and abs(float(obtido) - float(esp)) < 0.01
    check(f"filtro {nome_slug}", ok, f"obtido={obtido} esperado={esp} | {q.text[:70]}")


teste_filtro("gt", [{"column": "quantidade", "operator": ">", "value": 5}], None,
             "SELECT SUM(total) FROM fato_vendas WHERE quantidade > 5")
teste_filtro("gte", [{"column": "quantidade", "operator": ">=", "value": 3}], None,
             "SELECT SUM(total) FROM fato_vendas WHERE quantidade >= 3")
teste_filtro("lt", [{"column": "quantidade", "operator": "<", "value": 3}], None,
             "SELECT SUM(total) FROM fato_vendas WHERE quantidade < 3")
teste_filtro("lte", [{"column": "quantidade", "operator": "<=", "value": 2}], None,
             "SELECT SUM(total) FROM fato_vendas WHERE quantidade <= 2")
teste_filtro("eq_str", [{"column": "vendedor", "operator": "=", "value": "João Silva"}], None,
             "SELECT SUM(total) FROM fato_vendas WHERE vendedor = 'João Silva'")
teste_filtro("neq", [{"column": "vendedor", "operator": "!=", "value": "João Silva"}], None,
             "SELECT SUM(total) FROM fato_vendas WHERE vendedor != 'João Silva'")
teste_filtro("in", [{"column": "produto", "operator": "IN", "value": ["Notebook Dell", "Webcam HD"]}], None,
             "SELECT SUM(total) FROM fato_vendas WHERE produto IN ('Notebook Dell', 'Webcam HD')")
teste_filtro("not_in", [{"column": "produto", "operator": "NOT IN", "value": ["Notebook Dell"]}], None,
             "SELECT SUM(total) FROM fato_vendas WHERE produto NOT IN ('Notebook Dell')")
teste_filtro("like", [{"column": "produto", "operator": "LIKE", "value": "%Notebook%"}], None,
             "SELECT SUM(total) FROM fato_vendas WHERE produto LIKE '%Notebook%'")
mp2, _ = criar("tstm_flt_isnull_pq", "IsNull PQ", "fato_vendas_parquet", "count", filtros=[{"column": "observacoes", "operator": "IS NULL"}])
q = valor(mp2["id"]).json()
esp = exp_sql("SELECT COUNT(*) FROM fato_vendas_parquet WHERE observacoes IS NULL")
check("filtro IS NULL", str(q.get("value")) == str(esp), f"{q.get('value')} vs {esp}")
mpn, _ = criar("tstm_flt_isnotnull_pq", "IsNotNull PQ", "fato_vendas_parquet", "count", filtros=[{"column": "observacoes", "operator": "IS NOT NULL"}])
q = valor(mpn["id"]).json()
esp = exp_sql("SELECT COUNT(*) FROM fato_vendas_parquet WHERE observacoes IS NOT NULL")
check("filtro IS NOT NULL", str(q.get("value")) == str(esp), f"{q.get('value')} vs {esp}")

# merge: filtro da metrica sobrescrito pelo da query na mesma coluna
mm, _ = criar("tstm_merge_override", "Merge Override", "fato_vendas", "sum", coluna="total",
              filtros=[{"column": "quantidade", "operator": ">", "value": 0}])
q = c.post(f"/metrics/{mm['id']}/query", json={"filters": [{"column": "quantidade", "operator": ">", "value": 5}]})
obtido = q.json().get("value")
esp = exp_sql("SELECT SUM(total) FROM fato_vendas WHERE quantidade > 5")
check("merge: query sobrescreve mesma coluna", abs(float(obtido) - float(esp)) < 0.01, f"{obtido} vs {esp}")

# merge: colunas diferentes somam com AND
q = c.post(f"/metrics/{mm['id']}/query", json={"filters": [{"column": "vendedor", "operator": "=", "value": "Ana Costa"}]})
obtido = q.json().get("value")
esp = exp_sql("SELECT SUM(total) FROM fato_vendas WHERE quantidade > 0 AND vendedor = 'Ana Costa'")
check("merge: colunas diferentes fazem AND", abs(float(obtido) - float(esp)) < 0.01, f"{obtido} vs {esp}")

# ---------- E. custom_sql ----------
print("\n[E] CUSTOM SQL")
mc, _ = criar("tstm_customsql", "Custom SQL", "fato_vendas", "sum", custom="SELECT SUM(quantidade) FROM fato_vendas")
q = valor(mc["id"]).json()
check("custom_sql executado", q["value"] == 43, str(q))

mcw, _ = criar("tstm_customsql_where", "Custom SQL Where", "fato_vendas", "sum",
               custom="SELECT SUM(total) FROM fato_vendas")
q = c.post(f"/metrics/{mcw['id']}/query", json={"filters": [{"column": "quantidade", "operator": ">", "value": 5}]})
obtido = q.json().get("value")
esp = exp_sql("SELECT SUM(total) FROM fato_vendas WHERE quantidade > 5")
check("custom_sql + filtro de query (WHERE anexado)", abs(float(obtido) - float(esp)) < 0.01, f"{obtido} vs {esp}")

# ---------- F. uma metrica por formato (oficiais, ficam visiveis) ----------
print("\n[F] METRICA OFICIAL POR FONTE")
oficiais = [
    ("met_total_vendas_parquet", "Total Vendas Parquet", "fato_vendas_parquet", "sum", "valor_total",
     "SELECT SUM(valor_total) FROM fato_vendas_parquet"),
    ("met_total_vendas_avro", "Total Vendas Avro", "fato_vendas_avro", "sum", "valor_total",
     "SELECT SUM(valor_total) FROM fato_vendas_avro"),
    ("met_total_vendas_orc", "Total Vendas ORC", "fato_vendas_orc", "sum", "valor_total",
     "SELECT SUM(valor_total) FROM fato_vendas_orc"),
    ("met_preco_medio_produtos", "Preco Medio Produtos", "fato_produtos", "avg", "preco_venda",
     "SELECT AVG(preco_venda) FROM fato_produtos"),
    ("met_qtd_clientes", "Qtd Clientes", "fato_clientes", "count", None,
     "SELECT COUNT(*) FROM fato_clientes"),
    ("met_segmentos_clientes_xml", "Segmentos Clientes XML", "fato_clientes_xml", "count_distinct", "segmento",
     "SELECT COUNT(DISTINCT segmento) FROM fato_clientes_xml"),
]
for nome, label, fato, agg, col, sql_esp in oficiais:
    mo = get_or_create(nome, label=label, fato=fato, agg=agg, coluna=col, fmt={"decimals": 2})
    if mo is None:
        continue
    q = valor(mo["id"]).json()
    esp = exp_sql(sql_esp)
    ok = esp is not None and abs(float(q["value"]) - float(esp)) < 0.01
    check(f"{nome} = {esp}", ok, f"obtido={q['value']}")
    print(f"      exibicao: {q['formatted_value']}")

print("\n  Metricas oficiais ja existentes:")
for nome_oficial in ["total_vendas", "quantidade_total", "ticket_medio"]:
    mo = next((x for x in c.get("/metrics").json() if x["name"] == nome_oficial), None)
    if mo:
        q = valor(mo["id"]).json()
        check(f"{nome_oficial} responde ({q['formatted_value']})", True)
    else:
        check(f"{nome_oficial} existe", False, "nao encontrada")

# ---------- G. erros tratados ----------
print("\n[G] TRATAMENTO DE ERROS")
mt, _ = criar("tstm_tabelainexistente", "Tabela Fantasma", "fato_fantasma", "count")
resp = c.post(f"/metrics/{mt['id']}/query", json={})
check("fact_table inexistente -> 400", resp.status_code == 400, f"status={resp.status_code}")

mcol, _ = criar("tstm_colunainexistente", "Coluna Fantasma", "fato_vendas", "sum", coluna="coluna_nada")
resp = c.post(f"/metrics/{mcol['id']}/query", json={})
check("coluna inexistente -> 400", resp.status_code == 400, f"status={resp.status_code}")

msql, _ = criar("tstm_sqlruim", "SQL Ruim", "fato_vendas", "sum", custom="SELECT * FROM nada")
resp = c.post(f"/metrics/{msql['id']}/query", json={})
check("custom_sql invalido -> 400", resp.status_code == 400, f"status={resp.status_code}")

check("query em id inexistente -> 404", c.post("/metrics/id-falso/query", json={}).status_code == 404)

# ---------- H. limpeza ----------
print("\n[H] LIMPEZA")
for mid in ids_cleanup:
    c.delete(f"/metrics/{mid}")
restaram = [x["name"] for x in c.get("/metrics").json() if x["name"].startswith("tstm_")]
check("limpeza de metricas de teste", not restaram, str(restaram))
oficiais_restantes = [x["name"] for x in c.get("/metrics").json()]
check("metricas oficiais preservadas", len(oficiais_restantes) >= 9, str(len(oficiais_restantes)))

falhas = [(n, dd) for n, p, dd in resultados if not p]
print("\n" + "=" * 78)
print(f"RESULTADO: {len(resultados) - len(falhas)}/{len(resultados)} testes aprovados")
if falhas:
    print("\nFALHAS:")
    for n, dd in falhas:
        print(f"  - {n}: {dd}")
import sys
sys.exit(0 if not falhas else 1)
