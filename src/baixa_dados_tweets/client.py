"""Cliente HTTP para a API v2 do X/Twitter com controle de taxa e orçamento."""

import time
from typing import Any

import httpx
from rich.console import Console

from baixa_dados_tweets.config import (
    COST_PER_TWEET_READ_USD,
    settings,
)

console = Console()


class XAPIError(Exception):
    """Exceção base para erros na API do X."""

    def __init__(self, status_code: int, message: str, details: Any = None):
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.details = details


class BudgetExceededError(Exception):
    """Lançado quando o limite de orçamento estipulado pelo usuário é atingido."""

    pass


class XClient:
    """Cliente oficial para interagir com os endpoints da API v2 do X."""

    BASE_URL = "https://api.x.com/2"

    def __init__(self, bearer_token: str | None = None, max_budget_usd: float | None = None):
        self.bearer_token = bearer_token or settings.bearer_token
        # Teto de gasto desta sessão: parâmetro explícito (ex.: --max-budget) ou valor do .env
        self.max_budget_usd = max_budget_usd if max_budget_usd is not None else settings.max_budget_usd
        if not self.bearer_token or self.bearer_token == "seu_bearer_token_aqui":
            raise ValueError(
                "X_BEARER_TOKEN não configurado! "
                "Copie o arquivo .env.example para .env e preencha com seu token do Developer Portal."
            )

        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "User-Agent": "BaixaDadosTweets/1.0",
            },
            timeout=30.0,
        )

        # Estatísticas de consumo da sessão
        self.total_tweets_read = 0
        self.total_requests_made = 0
        self.last_rate_limit_info: dict[str, Any] = {}

    @property
    def estimated_cost_usd(self) -> float:
        """Cálculo do custo estimado no modelo Pay-Per-Use ($0.005 por tweet lido)."""
        return self.total_tweets_read * COST_PER_TWEET_READ_USD

    def _update_rate_limit_info(self, headers: httpx.Headers) -> None:
        """Extrai informações de rate limit dos cabeçalhos HTTP."""
        limit = headers.get("x-rate-limit-limit")
        remaining = headers.get("x-rate-limit-remaining")
        reset_ts = headers.get("x-rate-limit-reset")

        if limit is not None and remaining is not None and reset_ts is not None:
            self.last_rate_limit_info = {
                "limit": int(limit),
                "remaining": int(remaining),
                "reset_timestamp": int(reset_ts),
                "seconds_until_reset": max(0, int(reset_ts) - int(time.time())),
            }

    def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Executa requisição HTTP com verificação de erros e rate limits."""
        # Verificação preventiva de orçamento
        if self.estimated_cost_usd >= self.max_budget_usd:
            raise BudgetExceededError(
                f"Limite de orçamento atingido: US$ {self.estimated_cost_usd:.4f} >= US$ {self.max_budget_usd:.2f}"
            )

        retries = 3
        backoff = 2.0

        for attempt in range(retries):
            try:
                response = self.client.request(method, endpoint, **kwargs)
                self.total_requests_made += 1
                self._update_rate_limit_info(response.headers)

                # Sucesso
                if response.status_code == 200:
                    return response.json()

                # Rate limit (HTTP 429)
                if response.status_code == 429:
                    wait_seconds = self.last_rate_limit_info.get("seconds_until_reset", 60) + 2
                    console.print(
                        f"[yellow]⚠️ Rate limit atingido (HTTP 429). Aguardando {wait_seconds}s para reiniciar a janela...[/yellow]"
                    )
                    time.sleep(wait_seconds)
                    continue

                # Erros comuns
                error_body = response.text
                try:
                    error_json = response.json()
                except (ValueError, TypeError):
                    error_json = {"raw": error_body}

                if response.status_code == 401:
                    raise XAPIError(
                        401,
                        "Token de autenticação inválido ou não autorizado. Verifique seu X_BEARER_TOKEN.",
                        error_json,
                    )
                elif response.status_code == 402:
                    raise XAPIError(
                        402,
                        "Créditos esgotados / Pagamento necessário (402 Payment Required). "
                        "Seu token autenticou com sucesso, mas a conta no Developer Portal precisa de saldo de créditos pré-pagos.",
                        error_json,
                    )
                elif response.status_code == 403:
                    raise XAPIError(
                        403,
                        "Acesso negado (403 Forbidden). Verifique se seu plano/crédito na Developer Console está ativo.",
                        error_json,
                    )
                elif response.status_code >= 500:
                    console.print(
                        f"[yellow]Erro de servidor {response.status_code}, tentativa {attempt + 1}/{retries}...[/yellow]"
                    )
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                else:
                    raise XAPIError(response.status_code, response.reason_phrase, error_json)

            except httpx.RequestError:
                if attempt == retries - 1:
                    raise
                time.sleep(backoff)
                backoff *= 2

        raise XAPIError(500, "Falha na requisição após múltiplas tentativas.")

    def test_connection(self) -> dict[str, Any]:
        """Testa conectividade buscando dados básicos da conta pública oficial @X."""
        data = self._request("GET", "/users/by/username/X", params={"user.fields": "description,public_metrics"})
        return data

    def search_tweets(
        self,
        query: str,
        max_results: int = 10,
        next_token: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        until_id: str | None = None,
        since_id: str | None = None,
        archive: bool = False,
    ) -> dict[str, Any]:
        """
        Busca tweets via endpoint Recent Search (/2/tweets/search/recent) ou Full-Archive (/2/tweets/search/all).

        :param query: Termo de pesquisa (ex: 'python lang:pt -is:retweet')
        :param max_results: Quantidade por página (mínimo 10, máximo 100)
        :param next_token: Token de paginação retornado em meta.next_token
        :param start_time: Data/hora ISO UTC inicial
        :param end_time: Data/hora ISO UTC final
        :param until_id: Retorna tweets com ID menor (mais antigos) que este ID
        :param since_id: Retorna tweets com ID maior (mais recentes) que este ID
        :param archive: Se True, consulta o arquivo histórico completo (/2/tweets/search/all)
        """
        endpoint = "/tweets/search/all" if archive else "/tweets/search/recent"
        params: dict[str, Any] = {
            "query": query,
            "max_results": max(10, min(100, max_results)),
            "tweet.fields": "created_at,public_metrics,lang,author_id,conversation_id",
            "expansions": "author_id",
            "user.fields": "name,username,verified,public_metrics",
        }

        if next_token:
            params["next_token"] = next_token

        # O X proíbe enviar until_id/since_id junto com start_time/end_time
        if until_id and not (start_time or end_time):
            params["until_id"] = until_id
        if since_id and not (start_time or end_time):
            params["since_id"] = since_id

        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        result = self._request("GET", endpoint, params=params)

        # Incrementa contador de tweets lidos para cálculo de custo
        tweets = result.get("data", [])
        self.total_tweets_read += len(tweets)

        return result

    def search_recent_tweets(self, *args, **kwargs) -> dict[str, Any]:
        """Alias mantido para compatibilidade retroativa."""
        return self.search_tweets(*args, **kwargs)

    def close(self) -> None:
        """Fecha a conexão HTTP subjacente."""
        self.client.close()
