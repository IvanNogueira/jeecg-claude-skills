---
name: jeecg
description: >-
  Dispatcher unificado para todas as tarefas JeecgBoot. Use para qualquer pedido relacionado a JeecgBoot,
  incluindo: gerar código CRUD, gerar código, criar módulo, nova funcionalidade, nova entidade, criar tabela,
  adicionar campo, acrescentar campo, incluir campo, novo campo, alterar campo, modificar campo, remover campo, excluir campo;
  formulário online, cgform, criar tabela online, formulário metadado, formulário de baixo código, configurar tabela;
  relatório online, cgreport, relatório SQL, criar relatório, gerar relatório, novo relatório;
  gráfico online, graphreport, visualização de dados, criar gráfico, gerar gráfico, gráfico de barras, gráfico de linhas, gráfico de pizza;
  designer de formulário, desform, formulário por arrastar e soltar, formulário visual, formulário OA,
  criar solicitação de aprovação, pedido de férias, formulário com fluxo;
  BPMN, Flowable, fluxo de trabalho, processo de aprovação, criar fluxo, gerar fluxo, desenhar fluxo, nós de aprovação;
  JiMu Report, jimureport, relatório Excel, relatório de impressão, relatório agrupado, preenchimento de dados;
  tela grande, painel de monitoramento, mural de dados, visualização em tela cheia;
  dashboard, painel de indicadores, painel de dados, quadro de KPIs;
  papéis, usuários, departamentos, cargos, dicionário de dados, dados mestres,
  consultar papéis, consultar usuários, consultar dicionário, criar dicionário;
  MCP, marketplace, plugin MCP, LobeHub, instalar servidor MCP.
---

# JeecgBoot — Dispatcher de Skills

Este skill identifica automaticamente qual sub-skill usar e delega o fluxo para ela.

## Passo 1 — Identificar a sub-skill

Com base na intenção do usuário, selecione a sub-skill na tabela abaixo:

| Intenção / Palavras-chave | Sub-skill |
|---------------------------|-----------|
| Gerar código CRUD, novo módulo, adicionar/remover/alterar campo em módulo existente, nova entidade Java | `jeecg-codegen` |
| Formulário online (cgform), criar/editar tabela online, formulário metadado, controles online, aprimoramento JS/Java/SQL no cgform | `jeecg-onlform` |
| Relatório online (cgreport), relatório SQL, listagem de dados baseada em SQL | `jeecg-onlreport` |
| Gráfico online (graphreport), visualização de dados, barras, linhas, pizza, combinado | `jeecg-onlchart` |
| Designer de formulário (desform), arrastar campos, formulário visual, OA com aprovação, criar fluxo + formulário | `jeecg-desform` |
| BPMN, Flowable, fluxo de trabalho, processo de aprovação, nós de aprovação | `jeecg-bpmn` |
| JiMu Report, relatório Excel, impressão, agrupamento, relatório de dados complexo | `jimureport` |
| Tela grande, painel de monitoramento, mural de dados, posicionamento absoluto, fundo escuro | `jimubi-bigscreen` |
| Dashboard, painel de indicadores, painel de dados do dia a dia, grade de 24 colunas, fundo claro | `jimubi-dashboard` |
| Papéis, usuários, departamentos, dicionário de dados, dados mestres, consulta/criação de entidades do sistema | `jeecg-system` |
| MCP, marketplace, plugin MCP, LobeHub, instalar servidor MCP | `lobehub-mcp` |
| Fluxo de IA, AI flow, orquestração de agentes/LLM, nós de IA | `jeecg-aiflow` |
| Geração de código via templates Freemarker, geração em lote/paralela, uniapp | `jeecg-codegen-new` |
| Utilitários de desenvolvimento, depuração e apoio ao ambiente JeecgBoot | `jeecg-dev` |

> Se o pedido combinar múltiplas áreas (ex.: criar módulo CRUD + associar fluxo de aprovação), identifique a skill principal e mencione que uma segunda skill será usada em seguida.

## Passo 2 — Carregar a sub-skill

Invoque a sub-skill identificada com a ferramenta **Skill**, passando o nome exato
da tabela acima (ex.: `jeecg-codegen`). Isso funciona tanto na instalação como
plugin quanto em `~/.claude/skills/`.

Se a sub-skill não aparecer na lista de skills disponíveis, localize o `SKILL.md`
dela com Glob (`**/skills/{sub-skill}/SKILL.md`) e carregue com Read.

## Passo 3 — Executar

Siga **exatamente** o fluxo descrito na sub-skill carregada: pré-condições, passos de interação, scripts Python, validações, saídas esperadas.

Não omita etapas do fluxo da sub-skill. O dispatcher apenas identifica e delega — toda a lógica de execução está na sub-skill.
