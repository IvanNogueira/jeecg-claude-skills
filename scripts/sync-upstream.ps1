<#
.SYNOPSIS
    Sincroniza as skills oficiais de github.com/jeecgboot/skills preservando as customizações locais.

.DESCRIPTION
    - Baixa o upstream oficial (jeecgboot/skills).
    - Substitui as skills que vêm do upstream pela versão nova.
    - PRESERVA integralmente as skills listadas em $OwnSkills (não existem no upstream).
    - Reaplica os patches locais (bloco MCP no jeecg-codegen).
    - Sanitiza tokens/segredos/IPs internos antes de deixar qualquer coisa versionada.

.EXAMPLE
    ./scripts/sync-upstream.ps1
    ./scripts/sync-upstream.ps1 -WhatIf
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$UpstreamRepo = 'https://github.com/jeecgboot/skills',
    [string]$Branch = 'main'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$skillsDir = Join-Path $repoRoot 'skills'

# robocopy sinaliza sucesso com exit codes 0-7 (8+ = falha real). Wrapper para
# que esses códigos não sejam tratados como erro pelo chamador.
function Invoke-Robocopy {
    param([string]$Source, [string]$Destination)
    & robocopy $Source $Destination /E /XD '__pycache__' /XF '*.pyc' /NFL /NDL /NJH /NJS /R:1 /W:1 | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy falhou ($Source -> $Destination), exit $LASTEXITCODE" }
    $global:LASTEXITCODE = 0
}

# Skills próprias — NUNCA sobrescritas pelo upstream.
$OwnSkills = @('jeecg', 'lobehub-mcp')

$tmp = Join-Path ([System.IO.Path]::GetTempPath()) "jeecg-upstream-$(Get-Random)"

