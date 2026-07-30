---
name: lobehub-mcp
description: "Descobrir, instalar e configurar MCP servers do LobeHub MCP Marketplace. Use quando: precisar adicionar um novo servidor MCP ao projeto; buscar plugins MCP disponíveis; configurar yt-boot-jeecg-mcp ou outro plugin MCP via CLI do LobeHub; registrar credenciais no marketplace."
argument-hint: "Nome do plugin MCP a instalar (ex: yt-boot-jeecg-mcp) ou palavra-chave de busca"
---

# LobeHub MCP Marketplace — Setup & Install

Workflow para descobrir e configurar MCP servers do [LobeHub MCP Marketplace](https://lobehub.com/mcp) neste projeto JeecgBoot.

## Pré-requisitos

- Node.js instalado (`node --version`)
- Credenciais do LobeHub criadas em `~/.lobehub-market/credentials.json`

Se as credenciais ainda não existem:

```bash
npx -y @lobehub/market-cli register \
  --name "github-copilot" \
  --description "GitHub Copilot agent in VS Code" \
  --source "github-copilot"
```

## Procedimento

### 1. Buscar plugins disponíveis

```bash
npx -y @lobehub/market-cli mcp search --q "KEYWORD"
# Exemplo: --q "jeecg" ou --q "database sql"
# Ordenar por mais instalados: --sort installCount
# Ordenar por melhor avaliação: --sort ratingAverage
```

### 2. Ver detalhes do plugin

```bash
npx -y @lobehub/market-cli mcp view <identifier>
# Com comentários de outros agentes:
npx -y @lobehub/market-cli mcp view <identifier> --comments
```

### 3. Configurar no projeto VS Code

Editar (ou criar) `.vscode/mcp.json` na raiz do projeto:

```json
{
    "servers": {
        "<identifier>": {
            "type": "stdio",
            "command": "node",
            "args": ["/caminho/local/dist/index.js"]
        }
    }
}
```

> **Alternativa via npx** (sem clone local):
> ```json
> {
>     "servers": {
>         "<identifier>": {
>             "type": "stdio",
>             "command": "npx",
>             "args": ["-y", "<identifier>"]
>         }
>     }
> }
> ```

### 4. Verificar funcionamento

Reiniciar o servidor MCP no VS Code (`Ctrl+Shift+P` → "MCP: Restart Server") e confirmar que as ferramentas estão disponíveis.

### 5. Avaliar o plugin (opcional)

```bash
# Avaliar
npx -y @lobehub/market-cli mcp rate <identifier> --score <1-5>

# Comentar com avaliação
npx -y @lobehub/market-cli mcp comment <identifier> \
  -c "Descrição da experiência" --rating <1-5>
```

---

## Plugin yt-boot-jeecg-mcp (já configurado neste projeto)

| Campo       | Valor                                      |
|-------------|--------------------------------------------|
| Identifier  | `yt-boot-jeecg-mcp`                        |
| Versão      | 1.0.0                                      |
| Autor       | yt-boot                                    |
| GitHub      | https://github.com/yt-boot/jeecg-mcp       |
| Descrição   | Mastra MCP Server para geração de código JeecgBoot |

Config atual em [.vscode/mcp.json](../../.vscode/mcp.json) — usa o build local em `<CAMINHO_ABSOLUTO>/jeecg-mcp/dist/index.js`.

A ferramenta exposta pelo servidor é `generateJeecgModule`. Ver uso em [copilot-instructions.md](../../.github/copilot-instructions.md#regras-do-mcp-generatejeecgmodule).
