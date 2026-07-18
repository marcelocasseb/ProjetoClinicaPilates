# State

**Last Updated:** 2026-07-18
**Current Work:** Feature `infra-base-sam` — tasks.md aprovado/em revisão. PRÓXIMO PASSO: executar T1 (scaffold Python). Implementar T1→T5 offline; T6 (deploy) bloqueado por B-001 (SAM CLI).

**Onde paramos (retomar aqui):**
- ✅ Projeto inicializado (PROJECT/ROADMAP/STATE), commit `621b608`
- ✅ Decisão de banco: DynamoDB single-table (AD-005)
- ✅ Spec `cadastro-pacientes` escrita (PAC-01..09) — aguarda infra
- ✅ Spec + tasks `infra-base-sam` escritas (INFRA-01..06, T1..T6)
- ✅ Convenção de testes: pytest + moto, cobertura pragmática (TESTING.md)
- ⏭️ FAZER A SEGUIR: executar tasks da infra a partir de T1
- 🧊 Depois da infra: voltar para implementar o CRUD de `cadastro-pacientes`

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

### B-001: SAM CLI não instalado (2026-07-18)

**Discovered:** 2026-07-18
**Impact:** Bloqueia `sam build`/`sam deploy` da feature Infra Base. AWS CLI (2.34.4) e credenciais não verificadas ainda. Não bloqueia escrever template.yaml nem o código.
**Workaround:** Preparar todo o código/template offline; instalar SAM CLI antes do primeiro deploy.
**Resolution:** Instalar AWS SAM CLI no Windows e confirmar credenciais AWS (`aws sts get-caller-identity`).

### B-002: Python local 3.14 vs runtime Lambda (2026-07-18)

**Discovered:** 2026-07-18
**Impact:** Python local é 3.14.4; Lambda não tem runtime 3.14. Build de dependências (ex: pydantic-core, wheel compilada) precisa mirar a plataforma do Lambda.
**Workaround:** Definir runtime `python3.13` no template; usar `sam build` (baixa wheels manylinux corretas). Sem Docker por decisão de projeto.
**Resolution:** Confirmar que `sam build` resolve as wheels corretas para python3.13/x86_64; se não, considerar Lambda layer ou build direcionado.

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
