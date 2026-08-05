---
name: jeecg
description: >-
  Dispatcher para tarefas JeecgBoot e JimuReport — identifica a sub-skill correta e delega.
  Use para: gerar código CRUD, criar módulo, nova entidade, criar tabela,
  adicionar/alterar/remover campo (代码生成, 加字段, generate code);
  formulário online, cgform, tabela online, low-code (在线表单);
  relatório online, cgreport, relatório SQL (创建报表);
  gráfico online, barras, linhas, pizza (创建图表);
  designer de formulário, desform, arrastar e soltar, formulário OA,
  aprovação, férias, reembolso (表单设计器);
  BPMN, Flowable, workflow, fluxo e processo de aprovação (创建流程);
  fluxo de IA, AIFlow, orquestração de LLM (AI编排);
  JiMu Report, relatório Excel, impressão, agrupado, preenchimento (积木报表);
  tela grande, big screen, painel de monitoramento (大屏);
  dashboard, painel de indicadores, KPIs, kanban (仪表盘);
  papéis, usuários, departamentos, dicionário, dados mestres (查询字典);
  MCP, LobeHub, instalar servidor MCP.
---

# JeecgBoot — Dispatcher de Skills

Este skill **não executa** tarefas: ele identifica a sub-skill correta, coleta o que
falta para ela rodar, e delega. Toda a lógica de execução vive na sub-skill.

## Passo 0 — Se o pedido for "atualizar as skills"

Só quando o usuário pedir explicitamente para atualizar/sincronizar as skills
(ex.: "atualiza as skills do jeecg", "sincroniza com o upstream"). **Nunca** rode isso
por conta própria ao atender um pedido normal.

1. Localize o script de sync com Glob: `**/scripts/sync-upstream.ps1` (ou `.sh` em
   Linux/macOS). Ele fica na raiz do repositório `jeecg-claude-skills`.
2. Execute-o. Ele baixa as skills oficiais de `jeecgboot/skills`, **preserva** as
   skills próprias (`jeecg`, `lobehub-mcp`), reaplica o bloco de config do
   `jeecg-mcp` e sanitiza segredos.
3. Mostre o resumo ao usuário e lembre que as skills novas só entram em vigor em uma
   **sessão nova**.

Se o script não for encontrado (caso de instalação via plugin sem o repo local),
oriente: `/plugin update` para o plugin, ou clonar o repo para rodar o sync.

## Passo 1 — Pré-requisitos de conexão

Quase todas as sub-skills falam com uma instância JeecgBoot via API REST. Se o pedido
implicar chamada de API e o usuário ainda não informou, pergunte **antes** de delegar:

> Preciso da URL base do JeecgBoot (ex.: `http://localhost:8080/jeecg-boot`) e do
> `X-Access-Token` (F12 → Network → qualquer request → Request Headers).

Só o `SIGNATURE_SECRET` (de `window._CONFIG.signatureSecret`) é adicional, e apenas
para as APIs de datasource do JiMu/BI.

Não invente endpoints nem tokens. Se faltar dado, pergunte.

## Passo 2 — Identificar a sub-skill

| Intenção / sinais no pedido | Sub-skill |
|---|---|
| Gerar CRUD completo como **código-fonte no repositório** (Java + Vue3 + SQL de menu), nova entidade, adicionar/alterar/remover campo em módulo já gerado | `jeecg-codegen` |
| **Online Form** (`cgform`) — criar/editar tabela e formulário por metadado, sem gerar código; single/master-detail/tree, 26 controles, JS/Java/SQL enhance, permissões, CRUD de dados | `jeecg-onlform` |
| **Online Report** (`cgreport`) — listagem/relatório somente-leitura dirigido por SQL | `jeecg-onlreport` |
| **Online Chart** (`graphreport`) — barra, linha, pizza, combinado | `jeecg-onlchart` |
| **Form Designer** (`desform`) — formulário arrastar-e-soltar, app OA de aprovação (férias, reembolso, viagem), views PC/mobile | `jeecg-desform` |
| **BPMN / Flowable** — processo de aprovação, cadeia de aprovadores, gateways, contra-assinatura, subprocesso | `jeecg-bpmn` |
| **AIFlow** — orquestração de IA/LLM, fluxo de knowledge base, nós de modelo, debug/publicação de fluxo de IA | `jeecg-aiflow` |
| **Dados mestres** — usuários, papéis, departamentos, cargos, dicionários, tenants, datasources, tarefas agendadas | `jeecg-system` |
| **JiMu Report** (`积木报表`) — relatório tipo Excel, impressão, agrupamento, loop, preenchimento de dados | `jimureport` |
| **Big screen** (`大屏`) — tela cheia, posicionamento absoluto, fundo escuro, sala de monitoramento | `jimubi-bigscreen` |
| **Dashboard** (`仪表盘/看板`) — grade de 24 colunas, fundo claro, painel de KPIs do dia a dia | `jimubi-dashboard` |
| **MCP** — descobrir/instalar servidor MCP, LobeHub Marketplace | `lobehub-mcp` |

