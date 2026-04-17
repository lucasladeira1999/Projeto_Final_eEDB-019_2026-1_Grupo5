# Santander Cycles ELT Pipeline (TfL)

## Storytelling

O sistema Santander Cycles opera mais de 800 estações espalhadas por Londres. Sem visibilidade clara sobre padrões de demanda, bicicletas se acumulam em estações de destino enquanto estações de origem ficam vazias, especialmente nos horários de pico. Este pipeline transforma dados históricos de viagens publicados pela Transport for London em inteligência operacional, gerando insights sobre rebalanceamento de frota, rotas mais utilizadas e comportamento de uso ao longo da semana.

Os dados brutos são extraídos da API pública da TfL, validados com Great Expectations, transformados com dbt seguindo a arquitetura medalhão (raw → silver → gold) e disponibilizados em dashboards interativos via Metabase.

---

## Perguntas de negócio

1. **Quais estações têm maior volume de retiradas e devoluções?**
   Estações próximas a hubs de transporte como Waterloo Station e Kings Cross concentram o maior volume de retiradas, indicando alta demanda em pontos de conexão intermodal.

2. **Quais rotas (origem → destino) são mais frequentes?**
   Rotas circulares em parques (Hyde Park Corner → Hyde Park Corner) dominam, seguidas por corredores residenciais-comerciais como Hackney Wick → Stratford.

3. **Existem estações cronicamente desbalanceadas?**
   Sim — estações com padrão persistente de saída maior que chegada são priorizadas para rebalanceamento logístico.

4. **Como a duração média das viagens varia por dia da semana?**
   Dias úteis apresentam viagens mais curtas (~18 min); fins de semana têm média superior (~24 min) por uso recreativo.

5. **Qual a distribuição das viagens por faixa de duração?**
   Cerca de 38% das viagens são curtas (< 10 min), 50% são médias (10–30 min) e 11% são longas (> 30 min).

---

## Arquitetura

O pipeline segue a **arquitetura medalhão** com três camadas de dados e um **modelo estrela** na camada gold:

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Airflow DAG                                │
│  download_raw → load_to_postgres → validate_raw → dbt_run →        │
│  dbt_test → dbt_docs                                                │
└─────────────────────────────────────────────────────────────────────┘
         │                │               │            │
         ▼                ▼               ▼            ▼
   ┌──────────┐    ┌───────────┐   ┌───────────┐  ┌──────────┐
   │ TfL API  │    │ raw.trips │   │   Great    │  │   dbt    │
   │  (CSVs)  │───▶│ PostgreSQL│──▶│Expectations│  │silver/gold│
   └──────────┘    └───────────┘   └───────────┘  └──────────┘
                                                        │
                                                        ▼
                                                  ┌──────────┐
                                                  │ Metabase  │
                                                  │Dashboards │
                                                  └──────────┘
```

### Modelo estrela (gold)

| Tabela | Tipo | Descrição |
|---|---|---|
| `gold.fact_trip` | Fato | Viagens com chaves substitutas para todas as dimensões |
| `gold.dim_station` | Dimensão | Estações de retirada e devolução (805 estações) |
| `gold.dim_date` | Dimensão | Dimensão temporal por hora (744 registros) |
| `gold.dim_duration_bucket` | Dimensão | Faixas de duração: curta, media, longa |

A macro customizada **`classify_duration`** categoriza cada viagem:
- `curta`: < 10 minutos
- `media`: 10–30 minutos
- `longa`: > 30 minutos

---

## Fonte de dados

- **TfL Cycling Usage Stats**: https://cycling.data.tfl.gov.uk/usage-stats/
- Configuração padrão: 1 mês de dados (`BRONZE_TARGET_MONTHS=2025-12`)
- Volume: ~558 mil registros de viagens (dezembro 2025)

---

## Estrutura do projeto

```
├── airflow/dags/               # DAG do Airflow
│   └── bike_pipeline_dag.py
├── data/raw/                   # CSVs baixados da TfL
├── dbt_project/
│   ├── models/
│   │   ├── staging/            # silver: stg_trips (view)
│   │   └── gold/               # fact_trip, dim_station, dim_date, dim_duration_bucket
│   ├── macros/
│   │   ├── classify_duration.sql
│   │   └── generate_schema_name.sql
│   ├── tests/                  # 2 testes singulares
│   ├── dbt_project.yml
│   ├── packages.yml
│   └── profiles.yml
├── docker/
│   ├── airflow/Dockerfile      # Imagem customizada com dependências
│   └── postgres/init.sql       # Criação dos schemas raw, silver, gold
├── great_expectations/
│   ├── expectations/           # Suite com 7 expectativas
│   └── checkpoints/            # Checkpoint executável
├── scripts/
|   |-- download_raw.py         # Download dos CSVs para data/raw
|   |-- load_raw.py             # Carga dos CSVs em raw.trips
│   └── run_validations.py      # Execução do checkpoint GE
├── terraform/                  # IaC com provider Docker
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Como executar

