import httpx

BASE = "http://localhost:8000/api"
c = httpx.Client(base_url=BASE, timeout=120)

resultados = []


def check(nome, cond, detalhe=""):
    resultados.append((nome, bool(cond), str(detalhe)[:130]))
    print(f"  [{'PASS' if cond else 'FAIL'}] {nome}" + (f" | {str(detalhe)[:110]}" if not cond else ""))


stg_antes = len(c.get("/staging").json())

print("=" * 78)
print("TESTE - STAGING WIZARD / DRY-RUN")
print("=" * 78)

# ---------- A. DRY-RUN BASICO ----------
print("\n[A] DRY-RUN SEM TRANSFORMACOES")
r = c.post("/staging/dry-run", json={"source_table": "raw_vendas", "transforms": [], "limit": 20})
if r.status_code >= 400:
    check("dry-run basico", False, r.text[:120])
    d = {}
else:
    d = r.json()
    check("retorna amostra completa", d.get("total_rows") == 15 and d.get("source_total_rows") == 15,
          f"{d.get('total_rows')}/{d.get('source_total_rows')}")
    check("colunas presentes", len(d.get("columns", [])) == 7, str(d.get("columns")))
    check("sql gerado visivel e eh SELECT", isinstance(d.get("sql"), str) and d["sql"].strip().upper().startswith("SELECT"),
          d.get("sql", "")[:80])
    check("limit aplicado", c.post("/staging/dry-run", json={"source_table": "raw_vendas", "transforms": [], "limit": 3}).json().get("total_rows") == 3)

# ---------- B. COM TRANSFORMACOES ----------
print("\n[B] DRY-RUN COM TRANSFORMACOES")
resp_b = c.post("/staging/dry-run", json={
    "source_table": "raw_vendas",
    "transforms": [
        {"type": "rename", "config": {"data": "data_venda"}},
        {"type": "cast", "config": {"data_venda": "date"}},
        {"type": "filter", "config": {"column": "quantidade", "operator": ">", "value": 5}},
    ],
    "limit": 50,
})
d = resp_b.json() if resp_b.status_code < 400 else {}
check("rename+cast+filter combinados",
      resp_b.status_code == 200 and "data_venda" in d.get("columns", []) and d.get("total_rows") == 2,
      f"cols={d.get('columns')} rows={d.get('total_rows')}")

check("cast para data funcionou na amostra",
      all(x.get("data_venda") for x in d.get("data", [])) and len(d.get("data", [])) > 0)

# deduplicate
r = c.post("/staging/dry-run", json={
    "source_table": "raw_vendas",
    "transforms": [{"type": "deduplicate", "config": {"keys": ["produto"], "keep": "first"}}],
}).json()
check("deduplicate produto -> 14", r.json() if isinstance(r, httpx.Response) else r).get("total_rows") == 14 if False else check(
    "deduplicate produto -> 14", isinstance(r, dict) and r.get("total_rows") == 14, str(r.get("total_rows")))

# receita limpar textos (trim em todas as colunas de texto)
r = c.post("/staging/dry-run", json={
    "source_table": "raw_clientes",
    "transforms": [{"type": "trim", "config": {"columns": ["nome", "cidade"]}}],
}).json()
check("receita trim multi-colunas", r.get("total_rows") == 8)

# sugestao de cast em coluna de texto com data
r = c.post("/staging/dry-run", json={
    "source_table": "raw_clientes",
    "transforms": [{"type": "cast", "config": {"data_cadastro": "date"}}],
}).json()
datas_ok = all(x.get("data_cadastro") for x in r.get("data", []))
check("sugestao cast data_cadastro->date valida", datas_ok and r.get("total_rows") == 8)

# ---------- C. MODO SQL ----------
print("\n[C] MODO SQL")
r = c.post("/staging/dry-run", json={
    "source_table": "stg_vendas",
    "mode": "sql",
    "custom_sql": "SELECT vendedor, SUM(total) AS t FROM _input GROUP BY vendedor ORDER BY t DESC",
}).json()
check("modo sql com _input", r.get("total_rows") == 4 and r["data"][0]["vendedor"] == "Ana Costa",
      str(r.get("data", [{}])[:1]))

# ---------- D. ERROS ----------
print("\n[D] ERROS TRATADOS")
check("origem inexistente -> 400", c.post("/staging/dry-run", json={"source_table": "tabela_fantasma"}).status_code == 400)
check("origem invalida (injecao) -> 400",
      c.post("/staging/dry-run", json={"source_table": "raw_vendas; DROP TABLE stg_vendas"}).status_code == 400)
resp = c.post("/staging/dry-run", json={
    "source_table": "raw_vendas",
    "transforms": [{"type": "add_column", "config": {"name": "x", "expression": "coluna_nada * 2"}}],
})
check("expressao invalida -> 400", resp.status_code == 400, f"status={resp.status_code}")

# ---------- E. NAO PERSISTE ----------
print("\n[E] NAO PERSISTE")
for _ in range(3):
    c.post("/staging/dry-run", json={"source_table": "raw_vendas", "transforms": [{"type": "limit", "config": {"rows": 2}}]})
depois = len(c.get("/staging").json())
check("nenhum staging criado pelo dry-run", depois == stg_antes, f"{stg_antes} -> {depois}")
tabelas = [t["name"] for t in c.get("/catalog/tables").json()["tables"]]
check("nenhuma tabela _dryrun criada", not any("_dryrun" in t for t in tabelas))

falhas = [(n, dd) for n, p, dd in resultados if not p]
print("\n" + "=" * 78)
print(f"RESULTADO: {len(resultados) - len(falhas)}/{len(resultados)} testes aprovados")
if falhas:
    print("\nFALHAS:")
    for n, dd in falhas:
        print(f"  - {n}: {dd}")
import sys
sys.exit(0 if not falhas else 1)
