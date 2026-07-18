# State

**Last Updated:** 2026-07-18
**Current Work:** Feature `infra-base-sam` — T1–T5 ✅ concluídas (código Python testado + template.yaml validado com `sam validate --lint`). PRÓXIMO PASSO: T6 = deploy (`sam build` + `sam deploy --guided`). Pré-requisito: confirmar credenciais AWS (`aws sts get-caller-identity`).

**Onde paramos (retomar aqui):**
- ✅ Projeto inicializado (PROJECT/ROADMAP/STATE), commit `621b608`
- ✅ Planejamento da infra + TESTING.md commitados, commit `8e855b6`
- ✅ Decisão de banco: DynamoDB single-table (AD-005)
- ✅ Spec `cadastro-pacientes` escrita (PAC-01..09) — aguarda infra
- ✅ Spec + tasks `infra-base-sam` (INFRA-01..06, T1..T6)
- ✅ Convenção de testes: pytest + moto, cobertura pragmática (TESTING.md)
- ✅ **T1 scaffold done** (`6d3fc75`): src/app, tests/, requirements, pyproject, .gitignore; venv `.venv` criado, deps instaladas OK no Python 3.14
- ✅ **T2 done**: `src/app/main.py` (FastAPI + GET /health) + `tests/test_health.py` (2 testes verdes)
- ✅ **T3 done**: `src/app/handler.py` (Mangum) + `tests/test_handler.py` (smoke test v2, 200) — 3 testes no total
- ✅ **T4+T5 done**: `template.yaml` (Lambda py3.13 + HTTP API proxy + CORS + DynamoDB PK/SK on-demand + IAM DynamoDBCrudPolicy + TABLE_NAME). Validado: `sam validate --lint` OK
- ✅ SAM CLI 1.163.0 instalado → **B-001 resolvido**
- ⏭️ FAZER A SEGUIR: **T6** = `sam build` + `sam deploy --guided`; depois `curl <ApiBaseUrl>/health` → 200
- 🧊 Depois da infra: implementar CRUD de `cadastro-pacientes`

**Ambiente local:** venv em `.venv` (Python 3.14). Testes: `.\.venv\Scripts\python.exe -m pytest -q`.
**SAM CLI:** não está no PATH da sessão automatizada; caminho completo = `C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd` (no terminal do usuário, `sam` funciona direto).

---

## Recent Decisions (Last 60 days)

### AD-001: Backend em FastAPI + Mangum (2026-07-18)

**Decision:** Usar FastAPI com adaptador Mangum em uma única Lambda com roteamento interno.
**Reason:** Validação via Pydantic, docs automáticas, alinhado à sugestão da especificação original.
**Trade-off:** ZIP um pouco maior que Flask.
**Impact:** Handler Lambda usa Mangum; rotas definidas no app FastAPI.

### AD-002: IaC com AWS SAM (2026-07-18)

**Decision:** Provisionar a infraestrutura com AWS SAM.
**Reason:** Menor complexidade para uma stack puramente serverless (Lambda + API Gateway + DynamoDB); usuário delegou a escolha.
**Trade-off:** Menos flexível/multi-cloud que Terraform, menos poderoso que CDK.
**Impact:** Template `template.yaml` do SAM define os recursos; deploy via `sam deploy`.

### AD-003: Escopo do v1 restrito a CRUD de Pacientes (2026-07-18)

**Decision:** v1 entrega apenas o CRUD de pacientes + infraestrutura base. Sessões/aparelhos, Cognito e uploads ficam para milestones seguintes.
**Reason:** Escolha do usuário no questionário de inicialização — reduzir escopo inicial.
**Trade-off:** O core do produto (registro de aparelhos por sessão) só chega no M2.
**Impact:** ROADMAP organizado em M1–M4.

### AD-004: Frontend especificado à parte via spec "impecable" (2026-07-18)

**Decision:** A stack e a implementação do frontend serão definidas em uma especificação separada chamada "impecable".
**Reason:** Preferência do usuário — criar especificações próprias para o front.
**Trade-off:** Framework de frontend fica indefinido no PROJECT.md por ora.
**Impact:** M4 depende dessa spec; hospedagem já definida como S3 + CloudFront.

### AD-005: Manter DynamoDB com single-table design centrado no cliente (2026-07-18)

**Decision:** Confirmado DynamoDB (não migrar para relacional). Modelo single-table onde tudo pende do cliente. Convenção de chaves compartilhada por todas as features:
- Perfil: `PK=CLIENT#<id>`, `SK=PROFILE`
- Medida corporal: `PK=CLIENT#<id>`, `SK=MEASURE#<ISO-date>`
- Pressão arterial: `PK=CLIENT#<id>`, `SK=BP#<ISO-date>`
- Aula/sessão: `PK=CLIENT#<id>`, `SK=SESSION#<ISO-date>` (com lista denormalizada de exercícios/procedimentos)
- Consulta: `PK=CLIENT#<id>`, `SK=CONSULT#<ISO-date>`
- Catálogo de exercícios: `PK=EXERCISE`, `SK=EX#<id>`
**Reason:** Os dados são centrados no cliente e em série temporal (medidas, pressão, aulas, consultas). "Última aula" e "evolução do paciente" são queries nativas do DynamoDB (Query por PK + range no SK). Schema-less facilita adicionar novos tipos (ex: consultas) sem migração. Mantém meta de custo $0–5/mês.
**Trade-off:** Relatórios cruzados entre pacientes (agregações da clínica inteira) exigem GSI ou exportação — aceito por ora; o sistema é uma ficha por paciente.
**Impact:** Todas as feature specs referenciam esta convenção de chaves. Reverte a avaliação anterior que considerava Aurora/relacional.

---

## Active Blockers

### B-001: SAM CLI não instalado — ✅ RESOLVIDO (2026-07-18)

**Discovered:** 2026-07-18
**Impact:** Bloqueava `sam build`/`sam deploy` da feature Infra Base.
**Resolution:** SAM CLI 1.163.0 instalado (via winget). Deploy destravado. Pendente ainda: confirmar credenciais AWS (`aws sts get-caller-identity`) antes da T6.

### B-002: Python local 3.14 vs runtime Lambda (2026-07-18) — PARCIALMENTE RESOLVIDO

**Discovered:** 2026-07-18
**Impact:** Python local é 3.14.4; Lambda não tem runtime 3.14. Build de dependências (ex: pydantic-core, wheel compilada) precisa mirar a plataforma do Lambda.
**Update (T1):** Instalação local no Python 3.14 FUNCIONOU — havia wheels cp314 (pydantic-core 2.46.4, fastapi 0.139.2, moto 5.2.2). Testes locais desbloqueados.
**Restante:** Confirmar que `sam build` resolve wheels para python3.13/x86_64 no deploy (T6). Sem Docker por decisão de projeto.
**Resolution:** Validar no `sam build` (T6); se falhar, considerar Lambda layer ou `--use-container`.

---

## Lessons Learned

_Nenhuma ainda._

---

## Quick Tasks Completed

| #   | Description | Date | Commit | Status |
| --- | ----------- | ---- | ------ | ------ |

---

## Deferred Ideas

- [ ] Upload de fotos/laudos/anexos por paciente (S3) — Captured during: inicialização
- [ ] Relatórios de uso de aparelhos — Captured during: inicialização

---

## Todos

- [ ] Especificar frontend via spec "impecable" (M4)

---

## Preferences

**Model Guidance Shown:** never
