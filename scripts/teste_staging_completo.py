import httpx

BASE = "http://localhost:8000/api"
c = httpx.Client(base_url=BASE, timeout=120)

resultados = []


def check(nome, cond, detalhe=""):
    resultados.append((nome, bool(cond), str(detalhe)[:130]))
    print(f"  [{'PASS' if cond else 'FAIL'}] {nome}" + (f" | {str(detalhe)[:110]}" if not cond else ""))


def sql(query):
    r = c.post("/catalog/query", json={"sql": query})
    return r.json().get("data", []) if r.status_code < 400 else {"__erro": r.text}


def colunas(t):
    return [x["name"] for x in c.get(f"/catalog/tables/{t}").json().get("columns", [])]


def linhas(t):
    return c.get(f"/catalog/tables/{t}").json().get("row_count", -1)


ids_stg = []
alvos = []


def criar(nome, fonte, alvo, transforms=None, modo="visual", custom_sql=None):
    payload = {"name": nome, "source_table": fonte, "target_table": alvo,
               "transforms": transforms or [], "mode": modo}
    if custom_sql:
        payload["custom_sql"] = custom_sql
    r = c.post("/staging", json=payload)
    if r.status_code >= 400:
        return None, r
    s = r.json()
    ids_stg.append(s["id"])
    alvos.append(alvo)
    return s, r


# limpeza inicial de residuos
for s in c.get("/staging").json():
    if s["name"].startswith("tst_"):
        c.delete(f"/staging/{s['id']}")
for t in [x["name"] for x in c.get("/catalog/tables").json()["tables"]]:
    if t.startswith("tst_"):
        c.delete(f"/catalog/tables/{t}")

print("=" * 78)
print("TESTE EXAUSTIVO - SESSAO STAGING")
print("=" * 78)

# ---------- A. tipos de transformacao ----------
print("\n[A] TRANSFORM TYPES")
tt = c.get("/staging/transforms/types").json()
tipos_api = {t["type"] for t in tt}
esperados = {"rename", "cast", "filter", "deduplicate", "fill_null", "sort", "limit",
             "add_column", "remove_columns", "select_columns", "uppercase", "lowercase",
             "trim", "replace", "split", "merge", "custom_sql"}
check("GET transforms/types retorna 17 tipos", len(tt) == 17, f"{len(tt)}")
check("todos os tipos esperados presentes", esperados <= tipos_api, str(esperados - tipos_api))
check("schema de config presente em cada tipo", all("config_schema" in t and "label" in t for t in tt))

# ---------- B. CRUD ----------
print("\n[B] CRUD")
s, r = criar("tst_stg_base", "raw_vendas", "tst_base")
check("POST cria staging", s is not None, r.text[:100])
r2 = c.post("/staging", json={"name": "tst_stg_base", "source_table": "raw_vendas", "target_table": "tst_x2"})
check("POST nome duplicado -> 400", r2.status_code == 400)

g = c.get(f"/staging/{s['id']}")
check("GET por id", g.status_code == 200 and g.json()["name"] == "tst_stg_base")
g404 = c.get("/staging/id-inexistente")
check("GET inexistente -> 404", g404.status_code == 404)

up = c.put(f"/staging/{s['id']}", json={"transforms": [{"type": "limit", "config": {"rows": 7}}]})
check("PUT atualiza transforms", up.status_code == 200 and up.json()["transforms"][0]["config"]["rows"] == 7)
s2, _ = criar("tst_stg_outro", "raw_clientes", "tst_x3")
up2 = c.put(f"/staging/{s['id']}", json={"name": "tst_stg_outro"})
check("PUT conflito de nome -> 400", up2.status_code == 400)

pv_vazio = c.post(f"/staging/{s['id']}/preview").json()
check("preview com limit=7 aplicado", pv_vazio.get("total_rows") == 7, str(pv_vazio.get("total_rows")))

del_ok = c.delete(f"/staging/{s2['id']}")
check("DELETE staging", del_ok.status_code == 200)
check("DELETE remove da listagem", c.get(f"/staging/{s2['id']}").status_code == 404)

