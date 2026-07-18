# Infraestrutura Base (SAM) Tasks

**Spec**: `.specs/features/infra-base-sam/spec.md`
**Testing**: `.specs/codebase/TESTING.md`
**Status**: In Progress (T1–T5 ✅ done; T6 = deploy pendente)

---

## Execution Plan

As tarefas são majoritariamente sequenciais: cada uma constrói sobre a anterior e várias tocam o mesmo `template.yaml`. Pouca paralelização real.

```
Phase 1 (Foundation, Sequential):
  T1 → T2 → T3

Phase 2 (Infra template, Sequential):
  T3 → T4 → T5

Phase 3 (Deploy validation, Sequential — bloqueada por B-001):
  T5 → T6
```

---

## Task Breakdown

### T1: Scaffold do projeto Python ✅ DONE

**What**: Criar a estrutura base do projeto backend (pacote `app`, dependências, config de testes, .gitignore).
**Where**: `src/app/__init__.py`, `requirements.txt`, `pyproject.toml`, `tests/__init__.py`, `.gitignore`
**Depends on**: None
**Reuses**: —
**Requirement**: INFRA-01 (fundação)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Estrutura `src/app/` e `tests/` criada
- [ ] `requirements.txt` com `fastapi`, `mangum`, `boto3` (runtime) e `pytest`, `moto` (dev)
- [ ] `pyproject.toml` com config do pytest (testpaths=tests)
- [ ] `.gitignore` cobre `.aws-sam/`, `__pycache__/`, `*.pyc`, `.venv/`
- [ ] Gate check passes: `python -m compileall src && pytest --collect-only -q`

**Tests**: none
**Gate**: build

**Verify**: `pytest --collect-only -q` roda sem erro de importação.

**Commit**: `chore(infra): scaffold do projeto Python (app, deps, pytest)`

---

### T2: App FastAPI com endpoint /health ✅ DONE

**What**: Criar a aplicação FastAPI com uma rota `GET /health` retornando `{"status":"ok"}`, com teste unitário.
**Where**: `src/app/main.py`, `tests/test_health.py`
**Depends on**: T1
**Reuses**: —
**Requirement**: INFRA-02, INFRA-03

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `app = FastAPI()` definido em `src/app/main.py`
- [ ] `GET /health` retorna `200` com `{"status":"ok"}`
- [ ] Rota inexistente retorna `404` (padrão FastAPI)
- [ ] Teste unitário via `fastapi.testclient.TestClient` cobre `/health` (200) e rota inexistente (404)
- [ ] Gate check passes: `pytest -q`
- [ ] Test count: 2 tests pass (no silent deletions)

**Tests**: unit
**Gate**: quick

**Verify**: `pytest -q tests/test_health.py` → 2 passed.

**Commit**: `feat(infra): app FastAPI com endpoint /health`

---

### T3: Handler Mangum (entrypoint Lambda) ✅ DONE

**What**: Adicionar o adaptador Mangum que expõe o app FastAPI como handler de Lambda, com smoke test de evento API Gateway.
**Where**: `src/app/handler.py`, `tests/test_handler.py`
**Depends on**: T2
**Reuses**: `src/app/main.py` (app)
**Requirement**: INFRA-03

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `handler = Mangum(app)` em `src/app/handler.py`
- [ ] Smoke test invoca `handler` com um evento API Gateway HTTP mínimo de `GET /health` e valida `statusCode == 200`
- [ ] Gate check passes: `pytest -q`
- [ ] Test count: 1 test passes (no silent deletions)

**Tests**: unit
**Gate**: quick

**Verify**: `pytest -q tests/test_handler.py` → 1 passed.

**Commit**: `feat(infra): handler Mangum como entrypoint da Lambda`

---

### T4: Template SAM — Lambda + API Gateway (proxy) + CORS ✅ DONE

**What**: Criar `template.yaml` provisionando a função Lambda (runtime python3.13, handler `app.handler.handler`) e API Gateway HTTP com integração proxy e CORS.
**Where**: `template.yaml`
**Depends on**: T3
**Reuses**: `src/app/handler.py` (handler alvo)
**Requirement**: INFRA-01, INFRA-02, INFRA-04

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `AWS::Serverless::Function` com `Runtime: python3.13`, `Handler: app.handler.handler`, `CodeUri: src/`
- [ ] Evento HTTP API com rota proxy (`ANY /{proxy+}` ou catch-all) apontando para a Lambda
- [ ] CORS configurado no HTTP API (AllowOrigins, AllowMethods, AllowHeaders)
- [ ] `Outputs` expõe a URL base do API
- [ ] Gate check passes: `python -m compileall src && pytest --collect-only -q`

**Tests**: none
**Gate**: build

**Verify**: `sam validate` (quando SAM CLI instalado) retorna template válido; até lá, revisão manual do YAML.