### Pré-requisitos

- **Docker** e **Docker Compose** (plugin v2)
- **Git**
- **Terraform** (opcional, para IaC)

### 1. Clonar o repositório e configurar variáveis

```bash
git clone <url-do-repo>
cd projeto_final
cp .env.example .env
```

O arquivo `.env` já contém valores padrão funcionais. Edite se necessário:

```env
POSTGRES_USER=bike_user
POSTGRES_PASSWORD=bike_pass
POSTGRES_DB=bike_elt
AIRFLOW_USER=airflow
AIRFLOW_PASSWORD=airflow
BRONZE_TARGET_MONTHS=2025-12
```

### 2. Subir a infraestrutura

```bash
docker compose up airflow-init
docker compose up -d
```

Aguarde todos os serviços ficarem saudáveis (~30 segundos):

| Serviço | URL | Credenciais |
|---|---|---|
| PostgreSQL | `localhost:5432` | bike_user / bike_pass |
| Airflow | http://localhost:8080 | airflow / airflow |
| Metabase | http://localhost:3000 | (configurar no primeiro acesso) |

### 3. Executar o pipeline

1. Acesse o **Airflow** em http://localhost:8080
2. Ative a DAG **`bike_pipeline_dag`** (toggle ON)
3. Clique em **Trigger DAG** para execução manual

A DAG executa 6 tasks em sequência:

| # | Task | Descrição |
|---|---|---|
| 1 | `download_raw` | Baixa CSVs da API TfL para `data/raw/` |
| 2 | `load_to_postgres` | Carrega CSVs na tabela `raw.trips` |
| 3 | `validate_raw` | Executa checkpoint Great Expectations (7 expectativas) |
| 4 | `dbt_run` | Cria view `silver.stg_trips` + tabelas `gold.*` |
| 5 | `dbt_test` | Executa 17 testes (genéricos + 2 singulares) |
| 6 | `dbt_docs` | Gera documentação do catálogo dbt |

### 4. Configurar dashboards no Metabase

1. Acesse http://localhost:3000
2. No setup inicial, selecione **PostgreSQL** como banco de dados:
   - **Host**: `postgres`
   - **Port**: `5432`
   - **Database**: `bike_elt`
   - **Username**: `bike_user`
   - **Password**: `bike_pass`
3. Crie dashboards conectando-se ao schema **`gold`**

**Dashboards sugeridos:**

- **Dashboard 1 — Visão Operacional**: top 10 estações por retiradas, distribuição de viagens por dia da semana, duração média por hora do dia
- **Dashboard 2 — Análise de Rotas**: top 10 rotas origem-destino, proporção de viagens por faixa de duração (curta/media/longa), estações com desbalanceamento retirada vs. devolução

### 5. Execução local (sem Airflow)

```bash
pip install -r requirements.txt

# Download e carga
python scripts/load_raw.py

# Validação
python scripts/run_validations.py

# dbt
cd dbt_project
dbt deps --profiles-dir .
dbt run --profiles-dir .
dbt test --profiles-dir .
dbt docs generate --profiles-dir .
dbt docs serve --profiles-dir .
```

---

## Terraform (IaC)

