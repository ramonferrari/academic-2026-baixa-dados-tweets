# Baixa Dados Tweets (X / Twitter API v2)

Pipeline em Python moderno gerenciado com **uv** para download em larga escala, higienizacao, salvamento incremental e exportacao em **Apache Parquet** a partir da API oficial do X (Twitter) v2.

---

## Modelo de Cobranca e Custos da API do X (Pay-Per-Use)

A API v2 oficial do X opera sob modelo pre-pago por requisicao (*Pay-Per-Use*). Cada tweet entregue consome saldo dos seus creditos de desenvolvedor:

* **Tarifa de leitura de tweets:** **US$ 0,005 por tweet lido** (~R$ 0,029).
* **Consumo de creditos:**
  * **100 tweets:** US$ 0,50 (~R$ 2,90) - ideal para amostras e testes de schema
  * **1.000 tweets:** US$ 5,00 (~R$ 29,00)
  * **9.000 tweets:** US$ 45,00 (~R$ 261,00) - cobertura de ~7 horas de discussao global intensa
  * **30.000 tweets:** US$ 150,00 (~R$ 870,00) - estimativa de 24h completas de grande volume global

> [!IMPORTANT]
> **A API do X cobra por leitura:** O X nao armazena historico do que voce ja baixou. Se voce fizer uma busca que retorne os mesmos tweets novamente, voce sera cobrado mais uma vez. Para evitar isso, este projeto possui **continuidade inteligente com IDs e filtros de tempo (`--resume` e `--resume-latest`)**.

---

## Estrutura do Projeto

```text
baixa-dados-tweets/
├── .env.example                 # Modelo publico de variaveis de ambiente
├── .env                         # Suas chaves e saldo real (ignorado pelo git)
├── .gitignore                   # Protecao contra vazamento de chaves e dados brutos
├── pyproject.toml               # Dependencias do projeto (uv / PEP 621)
├── uv.lock                      # Lockfile deterministico do uv
├── README.md                    # Guia completo de uso e manual de parametros
├── CITATION.cff                 # Metadados de citacao formal no padrao CFF
├── data/                        # Dados gerados (ignorado pelo git)
│   ├── sample_tweets.parquet    # Amostra de teste colunar
│   └── bulk/                    # Coletas em larga escala (.parquet e .jsonl)
└── src/
    ├── 01_test_connectivity.py  # [Passo 1] Valida autenticacao, latencia e saldo
    ├── 02_fetch_sample_tweets.py# [Passo 2] Amostra rapida (10 tweets) com tabela visual
    ├── 03_bulk_download_tweets.py# [Passo 3] Coletor em lote com paginacao e resume
    └── baixa_dados_tweets/      # Modulos reutilizaveis
        ├── client.py            # Cliente HTTP com retries, rate limits e limite financeiro
        ├── config.py            # Settings (Pydantic), custos e Query Padrao
        ├── storage.py           # Normalizacao, streaming .jsonl e Parquet desduplicado
        └── topics.py            # Mapeamento multilingue de idiomas
```

---

## Instalacao Rapida