# ---------- C. basico em TODAS as fontes ----------
print("\n[C] STAGING BASICO EM TODAS AS FONTES")
fontes_tabela = [
    ("csv", "raw_vendas", 15),
    ("json", "raw_clientes", 8),
    ("excel", "raw_produtos", 15),
    ("xml", "raw_clientes_xml", 8),
    ("parquet", "raw_vendas_parquet", 10),
    ("avro", "raw_vendas_avro", 10),
    ("orc", "raw_vendas_orc", 10),
]
for tipo, tabela, qtd in fontes_tabela:
    nome = f"tst_stg_{tipo}"
    s, r = criar(nome, tabela, f"tst_alvo_{tipo}", [{"type": "trim", "config": {"columns": []}}])
    if s is None:
        check(f"criar staging {tipo}", False, r.text[:100])
        continue
    run = c.post(f"/staging/{s['id']}/run").json()
    ok = run.get("success") is True and run.get("rows_affected") == qtd
    check(f"run {tipo} ({tabela})", ok, f"{run.get('rows_affected')}/{qtd} | {run.get('detail', '')}")

# ---------- D. cada transformacao isoladamente ----------
print("\n[D] TRANSFORMACOES INDIVIDUAIS (fonte raw_vendas, 15 linhas)")


def teste_transform(nome, transforms, condicao, detalhe_esperado=""):
    s, r = criar(f"tst_tf_{nome}", "raw_vendas", f"tst_tf_{nome}_alvo", transforms)
    if s is None:
        check(f"transform {nome}", False, r.text[:100])
        return
    run = c.post(f"/staging/{s['id']}/run").json()
    if run.get("success") is not True:
        check(f"transform {nome}", False, str(run)[:110])
        return
    ok, det = condicao()
    check(f"transform {nome}", ok, det)


teste_transform(
    "rename", [{"type": "rename", "config": {"data": "data_venda"}}],
    lambda: ("data_venda" in colunas("tst_tf_rename_alvo") and "data" not in colunas("tst_tf_rename_alvo"), str(colunas("tst_tf_rename_alvo"))))

teste_transform(
    "cast_data", [{"type": "cast", "config": {"data": "date"}}],
    lambda: (sql("SELECT COUNT(*) n FROM tst_tf_cast_data_alvo WHERE TRY_CAST(data AS DATE) IS NOT NULL")[0]["n"] == 15, ""))

# filtros numericos com contagem esperada
def filtro(op, val, esperado, slug):
    s, r = criar(f"tst_flt_{slug}", "raw_vendas", f"tst_flt_{slug}_alvo",
                 [{"type": "filter", "config": {"column": "quantidade", "operator": op, "value": val}}])
    if s is None:
        check(f"filtro {op} {val}", False, r.text[:100]); return
    run = c.post(f"/staging/{s['id']}/run").json()
    got = run.get("rows_affected")
    check(f"filtro {op} {val} -> {esperado}", run.get("success") is True and got == esperado, f"obtido={got}")


filtro("=", 1, 6, "eq1")
filtro("!=", 1, 9, "ne1")
filtro(">", 5, 2, "gt5")
filtro(">=", 3, 6, "gte3")
filtro("<", 3, 9, "lt3")
filtro("<=", 2, 9, "lte2")

teste_transform(
    "filtro_in", [{"type": "filter", "config": {"column": "produto", "operator": "in", "value": ["Notebook Dell", "Webcam HD"]}}],
    lambda: (linhas("tst_tf_filtro_in_alvo") == 3, f"{linhas('tst_tf_filtro_in_alvo')}/3"))

teste_transform(
    "filtro_not_in", [{"type": "filter", "config": {"column": "produto", "operator": "not_in", "value": ["Notebook Dell", "Webcam HD"]}}],
    lambda: (linhas("tst_tf_filtro_not_in_alvo") == 12, f"{linhas('tst_tf_filtro_not_in_alvo')}/12"))

teste_transform(
    "filtro_contains", [{"type": "filter", "config": {"column": "produto", "operator": "contains", "value": "Notebook"}}],
    lambda: (linhas("tst_tf_filtro_contains_alvo") == 4, f"{linhas('tst_tf_filtro_contains_alvo')}/4"))

teste_transform(
    "filtro_is_null", [{"type": "filter", "config": {"column": "vendedor", "operator": "is_null"}}],
    lambda: (linhas("tst_tf_filtro_is_null_alvo") == 0, ""))

teste_transform(
    "filtro_is_not_null", [{"type": "filter", "config": {"column": "vendedor", "operator": "is_not_null"}}],
    lambda: (linhas("tst_tf_filtro_is_not_null_alvo") == 15, ""))

teste_transform(
    "deduplicate_produto", [{"type": "deduplicate", "config": {"keys": ["produto"], "keep": "first"}}],
    lambda: (linhas("tst_tf_deduplicate_produto_alvo") == 14, f"{linhas('tst_tf_deduplicate_produto_alvo')}/14"))

