# Contexto do projeto para assistentes de IA (Gemini, Claude Code e similares)

Este arquivo é lido automaticamente por agentes de código (Gemini CLI / Antigravity leem `GEMINI.md`; o Claude Code lê `CLAUDE.md`, que aponta para cá). Ele existe para que **você, que baixou este repositório, peça ajuda ao seu assistente** para adaptá-lo ao seu caso (outro assunto, outros campos, outro formato, outro orçamento) sem que ele precise redescobrir como o projeto funciona.

Se você é o agente: leia este arquivo inteiro antes de editar qualquer coisa, e responda no idioma do usuário.

---

## 1. O que o projeto faz

Coleta posts públicos do X (Twitter) pela **API oficial v2**, em escala, com:

- paginação automática (`next_token`);
- trava de orçamento e estimativa de custo (modelo *pay-per-use*, US$ 0,005 por post retornado);
- continuidade sem pagar duas vezes (`--resume`, `--resume-latest`);
- gravação incremental em `.jsonl` e consolidação final em **Apache Parquet** desduplicado por `id`;
- escolha automática entre os endpoints Recent Search (7 dias) e Full-Archive (qualquer data).

O padrão do repositório é coletar posts sobre Inteligência Artificial em 15 idiomas (`DEFAULT_AI_QUERY` em `config.py`), mas o assunto é só uma query: **trocar de assunto não exige mudar código** (veja a seção 5).

## 2. Regras para o agente (leia antes de agir)

**Dinheiro e credenciais**

1. **Cada execução do script 02 ou 03 gasta créditos reais do usuário.** Antes de rodar qualquer coleta, diga o custo máximo (`limite x US$ 0,005`) e **peça confirmação**. Para testar uma alteração, use `--limit 10` (cerca de US$ 0,05) ou o script 02.
2. **Nunca leia, imprima, copie ou comite o `.env`** nem o `X_BEARER_TOKEN`. Não cole o token em respostas, logs, mensagens de commit ou arquivos. Se precisar saber se o token está configurado, rode `uv run python src/01_test_connectivity.py` (ele só mostra o token mascarado).
3. Não aumente `MAX_BUDGET_USD` / `MAX_TWEETS_LIMIT` nem remova a trava de orçamento sem o usuário pedir explicitamente.

**Dados**

4. A pasta `data/` e os arquivos `*.parquet` / `*.jsonl` estão no `.gitignore` de propósito: os Termos do Desenvolvedor do X restringem a redistribuição de posts. **Nunca os comite nem os publique**, e não os envie a serviços externos sem o usuário saber.
5. Não apague nem sobrescreva a base em `data/bulk/` sem confirmar; refazer a coleta custa dinheiro. Faça cópia antes de qualquer transformação destrutiva.

**Código**

6. Análise de dados e dataframes: use **Polars** (`import polars as pl`) e, se necessário, DuckDB. Esta é a convenção do projeto (Polars já é dependência; Pandas não é). Só use Pandas se o usuário pedir explicitamente.
7. Ao terminar uma alteração, rode `uv run ruff check --fix && uv run ruff format` e confirme que passou.
8. Mantenha o estilo: Python 3.12, `X | None` em vez de `Optional[X]`, docstrings e comentários em português, saída de terminal com `rich`, HTTP com `httpx`. Linha de até 120 caracteres.
9. Não use Unicode decorativo/emojis em documentação do repositório.

## 3. Mapa do código

```text
src/
├── 01_test_connectivity.py     # Valida token, latência e saldo (HTTP 200/401/402/403)
├── 02_fetch_sample_tweets.py   # Baixa 10-100 posts e mostra em tabela; salva em data/sample_tweets.*
├── 03_bulk_download_tweets.py  # Coletor principal: argparse, resume, janelas, progresso, Parquet
└── baixa_dados_tweets/
    ├── client.py   # XClient: _request (retries, 429, erros 4xx/5xx, trava de orçamento),
    │               # search_tweets(...) escolhe /search/recent ou /search/all
    ├── config.py   # Settings (lê .env), COST_PER_TWEET_READ_USD, DEFAULT_USD_TO_BRL, DEFAULT_AI_QUERY
    ├── storage.py  # format_iso_time, normalize_tweet_record, append_jsonl, jsonl_to_parquet, save_json
    └── topics.py   # Catálogo auxiliar de termos por idioma; NÃO é usado pelos scripts atuais
```

Fluxo de dados do script 03:

```text
args -> XClient.search_tweets() -> resposta JSON
     -> normalize_tweet_record() (uma linha por post)
     -> append_jsonl()  (grava a cada página)
     -> ao final: jsonl_to_parquet() (desduplica por id) + meta_*.json da execução
```

Saída em `data/bulk/`: `<output-name>.jsonl`, `<output-name>.parquet`, `meta_*.json`.
Colunas do Parquet: `id`, `created_at` (texto ISO, UTC), `text`, `lang`, `author_id`, `author_username`, `author_name`, `author_verified`, `retweet_count`, `reply_count`, `like_count`, `quote_count`, `raw` (JSON original do post em texto).

## 4. Fatos da API do X que o agente precisa respeitar

- **Autenticação:** `Authorization: Bearer <token>`; base `https://api.x.com/2`.
- **Endpoints de busca:**
  - `/tweets/search/recent`: últimos 7 dias; query de até **512** caracteres.
  - `/tweets/search/all` (Full-Archive): qualquer data; query de até 1.024 caracteres. Depende do nível de acesso da conta (sem acesso: HTTP 403).
- **`until_id` / `since_id` NÃO podem ser enviados junto com `start_time` / `end_time`** (HTTP 400). O `search_tweets` e o `--resume` já tratam isso: com janela de tempo, o ponto de retomada vira `end_time`. Não quebre essa regra.
- **Ordem:** a busca devolve do mais novo para o mais antigo. Por isso, ao coletar um intervalo maior que o `--limit`, você obtém o trecho mais recente e perde o resto.
- **Erros:** 401 = token inválido; **402 = conta sem créditos** (cadastrar cartão não basta, é preciso comprar créditos no projeto do token); 403 = sem acesso ao endpoint; 429 = limite de requisições (o cliente espera e repete).
- **Preço:** US$ 0,005 por post retornado. Posts relidos no mesmo dia UTC são cobrados uma vez (garantia "soft"); em dias diferentes são cobrados de novo. Confira valores atuais no Developer Console.
- **Sintaxe de query:**
  - a busca ignora maiúsculas/minúsculas e acentos (`IA` casa com "ia fazer", `AI` com "aí");
  - `AND` tem precedência sobre `OR`: escreva `(a OR b) -is:retweet`;
  - frases exatas só com **aspas duplas**;
  - `lang:XX`, `-is:retweet`, `-is:reply`, `#hashtag`, `@conta` existem; **`min_faves:` NÃO existe na API v2**.
- **Campo `lang`:** vem do classificador do X (BCP 47). `und` = indeterminado; `qme`/`zxx` = sem texto linguístico.
- **Métricas** (`like_count` etc.) são o retrato do momento da coleta.

## 5. Como atender pedidos comuns do usuário

### Trocar o assunto da coleta
Não mexa no código: use `--query` e um `--output-name` próprio (para não misturar bases). Para mudar o **padrão**, edite `DEFAULT_AI_QUERY` em `config.py`.
1. Monte a query respeitando a seção 4 (parênteses, aspas duplas, `-is:retweet`).
2. Confirme `len(query) <= 512`.
3. Valide com o script 02 (`--count 10`) e mostre ao usuário os posts retornados; ajuste se houver ruído.
4. Só então proponha a coleta em escala, informando o custo máximo.

Exemplo: `uv run python src/02_fetch_sample_tweets.py --query '(selic OR "banco central") lang:pt -is:retweet' --count 10`

### Coletar apenas certos idiomas, ou excluir respostas
Adicione `lang:xx` (um por vez dentro de parênteses com `OR`) e/ou `-is:reply` à query. Lembre que `lang:` filtra pelo idioma detectado pelo X.

### Salvar campos adicionais (hashtags, post respondido, local, fonte...)
1. Em `client.py`, no dicionário `params` de `search_tweets`, acrescente o campo em `tweet.fields` (ex.: `entities`, `referenced_tweets`, `in_reply_to_user_id`, `geo`, `possibly_sensitive`, `source`) e, se for dado do autor, em `user.fields`.
2. Em `storage.py`, `normalize_tweet_record`, crie a nova coluna.
3. **Armadilhas:** (a) o `raw` só contém os campos que foram pedidos à API, então posts já baixados **não** ganham o campo novo sem nova coleta (e novo pagamento); (b) `jsonl_to_parquet` usa `pa.Table.from_pylist`, que **infere as colunas pelo primeiro registro**: se o `.jsonl` antigo não tem a coluna nova, ela é **descartada silenciosamente** do Parquet. Ao adicionar colunas, monte o esquema pela união das chaves de todos os registros (ou use outro `--output-name`) e verifique `df.columns` depois. `conversation_id` hoje existe apenas dentro de `raw`.

