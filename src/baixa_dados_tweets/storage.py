"""Utilitários de armazenamento para dados de tweets baixados (JSON, JSONL e Parquet)."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


def format_iso_time(val: str | None = None, since_hours: float | None = None) -> str | None:
    """
    Formata datas para o padrão rigoroso ISO 8601 UTC exigido pela API v2 do X.
    Exemplos: '2026-10-17' -> '2026-10-17T00:00:00Z'
    ou --since-hours 24 -> calcula a data/hora exata de 24 horas atrás.
    """
    if since_hours is not None and since_hours > 0:
        dt = datetime.now(UTC) - timedelta(hours=since_hours)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    if not val:
        return None
    val = val.strip()
    if len(val) == 10 and val.count("-") == 2:
        return f"{val}T00:00:00Z"
    if val.endswith("Z"):
        return val
    return val + "Z" if "T" in val else f"{val}T00:00:00Z"


def ensure_data_directory(subfolder: str = "") -> Path:
    """Garante que o diretório de dados exista."""
    base_dir = Path(__file__).resolve().parent.parent.parent / "data"
    target_dir = base_dir / subfolder if subfolder else base_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def save_json(data: Any, filepath: Path) -> Path:
    """Salva dados em formato JSON formatado."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


def append_jsonl(records: list[dict[str, Any]], filepath: Path) -> int:
    """Adiciona múltiplos registros a um arquivo .jsonl (JSON Lines)."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        f.writelines(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    return len(records)


def normalize_tweet_record(
    tweet: dict[str, Any],
    users_map: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Normaliza um objeto de tweet da API v2 para formato tabular simples."""
    users_map = users_map or {}
    author_id = tweet.get("author_id", "")
    author_info = users_map.get(author_id, {})
    metrics = tweet.get("public_metrics", {})

    return {
        "id": str(tweet.get("id", "")),
        "created_at": tweet.get("created_at", ""),
        "text": tweet.get("text", ""),
        "lang": tweet.get("lang", ""),
        "author_id": str(author_id),
        "author_username": author_info.get("username", ""),
        "author_name": author_info.get("name", ""),
        "author_verified": author_info.get("verified", False),
        "retweet_count": int(metrics.get("retweet_count", 0)),
        "reply_count": int(metrics.get("reply_count", 0)),
        "like_count": int(metrics.get("like_count", 0)),
        "quote_count": int(metrics.get("quote_count", 0)),
        "raw": tweet,
    }


def jsonl_to_parquet(jsonl_path: Path, parquet_path: Path | None = None) -> Path | None:
    """
    Converte um arquivo JSONL em Apache Parquet colunar e comprimido (Snappy).
    Desduplica registros pelo campo 'id' para garantir unicidade.
    """
    if parquet_path is None:
        parquet_path = jsonl_path.with_suffix(".parquet")

    if not jsonl_path.exists():
        return None

    records = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                row = json.loads(line)
                # Serializa o dict 'raw' em string JSON para não conflitar com schema colunar
                if "raw" in row and isinstance(row["raw"], (dict, list)):
                    row["raw"] = json.dumps(row["raw"], ensure_ascii=False)
                records.append(row)

    if not records:
        return None

    # Desduplicação por ID
    seen_ids = set()
    unique_records = []
    for row in records:
        t_id = row.get("id")
        if t_id and t_id in seen_ids:
            continue
        if t_id:
            seen_ids.add(t_id)
        unique_records.append(row)

    table = pa.Table.from_pylist(unique_records)
    pq.write_table(table, parquet_path, compression="snappy")
    return parquet_path
