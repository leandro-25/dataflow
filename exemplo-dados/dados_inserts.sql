-- Arquivo SQL com dados de exemplo para teste de conectores
-- Execute apenas os INSERTs após criar as tabelas

-- Inserir categorias
INSERT INTO categorias (nome, descricao) VALUES 
('Informática', 'Computadores e periféricos'),
('Eletrônicos', 'Aparelhos eletrônicos em geral'),
('Móveis', 'Móveis para escritório e casa'),
('Áudio', 'Fones, caixas de som e equipamentos de áudio'),
('Acessórios', 'Cabos, adaptadores e periféricos diversos');

-- Inserir clientes
INSERT INTO clientes (nome, email, telefone, data_nascimento, cpf, endereco, cidade, estado, cep, status) VALUES 
('João Silva', 'joao.silva@email.com', '(11) 98765-4321', '1985-03-15', '123.456.789-00', 'Rua das Flores, 123', 'São Paulo', 'SP', '01234-567', 'ativo'),
('Maria Santos', 'maria.santos@email.com', '(21) 98765-4322', '1990-07-22', '987.654.321-00', 'Avenida Brasil, 456', 'Rio de Janeiro', 'RJ', '20000-000', 'ativo'),
('Carlos Oliveira', 'carlos.oliveira@email.com', '(31) 98765-4323', '1988-11-08', '456.789.123-00', 'Rua Mineiros, 789', 'Belo Horizonte', 'MG', '30000-000', 'ativo'),
('Ana Costa', 'ana.costa@email.com', '(51) 98765-4324', '1992-05-30', '789.123.456-00', 'Rua dos Andradas, 321', 'Porto Alegre', 'RS', '90000-000', 'ativo'),
('Pedro Souza', 'pedro.souza@email.com', '(41) 98765-4325', '1978-09-12', '321.654.987-00', 'Rua XV de Novembro, 100', 'Curitiba', 'PR', '80000-000', 'ativo'),
('Julia Mendes', 'julia.mendes@email.com', '(71) 98765-4326', '1995-12-25', '654.987.321-00', 'Avenida Atlântica, 200', 'Salvador', 'BA', '40000-000', 'inativo'),
('Roberto Alves', 'roberto.alves@email.com', '(85) 98765-4327', '1982-04-18', '111.222.333-00', 'Rua Dr. João Pessoa, 50', 'Fortaleza', 'CE', '60000-000', 'ativo'),
('Fernanda Lima', 'fernanda.lima@email.com', '(81) 98765-4328', '1987-08-30', '444.555.666-00', 'Rua do Bom Jesus, 80', 'Recife', 'PE', '50000-000', 'ativo');

-- Inserir fornecedores
INSERT INTO fornecedores (nome, cnpj, contato, telefone, email, endereco, cidade, estado, status) VALUES 
('Dell Computadores Ltda', '12.345.678/0001-01', 'Carlos Dell', '(11) 4000-0001', 'vendas@dell.com.br', 'Av. Paulista, 1000', 'São Paulo', 'SP', 'ativo'),
('Logitech Brasil', '23.456.789/0001-02', 'Maria Logi', '(11) 4000-0002', 'contato@logitech.com', 'Av. Brigadeiro Faria Lima, 500', 'São Paulo', 'SP', 'ativo'),
('LG Electronics', '34.567.890/0001-03', 'João LG', '(11) 4000-0003', 'vendas@lg.com.br', 'Av. Eng. Luís Carlos Berrini, 100', 'São Paulo', 'SP', 'ativo'),
('JBL do Brasil', '45.678.901/0001-04', 'Ana JBL', '(21) 4000-0004', 'contato@jbl.com.br', 'Av. Niemeyer, 200', 'Rio de Janeiro', 'RJ', 'ativo'),
('Redragon Periféricos', '56.789.012/0001-05', 'Pedro Red', '(31) 4000-0005', 'vendas@redragon.com', 'Av. Amazonas, 300', 'Belo Horizonte', 'MG', 'ativo');

