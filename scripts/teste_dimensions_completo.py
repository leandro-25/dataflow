import httpx

BASE = "http://localhost:8000/api"
c = httpx.Client(base_url=BASE, timeout=120)

resultados = []


def check(nome, cond, detalhe=""):
    resultados.append((nome, bool(cond), str(detalhe)[:130]))
    print(f"  [{'PASS' if cond else 'FAIL'}] {nome}" + (f" | {str(detalhe)[:110]}" if not cond else ""))


def sql(query):
    r = c.post("/catalog/query", json={"sql": query})
    if r.status_code >= 400:
        print(f"    [SQL ERRO] {query[:90]} -> {r.text[:120]}")
        return []
    return r.json().get("data", [])


def colunas(t):
    return [x["name"] for x in c.get(f"/catalog/tables/{t}").json().get("columns", [])]


def linhas(t):
    return c.get(f"/catalog/tables/{t}").json().get("row_count", -1)


ids_dim = []
alvos = []


def criar(nome, fonte, alvo, pk, sk=None, attrs=None, modo="visual", custom_sql=None, hierarchies=None):
    payload = {"name": nome, "source_table": fonte, "target_table": alvo,
               "primary_key": pk, "attributes": attrs or [], "mode": modo}
    if sk:
        payload["surrogate_key"] = sk
    if custom_sql:
        payload["custom_sql"] = custom_sql
    if hierarchies is not None:
        payload["hierarchies"] = hierarchies
    r = c.post("/dimensions", json=payload)
    if r.status_code >= 400:
        return None, r
    d = r.json()
    ids_dim.append(d["id"])
    alvos.append(alvo)
    return d, r


# limpeza inicial de residuos de execucoes anteriores
for d in c.get("/dimensions").json():
    if d["name"].startswith("tstd_"):
        c.delete(f"/dimensions/{d['id']}")
for t in [x["name"] for x in c.get("/catalog/tables").json()["tables"]]:
    if t.startswith("tstd_"):
        c.delete(f"/catalog/tables/{t}")

print("=" * 78)
print("TESTE EXAUSTIVO - SESSAO DIMENSIONS")
print("=" * 78)

# ---------- A. CRUD ----------
print("\n[A] CRUD")
d, r = criar("tstd_base", "stg_vendas", "tstd_base_alvo", pk="vendedor", sk="sk_teste", attrs=["vendedor"])
check("POST cria dimension", d is not None, r.text[:100])
r2 = c.post("/dimensions", json={"name": "tstd_base", "source_table": "stg_vendas",
                                 "target_table": "x2", "primary_key": "vendedor"})
check("POST nome duplicado -> 400", r2.status_code == 400)

g = c.get(f"/dimensions/{d['id']}")
check("GET por id retorna config completa",
      g.status_code == 200 and g.json()["primary_key"] == "vendedor" and g.json()["surrogate_key"] == "sk_teste")

hier = [{"level": "cidade", "levels": ["cidade", "estado"]}]
dh, _ = criar("tstd_hierarquia", "stg_clientes", "tstd_hier_alvo", pk="id", attrs=["id"], hierarchies=hier)
gh = c.get(f"/dimensions/{dh['id']}").json()
check("hierarchies aceito e persistido", gh.get("hierarchies") == hier, str(gh.get("hierarchies"))[:100])

up = c.put(f"/dimensions/{d['id']}", json={"attributes": ["vendedor", "produto"]})
check("PUT atualiza atributos", up.status_code == 200 and up.json()["attributes"] == ["vendedor", "produto"])
up2 = c.put(f"/dimensions/{d['id']}", json={"name": "tstd_hierarquia"})
check("PUT conflito de nome -> 400", up2.status_code == 400)
check("GET inexistente -> 404", c.get("/dimensions/id-falso").status_code == 404)
del_ok = c.delete(f"/dimensions/{dh['id']}")
check("DELETE + 404 posterior", del_ok.status_code == 200 and c.get(f"/dimensions/{dh['id']}").status_code == 404)

