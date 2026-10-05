-- Script para criar tabelas de exemplo em PostgreSQL e MySQL
-- Execute este script no seu banco de dados para testar os conectores

-- Tabela de clientes
CREATE TABLE clientes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    email VARCHAR(150) UNIQUE,
    telefone VARCHAR(20),
    data_nascimento DATE,
    cpf VARCHAR(14) UNIQUE,
    endereco TEXT,
    cidade VARCHAR(100),
    estado VARCHAR(2),
    cep VARCHAR(9),
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'ativo'
);

-- Tabela de categorias
CREATE TABLE categorias (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    categoria_pai_id INTEGER REFERENCES categorias(id),
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de produtos
CREATE TABLE produtos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    descricao TEXT,
    categoria_id INTEGER REFERENCES categorias(id),
    preco_custo DECIMAL(10,2),
    preco_venda DECIMAL(10,2),
    estoque INTEGER DEFAULT 0,
    estoque_minimo INTEGER DEFAULT 5,
    sku VARCHAR(50) UNIQUE,
    codigo_barras VARCHAR(20),
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'ativo'
);

-- Tabela de fornecedores
CREATE TABLE fornecedores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    cnpj VARCHAR(18) UNIQUE,
    contato VARCHAR(100),
    telefone VARCHAR(20),
    email VARCHAR(150),
    endereco TEXT,
    cidade VARCHAR(100),
    estado VARCHAR(2),
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'ativo'
);

-- Tabela de vendas
CREATE TABLE vendas (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER REFERENCES clientes(id),
    data_venda TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valor_total DECIMAL(10,2) NOT NULL,
    forma_pagamento VARCHAR(50),
    status VARCHAR(20) DEFAULT 'concluida',
    observacoes TEXT
);

-- Tabela de itens_venda
CREATE TABLE itens_venda (
    id SERIAL PRIMARY KEY,
    venda_id INTEGER REFERENCES vendas(id),
    produto_id INTEGER REFERENCES produtos(id),
    quantidade INTEGER NOT NULL,
    preco_unitario DECIMAL(10,2) NOT NULL,
    desconto_percentual DECIMAL(5,2) DEFAULT 0,
    subtotal DECIMAL(10,2) NOT NULL
);

-- Inserir dados de exemplo
INSERT INTO categorias (nome, descricao) VALUES
('Informática', 'Computadores e periféricos'),
('Eletrônicos', 'Aparelhos eletrônicos em geral'),
('Móveis', 'Móveis para escritório e casa'),
('Áudio', 'Fones, caixas de som e equipamentos de áudio');

INSERT INTO clientes (nome, email, telefone, data_nascimento, cpf, endereco, cidade, estado, cep) VALUES
('João Silva', 'joao.silva@email.com', '(11) 98765-4321', '1985-03-15', '123.456.789-00', 'Rua das Flores, 123', 'São Paulo', 'SP', '01234-567'),
('Maria Santos', 'maria.santos@email.com', '(21) 98765-4322', '1990-07-22', '987.654.321-00', 'Avenida Brasil, 456', 'Rio de Janeiro', 'RJ', '20000-000'),
('Carlos Oliveira', 'carlos.oliveira@email.com', '(31) 98765-4323', '1988-11-08', '456.789.123-00', 'Rua Mineiros, 789', 'Belo Horizonte', 'MG', '30000-000'),
('Ana Costa', 'ana.costa@email.com', '(51) 98765-4324', '1992-05-30', '789.123.456-00', 'Rua dos Andradas, 321', 'Porto Alegre', 'RS', '90000-000');

INSERT INTO produtos (nome, descricao, categoria_id, preco_custo, preco_venda, estoque, sku, codigo_barras) VALUES
('Notebook Dell Inspiron', 'Notebook Dell Intel Core i5, 8GB RAM, 256GB SSD', 1, 2800.00, 3500.00, 15, 'NOTE-DELL-001', '7891234567890'),
('Mouse Logitech MX Master', 'Mouse sem fio ergonômico', 1, 65.00, 89.90, 50, 'MOUSE-LOG-001', '7891234567891'),
('Teclado Mecânico Redragon', 'Teclado mecânico RGB', 1, 220.00, 299.00, 25, 'TECL-RED-001', '7891234567892'),
('Monitor LG 27 UltraWide', 'Monitor 27" UltraWide 4K', 2, 950.00, 1200.00, 8, 'MON-LG-001', '7891234567893'),
('Fone Bluetooth JBL', 'Fone de ouvido Bluetooth', 4, 150.00, 199.00, 40, 'FONE-JBL-001', '7891234567894');

INSERT INTO vendas (cliente_id, data_venda, valor_total, forma_pagamento, status) VALUES
(1, '2024-01-15 10:30:00', 3500.00, 'cartao_credito', 'concluida'),
(2, '2024-01-16 14:20:00', 449.50, 'debito', 'concluida'),
(1, '2024-01-17 09:15:00', 598.00, 'pix', 'concluida'),
(3, '2024-01-18 16:45:00', 1200.00, 'cartao_credito', 'concluida'),
(2, '2024-01-19 11:30:00', 450.00, 'dinheiro', 'concluida');

INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario, desconto_percentual, subtotal) VALUES
(1, 1, 1, 3500.00, 0, 3500.00),
(2, 2, 5, 89.90, 0, 449.50),
(3, 3, 2, 299.00, 0, 598.00),
(4, 4, 1, 1200.00, 0, 1200.00),
(5, 5, 3, 150.00, 0, 450.00);