-- Inserir produtos
INSERT INTO produtos (nome, descricao, categoria_id, preco_custo, preco_venda, estoque, sku, codigo_barras, status) VALUES 
('Notebook Dell Inspiron', 'Notebook Dell Intel Core i5, 8GB RAM, 256GB SSD', 1, 2800.00, 3500.00, 15, 'NOTE-DELL-001', '7891234567890', 'ativo'),
('Mouse Logitech MX Master', 'Mouse sem fio ergonômico', 1, 65.00, 89.90, 50, 'MOUSE-LOG-001', '7891234567891', 'ativo'),
('Teclado Mecânico Redragon', 'Teclado mecânico RGB', 1, 220.00, 299.00, 25, 'TECL-RED-001', '7891234567892', 'ativo'),
('Monitor LG 27 UltraWide', 'Monitor 27" UltraWide 4K', 2, 950.00, 1200.00, 8, 'MON-LG-001', '7891234567893', 'ativo'),
('Fone Bluetooth JBL', 'Fone de ouvido Bluetooth', 4, 150.00, 199.00, 40, 'FONE-JBL-001', '7891234567894', 'ativo'),
('Webcam Logitech C920', 'Webcam HD 1080p', 1, 180.00, 249.90, 20, 'WEBC-LOG-001', '7891234567895', 'ativo'),
('Caixa de Som JBL Flip', 'Caixa de som Bluetooth resistente à água', 4, 220.00, 299.00, 15, 'CAIX-JBL-001', '7891234567896', 'ativo'),
('Mouse Pad Gamer XXL', 'Mouse pad 90x40cm', 5, 25.00, 49.90, 100, 'MOUP-GAM-001', '7891234567897', 'ativo'),
('Hub USB 4 Portas', 'Hub USB 3.0 4 portas', 5, 35.00, 59.90, 60, 'HUB-USB-001', '7891234567898', 'ativo'),
('Cabo HDMI 2m', 'Cabo HDMI 4K 2 metros', 5, 15.00, 29.90, 200, 'CAB-HDMI-001', '7891234567899', 'ativo'),
('Notebook Dell XPS 13', 'Notebook Dell Intel Core i7, 16GB RAM, 512GB SSD', 1, 4500.00, 5999.00, 5, 'NOTE-DELL-002', '7891234567900', 'ativo'),
('Monitor Samsung 24"', 'Monitor 24" Full HD', 2, 450.00, 599.00, 12, 'MON-SAM-001', '7891234567901', 'ativo'),
('Fone JBL Tune 510', 'Fone de ouvido Bluetooth supra-auricular', 4, 100.00, 149.90, 35, 'FONE-JBL-002', '7891234567902', 'ativo'),
('Teclado Logitech K380', 'Teclado sem fio multi-dispositivo', 1, 120.00, 179.90, 30, 'TECL-LOG-001', '7891234567903', 'ativo'),
('Mouse Logitech G502', 'Mouse gamer RGB', 1, 90.00, 129.90, 45, 'MOUSE-G502', '7891234567904', 'ativo');

-- Inserir vendas
INSERT INTO vendas (cliente_id, data_venda, valor_total, forma_pagamento, status, observacoes) VALUES 
(1, '2024-01-15 10:30:00', 3500.00, 'cartao_credito', 'concluida', 'Venda via site'),
(2, '2024-01-16 14:20:00', 449.50, 'debito', 'concluida', NULL),
(1, '2024-01-17 09:15:00', 598.00, 'pix', 'concluida', 'Pagamento instantâneo'),
(3, '2024-01-18 16:45:00', 1200.00, 'cartao_credito', 'concluida', NULL),
(2, '2024-01-19 11:30:00', 450.00, 'dinheiro', 'concluida', NULL),
(4, '2024-01-20 15:00:00', 299.00, 'pix', 'concluida', 'Desconto promocional'),
(5, '2024-01-21 10:00:00', 249.90, 'cartao_credito', 'concluida', NULL),
(1, '2024-01-22 13:30:00', 179.90, 'debito', 'concluida', NULL),
(3, '2024-01-23 16:00:00', 5999.00, 'cartao_credito', 'concluida', 'Produto de alto valor'),
(2, '2024-01-24 11:45:00', 149.90, 'pix', 'concluida', NULL),
(6, '2024-01-25 14:15:00', 89.90, 'dinheiro', 'cancelada', 'Cancelada pelo cliente'),
(4, '2024-01-26 09:30:00', 299.00, 'cartao_credito', 'concluida', NULL),
(7, '2024-01-27 12:00:00', 129.90, 'debito', 'concluida', NULL),
(8, '2024-01-28 15:30:00', 599.00, 'pix', 'concluida', NULL),
(5, '2024-01-29 10:45:00', 199.00, 'cartao_credito', 'concluida', NULL);

-- Inserir itens de venda
INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario, desconto_percentual, subtotal) VALUES 
(1, 1, 1, 3500.00, 0, 3500.00),
(2, 2, 5, 89.90, 0, 449.50),
(3, 3, 2, 299.00, 0, 598.00),
(4, 4, 1, 1200.00, 0, 1200.00),
(5, 5, 3, 150.00, 0, 450.00),
(6, 3, 1, 299.00, 0, 299.00),
(7, 6, 1, 249.90, 0, 249.90),
(8, 9, 3, 59.90, 0, 179.90),
(9, 11, 1, 5999.00, 0, 5999.00),
(10, 13, 1, 149.90, 0, 149.90),
(11, 2, 1, 89.90, 0, 89.90),
(12, 3, 1, 299.00, 0, 299.00),
(13, 15, 1, 129.90, 0, 129.90),
(14, 12, 1, 599.00, 0, 599.00),
(15, 5, 1, 199.00, 0, 199.00);
