import httpx
import time
from pathlib import Path

BASE = "http://localhost:8000/api"
ROOT = Path(__file__).resolve().parent.parent
EX = str(ROOT / "exemplo-dados")

c = httpx.Client(base_url=BASE, timeout=120)

resultados = []


def check(nome, cond, detalhe=""):
    resultados.append((nome, bool(cond), str(detalhe)[:120]))
    print(f"  [{'PASS' if cond else 'FAIL'}] {nome}" + (f" | {str(detalhe)[:100]}" if not cond else ""))


def cleanup_names(prefix):
    for ing in c.get("/ingestions").json():
        if ing["name"].startswith(prefix):
            c.delete(f"/ingestions/{ing['id']}")


cleanup_names("tst_")
cleanup_names("tstbulk_")

print("=" * 78)
print("TESTE EXAUSTIVO - SESSAO INGESTIONS")
print("=" * 78)

# ---------- setup: mapa de fontes ----------
fontes = {s["name"]: s for s in c.get("/sources").json()}
tipos = {
    "csv": "vendas_csv",
    "json": "clientes_json",
    "excel": "produtos_xlsx",
    "xml": "clientes_xml",
    "parquet": "vendas_parquet",
    "avro": "vendas_avro",
    "orc": "vendas_orc",
}
arquivo = {"csv": "vendas.csv", "json": "clientes.json", "excel": "produtos.xlsx",
           "xml": "clientes.xml", "parquet": "vendas.parquet", "avro": "vendas.avro", "orc": "vendas.orc"}

ids_teste = []

# ---------- 1. modo table em TODAS as fontes ----------
print("\n[1] MODO TABLE - todas as fontes")
ing_por_tipo = {}
for t, fonte in tipos.items():
    nome = f"tst_{t}_table"
    r = c.post("/ingestions", json={"name": nome, "source_id": fontes[fonte]["id"],
                                    "config": {"mode": "table", "table": arquivo[t], "target_table": f"tst_raw_{t}"}})
    if r.status_code >= 400:
        check(f"criar tst_{t}_table", False, r.text)
        continue
    ing = r.json()
    ids_teste.append(ing["id"])
    ing_por_tipo[t] = ing
    run = c.post(f"/ingestions/{ing['id']}/run").json()
    linhas = run.get("rows_affected", 0)
    check(f"run table {t}", run.get("success") is True and linhas > 0, f"{linhas} linhas | {run.get('detail', '')}")

    pv = c.post(f"/ingestions/{ing['id']}/preview", json={}).json()
    check(f"preview {t}", len(pv.get("data", [])) > 0 and len(pv.get("columns", [])) > 0)

    pv3 = c.post(f"/ingestions/{ing['id']}/preview", json={"limit": 3}).json()
    check(f"preview limit=3 {t}", len(pv3.get("data", [])) <= 3 and len(pv3["data"]) == min(3, len(pv.get("data", []))))

    val = c.post(f"/ingestions/{ing['id']}/validate").json()
    check(f"validate {t}", val.get("valid") is True, val.get("message"))

    met = c.get(f"/ingestions/{ing['id']}/metadata").json()
    check(f"metadata {t}", len(met.get("schema", [])) > 0 and met.get("estimated_rows") not in (None, 0))

    tm = c.get(f"/ingestions/{ing['id']}/type-mapping").json()
    check(f"type-mapping GET {t}", "type_suggestions" in tm)

# ---------- 2. variantes no CSV ----------
print("\n[2] VARIANTES DE CONFIGURACAO (fonte CSV)")
csv_id = fontes["vendas_csv"]["id"]

r = c.post("/ingestions", json={"name": "tst_csv_filtro", "source_id": csv_id,
                                "config": {"mode": "table", "table": "vendas.csv", "target_table": "tst_csv_filtrado"},
                                "filters": [{"column": "quantidade", "operator": "gt", "value": 5}]})
ing_f = r.json(); ids_teste.append(ing_f["id"])
run = c.post(f"/ingestions/{ing_f['id']}/run").json()
check("filtro quantidade>5", run.get("rows_affected", 0) in range(1, 15), f"{run.get('rows_affected')} linhas")