# ---------- B. uma dimension por formato ----------
print("\n[B] DIMENSION POR FORMATO DE ARQUIVO (7 formatos)")
por_formato = [
    ("csv",     "tstd_vendas",       "stg_vendas",         "vendedor", "sk_dim_venda",    ["vendedor"],              4),
    ("json",    "tstd_clientes",     "stg_clientes",       "id",       "sk_cliente",      ["nome", "cidade"],        8),
    ("xml",     "tstd_clientes_xml", "stg_clientes_xml",   "id",       "sk_cliente_xml",  ["nome", "segmento"],      8),
    ("excel",   "tstd_produtos",     "stg_produtos",       "id",       "sk_produto",      ["nome", "categoria"],     15),
    ("parquet", "tstd_parquet",      "stg_vendas_parquet", "id",       "sk_venda_pq",     ["forma_pagamento"],       10),
    ("avro",    "tstd_avro",         "stg_vendas_avro",    "id",       "sk_venda_av",     ["forma_pagamento"],       10),
    ("orc",     "tstd_orc",          "stg_vendas_orc",     "id",       "sk_venda_orc",    ["forma_pagamento"],       10),
]
for tipo, nome, fonte, pk, sk, attrs, esperado in por_formato:
    d, r = criar(nome, fonte, f"tstd_{tipo}_alvo", pk=pk, sk=sk, attrs=attrs)
    if d is None:
        check(f"criar dimension {tipo}", False, r.text[:100])
        continue
    pv = c.post(f"/dimensions/{d['id']}/preview")
    pv_ok = pv.status_code == 200 and len(pv.json().get("data", [])) > 0
    check(f"preview antes do run ({tipo})", pv_ok, pv.text[:100])

    run = c.post(f"/dimensions/{d['id']}/run").json()
    ok = run.get("success") is True and run.get("rows_affected") == esperado
    check(f"run {tipo} -> {esperado} registros", ok,
          f"{run.get('rows_affected')}/{esperado} | {run.get('detail', '')}")

    alvo = f"tstd_{tipo}_alvo"
    n_cat = linhas(alvo)
    sk_ok = sql(f"SELECT MIN({sk}) mn, MAX({sk}) mx, COUNT(DISTINCT {sk}) dist FROM {alvo}")
    seq_ok = bool(sk_ok) and sk_ok[0]["mn"] == 1 and sk_ok[0]["mx"] == esperado and sk_ok[0]["dist"] == esperado
    check(f"surrogate key sequencial 1..{esperado} ({tipo})", seq_ok, str(sk_ok[:1]))

    dist_ok = sql(f"SELECT COUNT(*) total, COUNT(DISTINCT {pk}) unicos FROM {alvo}")
    sem_duplicatas = bool(dist_ok) and dist_ok[0]["total"] == dist_ok[0]["unicos"]
    check(f"sem duplicatas de PK ({tipo})", sem_duplicatas, str(dist_ok[:1]))

    pv2 = c.post(f"/dimensions/{d['id']}/preview").json()
    check(f"preview apos o run ({tipo})", len(pv2.get("data", [])) > 0 and pv2["columns"][0] == sk)

# ---------- C. variantes ----------
print("\n[C] VARIANTES")

# 1. sem surrogate key
d1, _ = criar("tstd_sem_sk", "stg_vendas", "tstd_sem_sk_alvo", pk="produto", attrs=["produto"])
run = c.post(f"/dimensions/{d1['id']}/run").json()
n_dist = sql("SELECT COUNT(DISTINCT produto) n FROM stg_vendas")[0]["n"]
check("sem surrogate key (DISTINCT simples)",
      run.get("success") is True and run.get("rows_affected") == n_dist and "sk" not in "".join(colunas("tstd_sem_sk_alvo")),
      f"{run.get('rows_affected')} vs distintos={n_dist}")

# 2. attributes vazio -> todas as colunas
d2, _ = criar("tstd_todas_cols", "stg_vendas_parquet", "tstd_tcols_alvo", pk="id", sk="sk_t")
run = c.post(f"/dimensions/{d2['id']}/run").json()
origem_cols = colunas("stg_vendas_parquet")
alvo_cols = colunas("tstd_tcols_alvo")
todas = all(x in alvo_cols for x in origem_cols) and "sk_t" in alvo_cols
check("attributes vazio traz todas as colunas (*)", run.get("success") is True and todas, str(alvo_cols))

# 3. chaves naturais repetidas sao deduplicadas
d3, _ = criar("tstd_dedup", "stg_vendas", "tstd_dedup_alvo", pk="vendedor", sk="sk_v", attrs=["vendedor"])
run = c.post(f"/dimensions/{d3['id']}/run").json()
check("dedup de chave natural repetida (15 -> 4)", run.get("rows_affected") == 4, str(run)[:100])

