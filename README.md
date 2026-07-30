# JeecgBoot Claude Skills

Suite de skills para [Claude Code](https://claude.com/claude-code) que automatiza o
desenvolvimento em **[JeecgBoot](https://github.com/jeecgboot/JeecgBoot)** — desde
geração de CRUD até relatórios, fluxos BPMN e dashboards de BI.

Tudo é acessível por um único ponto de entrada: **`/jeecg`**.

## Instalação

No Claude Code:

```
/plugin marketplace add ivan-wind/jeecg-claude-skills
/plugin install jeecg-claude-skills
```

> Troque `ivan-wind` pelo owner do repositório, caso tenha feito um fork.

<details>
<summary>Instalação manual (sem plugin)</summary>

```bash
git clone https://github.com/ivan-wind/jeecg-claude-skills.git
cp -r jeecg-claude-skills/skills/* ~/.claude/skills/
```

</details>

## Uso

Basta descrever a tarefa — o dispatcher `/jeecg` identifica a sub-skill correta e delega:

```
/jeecg criar um módulo de cadastro de fornecedores com CNPJ, razão social e status
/jeecg adicionar um campo data_vencimento na tabela de contratos
/jeecg fazer um relatório de vendas por região
/jeecg criar um fluxo de aprovação: solicitante → gerente → financeiro
/jeecg montar um dashboard com os KPIs de faturamento
```

Também é possível chamar uma sub-skill diretamente, ex.: `/jeecg-codegen`.

## Skills incluídas

| Skill | Função |
|---|---|
| `jeecg` | **Dispatcher** — identifica a intenção e delega para a sub-skill correta |
| `jeecg-codegen` | Geração de CRUD completo (back-end Java + front-end Vue), campos, entidades |
| `jeecg-onlform` | Online Form (`cgform`) — tabelas/formulários metadata-driven, 26 controles, JS/Java/SQL enhance, permissões |
| `jeecg-onlreport` | Online Report (`cgreport`) — relatórios SQL-driven |
| `jeecg-onlchart` | Online Chart (`graphreport`) — barra, linha, pizza, combinado |
| `jeecg-desform` | Form Designer — formulários drag-and-drop, apps OA com aprovação |
| `jeecg-bpmn` | BPMN / Flowable — desenho de processos e fluxos de aprovação |
| `jeecg-system` | Dados mestres — usuários, papéis, departamentos, dicionários, cargos |
| `jimureport` | JiMu Report — relatórios Excel, impressão, agrupamento, preenchimento |
| `jimubi-bigscreen` | Big screens — visualização full-screen, posicionamento absoluto |
| `jimubi-dashboard` | Dashboards / kanban — grid de 24 colunas, painéis de KPI |
| `lobehub-mcp` | Descoberta e instalação de MCP servers via LobeHub Marketplace |

## Configuração

As skills interagem com uma instância JeecgBoot via API REST. Antes de usar, você
precisa fornecer no chat (ou configurar no seu ambiente):

- **URL base** da sua instância — ex.: `http://localhost:8080/jeecg-boot`
- **`X-Access-Token`** — obtido após login na instância
- **`SIGNATURE_SECRET`** — disponível em `window._CONFIG.signatureSecret` no front-end,
  necessário apenas para as APIs de datasource do JiMu/BI

Todos os exemplos nas skills usam placeholders (`<X-Access-Token>`,
`<SIGNATURE_SECRET>`, `localhost:8080`) — **nenhuma credencial real está
versionada neste repositório**. Não commite as suas.

### MCP `jeecg-mcp` (opcional)

A skill `jeecg-codegen` pode usar o MCP server `jeecg-mcp` para gerar módulos.
Configure apontando para o seu build local:

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
- Python 3.11+ com `requests` (usado pelos scripts de automação de várias skills)

## Licença

MIT — veja [LICENSE](LICENSE).
