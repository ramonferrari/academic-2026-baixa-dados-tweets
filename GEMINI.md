# Projeto: Baixa Dados Tweets (X/Twitter API v2)

Guia de contexto e memória operacional do projeto para o agente Gemini / Antigravity.

---

## 1. O Que Pretendemos Fazer (Visão Geral e Objetivos)

O objetivo principal deste projeto é construir um pipeline robusto, econômico e reprodutível para coletar e analisar postagens públicas em escala global sobre **Inteligência Artificial (IA)** na API oficial v2 do X/Twitter.

### Metas do Projeto:
1. **Cobertura Global Multilíngue:** Capturar discussões dos 15 maiores idiomas do X (incluindo Português, Espanhol, Inglês, Japonês, Chinês, Árabe, Turco, etc.) e menções aos principais modelos de fronteira (`ChatGPT`, `Claude`, `Gemini`, `GPT`, `LLM`, `GenAI`).
2. **Qualidade e Relevância Máxima (Ruído Zero):** Formular termos de busca restritos para eliminar falsos cognatos (ex.: verbos em português como "ia fazer" ou expressões coloquiais "arruma uma aí").
3. **Controle Financeiro Rigoroso:** Operar sob o modelo *Pay-Per-Use* da API v2 ($0.005 por tweet lido) com travas automáticas de segurança, cálculo de custos em tempo real (USD e BRL) e proteção contra cobranças repetidas.
4. **Armazenamento Analítico Moderno:** Persistir dados continuamente em `.jsonl` para tolerância a falhas e convertê-los automaticamente em **Apache Parquet (`.parquet`)** colunar com compressão Snappy e desduplicação por ID.
5. **Estudos e Segregação Futura:** Viabilizar análises comparativas de sentimentos, modelagem de tópicos (BERTopic) e segregação por idioma através da coluna nativa `lang`.
6. **Pilha Analítica Estrita (NUNCA usar Pandas):** Toda análise de dados, manipulação de dataframes e consulta colunar deve ser feita exclusivamente com **Polars** (`import polars as pl`) e **DuckDB**.

---

## 2. O Que Já Fizemos

1. **Setup da Infraestrutura:**
   - Projeto configurado em Python 3.12 gerenciado com `uv` (`pyproject.toml`, `uv.lock`).
   - Dependências: `httpx`, `pyarrow`, `rich`, `pydantic-settings`, `python-dotenv`.
   - Estrutura modular em `src/baixa_dados_tweets/` (`client.py`, `config.py`, `storage.py`, `topics.py`).

2. **Diagnóstico da API e Modelo Financeiro:**
   - Resolução do erro HTTP 402 (*Payment Required / Credits Depleted*) esclarecendo que a API v2 requer compra pré-paga de créditos na Developer Console.
   - Orçamento e travas fixadas em US$ 45.00 (~9.000 tweets).

3. **Engenharia da Query Oficial (460 caracteres, teto 512):**
   - Resolução do problema de case-insensitivity do X: substituição do termo solto `AI` por `(AI lang:en)` e `IA` por `#IA` e `"inteligência artificial"`.
   - Correção da precedência booleana com parênteses externos: `(...) -is:retweet` para barrar 100% dos retweets.

4. **Trinca de Scripts Operacionais (Execução sem Parâmetros):**
   - `src/01_test_connectivity.py`: Validação de autenticação, latência e saldo.
   - `src/02_fetch_sample_tweets.py`: Download de amostra (10 tweets) com renderização visual formatada.
   - `src/03_bulk_download_tweets.py`: Coleta massiva com paginação `next_token`, rate limiting e exportação Parquet.
   - Remoção de scripts obsoletos/duplicados (`04_search_ai_multilingual.py`) para evitar confusão.

5. **Primeira Coleta em Larga Escala Concluída:**
   - **8.998 tweets baixados** em 136 segundos.
   - Custo total: **US$ 44.9900** (~R$ 260.94) — consumo exato da trava de créditos.
   - Janela temporal: das 12:19:55 UTC às 19:23:17 UTC de 17/10/2026 (~7 horas ininterruptas de dados).
   - Dados persistidos em `data/bulk/tweets_ia_global.jsonl` e `data/bulk/tweets_ia_global.parquet`.

6. **Auditoria e Avaliação Qualitativa da Base:**
   - Presença de **39 idiomas distintos** (`en`: 85,5%, `tr`: 2,1%, `zh`: 2,1%, `ja`: 2,07%, `es`: 1,84%, `pt`: 1,62%, `ar`: 1,44%).
   - Forte penetração nominal de modelos: **Claude** (9,54%), **ChatGPT** (5,30%), **Gemini** (4,98%).
   - Ruído nulo: os tweets coletados tratam genuinamente de modelos, debates éticos, programação e política.

