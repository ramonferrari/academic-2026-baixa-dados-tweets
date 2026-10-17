#!/usr/bin/env python3
"""
01_test_connectivity.py
=======================
Testa a conectividade com a API v2 oficial do X/Twitter e valida o Bearer Token.
Mostra o status da conexão, latência, cabeçalhos de rate limit e orçamento configurado.

Uso:
    uv run python src/01_test_connectivity.py
"""

import sys
import time
from pathlib import Path

# Adiciona o diretório 'src' ao sys.path para garantir imports corretos
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from baixa_dados_tweets.client import XAPIError, XClient
from baixa_dados_tweets.config import COST_PER_TWEET_READ_USD, settings

console = Console()


def main():
    console.print("\n[bold cyan]🔍 01. Teste de Conectividade com a API do X/Twitter[/bold cyan]")
    console.print("=" * 60)

    # 1. Verificar configuração do .env
    env_file = SRC_DIR.parent / ".env"
    if not env_file.exists():
        console.print(
            Panel(
                "[bold red]❌ Arquivo .env não encontrado![/bold red]\n\n"
                "Para configurar suas credenciais:\n"
                "  1. Copie o arquivo modelo: [green]cp .env.example .env[/green]\n"
                "  2. Obtenha seu Bearer Token em: [link=https://developer.x.com/en/portal/dashboard]https://developer.x.com/en/portal/dashboard[/link]\n"
                "  3. Edite o arquivo [yellow].env[/yellow] e insira seu [yellow]X_BEARER_TOKEN[/yellow].",
                title="Configuração Pendente",
                border_style="red",
            )
        )
        sys.exit(1)

    if not settings.has_bearer_token:
        console.print(
            Panel(
                "[bold yellow]⚠️ X_BEARER_TOKEN ainda não foi preenchido no .env![/bold yellow]\n\n"
                "Abra o arquivo [bold].env[/bold] e substitua 'seu_bearer_token_aqui' pelo seu token real do Developer Portal.",
                title="Atenção",
                border_style="yellow",
            )
        )
        sys.exit(1)

    # Mascarar o token para exibição segura
    raw_token = settings.bearer_token
    masked_token = raw_token[:6] + "..." + raw_token[-4:] if len(raw_token) > 12 else "***"

    console.print(f"[dim]Chave carregada:[/dim] [green]{masked_token}[/green]")
    console.print(
        f"[dim]Trava de Orçamento:[/dim] [yellow]US$ {settings.max_budget_usd:.2f}[/yellow] "
        f"(~R$ {settings.max_budget_usd * 5.8:.2f})"
    )
    console.print("[dim]Tentando conectar à API v2 (https://api.x.com/2)...[/dim]\n")

    # 2. Inicializar cliente e testar requisição
    try:
        client = XClient()
        start_time = time.perf_counter()
        response_data = client.test_connection()
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        user_info = response_data.get("data", {})
        rate_info = client.last_rate_limit_info

        table = Table(title="📊 Status da Conexão", show_header=True, header_style="bold magenta")
        table.add_column("Propriedade", style="cyan")
        table.add_column("Valor", style="white")

        table.add_row("Status HTTP", "[bold green]200 OK (Conectado!)[/bold green]")
        table.add_row("Latência", f"{elapsed_ms:.1f} ms")
        table.add_row("Conta de Teste Consultada", f"@{user_info.get('username')} ({user_info.get('name')})")
        table.add_row("ID da Conta Oficial", str(user_info.get("id")))

        if rate_info:
            table.add_row("Limite da Janela (15m)", str(rate_info.get("limit")))
            table.add_row("Requisições Restantes", str(rate_info.get("remaining")))
            table.add_row("Tempo até Reset", f"{rate_info.get('seconds_until_reset')} segundos")

        table.add_row(
            "Custo Estimado por 1.000 Tweets",
            f"US$ {COST_PER_TWEET_READ_USD * 1000:.2f} (modelo Pay-Per-Use)",
        )

        console.print(table)
        console.print(
            Panel(
                "[bold green]✅ Sucesso! Suas credenciais da API do X estão válidas e funcionais.[/bold green]\n"
                "Você já pode prosseguir para o passo 02:\n"
                "  [cyan]uv run python src/02_fetch_sample_tweets.py[/cyan]",
                border_style="green",
            )
        )
        client.close()

    except XAPIError as err:
        console.print(f"[bold red]❌ Erro retornado pela API do X:[/bold red] {err}")
        if err.status_code == 401:
            console.print(
                "[yellow]👉 Dica: Seu token pode ter sido revogado ou conter espaços extras. Gere um novo no Developer Portal.[/yellow]"
            )
        elif err.status_code == 402:
            console.print(
                Panel(
                    "[bold yellow]💳 Autenticação bem-sucedida, mas saldo zerado (HTTP 402 - credits depleted)[/bold yellow]\n\n"
                    "Seu [green]X_BEARER_TOKEN[/green] foi aceito e validado pela API do X com sucesso!\n"
                    "No entanto, como a API do X opera no modelo [bold]Pay-Per-Use[/bold], a conta precisa ter um saldo mínimo de créditos.\n\n"
                    "Para liberar o download:\n"
                    "  1. Acesse: [link=https://developer.x.com/en/portal/dashboard]https://developer.x.com/en/portal/dashboard[/link]\n"
                    "  2. Vá na seção de Faturamento/Billing e adicione créditos para ativar seu projeto.\n"
                    "  3. Assim que houver saldo, este teste passará com status 200 OK!",
                    title="Ação Necessária no Console do X",
                    border_style="yellow",
                )
            )
        elif err.status_code == 403:
            console.print(
                "[yellow]👉 Dica: Erro 403 costuma indicar que o projeto no Developer Portal não possui créditos pré-pagos ou não habilitou o endpoint v2.[/yellow]"
            )
        sys.exit(1)
    except Exception as exc:
        console.print(f"[bold red]❌ Erro inesperado na requisição:[/bold red] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
