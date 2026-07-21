# Roadmap

**Current Milestone:** M2 — Registro de Sessões e Aparelhos (próximo)
**Status:** M1 concluído ✅ — iniciar M2

---

## M1 — Fundação + CRUD de Pacientes

**Goal:** Ter a infraestrutura serverless base provisionada e um CRUD de pacientes funcional end-to-end (API).
**Target:** Primeira versão utilizável do backend.

### Features

**Infraestrutura base (SAM)** - COMPLETE

- Template SAM com Lambda, API Gateway (proxy) e tabela DynamoDB
- Deploy via `sam deploy` (stack `clinica-pilates` no ar, us-east-1)
- Configuração de CORS
- Verificado: `GET /health` → `{"status":"ok"}`

**CRUD de Pacientes** - COMPLETE

- Modelagem da entidade Paciente no DynamoDB (single-table, `SK=PROFILE`)
- Endpoints: criar, listar, obter, editar, remover (soft delete) paciente
- Backend FastAPI + Mangum com roteamento interno em uma Lambda
- Validação via Pydantic
- 45 testes verdes (schemas + repositório com moto + endpoints); PAC-01..09 Verified
- ✅ Deployado na stack `clinica-pilates` (2026-07-20); smoke-test público OK

**Milestone M1 CONCLUÍDO** ✅

---

## M2 — Aparelhos e Registro de Sessões

**Goal:** Registrar, por paciente, os aparelhos utilizados em cada sessão (core do produto).
Cada clínica mantém seu próprio catálogo de aparelhos (multi-tenant, AD-007).

### Features

**1. Cadastro de Aparelhos (por clínica)** - PLANNED  ← fazer primeiro (fundação)

- Catálogo de aparelhos próprio de cada clínica (A pode ter o que B não tem)
- Modelagem: `PK=CLINIC#<clinicId>`, `SK=APARELHO#<id>` (nível clínica, não paciente)
- Listagem por Query direto na PK da clínica (sem GSI necessário)
- CRUD (criar, listar, editar, remover — soft delete para preservar histórico)

**2. Registro de Sessões** - PLANNED  ← depende do catálogo de aparelhos

- Modelagem sessão sob o paciente: `PK=CLINIC#<clinicId>#CLIENT#<clientId>`, `SK=SESSION#<data>`
- Sessão referencia aparelhos do catálogo, guardando snapshot (id + nome) — histórico imune a edição/remoção do aparelho
- Endpoints para registrar e consultar sessões por paciente ("última sessão", "evolução" = 1 Query por PK)

---

## M3 — Autenticação da Equipe

**Goal:** Proteger o sistema com login da equipe da clínica.

### Features

**Login com Cognito** - PLANNED

- User pool para a equipe
- Integração de autenticação no API Gateway
- Fluxo de login no frontend

---

## M4 — Frontend definitivo + Domínio

**Goal:** Interface web finalizada e publicada em domínio próprio.

### Features

**Frontend (spec "impecable")** - PLANNED

- Especificação e implementação da SPA
- Deploy em S3 + CloudFront

**Domínio + SSL** - PLANNED

- Route 53 + ACM

---

## Future Considerations

- Upload de fotos, laudos e anexos por paciente (S3)
- Relatórios/estatísticas de uso de aparelhos
- Exportação de dados dos pacientes
