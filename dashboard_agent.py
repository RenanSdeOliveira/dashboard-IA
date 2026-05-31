"""
Dashboard Generator Agent
=========================

Agente de IA que lê qualquer arquivo de dados (.xlsx, .csv, .json),
analisa os campos e KPIs disponíveis, e gera automaticamente um
dashboard HTML interativo com Chart.js — pronto para abrir no navegador.

Uso:
    python dashboard_agent.py ARQUIVO_DE_DADOS [--output dashboard.html] [--title "Meu Dashboard"]

Exemplos:
    python dashboard_agent.py vendas.xlsx
    python dashboard_agent.py relatorio.csv --output meu_dashboard.html
    python dashboard_agent.py dados.json --title "KPIs de Vendas 2025"

Dependências:
    pip install anthropic pandas openpyxl

Variável de ambiente obrigatória:
    ANTHROPIC_API_KEY  — sua chave de API da Anthropic
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import anthropic
import pandas as pd


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 8000
MAX_ROWS_SAMPLE = 50       # Linhas enviadas ao modelo para análise
MAX_COLS_STATS = 30        # Máximo de colunas com estatísticas detalhadas


# ---------------------------------------------------------------------------
# Leitura de dados
# ---------------------------------------------------------------------------
def load_data(path: Path) -> pd.DataFrame:
    """Carrega .xlsx, .csv ou .json em um DataFrame."""
    ext = path.suffix.lower()
    if ext in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(path)
    if ext == ".csv":
        return pd.read_csv(path)
    if ext == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return pd.DataFrame(raw)
        if isinstance(raw, dict):
            # Tenta o primeiro array encontrado nos valores
            for v in raw.values():
                if isinstance(v, list):
                    return pd.DataFrame(v)
            return pd.DataFrame([raw])
    raise ValueError(f"Formato não suportado: {ext}. Use .xlsx, .csv ou .json")


def build_data_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Monta um resumo compacto dos dados para enviar ao modelo."""
    summary: dict[str, Any] = {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": {},
    }

    for col in df.columns:
        series = df[col].dropna()
        info: dict[str, Any] = {
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isna().sum()),
            "unique_count": int(series.nunique()),
        }

        if pd.api.types.is_numeric_dtype(series):
            info["type"] = "numeric"
            if len(series):
                info["min"] = float(series.min())
                info["max"] = float(series.max())
                info["mean"] = round(float(series.mean()), 2)
                info["sum"] = float(series.sum())

        elif pd.api.types.is_datetime64_any_dtype(series):
            info["type"] = "datetime"
            if len(series):
                info["min"] = str(series.min())
                info["max"] = str(series.max())

        else:
            info["type"] = "categorical"
            vc = series.value_counts()
            info["top_values"] = vc.head(15).to_dict()

        summary["columns"][col] = info

    # Amostra de linhas (como lista de dicts, serializable)
    sample = df.head(MAX_ROWS_SAMPLE).copy()
    for col in sample.select_dtypes(include=["datetime64"]).columns:
        sample[col] = sample[col].astype(str)
    summary["sample_rows"] = json.loads(sample.to_json(orient="records", default_handler=str))

    return summary


# ---------------------------------------------------------------------------
# Prompt de sistema
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """
Você é um agente especialista em análise de dados e visualização.

Receberá um resumo estruturado de um dataset (estatísticas por coluna + amostra de linhas)
e um título opcional. Sua tarefa é gerar um dashboard HTML completo, autossuficiente
e interativo.

## Regras de análise

1. Identifique os KPIs mais relevantes do dataset (receita total, ticket médio, contagem,
   taxas percentuais, etc.) e exiba-os como cards no topo.

2. Para cada dimensão importante, escolha o tipo de gráfico mais adequado:
   - Séries temporais → linha com área
   - Ranking / comparação entre categorias com rótulos longos → barras horizontais
   - Comparação entre poucas categorias → barras verticais
   - Proporção de partes num todo (≤8 categorias) → donut
   - Distribuição numérica → histograma ou barras
   - Correlação entre dois numéricos → scatter

3. Inclua filtros <select> que atualizem todos os gráficos e KPIs em tempo real via JavaScript.
   Escolha os filtros mais úteis com base nas colunas categóricas disponíveis.

4. Escolha no mínimo 4 e no máximo 8 gráficos. Priorize os mais informativos.

## Regras de output

- Retorne APENAS o HTML completo, sem nenhum texto antes ou depois.
- O HTML deve ser autossuficiente: sem arquivos externos além do Chart.js via CDN.
- Use Chart.js 4.4.1 via CDN: https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js
- Incorporate todos os dados diretamente no JavaScript (sem fetch).
- Layout responsivo: funciona bem em desktop (≥900px) e mobile (≤480px).
- Paleta de cores consistente e profissional.
- Título do dashboard no topo da página.
- Rodapé com contagem de registros e data de geração.

## Estrutura do HTML

```
<head> com meta charset, viewport, título e <style> inline </head>
<body>
  <header> título + subtítulo com contagem de registros </header>
  <section class="filters"> selects de filtro </section>
  <section class="kpi-grid"> cards de KPI </section>
  <section class="charts"> gráficos em grid responsivo </section>
  <footer> metadados </footer>
  <script src="Chart.js CDN"></script>
  <script> dados + lógica de filtragem + renderização de gráficos </script>
</body>
```

## Estilo

- Fundo da página: #f8f9fa
- Cards e gráficos: fundo branco, borda 1px solid #e2e8f0, border-radius 12px, padding 20px
- Fonte: system-ui, -apple-system, sans-serif
- KPI cards: label em 12px cinza, valor em 28px peso 600, cor primária #1e40af
- Cores dos gráficos (use nesta ordem): #3b82f6, #8b5cf6, #10b981, #f59e0b, #ef4444, #06b6d4, #f97316, #84cc16
- Grid de gráficos: repeat(auto-fit, minmax(420px, 1fr)), gap 16px
- Grid de KPIs: repeat(auto-fit, minmax(160px, 1fr)), gap 12px
- Mobile (<600px): grids viram 1 coluna

## JavaScript

- Embuta os dados como const DATA = [...] no topo do script.
- Crie uma função renderAll() que lê os filtros, filtra DATA, e atualiza todos os charts e KPIs.
- Destrua e recrie charts (chart.destroy() + new Chart()) ao filtrar, ou use chart.data.datasets[0].data = [...]; chart.update();
- Use Math.round() e toLocaleString() em todos os valores numéricos exibidos.
- Ao inicializar, chame renderAll() uma vez.
""".strip()


