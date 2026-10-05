import httpx

BASE = "http://localhost:8000/api"
c = httpx.Client(base_url=BASE, timeout=120)

resultados = []


def check(nome, cond, detalhe=""):
    resultados.append((nome, bool(cond), str(detalhe)[:130]))
    print(f"  [{'PASS' if cond else 'FAIL'}] {nome}" + (f" | {str(detalhe)[:110]}" if not cond else ""))


ids_dash = []

LAYOUT_COMPLETO = [
    {"id": "k1", "type": "kpi", "width": 4, "x": 0, "y": 0, "w": 4, "h": 2,
     "config": {"label": "Total", "value": "R$ 25,193.50", "change": 5.2}},
    {"id": "k2", "type": "kpi", "width": 3, "x": 4, "y": 0, "w": 3, "h": 2,
     "config": {"label": "Itens", "value": "43"}},
    {"id": "g1", "type": "chart_line", "width": 5, "x": 0, "y": 2, "w": 5, "h": 4,
     "config": {"title": "Linha", "data": [{"name": "jan", "value": 10}, {"name": "fev", "value": 20}]}},
    {"id": "g2", "type": "chart_bar", "width": 6, "x": 0, "y": 6, "w": 6, "h": 4,
     "config": {"title": "Barras", "data": [{"name": "Ana", "value": 11200}, {"name": "João", "value": 6078}]}},
    {"id": "g3", "type": "chart_pie", "width": 6, "x": 6, "y": 6, "w": 6, "h": 4,
     "config": {"title": "Pizza", "data": [{"name": "Notebook", "value": 17500}, {"name": "Mouse", "value": 700}]}},
    {"id": "g4", "type": "chart_area", "width": 12, "x": 0, "y": 10, "w": 12, "h": 3,
     "config": {"title": "Area", "data": [{"name": "q1", "value": 8000}, {"name": "q2", "value": 12000}]}},
    {"id": "t1", "type": "table", "width": 12, "x": 0, "y": 13, "w": 12, "h": 5,
     "config": {"title": "Detalhes", "columns": ["vendedor", "total"],
                "data": [{"vendedor": "Ana Costa", "total": 11200}, {"vendedor": "João Silva", "total": 6078}]}},
]
TIPOS_ESPERADOS = ["kpi", "kpi", "chart_line", "chart_bar", "chart_pie", "chart_area", "table"]


def criar(nome, titulo="Dashboard Teste", layout=None, **extra):
    payload = {"name": nome, "title": titulo, "layout": layout or []}
    payload.update(extra)
    r = c.post("/dashboards", json=payload)
    if r.status_code >= 400:
        return None, r
    d = r.json()
    if nome.startswith("tstdash_"):
        ids_dash.append(d["id"])
    return d, r


def get_or_create(nome, **kw):
    existente = next((x for x in c.get("/dashboards").json() if x["name"] == nome), None)
    if existente:
        print(f"    [existe] {nome}")
        return existente
    d, r = criar(nome, **kw)
    if d is None:
        print(f"    [ERRO] {nome}: {r.text[:150]}")
    return d


# limpeza inicial de residuos de teste
for d in c.get("/dashboards").json():
    if d["name"].startswith("tstdash_"):
        c.delete(f"/dashboards/{d['id']}")

_OFICIAL = "dashboard_vendas"


def presenca(etapa):
    nomes = [x["name"] for x in c.get("/dashboards").json()]
    marcador = "OK" if _OFICIAL in nomes else "*** SUMIU ***"
    print(f"  [rastreio] {etapa}: oficial={marcador} | total={len(nomes)}")
    return _OFICIAL in nomes


presenca("apos limpeza inicial")

print("=" * 78)
print("TESTE EXAUSTIVO - SESSAO DASHBOARDS")
print("=" * 78)

