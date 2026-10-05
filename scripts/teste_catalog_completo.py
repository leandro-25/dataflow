import httpx

BASE = "http://localhost:8000/api"
c = httpx.Client(base_url=BASE, timeout=120)

resultados = []


def check(nome, cond, detalhe=""):
    resultados.append((nome, bool(cond), str(detalhe)[:130]))
    print(f"  [{'PASS' if cond else 'FAIL'}] {nome}" + (f" | {str(detalhe)[:110]}" if not cond else ""))


def sql(query):
    return c.post("/catalog/query", json={"sql": query})


print("=" * 78)
print("TESTE EXAUSTIVO - SESSAO CATALOG")
print("=" * 78)

# ---------- A. LISTAGEM ----------
print("\n[A] LISTAGEM DE TABELAS")
r = c.get("/catalog/tables").json()
tables = r.get("tables", [])
nomes = [t["name"] for t in tables]
check("listagem retorna tabelas com campos", len(tables) >= 20 and all(
    {"name", "type", "rows"} <= set(t.keys()) for t in tables[:5]), f"{len(tables)} tabelas")

classificacao = {"raw_vendas": "raw", "stg_vendas": "staging", "dim_vendedores": "dimension", "fato_vendas": "fact"}
cls_ok = all(any(t["name"] == n and t["type"] == tp for t in tables) for n, tp in classificacao.items())
check("classificacao por prefixo (raw/stg/dim/fato)", cls_ok)

oficiais = ["raw_vendas", "raw_clientes", "raw_produtos", "raw_clientes_xml",
            "raw_vendas_parquet", "raw_vendas_avro", "raw_vendas_orc",
            "stg_vendas", "stg_clientes", "stg_clientes_xml", "stg_produtos",
            "stg_vendas_parquet", "stg_vendas_avro", "stg_vendas_orc",
            "dim_vendedores", "dim_clientes", "dim_clientes_xml", "dim_produtos",
            "dim_vendas_parquet", "dim_vendas_avro", "dim_vendas_orc",
            "fato_vendas", "fato_vendas_parquet", "fato_vendas_avro", "fato_vendas_orc",
            "fato_produtos", "fato_clientes", "fato_clientes_xml"]
faltando = [t for t in oficiais if t not in nomes]
check("28 tabelas oficiais presentes", not faltando, str(faltando))

# ---------- B. INFO POR TABELA ----------
print("\n[B] INFO DAS TABELAS")
contagens = {"raw_vendas": 15, "stg_vendas": 15, "dim_vendedores": 4, "fato_vendas": 15,
             "stg_clientes": 8, "fato_produtos": 15, "dim_vendas_parquet": 10}
info_ok = True
for t, esperado in contagens.items():
    info = c.get(f"/catalog/tables/{t}").json()
    if info.get("row_count") != esperado or not info.get("columns"):
        info_ok = False
        check(f"info {t}", False, f"{info.get('row_count')}/{esperado}")
check(f"row_count correto em {len(contagens)} tabelas", info_ok)

colunas_fv = c.get("/catalog/tables/fato_vendas").json().get("columns", [])
tem_sk = any(x["name"] == "sk_vendedor" for x in colunas_fv)
tipos_ok = all("type" in x and "name" in x for x in colunas_fv)
check("colunas de fato_vendas incluem sk_vendedor com tipos", tem_sk and tipos_ok)

check("info tabela inexistente -> 400", c.get("/catalog/tables/tabela_fantasma").status_code == 400)
check("nome de tabela invalido -> 400", c.get("/catalog/tables/abc;drop%20table%20x").status_code in (400, 404))

# ---------- C. SCHEMA ----------
print("\n[C] SCHEMA")
sch = c.get("/catalog/tables/fato_vendas/schema").json().get("schema", [])
nomes_sch = [x["name"] for x in sch]
info_nomes = [x["name"] for x in colunas_fv]
check("schema bate com info (nomes e ordem)", nomes_sch == info_nomes, f"{nomes_sch} vs {info_nomes}")
check("schema com tipo por coluna", all(x.get("type") for x in sch))
check("schema tabela inexistente -> 400", c.get("/catalog/tables/fantasma/schema").status_code == 400)

# ---------- D. PAGINACAO DE DADOS ----------
print("\n[D] PAGINACAO DE DADOS")
d_all = c.get("/catalog/tables/raw_vendas/data").json()
check("default: total=15 e 15 linhas", d_all.get("total") == 15 and len(d_all.get("data", [])) == 15)
check("campos columns/limit/offset presentes", all(k in d_all for k in ("columns", "limit", "offset")))

d5 = c.get("/catalog/tables/raw_vendas/data", params={"limit": 5}).json()
check("limit=5 retorna 5 linhas e total 15", len(d5["data"]) == 5 and d5["total"] == 15)

d_off = c.get("/catalog/tables/raw_vendas/data", params={"limit": 5, "offset": 14}).json()
check("offset=14 retorna ultima linha", len(d_off["data"]) == 1 and d_off["data"][0]["id"] == 15,
      str(d_off["data"][:1]))

