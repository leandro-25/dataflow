"""Teste de aceitação de todas as fontes de dados do Dataflow."""
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from connectors.factory import get_connector

EXEMPLOS = ROOT / "exemplo-dados"

SQL_TEMP = Path(__file__).resolve().parent / "_teste_query_temp.sql"
SQL_TEMP.write_text("SELECT 1 AS id, 'Produto Teste' AS produto, 10.5 AS valor;", encoding="utf-8")

FONTES = {
    "csv": {
        "config": {"file_path": str(EXEMPLOS / "vendas.csv"), "delimiter": ",", "encoding": "utf-8"},
        "esperado": "sucesso",
    },
    "excel": {
        "config": {"file_path": str(EXEMPLOS / "produtos.xlsx")},
        "esperado": "sucesso",
    },
    "json": {
        "config": {"file_path": str(EXEMPLOS / "clientes.json"), "orientation": "records"},
        "esperado": "sucesso",
    },
    "xml": {
        "config": {"file_path": str(EXEMPLOS / "clientes.xml"), "row_element": "cliente"},
        "esperado": "sucesso",
    },
    "parquet": {
        "config": {"file_path": str(EXEMPLOS / "vendas.parquet")},
        "esperado": "sucesso",
    },
    "avro": {
        "config": {"file_path": str(EXEMPLOS / "vendas.avro")},
        "esperado": "sucesso",
    },
    "orc": {
        "config": {"file_path": str(EXEMPLOS / "vendas.orc")},
        "esperado": "sucesso",
    },
    "sql_file": {
        "config": {"file_path": str(SQL_TEMP), "target_type": "duckdb"},
        "esperado": "sucesso",
    },
    "delta_lake": {
        "config": {"table_path": str(EXEMPLOS / "delta_vendas.parquet")},
        "esperado": "falha_graciosa",
    },
    "postgres": {
        "config": {"host": "localhost", "port": 5432, "database": "dataflow_test", "user": "postgres", "password": "senha123"},
        "esperado": "falha_graciosa",
    },
    "mysql": {
        "config": {"host": "localhost", "port": 3306, "database": "dataflow_test", "user": "root", "password": "senha123"},
        "esperado": "falha_graciosa",
    },
    "google_sheets": {
        "config": {"spreadsheet_id": "ID_INEXISTENTE_TESTE"},
        "esperado": "falha_graciosa",
    },
}


def testar_tipo(tipo: str, cfg: dict, esperado: str) -> dict:
    resultado = {"tipo": tipo, "ok": False, "mensagem": "", "linhas": None}

    try:
        connector = get_connector(tipo, cfg["config"])
    except Exception as e:
        resultado["mensagem"] = f"Factory recusou o tipo: {e}"
        return resultado

    try:
        sucesso, msg = connector.test_connection()
        resultado["mensagem"] = msg

        if esperado == "sucesso":
            if not sucesso:
                return resultado
            tabelas = connector.list_tables()
            schema = connector.get_schema(tabelas[0] if tabelas else None)
            df = connector.extract(None, is_query=False)
            if len(df) == 0:
                resultado["mensagem"] = "extract retornou 0 linhas"
                return resultado
            resultado["linhas"] = len(df)
            resultado["colunas"] = len(schema)
            resultado["tabelas"] = len(tabelas)
            resultado["ok"] = True
        else:
            resultado["ok"] = sucesso is False
            resultado["linhas"] = None
    except Exception as e:
        resultado["mensagem"] = f"EXCEÇÃO NÃO TRATADA: {e}"
        traceback.print_exc()

    return resultado


def main():
    print("=" * 78)
    print("TESTE DE ACEITACAO DE FONTES DE DADOS - DATAFLOW")
    print("=" * 78)

    tipos = list(FONTES.keys())
    resultados = [testar_tipo(t, FONTES[t], FONTES[t]["esperado"]) for t in tipos]

    tipo_invalido_aceito = False
    try:
        get_connector("tipo_inexistente", {})
        tipo_invalido_aceito = True
    except ValueError:
        pass

    SQL_TEMP.unlink(missing_ok=True)

    print(f"\n{'TIPO':<15}{'RESULTADO':<12}{'DETALHE'}")
    print("-" * 78)
    aprovados = 0
    for r in resultados:
        status = "PASSOU" if r["ok"] else "FALHOU"
        detalhe = r["mensagem"]
        if r.get("linhas") is not None:
            detalhe = f"{r['linhas']} linhas, {r['colunas']} colunas | {detalhe[:60]}"
        else:
            detalhe = detalhe[:70]
        print(f"{r['tipo']:<15}{status:<12}{detalhe}")
        if r["ok"]:
            aprovados += 1

    print("-" * 78)
    if tipo_invalido_aceito:
        print("AVISO: factory aceitou tipo invalido sem erro!")
    else:
        print("Tipo invalido corretamente rejeitado com ValueError")

    total = len(resultados)
    print(f"\nRESULTADO FINAL: {aprovados}/{total} fontes aprovadas")
    return 0 if aprovados == total and not tipo_invalido_aceito else 1


if __name__ == "__main__":
    sys.exit(main())
