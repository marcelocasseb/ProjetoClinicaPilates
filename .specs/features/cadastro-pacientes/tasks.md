# Cadastro de Pacientes Tasks

**Spec**: `.specs/features/cadastro-pacientes/spec.md`
**Testing**: `.specs/codebase/TESTING.md`
**Status**: Done (T1–T4 ✅ — 45 tests verdes; PAC-01..09 Verified)

CRUD de pacientes sobre a tabela DynamoDB já provisionada (single-table, `PK=CLIENT#<id>`, `SK=PROFILE`, ver AD-005). Três camadas: schemas Pydantic (validação), repositório (acesso DynamoDB via boto3/moto) e router FastAPI (endpoints), fiado no app existente em `src/app/main.py`.

---

## Execution Plan

```
Phase 1 (Foundation, Parallel):
  T1 [P]  (schemas)
  T2 [P]  (repository)

Phase 2 (Router, Sequential — mesmo arquivo):
  (T1, T2) → T3 → T4
```

T1 e T2 são independentes (arquivos distintos, sem dependência de código) e seus testes são parallel-safe (unit / moto). T3 e T4 tocam o mesmo `routers/pacientes.py` (estado compartilhado) → sequenciais.

---

## Task Breakdown

### T1: Schemas Pydantic de Paciente [P]

**What**: Definir os modelos de entrada/saída de paciente com validações (nome obrigatório, email formato, dataNascimento formato, ignorar campos desconhecidos, vazios → None).
**Where**: `src/app/schemas.py`, `tests/test_schemas.py`
**Depends on**: None
**Reuses**: — (Pydantic v2, já dependência transitiva do FastAPI)
**Requirement**: PAC-03, PAC-04, PAC-09

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `PacienteCreate` (nome obrigatório; dataNascimento/endereco/telefone/email opcionais)
- [ ] `PacienteUpdate` (mesmos campos; nome obrigatório na edição — PAC-07 AC2)
- [ ] `PacienteOut` (id, nome, dataNascimento, endereco, telefone, email, ativo, criadoEm, atualizadoEm)
- [ ] Validador: `nome` só-espaços/vazio → `400` (rejeitado) — PAC-03
- [ ] Validador: `email` inválido → rejeitado (regex simples, sem `email-validator`) — PAC-04
- [ ] Validador: `dataNascimento` fora de `YYYY-MM-DD` → rejeitado — PAC-09
- [ ] `model_config` com `extra="ignore"` (campos desconhecidos não persistem) — PAC-09
- [ ] `telefone`/`email` vazios (`""`/espaços) tratados como não informados (`None`) — PAC-09
- [ ] Gate check passes: `pytest -q`
- [ ] Test count: ≥8 tests pass (no silent deletions)

**Tests**: unit
**Gate**: quick

**Verify**: `pytest -q tests/test_schemas.py` → todos verdes.

**Commit**: `feat(pacientes): schemas Pydantic com validação de entrada`

---

### T2: Repositório DynamoDB de Paciente [P]

**What**: Camada de acesso a dados para o item de perfil do paciente na tabela única, com create/get/list/update/soft-delete, testada com moto.
**Where**: `src/app/repository.py`, `tests/test_repository.py`
**Depends on**: None
**Reuses**: convenção de chaves AD-005; `TABLE_NAME` via env (injetada pelo template SAM)
**Requirement**: PAC-02, PAC-05, PAC-06, PAC-08

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `PacienteRepository` lê a tabela de `os.environ["TABLE_NAME"]` (boto3 resource, lazy)
- [ ] `create(data)` → gera `id` (uuid), grava `PK=CLIENT#<id>`, `SK=PROFILE`, `ativo=True`, `criadoEm`/`atualizadoEm` ISO — PAC-02
- [ ] `get(id)` → item se existe **e ativo**, senão `None` — PAC-06
- [ ] `list_ativos()` → apenas itens `SK=PROFILE` com `ativo=True` — PAC-05
- [ ] `update(id, data)` → atualiza campos + `atualizadoEm`; `None` se inexistente/removido — PAC-07 (data layer)
- [ ] `soft_delete(id)` → seta `ativo=False`; `False` se inexistente/já removido; item permanece na tabela — PAC-08
- [ ] Fixture moto (`@mock_aws`) cria a tabela PK/SK on-demand antes dos testes
- [ ] Gate check passes: `pytest -q`
- [ ] Test count: ≥7 tests pass (no silent deletions)

**Tests**: unit
**Gate**: quick

**Verify**: `pytest -q tests/test_repository.py` → todos verdes.

**Commit**: `feat(pacientes): repositório DynamoDB single-table (create/get/list/update/soft-delete)`

---

### T3: Router — cadastrar e obter paciente

