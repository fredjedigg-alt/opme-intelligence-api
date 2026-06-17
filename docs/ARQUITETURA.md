# Arquitetura — OPME Intelligence API

## 1. Visão de camadas (implementado vs. alvo)

```
                        OPME MARKET INTELLIGENCE LAYER
 ┌───────────── FONTES ─────────────┐
 │ APIs públicas · ERPs · planilhas │   (alvo — Fase 2)
 │ marketplaces · PDFs · catálogos  │
 └───────────────┬──────────────────┘
                 ▼
        [Ingestão / Landing]            (alvo — Airbyte / Python / MinIO)
                 ▼
        [Parsing documental]            (alvo — PyMuPDF/pdfplumber/Docling/OCR)
                 ▼
   ┌──────────────────────────────────────────────────┐
   │   CAMADA HÍBRIDA DE INTELIGÊNCIA  (IMPLEMENTADO)   │
   │   regras  →  similaridade  →  decisão  →  LLM opc. │
   └───────────────┬───────────────────────┬───────────┘
                   ▼                        ▼
        [Taxonomia mestre OPME]    [Índice de candidatos]
                   ▼                        ▼
   ┌──────────────────────────────────────────────────┐
   │  CAMADA ANALÍTICA  (IMPLEMENTADO — SQLite/stats)  │
   │  benchmark · dispersão · outliers · economia      │
   └───────────────┬───────────────────────────────────┘
                   ▼
        [API REST /api/v1]  →  Swagger/ReDoc · BI · Copiloto (alvo)
```

O que está **implementado** nesta entrega: a camada híbrida de inteligência, a taxonomia
mestre, a camada analítica e a API REST versionada. As camadas de ingestão e parsing
documental são o caminho de evolução (Fases 2–3).

## 2. Componentes da aplicação

| Módulo | Responsabilidade |
|---|---|
| `app/main.py` | Bootstrap FastAPI, lifespan (init DB), middleware (request_id + acesso), versionamento. |
| `app/config.py` | Configuração 12-factor via `pydantic-settings`. |
| `app/logging_config.py` | Logging estruturado JSON, `request_id` por requisição, rotação em arquivo. |
| `app/database.py` | Conexão SQLite, esquema e disparo do seed. |
| `app/security.py` | Hashing PBKDF2 e emissão/validação de JWT. |
| `app/schemas.py` | Contratos Pydantic (validação de entrada/saída). |
| `app/errors.py` | Hierarquia de exceções e handlers com envelope padronizado. |
| `app/ai/extractor.py` | Extração determinística de atributos (regras/regex). |
| `app/ai/similarity.py` | Similaridade textual leve (Jaccard + sequência), sem deps. |
| `app/ai/classifier.py` | Classificação taxonômica híbrida (Serviço 1). |
| `app/ai/benchmark.py` | Estatística de preço, dispersão e outliers (Serviço 2). |
| `app/ai/comparability.py` | Decisão de comparabilidade econômica (Serviço 3). |
| `app/ai/llm.py` | Enriquecimento opcional por Claude, com fallback. |
| `app/api/v1/*` | Rotas versionadas (auth, classify, benchmark, comparability, meta). |

## 3. Esquema de dados (implementado)

```sql
users(id, username, password_hash, role)

opme_taxonomy(taxonomy_id, specialty, family, subfamily,
              canonical_label, keywords, default_uom)

price_observation(obs_id, taxonomy_id→opme_taxonomy,
                  canonical_name, supplier, manufacturer, region,
                  uom_standard, normalized_price, observation_date)
```

A taxonomia tem 10 nós em 5 especialidades (Ortopedia, Cardiologia, Vascular,
Cirurgia Geral, Neurocirurgia, Bucomaxilo). As observações de preço são sintéticas,
geradas com semente fixa (`random.seed(42)`), com dispersão controlada e outliers
propositais para exercitar o benchmark.

## 4. Modelo lógico-alvo (Fases 2–3)

Para suportar BI **e** IA juntos, o modelo evolui para incluir repositório documental e
índice vetorial, mantendo rastreabilidade de cada fato analítico até o documento e o trecho
de evidência (`document`, `document_chunk`, `document_entity_extraction`, `fact_price_observation`,
`llm_run`, `human_review_queue`, etc.). Ver o blueprint completo da Atlas Health.

## 5. Fluxo de uma requisição

```
Cliente → [middleware: gera request_id + cronômetro]
        → [rota /api/v1/... : valida JWT + rate limit]
        → [Pydantic: valida corpo] (falha → 422 padronizado)
        → [serviço de IA em app/ai/*]
        → [resposta + header X-Request-ID]
        → [log de acesso JSON: método, path, status, latency_ms, request_id]
```