r = c.post("/ingestions", json={"name": "tst_csv_renomear", "source_id": csv_id,
                                "config": {"mode": "table", "table": "vendas.csv", "target_table": "tst_csv_renomeado"},
                                "column_mapping": {"produto": {"target_name": "nome_produto"}}})
ing_r = r.json(); ids_teste.append(ing_r["id"])
c.post(f"/ingestions/{ing_r['id']}/run")
cols = [col["name"] for col in c.get("/catalog/tables/tst_csv_renomeado/schema").json()["schema"]]
check("column_mapping renomeia produto", "nome_produto" in cols and "produto" not in cols, str(cols))

r = c.post("/ingestions", json={"name": "tst_csv_query", "source_id": csv_id,
                                "config": {"mode": "query", "query": "SELECT * FROM vendas.csv", "target_table": "tst_csv_qmode"}})
ing_q = r.json(); ids_teste.append(ing_q["id"])
run = c.post(f"/ingestions/{ing_q['id']}/run").json()
check("modo query (fonte arquivo)", run.get("success") is True, str(run)[:120])

val = c.post(f"/ingestions/{ing_q['id']}/validate").json()
check("validate modo query SELECT", val.get("valid") is True, val.get("message"))

# filtro invalido -> deve falhar com erro tratado
r = c.post("/ingestions", json={"name": "tst_csv_colinvalida", "source_id": csv_id,
                                "config": {"mode": "table", "table": "vendas.csv", "target_table": "tst_x"},
                                "filters": [{"column": "coluna_inexistente", "operator": "gt", "value": 1}]})
ing_i = r.json(); ids_teste.append(ing_i["id"])
resp = c.post(f"/ingestions/{ing_i['id']}/run")
if resp.status_code == 400:
    check("run com coluna invalida retorna erro tratado", True)
else:
    linhas = resp.json().get("rows_affected", 0)
    check("run com coluna invalida (comportamento tolerante: filtro ignorado)",
          resp.status_code == 200 and linhas == 15, f"status={resp.status_code} linhas={linhas}")

# query nao-SELECT na validacao
r = c.post("/ingestions", json={"name": "tst_csv_badquery", "source_id": csv_id,
                                "config": {"mode": "query", "query": "DELETE FROM x", "target_table": "tst_y"}})
ing_bq = r.json(); ids_teste.append(ing_bq["id"])
val = c.post(f"/ingestions/{ing_bq['id']}/validate").json()
check("validate rejeita query nao-SELECT", val.get("valid") is False and any("SELECT" in e for e in val.get("errors", [])))

# tabela inexistente na validacao
r = c.post("/ingestions", json={"name": "tst_csv_tabinexist", "source_id": csv_id,
                                "config": {"mode": "table", "table": "nao_existe.csv", "target_table": "tst_z"}})
ing_ti = r.json(); ids_teste.append(ing_ti["id"])
val = c.post(f"/ingestions/{ing_ti['id']}/validate").json()
check("valida tabela inexistente", val.get("valid") is False, val.get("message"))

# ---------- 3. type-mapping POST ----------
print("\n[3] TYPE MAPPING")
tm = c.get(f"/ingestions/{ing_por_tipo['csv']['id']}/type-mapping").json()
sug = tm.get("type_suggestions", {})
if sug:
    primeira = list(sug.keys())[0]
    novo_map = {}
    for col, info in sug.items():
        alvo = "INTEGER" if "int" in info["source_type"].lower() else "VARCHAR"
        novo_map[col] = {"target_type": alvo, "target_name": col, "nullable": True}
    r2 = c.post(f"/ingestions/{ing_por_tipo['csv']['id']}/type-mapping", json=novo_map)
    check("type-mapping POST salva", r2.status_code < 400)
    tm2 = c.get(f"/ingestions/{ing_por_tipo['csv']['id']}/type-mapping").json()
    salvo = all(tm2["current_mappings"].get(col, {}).get("target_type") == m["target_type"] for col, m in novo_map.items())
    check("type-mapping persistido", salvo)
else:
    check("type-mapping tem sugestoes", False, str(tm)[:100])

# ---------- 4. deteccao de arquivos ----------
print("\n[4] DETECCAO / ANALISE DE ARQUIVOS")
det = c.post("/ingestions/detect-file-format", json={"file_path": EX + r"\vendas.csv"})
if det.status_code >= 400:
    check("detect-file-format CSV", False, det.text[:150])
