# hyperresearch neste repositório

Este projeto tem o [hyperresearch](https://github.com/jordan-gibbs/hyperresearch)
(v0.10.0) instalado como base de pesquisa dirigida por agente. Ele adiciona ao
repositório um *vault* de notas em markdown e o comando `/hyperresearch` do
Claude Code, que executa um pipeline de 16 passos com revisão adversarial e
proveniência completa das fontes.

O uso pretendido aqui é levantar e manter evidência de mercado para a camada de
inteligência OPME — regulação (ANVISA, ANS), tabelas de referência de preço,
literatura sobre variação de preço em materiais especiais — como notas
citáveis e versionadas, em vez de links soltos.

O hyperresearch é **ortogonal à API**: nada em `app/` depende dele, e a API
continua rodando 100% offline. Ele é ferramental de pesquisa, não runtime.

---

## Pré-requisito: o CLI precisa estar no PATH

Os arquivos gerados (`CLAUDE.md`, `.claude/agents/*.md`, `.hyperresearch/hook.js`)
invocam o binário pelo nome puro `hyperresearch`. Instale-o de uma destas formas:

```bash
# Opção A — no virtualenv do projeto (mesmo .venv do README)
source .venv/bin/activate
pip install hyperresearch

# Opção B — isolado, disponível em qualquer shell
pipx install hyperresearch
```

Requer **Python 3.11–3.13** (o 3.14 ainda não é suportado pelo hyperresearch —
note que a API em si roda em 3.14). Se o seu ambiente principal for 3.14, use a
opção B com um interpretador 3.13 ou anterior.

Confirme:

```bash
hyperresearch --version   # hyperresearch v0.10.0
hyperresearch status      # saúde do vault
hyperresearch lint        # deve reportar "Vault is healthy"
```

## O que está versionado

| Caminho | Conteúdo |
|---|---|
| `CLAUDE.md` | Bloco `<!-- hyperresearch:start -->` com as instruções de uso para o agente. |
| `.claude/skills/hyperresearch*/` | Skill de entrada (roteador) + 18 skills de passo do pipeline. |
| `.claude/agents/hyperresearch-*.md` | 16 subagentes (fetcher, críticos, sintetizador, patcher, cite-checker etc.). |
| `.claude/settings.json` | Hook `PreToolUse` que lembra o agente de consultar o vault antes de buscar na web. |
| `.hyperresearch/config.toml` | Configuração do vault (busca, fetch, ranking, recuperação open-access). |
| `.hyperresearch/hook.js` | Implementação do hook. |
| `research/notes/` | As notas de pesquisa — o material que vale a pena versionar. |

Ficam **fora** do versionamento (ver `.gitignore`): `.hyperresearch/hyperresearch.db`
(índice SQLite, recriado por `hyperresearch sync`), `research/runs/`, `research/temp/`,
`research/raw/`, `research/index/` e `research/assets/` — todos derivados ou volumosos.

## Uso

```
/hyperresearch <pergunta de pesquisa>
```

O passo 1 classifica a pergunta em `light` (~30-40 min, sem críticos) ou `full`
(pipeline completo com revisão adversarial); `dissertation` é opt-in por run. A
*scale gear* instalada é `full` (~55-80 fontes); `hyperresearch profile use premier`
sobe para ~100-130 fontes.

Comandos úteis fora do pipeline:

```bash
hyperresearch search "preço materiais especiais" --json   # busca full-text no vault
hyperresearch fetch "<url>" --tag opme --json             # busca uma página e vira nota
hyperresearch note list --status draft --json             # notas ainda não curadas
hyperresearch run status --json                           # posição do run mais recente
hyperresearch run resume --json                           # retoma um run interrompido
hyperresearch repair --json                               # reconstrói links e índices
```

## Configuração opcional

- **Unpaywall** — para recuperar versões open-access de artigos com paywall,
  preencha `contact_email` em `[scholar]` no `.hyperresearch/config.toml`. Sem
  isso, a recuperação ainda funciona pelo Europe PMC, que não exige chave.
- **Busca semântica** — `[embeddings] provider` está em `none`. Pode ser
  apontado para Voyage ou OpenAI se houver chave disponível.
- **Conteúdo com login** (portais de tabela de preço, notícias pagas) exige um
  perfil de navegador: `hyperresearch setup`.

## Rede

O `hyperresearch fetch` sobe um Chromium headless (via crawl4ai/patchright) e
precisa de saída HTTPS livre para os domínios pesquisados. Em ambientes com
proxy de egresso restritivo, o fetch falha com `ERR_TUNNEL_CONNECTION_FAILED`
mesmo com o binário e o vault corretos — nesse caso o problema é a política de
rede, não a instalação. Todo o restante (vault, busca, notas, índices, hook,
skills) funciona offline.
