# 🐦 Baixa Dados Tweets (X / Twitter API v2)

Pipeline em Python moderno gerenciado com **uv** para download em larga escala, higienização, salvamento incremental e exportação em **Apache Parquet** a partir da API oficial do X (Twitter) v2.

---

## 💰 Modelo de Cobrança e Custos da API do X (Pay-Per-Use)

A API v2 oficial do X opera sob modelo pré-pago por requisição (*Pay-Per-Use*). Cada tweet entregue consome saldo dos seus créditos de desenvolvedor:

* **Tarifa de leitura de tweets:** **US$ 0,005 por tweet lido** (~R$ 0,029).
* **Consumo de créditos:**
  * **100 tweets:** US$ 0,50 (~R$ 2,90) — *ideal para amostras e testes de schema*
  * **1.000 tweets:** US$ 5,00 (~R$ 29,00)
  * **9.000 tweets:** US$ 45,00 (~R$ 261,00) — *cobertura de ~7 horas de IA no mundo*
  * **30.000 tweets:** US$ 150,00 (~R$ 870,00) — *estimativa de 24h completas de IA global*

> [!IMPORTANT]
> **A API do X cobra por leitura:** O X não armazena histórico do que você já baixou. Se você fizer uma busca que retorne os mesmos tweets novamente, você será cobrado mais uma vez. Para evitar isso, este projeto possui **continuidade inteligente com IDs e filtros de tempo (`--resume` e `--resume-latest`)**.

---

## 📂 Estrutura do Projeto

```text
baixa-dados-tweets/
├── .env.example                 # Modelo público de variáveis de ambiente
├── .env                         # Suas chaves e saldo real (ignorado pelo git)
├── .gitignore                   # Proteção contra vazamento de chaves e dados brutos
├── pyproject.toml               # Dependências do projeto (uv / PEP 621)
├── uv.lock                      # Lockfile determinístico do uv
├── GEMINI.md                    # Memória de contexto operacional e notas de sessão
├── README.md                    # Guia completo de uso e manual de parâmetros
├── data/                        # Dados gerados (ignorado pelo git)
│   ├── sample_tweets.parquet    # Amostra de teste colunar
│   └── bulk/                    # Coletas em larga escala (.parquet e .jsonl)
└── src/
    ├── 01_test_connectivity.py  # [Passo 1] Valida autenticação, latência e saldo
    ├── 02_fetch_sample_tweets.py# [Passo 2] Amostra rápida (10 tweets) com tabela visual
    ├── 03_bulk_download_tweets.py# [Passo 3] Coletor em lote com paginação e resume
    └── baixa_dados_tweets/      # Módulos reutilizáveis
        ├── client.py            # Cliente HTTP com retries, rate limits e até 402 guard
        ├── config.py            # Settings (Pydantic), custos e Query Canônica de IA
        ├── storage.py           # Normalização, streaming .jsonl e Parquet desduplicado
        └── topics.py            # Mapeamento multilíngue (15 idiomas)
```

---

## ⚙️ Instalação Rápida

