import httpx

BASE = "http://localhost:8000/api"
c = httpx.Client(base_url=BASE, timeout=300)

resultados = []


def check(nome, cond, detalhe=""):
    resultados.append((nome, bool(cond), str(detalhe)[:130]))
    print(f"  [{'PASS' if cond else 'FAIL'}] {nome}" + (f" | {str(detalhe)[:110]}" if not cond else ""))


def recursos(tipo):
    return c.get(f"/{tipo}").json()


def linhas(t):
    return c.get(f"/catalog/tables/{t}").json().get("row_count", -1)


print("=" * 78)
print("TESTE EXAUSTIVO - SESSAO PIPELINE (EXECUCAO)")
print("=" * 78)

# ---------- A. DAG ----------
print("\n[A] ESTRUTURA DO DAG")
dag = c.get("/execution/dag").json()
nodes, edges = dag.get("nodes", []), dag.get("edges", [])
por_tipo = {}
for n in nodes:
    por_tipo[n["type"]] = por_tipo.get(n["type"], 0) + 1
print(f"    nos={len(nodes)} | {por_tipo}")
check("DAG responde com nos e arestas", len(nodes) > 0 and len(edges) > 0)
check("7 nos de cada tipo (source/ingestion/staging/dimension/fact)",
      all(por_tipo.get(t) == 7 for t in ["source", "ingestion", "staging", "dimension", "fact"]), str(por_tipo))

arestas_por_par = {}
for e in edges:
    par = e["source"].split(":")[0] + "->" + e["target"].split(":")[0]
    arestas_por_par[par] = arestas_por_par.get(par, 0) + 1
print(f"    arestas={len(edges)} | {arestas_por_par}")
check("7 ligacoes source->ingestion", arestas_por_par.get("source->ingestion") == 7, str(arestas_por_par))
check("7 ligacoes ingestion->staging", arestas_por_par.get("ingestion->staging") == 7, str(arestas_por_par))
check("7 ligacoes staging->dimension", arestas_por_par.get("staging->dimension") == 7, str(arestas_por_par))
check("7 ligacoes staging->fact", arestas_por_par.get("staging->fact") == 7, str(arestas_por_par))

# todo no executavel tem entrada (menos sources)
ids_com_entrada = {e["target"] for e in edges}
sem_entrada = [n["id"] for n in nodes if n["type"] != "source" and n["id"] not in ids_com_entrada]
check("todo no executavel possui dependencia", not sem_entrada, str(sem_entrada[:5]))

# mapa nome->id para uso posterior
mapa = {(n["type"], n["name"]): n["resource_id"] for n in nodes}

# ---------- B. STATUS ----------
print("\n[B] STATUS")
st = c.get("/execution/status").json()
check("status responde com campos",
      isinstance(st.get("running_executions"), int) and "last_execution" in st, str(st)[:120])

# ---------- C. EXECUCAO INDIVIDUAL ----------
print("\n[C] EXECUCAO INDIVIDUAL POR RECURSO")
id_stg_vendas = mapa[("staging", "stg_vendas")]
r = c.post(f"/execution/run/staging/{id_stg_vendas}").json()
tipos_r = [x["node"].split(":")[0] for x in r.get("results", [])]
check("run a partir do staging executa no + dependentes",
      r.get("success") is True and "staging" in tipos_r and "dimension" in tipos_r and "fact" in tipos_r,
      str(tipos_r))
check("nenhum erro na cadeia", all(x["status"] == "success" for x in r.get("results", [])), str(r.get("results"))[:150])

id_ing_vendas = mapa[("ingestion", "ing_raw_vendas")]
r = c.post(f"/execution/run/ingestion/{id_ing_vendas}").json()
check("run individual de ingestion ok",
      r.get("success") is True and all(x["status"] == "success" for x in r["results"]),
      str(r.get("results"))[:120])

id_dim = mapa[("dimension", "dim_vendedores")]
r = c.post(f"/execution/run/dimension/{id_dim}").json()
linhas_dim = [x for x in r["results"] if x["node"].startswith("dimension")]
check("run individual de dimension ok", r.get("success") is True and len(linhas_dim) >= 1)

