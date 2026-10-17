#!/usr/bin/env python3
"""
02_fetch_sample_tweets.py
=========================
Baixa uma amostra de tweets (ex: 10 a 50) para um termo de busca, exibe na tela
em formato de tabela e salva os resultados em:
- data/sample_tweets.json (bruto da API)
- data/sample_tweets.jsonl (streaming/linhas)
- data/sample_tweets.parquet (colunar de alta performance para DuckDB/Polars)

Uso:
    uv run python src/02_fetch_sample_tweets.py
    uv run python src/02_fetch_sample_tweets.py --query "inteligencia artificial lang:pt" --count 15
    uv run python src/02_fetch_sample_tweets.py --since-hours 24 --count 20
"""

import argparse
import sys
from pathlib import Path

# Adiciona o diretório 'src' ao sys.path para garantir imports corretos
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rich.console import Console
from rich.table import Table

from baixa_dados_tweets.client import XAPIError, XClient
from baixa_dados_tweets.config import (
    COST_PER_TWEET_READ_USD,
    DEFAULT_AI_QUERY,
    DEFAULT_USD_TO_BRL,
)
from baixa_dados_tweets.storage import (
    append_jsonl,
    ensure_data_directory,
    format_iso_time,
    jsonl_to_parquet,
    normalize_tweet_record,
    save_json,
)

console = Console()


def parse_args():
    parser = argparse.ArgumentParser(description="Baixa uma amostra de teste de tweets sobre IA (15 idiomas)")
    parser.add_argument(
        "--query",
        type=str,
        default=DEFAULT_AI_QUERY,
        help="Termo de busca com operadores da API v2 (padrão: 15 maiores idiomas + IAs)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Quantidade de tweets na amostra (10 a 100, padrão: 10)",
    )
    parser.add_argument(
        "--since-hours",
        type=float,
        default=None,
        help="Buscar tweets publicados apenas nas últimas N horas (ex: --since-hours 24)",
    )
    parser.add_argument(
        "--start-time",
        type=str,
        default=None,
        help="Data/hora inicial UTC no formato ISO (ex: '2026-10-17' ou '2026-10-17T00:00:00Z')",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    count = max(10, min(100, args.count))
    iso_start_time = format_iso_time(args.start_time, args.since_hours)

    console.print("\n[bold cyan]📥 02. Baixar Amostra de Tweets do X/Twitter[/bold cyan]")
    console.print("=" * 60)
    console.print(f"[bold]Query de busca:[/bold] [yellow]{args.query}[/yellow]")
    console.print(f"[bold]Quantidade solicitada:[/bold] [yellow]{count}[/yellow] tweets")
    if iso_start_time:
        console.print(f"[bold]Filtro de Tempo (Início UTC):[/bold] [cyan]{iso_start_time}[/cyan]")
    else:
        console.print("[dim]Filtro de Tempo: Janela padrão recente (últimos 7 dias, ordem mais recente primeiro)[/dim]")

    try:
        client = XClient()
    except ValueError as e:
        console.print(f"[bold red]❌ Configuração ausente:[/bold red] {e}")
        sys.exit(1)

    console.print("[dim]Consultando endpoint /2/tweets/search/recent...[/dim]\n")

    try:
        response = client.search_recent_tweets(
            query=args.query,
            max_results=count,
            start_time=iso_start_time,
        )
        tweets = response.get("data", [])
        includes = response.get("includes", {})
        users = {u["id"]: u for u in includes.get("users", [])}
        meta = response.get("meta", {})

        if not tweets:
            console.print("[yellow]Nenhum tweet encontrado para essa busca no período solicitado.[/yellow]")
            client.close()
            return

        table = Table(title=f"Amostra de Tweets ({len(tweets)} encontrados)", show_lines=True)
        table.add_column("Autor", style="cyan", width=18)
        table.add_column("Tweet", style="white")
        table.add_column("Curtidas", justify="right", style="green", width=10)
        table.add_column("RTs", justify="right", style="magenta", width=8)
        table.add_column("Data (UTC)", style="dim", width=20)

        normalized_records = []
        for tweet in tweets:
            record = normalize_tweet_record(tweet, users)
            normalized_records.append(record)

            author_tag = f"@{record['author_username']}" if record["author_username"] else record["author_id"]
            text_preview = record["text"].replace("\n", " ")
            if len(text_preview) > 90:
                text_preview = text_preview[:87] + "..."

            table.add_row(
                author_tag,
                text_preview,
                str(record["like_count"]),
                str(record["retweet_count"]),
                str(record["created_at"])[:19],
            )

        console.print(table)

        # Salvar em disco
        data_dir = ensure_data_directory()
        json_path = data_dir / "sample_tweets.json"
        jsonl_path = data_dir / "sample_tweets.jsonl"
        parquet_path = data_dir / "sample_tweets.parquet"

        save_json(response, json_path)
        if jsonl_path.exists():
            jsonl_path.unlink()
        append_jsonl(normalized_records, jsonl_path)
        jsonl_to_parquet(jsonl_path, parquet_path)

        # Calcular custos
        cost_usd = len(tweets) * COST_PER_TWEET_READ_USD
        cost_brl = cost_usd * DEFAULT_USD_TO_BRL

        console.print("\n[bold green]💾 Dados salvos com sucesso nos 3 formatos:[/bold green]")
        console.print(f"  • JSON Completo (bruto): [cyan]{json_path}[/cyan]")
        console.print(f"  • JSONL (streaming tabular): [cyan]{jsonl_path}[/cyan]")
        console.print(f"  • Parquet (colunar analítico): [bold green]{parquet_path}[/bold green]")

        console.print("\n[bold]💰 Custo desta execução (estimativa Pay-Per-Use):[/bold]")
        console.print(f"  • Tweets lidos: [bold]{len(tweets)}[/bold]")
        console.print(f"  • Custo USD: [green]${cost_usd:.4f}[/green]")
        console.print(f"  • Custo BRL (~R$ 5,80/USD): [green]R$ {cost_brl:.4f}[/green]")

        if meta.get("next_token"):
            console.print(f"\n[dim]Próximo token de paginação disponível: {meta['next_token'][:20]}...[/dim]")
            console.print("Para baixar em larga escala com paginação contínua, use o script 03 ou 04:")
            console.print("  [cyan]uv run python src/03_bulk_download_tweets.py[/cyan]")

        client.close()

    except XAPIError as err:
        console.print(f"[bold red]❌ Erro retornado pela API do X:[/bold red] {err}")
        sys.exit(1)
    except Exception as exc:
        console.print(f"[bold red]❌ Erro inesperado:[/bold red] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