### Mudar orçamento e limites
Use `--limit` e `--max-budget` por execução, ou `MAX_TWEETS_LIMIT` / `MAX_BUDGET_USD` no `.env`. A trava usa o custo **estimado localmente** (posts recebidos x `COST_PER_TWEET_READ_USD` em `config.py`); se o X mudar o preço, atualize essa constante. O saldo real só é visto no Developer Console.

### Pré-processar o texto (limpar links, menções, etc.)
Faça sobre o Parquet com Polars, em um script novo (por exemplo `src/04_limpar_texto.py`), sem alterar a base original:

```python
import polars as pl

df = pl.read_parquet("data/bulk/tweets_ia_global.parquet")
df = df.with_columns(
    pl.col("text")
    .str.replace_all(r"https?://\S+", "")  # links t.co
    .str.replace_all(r"@\w+", "")  # menções
    .str.replace_all(r"\s+", " ")
    .str.strip_chars()
    .alias("texto_limpo")
)
df.write_parquet("data/processed/tweets_limpos.parquet")
```

### Segregar por idioma
```python
for (lang,), parte in df.group_by("lang"):
    parte.write_parquet(f"data/processed/lang_{lang}.parquet")
```

### Conferir a cobertura temporal (detectar buracos)
```python
df = df.with_columns(pl.col("created_at").str.to_datetime("%Y-%m-%dT%H:%M:%S%.3fZ", time_zone="UTC"))
print(df.group_by(pl.col("created_at").dt.truncate("1h").alias("hora_utc")).len().sort("hora_utc"))
```

### Usar outro formato de saída, banco de dados ou DuckDB
Trabalhe a partir do Parquet. Para SQL: `uv add duckdb` e `duckdb.sql("SELECT ... FROM 'data/bulk/x.parquet'")`. Evite alterar `append_jsonl`/`jsonl_to_parquet` se não for necessário: o `--resume` depende do Parquet para saber onde parou.

### Coletar um período específico ou continuar uma coleta
Use `--start-time` / `--end-time` (UTC, ISO 8601), `--since-hours`, `--resume` (para trás) ou `--resume-latest` (para frente). Veja o README para exemplos e para o aviso sobre buracos.

## 6. Armadilhas conhecidas

1. **Custo é estimativa local.** A fatura real é a do Developer Console.
2. **`--resume-latest` pode deixar um buraco** se houver mais posts novos do que o `--limit` (a busca começa pelo mais novo).
3. **Reutilizar `--output-name` com outra query mistura bases**, e o `--resume` passa a usar os limites da base misturada. Use um nome por assunto.
4. **`created_at` é texto**, não data: converta com `str.to_datetime` (formato e fuso acima) antes de agrupar por tempo.
5. **Novas colunas podem sumir do Parquet** (veja a seção 5, "Salvar campos adicionais").
6. **`topics.py` não é usado** pelos scripts e traz termos de uma versão anterior (mais idiomas). Não o trate como fonte da query atual: a fonte é `DEFAULT_AI_QUERY`.
7. **Full-Archive depende do nível de acesso da conta.** Se der 403, não é bug do código.

## 7. Como validar uma alteração

```bash
uv run ruff check --fix && uv run ruff format          # lint e formatação
uv run python src/03_bulk_download_tweets.py --help     # a CLI ainda sobe?
uv run python src/01_test_connectivity.py               # credenciais e saldo (não gasta créditos de posts)
uv run python src/02_fetch_sample_tweets.py --count 10  # custa ~US$ 0,05; confirme com o usuário
```

Para testar a trava de orçamento **sem chamar a API** (custo zero):

```python
import sys

sys.path.insert(0, "src")
from baixa_dados_tweets.client import XClient, BudgetExceededError

c = XClient(max_budget_usd=0.05)
c.total_tweets_read = 10  # simula US$ 0,05 gastos
try:
    c._request("GET", "/tweets/search/recent", params={})
except BudgetExceededError:
    print("trava OK")
```

## 8. Extensões naturais

Análise de sentimento, modelagem de tópicos (por exemplo BERTopic com embeddings multilíngues), comparação entre idiomas ou entre marcas citadas, séries temporais por hora. Sempre a partir do Parquet, em scripts separados, e sem comitar dados.
