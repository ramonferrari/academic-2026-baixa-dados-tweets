# Baixa Dados Tweets (X / Twitter API v2)

Pipeline em Python, gerenciado com [uv](https://docs.astral.sh/uv/), para baixar posts públicos do X (Twitter) pela **API oficial v2**, com paginação automática, travas de custo, continuidade sem pagar duas vezes e exportação em **Apache Parquet**.

O repositório foi construído para uma coleta sobre Inteligência Artificial em múltiplos idiomas, mas funciona para **qualquer assunto**: basta trocar a query (veja [Como pesquisar outro assunto](#como-pesquisar-outro-assunto)).

> Este repositório contém **apenas código**. Os dados coletados não são versionados nem distribuídos aqui (veja [Dados e Termos do X](#dados-e-termos-do-x)).

## Sumário

1. [Custos da API](#custos-da-api)
2. [Requisitos e instalação](#requisitos-e-instalação)
3. [Guia rápido (3 passos)](#guia-rápido-3-passos)
4. [O que é salvo e em que formato](#o-que-é-salvo-e-em-que-formato)
5. [Como pesquisar outro assunto](#como-pesquisar-outro-assunto)
6. [Sintaxe de queries do X](#sintaxe-de-queries-do-x)
7. [Manual de parâmetros](#manual-de-parâmetros-do-coletor-03_bulk_download_tweetspy)
8. [Receitas de uso](#receitas-de-uso)
9. [Analisando os dados](#analisando-os-dados)
10. [Limitações e cuidados metodológicos](#limitações-e-cuidados-metodológicos)
11. [Dados e Termos do X](#dados-e-termos-do-x)
12. [Adaptando com um assistente de IA](#adaptando-com-um-assistente-de-ia)
13. [Estrutura do projeto](#estrutura-do-projeto)
14. [Qualidade de código](#qualidade-de-código)
15. [Licença e como citar](#licença-e-como-citar)

---

## Custos da API

A API v2 do X usa cobrança **pré-paga por uso** (*pay-per-use*): você compra créditos no Developer Console e cada post retornado consome saldo.

* **Leitura de posts:** US$ 0,005 por post retornado (~R$ 0,03).
* **Deduplicação diária:** segundo a documentação de preços do X, o mesmo post lido mais de uma vez **dentro do mesmo dia UTC** é cobrado uma única vez (garantia "soft"). Em **dias UTC diferentes** a leitura é cobrada de novo. Não conte com isso para economizar: use `--resume` / `--resume-latest`.
* **Preços e regras mudam.** Confirme os valores vigentes no Developer Console antes de planejar um orçamento.

| Posts baixados | Custo estimado (USD) |
| ---: | ---: |
| 100 | 0,50 |
| 1.000 | 5,00 |
| 10.000 | 50,00 |
| 25.000 | 125,00 |

**Coleta de referência do autor:** 24 horas completas de 17/10/2026 (UTC) sobre IA, em 15 idiomas, sem retweets, resultaram em **25.070 posts**, o que custa cerca de **US$ 125**. Use isso como régua para dimensionar o seu estudo.

> [!IMPORTANT]
> **O custo exibido pelo script é uma estimativa local** (posts recebidos x US$ 0,005). O saldo real e a fatura valem os do Developer Console. Confira lá após cada coleta grande.

> [!IMPORTANT]
> **Sem continuidade você paga duas vezes.** A API é *stateless*: se uma nova busca devolver posts que você já baixou, eles são cobrados de novo (exceto pela deduplicação diária acima). Por isso o coletor guarda o ID do post mais antigo e do mais recente da sua base e permite continuar exatamente de onde parou.

---

## Requisitos e instalação

### Requisitos

* Python 3.12 ou superior (gerenciado automaticamente pelo `uv`).
* [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado.
* Uma conta no [X Developer Console](https://developer.x.com/en/portal/dashboard) com **créditos comprados** e um **Bearer Token**.

### 1. Obtenha as credenciais

1. Acesse o [X Developer Console](https://developer.x.com/en/portal/dashboard) e crie um **Project** com um **App**.
2. Em **Billing/Faturamento**, adicione um cartão **e compre créditos**. Apenas cadastrar o cartão não basta: com saldo zero a API responde `HTTP 402 (Payment Required)`.
3. Em **Keys and Tokens** do App, gere o **Bearer Token**. Ele é suficiente para ler posts públicos.
4. Atenção: os créditos precisam estar no **mesmo projeto** ao qual o token pertence. Após a compra, pode levar alguns minutos para o saldo ser reconhecido.

### 2. Clone e instale

```bash
git clone https://github.com/ramonferrari/academic-2026-baixa-dados-tweets.git
cd academic-2026-baixa-dados-tweets
uv sync
```

### 3. Configure o `.env`

```bash
cp .env.example .env
```

Abra o `.env` e preencha:

| Variável | Para que serve | Exemplo |
| :--- | :--- | :--- |
| `X_BEARER_TOKEN` | Seu token de acesso. **Nunca** o publique. | `AAAA...` |
| `MAX_BUDGET_USD` | Teto de gasto por execução (trava de segurança). | `50.00` |
| `MAX_TWEETS_LIMIT` | Quantidade máxima padrão de posts por execução. | `10000` |

O arquivo `.env` está no `.gitignore` e não é versionado.

---

## Guia rápido (3 passos)

Os scripts são numerados na ordem em que você deve usá-los. Sem parâmetros, usam a query padrão do projeto (IA em 15 idiomas, 460 caracteres, sem retweets).

### Passo 1: testar credenciais e saldo

```bash
uv run python src/01_test_connectivity.py
```

Deve terminar com `200 OK (Conectado!)`. Se aparecer `HTTP 402`, a conta está sem créditos; se aparecer `HTTP 401`, o token está errado.

### Passo 2: baixar uma amostra de 10 posts

```bash
uv run python src/02_fetch_sample_tweets.py
```

Imprime uma tabela no terminal para você **conferir se a query traz o que você quer**, antes de gastar mais. Custo: cerca de US$ 0,05. Salva em `data/sample_tweets.*`.

### Passo 3: coleta em larga escala

```bash
uv run python src/03_bulk_download_tweets.py
```

Começa pelos posts mais recentes e vai voltando no tempo, em páginas de 100, até atingir `--limit` posts, o teto de orçamento, ou o fim dos resultados. Cada página é gravada em `.jsonl` assim que chega (se você interromper com `Ctrl+C`, nada se perde) e, ao final, o `.parquet` é regerado **sem duplicatas**.

---

## O que é salvo e em que formato

Tudo é gravado em `data/` (ignorado pelo git). Em `data/bulk/`, para um `--output-name` (padrão `tweets_ia_global`):

| Arquivo | Conteúdo |
| :--- | :--- |
| `<nome>.jsonl` | Um post por linha, gravado de forma incremental. Acumula entre execuções. |
| `<nome>.parquet` | Mesma base consolidada e **desduplicada por `id`**, comprimida (Snappy). É o arquivo para análise. |
| `meta_<query>_<data>.json` | Um por execução: query usada, endpoint, filtros de tempo, custo estimado, intervalo de datas coletado, `until_id`/`since_id`. Serve como registro de reprodutibilidade. |

### Colunas do Parquet

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `id` | texto | ID do post (Snowflake). Guardado como texto para não perder precisão. |
| `created_at` | texto | Data/hora de publicação em ISO 8601, **UTC** (ex.: `2026-10-17T12:19:55.000Z`). |
| `text` | texto | Texto do post. |
| `lang` | texto | Idioma detectado **pelo X** (código BCP 47: `en`, `pt`, `ja`...). `und` = indeterminado; `qme`/`zxx` = só mídia/menções/sem texto linguístico. |
| `author_id`, `author_username`, `author_name` | texto | Dados do autor. |
| `author_verified` | booleano | Se a conta é verificada. |
| `like_count`, `retweet_count`, `reply_count`, `quote_count` | inteiro | Métricas públicas **no momento da coleta** (não são atualizadas depois). |
| `raw` | texto (JSON) | Objeto original do post devolvido pela API, para campos não normalizados. |

> Reexecutar com o mesmo `--output-name` **acrescenta** ao `.jsonl` e regenera o `.parquet`. Se mudar de assunto, use outro `--output-name`; caso contrário as bases se misturam e o `--resume` usará os limites da base misturada.

---

## Como pesquisar outro assunto

O assunto é definido pela `--query`. O fluxo recomendado tem dois passos:

### Passo A: valide a query com poucos posts

```bash
uv run python src/02_fetch_sample_tweets.py \
  --query '(bitcoin OR btc OR cripto) lang:pt -is:retweet' \
  --count 10
```

Leia o que apareceu. Se houver ruído (posts fora do tema), ajuste a query e repita. Cada tentativa custa centavos.

### Passo B: colete em escala com um nome próprio

```bash
uv run python src/03_bulk_download_tweets.py \
  --query '(bitcoin OR btc OR cripto) lang:pt -is:retweet' \
  --output-name tweets_bitcoin_pt \
  --limit 500 \
  --max-budget 2.50
```

Gera `data/bulk/tweets_bitcoin_pt.jsonl` e `.parquet`.

> **Aspas no terminal:** use **aspas simples por fora** da query e **aspas duplas por dentro** para expressões exatas, como em `'(selic OR "banco central") lang:pt -is:retweet'`. O X só reconhece frases entre aspas **duplas**.

### Exemplos

```bash
# Economia (português)
uv run python src/03_bulk_download_tweets.py \
  --query '(selic OR ipca OR inflação OR "banco central") lang:pt -is:retweet' \
  --output-name tweets_economia_br --limit 1000

# Futebol
uv run python src/03_bulk_download_tweets.py \
  --query '(brasileirão OR "copa do brasil" OR libertadores) lang:pt -is:retweet' \
  --output-name tweets_futebol_br --limit 1000

# Mudanças climáticas, multilíngue
uv run python src/03_bulk_download_tweets.py \
  --query '("mudanças climáticas" OR "climate change" OR "cambio climático") -is:retweet' \
  --output-name tweets_clima_global --limit 2000

# Menções a uma marca
uv run python src/03_bulk_download_tweets.py \
  --query '(nubank OR @nubank) lang:pt -is:retweet' \
  --output-name tweets_nubank --limit 500
```

---

## Sintaxe de queries do X

Referência oficial: [Building queries for Search Posts](https://docs.x.com/x-api/posts/search/integrate/build-a-query).

| Operador | Exemplo | O que faz |
| :--- | :--- | :--- |
| Palavras separadas por espaço | `vacina covid` | E implícito: exige as duas palavras. |
| `OR` | `(petrobras OR petr4)` | Pelo menos um dos termos. |
| Frase exata | `"banco central"` | Ordem e palavras exatas (aspas **duplas**). |
| `lang:` | `lang:pt` | Filtra pelo idioma detectado pelo X. |
| `-is:retweet` | `(...) -is:retweet` | Exclui retweets. **Recomendado sempre**, para não pagar pelo mesmo texto repetido. |
| `-is:reply` | `(...) -is:reply` | Exclui respostas, mantendo posts originais. |
| `#` | `#DataScience` | Hashtag. |
| `@` | `@XDevelopers` | Menciona a conta. |

Operadores de engajamento mínimo (como `min_faves:`) existem na busca do site, mas **não na API v2**. Para filtrar por curtidas, baixe e filtre depois com Polars.

### Três armadilhas que custam dinheiro

1. **A busca ignora maiúsculas/minúsculas e acentos.** `IA`, `ia` e `iá` são o mesmo termo, e `AI` casa com "aí". Buscar `IA` solto em português traz "ia fazer", "e aí". Para siglas curtas, amarre a um idioma, `(AI lang:en)`, ou use hashtag, `#IA`. Foi assim que a query padrão eliminou o ruído.
2. **`AND` tem precedência sobre `OR`.** Sempre coloque os termos alternativos entre parênteses antes dos filtros negativos:
   * Errado: `termo1 OR termo2 -is:retweet` (o filtro vale só para `termo2`).
   * Certo: `(termo1 OR termo2) -is:retweet`.
3. **Limite de tamanho.** A query tem no máximo **512 caracteres** no Recent Search (1.024 no Full-Archive, segundo a documentação do X). A query padrão usa 460.

A query padrão do projeto está em [`config.py`](src/baixa_dados_tweets/config.py) (`DEFAULT_AI_QUERY`).

---

## Manual de parâmetros do coletor (`03_bulk_download_tweets.py`)

| Parâmetro | Padrão | O que faz |
| :--- | :---: | :--- |
| `--query` | query de IA | Query com a sintaxe da API v2. |
| `--limit` | `MAX_TWEETS_LIMIT` do `.env` | Máximo de **novos** posts nesta execução. |
| `--max-budget` | `MAX_BUDGET_USD` do `.env` | Trava de gasto em USD (estimativa local). A coleta para ao atingir o valor. |
| `--output-name` | `tweets_ia_global` | Nome base dos arquivos em `data/bulk/`. |
| `--resume` | desligado | Continua **para trás no tempo**, a partir do post mais antigo já salvo. |
| `--resume-latest` | desligado | Coleta posts **mais novos** que o mais recente já salvo. |
| `--start-time` | nenhum | Início da janela (UTC, ISO 8601): `2026-10-17` ou `2026-10-17T00:00:00Z`. |
| `--end-time` | nenhum | Fim da janela (UTC). |
| `--since-hours` | nenhum | Atalho: apenas as últimas N horas. |
| `--archive` | automático | Força o endpoint **Full-Archive** (`/2/tweets/search/all`). |
| `--batch-size` | `100` | Posts por requisição (10 a 100). Mantenha 100. |

### Dois endpoints, escolhidos automaticamente

* **Recent Search** (`/2/tweets/search/recent`): últimos **7 dias**. É o padrão.
* **Full-Archive Search** (`/2/tweets/search/all`): qualquer data. O script o ativa sozinho quando `--start-time`/`--end-time` (ou a base usada em `--resume`/`--resume-latest`) estão a mais de ~6 dias do presente. **Depende do seu nível de acesso:** a conta do autor teve acesso com créditos pré-pagos; se a sua não tiver, a API devolverá erro 403.

### Regras da API que o script já trata por você

* A API **proíbe misturar `until_id`/`since_id` com `start_time`/`end_time`** (erro `HTTP 400`). Quando você usa `--resume` junto com `--start-time`, o script converte o ponto de retomada em um `end_time` de 1 segundo antes do post mais antigo da base.
* `HTTP 429` (limite de requisições): o script espera a janela reiniciar e continua.
* Parada segura com `Ctrl+C`: a página atual termina de ser gravada.

---

## Receitas de uso

### Continuar para trás sem repetir o que já foi pago

```bash
uv run python src/03_bulk_download_tweets.py --resume
```

Pega o ID do post mais antigo do `.parquet` e pede à API só posts anteriores a ele.

### Continuar para trás, mas só até uma data

```bash
uv run python src/03_bulk_download_tweets.py --resume --start-time "2026-10-17T00:00:00Z"
```

### Baixar um dia inteiro (UTC)

```bash
uv run python src/03_bulk_download_tweets.py \
  --start-time "2026-10-17T00:00:00Z" \
  --end-time "2026-10-17T23:59:59Z" \
  --limit 30000 --max-budget 150
```

Se o dia não couber em uma só execução (limite de posts ou de orçamento), a coleta termina nos posts mais antigos que alcançou. Continue o trecho que falta com `--resume --start-time <início do dia>`, ou fatie o dia em janelas com `--start-time`/`--end-time`.

### Atualizar com posts novos

```bash
uv run python src/03_bulk_download_tweets.py --resume-latest
```

> **Cuidado:** a busca sempre devolve do mais novo para o mais antigo. Se entre o seu último post salvo e o presente houver **mais posts do que o seu `--limit`**, você receberá só os mais recentes e ficará um **buraco** no meio. Para intervalos grandes, use janelas explícitas com `--start-time`/`--end-time` e confira a cobertura (veja a seção seguinte).

### Gastar no máximo um valor

```bash
uv run python src/03_bulk_download_tweets.py --limit 500 --max-budget 2.50
```

### Apenas as últimas horas

```bash
uv run python src/03_bulk_download_tweets.py --since-hours 4 --limit 300
```

---

## Analisando os dados

Use o Parquet com [Polars](https://pola.rs/) (já é dependência do projeto).

```python
import polars as pl

df = pl.read_parquet("data/bulk/tweets_ia_global.parquet")

# Idiomas mais frequentes (usa o campo "lang" detectado pelo X)
print(df["lang"].value_counts(sort=True).head(10))

# Apenas português
df_pt = df.filter(pl.col("lang") == "pt")

# Posts mais curtidos
print(df.sort("like_count", descending=True).select("author_username", "like_count", "text").head(10))
```

### Conferir a cobertura temporal (detectar buracos)

`created_at` é texto ISO em UTC; converta antes de agrupar:

```python
df = df.with_columns(pl.col("created_at").str.to_datetime("%Y-%m-%dT%H:%M:%S%.3fZ", time_zone="UTC"))

por_hora = df.group_by(pl.col("created_at").dt.truncate("1h").alias("hora_utc")).len().sort("hora_utc")
print(por_hora)  # horas ausentes ou muito baixas indicam lacunas
```

### Segregar por idioma

```python
for (lang,), parte in df.group_by("lang"):
    parte.write_parquet(f"data/lang_{lang}.parquet")
```

### DuckDB (opcional)

DuckDB não vem instalado. Para usá-lo: `uv add duckdb` (ou `uv run --with duckdb python`).

```python
import duckdb

duckdb.sql("""
    SELECT lang, COUNT(*) AS total, AVG(like_count) AS media_curtidas
    FROM 'data/bulk/tweets_ia_global.parquet'
    GROUP BY lang ORDER BY total DESC LIMIT 10
""").show()
```

---

## Limitações e cuidados metodológicos

Se você for usar os dados em pesquisa, descreva estas limitações no seu método:

1. **A amostra é definida pela query, não é aleatória.** Ela contém os posts públicos que casam com os termos. Termos em outros idiomas, gírias e sinônimos não listados ficam de fora, e a query padrão favorece o inglês porque o inglês domina o volume no X.
2. **Retweets são excluídos** (`-is:retweet`). As métricas de alcance, portanto, não incluem a difusão por retweet. Respostas e citações são mantidas, salvo se você usar `-is:reply`.
3. **Não é um censo.** Posts apagados, de contas protegidas, suspensas ou removidos antes da coleta não aparecem, e o X pode aplicar outros filtros internos.
4. **Métricas são um retrato do instante da coleta.** `like_count` e afins de um post publicado minutos antes da coleta são muito menores do que seriam dias depois. Compare apenas posts com mesma idade.
5. **Idioma vem do classificador do X** (`lang`), que erra em textos curtos e mistos. `und`, `qme` e `zxx` não são idiomas reais.
6. **Horários são UTC.** O horário de Brasília é UTC-3.
7. **Registre a coleta.** Os arquivos `meta_*.json` guardam a query, o endpoint, as janelas e as datas efetivamente cobertas. Guarde-os junto com os dados e cite a query exata no trabalho.
8. **Lacunas.** Confira a cobertura por hora (seção anterior) antes de analisar séries temporais.

---

## Dados e Termos do X

* **Não publique os dados coletados.** A pasta `data/` e os arquivos `*.parquet`/`*.jsonl` estão no `.gitignore` justamente porque os [Termos do Desenvolvedor do X](https://developer.x.com/en/developer-terms/agreement-and-policy) restringem a redistribuição de conteúdo da plataforma. Leia a política vigente antes de compartilhar qualquer coisa derivada dos posts (inclusive listas de IDs, que têm regras próprias).
* **Credenciais:** o `.env` nunca deve ser versionado. Se um token vazar, revogue-o e gere outro no Developer Console.
* **Dados pessoais:** posts contêm identificadores de pessoas reais. Trate-os conforme a legislação aplicável (por exemplo, a LGPD) e as normas do comitê de ética da sua instituição.
* Este projeto **não é afiliado ao X Corp.** Uso de nomes e marcas apenas para identificação.

---

## Adaptando com um assistente de IA

O repositório traz um arquivo de contexto, [`GEMINI.md`](GEMINI.md), que explica a um assistente de código como o projeto funciona, quais são as regras da API do X, como cada parte do código se encaixa e quais armadilhas evitar. O [`CLAUDE.md`](CLAUDE.md) apenas aponta para ele, para o Claude Code.

Abra a pasta do projeto no **Gemini CLI, Antigravity, Claude Code** ou ferramenta equivalente (eles carregam esses arquivos sozinhos) e peça a adaptação em linguagem natural. Exemplos:

* "Quero coletar posts sobre a eleição municipal de São Paulo, só em português, sem respostas. Monte a query e valide com uma amostra."
* "Preciso salvar também as hashtags e o ID do post respondido."
* "Crie um script que limpe links e menções do texto e separe a base por idioma."

O contexto instrui o assistente a **pedir confirmação antes de qualquer execução que gaste créditos**, a nunca expor o `.env` e a nunca versionar os dados coletados. Mesmo assim, revise o que ele propõe antes de rodar coletas grandes.

---

## Estrutura do projeto

```text
.
├── .env.example                    # Modelo das variáveis de ambiente (sem segredos)
├── .gitignore                      # Protege .env e dados coletados
├── CITATION.cff                    # Metadados de citação (botão "Cite this repository")
├── CLAUDE.md                       # Aponta para o GEMINI.md (Claude Code)
├── GEMINI.md                       # Contexto para assistentes de IA adaptarem o projeto
├── LICENSE                         # Apache 2.0
├── README.md
├── pyproject.toml / uv.lock        # Dependências e versões travadas
├── data/                           # Gerado localmente; não versionado
│   ├── sample_tweets.*             # Saída do script 02
│   └── bulk/                       # Saídas do script 03 (.jsonl, .parquet, meta_*.json)
└── src/
    ├── 01_test_connectivity.py     # Passo 1: credenciais, latência, saldo
    ├── 02_fetch_sample_tweets.py   # Passo 2: amostra de 10 posts
    ├── 03_bulk_download_tweets.py  # Passo 3: coleta em escala, resume, janelas
    └── baixa_dados_tweets/
        ├── client.py               # Cliente HTTP: retries, rate limit, trava de orçamento
        ├── config.py               # Variáveis do .env, preços e query padrão
        ├── storage.py              # Normalização, JSONL incremental, Parquet desduplicado
        └── topics.py               # Catálogo auxiliar de termos por idioma (não usado pelos scripts)
```

---

## Qualidade de código

```bash
uv run ruff check --fix && uv run ruff format
```

---

## Licença e como citar

Distribuído sob a licença **Apache 2.0** (arquivo [LICENSE](LICENSE)). Ao reutilizar o código, mantenha o aviso de copyright e a licença.

Se este projeto apoiar uma pesquisa, cite-o:

```bibtex
@software{ferrari2026baixadados,
  author  = {Ferrari, Ramon},
  title   = {Baixa Dados Tweets: Pipeline de Coleta e Análise em Larga Escala via API v2 do X},
  year    = {2026},
  url     = {https://github.com/ramonferrari/academic-2026-baixa-dados-tweets},
  license = {Apache-2.0}
}
```

Ou use o botão **"Cite this repository"** do GitHub, gerado a partir de [CITATION.cff](CITATION.cff).