# ---------- A. CRUD ----------
print("\n[A] CRUD")
d, r = criar("tstdash_base", "Meu Dashboard", layout=LAYOUT_COMPLETO,
             description="desc teste", refresh_interval=60,
             filters=[{"field": "vendedor", "type": "text"}])
check("POST cria dashboard", d is not None, r.text[:100])
r2 = c.post("/dashboards", json={"name": "tstdash_base", "title": "dup"})
check("POST nome duplicado -> 400", r2.status_code == 400)

g = c.get(f"/dashboards/{d['id']}")
gj = g.json()
check("GET retorna config completa",
      g.status_code == 200 and gj["title"] == "Meu Dashboard"
      and gj["refresh_interval"] == 60 and gj["description"] == "desc teste"
      and len(gj["layout"]) == 7 and gj["filters"][0]["field"] == "vendedor")

check("GET inexistente -> 404", c.get("/dashboards/id-falso").status_code == 404)
check("data de inexistente -> 404", c.get("/dashboards/id-falso/data").status_code == 404)

up = c.put(f"/dashboards/{d['id']}", json={"title": "Titulo Atualizado", "refresh_interval": 30})
check("PUT atualiza title/refresh", up.status_code == 200 and up.json()["title"] == "Titulo Atualizado"
      and up.json()["refresh_interval"] == 30)
d_outro, _ = criar("tstdash_outro", "Outro")
up2 = c.put(f"/dashboards/{d['id']}", json={"name": "tstdash_outro"})
check("PUT conflito de nome -> 400", up2.status_code == 400)
del_ok = c.delete(f"/dashboards/{d_outro['id']}")
check("DELETE + 404 posterior",
      del_ok.status_code == 200 and c.get(f"/dashboards/{d_outro['id']}").status_code == 404)

# ---------- B. tipos de componente via /data ----------
presenca("inicio [B]")
print("\n[B] COMPONENTES DO LAYOUT VIA /data")
data = c.get(f"/dashboards/{d['id']}/data").json()
comps = data.get("components", [])
check("data retorna components", isinstance(comps, list) and len(comps) == 7, f"{len(comps)}")
tipos_retornados = [x["type"] for x in comps]
check("todos os 6 tipos suportados presentes", set(TIPOS_ESPERADOS) <= set(tipos_retornados), str(tipos_retornados))
check("largura (width) preservada", all(x.get("width") for x in comps))

kpi = next(x for x in comps if x["type"] == "kpi")
check("kpi com label/value/change", kpi["config"]["label"] == "Total" and kpi["config"]["change"] == 5.2)
bar = next(x for x in comps if x["type"] == "chart_bar")
check("chart_bar com dados", len(bar["config"]["data"]) == 2 and "title" in bar["config"])
tab = next(x for x in comps if x["type"] == "table")
check("table com columns+data", tab["config"]["columns"] == ["vendedor", "total"] and len(tab["config"]["data"]) == 2)

geometria_ok = all(
    isinstance(x.get("id"), str) and all(isinstance(x.get(k), (int, float)) for k in ("x", "y", "w", "h"))
    for x in comps
)
check("geometria id/x/y/w/h preservada no round-trip", geometria_ok, str([(x.get('id'), x.get('x'), x.get('w')) for x in comps[:3]]))
g2c = next(x for x in comps if x.get("id") == "g2")
check("posicao do componente g2 mantida", g2c.get("x") == 0 and g2c.get("y") == 6 and g2c.get("w") == 6, str(g2c))

# componente nao suportado nao quebra o endpoint
d_ns, _ = criar("tstdash_naosuportado", layout=[{"type": "widget_exotico", "config": {}}])
data_ns = c.get(f"/dashboards/{d_ns['id']}/data").json()
check("tipo nao suportado retorna sem erro (frontend exibe aviso)",
      data_ns["components"][0]["type"] == "widget_exotico")