**What**: Criar o router FastAPI de pacientes com `POST /pacientes` e `GET /pacientes/{id}`, fiado no app principal.
**Where**: `src/app/routers/__init__.py`, `src/app/routers/pacientes.py`, `src/app/main.py` (modify), `tests/test_pacientes.py`
**Depends on**: T1, T2
**Reuses**: `src/app/schemas.py` (T1), `src/app/repository.py` (T2), `src/app/main.py` (app existente)
**Requirement**: PAC-01, PAC-06

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `POST /pacientes` com `nome` válido → `201` com paciente criado (id, criadoEm) — PAC-01 AC1
- [ ] `POST /pacientes` sem `nome`/vazio → `422`/`400` — PAC-01 AC4
- [ ] `POST /pacientes` com `email` inválido → `422`/`400` — PAC-01 AC5
- [ ] `GET /pacientes/{id}` existente/ativo → `200` — PAC-06 AC1
- [ ] `GET /pacientes/{id}` inexistente → `404` — PAC-06 AC2
- [ ] Router incluído em `main.py` via `app.include_router(...)`
- [ ] Dependência do repositório via `Depends` (testável com moto + `TABLE_NAME`)
- [ ] Fluxo ponta-a-ponta: `POST` depois `GET` retorna o mesmo paciente — Independent Test P1
- [ ] Gate check passes: `pytest -q`
- [ ] Test count: ≥5 novos tests pass (no silent deletions)

**Tests**: unit
**Gate**: quick

**Verify**: `pytest -q tests/test_pacientes.py` → verdes; `/health` continua 200 (sem regressão).

**Commit**: `feat(pacientes): endpoints criar e obter paciente`

---

### T4: Router — listar, editar e remover paciente

**What**: Adicionar ao router `GET /pacientes`, `PUT /pacientes/{id}` e `DELETE /pacientes/{id}` (soft delete).
**Where**: `src/app/routers/pacientes.py` (modify), `tests/test_pacientes.py` (modify)
**Depends on**: T3
**Reuses**: router e testes de T3; repositório T2
**Requirement**: PAC-05, PAC-07, PAC-08

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `GET /pacientes` → `200` com lista de ativos; lista vazia quando não há; omite removidos — PAC-05
- [ ] `PUT /pacientes/{id}` válido → `200` com atualizado + `atualizadoEm` — PAC-07 AC1/AC4
- [ ] `PUT /pacientes/{id}` com `nome` vazio → `422`/`400` — PAC-07 AC2
- [ ] `PUT /pacientes/{id}` inexistente/removido → `404` — PAC-07 AC3
- [ ] `DELETE /pacientes/{id}` → `204`; `GET` posterior → `404`; item permanece na tabela — PAC-08 AC1/AC2/AC4
- [ ] `DELETE /pacientes/{id}` inexistente/já removido → `404` — PAC-08 AC3
- [ ] Gate check passes: `pytest -q`
- [ ] Test count: ≥6 novos tests pass (no silent deletions)

**Tests**: unit
**Gate**: quick

**Verify**: `pytest -q` → suíte inteira verde (health + handler + schemas + repository + pacientes).

**Commit**: `feat(pacientes): endpoints listar, editar e remover (soft delete)`

---

## Parallel Execution Map

```
Phase 1 (Parallel):
  ├── T1 [P]  (schemas.py)
  └── T2 [P]  (repository.py)

Phase 2 (Sequential):
  (T1 + T2) → T3 → T4
```

`[P]` válido para T1/T2: sem dependência de código entre si, arquivos distintos, testes unit/moto parallel-safe (TESTING.md). T3 depende de ambos; T4 estende o arquivo de T3 (estado compartilhado) → sequencial.

---

## Pre-Approval Validation

### Check 1 — Task Granularity

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Schemas | 1 módulo coeso (modelos+validadores) | ✅ Granular |
| T2: Repository | 1 módulo coeso (data layer) | ✅ Granular |
| T3: Router criar/obter | 2 endpoints + fiação (1 recurso) | ✅ Granular |
| T4: Router listar/editar/remover | 3 endpoints no mesmo router | ⚠️ OK (coeso, mesmo recurso REST) |

### Check 2 — Diagram-Definition Cross-Check

| Task | Depends On (body) | Diagram Shows | Status |
| ---- | ----------------- | ------------- | ------ |
| T1 | None | (início, paralelo) | ✅ Match |
| T2 | None | (início, paralelo) | ✅ Match |
| T3 | T1, T2 | (T1+T2) → T3 | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |

T1 e T2 não dependem um do outro → `[P]` válido.

### Check 3 — Test Co-location Validation

| Task | Code Layer | Matrix Requires | Task Says | Status |
| ---- | ---------- | --------------- | --------- | ------ |
| T1 | Modelos/validação (Pydantic) | unit | unit | ✅ OK |
| T2 | Acesso a dados (DynamoDB) | unit (moto) | unit | ✅ OK |
| T3 | Rotas/handlers FastAPI | unit | unit | ✅ OK |
| T4 | Rotas/handlers FastAPI | unit | unit | ✅ OK |

Todos os checks ✅.

---

## Requirement Coverage

| Requirement | Task(s) |
| ----------- | ------- |
| PAC-01 | T3 |
| PAC-02 | T2 |
| PAC-03 | T1 |
| PAC-04 | T1 |
| PAC-05 | T2, T4 |
| PAC-06 | T2, T3 |
| PAC-07 | T1, T4 |
| PAC-08 | T2, T4 |
| PAC-09 | T1 |

Cobertura: 9/9 requisitos mapeados para tasks. ✅
