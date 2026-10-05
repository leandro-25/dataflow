# Configurações de Conectores para Teste

Este documento contém as configurações e instruções para testar todos os conectores do Dataflow.

## 1. PostgreSQL

### Configuração de Conexão
```json
{
  "host": "localhost",
  "port": 5432,
  "database": "dataflow_test",
  "username": "postgres",
  "password": "senha123"
}
```

### Setup do Banco de Dados
1. Instale PostgreSQL: `docker run --name postgres-dataflow -e POSTGRES_PASSWORD=senha123 -e POSTGRES_DB=dataflow_test -p 5432:5432 -d postgres:15`
2. Execute o script: `psql -h localhost -U postgres -d dataflow_test -f database_setup.sql`

### Tabelas Disponíveis
- `clientes` - Cadastro de clientes
- `categorias` - Categorias de produtos
- `produtos` - Catálogo de produtos
- `fornecedores` - Cadastro de fornecedores
- `vendas` - Vendas realizadas
- `itens_venda` - Itens das vendas

## 2. MySQL

### Configuração de Conexão
```json
{
  "host": "localhost",
  "port": 3306,
  "database": "dataflow_test",
  "username": "root",
  "password": "senha123"
}
```

### Setup do Banco de Dados
1. Instale MySQL: `docker run --name mysql-dataflow -e MYSQL_ROOT_PASSWORD=senha123 -e MYSQL_DATABASE=dataflow_test -p 3306:3306 -d mysql:8.0`
2. Execute o script: `mysql -h localhost -u root -psenha123 dataflow_test < database_setup.sql`

### Observação
O script `database_setup.sql` é compatível com PostgreSQL e MySQL (exceto pelo tipo SERIAL que pode precisar ser ajustado para AUTO_INCREMENT no MySQL).

## 3. Google Sheets

### Configuração de Conexão
```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "sheet_name": "Sheet1",
  "range": "A1:Z1000",
  "credentials_path": "./google_sheets_credentials.json"
}
```

### Setup do Google Sheets
1. **Criar Projeto Google Cloud**:
   - Acesse https://console.cloud.google.com
   - Crie um novo projeto
   - Ative a "Google Sheets API"

2. **Criar Credenciais**:
   - Vá para "APIs & Services" > "Credentials"
   - Clique "Create Credentials" > "Service Account"
   - Baixe o arquivo JSON das credenciais
   - Renomeie para `google_sheets_credentials.json`

3. **Compartilhar Planilha**:
   - Crie uma planilha no Google Sheets
   - Compartilhe com o email do service account
   - Copie o ID da planilha da URL

### Exemplo de Planilha
Crie uma planilha com os seguintes dados:

| ID | Data | Cliente | Produto | Quantidade | Valor | Total |
|----|------|---------|---------|------------|-------|-------|
| 1 | 2024-01-15 | João Silva | Notebook Dell | 1 | 3500.00 | 3500.00 |
| 2 | 2024-01-16 | Maria Santos | Mouse Logitech | 5 | 89.90 | 449.50 |
| 3 | 2024-01-17 | Carlos Oliveira | Teclado Mecânico | 2 | 299.00 | 598.00 |

## 4. REST API

### Configuração de Conexão
```json
{
  "base_url": "http://localhost:8001",
  "headers": {
    "Content-Type": "application/json",
    "Accept": "application/json"
  },
  "timeout": 30
}
```

### Setup da API de Exemplo
1. **Instale Dependências**:
   ```bash
   pip install fastapi uvicorn
   ```

2. **Execute o Servidor**:
   ```bash
   cd exemplo-dados
   python rest_api_server.py
   ```

3. **API estará disponível em**: http://localhost:8001

### Endpoints Disponíveis
- `GET /clientes` - Lista todos os clientes
- `GET /clientes/{id}` - Retorna cliente específico
- `GET /produtos` - Lista todos os produtos
- `GET /produtos/{id}` - Retorna produto específico
- `GET /vendas` - Lista todas as vendas
- `GET /vendas/{id}` - Retorna venda específica
- `GET /estatisticas` - Retorna estatísticas gerais
- `GET /docs` - Documentação interativa (Swagger)

### Exemplo de Uso no Dataflow
1. Crie uma fonte de dados do tipo "REST API"
2. Configure a URL base: `http://localhost:8001`
3. Para obter clientes, use o endpoint: `/clientes`
4. Para obter produtos, use o endpoint: `/produtos`
5. Para obter vendas, use o endpoint: `/vendas`

## 5. Arquivos Locais (CSV, JSON, Excel)

### Configuração de Conexão
```json
{
  "file_path": "./exemplo-dados/vendas.csv",
  "delimiter": ",",
  "encoding": "utf-8",
  "has_header": true
}
```

### Arquivos Disponíveis
- `vendas.csv` - Dados de vendas em formato CSV
- `clientes.json` - Cadastro de clientes em formato JSON
- `produtos.xlsx` - Catálogo de produtos em formato Excel

## Fluxo de Teste Sugerido

1. **Teste Arquivos Locais**:
   - Crie fontes para `vendas.csv`, `clientes.json`, `produtos.xlsx`
   - Crie ingestões e carregue os dados

2. **Teste REST API**:
   - Inicie o servidor: `python rest_api_server.py`
   - Crie fontes para os endpoints `/clientes`, `/produtos`, `/vendas`
   - Ingestão dos dados da API

3. **Teste PostgreSQL**:
   - Inicie o container PostgreSQL
   - Execute o script de setup
   - Crie fontes para as tabelas do banco

4. **Teste Google Sheets**:
   - Configure as credenciais
   - Crie fonte para a planilha compartilhada

5. **Pipeline Completo**:
   - Combine dados de múltiplas fontes
   - Crie transformações no staging
   - Modele dimensões e fatos
   - Gere métricas e dashboards

## Dicas de Teste

- Comece com arquivos locais (mais simples)
- Teste um conector de cada vez
- Verifique o preview dos dados antes de ingerir
- Use nomes descritivos para fontes e ingestões
- Documente suas transformações para facilitar debugging