# ---------- C. variantes ----------
presenca("inicio [C]")
print("\n[C] VARIANTES")
d_v, _ = criar("tstdash_layoutvazio", "Layout Vazio")
data_v = c.get(f"/dashboards/{d_v['id']}/data").json()
check("layout vazio aceito", data_v.get("components") == [])

d_f, _ = criar("tstdash_semopc", "Sem Opcionais")
g2 = c.get(f"/dashboards/{d_f['id']}").json()
check("campos opcionais default", g2.get("description") in (None, "") and not g2.get("filters"))

# update de layout reflete em /data
novo_layout = [{"type": "kpi", "width": 12, "config": {"label": "Unico", "value": "42"}}]
up3 = c.put(f"/dashboards/{d_v['id']}", json={"layout": novo_layout})
data_up = c.get(f"/dashboards/{d_v['id']}/data").json()
check("update layout reflete em /data",
      up3.status_code == 200 and len(data_up["components"]) == 1 and data_up["components"][0]["config"]["value"] == "42")

# ---------- D. validacoes ----------
presenca("inicio [D]")
print("\n[D] VALIDACOES")
r_name_espaco = c.post("/dashboards", json={"name": "nome com espaco", "title": "x"})
check("nome com caractere invalido -> 422", r_name_espaco.status_code == 422, f"{r_name_espaco.status_code}")
r_sem_titulo = c.post("/dashboards", json={"name": "tstdash_semtitulo"})
check("title ausente -> 422", r_sem_titulo.status_code == 422, f"{r_sem_titulo.status_code}")

# ---------- E. dashboard oficial ----------
presenca("inicio [E]")
print("\n[E] DASHBOARD OFICIAL (dados reais)")
dv = next((x for x in c.get("/dashboards").json() if x["name"] == "dashboard_vendas"), None)
if dv:
    dd = c.get(f"/dashboards/{dv['id']}/data").json()
    comps_o = dd["components"]
    check("dashboard_vendas presente com 6 componentes", len(comps_o) == 6, str(len(comps_o)))
    kpis = [x for x in comps_o if x["type"] == "kpi"]
    graficos = [x for x in comps_o if x["type"].startswith("chart")]
    tabelas = [x for x in comps_o if x["type"] == "table"]
    check("estrutura: 3 KPIs + 2 graficos + 1 tabela", len(kpis) == 3 and len(graficos) == 2 and len(tabelas) == 1,
          f"k={len(kpis)} g={len(graficos)} t={len(tabelas)}")
    tot_kpi = next((x for x in kpis if x["config"].get("label") == "Total de Vendas"), None)
    check("KPI Total de Vendas com valor real", bool(tot_kpi and "25,193" in str(tot_kpi["config"].get("value"))),
          str(tot_kpi))
    bar_o = next((x for x in graficos if x["type"] == "chart_bar"), None)
    n_barras = len(bar_o["config"]["data"]) if bar_o else 0
    check("grafico de barras com dados por vendedor (4)", n_barras == 4, str(n_barras))
else:
    check("dashboard_vendas existe", False, "nao encontrado")

# ---------- F. limpeza ----------
presenca("inicio [F] - ANTES DA LIMPEZA FINAL")
print("\n[F] LIMPEZA")
for did in ids_dash:
    c.delete(f"/dashboards/{did}")
restaram = [x["name"] for x in c.get("/dashboards").json() if x["name"].startswith("tstdash_")]
oficiais = [x["name"] for x in c.get("/dashboards").json()]
check("limpeza de dashboards de teste", not restaram, str(restaram))
check("dashboards oficiais preservados", "dashboard_vendas" in oficiais, str(oficiais))

falhas = [(n, dd) for n, p, dd in resultados if not p]
print("\n" + "=" * 78)
print(f"RESULTADO: {len(resultados) - len(falhas)}/{len(resultados)} testes aprovados")
if falhas:
    print("\nFALHAS:")
    for n, dd in falhas:
        print(f"  - {n}: {dd}")
import sys
sys.exit(0 if not falhas else 1)

