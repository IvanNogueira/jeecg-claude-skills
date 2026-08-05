# JeecgBoot Claude Skills

Suite de skills para [Claude Code](https://claude.com/claude-code) que automatiza o
desenvolvimento em **[JeecgBoot](https://github.com/jeecgboot/JeecgBoot)** — geração
de CRUD, formulários, relatórios, fluxos BPMN, dashboards e telas de BI.

Empacota as **13 skills oficiais** de [`jeecgboot/skills`](https://github.com/jeecgboot/skills)
(sincronizadas automaticamente) mais **2 skills próprias**, com um único ponto de
entrada: **`/jeecg`**.

## Instalação

```
/plugin marketplace add IvanNogueira/jeecg-claude-skills
/plugin install jeecg-claude-skills
```

> Troque `IvanNogueira` pelo owner do repositório caso tenha feito um fork.

<details>
<summary>Instalação manual (sem plugin)</summary>

```bash
git clone https://github.com/IvanNogueira/jeecg-claude-skills.git
cp -r jeecg-claude-skills/skills/* ~/.claude/skills/
```

</details>

## Uso

Descreva a tarefa — o dispatcher `/jeecg` identifica a sub-skill correta e delega:

```
/jeecg criar um módulo de cadastro de fornecedores com CNPJ, razão social e status
/jeecg adicionar um campo data_vencimento na tabela de contratos
/jeecg fazer um relatório de vendas por região
/jeecg criar um fluxo de aprovação: solicitante → gerente → financeiro
/jeecg montar um dashboard com os KPIs de faturamento
```

Também é possível chamar uma sub-skill diretamente, ex.: `/jeecg-codegen`.

## Skills incluídas

### Próprias

| Skill | Função |
|---|---|
| `jeecg` | **Dispatcher** — identifica a intenção e delega para a sub-skill correta |
| `lobehub-mcp` | Descoberta e instalação de MCP servers via LobeHub Marketplace |

### Oficiais (sincronizadas de `jeecgboot/skills`)

| Skill | Função |
|---|---|
| `jeecg-codegen` | Geração de CRUD completo (back-end Java + front-end Vue3 + SQL de menu) |
| `jeecg-codegen-new` | Geração via templates Freemarker, modo paralelo/lote, uniapp. **Manual:** declara `disable-model-invocation`, use `/jeecg-codegen-new` |
| `jeecg-aiflow` | Fluxos de IA — orquestração de agentes e nós de LLM |
| `jeecg-onlform` | Online Form (`cgform`) — tabelas metadata-driven, controles, JS/Java/SQL enhance |
| `jeecg-onlreport` | Online Report (`cgreport`) — relatórios SQL-driven |
| `jeecg-onlchart` | Online Chart (`graphreport`) — barra, linha, pizza, combinado |
| `jeecg-desform` | Form Designer — formulários drag-and-drop, apps OA com aprovação |
| `jeecg-bpmn` | BPMN / Flowable — processos, contra-assinatura, subprocessos, gateways |
| `jeecg-system` | Dados mestres — usuários, papéis, departamentos, dicionários |
| `jeecg-dev` | Padrões de código JeecgBoot (`开发规范`) — comentários de rastreio, nomenclatura, convenções de API. **Manual:** use `/jeecg-dev` |
| `jimureport` | JiMu Report — relatórios Excel, impressão, agrupamento, preenchimento |
| `jimubi-bigscreen` | Big screens — visualização full-screen, posicionamento absoluto |
| `jimubi-dashboard` | Dashboards / kanban — grid de 24 colunas, painéis de KPI |

## Atualização automática

As skills oficiais são sincronizadas de `jeecgboot/skills` **sem perder as
customizações locais**:

- **GitHub Action diária** (`.github/workflows/sync-upstream.yml`, 06:00 UTC) — abre
  um PR quando há novidades no upstream. Pode ser disparada manualmente em
  *Actions → Sync upstream skills → Run workflow*.
- **Script manual:**

  ```powershell
  ./scripts/sync-upstream.ps1          # Windows
  ./scripts/sync-upstream.sh           # Linux/macOS
  ```

O sync preserva integralmente `jeecg` e `lobehub-mcp`, reaplica o bloco de config
do MCP em `jeecg-codegen` e roda a sanitização de segredos. A procedência do último
sync fica em [UPSTREAM.json](UPSTREAM.json).

## Configuração

As skills interagem com uma instância JeecgBoot via API REST. Forneça no chat (ou
configure no seu ambiente):

- **URL base** — ex.: `http://localhost:8080/jeecg-boot`
- **`X-Access-Token`** — obtido após login (F12 → Network → Request Headers)
- **`SIGNATURE_SECRET`** — de `window._CONFIG.signatureSecret` no front-end;
  necessário apenas para as APIs de datasource do JiMu/BI

Todos os exemplos usam placeholders (`<X-Access-Token>`, `<SIGNATURE_SECRET>`,
`localhost:8080`) — **nenhuma credencial real está versionada aqui**, e o sync
reaplica essa sanitização a cada execução. Não commite as suas.

### MCP `jeecg-mcp` (opcional)

A skill `jeecg-codegen` pode usar o MCP server `jeecg-mcp` (ferramenta
`generateJeecgModule`). Aponte para o seu build local:

```json
{
  "mcpServers": {
    "jeecg-mcp": {
      "command": "node",
      "args": ["<CAMINHO_ABSOLUTO>/jeecg-mcp/dist/index.js"]
    }
  }
}
```

## Requisitos

- Claude Code
- Uma instância JeecgBoot acessível
- Python 3.11+ com `requests` (usado pelos scripts de automação das skills)

## Licença e créditos

As skills em `skills/` — exceto `jeecg` e `lobehub-mcp` — são derivadas de
[jeecgboot/skills](https://github.com/jeecgboot/skills), licenciadas sob
**Apache License 2.0**. Veja [LICENSE](LICENSE) e [NOTICE](NOTICE).
