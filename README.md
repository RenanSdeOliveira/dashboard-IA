# Porsche Sales Data Pipeline
 
Sistema completo de sanitização, análise e visualização de dados de vendas da Porsche — do dado bruto ao dashboard interativo.
 
---
 
## Visão geral
 
Este repositório contém três componentes principais que trabalham em conjunto:
 
| Arquivo | Descrição |
|---|---|
| `schema.md` | Contrato de dados — define todas as regras de normalização |
| `sanitize_porsche.py` | Script Python que executa as regras e gera o Excel limpo |
| `porsche_database.xlsx` | Planilha bruta com dados inconsistentes |
| `porsche_database_sanitized.xlsx` | Planilha limpa gerada pelo script |
| `dashboard.html` | Dashboard interativo com KPIs e gráficos filtráveis |
 
---
 
## Como funciona
 
### 1. `schema.md` — o contrato de dados
 
Documento de referência que especifica:
 
- Quais colunas existem no Excel bruto e quais são obrigatórias
- Como cada coluna deve ser normalizada (formato de entrada → formato de saída)
- Quais valores são considerados inválidos e como marcá-los (`INVALID`)
- Regras de qualidade a verificar após a sanitização
É o ponto de partida para qualquer contribuição ou extensão do pipeline — toda regra de negócio vive aqui antes de virar código.
 
### 2. `sanitize_porsche.py` — o script de sanitização
 
Lê `porsche_database.xlsx`, aplica todas as transformações definidas no schema e grava `porsche_database_sanitized.xlsx`. Cada coluna sanitizada é inserida imediatamente à direita de sua coluna de origem.
 
**Uso:**
 
Solicite a IA de preferência para executar, passando o script e o arquivo base. Ou se tiver o python instalado use manualmente.
 
**O que o script transforma:**
 
| Campo | Exemplo de entrada | Saída |
|---|---|---|
| Data | `April 31st, 2024` | `INVALID` |
| Data | `2024.07.11` | `2024-07-11` |
| Preço | `188k USD` | `188000.00` |
| Preço | `eighty two thousand USD` | `82000.00` |
| Quilometragem | `KM 18.900` | `11744` (convertido de km) |
| Quilometragem | `new` | `0` |
| Ano do modelo | `twenty twenty four` | `2024` |
| Ano do modelo | `20-23` | `2023` |
| Estado | `california` | `CA` |
| Pagamento | `bank-transfer` | `Bank Transfer` |
| Status | `DELIVERD` | `Delivered` |
 
Ao final da execução, o script imprime um resumo de quantos valores `INVALID` foram gerados por coluna.
 
**Organização interna do código:**
 
- Uma função de sanitização dedicada por tipo de dado: `sanitize_date`, `sanitize_price`, `sanitize_mileage`, `sanitize_year`, `sanitize_payment`, `sanitize_state`, `sanitize_delivery`, entre outras
- `COLUMN_PIPELINE` — lista central que associa cada coluna-fonte à sua função de limpeza e ao nome da coluna de saída
- `process_workbook` — função principal que orquestra leitura, transformação e escrita do Excel com formatação visual (cabeçalhos coloridos, colunas sanitizadas destacadas em verde)
### 3. `porsche_database.xlsx` e `porsche_database_sanitized.xlsx`
 
A planilha bruta contém 100 registros de vendas com inconsistências reais: datas em formatos variados, preços escritos por extenso, quilometragem em quilômetros, estados em caixa baixa, erros de digitação em status de entrega, entre outros.
 
A planilha sanitizada mantém todas as colunas originais e adiciona as colunas normalizadas ao lado de cada fonte, facilitando auditoria e comparação direta entre o valor bruto e o tratado.
 
### 4. `dashboard.html` — dashboard interativo
 
Arquivo HTML autossuficiente (sem dependências externas além de Chart.js via CDN) que consome os dados já sanitizados e exibe:
 
**KPIs no topo:**
- Receita total, ticket médio, taxa de entrega e taxa de cancelamento — todos reativos aos filtros
**Gráficos:**
 
| Visualização | Tipo de gráfico | Justificativa |
|---|---|---|
| Evolução de receita ao longo do tempo | Linha com área | Tendência temporal contínua |
| Receita por família de modelo | Barras horizontais | Comparação de categorias nomeadas |
| Distribuição dos meios de pagamento | Donut | Proporção de partes num todo |
| Pipeline de entregas | Barras verticais | Frequência de categorias discretas com cor semântica |
| Vendas por ano do modelo | Barras verticais | Progressão cronológica natural |
| Ranking de vendedores | Barras horizontais | Ranking com rótulos de texto longos |
 
**Filtros interativos:**
- Ano do modelo (2020–2026)
- Família de produto (911, Taycan, Cayenne, Panamera, Macan, 718)
- Status de entrega
- Ordenação do ranking de vendedores (por receita ou por número de vendas)
Todos os gráficos e KPIs se atualizam em tempo real ao aplicar qualquer filtro.
 
**Para abrir:** basta fazer duplo clique no arquivo `dashboard.html` — nenhum servidor necessário.
 