7. **Implementação de Continuidade Inteligente e Desduplicação:**
   - Atualização do `03_bulk_download_tweets.py` com suporte a `--resume` (continua para trás a partir do tweet mais antigo usando `until_id`) e `--resume-latest` (pega tweets novos após o mais recente via `since_id`).
   - Adicionada desduplicação estrita por `id` na conversão do Parquet em `storage.py`.

---

## 3. O Que Falta Fazer

1. **Recarga de Créditos para Completar o Dia (17/10/2026):**
   - Quando o Ferrari decidir alocar novo saldo na conta Developer:
     - Coletar a manhã restante (00:00 às 12:19 UTC): `uv run python src/03_bulk_download_tweets.py --resume` (estimativa: ~15.000 tweets / ~US$ 75).
     - Coletar o final da noite (19:23 às 23:59 UTC): `uv run python src/03_bulk_download_tweets.py --resume-latest` (estimativa: ~5.500 tweets / ~US$ 28).
2. **Pipeline de Pré-Processamento e NLP:**
   - Desenvolver script de limpeza de texto (remoção de links `https://t.co/...`, menções `@username`, quebras de linha sujas).
   - Segregação automática de arquivos Parquet por idioma (`data/processed/lang_pt.parquet`, etc.).
3. **Análise Temática e Semântica:**
   - Clusterização de tópicos via BERTopic / embeddings multilíngues.
   - Comparativo de percepção de marca e sentimento entre modelos (Claude vs ChatGPT vs Gemini).
4. **Relatórios e Visualização:**
   - Notebook ou script de geração de gráficos com DuckDB e Plotly/Seaborn.

---

---

tipo: procedimento
status: arquivado

# Sessão: Coleta Massiva de Tweets sobre IA Multilíngue via API v2 do X

## Contexto
O Ferrari solicitou a criação de um projeto para coletar postagens públicas no X/Twitter sobre Inteligência Artificial cobrindo múltiplos idiomas (com foco nos 15 a 20 maiores) e as principais IAs generativas de fronteira (ChatGPT, Claude, Gemini, GPT). O Ferrari contratou créditos de desenvolvedor (US$ 45.00 no modelo Pay-Per-Use) e precisava de um fluxo limpo em Python com `uv`, com zero complexidade de linha de comando, travas financeiras rígidas para não estourar o orçamento e persistência em Apache Parquet para análise posterior.

## O que foi feito
1. Estruturado o ambiente Python 3.12 com `uv` em `/Users/Ferrariferrari/second_brain/baixa-dados-tweets` contendo `pyproject.toml`, `.env` e controle de pacotes (`httpx`, `pyarrow`, `rich`, `pydantic-settings`).
2. Diagnosticada a cobrança da API do X: solucionado o erro HTTP 402 após esclarecer a necessidade de compra pré-paga de créditos na Developer Console.
3. Projetada a query canônica de busca (460 caracteres, abaixo do limite de 512) em `src/baixa_dados_tweets/config.py`:
   - Incluídos os 15 maiores idiomas e os termos `ChatGPT`, `Claude`, `Gemini`, `GPT`, `LLM`, `GenAI`.
   - Restringida a sigla inglesa para `(AI lang:en)` e hashtags `#AI`, `#IA`, `#KI` para eliminar ruído coloquial em português e espanhol ("arruma uma aí", "ia trabalhar").
   - Aplicada precedência booleana rigorosa com `(...) -is:retweet` para banir retweets.
4. Construída a trinca de scripts em `src/`:
   - `01_test_connectivity.py`: Validação de conexão e autenticação com @X.
   - `02_fetch_sample_tweets.py`: Teste amostral de 10 tweets com visualização em tabela Rich.
   - `03_bulk_download_tweets.py`: Coleta massiva contínua com paginação via `next_token`, streaming `.jsonl` e conversão atômica para `.parquet`.
5. Excluído o script redundante `04_search_ai_multilingual.py` a pedido do Ferrari para evitar confusão.
6. Executado o coletor massivo `03_bulk_download_tweets.py`:
   - Baixados com sucesso **8.998 tweets** em 136,2 segundos, consumindo **US$ 44.9900** (~R$ 260,94).
   - Janela de dados coletados: `2026-10-17T12:19:55Z` até `2026-10-17T19:23:17Z` (~7 horas contínuas de 17/10/2026).
   - Arquivos gerados: `data/bulk/tweets_ia_global.jsonl` e `data/bulk/tweets_ia_global.parquet`.