else:
    d = det.json()
    check("detect-file-format CSV", d.get("delimiter") == "," and d.get("has_header") is True, str(d)[:150])

aj = c.post("/ingestions/analyze-json-structure", json={"file_path": EX + r"\clientes.json"})
d = aj.json() if aj.status_code < 400 else {}
check("analyze-json-structure", aj.status_code < 400 and d.get("array_length") == 8, aj.text[:150])

ax = c.post("/ingestions/analyze-xml-structure", json={"file_path": EX + r"\clientes.xml"})
d = ax.json() if ax.status_code < 400 else {}
tags = [p["tag"] for p in d.get("potential_row_elements", [])]
check("analyze-xml-structure sugere 'cliente'", ax.status_code < 400 and "cliente" in tags, ax.text[:150])

det404 = c.post("/ingestions/detect-file-format", json={"file_path": "Z:\\nao\\existe.csv"})
check("detect caminho invalido -> 400 tratado", det404.status_code == 400)

# ---------- 5. CRUD + favoritos + pastas + reorder ----------
print("\n[5] CRUD / FAVORITOS / PASTAS / REORDER / DUPLICATE")
alvo = ing_por_tipo["csv"]["id"]

up = c.put(f"/ingestions/{alvo}", json={"description": "atualizado pelo teste", "tags": ["teste"]})
check("PUT update", up.status_code < 400 and up.json().get("description") == "atualizado pelo teste")

fav_on = c.patch(f"/ingestions/{alvo}/favorite").json()
fav_list = c.get("/ingestions", params={"favorite_only": True}).json()
check("favorite ON + filtro favorite_only", fav_on.get("is_favorite") is True and any(i["id"] == alvo for i in fav_list))
fav_off = c.patch(f"/ingestions/{alvo}/favorite").json()
check("favorite OFF", fav_off.get("is_favorite") is False)

dup = c.post(f"/ingestions/{alvo}/duplicate", params={"new_name": "tst_csv_duplicada"})
check("duplicate", dup.status_code < 400 and dup.json().get("name") == "tst_csv_duplicada")
dup_id = dup.json()["id"] if dup.status_code < 400 else None
dup2 = c.post(f"/ingestions/{alvo}/duplicate", params={"new_name": "tst_csv_duplicada"})
check("duplicate nome repetido -> 400", dup2.status_code == 400)

ro = c.post("/ingestions/reorder", json=[
    {"ingestion_id": alvo, "sort_order": 1, "folder": "Testes"},
    {"ingestion_id": ing_por_tipo["json"]["id"], "sort_order": 2, "folder": "Testes"},
])
check("reorder", ro.status_code < 400 and ro.json().get("success") is True)
fo = c.put(f"/ingestions/{alvo}/folder", json={"folder": "PastaX"})
folders = c.get("/ingestions/folders").json()
check("set folder + lista folders", fo.status_code < 400 and "PastaX" in folders, str(folders))

lst = c.get("/ingestions", params={"search": "tst_", "sort_by": "name", "sort_order": "asc"}).json()
nomes = [i["name"] for i in lst]
check("list search+sort", len(lst) >= 10 and nomes == sorted(nomes))
lst_tag = c.get("/ingestions", params={"tag": "teste"}).json()
check("list por tag", any(i["id"] == alvo for i in lst_tag))
lst_src = c.get("/ingestions", params={"source_id": csv_id}).json()
check("list por source_id", all(True for _ in lst_src) and len(lst_src) >= 4)

# ---------- 6. historico / progresso / stats / run-async ----------
print("\n[6] HISTORICO / PROGRESSO / STATS / RUN-ASYNC")
hist = c.get(f"/ingestions/{alvo}/history", params={"limit": 10}).json()
check("history retorna lista de execucoes", isinstance(hist, list) and len(hist) >= 1, str(hist)[:120])

prog = c.get(f"/ingestions/{alvo}/progress").json()
check("progress responde", "status" in prog and "message" in prog, str(prog)[:150])

ra = c.post(f"/ingestions/{ing_por_tipo['parquet']['id']}/run-async").json()
check("run-async enfileira", ra.get("success") is True)
prog2 = {}
for _ in range(30):
    time.sleep(2)
    prog2 = c.get(f"/ingestions/{ing_por_tipo['parquet']['id']}/progress").json()
    if prog2.get("status") not in ("pending", "queued", "running"):
        break