# 4. SQL mode
seg_distintos = sql("SELECT COUNT(DISTINCT segmento) n FROM stg_clientes")[0]["n"]
d4, _ = criar("tstd_sqlmode", "stg_clientes", "tstd_sql_alvo", pk="segmento", modo="sql",
              custom_sql="SELECT DISTINCT segmento, UPPER(segmento) AS seg_maiusculo FROM _input WHERE segmento IS NOT NULL")
run = c.post(f"/dimensions/{d4['id']}/run").json()
pv = c.post(f"/dimensions/{d4['id']}/preview").json()
check("modo sql com _input", run.get("success") is True and run.get("rows_affected") == seg_distintos,
      f"{run.get('rows_affected')}/{seg_distintos}")
maiusculos_ok = all(str(r_["seg_maiusculo"]).isupper() for r_ in pv.get("data", []))
check("modo sql transformacao aplicada (UPPER)", maiusculos_ok, str(pv.get("data", [])[:2]))

# 5. update + re-run reflete mudanca
d5, _ = criar("tstd_rerun", "stg_clientes", "tstd_rerun_alvo", pk="id", sk="sk_rc", attrs=["nome"])
c.post(f"/dimensions/{d5['id']}/run")
antes = colunas("tstd_rerun_alvo")
c.put(f"/dimensions/{d5['id']}", json={"attributes": ["nome", "cidade"]})
run5 = c.post(f"/dimensions/{d5['id']}/run").json()
depois = colunas("tstd_rerun_alvo")
check("update + re-run reflete novos atributos",
      run5.get("success") is True and "cidade" in depois and "cidade" not in antes,
      f"run={str(run5)[:80]} | {antes} -> {depois}")

# ---------- D. erros tratados ----------
print("\n[D] TRATAMENTO DE ERROS")
de, _ = criar("tstd_fonteinexistente", "tabela_fantasma", "tstd_err1", pk="id")
presp = c.post(f"/dimensions/{de['id']}/preview")
runresp = c.post(f"/dimensions/{de['id']}/run")
check("fonte inexistente: preview/run -> 400", presp.status_code == 400 and runresp.status_code == 400)
status_depois = c.get(f"/dimensions/{de['id']}").json()["status"]
check("status marcado como error apos falha", status_depois == "error", status_depois)

dpk, _ = criar("tstd_pkinvalido", "stg_vendas", "tstd_err2", pk="coluna_nao_existe", sk="sk_x", attrs=["vendedor"])
resp = c.post(f"/dimensions/{dpk['id']}/run")
check("PK inexistente -> 400 tratado", resp.status_code == 400, f"status={resp.status_code}")

dbad, _ = criar("tstd_sqlinvalido", "stg_vendas", "tstd_err3", pk="x", modo="sql",
                custom_sql="SELECT * FROM nao_existe_nem_um_pouco")
resp = c.post(f"/dimensions/{dbad['id']}/run")
check("sql invalido -> 400 tratado", resp.status_code == 400, f"status={resp.status_code}")

check("preview inexistente -> 404", c.post("/dimensions/id-falso/preview").status_code == 404)
check("run inexistente -> 404", c.post("/dimensions/id-falso/run").status_code == 404)

# ---------- E. limpeza ----------
print("\n[E] LIMPEZA")
for did in ids_dim:
    c.delete(f"/dimensions/{did}")
restaram = [x["name"] for x in c.get("/dimensions").json() if x["name"].startswith("tstd_")]
removidas = sum(1 for t in alvos if c.delete(f"/catalog/tables/{t}").status_code in (200, 404))
check("limpeza de dimensions de teste", not restaram, str(restaram))
check(f"limpeza de {len(alvos)} tabelas de teste", removidas == len(alvos), f"{removidas}/{len(alvos)}")

falhas = [(n, dd) for n, p, dd in resultados if not p]
print("\n" + "=" * 78)
print(f"RESULTADO: {len(resultados) - len(falhas)}/{len(resultados)} testes aprovados")
if falhas:
    print("\nFALHAS:")
    for n, dd in falhas:
        print(f"  - {n}: {dd}")
import sys
sys.exit(0 if not falhas else 1)
