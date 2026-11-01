# ATLAS · Ferramentas (link na bio)

Site estático com o hub de link na bio, três calculadoras gratuitas e a página do diagnóstico
de compras de OPME, todos captando leads para a ATLAS - Gestão em Saúde. Sem build, sem cookies, sem rastreadores.

| Página | Caminho | Atalho | Formulário (Netlify Forms) |
|---|---|---|---|
| Hub de link na bio | `/` | — | — |
| Calculadora de glosas | `/glosas/` | `/g` | `calc-glosas` |
| Agenda ociosa e faltas | `/agenda/` | `/a` | `calc-agenda` |
| Materiais e OPME | `/materiais/` (aba compras: `/materiais/#compras`) | `/m` | `calc-materiais` |
| Diagnóstico de compras de OPME | `/opme/` | `/o` | `diagnostico-opme` |

O Raio-X, o Mini-Diagnóstico e o playbook continuam no site principal
(`atlasgestaosaude.com.br`) e são linkados a partir do hub.

## Como cada lead chega

Cada envio grava no Netlify Forms do projeto `atlas-ferramentas`:

- `nome`, `contato` (WhatsApp ou e-mail), `instituicao`, `cidade`, `papel`
- `resumo`: os números que a pessoa digitou e o resultado calculado, em texto
- `origem`: vem do parâmetro `?o=` do link (ex.: `?o=ig-glosa`). Sem parâmetro, fica `direto`
- consentimentos LGPD (tratamento e transferência internacional), no mesmo texto do site principal

Para receber por e-mail: Netlify → projeto `atlas-ferramentas` → Forms → Form notifications → Add notification → Email.

## Palavras-chave para "comente e receba" (Instagram)

Use estes links na automação de DM (ManyChat ou similar). O `?o=` identifica o post de origem.

| Palavra no comentário | Link enviado na DM |
|---|---|
| GLOSA | `https://atlas-ferramentas.netlify.app/g?o=ig-glosa` |
| AGENDA | `https://atlas-ferramentas.netlify.app/a?o=ig-agenda` |
| FALTA | `https://atlas-ferramentas.netlify.app/a?o=ig-falta` |
| MATERIAL | `https://atlas-ferramentas.netlify.app/m?o=ig-material` |
| OPME | `https://atlas-ferramentas.netlify.app/o?o=ig-opme` |
| COMPRA | `https://atlas-ferramentas.netlify.app/materiais/?o=ig-compra#compras` |
| RAIOX | `https://atlas-ferramentas.netlify.app/?o=ig-raiox` |

Link da bio: `https://atlas-ferramentas.netlify.app/?o=ig-bio`.
Troque o domínio quando apontar `ferramentas.atlasgestaosaude.com.br` para o projeto.

## OPME Intelligence: como é apresentado

A página `/opme/` apresenta o OPME Intelligence como **ferramenta própria usada dentro do diagnóstico**,
não como software à venda (coerente com "não vendemos software" do site principal). O texto promete só o
que a ferramenta faz hoje com os dados do cliente: padronizar descrições, decidir equivalência, medir
mediana, dispersão e compras fora da curva, e priorizar. Os preços de mercado do banco da API são
sintéticos (seed de demonstração), por isso a página não promete benchmark contra o mercado:
referência externa só entra com fonte e data declaradas.

## Princípios aplicados (os mesmos do site principal)

- Cada número exibido declara a natureza: **dado fornecido**, **cálculo** ou **estimativa**.
- Nenhuma referência de mercado sem fonte: as calculadoras usam só os números informados.
- As leituras automáticas são escritas como **hipótese a testar**, nunca como diagnóstico.
- Nenhum dado de paciente é pedido.

## Publicar

Projeto Netlify: `atlas-ferramentas` (site id `39159e37-ff77-4b7e-9a4f-d7365d942e23`),
form detection já ativado. Publica a pasta inteira, sem comando de build.

- **Arrastar e soltar:** Netlify → atlas-ferramentas → Deploys → arraste esta pasta.
- **CLI:** `netlify deploy --prod --dir . --site 39159e37-ff77-4b7e-9a4f-d7365d942e23`
- **Git:** conecte o repositório no projeto com base directory `sites/atlas-ferramentas`.

## Testar localmente

```bash
cd sites/atlas-ferramentas && python3 -m http.server 8765
# abra http://127.0.0.1:8765/  (o envio do formulário só funciona publicado no Netlify)
```