1. Certifique-se de ter o [uv](https://docs.astral.sh/uv/) instalado:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. Clone o repositorio e configure as credenciais:
   ```bash
   cp .env.example .env
   ```
3. Abra o `.env` e insira seu `X_BEARER_TOKEN` obtido no [X Developer Portal](https://developer.x.com/en/portal/dashboard).

---

## Como Pesquisar Qualquer Outro Assunto (Alem de IA)

O projeto vem calibrado por padrao para coletar tweets sobre Inteligencia Artificial, mas voce pode usalo para coletar **absolutamente qualquer tema** (futebol, politica, economia, eventos, marcas, entretenimento, saude, etc.).

Para coletar outro assunto, voce so precisa de dois passos simples:

### Passo A: Teste com 10 Tweets Primeiro (Sem Gastar Creditos a Toa)
Antes de baixar milhares de tweets e gastar saldo, teste sua query no script `02` para ver na tela se o conteudo retornado e exatamente o que voce espera:

```bash
uv run python src/02_fetch_sample_tweets.py --query "(bitcoin OR btc OR cripto) lang:pt -is:retweet" --count 10
```

Se os tweets exibidos no terminal fizerem sentido, va para o Passo B.

### Passo B: Fazer a Coleta em Larga Escala com Nome Customizado
Passe a sua `--query`, um nome de arquivo via `--output-name` (para nao misturar com outras coletas) e a quantidade desejada via `--limit`:

```bash
uv run python src/03_bulk_download_tweets.py \
  --query "(bitcoin OR btc OR cripto) lang:pt -is:retweet" \
  --output-name "tweets_bitcoin_pt" \
  --limit 500 \
  --max-budget 2.50
```

Isso salvara automaticamente os arquivos:
* `data/bulk/tweets_bitcoin_pt.jsonl`
* `data/bulk/tweets_bitcoin_pt.parquet`

---

### Exemplos Prontos de Queries para Outros Nichos

#### 1. Economia e Mercado Financeiro (em Portugues)
```bash
uv run python src/03_bulk_download_tweets.py \
  --query "(selic OR ipca OR inflacao OR 'banco central') lang:pt -is:retweet" \
  --output-name "tweets_economia_brasil" \
  --limit 1000
```

#### 2. Futebol e Esportes
```bash
uv run python src/03_bulk_download_tweets.py \
  --query "(brasileirao OR 'copa do brasil' OR libertadores) lang:pt -is:retweet" \
  --output-name "tweets_futebol_br" \
  --limit 1000
```

#### 3. Mudancas Climaticas e Sustentabilidade (Multilingue)
```bash
uv run python src/03_bulk_download_tweets.py \
  --query "('mudancas climaticas' OR 'climate change' OR 'cambio climatico') -is:retweet" \
  --output-name "tweets_clima_global" \
  --limit 2000
```

#### 4. Monitoramento de Marca ou Produto (Ex: Nubank)
```bash
uv run python src/03_bulk_download_tweets.py \
  --query "(nubank OR @nubank) lang:pt -is:retweet" \
  --output-name "tweets_nubank" \
  --limit 500
```

#### 5. Cinema e Cultura Pop (Ex: Oscar)
```bash
uv run python src/03_bulk_download_tweets.py \
  --query "(oscar OR #oscar OR 'academy awards') -is:retweet" \
  --output-name "tweets_oscar" \
  --limit 1500
```

---

## Guia de Construcao de Queries no X (Sintaxe Oficial v2)

Para evitar gastar creditos com tweets irrelevantes, entenda os operadores que voce pode combinar dentro do `--query`:

| Operador | Como Usar | Exemplo | O que faz |
| :--- | :--- | :--- | :--- |
| **Palavras simples** | `termo1 termo2` | `vacina covid` | Exige que ambos os termos estejam presentes (AND implicito). |
| **Alternativas (OR)** | `(termo1 OR termo2)` | `(petrobras OR petr4)` | Traz postagens que contenham ao menos um dos termos. |
| **Expressao exata** | `"termo composto"` | `"inteligencia artificial"` | Busca exatamente a ordem e as palavras entre aspas. |
| **Filtro de Idioma** | `lang:XX` | `lang:pt`, `lang:es`, `lang:en` | Filtra pelo idioma detectado oficialmente pelo X. |
| **Banir Retweets** | `-is:retweet` | `(...) -is:retweet` | **Obrigatorio!** Evita pagar repetido por retweets de um mesmo texto. |
| **Banir Respostas** | `-is:reply` | `(...) -is:reply` | Retorna apenas postagens originais (ignora replies de conversas). |
| **Hashtags** | `#Hashtag` | `#DataScience` | Encontra postagens contendo a hashtag especifica. |
| **Menções** | `@usuario` | `@XDevelopers` | Postagens que mencionam a conta indicada. |
| **Engajamento Minimo**| `min_faves:N` | `min_faves:10` | Apenas tweets com no minimo 10 curtidas (elimina bots e contas vazias). |

### Tres Regras Fundamentais para Nao Errar:
1. **O X e Case-Insensitive:** A busca nao diferencia maiusculas de minusculas. `AI` e igual a `ai` ou `ai`. Se for pesquisar siglas curtas, especifique o idioma `(AI lang:en)` ou use hashtag `#AI`.
2. **Precedencia Booleana:** O operador `AND` tem prioridade sobre o `OR`. Sempre use parenteses ao agrupar termos alternativos antes de aplicar filtros negativos:
   * **Errado:** `termo1 OR termo2 -is:retweet` (o filtro so se aplica ao termo2).
   * **Correto:** `(termo1 OR termo2) -is:retweet` (o filtro se aplica a todos os termos).
3. **Teto de 512 Caracteres:** A string inteira do `--query` nao pode ultrapassar 512 caracteres no endpoint Recent Search.

---

## Manual de Parametros do Coletor (`03_bulk_download_tweets.py`)

| Parametro | Padrao | O que faz / Para que serve |
| :--- | :---: | :--- |
| **`--query`** | *Query IA* | Termo ou query personalizada com sintaxe da API v2. |
| **`--limit`** | `9000` | Quantidade maxima de tweets a baixar nesta execucao. |
| **`--output-name`** | `tweets_ia_global` | Nome base dos arquivos gerados dentro de `data/bulk/`. |
| **`--resume`** | `False` | **Continua voltando no tempo** a partir do tweet mais antigo salvo na base, **sem pagar nada duplicado**. |
| **`--resume-latest`**| `False` | **Busca apenas tweets novos** publicados apos o tweet mais recente ja salvo. |
| **`--max-budget`** | `45.0` | Trava de seguranca financeira em USD. A coleta aborta se atingir esse valor. |
| **`--since-hours`** | `None` | Coleta tweets publicados apenas nas ultimas N horas (ex: `--since-hours 12`). |
| **`--start-time`** | `None` | Data/hora UTC inicial no formato ISO (ex: `2026-10-17T00:00:00Z`). |
| **`--end-time`** | `None` | Data/hora UTC final no formato ISO (ex: `2026-10-17T12:19:54Z`). |
| **`--batch-size`** | `100` | Quantidade de tweets por requisicao (10 a 100). Mantenha em 100 para economia maxima de chamadas. |

---

## Receitas Prontas para o Dia a Dia

### 1. Continuar Coleta Voltando no Tempo (Sem Repetir Tweet Ja Pago)
Use quando voce alocou mais creditos e quer continuar baixando tweets para tras sem pagar nada que ja tenha sido baixado:
```bash
uv run python src/03_bulk_download_tweets.py --resume
```
> O script localiza o ID do tweet mais antigo na base existente e solicita a API do X apenas tweets anteriores a ele (`until_id`). Zero sobreposicao.

### 2. Coletar Novos Tweets Publicados Recentemente
Para atualizar sua base com o que acabou de sair nas ultimas horas:
```bash
uv run python src/03_bulk_download_tweets.py --resume-latest
```

### 3. Coleta com Orcamento Limitado (Ex: Gastar no Maximo US$ 2,50)
Para fazer um estudo pontual de ate 500 tweets com trava estrita de 2,50 dolares:
```bash
uv run python src/03_bulk_download_tweets.py --limit 500 --max-budget 2.50
```

### 4. Coletar Apenas as Ultimas 4 Horas
```bash
uv run python src/03_bulk_download_tweets.py --since-hours 4 --limit 300
```

### 5. Delimitar uma Janela Estrita de Horario UTC
```bash
uv run python src/03_bulk_download_tweets.py \
  --start-time "2026-10-17T00:00:00Z" \
  --end-time "2026-10-17T12:00:00Z" \
  --limit 5000
```

---

## Como Abrir e Analisar a Base Salva (.parquet)

Os dados sao salvos em formato colunar comprimido `.parquet` dentro de `data/bulk/`. O arquivo contem o campo nativo de idioma (`lang`), dados do autor (`author_username`, `author_verified`) e engajamento (`like_count`, `retweet_count`, `reply_count`).

### Com Polars (Nativo e Ultra-Rapido)
```python
import polars as pl

# Leitura instantanea do Parquet
df = pl.read_parquet("data/bulk/tweets_ia_global.parquet")

# Filtrar apenas postagens em Portugues
df_pt = df.filter(pl.col("lang") == "pt")
print(f"Total em portugues: {len(df_pt)}")

# Ver distribuicao dos 10 maiores idiomas
print(df["lang"].value_counts(sort=True).head(10))

# Filtrar tweets mais curtidos
virais = df.filter(pl.col("like_count") > 500).select(["author_username", "like_count", "text"])
print(virais)
```

### Com DuckDB (via SQL)
```python
import duckdb

# Top 10 idiomas mais frequentes na base
duckdb.sql("""
    SELECT lang, COUNT(*) as total, AVG(like_count) as media_curtidas
    FROM 'data/bulk/*.parquet'
    GROUP BY lang
    ORDER BY total DESC
    LIMIT 10;
""").show()
```

---

## Seguranca de Credenciais e Repositorio Publico

Este projeto esta pronto e seguro para publicacao em repositorios publicos:
* O arquivo `.env` com suas chaves reais e a pasta `data/` com os dados baixados estao no `.gitignore`.
* Nenhum token ou dado confidencial e enviado ao Git.
* O arquivo `.env.example` fornece o gabarito sem credenciais para outros usuarios.

---

## Como Citar este Projeto

Se voce utilizar este pipeline ou os metodos de coleta em sua pesquisa, artigo ou projeto, por favor cite como:

```bibtex
@software{ferrari2026baixadados,
  author = {Ferrari, Ramon},
  title = {Baixa Dados Tweets: Pipeline de Coleta e Analise em Larga Escala via API v2 do X},
  year = {2026},
  url = {https://github.com/ramonferrari/baixa-dados-tweets},
  license = {Apache-2.0}
}
```

Voce tambem pode utilizar o botao oficial **"Cite this repository"** na barra lateral direita do GitHub gerado pelo arquivo [CITATION.cff](CITATION.cff).