7. Conduzida auditoria analítica e qualitativa da base de 8.998 tweets:
   - Identificados 39 idiomas no campo nativo `lang` da API (`en`: 85,53%, `tr`: 2,13%, `zh`: 2,12%, `ja`: 2,07%, `es`: 1,84%, `pt`: 1,62% com 146 tweets, `ar`: 1,44%).
   - Verificada a distribuição de menções: Claude (858 tweets / 9,54%), ChatGPT (477 tweets / 5,30%), Gemini (448 tweets / 4,98%).
   - Confirmada ausência de falsos cognatos: base 100% limpa com discussões reais de tecnologia, memes e política.
8. Implementada continuidade inteligente e prevenção contra cobranças duplicadas do X em `client.py` e `03_bulk_download_tweets.py`:
   - Adicionada flag `--resume` utilizando `until_id` com base no tweet mais antigo existente (`2111432016281633242`).
   - Adicionada flag `--resume-latest` utilizando `since_id` com base no tweet mais novo existente (`2111538560406839414`).
   - Implementada desduplicação por `id` em `storage.py` no pipeline Parquet.

## Decisões
1. O Ferrari optou por concentrar o escopo de idiomas nos 15 maiores e priorizar a inclusão nominal dos principais modelos generativos (`ChatGPT`, `Claude`, `Gemini`, `GPT`, `LLM`, `GenAI`), mantendo o tamanho da query dentro do teto estrito de 512 caracteres da API.
2. O Ferrari decidiu excluir o script `04_search_ai_multilingual.py`, consolidando a operação em scripts numerados diretos (`01`, `02`, `03`) que executam sem necessidade de passar parâmetros complexos no terminal.
3. O Ferrari estabeleceu a trava de orçamento em US$ 45.00 para a primeira rodada exploratória, consumindo integralmente o crédito na coleta das últimas 7 horas do dia.
4. Decidiu-se implementar a continuidade via IDs do Twitter (*Snowflake IDs* via `until_id` e `since_id`) em vez de timestamps soltos, garantindo que o X não cobre novamente por tweets já lidos caso mais créditos sejam adicionados.

## Aprendizados
1. A API v2 do X é estritamente *stateless* e tarifada por leitura ($0.005 por tweet entregue). Ela não armazena histórico de requisições anteriores: requisições com sobreposição temporal faturam novamente pelos mesmos tweets se não forem delimitadas por `until_id` ou `end_time`.
2. A busca da API v2 ignora capitalização (*case-insensitive*) e acentuação: buscar `AI` ou `IA` solto em português/espanhol atrai volume massivo de ruído coloquial ("ia lá", "aí sim"). A contenção eficaz exige vincular a sigla ao idioma em inglês `(AI lang:en)` e usar hashtags (`#AI`, `#IA`) ou a expressão completa (`"inteligência artificial"`).
3. O operador booleano `AND` tem precedência sobre o `OR` na sintaxe do X: a expressão de negação `-is:retweet` precisa de parênteses externos englobando todo o bloco de termos `(...) -is:retweet`, caso contrário o filtro só se aplica ao último termo.
4. O campo `lang` da API v2 possui classificação algorítmica confiável de idioma em padrão BCP 47 (com `und` reservado a textos curtos ou emojis), permitindo particionamento e estudos comparativos sem necessidade de classificadores adicionais de NLP.
5. O volume de tweets orgânicos sobre IA nos 15 maiores idiomas é de aproximadamente ~1.280 tweets por hora, totalizando cerca de 30.000 tweets por dia de 24 horas.

## Em aberto
1. Definição pelo Ferrari de recarga de créditos na Developer Console para completar o dia de 17/10/2026 (estimativa de ~US$ 105 para cobrir as 17 horas restantes).
2. Definição dos critérios de pré-processamento de texto e modelagem de tópicos para os dados coletados.

## Próximos passos
1. Para buscar a madrugada/manhã de hoje (00:00 até 12:19 UTC) sem pagar duplicado: executar `uv run python src/03_bulk_download_tweets.py --resume`.
2. Para buscar o final da noite (após 19:23 UTC até o fim do dia) sem pagar duplicado: executar `uv run python src/03_bulk_download_tweets.py --resume-latest`.
3. Criar script de extração e segmentação da base Parquet por idioma para análise comparativa.
