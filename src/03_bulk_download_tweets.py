#!/usr/bin/env python3
"""
03_bulk_download_tweets.py
==========================
Baixa tweets em larga escala da API v2 do X com suporte a:
- Paginação automática via next_token
- Continuidade inteligente (--resume para voltar no tempo, --resume-latest para tweets novos)
- Prevenção total de cobranças duplicadas da API do X
- Filtros de tempo (--since-hours, --start-time, --end-time)
- Salvamento contínuo em .jsonl (não perde dados se interrompido)
- Desduplicação automática por ID e exportação final em Apache Parquet (.parquet)
- Trava de segurança de orçamento ($0.005 por tweet lido)
- Respeito a Rate Limits (espera automática se atingir o teto de requisições)
- Barra de progresso rica com estimativa de custos em tempo real (USD e BRL)

Uso:
    uv run python src/03_bulk_download_tweets.py
    uv run python src/03_bulk_download_tweets.py --resume
    uv run python src/03_bulk_download_tweets.py --resume-latest
"""

import argparse
import re
import signal
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq

# Adiciona o diretório 'src' ao sys.path para garantir imports corretos
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from baixa_dados_tweets.client import BudgetExceededError, XAPIError, XClient
from baixa_dados_tweets.config import (
    COST_PER_TWEET_READ_USD,
    DEFAULT_AI_QUERY,
    DEFAULT_USD_TO_BRL,
    settings,
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
INTERRUPTED = False


def signal_handler(sig, frame):
    global INTERRUPTED
    console.print(
        "\n[bold yellow]⚠️ Interrupção solicitada (Ctrl+C). Finalizando lote atual com segurança...[/bold yellow]"
    )
    INTERRUPTED = True


signal.signal(signal.SIGINT, signal_handler)


def slugify(text: str) -> str:
    """Gera um slug seguro para nome de arquivo a partir da query."""
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", text)[:30]


def get_existing_bounds(parquet_path: Path) -> tuple[str | None, str | None, str | None, str | None, int]:
    """
    Inspeciona arquivo Parquet existente para obter:
    (oldest_id, oldest_date, newest_id, newest_date, total_existing)
    """
    if not parquet_path.exists():
        return None, None, None, None, 0
    try:
        table = pq.read_table(parquet_path)
        dates = [str(d) for d in table.column("created_at").to_pylist()]
        ids = [str(i) for i in table.column("id").to_pylist()]
        if not dates:
            return None, None, None, None, 0
        min_date = min(dates)
        max_date = max(dates)
        oldest_id = ids[dates.index(min_date)]
        newest_id = ids[dates.index(max_date)]
        return oldest_id, min_date, newest_id, max_date, len(ids)
    except Exception as e:
        console.print(f"[dim]Aviso ao ler Parquet existente: {e}[/dim]")
        return None, None, None, None, 0


def parse_args():
    parser = argparse.ArgumentParser(
        description="Baixa tweets em larga escala sobre IA nos 15 maiores idiomas até o limite de créditos"
    )
    parser.add_argument(
        "--query",
        type=str,
        default=DEFAULT_AI_QUERY,
        help="Termo de pesquisa com sintaxe da API v2 (padrão: 15 maiores idiomas + ChatGPT, Claude, Gemini, GPT)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=settings.max_tweets_limit,
        help=f"Quantidade máxima de tweets a baixar no total (padrão do .env: {settings.max_tweets_limit} tweets)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Quantidade de tweets por requisição (mínimo 10, máximo 100, padrão: 100 para máxima eficiência)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Continua a coleta voltando no tempo a partir do tweet mais antigo já baixado (evita pagar duplicado)",
    )
    parser.add_argument(
        "--resume-latest",
        action="store_true",
        help="Coleta tweets novos publicados após o tweet mais recente já baixado",
    )
    parser.add_argument(
        "--since-hours",
        type=float,
        default=None,
        help="Coleta apenas tweets publicados nas últimas N horas (ex: --since-hours 24)",
    )
    parser.add_argument(
        "--start-time",
        type=str,
        default=None,
        help="Data/hora inicial UTC mais antiga a considerar (ex: '2026-10-17' ou '2026-10-17T00:00:00Z')",
    )
    parser.add_argument(
        "--end-time",
        type=str,
        default=None,
        help="Data/hora final UTC mais recente a considerar (ex: '2026-10-17T12:00:00Z')",
    )
    parser.add_argument(
        "--max-budget",
        type=float,
        default=settings.max_budget_usd,
        help=f"Teto máximo de orçamento em USD para esta execução (padrão do .env: US$ {settings.max_budget_usd:.2f})",
    )
    parser.add_argument(
        "--output-name",
        type=str,
        default="tweets_ia_global",
        help="Nome personalizado para o arquivo .jsonl/.parquet gerado",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    max_budget = args.max_budget if args.max_budget is not None else settings.max_budget_usd
    batch_size = max(10, min(100, args.batch_size))
    total_target = max(10, args.limit)

    bulk_dir = ensure_data_directory("bulk")
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    query_slug = slugify(args.query) or "search"
    base_name = args.output_name or f"tweets_{query_slug}_{timestamp_str}"
    output_filepath = bulk_dir / f"{base_name}.jsonl" if not base_name.endswith(".jsonl") else bulk_dir / base_name
    parquet_filepath = output_filepath.with_suffix(".parquet")
    meta_filepath = bulk_dir / f"meta_{query_slug}_{timestamp_str}.json"

    iso_start_time = format_iso_time(args.start_time, args.since_hours)
    iso_end_time = format_iso_time(args.end_time)
    until_id: str | None = None
    since_id: str | None = None

    oldest_id, min_date, newest_id, max_date, existing_count = get_existing_bounds(parquet_filepath)

    if args.resume:
        if oldest_id:
            until_id = oldest_id
            console.print(
                f"[bold green]🔄 Modo --resume ativado:[/bold green] Continuando para trás a partir do tweet mais antigo ({min_date}). Zero duplicatas!"
            )
        else:
            console.print(
                "[yellow]⚠️ Modo --resume ativado, mas nenhum dado prévio encontrado. Iniciando busca normal...[/yellow]"
            )
    elif args.resume_latest:
        if newest_id:
            since_id = newest_id
            console.print(
                f"[bold green]🔄 Modo --resume-latest ativado:[/bold green] Buscando tweets novos publicados após {max_date}. Zero duplicatas!"
            )
        else:
            console.print(
                "[yellow]⚠️ Modo --resume-latest ativado, mas nenhum dado prévio encontrado. Iniciando busca normal...[/yellow]"
            )

    console.print("\n[bold cyan]🚀 03. Coletor de Dados em Larga Escala (X/Twitter API v2)[/bold cyan]")
    console.print("=" * 68)

    try:
        client = XClient()
    except ValueError as e:
        console.print(f"[bold red]❌ Erro de configuração:[/bold red] {e}")
        sys.exit(1)

    max_expected_cost_usd = total_target * COST_PER_TWEET_READ_USD
    max_expected_cost_brl = max_expected_cost_usd * DEFAULT_USD_TO_BRL

    summary_table = Table(show_header=False, box=None)
    summary_table.add_row("[bold cyan]Termo de Busca:[/bold cyan]", f"[yellow]{args.query}[/yellow]")
    summary_table.add_row("[bold cyan]Meta de Novos Tweets:[/bold cyan]", f"{total_target:,} tweets")
    summary_table.add_row("[bold cyan]Tamanho do Lote:[/bold cyan]", f"{batch_size} tweets por requisição")
    if existing_count > 0:
        summary_table.add_row(
            "[bold cyan]Base Existente:[/bold cyan]", f"{existing_count:,} tweets salvos anteriormente"
        )
    if until_id:
        summary_table.add_row(
            "[bold cyan]Filtro de Continuidade:[/bold cyan]", f"Tweets anteriores a ID {until_id} ({min_date})"
        )
    elif since_id:
        summary_table.add_row(
            "[bold cyan]Filtro de Continuidade:[/bold cyan]", f"Tweets posteriores a ID {since_id} ({max_date})"
        )
    else:
        summary_table.add_row(
            "[bold cyan]Filtro de Data/Hora:[/bold cyan]",
            f"Início: {iso_start_time or 'Últimos 7 dias (padrão)'} | Fim: {iso_end_time or 'Agora'}",
        )
    summary_table.add_row(
        "[bold cyan]Custo Máximo Estimado:[/bold cyan]",
        f"US$ {max_expected_cost_usd:.2f} (~R$ {max_expected_cost_brl:.2f})",
    )
    summary_table.add_row("[bold cyan]Teto de Orçamento (Trava):[/bold cyan]", f"[green]US$ {max_budget:.2f}[/green]")
    summary_table.add_row("[bold cyan]Arquivo de Saída:[/bold cyan]", f"[dim]{output_filepath.name} + .parquet[/dim]")

    console.print(Panel(summary_table, title="Parâmetros de Execução", border_style="cyan"))

    next_token: str | None = None
    total_downloaded = 0
    pages_fetched = 0
    start_time = time.time()
    oldest_tweet_date = None
    newest_tweet_date = None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("• {task.completed}/{task.total} tweets"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[green]Baixando tweets...", total=total_target)

        while total_downloaded < total_target and not INTERRUPTED:
            remaining_needed = total_target - total_downloaded
            current_batch = min(batch_size, remaining_needed)
            current_batch = max(current_batch, 10)

            try:
                response = client.search_recent_tweets(
                    query=args.query,
                    max_results=current_batch,
                    next_token=next_token,
                    start_time=iso_start_time,
                    end_time=iso_end_time,
                    until_id=until_id,
                    since_id=since_id,
                )
            except BudgetExceededError as be:
                console.print(f"\n[bold yellow]🛑 {be}[/bold yellow]")
                break
            except XAPIError as err:
                console.print(f"\n[bold red]❌ Erro na API do X:[/bold red] {err}")
                break
            except Exception as exc:
                console.print(f"\n[bold red]❌ Falha na requisição:[/bold red] {exc}")
                break

            tweets = response.get("data", [])
            includes = response.get("includes", {})
            users = {u["id"]: u for u in includes.get("users", [])}
            meta = response.get("meta", {})

            if not tweets:
                console.print(
                    "\n[yellow]Fim dos resultados disponíveis para esta consulta no período solicitado.[/yellow]"
                )
                break

            # Rastreamento de datas dos tweets
            for t in tweets:
                dt_str = t.get("created_at")
                if dt_str:
                    if newest_tweet_date is None or dt_str > newest_tweet_date:
                        newest_tweet_date = dt_str
                    if oldest_tweet_date is None or dt_str < oldest_tweet_date:
                        oldest_tweet_date = dt_str

            records = [normalize_tweet_record(t, users) for t in tweets]
            append_jsonl(records, output_filepath)

            total_downloaded += len(records)
            pages_fetched += 1
            progress.update(task, completed=min(total_downloaded, total_target))

            next_token = meta.get("next_token")
            if not next_token:
                console.print("\n[dim]Nenhuma página seguinte (next_token ausente). Coleta completa![/dim]")
                break

            time.sleep(1.0)

    # Conversão automática para Parquet com desduplicação
    parquet_saved = None
    if output_filepath.exists():
        parquet_saved = jsonl_to_parquet(output_filepath, parquet_filepath)

    elapsed_seconds = time.time() - start_time
    total_cost_usd = total_downloaded * COST_PER_TWEET_READ_USD
    total_cost_brl = total_cost_usd * DEFAULT_USD_TO_BRL

    meta_info = {
        "query": args.query,
        "new_tweets_downloaded": total_downloaded,
        "pages_fetched": pages_fetched,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "cost_usd": round(total_cost_usd, 4),
        "cost_brl": round(total_cost_brl, 4),
        "time_filters": {
            "start_time": iso_start_time,
            "end_time": iso_end_time,
            "until_id": until_id,
            "since_id": since_id,
        },
        "tweet_dates_range": {
            "newest": newest_tweet_date,
            "oldest": oldest_tweet_date,
        },
        "last_next_token": next_token,
        "interrupted_by_user": INTERRUPTED,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "jsonl_file": str(output_filepath),
        "parquet_file": str(parquet_saved) if parquet_saved else None,
    }
    save_json(meta_info, meta_filepath)
    client.close()

    console.print("\n" + "=" * 68)
    console.print("[bold green]🏁 Coleta em Larga Escala Finalizada com Sucesso![/bold green]")
    console.print(f"  • Novos tweets baixados nesta rodada: [bold]{total_downloaded:,}[/bold]")
    console.print(
        f"  • Período deste lote: [cyan]{oldest_tweet_date or 'N/A'}[/cyan] até [cyan]{newest_tweet_date or 'N/A'}[/cyan]"
    )
    console.print(f"  • Páginas requisitadas: [bold]{pages_fetched}[/bold]")
    console.print(f"  • Tempo decorrido: [bold]{elapsed_seconds:.1f} segundos[/bold]")
    console.print(
        f"  • Custo desta rodada: [bold green]US$ {total_cost_usd:.4f}[/bold green] (~R$ {total_cost_brl:.2f})"
    )
    console.print(f"  • Arquivo JSONL consolidado: [cyan]{output_filepath}[/cyan]")
    if parquet_saved:
        console.print(f"  • Arquivo Parquet consolidado (sem duplicatas): [bold green]{parquet_saved}[/bold green]")
    console.print(f"  • Metadados desta Coleta: [cyan]{meta_filepath}[/cyan]")
    console.print("=" * 68 + "\n")


if __name__ == "__main__":
    main()