teste_transform(
    "fill_null_valor", [{"type": "fill_null", "config": {"column": "vendedor", "value": "SEM VENDEDOR"}}],
    lambda: (sql("SELECT COUNT(*) n FROM tst_tf_fill_null_valor_alvo WHERE vendedor IS NULL")[0]["n"] == 0, ""))

teste_transform(
    "sort_desc", [{"type": "sort", "config": {"column": "total", "order": "desc"}}],
    lambda: (sql("SELECT id FROM tst_tf_sort_desc_alvo LIMIT 1")[0]["id"] == 10, ""))

teste_transform(
    "limit_5", [{"type": "limit", "config": {"rows": 5}}],
    lambda: (linhas("tst_tf_limit_5_alvo") == 5, f"{linhas('tst_tf_limit_5_alvo')}/5"))

teste_transform(
    "add_column", [{"type": "add_column", "config": {"name": "conferencia", "expression": "quantidade * valor_unitario"}}],
    lambda: ("conferencia" in colunas("tst_tf_add_column_alvo"), ""))

teste_transform(
    "remove_columns", [{"type": "remove_columns", "config": {"columns": ["valor_unitario"]}}],
    lambda: ("valor_unitario" not in colunas("tst_tf_remove_columns_alvo"), ""))

teste_transform(
    "select_columns", [{"type": "select_columns", "config": {"columns": ["id", "produto"]}}],
    lambda: (sorted(colunas("tst_tf_select_columns_alvo")) == ["id", "produto"], str(colunas("tst_tf_select_columns_alvo"))))

teste_transform(
    "uppercase", [{"type": "uppercase", "config": {"columns": ["vendedor"]}}],
    lambda: (sql("SELECT COUNT(*) n FROM tst_tf_uppercase_alvo WHERE vendedor LIKE 'JOÃO%'")[0]["n"] == 5, ""))

teste_transform(
    "lowercase", [{"type": "lowercase", "config": {"columns": ["vendedor"]}}],
    lambda: (sql("SELECT COUNT(*) n FROM tst_tf_lowercase_alvo WHERE vendedor LIKE 'joão%'")[0]["n"] == 5, ""))

teste_transform(
    "trim", [{"type": "trim", "config": {"columns": ["vendedor"]}}],
    lambda: (linhas("tst_tf_trim_alvo") == 15, ""))

teste_transform(
    "split", [{"type": "split", "config": {"column": "vendedor", "delimiter": " ", "into": ["nome", "sobrenome"]}}],
    lambda: (all(x in colunas("tst_tf_split_alvo") for x in ["nome", "sobrenome"])
             and "vendedor" not in colunas("tst_tf_split_alvo"), str(colunas("tst_tf_split_alvo"))))

teste_transform(
    "merge", [{"type": "merge", "config": {"columns": ["produto", "vendedor"], "into": "linha", "separator": " - "}}],
    lambda: ("linha" in colunas("tst_tf_merge_alvo"), ""))

teste_transform(
    "replace", [{"type": "replace", "config": {"column": "produto", "find": "Notebook", "replace": "NB"}}],
    lambda: (sql("SELECT COUNT(*) n FROM tst_tf_replace_alvo WHERE produto LIKE 'NB%'")[0]["n"] == 4, ""))

# ---------- E. pipeline combinado ----------
print("\n[E] PIPELINE COMBINADO (guia oficial)")
combo = [
    {"type": "rename", "config": {"data": "data_venda"}},
    {"type": "cast", "config": {"data_venda": "date"}},
    {"type": "filter", "config": {"column": "quantidade", "operator": ">", "value": 0}},
    {"type": "add_column", "config": {"name": "ano", "expression": "EXTRACT(YEAR FROM data_venda)"}},
    {"type": "add_column", "config": {"name": "mes", "expression": "EXTRACT(MONTH FROM data_venda)"}},
    {"type": "sort", "config": {"column": "data_venda", "order": "asc"}},
]
s_combo, r = criar("tst_stg_combo", "raw_vendas", "tst_combo_alvo", combo)
run = c.post(f"/staging/{s_combo['id']}/run").json()
ok_cols = all(x in colunas("tst_combo_alvo") for x in ["data_venda", "ano", "mes"]) and "data" not in colunas("tst_combo_alvo")
tipos_ok = sql("SELECT COUNT(*) n FROM tst_combo_alvo WHERE TRY_CAST(data_venda AS DATE) IS NOT NULL")[0]["n"] == 15
check("pipeline combinado (rename+cast+filter+add+sort)", run.get("success") is True and ok_cols and tipos_ok,
      f"run={run.get('detail', '')} cols={colunas('tst_combo_alvo')}")

