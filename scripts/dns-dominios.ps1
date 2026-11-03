# Aponta o DNS (Route 53) dos tres enderecos para o CloudFront certo:
#   app.pilatesone.com.br       -> sistema (stack clinica-pilates-frontend)
#   pilatesone.com.br e www     -> site informativo (stack clinica-pilates-site)
# Cria ou atualiza (UPSERT) os registros A e AAAA. Pode rodar de novo sem problema.
#
# Uso (na raiz do projeto):
#   powershell -ExecutionPolicy Bypass -File scripts\dns-dominios.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\dns-dominios.ps1 -SoApp   # so o app.
#
# (Mensagens sem acento de proposito: o PowerShell 5.1 le .ps1 sem BOM como ANSI.)

param([switch]$SoApp)

$ErrorActionPreference = 'Stop'

$zona = 'Z088304815X5KV64D3NJ'        # hosted zone pilatesone.com.br
$zonaCloudFront = 'Z2FDTNDATAQYW2'   # fixo da AWS para todo alias de CloudFront

function Destino($stack) {
    $valor = aws cloudformation describe-stacks --stack-name $stack --query "Stacks[0].Outputs[?OutputKey=='CloudFrontDomain'].OutputValue" --output text
    if ($LASTEXITCODE -ne 0 -or -not $valor -or $valor -eq 'None') {
        throw "Nao achei a saida CloudFrontDomain da stack $stack. Ela ja foi publicada com o template novo?"
    }
    return $valor
}

$registros = @(@{ Nome = 'app.pilatesone.com.br.'; Destino = (Destino 'clinica-pilates-frontend') })
if (-not $SoApp) {
    $site = Destino 'clinica-pilates-site'
    $registros += @{ Nome = 'pilatesone.com.br.'; Destino = $site }
    $registros += @{ Nome = 'www.pilatesone.com.br.'; Destino = $site }
}

$mudancas = @()
foreach ($r in $registros) {
    foreach ($tipo in 'A', 'AAAA') {
        $mudancas += @{
            Action = 'UPSERT'
            ResourceRecordSet = @{
                Name = $r.Nome
                Type = $tipo
                AliasTarget = @{ HostedZoneId = $zonaCloudFront; DNSName = $r.Destino; EvaluateTargetHealth = $false }
            }
        }
    }
    Write-Host "$($r.Nome) -> $($r.Destino)"
}

$arquivo = Join-Path $env:TEMP 'dns-dominios.json'
$json = @{ Comment = 'Pilates One: app, raiz e www'; Changes = $mudancas } | ConvertTo-Json -Depth 6
[IO.File]::WriteAllText($arquivo, $json, (New-Object Text.UTF8Encoding $false))

Write-Host ""
Write-Host '==> Gravando no Route 53' -ForegroundColor Cyan
$mudanca = aws route53 change-resource-record-sets --hosted-zone-id $zona --change-batch "file://$arquivo" --query 'ChangeInfo.Id' --output text
if ($LASTEXITCODE -ne 0) { throw 'Falhou ao gravar no Route 53.' }
aws route53 wait resource-record-sets-changed --id $mudanca
Write-Host 'OK - DNS atualizado (pode levar alguns minutos para todo mundo enxergar).' -ForegroundColor Green