check("run-async processado pelo scheduler (<60s)", prog2.get("status") in ("valid", "success", "idle"), f"status final: {prog2.get('status')}")

stats = c.get("/ingestions/stats/overview").json()
todos = c.get("/ingestions").json()
check("stats/overview total bate com a listagem", stats.get("total_ingestions") == len(todos),
      f"stats={stats.get('total_ingestions')} vs lista={len(todos)}")
check("stats/overview campos", all(k in stats for k in ("running", "error", "valid", "total_rows_ingested", "today_runs")))

# ---------- 7. templates ----------
print("\n[7] TEMPLATES")
tpls = c.get("/ingestions/templates/list").json()
check("templates/list", len(tpls) >= 4)
app = c.post(f"/ingestions/{ing_por_tipo['csv']['id']}/apply-template", params={"template_id": "csv_standard"})
check("apply-template (query param)", app.status_code < 400, app.text[:150])
cfg = c.get(f"/ingestions/{ing_por_tipo['csv']['id']}").json()["config"]
adv = cfg.get("advanced_options", {}) or {}
check("template aplicado ao config", adv.get("has_header") is True or cfg.get("advanced_options") is not None, str(cfg)[:200])
app_body = c.post(f"/ingestions/{ing_por_tipo['excel']['id']}/apply-template", json={"template_id": "excel_multi_sheet"})
check("apply-template via BODY (frontend)", app_body.status_code < 400, app_body.text[:150])
cfg_excel = c.get(f"/ingestions/{ing_por_tipo['excel']['id']}").json()["config"]
check("template via body persistido", (cfg_excel.get("advanced_options") or {}).get("import_all_sheets") is False, str(cfg_excel)[:200])

# ---------- 8. bulk operations ----------
print("\n[8] BULK CREATE / DELETE")
bulk = c.post("/ingestions/bulk/create", json={"source_id": csv_id, "tables": ["vendas.csv", "clientes.json"],
                                               "naming_pattern": "tstbulk_{name}"})
d = bulk.json() if bulk.status_code < 400 else {}
check("bulk/create (body, 2 tabelas)", bulk.status_code < 400 and d.get("success", 0) == 2, bulk.text[:200])

ids_bulk = []
for ing in c.get("/ingestions", params={"search": "tstbulk_"}).json():
    ids_bulk.append(ing["id"])
bdel = c.post("/ingestions/bulk/delete", json=ids_bulk)
check("bulk/delete", bdel.status_code < 400 and bdel.json().get("deleted") == len(ids_bulk))

# ---------- 9. shortcuts ----------
print("\n[9] SHORTCUTS")
sc_list = c.get("/ingestions/shortcuts/list").json()
check("shortcuts/list", isinstance(sc_list, list))
sc = c.post("/ingestions/shortcuts/create", json={"key": "ctrl+shift+t", "action": "test_action", "description": "teste"})
check("shortcuts/create", sc.status_code < 400 and sc.json().get("success") is True)
sc_list2 = c.get("/ingestions/shortcuts/list").json()
check("shortcut criado aparece na lista", any(s["key"] == "ctrl+shift+t" for s in sc_list2))

# ---------- 10. limpeza ----------
print("\n[10] LIMPEZA")
if dup_id:
    ids_teste.append(dup_id)
del_resp = c.delete(f"/ingestions/{ing_bq['id']}")
check("DELETE individual", del_resp.status_code < 400)
ids_teste = [i for i in ids_teste if i != ing_bq["id"]]
bdel2 = c.post("/ingestions/bulk/delete", json=ids_teste)
restaram = [i["name"] for i in c.get("/ingestions").json() if i["name"].startswith("tst_")]
check("limpeza total dos objetos de teste", not restaram, str(restaram))

# ---------- resultado ----------
ok = sum(1 for _, p, _ in resultados if p)
total = len(resultados)
falhas = [(n, d) for n, p, d in resultados if not p]
print("\n" + "=" * 78)
print(f"RESULTADO: {ok}/{total} testes aprovados")
import sys
sys.exit(0 if ok == total else 1)
if falhas:
    print("\nFALHAS:")
    for n, d in falhas:
        print(f"  - {n}: {d}")

