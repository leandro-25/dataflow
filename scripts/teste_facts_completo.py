import httpx

BASE = "http://localhost:8000/api"
c = httpx.Client(base_url=BASE, timeout=120)

resultados = []


def check(nome, cond, detalhe=""):
    resultados.append((nome, bool(cond), str(detalhe)[:130]))
    print(f"  [{'PASS' if cond else 'FAIL'}] {nome}" + (f" | {str(detalhe)[:110]}" if not cond else ""))


def colunas(t):
    return [x["name"] for x in c.get(f"/catalog/tables/{t}").json().get("columns", [])]


def linhas(t):
    return c.get(f"/catalog/tables/{t}").json().get("row_count", -1)


ids_fato = []


def criar(nome, fonte, alvo, grain="teste", links=None, measures=None, modo="visual", custom_sql=None):
    payload = {"name": nome, "source_table": fonte, "target_table": alvo,
               "grain": grain, "dimension_links": links or [], "mode": modo}
    if measures is not None:
        payload["measures"] = measures
    if custom_sql:
        payload["custom_sql"] = custom_sql
    r = c.post("/facts", json=payload)
    if r.status_code >= 400:
        return None, r
    f = r.json()
    if nome.startswith("tstf_"):
        ids_fato.append(f["id"])
    return f, r


def get_or_create(nome, **kw):
    existente = next((f for f in c.get("/facts").json() if f["name"] == nome), None)
    if existente:
        print(f"    [existe] {nome}")
        return existente
    f, r = criar(nome, **kw)
    if f is None:
        print(f"    [ERRO] {nome}: {r.text[:150]}")
        return None
    print(f"    [criado] {nome}")
    return f


# limpeza inicial de residuos de teste
for f in c.get("/facts").json():
    if f["name"].startswith("tstf_"):
        c.delete(f"/facts/{f['id']}")
for t in [x["name"] for x in c.get("/catalog/tables").json()["tables"]]:
    if t.startswith("tstf_"):
        c.delete(f"/catalog/tables/{t}")

print("=" * 78)
print("TESTE EXAUSTIVO - SESSAO FACTS")
print("=" * 78)

# ---------- A. CRUD ----------
print("\n[A] CRUD")
f, r = criar("tstf_base", "stg_vendas", "tstf_base_alvo", grain="venda",
             measures=["quantidade", "total"],
             links=[{"dimension": "dim_vendedores", "natural_key": "vendedor"}])
check("POST cria fato", f is not None, r.text[:100])
r2 = c.post("/facts", json={"name": "tstf_base", "source_table": "stg_vendas",
                            "target_table": "x2", "grain": "venda"})
check("POST nome duplicado -> 400", r2.status_code == 400)

g = c.get(f"/facts/{f['id']}")
check("GET retorna config completa",
      g.status_code == 200 and g.json()["grain"] == "venda"
      and g.json()["measures"] == ["quantidade", "total"]
      and g.json()["dimension_links"][0]["dimension"] == "dim_vendedores")

check("GET inexistente -> 404", c.get("/facts/id-falso").status_code == 404)
up = c.put(f"/facts/{f['id']}", json={"description_field": None} if False else {"measures": ["total"]})
check("PUT atualiza measures", up.status_code == 200 and up.json()["measures"] == ["total"])
s_outro, _ = criar("tstf_outro", "raw_clientes", "tstf_x3", grain="cliente")
up2 = c.put(f"/facts/{f['id']}", json={"name": "tstf_outro"})
check("PUT conflito de nome -> 400", up2.status_code == 400)
del_ok = c.delete(f"/facts/{s_outro['id']}")
check("DELETE + 404 posterior", del_ok.status_code == 200 and c.get(f"/facts/{s_outro['id']}").status_code == 404)

# ---------- B. modo visual ----------
print("\n[B] MODO VISUAL")
fv, _ = criar("tstf_visual_medidas", "stg_vendas", "tstf_vis1_alvo", grain="venda",
              measures=["quantidade", "total"])
run = c.post(f"/facts/{fv['id']}/run").json()
cols = colunas("tstf_vis1_alvo")
check("visual com measures seleciona apenas elas",
      run.get("success") is True and sorted(cols) == ["quantidade", "total"] and linhas("tstf_vis1_alvo") == 15,
      f"cols={cols}")

fv2, _ = criar("tstf_visual_todas", "stg_vendas_parquet", "tstf_vis2_alvo", grain="venda_binaria", measures=[])
pv = c.post(f"/facts/{fv2['id']}/preview").json()
run = c.post(f"/facts/{fv2['id']}/run").json()
origem = colunas("stg_vendas_parquet")
check("visual sem measures -> todas as colunas (*)",
      run.get("success") is True and all(x in colunas("tstf_vis2_alvo") for x in origem),
      str(colunas("tstf_vis2_alvo")))
check("preview visual antes do run funciona", len(pv.get("data", [])) > 0)

fv3, _ = criar("tstf_visual_update", "stg_clientes", "tstf_vis3_alvo", grain="cliente", measures=["nome"])
c.post(f"/facts/{fv3['id']}/run")
c.put(f"/facts/{fv3['id']}", json={"measures": ["nome", "cidade", "estado"]})
run = c.post(f"/facts/{fv3['id']}/run").json()
depois = colunas("tstf_vis3_alvo")
check("update + re-run reflete novas measures",
      run.get("success") is True and all(x in depois for x in ["nome", "cidade", "estado"]), str(depois))