# ---------------------------------------------------------------------------
# Geração do dashboard via API
# ---------------------------------------------------------------------------
def generate_dashboard(
    data_summary: dict[str, Any],
    title: str,
    api_key: str,
) -> str:
    """Chama a API da Anthropic e retorna o HTML do dashboard."""

    client = anthropic.Anthropic(api_key=api_key)

    user_message = f"""
Título do dashboard: {title}

Resumo dos dados:
{json.dumps(data_summary, ensure_ascii=False, indent=2)}

Gere o dashboard HTML completo seguindo todas as instruções do sistema.
Retorne APENAS o código HTML, sem texto explicativo.
""".strip()

    print("  Chamando a API da Anthropic (pode levar alguns segundos)...")

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    html = message.content[0].text.strip()

    # Remove eventuais marcadores de código se o modelo os incluir
    if html.startswith("```html"):
        html = html[7:]
    if html.startswith("```"):
        html = html[3:]
    if html.endswith("```"):
        html = html[:-3]

    return html.strip()


# ---------------------------------------------------------------------------
# CLI principal
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gera um dashboard HTML interativo a partir de um arquivo de dados usando IA.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", help="Arquivo de dados (.xlsx, .csv, .json)")
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Caminho do HTML de saída (padrão: <nome_do_arquivo>_dashboard.html)",
    )
    parser.add_argument(
        "--title", "-t",
        default=None,
        help="Título do dashboard (padrão: derivado do nome do arquivo)",
    )
    args = parser.parse_args(argv)

    # API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERRO: variável de ambiente ANTHROPIC_API_KEY não definida.", file=sys.stderr)
        return 1

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERRO: arquivo não encontrado: {input_path}", file=sys.stderr)
        return 1

    # Caminhos de saída
    output_path = Path(args.output) if args.output else input_path.with_name(
        input_path.stem + "_dashboard.html"
    )
    title = args.title or (input_path.stem.replace("_", " ").replace("-", " ").title() + " Dashboard")

    # Pipeline
    print(f"\n{'='*55}")
    print(f"  Dashboard Generator Agent")
    print(f"{'='*55}")
    print(f"  Entrada : {input_path}")
    print(f"  Saída   : {output_path}")
    print(f"  Título  : {title}")
    print(f"{'='*55}\n")

    print("[ 1/4 ] Carregando dados...")
    try:
        df = load_data(input_path)
    except Exception as e:
        print(f"ERRO ao carregar dados: {e}", file=sys.stderr)
        return 1
    print(f"        {len(df)} linhas × {len(df.columns)} colunas carregadas.")

    print("[ 2/4 ] Analisando colunas e calculando estatísticas...")
    summary = build_data_summary(df)
    print(f"        {len(summary['columns'])} colunas analisadas.")

    print("[ 3/4 ] Gerando dashboard com IA...")
    try:
        html = generate_dashboard(summary, title, api_key)
    except anthropic.APIError as e:
        print(f"ERRO na API Anthropic: {e}", file=sys.stderr)
        return 1

    if len(html) < 500:
        print("AVISO: o HTML gerado parece muito curto. Verifique o output.", file=sys.stderr)

    print("[ 4/4 ] Salvando arquivo...")
    output_path.write_text(html, encoding="utf-8")

    print(f"\n  Dashboard gerado com sucesso!")
    print(f"  Abra no navegador: {output_path.resolve()}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
