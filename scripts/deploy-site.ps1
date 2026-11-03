# Publica o site informativo (pasta site/) no S3 + CloudFront da stack clinica-pilates-site.
#
# Uso (na raiz do projeto):
#   powershell -ExecutionPolicy Bypass -File scripts\deploy-site.ps1
#
# Cache: as paginas .html nunca ficam em cache (texto muda sem mudar o nome do arquivo);
# imagens e CSS ficam 1 dia. O deploy limpa o cache do CloudFront no fim de qualquer jeito.
# (Mensagens sem acento de proposito: o PowerShell 5.1 le .ps1 sem BOM como ANSI.)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

$stack = 'clinica-pilates-site'

function Passo($descricao, [scriptblock]$comando) {
    Write-Host ""
    Write-Host "==> $descricao" -ForegroundColor Cyan
    & $comando
    if ($LASTEXITCODE -ne 0) { throw "Falhou: $descricao (codigo $LASTEXITCODE)" }
}

function Saida($chave) {
    $valor = aws cloudformation describe-stacks --stack-name $stack --query "Stacks[0].Outputs[?OutputKey=='$chave'].OutputValue" --output text
    if ($LASTEXITCODE -ne 0 -or -not $valor) { throw "Nao achei a saida $chave da stack $stack." }
    return $valor
}

$bucket = 's3://' + (Saida 'BucketName')
$distribution = Saida 'DistributionId'
$site = Saida 'SiteUrl'

Passo 'Enviando imagens e CSS (cache de 1 dia)' {
    aws s3 sync site $bucket --delete --exclude '*.html' --cache-control 'public, max-age=86400'
}

Passo 'Enviando as paginas .html (sem cache)' {
    aws s3 sync site $bucket --exclude '*' --include '*.html' --cache-control 'no-cache, must-revalidate' --content-type 'text/html; charset=utf-8'
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
$resposta = Invoke-WebRequest -Uri "$site/?t=$([DateTime]::UtcNow.Ticks)" -UseBasicParsing
if ($resposta.StatusCode -ne 200 -or $resposta.Content -notmatch 'Pilates One') {
    throw "O site respondeu $($resposta.StatusCode) sem o conteudo esperado."
}
Write-Host "OK - site publicado em $site" -ForegroundColor Green