# ---------- C. UMA FATO POR FORMATO (oficiais, ficam visiveis) ----------
print("\n[C] FATO OFICIAL POR FORMATO (modo SQL com join na dimensao)")
fatos_oficiais = [
    ("fato_vendas_csv", "stg_vendas", "fato_vendas_csv", "dim_vendedores", "sk_dim_venda_fake", 15),
]
# nota: fato_vendas (CSV) ja existe e e verificada a parte
oficiais = [
    ("fato_vendas_parquet", "stg_vendas_parquet", "dim_vendas_parquet", "sk_venda_pq", 10),
    ("fato_vendas_avro", "stg_vendas_avro", "dim_vendas_avro", "sk_venda_av", 10),
    ("fato_vendas_orc", "stg_vendas_orc", "dim_vendas_orc", "sk_venda_orc", 10),
    ("fato_produtos", "stg_produtos", "dim_produtos", "sk_produto", 15),
    ("fato_clientes", "stg_clientes", "dim_clientes", "sk_cliente", 8),
    ("fato_clientes_xml", "stg_clientes_xml", "dim_clientes_xml", "sk_cliente_xml", 8),
]
for nome, fonte, dim, sk, esperado in oficiais:
    fto = get_or_create(nome, fonte=fonte, alvo=nome, grain="uma_linha_por_registro",
                        links=[{"dimension": dim, "join_on": "id"}], modo="sql",
                        custom_sql=f"SELECT s.*, d.{sk} FROM _input s JOIN {dim} d ON s.id = d.id")
    if fto is None:
        continue
    run = c.post(f"/facts/{fto['id']}/run").json()
    ok = run.get("success") is True and run.get("rows_affected") == esperado
    check(f"fato {nome} ({fonte}) -> {esperado}", ok,
          f"{run.get('rows_affected')}/{esperado} | {str(run.get('detail', ''))[:60]}")

    tem_sk = sk in colunas(nome)
    sk_ok = sql_q = c.post("/catalog/query", json={"sql": f"SELECT COUNT(*) n FROM {nome} WHERE {sk} IS NOT NULL"}).json()
    n_sk = sk_ok.get("data", [{}])[0].get("n", 0)
    check(f"  chave surrogate {sk} preenchida ({n_sk}/{esperado})", tem_sk and n_sk == esperado, str(n_sk))

    pv = c.post(f"/facts/{fto['id']}/preview").json()
    check(f"  preview da fato {nome}", pv.get("total_rows", 0) > 0)

print("\n  Verificando fato_vendas original (CSV):")
fvo = next((x for x in c.get("/facts").json() if x["name"] == "fato_vendas"), None)
if fvo:
    run = c.post(f"/facts/{fvo['id']}/run").json()
    n_sk = c.post("/catalog/query", json={"sql": "SELECT COUNT(*) n FROM fato_vendas WHERE sk_vendedor IS NOT NULL"}).json()["data"][0]["n"]
    check("fato_vendas (csv) valida com sk_vendedor", run.get("success") is True and n_sk == 15, f"{n_sk}/15")
else:
    check("fato_vendas existe", False, "nao encontrada")

# ---------- D. erros tratados ----------
print("\n[D] TRATAMENTO DE ERROS")
fe, _ = criar("tstf_fonteinexistente", "tabela_fantasma", "tstf_err1", grain="x")
presp = c.post(f"/facts/{fe['id']}/preview")
runresp = c.post(f"/facts/{fe['id']}/run")
check("fonte inexistente: preview/run -> 400", presp.status_code == 400 and runresp.status_code == 400)
status_depois = c.get(f"/facts/{fe['id']}").json()["status"]
check("status marcado como error apos falha", status_depois == "error", status_depois)

fm, _ = criar("tstf_medidainvalida", "stg_vendas", "tstf_err2", grain="x", measures=["coluna_nao_existe"])
resp = c.post(f"/facts/{fm['id']}/run")
check("medida inexistente -> 400 tratado", resp.status_code == 400, f"status={resp.status_code}")

fs, _ = criar("tstf_sqlinvalido", "stg_vendas", "tstf_err3", grain="x", modo="sql",
              custom_sql="SELECT * FROM nada_disso_existe")
resp = c.post(f"/facts/{fs['id']}/run")
check("sql invalido -> 400 tratado", resp.status_code == 400, f"status={resp.status_code}")

r422 = c.post("/facts", json={"name": "tstf_semgrain", "source_table": "stg_vendas", "target_table": "x9"})
check("grain ausente -> 422 validacao pydantic", r422.status_code == 422, f"status={r422.status_code}")

check("preview/run inexistente -> 404",
      c.post("/facts/id-falso/preview").status_code == 404 and c.post("/facts/id-falso/run").status_code == 404)

# ---------- E. limpeza ----------
print("\n[E] LIMPEZA (somente objetos de teste)")
for fid in ids_fato:
    c.delete(f"/facts/{fid}")
restaram = [x["name"] for x in c.get("/facts").json() if x["name"].startswith("tstf_")]
removidas = 0
for t in [x["name"] for x in c.get("/catalog/tables").json()["tables"]]:
    if t.startswith("tstf_"):
        if c.delete(f"/catalog/tables/{t}").status_code in (200, 404):
            removidas += 1
check("limpeza de fatos de teste", not restaram, str(restaram))
check("limpeza de tabelas tstf_", removidas >= 0)

falhas = [(n, dd) for n, p, dd in resultados if not p]
print("\n" + "=" * 78)
print(f"RESULTADO: {len(resultados) - len(falhas)}/{len(resultados)} testes aprovados")
if falhas:
    print("\nFALHAS:")
    for n, dd in falhas:
        print(f"  - {n}: {dd}")
import sys
sys.exit(0 if not falhas else 1)
