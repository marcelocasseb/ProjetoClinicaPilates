# Sistema de Gestão de Pilates

**Vision:** Sistema serverless de baixo custo para cadastro de pacientes de uma clínica de Pilates e registro dos aparelhos utilizados por eles em cada sessão.
**For:** Equipe de uma clínica de Pilates pequena (uso concentrado em horário comercial).
**Solves:** Falta de um registro organizado de pacientes e do histórico de aparelhos usados por sessão, sem incorrer em custos fixos de infraestrutura.

## Goals

- Operar dentro do free tier da AWS: custo entre **$0 e $5/mês** no primeiro ano, escalando apenas com uso real.
- Permitir que a equipe cadastre e gerencie pacientes de forma simples (v1).
- Registrar, por paciente, os aparelhos utilizados em cada sessão (milestone seguinte).
- Zero infraestrutura ociosa: toda a stack é serverless e paga por uso.

## Tech Stack

**Core:**

- Frontend: SPA estática hospedada em **S3 + CloudFront**, no domínio **pilatesone.com.br**. Framework: **React + Vite** (o front "leve" do demo virou o de produção; a spec "impecable" do definitivo segue pendente).
- Backend: **Python** com **FastAPI + Mangum**, deploy em **AWS Lambda** via ZIP.
- API: **API Gateway** (HTTP) — roteamento por método explícito, CORS na borda, **JWT Authorizer** (Cognito).
- Database: **DynamoDB** on-demand (pay-per-request), single-table.
- Arquivos: **S3 privado** para imagens dos pacientes, acessado só por URL pré-assinada.

**Key dependencies:**

- Mangum (adaptador ASGI → Lambda)
- Amazon Cognito (autenticação da equipe)
- AWS SAM (Infraestrutura como Código)
- Route 53 + ACM (domínio + SSL — opcional)

## Scope

**v1 includes:**

- CRUD de pacientes (cadastro, edição, listagem, remoção)
- Backend Lambda único com roteamento interno das rotas
- Provisionamento da infraestrutura base via SAM (Lambda, API Gateway, DynamoDB)

**Explicitly out of scope (v1)** — registro histórico; o que já foi entregue desde então está marcado:

- ✅ Registro de sessões/aparelhos — entregue (M2)
- ✅ Login da equipe via Cognito — entregue (M3)
- ✅ Upload de arquivos/anexos em S3 — entregue (Imagens do Paciente, 2026-08-07)
- ⏳ Frontend definitivo (spec "impecable") — **ainda pendente**; o front atual (React+Vite) é o do demo, promovido a produção

## Constraints

- Técnico: uma única função Lambda com roteamento interno; DynamoDB on-demand; sem instâncias ociosas.
  O código roda sem Docker; o **build** oficial usa container (AD-006) só para gerar as wheels Linux —
  ver o atalho sem Docker em `.specs/codebase/ARQUITETURA.md`.
- Ambiente de dev: máquina com **7,7 GB de RAM** — o Docker Desktop não sobe junto com o VS Code.
- Custo: manter dentro do free tier ($0–$5/mês).
- Recursos: projeto de clínica pequena, tráfego baixo e intermitente.
