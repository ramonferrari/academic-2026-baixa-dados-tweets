"""Configurações e variáveis de ambiente do projeto."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Carrega .env da raiz do projeto
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Custos de referência oficiais da API v2 do X (Pay-Per-Use)
# https://docs.x.com / Developer Console Rate Card
COST_PER_TWEET_READ_USD = 0.005  # $0.005 por tweet lido (US$ 5,00 por 1.000 tweets)
COST_PER_USER_READ_USD = 0.010  # $0.010 por perfil de usuário lido
DEFAULT_USD_TO_BRL = 5.80  # Taxa de câmbio estimada para referência de orçamento

# Query Oficial Padrão do Projeto: 15 Maiores Idiomas do X + Modelos + Siglas Globais (460 chars)
DEFAULT_AI_QUERY = (
    "(ChatGPT OR Claude OR Gemini OR GPT OR LLM OR GenAI OR (AI lang:en) OR #AI OR #IA OR #KI OR "
    '"artificial intelligence" OR "inteligência artificial" OR '
    '"inteligencia artificial" OR "intelligence artificielle" OR '
    '"künstliche intelligenz" OR "intelligenza artificiale" OR '
    '"人工知能" OR "人工智能" OR "искусственный интеллект" OR '
    '"الذكاء الاصطناعي" OR "인공지능" OR "आर्टिफिशियल इंटेलिजेंस" OR '
    '"yapay zeka" OR "kunstmatige intelligentie" OR "sztuczna inteligencja") -is:retweet'
)


class Settings(BaseModel):
    """Configurações de conexão e limites de segurança."""

    bearer_token: str = Field(default_factory=lambda: os.getenv("X_BEARER_TOKEN", "").strip())
    api_key: str = Field(default_factory=lambda: os.getenv("X_API_KEY", "").strip())
    api_secret_key: str = Field(default_factory=lambda: os.getenv("X_API_SECRET_KEY", "").strip())
    access_token: str = Field(default_factory=lambda: os.getenv("X_ACCESS_TOKEN", "").strip())
    access_token_secret: str = Field(default_factory=lambda: os.getenv("X_ACCESS_TOKEN_SECRET", "").strip())

    # Trava de segurança para evitar gastos inesperados
    max_budget_usd: float = Field(default_factory=lambda: float(os.getenv("MAX_BUDGET_USD", "5.00")))
    max_tweets_limit: int = Field(default_factory=lambda: int(os.getenv("MAX_TWEETS_LIMIT", "1000")))

    # Diretórios
    data_dir: Path = Field(default=PROJECT_ROOT / "data")

    @property
    def has_bearer_token(self) -> bool:
        return bool(self.bearer_token and self.bearer_token != "seu_bearer_token_aqui")


settings = Settings()
