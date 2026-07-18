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

- Frontend: SPA estática hospedada em **S3 + CloudFront**. Framework **a definir** — será especificado à parte via spec "impecable".
- Backend: **Python** com **FastAPI + Mangum**, deploy em **AWS Lambda** via ZIP (sem Docker).
- API: **API Gateway** (HTTP, integração proxy) — roteamento, CORS, auth (Cognito), rate limiting.
- Database: **DynamoDB** on-demand (pay-per-request).

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

**Explicitly out of scope (v1):**

- Registro de sessões/aparelhos (milestone seguinte)
- Login da equipe via Cognito (milestone seguinte)
- Upload de arquivos/anexos em S3 (futuro)
- Frontend definitivo (será especificado separadamente via "impecable")

## Constraints

- Técnico: sem Docker; uma única função Lambda com roteamento interno; DynamoDB on-demand; sem instâncias ociosas.
- Custo: manter dentro do free tier ($0–$5/mês).
- Recursos: projeto de clínica pequena, tráfego baixo e intermitente.
