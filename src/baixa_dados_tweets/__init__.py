"""Pacote baixa_dados_tweets para coleta estruturada da API v2 do X/Twitter."""

from baixa_dados_tweets.client import BudgetExceededError, XAPIError, XClient
from baixa_dados_tweets.config import COST_PER_TWEET_READ_USD, settings
from baixa_dados_tweets.storage import (
    append_jsonl,
    ensure_data_directory,
    normalize_tweet_record,
    save_json,
)

__all__ = [
    "COST_PER_TWEET_READ_USD",
    "BudgetExceededError",
    "XAPIError",
    "XClient",
    "append_jsonl",
    "ensure_data_directory",
    "normalize_tweet_record",
    "save_json",
    "settings",
]