**Commit**: `feat(infra): template SAM com Lambda + API Gateway HTTP proxy + CORS`

---

### T5: Tabela DynamoDB + IAM menor privilégio + env var ✅ DONE

**What**: Adicionar ao template a tabela DynamoDB on-demand (PK/SK) e conceder à Lambda permissão apenas nessa tabela, injetando o nome via variável de ambiente.
**Where**: `template.yaml` (modify)
**Depends on**: T4
**Reuses**: `template.yaml` (recursos de T4)
**Requirement**: INFRA-05, INFRA-06

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `AWS::DynamoDB::Table` (ou `AWS::Serverless::SimpleTable`/resource) com `PK` (HASH, String) e `SK` (RANGE, String), `BillingMode: PAY_PER_REQUEST`
- [ ] Lambda recebe `TABLE_NAME` via `Environment.Variables`
- [ ] Policy IAM concede `dynamodb:*Item`/`Query` apenas no ARN dessa tabela (menor privilégio), não `*`
- [ ] Gate check passes: `python -m compileall src && pytest --collect-only -q`

**Tests**: none
**Gate**: build

**Verify**: revisão do YAML confirma tabela PK/SK on-demand e policy restrita ao ARN da tabela.

**Commit**: `feat(infra): tabela DynamoDB on-demand + IAM menor privilégio`

---

### T6: Validação de deploy (health end-to-end) — bloqueada por B-001

**What**: Fazer `sam build` + `sam deploy` e confirmar `GET /health` respondendo pela URL do API Gateway.
**Where**: — (execução; sem arquivo novo, exceto `samconfig.toml` gerado)
**Depends on**: T5
**Reuses**: `template.yaml`
**Requirement**: INFRA-01, INFRA-02

**Tools**:
- MCP: NONE
- Skill: NONE

**Blocked by**: B-001 (SAM CLI não instalado) — requer instalar SAM CLI + credenciais AWS (`aws sts get-caller-identity`).

**Done when**:
- [ ] `sam build` conclui resolvendo dependências para python3.13
- [ ] `sam deploy --guided` provisiona a stack sem erro
- [ ] `curl https://<api-url>/health` retorna `200 {"status":"ok"}`
- [ ] `aws dynamodb describe-table` confirma PK/SK e PAY_PER_REQUEST

**Tests**: none
**Gate**: full

**Verify**: `curl` do endpoint `/health` retorna 200; tabela existe na AWS.

**Commit**: `chore(infra): primeiro deploy da stack base (health OK)`

---

## Parallel Execution Map

```
Phase 1 (Sequential):  T1 → T2 → T3
Phase 2 (Sequential):  T3 → T4 → T5
Phase 3 (Sequential):  T5 → T6   [bloqueada por B-001]
```

Nenhuma task `[P]`: T1–T3 têm dependência linear; T4–T5 tocam o mesmo `template.yaml` (estado compartilhado, não paralelizável); T6 depende de tudo.

---

## Pre-Approval Validation

### Check 1 — Task Granularity

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Scaffold | estrutura + config (coeso) | ✅ Granular |
| T2: App /health | 1 endpoint + teste | ✅ Granular |
| T3: Handler Mangum | 1 entrypoint + teste | ✅ Granular |
| T4: Template Lambda+APIGW | 1 arquivo (template) | ✅ Granular |
| T5: DynamoDB+IAM | modifica 1 arquivo (coeso) | ✅ Granular |
| T6: Deploy validation | 1 ação de deploy | ✅ Granular |

### Check 2 — Diagram-Definition Cross-Check

| Task | Depends On (body) | Diagram Shows | Status |
| ---- | ----------------- | ------------- | ------ |
| T1 | None | (início) | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |

### Check 3 — Test Co-location Validation

| Task | Code Layer | Matrix Requires | Task Says | Status |
| ---- | ---------- | --------------- | --------- | ------ |
| T1 | Scaffold/config | none | none | ✅ OK |
| T2 | Rota FastAPI | unit | unit | ✅ OK |
| T3 | Handler Mangum | unit | unit | ✅ OK |
| T4 | Template SAM | none | none | ✅ OK |
| T5 | Template SAM (infra) | none | none | ✅ OK |
| T6 | Deploy (infra) | none | none | ✅ OK |

Todos os checks ✅ — pronto para aprovação.

---

## Requirement Coverage

| Requirement | Task(s) |
| ----------- | ------- |
| INFRA-01 | T1, T4, T6 |
| INFRA-02 | T2, T4, T6 |
| INFRA-03 | T2, T3 |
| INFRA-04 | T4 |
| INFRA-05 | T5 |
| INFRA-06 | T5 |

Cobertura: 6/6 requisitos mapeados para tasks. ✅
