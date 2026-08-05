#!/usr/bin/env bash
# Sincroniza as skills oficiais de github.com/jeecgboot/skills preservando as customizações locais.
#
#   - Substitui as skills que vêm do upstream pela versão nova.
#   - PRESERVA integralmente as skills em OWN_SKILLS (não existem no upstream).
#   - Reaplica o patch do bloco MCP no jeecg-codegen.
#   - Sanitiza tokens/segredos/IPs internos.
#
# Uso: ./scripts/sync-upstream.sh

set -euo pipefail

UPSTREAM_REPO="${UPSTREAM_REPO:-https://github.com/jeecgboot/skills}"
BRANCH="${BRANCH:-main}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"

# Skills próprias — NUNCA sobrescritas pelo upstream.
OWN_SKILLS=(jeecg lobehub-mcp)

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "==> Clonando $UPSTREAM_REPO ($BRANCH)..."
git clone --depth 1 --branch "$BRANCH" "$UPSTREAM_REPO" "$TMP/up" --quiet
UPSTREAM_SHA="$(git -C "$TMP/up" rev-parse HEAD)"
echo "    upstream HEAD: $UPSTREAM_SHA"

is_own() {
  local n="$1"
  for o in "${OWN_SKILLS[@]}"; do [[ "$o" == "$n" ]] && return 0; done
  return 1
}

echo "==> Aplicando skills do upstream..."
mkdir -p "$SKILLS_DIR"
for dir in "$TMP/up"/*/; do
  name="$(basename "$dir")"
  [[ "$name" == ".git" ]] && continue
  if is_own "$name"; then
    echo "    [skip] $name (skill própria)"
    continue
  fi
  rm -rf "$SKILLS_DIR/$name"
  cp -R "$dir" "$SKILLS_DIR/$name"
  find "$SKILLS_DIR/$name" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
  find "$SKILLS_DIR/$name" -name '*.pyc' -delete 2>/dev/null || true
  echo "    [ok]   $name"
done

for o in "${OWN_SKILLS[@]}"; do
  [[ -d "$SKILLS_DIR/$o" ]] && echo "    [keep] $o (preservada)"
done

# Reaplica o bloco MCP no jeecg-codegen, se o upstream não o tiver.
CODEGEN="$SKILLS_DIR/jeecg-codegen/SKILL.md"
if [[ -f "$CODEGEN" ]] && ! grep -q 'jeecg-mcp' "$CODEGEN"; then
  echo "==> Reaplicando bloco MCP em jeecg-codegen..."
  python3 - "$CODEGEN" <<'PY'
import sys, io

path = sys.argv[1]
block = '''
## MCP `jeecg-mcp`（可选 / opcional）

本 skill 可选择通过 `jeecg-mcp` MCP server 生成模块（工具：`generateJeecgModule`）。
配置示例 — 请将路径替换为你本地的 build：

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

> 安装与发现 MCP server 见 `lobehub-mcp` skill。
'''
# Remove o \n final do literal: sem isso o join abaixo produziria uma linha em
# branco a mais que a versão PowerShell, deixando o repo eternamente "sujo".
block = block.rstrip('\n')

lines = io.open(path, encoding='utf-8').read().split('\n')

# fim do frontmatter YAML (segundo '---')
fm_end, seen = -1, 0
for i, l in enumerate(lines):
    if l.strip() == '---':
        seen += 1
        if seen == 2:
            fm_end = i
            break

# insere após o parágrafo que segue o primeiro título H1
insert_at = len(lines)
for i in range(max(fm_end, 0), len(lines)):
    if lines[i].startswith('# '):
        insert_at = i + 1
        while insert_at < len(lines) and lines[insert_at].strip() != '' and not lines[insert_at].startswith('## '):
            insert_at += 1
        break

out = lines[:insert_at] + [block] + lines[insert_at:]
io.open(path, 'w', encoding='utf-8', newline='\n').write('\n'.join(out))
PY
fi

echo "==> Sanitizando segredos e caminhos locais..."
find "$SKILLS_DIR" -type f \
  \( -name '*.md' -o -name '*.py' -o -name '*.json' -o -name '*.ts' \
     -o -name '*.ftl' -o -name '*.txt' -o -name '*.yml' -o -name '*.yaml' \) -print0 |
while IFS= read -r -d '' f; do
  sed -i \
    -e 's/f5cf6d9e-3a62-4f0f-a235-e6d7c21b240b/<X-Access-Token>/g' \
    -e 's/dd05f1c54d63749eda95f9fa6d49v442a/<SIGNATURE_SECRET>/g' \
    -e 's/192\.168\.1\.6:8085/localhost:8080/g' \
    -e 's/192\.168\.[0-9]\+\.[0-9]\+/localhost/g' \
    -e 's#C:/Users/25067/\.claude/skills#~/.claude/skills#g' \
    -e 's#C:/Users/zhang/\.claude/skills#~/.claude/skills#g' \
    -e 's#G:\\idea_cache\\\.claude\\skills#~/.claude/skills#g' \
    -e 's#/home/double-check/Projetos/jeecg-mcp/dist/index\.js#<CAMINHO_ABSOLUTO>/jeecg-mcp/dist/index.js#g' \
    "$f"
done

# Sem timestamp de propósito — ele mudaria a cada execução e faria a Action abrir
# PR todo dia mesmo sem novidade no upstream. Formato idêntico ao sync-upstream.ps1.
cat > "$REPO_ROOT/UPSTREAM.json" <<EOF
{
  "upstream": "$UPSTREAM_REPO",
  "branch": "$BRANCH",
  "commit": "$UPSTREAM_SHA",
  "ownSkills": [$(printf '"%s",' "${OWN_SKILLS[@]}" | sed 's/,$//')]
}
EOF

echo ""
echo "==> Sync concluído. Revise com 'git diff' antes de commitar."
