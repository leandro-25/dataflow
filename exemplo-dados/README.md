# Dados de Exemplo para Teste do Dataflow

Este diretório contém arquivos e configurações de exemplo para testar todos os conectores e funcionalidades do projeto Dataflow.

## Arquivos Disponíveis

### Arquivos Locais
1. **vendas.csv** - Dados de vendas de produtos (15 registros)
2. **clientes.json** - Cadastro de clientes empresariais (8 clientes)
3. **produtos.xlsx** - Catálogo de produtos com estoque (15 produtos)
4. **clientes.xml** - Dados de clientes em formato XML

### Bancos de Dados
5. **database_setup.sql** - Script para criar tabelas em PostgreSQL e MySQL
6. **dados_inserts.sql** - Arquivo SQL com dados INSERT de exemplo

### Formatos Big Data
7. **gerar_formatos_binarios.py** - Script para gerar Parquet, Avro, ORC e Delta Lake
8. **vendas.avsc** - Schema Avro para validação de dados
9. **vendas.parquet**, **clientes.parquet**, **produtos.parquet** - Arquivos Parquet
10. **vendas.orc**, **clientes.orc** - Arquivos ORC
11. **vendas_avro.json**, **clientes_avro.json** - Dados no formato Avro (JSON)
12. **delta_vendas.parquet**, **delta_clientes.parquet** - Arquivos Parquet para Delta Lake

### APIs
13. **rest_api_server.py** - Servidor REST API de exemplo (FastAPI)
14. **google_sheets_config.json** - Configuração para Google Sheets

### Documentação
15. **configuracoes_conectores.md** - Guia completo de configuração
16. **README.md** - Este arquivo

## Conectores Suportados

### 1. Arquivos Locais
- **CSV**: Use `vendas.csv`
- **JSON**: Use `clientes.json`
- **Excel**: Use `produtos.xlsx`
- **XML**: Use `clientes.xml`

### 2. Bancos de Dados
- **PostgreSQL**: Use `database_setup.sql` + `dados_inserts.sql`
- **MySQL**: Use `database_setup.sql` + `dados_inserts.sql`

### 3. Formatos Big Data
- **Parquet**: Use `vendas.parquet`, `clientes.parquet`, `produtos.parquet`
- **ORC**: Use `vendas.orc`, `clientes.orc`
- **Avro**: Use `vendas.avsc` + `vendas_avro.json` (schema + dados)
- **Delta Lake**: Use `delta_vendas.parquet`, `delta_clientes.parquet`

### 4. PostgreSQL
- Execute: `docker run --name postgres-dataflow -e POSTGRES_PASSWORD=senha123 -e POSTGRES_DB=dataflow_test -p 5432:5432 -d postgres:15`
- Setup: `psql -h localhost -U postgres -d dataflow_test -f database_setup.sql`
- Insira dados: `psql -h localhost -U postgres -d dataflow_test -f dados_inserts.sql`

### 5. MySQL
- Execute: `docker run --name mysql-dataflow -e MYSQL_ROOT_PASSWORD=senha123 -e MYSQL_DATABASE=dataflow_test -p 3306:3306 -d mysql:8.0`
- Setup: `mysql -h localhost -u root -psenha123 dataflow_test < database_setup.sql`
- Insira dados: `mysql -h localhost -u root -psenha123 dataflow_test < dados_inserts.sql`

### 6. Google Sheets
- Configure credenciais no Google Cloud Console
- Compartilhe planilha com service account
- Use `google_sheets_config.json` como referência

### 7. REST API
- Inicie servidor: `python rest_api_server.py`
- API disponível em: http://localhost:8001
- Endpoints: `/clientes`, `/produtos`, `/vendas`, `/estatisticas`

## Como Usar

### Passo 1: Escolher um Conector
1. **Para começar**: Use arquivos locais (CSV, JSON, Excel)
2. **Para testar APIs**: Inicie o servidor REST API
3. **Para bancos de dados**: Use Docker containers
4. **Para Google Sheets**: Configure credenciais

### Passo 2: Criar Fontes de Dados
No frontend do Dataflow:
1. Acesse "Fontes de Dados"
2. Crie nova fonte com o conector desejado
3. Configure a conexão (veja `configuracoes_conectores.md`)
4. Teste a conexão

### Passo 3: Ingestão de Dados
1. Crie ingestões para cada fonte
2. Use o preview para verificar dados
3. Execute as ingestões para carregar no DuckDB

### Passo 4: Pipeline Completo
```
Fontes → Ingestão → Staging → Modelagem → Métricas → Dashboards
```

## Fluxo de Teste Sugerido

### Nível 1: Básico (Arquivos Locais)
1. Fonte CSV → Ingestão → Staging → Dashboard
2. Fonte JSON → Ingestão → Staging → Dashboard  
3. Fonte Excel → Ingestão → Staging → Dashboard

### Nível 2: Intermediário (APIs)
1. Inicie `rest_api_server.py`
2. Fonte REST API → Ingestão → Staging → Dashboard
3. Configure Google Sheets → Ingestão → Staging → Dashboard

### Nível 3: Avançado (Bancos de Dados)
1. PostgreSQL → Ingestão → Staging → Modelagem
2. MySQL → Ingestão → Staging → Modelagem
3. Combine múltiplas fontes → Pipeline completo

### Nível 4: Completo (Integração)
1. Múltiplas fontes (CSV + API + PostgreSQL)
2. Transformações complexas no Staging
3. Modelagem dimensional completa
4. Métricas avançadas e dashboards interativos

## Estrutura Sugerida de Pipeline

```
Fontes Diversas (CSV, JSON, API, PostgreSQL)
  ↓
Ingestão (raw_vendas, raw_clientes, raw_produtos)
  ↓
Staging (stg_vendas, stg_clientes, stg_produtos)
  ↓
Modelagem (dim_clientes, dim_produtos, dim_tempo, fato_vendas)
  ↓
Métricas (total_vendas, ticket_medio, top_produtos)
  ↓
Dashboards (Vendas, Clientes, Produtos, Performance)
```

## Testes Sugeridos

### Testes de Conectores
- [ ] Ingestão CSV funcionando
- [ ] Ingestão JSON funcionando  
- [ ] Ingestão Excel funcionando
- [ ] Conector PostgreSQL funcionando
- [ ] Conector MySQL funcionando
- [ ] Conector REST API funcionando
- [ ] Conector Google Sheets funcionando

### Testes de Pipeline
- [ ] Transformações no Staging
- [ ] Modelagem dimensional
- [ ] Cálculo de métricas
- [ ] Criação de dashboards
- [ ] Execução completa do DAG

## Documentação Adicional

- **Configurações Detalhadas**: `configuracoes_conectores.md`
- **API Documentation**: http://localhost:8001/docs (após iniciar servidor)
- **Google Sheets Setup**: `google_sheets_config.json`