try {
    Write-Host "==> Clonando $UpstreamRepo ($Branch)..." -ForegroundColor Cyan
    # git escreve o progresso em stderr; sem isso o $ErrorActionPreference='Stop'
    # transformaria a saída normal do clone em erro fatal.
    & git clone --depth 1 --branch $Branch --quiet $UpstreamRepo $tmp 2>$null
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path (Join-Path $tmp '.git'))) {
        throw "Falha ao clonar o upstream (exit $LASTEXITCODE)."
    }

    $upstreamSha = (git -C $tmp rev-parse HEAD).Trim()
    Write-Host "    upstream HEAD: $upstreamSha"

    # --- 1. Backup das skills próprias -------------------------------------
    $backup = Join-Path $tmp '__own__'
    New-Item -ItemType Directory -Force -Path $backup | Out-Null
    foreach ($own in $OwnSkills) {
        $src = Join-Path $skillsDir $own
        if (Test-Path $src) {
            if ($PSCmdlet.ShouldProcess($own, 'backup skill própria')) {
                Invoke-Robocopy -Source $src -Destination (Join-Path $backup $own)
            }
        }
    }

    # --- 2. Substitui as skills do upstream --------------------------------
    # robocopy é usado porque nomes de template Freemarker contêm ${...},
    # que o Copy-Item do PowerShell interpreta e quebra.
    Write-Host "==> Aplicando skills do upstream..." -ForegroundColor Cyan
    Get-ChildItem $tmp -Directory -Exclude '.git', '__own__' | ForEach-Object {
        $name = $_.Name
        if ($OwnSkills -contains $name) {
            Write-Host "    [skip] $name (skill própria)" -ForegroundColor Yellow
            return
        }
        $target = Join-Path $skillsDir $name
        if ($PSCmdlet.ShouldProcess($name, 'sincronizar do upstream')) {
            if (Test-Path $target) { Remove-Item $target -Recurse -Force }
            Invoke-Robocopy -Source $_.FullName -Destination $target
        }
        Write-Host "    [ok]   $name"
    }

    # --- 3. Restaura as skills próprias ------------------------------------
    foreach ($own in $OwnSkills) {
        $src = Join-Path $backup $own
        if (Test-Path $src) {
            $target = Join-Path $skillsDir $own
            if ($PSCmdlet.ShouldProcess($own, 'restaurar skill própria')) {
                if (Test-Path $target) { Remove-Item $target -Recurse -Force }
                Invoke-Robocopy -Source $src -Destination $target
            }
            Write-Host "    [keep] $own (preservada)" -ForegroundColor Green
        }
    }

    if (-not $PSCmdlet.ShouldProcess('pacote', 'aplicar patches e sanitizar')) { return }

    # --- 4. Reaplica o patch do bloco MCP no jeecg-codegen -----------------
    $codegen = Join-Path $skillsDir 'jeecg-codegen\SKILL.md'
    if ((Test-Path $codegen) -and -not (Select-String -Path $codegen -Pattern 'jeecg-mcp' -Quiet)) {
        Write-Host "==> Reaplicando bloco MCP em jeecg-codegen..." -ForegroundColor Cyan
        $mcpBlock = @'

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
'@
        $lines = [System.IO.File]::ReadAllText($codegen) -split "`r?`n"
        # Insere após o fim do frontmatter YAML (segundo '---') e o título H1 seguinte.
        $fmEnd = -1; $seen = 0
        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ($lines[$i].Trim() -eq '---') { $seen++; if ($seen -eq 2) { $fmEnd = $i; break } }
        }
        $insertAt = $lines.Count
        for ($i = [Math]::Max($fmEnd, 0); $i -lt $lines.Count; $i++) {
            if ($lines[$i] -match '^#\s') {
                $insertAt = $i + 1
                while ($insertAt -lt $lines.Count -and $lines[$insertAt].Trim() -ne '' -and $lines[$insertAt] -notmatch '^##\s') { $insertAt++ }
                break
            }
        }
        $out = @($lines[0..($insertAt - 1)]) + @($mcpBlock) + @($lines[$insertAt..($lines.Count - 1)])
        [System.IO.File]::WriteAllText($codegen, ($out -join "`n"), (New-Object System.Text.UTF8Encoding($false)))
    }

    # --- 5. Sanitização ----------------------------------------------------
    Write-Host "==> Sanitizando segredos e caminhos locais..." -ForegroundColor Cyan
    $exts = @('.md', '.py', '.json', '.ts', '.ftl', '.txt', '.yml', '.yaml')
    $script:sanitized = 0
    Get-ChildItem $skillsDir -Recurse -File -Force |
        Where-Object { $exts -contains $_.Extension } |
        ForEach-Object {
            $raw = [System.IO.File]::ReadAllText($_.FullName)
            $new = $raw
            $new = $new -replace 'f5cf6d9e-3a62-4f0f-a235-e6d7c21b240b', '<X-Access-Token>'
            $new = $new -replace 'dd05f1c54d63749eda95f9fa6d49v442a', '<SIGNATURE_SECRET>'
            $new = $new -replace '192\.168\.1\.6:8085', 'localhost:8080'
            $new = $new -replace '192\.168\.\d+\.\d+', 'localhost'
            $new = $new -replace 'C:/Users/(25067|zhang)/\.claude/skills', '~/.claude/skills'
            $new = $new -replace 'G:\\idea_cache\\\.claude\\skills', '~/.claude/skills'
            $new = $new -replace '/home/double-check/Projetos/jeecg-mcp/dist/index\.js', '<CAMINHO_ABSOLUTO>/jeecg-mcp/dist/index.js'
            if ($new -ne $raw) {
                [System.IO.File]::WriteAllText($_.FullName, $new, (New-Object System.Text.UTF8Encoding($false)))
                $script:sanitized++
            }
        }
    Write-Host "    arquivos sanitizados: $($script:sanitized)"

    # --- 6. Registra a procedência -----------------------------------------
    @{
        upstream    = $UpstreamRepo
        branch      = $Branch
        commit      = $upstreamSha
        syncedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
        ownSkills   = $OwnSkills
    } | ConvertTo-Json | Out-File (Join-Path $repoRoot 'UPSTREAM.json') -Encoding utf8

    Write-Host "`n==> Sync concluído. Revise com 'git diff' antes de commitar." -ForegroundColor Green
}
finally {
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue }
}