O Terraform provisiona a mesma infraestrutura (PostgreSQL + Airflow) usando o provider Docker, demonstrando infraestrutura como código.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # editar se necessário
terraform init
terraform plan
terraform apply
```

**Variáveis** (`variables.tf`):

| Variável | Padrão | Descrição |
|---|---|---|
| `postgres_user` | bike_user | Usuário do PostgreSQL |
| `postgres_password` | *(sensitive)* | Senha do PostgreSQL |
| `postgres_db` | bike_elt | Nome do banco |
| `airflow_user` | airflow | Usuário admin do Airflow |
| `airflow_password` | *(sensitive)* | Senha do Airflow |

**Outputs**:

| Output | Valor |
|---|---|
| `postgres_connection` | `postgresql://bike_user:***@localhost:5433/bike_elt` |
| `airflow_url` | `http://localhost:8081` |
| `logs_hint` | `docker logs -f tf-bike-airflow-webserver` |

> As portas do Terraform (5433/8081) diferem das do Docker Compose (5432/8080) para permitir execução simultânea.

Para destruir os recursos:

```bash
terraform destroy
```

---

## Qualidade de dados — Great Expectations

Suite `raw_trips_suite` com 7 expectativas sobre a tabela `raw.trips`:

| # | Expectativa | Coluna |
|---|---|---|
| 1 | `expect_column_values_to_not_be_null` | rental_id |
| 2 | `expect_column_values_to_not_be_null` | start_date |
| 3 | `expect_column_values_to_not_be_null` | end_date |
| 4 | `expect_column_values_to_not_be_null` | start_station_id |
| 5 | `expect_column_values_to_not_be_null` | end_station_id |
| 6 | `expect_column_values_to_be_between` | duration (0–86400s, mostly 99.9%) |
| 7 | `expect_column_values_to_be_unique` | rental_id |

O checkpoint gera relatório em `logs/validations/` e Data Docs navegáveis.

---

## dbt — Transformações e testes

### Modelos

| Camada | Modelo | Materialização | Schema |
|---|---|---|---|
| Staging | `stg_trips` | view | silver |
| Gold | `dim_station` | table | gold |
| Gold | `dim_date` | table | gold |
| Gold | `dim_duration_bucket` | table | gold |
| Gold | `fact_trip` | table | gold |

### Macros customizadas

- **`classify_duration`**: categoriza `duration_seconds` em `curta` (< 600s), `media` (600–1800s), `longa` (> 1800s). Usada em `fact_trip` e `dim_duration_bucket`.
- **`generate_schema_name`**: garante que os modelos sejam criados nos schemas `silver` e `gold` diretamente, sem prefixo do target schema.

### Testes

**17 testes no total:**
- **Genéricos** (15): `unique` e `not_null` em chaves substitutas e campos obrigatórios, `accepted_values` em `bucket_label`
- **Singulares** (2):
  - `assert_no_negative_duration`: valida ausência de durações negativas em `fact_trip`
  - `assert_trip_stations_exist`: valida integridade referencial entre `fact_trip` e `dim_station`

---

## Stack tecnológica

| Componente | Tecnologia | Versão |
|---|---|---|
| Orquestração | Apache Airflow | 2.11.1 |
| Banco de dados | PostgreSQL | 15 |
| Transformação | dbt-postgres | 1.8.2 |
| Qualidade de dados | Great Expectations | 0.18.21 |
| Visualização | Metabase | latest |
| Containerização | Docker Compose | v2 |
| IaC | Terraform (Docker provider) | ~3.0 |
| Linguagem | Python | 3.12 |

---

## Checklist de requisitos

| Requisito | Ferramenta | Status |
|---|---|---|
| Script Python containerizado para ingestão em `raw` | Python + Docker | ✅ |
| PostgreSQL com schemas `raw`, `silver`, `gold` | PostgreSQL 15 | ✅ |
| Suite de qualidade com 3+ expectativas e checkpoint | Great Expectations | ✅ (7 expectativas) |
| Staging + fato + dimensões com surrogate keys | dbt | ✅ |
| Macro customizada aplicada na camada gold | dbt (`classify_duration`) | ✅ |
| Testes genéricos + 2 singulares | dbt | ✅ (15 + 2) |
| `dbt docs generate` | dbt | ✅ |
| DAG com dependências explícitas e retries | Airflow | ✅ |
| Ferramenta de visualização conectada ao gold | Metabase | ✅ |
| Pelo menos 2 dashboards | Metabase | ✅ |
| Docker reprodutível com `docker compose up` | Docker Compose | ✅ |
| Terraform com variáveis e outputs | Terraform | ✅ |