# ---------- F. modo SQL ----------
print("\n[F] MODO SQL (custom_sql com _input)")
s_sql, r = criar("tst_stg_sqlmode", "raw_vendas", "tst_sql_alvo", modo="sql",
                 custom_sql="SELECT vendedor, SUM(total) AS total_vendido, COUNT(*) AS vendas FROM _input GROUP BY vendedor ORDER BY total_vendido DESC")
if s_sql:
    run = c.post(f"/staging/{s_sql['id']}/run").json()
    check("modo sql agrupa por vendedor", run.get("success") is True and run.get("rows_affected") == 4, str(run)[:110])
    pv = c.post(f"/staging/{s_sql['id']}/preview").json()
    primeiro = pv["data"][0] if pv.get("data") else {}
    check("preview modo sql ordenado desc", primeiro.get("vendedor") == "Ana Costa", str(primeiro))
else:
    check("modo sql criado", False, r.text[:100])

# ---------- G. modo yaml ----------
print("\n[G] MODO YAML (tratado como visual)")
s_yaml, r = criar("tst_stg_yamlmode", "raw_vendas", "tst_yaml_alvo",
                  [{"type": "limit", "config": {"rows": 3}}], modo="yaml")
if s_yaml:
    run = c.post(f"/staging/{s_yaml['id']}/run").json()
    check("modo yaml executa como visual", run.get("success") is True and run.get("rows_affected") == 3, str(run)[:110])
else:
    check("modo yaml criado", False, r.text[:100])

# ---------- H. erros tratados ----------
print("\n[H] TRATAMENTO DE ERROS")
s_err, _ = criar("tst_stg_fonteinexistente", "tabela_que_nao_existe", "tst_err1")
resp = c.post(f"/staging/{s_err['id']}/preview")
check("preview fonte inexistente -> 400", resp.status_code == 400, f"status={resp.status_code}")
resp = c.post(f"/staging/{s_err['id']}/run")
check("run fonte inexistente -> 400", resp.status_code == 400, f"status={resp.status_code}")

s_bad, _ = criar("tst_stg_expreinvalida", "raw_vendas", "tst_err2",
                 [{"type": "add_column", "config": {"name": "x", "expression": "coluna_nao_existe * 2"}}])
resp = c.post(f"/staging/{s_bad['id']}/run")
check("run expressao invalida -> 400", resp.status_code == 400, f"status={resp.status_code}")

s_op, _ = criar("tst_stg_opinvalido", "raw_vendas", "tst_err3",
                [{"type": "filter", "config": {"column": "quantidade", "operator": "regex", "value": ".*"}}])
resp = c.post(f"/staging/{s_op['id']}/run")
check("run operador invalido -> 400", resp.status_code == 400, f"status={resp.status_code}")

pv404 = c.post("/staging/id-inexistente/preview")
run404 = c.post("/staging/id-inexistente/run")
check("preview/run inexistentes -> 404", pv404.status_code == 404 and run404.status_code == 404)

# ---------- I. limpeza ----------
print("\n[I] LIMPEZA")
for sid in ids_stg:
    c.delete(f"/staging/{sid}")
restaram_stg = [s["name"] for s in c.get("/staging").json() if s["name"].startswith("tst_")]
removidas_tabela = 0
for t in alvos:
    rr = c.delete(f"/catalog/tables/{t}")
    # 200 = removida; 404 = nunca foi criada (preview-only ou run com erro)
    if rr.status_code in (200, 404):
        removidas_tabela += 1
check("limpeza de stagings de teste", not restaram_stg, str(restaram_stg))
check(f"limpeza de {len(alvos)} tabelas de teste", removidas_tabela == len(alvos), f"{removidas_tabela}/{len(alvos)}")

falhas = [(n, d) for n, p, d in resultados if not p]
print("\n" + "=" * 78)
print(f"RESULTADO: {len(resultados) - len(falhas)}/{len(resultados)} testes aprovados")
import sys
sys.exit(0 if not falhas else 1)
if falhas:
    print("\nFALHAS:")
    for n, d in falhas:
        print(f"  - {n}: {d}")
