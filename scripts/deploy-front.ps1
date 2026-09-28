# Publica o front (React/Vite) no S3 + CloudFront, com os headers de cache certos.
#
# Uso (na raiz do projeto):
#   powershell -ExecutionPolicy Bypass -File scripts\deploy-front.ps1
#
# Cache: assets com hash no nome sao imutaveis (cache de 1 ano); index.html e
# version.json NUNCA podem ficar em cache - o index aponta para o JS da versao
# atual, e o version.json e o que as abas abertas consultam para mostrar
# "Nova versao disponivel - Atualizar" (frontend/src/components/AvisoVersao.jsx).
# (Mensagens sem acento de proposito: o PowerShell 5.1 le .ps1 sem BOM como ANSI.)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

$bucket = 's3://clinica-pilates-frontend-sitebucket-n6oomystbesc'
$distribution = 'EGYNGZONKGVLT'
$site = 'https://d1th2j57vyxahs.cloudfront.net'

function Passo($descricao, [scriptblock]$comando) {
    Write-Host ""
    Write-Host "==> $descricao" -ForegroundColor Cyan
    & $comando
    if ($LASTEXITCODE -ne 0) { throw "Falhou: $descricao (codigo $LASTEXITCODE)" }
}

Passo 'Build do front (npm run build)' {
    Push-Location frontend
    try { npm run build } finally { Pop-Location }
}

$versao = (Get-Content frontend\dist\version.json -Raw | ConvertFrom-Json).version
if (-not $versao) { throw 'frontend\dist\version.json nao foi gerado pelo build.' }
Write-Host "Versao desta build: $versao"

Passo 'Enviando assets (cache longo, imutaveis)' {
    aws s3 sync frontend/dist $bucket --delete --exclude 'index.html' --exclude 'version.json' --cache-control 'public, max-age=31536000, immutable'
}

Passo 'Enviando index.html (sem cache)' {
    aws s3 cp frontend/dist/index.html "$bucket/index.html" --cache-control 'no-cache, must-revalidate' --content-type 'text/html'
}

Passo 'Enviando version.json (sem cache)' {
    aws s3 cp frontend/dist/version.json "$bucket/version.json" --cache-control 'no-cache, must-revalidate' --content-type 'application/json'
}

$invalidacao = $null
Passo 'Limpando o cache do CloudFront' {
    $script:invalidacao = aws cloudfront create-invalidation --distribution-id $distribution --paths '/*' --query 'Invalidation.Id' --output text
}

Passo "Aguardando a limpeza do cache terminar ($invalidacao) - leva 1 a 2 min" {
    aws cloudfront wait invalidation-completed --distribution-id $distribution --id $invalidacao
}

Write-Host ""
Write-Host '==> Conferindo no ar' -ForegroundColor Cyan
$noAr = (Invoke-RestMethod -Uri "$site/version.json?t=$([DateTime]::UtcNow.Ticks)" -Headers @{ 'Cache-Control' = 'no-cache' }).version
if ($noAr -ne $versao) { throw "O site ainda responde a versao '$noAr' (esperado '$versao')." }
Write-Host "OK - front publicado. Versao no ar: $noAr" -ForegroundColor Green
Write-Host 'Abas ja abertas com a versao nova do aviso vao mostrar "Atualizar" em ate 5 min.'