1. Certifique-se de ter o [uv](https://docs.astral.sh/uv/) instalado:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. Clone o repositório e configure as credenciais:
   ```bash
   cp .env.example .env
   ```
3. Abra o `.env` e insira seu `X_BEARER_TOKEN` obtido no [X Developer Portal](https://developer.x.com/en/portal/dashboard).

---

## 🚀 Guia Rápido: A Trinca Operacional (Zero Parâmetros)

Os scripts já vêm calibrados com a **Query Canônica Global de IA** (cobre os 15 maiores idiomas e os principais modelos generativos como ChatGPT, Claude, Gemini, GPT e LLM):

### Passo 1: Testar Conexão e Saldo
Valida se seu Bearer Token está ativo e se a conta tem saldo para consultas:
```bash
uv run python src/01_test_connectivity.py
```

### Passo 2: Baixar Amostra de Validação (10 Tweets)
Faz o download de 10 tweets recentes e imprime uma tabela formatada no terminal para você checar se a busca está com ruído zero:
```bash
uv run python src/02_fetch_sample_tweets.py
```

### Passo 3: Coletar em Larga Escala (Até o Teto do .env)
Baixa até 9.000 tweets (ou até esgotar os US$ 45 de créditos), salvando continuamente em `.jsonl` e convertendo para `.parquet`:
```bash
uv run python src/03_bulk_download_tweets.py
```

---

## 📖 Manual de Parâmetros do Coletor (`03_bulk_download_tweets.py`)

Se você quiser customizar a coleta, o script aceita diversos parâmetros opcionais via terminal:

| Parâmetro | Padrão | O que faz / Para que serve |
| :--- | :---: | :--- |
| **`--resume`** | `False` | **Continua voltando no tempo** a partir do tweet mais antigo já salvo na sua base, **sem pagar nada duplicado**. |
| **`--resume-latest`**| `False` | **Busca apenas tweets novos** publicados após o tweet mais recente da base. |
| **`--limit`** | `9000` | Quantidade máxima de tweets a baixar nesta execução. |
| **`--max-budget`** | `45.0` | Trava de segurança financeira em USD. A coleta aborta se atingir esse valor. |
| **`--query`** | *Query IA* | Termo ou query personalizada com sintaxe da API v2. |
| **`--since-hours`** | `None` | Coleta tweets publicados apenas nas últimas N horas (ex: `--since-hours 12`). |
| **`--start-time`** | `None` | Data/hora UTC inicial no formato ISO (ex: `2026-10-17T00:00:00Z`). |
| **`--end-time`** | `None` | Data/hora UTC final no formato ISO (ex: `2026-10-17T12:19:54Z`). |
| **`--batch-size`** | `100` | Quantidade de tweets por requisição (10 a 100). Deixe em 100 para economia máxima de chamadas. |
| **`--output-name`** | `tweets_ia_global` | Nome base dos arquivos gerados dentro de `data/bulk/`. |

---

## 💡 Receitas Prontas para o Dia a Dia (Exemplos Práticos)

### 1. Continuar a Coleta para Trás (Completar a Madrugada/Manhã)
Use quando você colocou mais créditos e quer continuar baixando tweets anteriores ao seu lote atual:
```bash
uv run python src/03_bulk_download_tweets.py --resume
```
> O script lê automaticamente o arquivo Parquet existente, encontra o ID do tweet mais antigo e instrui a API do X a buscar apenas postagens anteriores a ele (`until_id`). **Zero sobreposição, zero custo dobrado.**

### 2. Coletar Tweets Recentes (O que saiu no final do dia/noite)
Use quando você já tem a base da tarde e quer apenas as novas postagens que saíram depois:
```bash
uv run python src/03_bulk_download_tweets.py --resume-latest
```

### 3. Coleta com Orçamento Limitado (Ex: Gastar no Máximo US$ 5,00)
Para fazer um estudo pontual de até 1.000 tweets com trava estrita de 5 dólares:
```bash
uv run python src/03_bulk_download_tweets.py --limit 1000 --max-budget 5.0
```

### 4. Buscar Tweets Publicados Apenas nas Últimas 6 Horas
```bash
uv run python src/03_bulk_download_tweets.py --since-hours 6 --limit 500
```

### 5. Coletar Outro Assunto Qualquer (Ex: Eleições ou Bitcoin)
```bash
uv run python src/03_bulk_download_tweets.py \
  --query "(bitcoin OR btc OR cripto) lang:pt -is:retweet" \
  --limit 500 \
  --output-name "tweets_bitcoin_pt"
```

### 6. Delimitar uma Janela Específica de Horário (UTC)
```bash
uv run python src/03_bulk_download_tweets.py \
  --start-time "2026-10-17T00:00:00Z" \
  --end-time "2026-10-17T12:00:00Z" \
  --limit 5000
```

---

## 🎯 Guia de Engenharia de Queries no X (Sintaxe da API v2)

Para extrair dados limpos sem gastar créditos com ruído, atente-se a estas regras da API do X:

1. **A busca é Case-Insensitive:** A API não diferencia `AI`, `ai` ou `aí`. Buscar `AI` solto no Brasil trará *"arruma uma aí"*.
   * **Como resolver:** Use `(AI lang:en)` para a sigla em inglês, e `#AI` / `#IA` para hashtags.
2. **Precedência do `AND` sobre `OR`:** Sempre use parênteses no bloco de termos antes de filtros de exclusão:
   * **Errado:** `termo1 OR termo2 -is:retweet` *(o -is:retweet só se aplica ao termo2!)*
   * **Correto:** `(termo1 OR termo2) -is:retweet` *(elimina retweets de todos os termos)*
3. **Limite de Tamanho da Query:** No endpoint Recent Search, o limite rígido é de **512 caracteres**. A nossa query canônica usa 460 caracteres:
   ```text
   (ChatGPT OR Claude OR Gemini OR GPT OR LLM OR GenAI OR (AI lang:en) OR #AI OR #IA OR #KI OR "artificial intelligence" OR "inteligência artificial" OR "inteligencia artificial" OR "intelligence artificielle" OR "künstliche intelligenz" OR "intelligenza artificiale" OR "人工知能" OR "人工智能" OR "искусственный интеллект" OR "الذكاء الاصطناعي" OR "인공지능" OR "आर्टिफिशियल इंटेलिजेंस" OR "yapay zeka" OR "kunstmatige intelligentie" OR "sztuczna inteligencja") -is:retweet
   ```

---

## 📊 Como Abrir e Analisar a Base Salva (.parquet)

Os dados são salvos em `data/bulk/tweets_ia_global.parquet` com o campo oficial de idioma (`lang`), métricas de engajamento e metadados do autor.

### Com Polars (Nativo e Ultra-Rápido):
```python
import polars as pl

# Leitura instantânea do Parquet
df = pl.read_parquet("data/bulk/tweets_ia_global.parquet")

# Filtrar apenas postagens em Português
df_pt = df.filter(pl.col("lang") == "pt")
print(f"Total em português: {len(df_pt)}")

# Ver distribuição dos 10 maiores idiomas
print(df["lang"].value_counts(sort=True).head(10))

# Tweets virais com mais de 1.000 curtidas
virais = df.filter(pl.col("like_count") > 1000).select(["author_username", "like_count", "text"])
print(virais)
```

### Com DuckDB (direto no terminal ou Python via SQL):
```python
import duckdb

# Top 10 idiomas mais frequentes na base
duckdb.sql("""
    SELECT lang, COUNT(*) as total, AVG(like_count) as media_curtidas
    FROM 'data/bulk/tweets_ia_global.parquet'
    GROUP BY lang
    ORDER BY total DESC
    LIMIT 10;
""").show()
```

---

## 🔒 Segurança de Credenciais e Repositório Público

Este projeto está pronto e seguro para publicação em repositórios públicos:
* O arquivo `.env` com suas chaves reais e a pasta `data/` com os dados baixados estão no `.gitignore`.
* Nenhum token fica salvo no histórico Git.
* O arquivo `.env.example` fornece o gabarito sem credenciais para outros usuários.


---

## 📚 Como Citar este Projeto

Se você utilizar este pipeline ou os métodos de coleta em sua pesquisa, artigo ou projeto, por favor cite como:

```bibtex
@software{ferrari2026baixadados,
  author = {Ferrari, Ramon},
  title = {Baixa Dados Tweets: Pipeline de Coleta e Análise em Larga Escala via API v2 do X},
  year = {2026},
  url = {https://github.com/ramonferrari/baixa-dados-tweets},
  license = {Apache-2.0}
}
```
Ou utilize o botão oficial **"Cite this repository"** na barra lateral direita do GitHub gerado pelo arquivo [CITATION.cff](CITATION.cff).
