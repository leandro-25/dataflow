import httpx

BASE = "http://localhost:8000/api"
EX = r"D:\FATEC\projetos\date\dataflow\exemplo-dados"

c = httpx.Client(base_url=BASE, timeout=120)
resultados = []


def check(nome, cond, detalhe=""):
    resultados.append((nome, bool(cond), str(detalhe)[:130]))
    print(f"  [{'PASS' if cond else 'FAIL'}] {nome}" + (f" | {str(detalhe)[:110]}" if not cond else ""))


def limpar(nome):
    for s in c.get("/sources").json():
        if s["name"] == nome:
            c.delete(f"/sources/{s['id']}")


for n in ["tstux_csv", "tstux_db", "tstux_sheets"]:
    limpar(n)

print("=" * 78)
print("TESTE - SOURCES: VALIDACAO DRY-RUN, MASCARAMENTO E PROTECOES")
print("=" * 78)

# ---------- A. VALIDACAO ANTES DE SALVAR ----------
print("\n[A] DRY-RUN /sources/validate")
v = c.post("/sources/validate", json={"type": "csv", "config": {"file_path": EX + r"\vendas.csv"}}).json()
check("csv valido -> sucesso", v.get("success") is True and "colunas" in v["message"].lower(), v["message"][:80])

v = c.post("/sources/validate", json={"type": "csv", "config": {"file_path": r"C:\nao\existe.csv"}}).json()
check("arquivo inexistente -> falha amigavel", v.get("success") is False and "encontrado" in v["message"].lower(), v["message"][:80])

v = c.post("/sources/validate", json={"type": "postgres", "config": {"host": "host-invalido-xyz", "port": 5432, "database": "x", "user": "x", "password": "x"}}).json()
check("postgres host errado -> falha sem crash", v.get("success") is False and len(v["message"]) > 0, v["message"][:80])

v = c.post("/sources/validate", json={"type": "tipo_inexistente", "config": {}}).json()
check("tipo inexistente -> falha com mensagem", v.get("success") is False and "suportado" in v["message"].lower(), v["message"][:80])

v = c.post("/sources/validate", json={"type": "xml", "config": {"file_path": EX + r"\clientes.xml", "row_element": "cliente"}}).json()
check("xml com row_element valida", v.get("success") is True)

# validate NAO persiste
antes = len(c.get("/sources").json())
c.post("/sources/validate", json={"type": "csv", "config": {"file_path": EX + r"\vendas.csv"}})
depois = len(c.get("/sources").json())
check("dry-run nao grava nada", antes == depois, f"{antes} -> {depois}")

# ---------- B. MASCARAMENTO DE CREDENCIAIS ----------
print("\n[B] MASCARAMENTO DE SENHAS")
r = c.post("/sources", json={"name": "tstux_db", "type": "mysql",
                             "config": {"host": "localhost", "port": 3306, "database": "db",
                                        "user": "admin", "password": "SegredoForte123"}})
check("criacao ok", r.status_code == 200)
sid = r.json()["id"]
cfg = r.json()["config"]
check("senha mascarada na resposta do create", cfg.get("password") == "__MASKED__", str(cfg.get("password"))[:40])

lista = [s for s in c.get("/sources").json() if s["name"] == "tstux_db"][0]
check("senha mascarada na listagem", lista["config"].get("password") == "__MASKED__")
check("segredo real NAO vazou na API", "SegredoForte123" not in str(c.get("/sources").text))

# update SEM senha -> preserva a salva
up = c.put(f"/sources/{sid}", json={"name": "tstux_db", "config": {"host": "localhost", "port": 3307,
                                                                   "database": "db", "user": "admin",
                                                                   "password": "__MASKED__"}})
cfg_up = up.json()["config"]
check("update com mascara aceito", up.status_code == 200 and cfg_up.get("password") == "__MASKED__")
check("porta atualizada junto", cfg_up.get("port") == 3307)

up_vazio = c.put(f"/sources/{sid}", json={"config": {"host": "localhost", "port": 3307,
                                                     "database": "db", "user": "admin", "password": ""}})
check("update com senha vazia tambem preserva", up_vazio.status_code == 200)

# google sheets credentials (dict) mascarado
r = c.post("/sources", json={"name": "tstux_sheets", "type": "google_sheets",
                             "config": {"spreadsheet_id": "ABC123", "credentials": {"type": "service_account", "private_key": "x"}}})
cfg_sh = r.json()["config"]
check("credentials (dict) mascaradas", cfg_sh.get("credentials") == "__MASKED__", str(cfg_sh.get("credentials"))[:50])
c.delete(f"/sources/{r.json()['id']}")

# ---------- C. EXCLUSAO COM INGESTOES VINCULADAS ----------
print("\n[C] PROTECAO DE EXCLUSAO")
ing = c.get("/ingestions").json()
fonte_com_ing = next((s for s in c.get("/sources").json()
                      if any(i["source_id"] == s["id"] for i in ing)), None)
if fonte_com_ing:
    resp = c.delete(f"/sources/{fonte_com_ing['id']}")
    check(f"exclusao bloqueada com ingestoes ({fonte_com_ing['name']})", resp.status_code == 409,
          f"status={resp.status_code} {resp.text[:60]}")
else:
    check("nenhuma fonte com ingestao para testar bloqueio", True)

# exclusao de fonte sem ingestao funciona
resp = c.delete(f"/sources/{sid}")
check("exclusao livre quando sem ingestoes", resp.status_code == 200)

falhas = [(n, dd) for n, p, dd in resultados if not p]
print("\n" + "=" * 78)
print(f"RESULTADO: {len(resultados) - len(falhas)}/{len(resultados)} testes aprovados")
if falhas:
    print("\nFALHAS:")
    for n, dd in falhas:
        print(f"  - {n}: {dd}")
import sys
sys.exit(0 if not falhas else 1)