id_fact = mapa[("fact", "fato_vendas")]
r = c.post(f"/execution/run/fact/{id_fact}").json()
check("run individual de fact ok", r.get("success") is True)

# ---------- D. COM DEPENDENCIAS ----------
print("\n[D] RUN A PARTIR DA SOURCE (with_deps=true)")
id_src_csv = mapa[("source", "vendas_csv")]
r = c.post(f"/execution/run/source/{id_src_csv}", params={"with_deps": True}).json()
seq_tipos = [x["node"].split(":")[0] for x in r.get("results", [])]
check("cadeia completa da source executada", r.get("success") is True and len(seq_tipos) >= 3, str(seq_tipos))
ordem_ok = seq_tipos.index("source") < seq_tipos.index("ingestion") < seq_tipos.index("staging")
check("ordem topologica respeitada (source<ingestion<staging)", ordem_ok, str(seq_tipos))
check("toda a cadeia com sucesso", all(x["status"] == "success" for x in r["results"]))

exec_cadeia = r.get("execution_id")
logs_cadeia = c.get(f"/execution/logs/{exec_cadeia}")
check("logs da execucao especifica", logs_cadeia.status_code == 200 and len(logs_cadeia.json()) == len(r["results"]),
      f"{len(logs_cadeia.json())}/{len(r['results'])}")

# ---------- E. PIPELINE COMPLETO ----------
print("\n[E] PIPELINE COMPLETO")
snapshot = {t: linhas(t) for t in ["raw_vendas", "raw_clientes", "stg_vendas", "stg_clientes",
                                   "dim_vendedores", "dim_clientes", "fato_vendas", "fato_clientes"]}
resp = c.post("/execution/run")
r = resp.json()
erros = [x for x in r.get("results", []) if x["status"] != "success"]
check("POST /run sucesso sem erros", resp.status_code == 200 and r.get("success") is True and not erros,
      str(erros[:3]))
check("todos os 35 nos executados", len(r.get("results", [])) == 35, f"{len(r.get('results', []))}/35")

logs_full = c.get(f"/execution/logs/{r['execution_id']}").json()
check("um log por no na execucao completa", len(logs_full) == 35, f"{len(logs_full)}/35")

pos = {t: linhas(t) for t in snapshot}
integro = all(pos[t] == snapshot[t] and pos[t] > 0 for t in snapshot)
check(f"dados integrais apos re-execucao", integro, f"antes={snapshot} depois={pos}")

mv = c.post("/metrics/" + next(m["id"] for m in recursos("metrics") if m["name"] == "total_vendas") + "/query", json={}).json()
check("metrica total_vendas valida apos pipeline", mv.get("formatted_value") == "R$ 25,193.50", str(mv))

# ---------- F. LOGS ----------
print("\n[F] LOGS")
logs = c.get("/execution/logs", params={"limit": 10}).json()
check("GET /logs respeita limit", isinstance(logs, list) and len(logs) <= 10, f"{len(logs)}")
campos = {"id", "execution_id", "resource_type", "status", "started_at"}
check("logs com campos essenciais", all(campos <= set(l.keys()) for l in logs[:3]))
check("ordenacao desc por criacao", all(logs[i]["created_at"] >= logs[i + 1]["created_at"] for i in range(len(logs) - 1)))

check("logs de execucao inexistente -> 404", c.get("/execution/logs/exec-inexistente").status_code == 404)

# ---------- G. ERROS ----------
print("\n[G] TRATAMENTO DE ERROS")
r_bad = c.post("/execution/run/tipofalso/id-falso")
check("tipo de recurso invalido -> 404", r_bad.status_code == 404, f"status={r_bad.status_code}")
r_bad2 = c.post("/execution/run/source/id-falso")
check("recurso inexistente no dag -> 404", r_bad2.status_code == 404, f"status={r_bad2.status_code}")

falhas = [(n, dd) for n, p, dd in resultados if not p]
print("\n" + "=" * 78)
print(f"RESULTADO: {len(resultados) - len(falhas)}/{len(resultados)} testes aprovados")
if falhas:
    print("\nFALHAS:")
    for n, dd in falhas:
        print(f"  - {n}: {dd}")
import sys
sys.exit(0 if not falhas else 1)