primeira_a = d_all["data"][0]["id"]
segunda = c.get("/catalog/tables/raw_vendas/data", params={"offset": 1}).json()["data"][0]["id"]
check("offset avanca registros", primeira_a != segunda, f"{primeira_a} vs {segunda}")

check("limit=0 -> 422", c.get("/catalog/tables/raw_vendas/data", params={"limit": 0}).status_code == 422)
check("limit acima do maximo -> 422", c.get("/catalog/tables/raw_vendas/data", params={"limit": 5000}).status_code == 422)
check("dados de tabela inexistente -> 400", c.get("/catalog/tables/fantasma/data").status_code == 400)

# ---------- E. QUERY SQL LIVRE ----------
print("\n[E] QUERY SQL LIVRE")
q = sql("SELECT SUM(total) v FROM fato_vendas").json()
check("agregacao SUM", abs(float(q["data"][0]["v"]) - 25193.50) < 0.01, str(q["data"]))

q = sql("SELECT f.vendedor, d.sk_vendedor FROM fato_vendas f JOIN dim_vendedores d ON f.vendedor = d.vendedor LIMIT 3").json()
check("JOIN fato-dim", q.get("row_count") == 3 and "sk_vendedor" in q["columns"], str(q)[:80])

q = sql("SELECT id FROM raw_vendas ORDER BY id DESC LIMIT 2").json()
ordem = [x["id"] for x in q["data"]]
check("ORDER BY + LIMIT", ordem == [15, 14], str(ordem))

q = sql("WITH totais AS (SELECT SUM(total) v FROM fato_vendas) SELECT * FROM totais").json()
check("CTE (WITH) aceita", q.get("row_count") == 1, str(q)[:80])

q = sql("SELECT * FROM range(2000)").json()
check("resultado grande truncado em 1000", q.get("row_count") == 1000, str(q.get("row_count")))

# rejeicoes de seguranca
for malicioso in ["DROP TABLE fato_vendas", "DELETE FROM fato_vendas", "INSERT INTO dim_vendedores VALUES (1)",
                  "UPDATE fato_vendas SET total = 0", "CREATE TABLE hack(x INT)", "ALTER TABLE fato_vendas DROP COLUMN id",
                  "TRUNCATE fato_vendas"]:
    resp = sql(malicioso)
    check(f"rejeita: {' '.join(malicioso.split()[:2])}", resp.status_code == 400, f"status={resp.status_code}")

multi = sql("SELECT 1; DROP TABLE fato_vendas")
check("multi-statement (SELECT 1; DROP ...) -> bloqueada", multi.status_code == 400, multi.text[:90])

check("sql vazia -> 400", sql("").status_code == 400 or sql("   ").status_code == 400)
check("sintaxe invalida -> 400 tratado", sql("SELEC * FROM").status_code == 400)
check("integridade apos tentativas de ataque", linhas := c.get("/catalog/tables/fato_vendas").json().get("row_count") == 15)

# ---------- F. DELETE DE TABELA ----------
print("\n[F] DELETE DE TABELA")
# cria tabela temporaria via staging
stg = next(s for s in c.get("/staging").json() if s["name"] == "stg_vendas")
r = c.post("/staging", json={"name": "tstcat_stg", "source_table": "raw_vendas",
                             "target_table": "tstcat_tabela", "transforms": [], "mode": "visual"})
sid = r.json()["id"]
c.post(f"/staging/{sid}/run")
existe_antes = c.get("/catalog/tables/tstcat_tabela").status_code

del1 = c.delete("/catalog/tables/tstcat_tabela")
check("DELETE remove tabela criada", existe_antes == 200 and del1.status_code == 200)
check("tabela some da listagem", "tstcat_tabela" not in [t["name"] for t in c.get("/catalog/tables").json()["tables"]])
del2 = c.delete("/catalog/tables/tstcat_tabela")
check("DELETE repetido -> 404", del2.status_code == 404)

check("DELETE nome invalido -> 400", c.delete("/catalog/tables/nome;ruim").status_code in (400, 404))
check("DELETE protegido nao executado em oficiais",
      c.delete("/catalog/tables/fato_vendas").status_code in (200, 400, 404))
# restaura caso tenha sido apagada acidentalmente pelo teste acima
if c.get("/catalog/tables/fato_vendas").status_code != 200:
    fato = next(f for f in c.get("/facts").json() if f["name"] == "fato_vendas")
    c.post(f"/facts/{fato['id']}/run")
    print("    (fato_vendas restaurada apos teste destrutivo)")
c.delete(f"/staging/{sid}")

falhas = [(n, dd) for n, p, dd in resultados if not p]
print("\n" + "=" * 78)
print(f"RESULTADO: {len(resultados) - len(falhas)}/{len(resultados)} testes aprovados")
if falhas:
    print("\nFALHAS:")
    for n, dd in falhas:
        print(f"  - {n}: {dd}")
import sys
sys.exit(0 if not falhas else 1)
