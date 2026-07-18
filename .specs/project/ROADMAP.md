# Roadmap

**Current Milestone:** M1 — Fundação + CRUD de Pacientes
**Status:** Planning

---

## M1 — Fundação + CRUD de Pacientes

**Goal:** Ter a infraestrutura serverless base provisionada e um CRUD de pacientes funcional end-to-end (API).
**Target:** Primeira versão utilizável do backend.

### Features

**Infraestrutura base (SAM)** - PLANNED

- Template SAM com Lambda, API Gateway (proxy) e tabela DynamoDB
- Deploy via `sam deploy`
- Configuração de CORS

**CRUD de Pacientes** - PLANNED

- Modelagem da entidade Paciente no DynamoDB
- Endpoints: criar, listar, obter, editar, remover paciente
- Backend FastAPI + Mangum com roteamento interno em uma Lambda
- Validação via Pydantic

---

## M2 — Registro de Sessões e Aparelhos

**Goal:** Registrar, por paciente, os aparelhos utilizados em cada sessão (core do produto).

### Features

**Registro de Sessões** - PLANNED

- Modelagem sessão (partition key = paciente, sort key = data/sessão)
- Endpoints para registrar e consultar sessões e aparelhos por paciente

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
