# Roadmap

**Current Milestone:** Rota do Demo — Aparelhos (em andamento)
**Status:** M1 concluído ✅ — priorizando um MVP demonstrável pro cliente

---

## 🎯 Rota do Demo (prioridade atual)

**Objetivo:** ter algo visual e convincente pra mostrar pro cliente o quanto antes,
validar a ideia e destravar venda antes de o sistema estar 100%.

**Sequência priorizada:**

1. ✅ **Cadastro de Aparelhos** — CONCLUÍDO e deployado (APR-01..09, 96 tests)
2. **Login simples** — tela de login que só escolhe a clínica (troca o header `X-Clinic-Id`). ← PRÓXIMO
   NÃO é o Cognito ainda — o `get_clinic_id()` no back já está isolado, então trocar
   simples → Cognito depois é mexer num ponto só.
3. **Front leve (demo)** — stack decidida + telas + fluxo principal. SEM a spec "impecable"
   ainda (evita caprichar em suposições que o cliente vai mudar).
4. **📣 DEMO pro cliente**
5. **Depois do demo:** spec "impecable" (front definitivo, com feedback do cliente) →
   Cognito de verdade → Registro de Sessões.

**Fora do demo (deferido):** Registro de Sessões, relatórios. Um demo com paciente +
aparelho + multi-clínica + telinha bonita já é convincente — não gold-platear antes de mostrar.

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

**1. Cadastro de Aparelhos (por clínica)** - COMPLETE ✅ (deployado 2026-07-21)

- Catálogo de aparelhos próprio de cada clínica (A pode ter o que B não tem)
- Modelagem: `PK=CLINIC#<clinicId>`, `SK=APARELHO#<id>` (nível clínica, não paciente)
- Listagem por Query direto na PK da clínica (sem GSI necessário)
- CRUD (criar, listar, editar, remover — soft delete). APR-01..09 Verified, 96 tests
- ✅ Deployado; smoke-test público OK (CRUD + isolamento entre clínicas)

**2. Registro de Sessões** - DEFERIDO (pós-demo)  ← depende do catálogo de aparelhos

- Modelagem sessão sob o paciente: `PK=CLINIC#<clinicId>#CLIENT#<clientId>`, `SK=SESSION#<data>`
- Sessão referencia aparelhos do catálogo, guardando snapshot (id + nome) — histórico imune a edição/remoção do aparelho
- Endpoints para registrar e consultar sessões por paciente ("última sessão", "evolução" = 1 Query por PK)
- **Sai da frente pela Rota do Demo** — entra depois de mostrar o MVP pro cliente

---

## M3 — Autenticação da Equipe

**Goal:** Proteger o sistema com login da equipe da clínica.

### Features

**Login simples (pré-demo)** - PLANNED  ← faz parte da Rota do Demo

- Tela de login que seleciona a clínica (substitui o header `X-Clinic-Id`)
- Sem Cognito ainda; suficiente pra contar a história multi-tenant no demo

**Login com Cognito (pós-demo)** - PLANNED

- User pool para a equipe
- Integração de autenticação no API Gateway
- `get_clinic_id()` passa a ler o `clinicId` do token (troca só esse ponto)

---

## M4 — Frontend + Domínio

**Goal:** Interface web publicada em domínio próprio.

### Features

**Front leve (demo)** - PLANNED  ← faz parte da Rota do Demo

- Stack decidida + telas + fluxo principal (paciente, aparelho, login simples)
- Objetivo: mostrar pro cliente rápido, iterar no visual

**Frontend definitivo (spec "impecable")** - PLANNED (pós-demo)

- Especificação "impecable" escrita **com o feedback do cliente**
- Implementação da SPA + deploy em S3 + CloudFront

**Domínio + SSL** - PLANNED

- Route 53 + ACM

---

## Future Considerations

- Upload de fotos, laudos e anexos por paciente (S3)
- Relatórios/estatísticas de uso de aparelhos
- Exportação de dados dos pacientes
- **Mobile** (mesma API): via PWA (front web responsivo/instalável) ou app nativo (React Native/Flutter). Backend já serve — não precisa refazer.
- Papéis/permissões dentro da clínica (roles via Cognito groups) — pós-Cognito
- Onboarding self-service de nova clínica (cria clinicId + admin)
