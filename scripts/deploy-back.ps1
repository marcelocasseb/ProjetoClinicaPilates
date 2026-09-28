# Publica o backend (stack SAM clinica-pilates: Lambda + API + Cognito + DynamoDB)
# SEM Docker, reaproveitando as bibliotecas Linux do ultimo build com container.
#
# Uso (na raiz do projeto):
#   powershell -ExecutionPolicy Bypass -File scripts\deploy-back.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\deploy-back.ps1 -SoMostrar   # so cria o change set e mostra o que muda
#
# Por que sem Docker: o `sam build --use-container` (AD-006) so existe para gerar a
# wheel Linux do pydantic-core, e a maquina nao aguenta subir o Docker. Enquanto
# src/requirements.txt nao mudar, copiamos so o codigo novo (src/app) para dentro
# de .aws-sam/build. Se mudar, o script para e pede o build com container.
# (Mensagens sem acento de proposito: o PowerShell 5.1 le .ps1 sem BOM como ANSI.)

param([switch]$SoMostrar)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

$stack = 'clinica-pilates'
$sam = 'C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd'
$build = '.aws-sam\build'
$funcao = "$build\ClinicaApiFunction"
$env:SAM_CLI_TELEMETRY = '0'

function Passo($descricao) {
    Write-Host ""
    Write-Host "==> $descricao" -ForegroundColor Cyan
}

function Checar($descricao) {
    if ($LASTEXITCODE -ne 0) { throw "Falhou: $descricao (codigo $LASTEXITCODE)" }
}

# --- 1. As bibliotecas Linux do build anterior ainda servem? ------------------
Passo 'Conferindo o build anterior'
$so = Get-ChildItem "$funcao\pydantic_core" -Filter '*linux-gnu.so' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $so) {
    throw "Nao achei a lib Linux do pydantic-core em $funcao. Rode uma vez: sam build --use-container"
}
if ((Get-Item src\requirements.txt).LastWriteTime -gt $so.LastWriteTime) {
    throw 'src\requirements.txt mudou depois do ultimo build com container. Rode: sam build --use-container'
}
Write-Host "OK - usando $($so.Name)"

# --- 2. Copia o codigo novo e o template -------------------------------------
Passo 'Copiando o codigo (src\app) e o template para o build'
$backup = '.aws-sam\build.bak-ultimo-deploy'
if (Test-Path $backup) { Remove-Item $backup -Recurse -Force }
Copy-Item $build $backup -Recurse
Remove-Item "$funcao\app" -Recurse -Force
Copy-Item src\app "$funcao\app" -Recurse
Get-ChildItem "$funcao\app" -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
# UTF-8 SEM BOM (o Set-Content -Encoding UTF8 do PowerShell 5.1 poe BOM).
$template = (Get-Content template.yaml -Raw -Encoding UTF8) -replace 'CodeUri: src/', 'CodeUri: ClinicaApiFunction'
[IO.File]::WriteAllText((Join-Path $PWD "$build\template.yaml"), $template, (New-Object Text.UTF8Encoding $false))

Passo 'Validando o template'
& $sam validate --lint -t "$build\template.yaml"
Checar 'sam validate'

# --- 3. Change set: mostra o que vai mudar ------------------------------------
# --no-execute-changeset: o `confirm_changeset = true` do samconfig.toml trava
# fora de um terminal interativo; executamos o change set logo abaixo.
Passo 'Criando o change set (ainda nao aplica nada)'
$ErrorActionPreference = 'Continue'   # o sam escreve progresso no stderr
$saida = & $sam deploy --no-execute-changeset --no-fail-on-empty-changeset 2>&1 | ForEach-Object {
    if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.Exception.Message } else { "$_" }
}
$codigo = $LASTEXITCODE
$ErrorActionPreference = 'Stop'
$saida | Where-Object { $_.Trim() } | ForEach-Object { Write-Host $_ }
if ($codigo -ne 0) { throw "Falhou: sam deploy (codigo $codigo)" }

$arn = ($saida | Select-String -Pattern 'arn:aws:cloudformation:\S+:changeSet/\S+' | Select-Object -Last 1).Matches.Value
if (-not $arn) {
    Write-Host ""
    Write-Host 'Nada para publicar - o backend no ar ja esta igual ao codigo.' -ForegroundColor Green
    exit 0
}

if ($SoMostrar) {
    Write-Host ""
    Write-Host "Change set criado, NAO aplicado: $arn" -ForegroundColor Yellow
    exit 0
}

# --- 4. Aplica e espera ----------------------------------------------------------
Passo 'Aplicando o change set'
aws cloudformation execute-change-set --change-set-name $arn
Checar 'execute-change-set'

Passo 'Aguardando a stack terminar de atualizar (1 a 3 min)'
aws cloudformation wait stack-update-complete --stack-name $stack
Checar 'a atualizacao da stack (veja os eventos no console do CloudFormation)'

# --- 5. Confere no ar ------------------------------------------------------------
Passo 'Conferindo no ar'
$api = aws cloudformation describe-stacks --stack-name $stack --query "Stacks[0].Outputs[?OutputKey=='ApiBaseUrl'].OutputValue" --output text
Checar 'describe-stacks'
$health = Invoke-RestMethod -Uri "$api/health"
Write-Host "GET $api/health -> $($health | ConvertTo-Json -Compress)"
Write-Host 'OK - backend publicado.' -ForegroundColor Green