### Desambiguação — os erros mais comuns

Antes de delegar, resolva estas confusões. Em caso de dúvida real, **pergunte** em uma
frase em vez de escolher errado — refazer custa muito mais.

- **`jeecg-codegen` vs `jeecg-onlform`** — ambos "criam um cadastro". Decida pelo
  artefato: se o usuário quer **arquivos versionados no projeto** (Entity, Controller,
  `.vue`, Flyway SQL) → `jeecg-codegen`. Se quer a tabela/formulário **configurados no
  sistema em runtime**, sem tocar no código → `jeecg-onlform`. Sinais de codegen:
  "no meu projeto", "gerar código", "commitar", "Vue3". Sinais de onlform: "online",
  "low-code", "sem programar", "direto no sistema".
- **`jeecg-onlform` vs `jeecg-desform`** — `onlform` é dirigido por metadado de tabela
  (grid + CRUD). `desform` é o designer visual de arrastar-e-soltar, usado para
  formulários OA com aprovação. "Designer", "arrastar", "aprovação" → `desform`.
- **`jeecg-onlreport` vs `jimureport` vs `jeecg-onlchart`** — todos "mostram dados".
  Lista simples via SQL → `onlreport`. Layout de célula tipo Excel, impressão,
  agrupamento, preenchimento → `jimureport`. Gráfico → `onlchart`.
- **`jimubi-bigscreen` vs `jimubi-dashboard`** — sistemas de layout **diferentes e
  incompatíveis**. Tela cheia para projeção/monitoramento, fundo escuro, posição
  absoluta → `bigscreen`. Painel de trabalho em grade de 24 colunas, fundo claro →
  `dashboard`. Nunca use um no lugar do outro.
- **`jeecg-bpmn` vs `jeecg-aiflow`** — aprovação humana (gerente → RH) → `bpmn`.
  Orquestração de LLM/agentes/knowledge base → `aiflow`.

### Sub-skills de invocação manual

Estas **não devem ser invocadas automaticamente** — respeite o contrato delas:

| Skill | Por quê |
|---|---|
| `jeecg-dev` | Padrões de desenvolvimento JeecgBoot (`开发规范`). A própria description exige *manual only*. Só quando o usuário digitar `/jeecg-dev`. |
| `jeecg-codegen-new` | Gerador alternativo via templates Freemarker. Tem `disable-model-invocation: true`, ou seja, **não é invocável pelo modelo**. |

Se o pedido se beneficiaria de uma delas, **avise o usuário** em uma linha
("os padrões de código estão em `/jeecg-dev`, rode se quiser que eu os aplique")
em vez de tentar invocá-la.

## Passo 3 — Delegar

Invoque a sub-skill com a ferramenta **Skill**, passando o nome exato da tabela
(ex.: `jeecg-codegen`). Funciona tanto instalado como plugin quanto em
`~/.claude/skills/`.

Se a sub-skill não aparecer entre as skills disponíveis, localize o arquivo com Glob
(`**/skills/{sub-skill}/SKILL.md`) e carregue com Read.

### Pedidos que envolvem mais de uma sub-skill

Identifique a **principal**, delegue para ela primeiro e diga ao usuário qual virá em
seguida. Combinações frequentes:

| Pedido | Ordem |
|---|---|
| App OA completo (formulário + aprovação) | `jeecg-desform` → `jeecg-bpmn` |
| Módulo CRUD com fluxo de aprovação | `jeecg-codegen` → `jeecg-bpmn` |
| Tabela online + relatório/impressão | `jeecg-onlform` → `jimureport` |
| Qualquer coisa que dependa de papel, departamento ou dicionário | `jeecg-system` **primeiro** |

**Dados mestres seguem "先查后建" (consultar antes de criar):** papéis, usuários,
departamentos e dicionários devem ser consultados via `jeecg-system` antes de criar
duplicatas.

> Exceção do `jeecg-codegen`: naquele fluxo, **criar** dicionário vai para o Flyway SQL,
> não pela API — a sub-skill explica o motivo. Consultar continua pela API.

## Passo 4 — Executar

Siga **exatamente** o fluxo da sub-skill carregada: pré-condições, ordem dos passos,
scripts, validações e saídas esperadas. Não omita etapas e não substitua os scripts
dela por chamadas de API improvisadas.
