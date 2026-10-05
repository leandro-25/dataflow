import httpx

BASE = "http://localhost:8000/api"
EX = r"D:\FATEC\projetos\date\dataflow\exemplo-dados"

c = httpx.Client(base_url=BASE, timeout=120)
resultados = []


def check(nome, cond, detalhe=""):
    resultados.append((nome, bool(cond), str(detalhe)[:130]))
    print(f"  [{'PASS' if cond else 'FAIL'}] {nome}" + (f" | {str(detalhe)[:110]}" if not cond else ""))


fontes = {s["name"]: s for s in c.get("/sources").json()}
ing_antes = len(c.get("/ingestions").json())

print("=" * 78)
print("TESTE - INGESTIONS: WIZARD / DRY-RUN")
print("=" * 78)

# ---------- A. DRY-RUN BASICO ----------
print("\n[A] DRY-RUN BASICO POR FONTE")
casos = [
    ("vendas_csv", "vendas.csv", 5),
    ("clientes_json", "clientes.json", 5),
    ("produtos_xlsx", "produtos.xlsx", 5),
    ("clientes_xml", "clientes.xml", 5),
    ("vendas_parquet", "vendas.parquet", 5),
    ("vendas_avro", "vendas.avro", 5),
    ("vendas_orc", "vendas.orc", 5),
]
for fonte_nome, tabela, limite in casos:
    r = c.post("/ingestions/dry-run", json={
        "source_id": fontes[fonte_nome]["id"],
        "config": {"mode": "table", "table": tabela},
        "limit": limite,
    })
    if r.status_code >= 400:
        check(f"dry-run {fonte_nome}", False, r.text[:100])
        continue
    d = r.json()
    ok = d.get("total_rows", 0) > 0 and len(d.get("columns", [])) > 0
    check(f"dry-run {fonte_nome} ({tabela})", ok, f"{d.get('total_rows')} linhas | {r.text[:80]}")

# limit menor que dados disponiveis
r = c.post("/ingestions/dry-run", json={
    "source_id": fontes["vendas_csv"]["id"],
    "config": {"mode": "table", "table": "vendas.csv"},
    "limit": 3,
}).json()
check("respeita limit=3", r.get("total_rows") == 3 and len(r["data"]) == 3)

# ---------- B. FILTROS E RENOMEACAO ----------
print("\n[B] DRY-RUN COM FILTROS / MAPEAMENTO")
r = c.post("/ingestions/dry-run", json={
    "source_id": fontes["vendas_csv"]["id"],
    "config": {"mode": "table", "table": "vendas.csv"},
    "filters": [{"column": "quantidade", "operator": "gt", "value": 5}],
    "limit": 50,
}).json()
check("filtro quantidade>5 aplicado (2 linhas)", r.get("total_rows") == 2, f"{r.get('total_rows')}/2")

r = c.post("/ingestions/dry-run", json={
    "source_id": fontes["vendas_csv"]["id"],
    "config": {"mode": "table", "table": "vendas.csv"},
    "column_mapping": {"produto": {"target_name": "nome_produto"}},
    "limit": 5,
}).json()
check("renomeacao aplicada na amostra", "nome_produto" in r.get("columns", []) and "produto" not in r.get("columns", []),
      str(r.get("columns")))

# ---------- C. ERROS TRATADOS ----------
print("\n[C] ERROS TRATADOS")
r = c.post("/ingestions/dry-run", json={"source_id": "id-falso", "config": {"mode": "table", "table": "x"}})
check("source inexistente -> 404", r.status_code == 404)

r = c.post("/ingestions/dry-run", json={"source_id": fontes["vendas_csv"]["id"], "config": {"mode": "table"}})
check("sem tabela -> 400", r.status_code == 400, r.text[:80])

r = c.post("/ingestions/dry-run", json={"source_id": fontes["vendas_csv"]["id"],
                                        "config": {"mode": "table", "table": "nao_existe.csv"}})
check("arquivo inexistente -> 400 amigavel", r.status_code == 400 and "encontrado" in r.text.lower(), r.text[:90])

# ---------- D. NAO PERSISTE ----------
print("\n[D] DRY-RUN NAO PERSISTE")
for _ in range(3):
    c.post("/ingestions/dry-run", json={
        "source_id": fontes["vendas_csv"]["id"],
        "config": {"mode": "table", "table": "vendas.csv"}, "limit": 2,
    })
depois = len(c.get("/ingestions").json())
check("nenhuma ingestao criada pelo dry-run", depois == ing_antes, f"{ing_antes} -> {depois}")

# tabelas de warehouse nao criadas
tabelas_wh = [t["name"] for t in c.get("/catalog/tables").json()["tables"]]
check("nenhuma tabela raw criada indevidamente", not any(t.startswith("raw_exemplo") for t in tabelas_wh))

falhas = [(n, dd) for n, p, dd in resultados if not p]
print("\n" + "=" * 78)
print(f"RESULTADO: {len(resultados) - len(falhas)}/{len(resultados)} testes aprovados")
if falhas:
    print("\nFALHAS:")
    for n, dd in falhas:
        print(f"  - {n}: {dd}")
import sys
sys.exit(0 if not falhas else 1)
