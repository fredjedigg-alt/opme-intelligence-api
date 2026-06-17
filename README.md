# OPME Intelligence API

**Camada de inteligência de mercado para OPME** (Órteses, Próteses e Materiais Especiais),
exposta como uma **API REST de IA** construída em **FastAPI**.

Projeto duplo:
- **Trabalho final da disciplina _Construção de APIs para Inteligência Artificial_ (UFG — Módulo 3)** — uma API funcional com múltiplos serviços de IA, autenticação, versionamento, logs, validação e tratamento de erros.
- **Ferramenta de BI para a consultoria Atlas Health** — transforma descrições caóticas de itens hospitalares em dados estruturados, comparáveis e analisáveis (benchmark de preço, dispersão, oportunidade de economia).

> A API roda **100% offline**, sem chave de LLM e sem banco externo (usa SQLite + motor de regras/similaridade). O enriquecimento por LLM (Claude) é **opcional**.

---

## 🚀 Início rápido (3 passos)

Pré-requisito: **Python 3.10+** (testado em 3.14).

```bash
# 1. Criar ambiente e instalar dependências
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt

# 2. (Opcional) Copiar configuração — a API roda sem isso, com defaults seguros
cp .env.example .env

# 3. Subir a API (o banco é criado e populado automaticamente no 1º start)
uvicorn app.main:app --reload
```

Acesse:
- **Documentação interativa (Swagger):** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc
- **Health check:** http://127.0.0.1:8000/api/v1/health

Credenciais de demonstração: **usuário `atlas` / senha `atlas123`**.

---

## 🔐 Autenticação (em 10 segundos)

Todos os endpoints de IA exigem **Bearer Token (JWT)**. Pelo Swagger, clique em
**Authorize** e informe `atlas` / `atlas123`. Via terminal:

```bash
# 1. Obter token
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/token \
  -d "username=atlas&password=atlas123" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 2. Chamar um serviço de IA
curl -X POST http://127.0.0.1:8000/api/v1/classify \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description":"stent farmacológico coronário 3.0 x 18 mm"}'
```

---

## 🧠 Serviços de IA (3 endpoints, operações distintas)

| Endpoint | Operação de IA | O que faz |
|---|---|---|
| `POST /api/v1/classify` | **NLP / extração + classificação** | Estrutura uma descrição livre em item OPME + classe taxonômica, com atributos, evidências e confiança. |
| `POST /api/v1/benchmark` | **Análise / estatística** | Calcula mediana, p25/p75, dispersão (CV), outliers (IQR) e economia potencial vs. mercado. |
| `POST /api/v1/comparability` | **Decisão / similaridade** | Decide se dois itens são equivalentes para benchmark de preço. |

Endpoints de apoio: `GET /api/v1/health`, `GET /api/v1/taxonomy`, `POST /api/v1/auth/token`.

### Exemplo — classificação

Request:
```json
{ "description": "Placa bloqueada distal rádio volar 2.4 mm titânio 6 furos, estéril, ref XZ-244, fabricante OrthoMed" }
```
Response (resumo):
```json
{
  "canonical_name": "Placa bloqueada distal rádio volar 2.4mm 6 furos titânio",
  "specialty": "Ortopedia",
  "taxonomy_path": "ORTOPEDIA > PLACAS > PLACA BLOQUEADA DISTAL RÁDIO VOLAR",
  "material": "titânio", "sterile": true, "reference_code": "XZ-244",
  "manufacturer": "OrthoMed", "dimensions": {"size_mm": 2.4, "holes": 6},
  "decision": "REVIEW", "confidence": 0.43,
  "evidence": [ {"field":"material","text":"titanio"}, ... ],
  "engine": "regras+similaridade"
}
```

### Exemplo — benchmark
```json
{ "description": "stent farmacológico coronário 3.0 x 18 mm", "reference_price": 7000 }
```
Retorna estatísticas, `by_supplier`, `by_region`, `outliers` e `saving_opportunity`
(no exemplo: ~35% acima da mediana de mercado).

---

## 🏗️ Como funciona (pipeline híbrido)

```
descrição livre
   │
   ▼
[1] Regras determinísticas  → material, dimensões, esterilidade, ref, fabricante (+ evidências)
   │
   ▼
[2] Similaridade textual    → recupera candidatos da taxonomia mestre (Jaccard + sequência)
   │
   ▼
[3] Decisão por limiar      → MATCH / REVIEW / NO_MATCH + score de confiança
   │
   ▼
[4] (opcional) LLM Claude   → refina nome canônico/atributos — com fallback automático
```

O LLM **nunca decide sozinho** e **nunca quebra a API**: sem chave, sem lib ou em caso de
erro, o sistema segue com regras + similaridade. Isso espelha a boa prática de
*human-in-the-loop* e classificação assistida descrita no blueprint da Atlas Health.

---

## ✅ Requisitos da disciplina — onde cada um está

| Critério UFG | Implementação |
|---|---|
| **≥ 2 serviços de IA distintos** | 3 endpoints: classificação (NLP), benchmark (analítico), comparabilidade (decisão). |
| **Validação de dados** | Schemas Pydantic v2 (`app/schemas.py`) com limites e tipos → 422 padronizado. |
| **Tratamento de erros** | Handlers centralizados + envelope único (`app/errors.py`). |
| **Logs** | JSON estruturado + `request_id` + log de acesso com latência (`app/logging_config.py`). |
| **Segurança** | JWT (PyJWT), senhas com PBKDF2, rate limiting (`app/security.py`, `app/api/deps.py`). |
| **Versionamento** | Prefixo `/api/v1` + versão no health (`app/main.py`). |
| **Documentação** | OpenAPI automático (`/docs`, `/redoc`) + este README + roteiro executivo. |
| **Executa em outra máquina** | Apenas `pip install -r requirements.txt`; SQLite + seed automático; sem serviços externos. |

---

## 🧪 Testes

```bash
pip install -r requirements-dev.txt
pytest
```
21 testes cobrindo cenários válidos e inválidos (auth, classificação, benchmark,
comparabilidade, validação, health).

---

## 📁 Estrutura

```
opme-intelligence-api/
├── app/
│   ├── main.py            # FastAPI: lifespan, middleware, versionamento
│   ├── config.py          # settings (12-factor)
│   ├── logging_config.py  # logs JSON + request_id
│   ├── database.py        # SQLite (schema + seed automático)
│   ├── security.py        # JWT + hashing PBKDF2
│   ├── schemas.py         # contratos Pydantic (validação)
│   ├── errors.py          # exceções + handlers
│   ├── ai/                # extractor, classifier, benchmark, comparability, llm
│   └── api/v1/            # rotas versionadas
├── data/seed_opme.py      # taxonomia + observações de preço sintéticas
├── tests/                 # suíte pytest
├── docs/                  # ROTEIRO_EXECUTIVO.md + ARQUITETURA.md
├── requirements.txt
└── .env.example
```

---

## 🤖 Ativando o LLM (opcional)

1. `pip install anthropic`
2. No `.env`, defina `ANTHROPIC_API_KEY=...`
3. Reinicie a API. A classificação passa a usar `engine: "regras+similaridade+llm"`.

Sem essas etapas, tudo continua funcionando offline.

---

## 📜 Licença
MIT.
