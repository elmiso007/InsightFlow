# =============================================================================
# limpar_historico.ps1
# -----------------------------------------------------------------------------
# Substitui credenciais hardcoded no historico git por placeholders [REDACTED_*]
# usando git filter-repo. Reescreve TODOS os commits.
#
# >>> PRE-REQUISITOS <<<
#   1. git filter-repo instalado:
#        pip install git-filter-repo
#      (ou baixar de https://github.com/newren/git-filter-repo)
#
#   2. TODAS as credenciais ja rotacionadas nos paineis externos
#      (OpenAI, Slack, Gemini, ServiceNow, Tray, Cplug, Gmail, Postgres).
#
#   3. Working tree limpo (sem alteracoes pendentes). Faca commit ou stash antes.
#
#   4. config.ini ja atualizado com as NOVAS credenciais.
#
# >>> O QUE ESTE SCRIPT FAZ <<<
#   1. Verifica pre-requisitos
#   2. Faz backup do diretorio .git/ em .git.backup-YYYYMMDD-HHMMSS/
#   3. Executa: git filter-repo --replace-text tools\replacements.txt --force
#   4. Faz garbage collection agressivo
#   5. Mostra como verificar o resultado
#
# >>> COMO REVERTER <<<
#   Se algo der errado, basta apagar .git/ e renomear o backup de volta:
#     Remove-Item -Recurse -Force .git
#     Rename-Item .git.backup-XXXX .git
#
# >>> EFEITOS COLATERAIS <<<
#   - Todos os SHAs de commit MUDAM (historico inteiro reescrito)
#   - Tags, branches e refs sao atualizados automaticamente
#   - Reflog antigo e descartado apos o gc
# =============================================================================

$ErrorActionPreference = 'Stop'

# Garantir que estamos na raiz do repo
$repoRoot = git rev-parse --show-toplevel 2>$null
if (-not $repoRoot) {
    Write-Host "ERRO: nao esta dentro de um repositorio git." -ForegroundColor Red
    exit 1
}
Set-Location $repoRoot
Write-Host "Repositorio: $repoRoot" -ForegroundColor Cyan

# 1. Verificar git filter-repo
$null = git filter-repo --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERRO: git filter-repo nao esta instalado." -ForegroundColor Red
    Write-Host "Instale com:  pip install git-filter-repo" -ForegroundColor Yellow
    exit 1
}
Write-Host "OK: git filter-repo disponivel" -ForegroundColor Green

# 2. Working tree limpo?
$dirty = git status --porcelain
if ($dirty) {
    Write-Host "ERRO: working tree tem alteracoes pendentes." -ForegroundColor Red
    Write-Host "      Faca commit ou stash antes de prosseguir." -ForegroundColor Yellow
    git status --short
    exit 1
}
Write-Host "OK: working tree limpo" -ForegroundColor Green

# 3. replacements.txt existe?
$replacementsFile = Join-Path $repoRoot 'tools\replacements.txt'
if (-not (Test-Path $replacementsFile)) {
    Write-Host "ERRO: $replacementsFile nao encontrado." -ForegroundColor Red
    exit 1
}
Write-Host "OK: replacements.txt encontrado" -ForegroundColor Green

# 4. Confirmacao final
Write-Host ""
Write-Host "ATENCAO: esta operacao reescreve TODOS os commits do repo." -ForegroundColor Yellow
Write-Host "Todas as SHAs vao mudar. Backup automatico do .git sera feito." -ForegroundColor Yellow
Write-Host ""
$confirm = Read-Host "Digite EXATAMENTE 'reescrever historico' para confirmar"
if ($confirm -ne 'reescrever historico') {
    Write-Host "Cancelado pelo usuario." -ForegroundColor Yellow
    exit 0
}

# 5. Backup do .git
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupDir = ".git.backup-$timestamp"
Write-Host ""
Write-Host "Criando backup em $backupDir ..." -ForegroundColor Cyan
Copy-Item -Path .git -Destination $backupDir -Recurse -Force
Write-Host "OK: backup criado" -ForegroundColor Green

# 6. Executar filter-repo
Write-Host ""
Write-Host "Executando git filter-repo --replace-text ..." -ForegroundColor Cyan
git filter-repo --replace-text $replacementsFile --force
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERRO: git filter-repo falhou." -ForegroundColor Red
    Write-Host "      Para reverter: Remove-Item -Recurse -Force .git ; Rename-Item $backupDir .git" -ForegroundColor Yellow
    exit 1
}
Write-Host "OK: historico reescrito" -ForegroundColor Green

# 7. Garbage collection agressivo
Write-Host ""
Write-Host "Rodando garbage collection ..." -ForegroundColor Cyan
git reflog expire --expire=now --all
git gc --prune=now --aggressive
Write-Host "OK: gc concluido" -ForegroundColor Green

# 8. Verificacao
Write-Host ""
Write-Host "=== VERIFICACAO ===" -ForegroundColor Cyan
Write-Host "Procurando credenciais antigas no historico (deve retornar VAZIO):" -ForegroundColor Cyan
# Carrega as credenciais antigas do replacements.txt (lado esquerdo de ==>).
# Buscar por elas no historico evita ter strings reais (mesmo parciais)
# versionadas aqui neste arquivo. replacements.txt esta no .gitignore.
$patterns = (Get-Content $replacementsFile) |
    ForEach-Object { ($_ -split '==>')[0] } |
    Where-Object { $_ }
$encontrou = $false
foreach ($p in $patterns) {
    $hits = git log --all --full-history --oneline -S $p 2>$null
    if ($hits) {
        Write-Host "  AINDA ENCONTRADO: $p" -ForegroundColor Red
        Write-Host $hits
        $encontrou = $true
    } else {
        Write-Host "  limpo: $p" -ForegroundColor Green
    }
}

Write-Host ""
if ($encontrou) {
    Write-Host "AVISO: algumas credenciais ainda aparecem. Verifique replacements.txt." -ForegroundColor Red
} else {
    Write-Host "Limpeza concluida com sucesso." -ForegroundColor Green
    Write-Host ""
    Write-Host "Proximos passos:" -ForegroundColor Cyan
    Write-Host "  1. Validar com: git log --oneline" -ForegroundColor White
    Write-Host "  2. Se tudo OK, apagar backup: Remove-Item -Recurse -Force $backupDir" -ForegroundColor White
    Write-Host "  3. Se for adicionar remote no futuro, sera push normal" -ForegroundColor White
}
