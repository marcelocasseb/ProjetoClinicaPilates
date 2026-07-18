# Infraestrutura Base (SAM) Specification

## Problem Statement

Nenhuma feature de negócio (a começar pelo Cadastro de Pacientes) pode rodar sem a fundação serverless provisionada: a função Lambda que executa o backend, a porta de entrada HTTP (API Gateway) e a tabela DynamoDB onde os dados vivem. Esta feature entrega esse esqueleto deployável — um "hello world" de ponta a ponta — sobre o qual o CRUD de pacientes (e tudo depois) é construído.

## Goals

- [ ] Um `template.yaml` (AWS SAM) que provisiona Lambda + API Gateway (HTTP, proxy) + tabela DynamoDB on-demand.
- [ ] Uma função Lambda em Python (FastAPI + Mangum) com roteamento interno, respondendo a um endpoint de health.
- [ ] Deploy reproduzível via `sam build` + `sam deploy`, com CORS habilitado.
- [ ] Tabela única seguindo a convenção de chaves do AD-005 (`PK`/`SK`).

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Endpoints de negócio (CRUD de pacientes) | Feature separada — esta entrega só o esqueleto + health |
| Autenticação Cognito | M3; API Gateway fica aberto por ora |
| Domínio próprio (Route 53 + ACM) | M4 |
| Frontend / S3 + CloudFront | Spec "impecable" (M4) |
| CI/CD automatizado | Futuro; deploy manual via SAM CLI por ora |
| GSIs para relatórios | Deferido (AD-005); só a tabela base com PK/SK |

---

## User Stories

### P1: Esqueleto deployável com health check ⭐ MVP

**User Story**: Como desenvolvedor, quero uma stack SAM que sobe Lambda + API Gateway + DynamoDB e responde a um health check, para ter uma fundação testável onde as features de negócio entram.

**Why P1**: É o pré-requisito de todas as demais features; sem isso nada roda de ponta a ponta.

**Acceptance Criteria**:

1. WHEN `sam build && sam deploy` é executado com credenciais AWS válidas THEN o sistema SHALL provisionar Lambda, API Gateway HTTP (proxy) e uma tabela DynamoDB on-demand.
2. WHEN uma requisição `GET /health` chega ao API Gateway THEN a Lambda SHALL responder `200` com um corpo JSON simples (ex: `{"status":"ok"}`).
3. WHEN a Lambda é invocada THEN ela SHALL usar FastAPI + Mangum com roteamento interno (uma função para todas as rotas).
4. WHEN uma rota inexistente é chamada THEN o sistema SHALL responder `404` (comportamento padrão do FastAPI).
5. WHEN o navegador faz uma requisição cross-origin THEN o API Gateway/Lambda SHALL retornar os headers CORS apropriados.

**Independent Test**: Após o deploy, `curl https://<api-url>/health` retorna `200 {"status":"ok"}`.

---

### P1: Tabela DynamoDB conforme convenção AD-005 ⭐ MVP

**User Story**: Como desenvolvedor, quero a tabela única já criada com o esquema de chaves definido, para que as features de negócio apenas gravem seus itens.

**Why P1**: O modelo single-table é compartilhado; a tabela precisa existir antes de qualquer CRUD.

**Acceptance Criteria**:

1. WHEN a stack é provisionada THEN o sistema SHALL criar uma tabela DynamoDB com `PK` (partition, String) e `SK` (sort, String).
2. WHEN a tabela é criada THEN ela SHALL usar modo de cobrança `PAY_PER_REQUEST` (on-demand).
3. WHEN a Lambda precisa acessar a tabela THEN ela SHALL receber o nome da tabela via variável de ambiente e ter permissão IAM de leitura/escrita apenas nessa tabela (menor privilégio).

**Independent Test**: `aws dynamodb describe-table --table-name <nome>` mostra `PK`/`SK` e `PAY_PER_REQUEST`.

---

## Edge Cases

- WHEN o SAM CLI não está instalado THEN o deploy falha localmente (ver Blocker B-001) — o `template.yaml` e o código ficam prontos mesmo assim.
- WHEN a Lambda lança exceção não tratada THEN o sistema SHALL retornar `500` sem vazar stack trace no corpo (tratamento genérico do FastAPI).
- WHEN o runtime alvo é definido THEN SHALL ser `python3.13` (Lambda não suporta 3.14; Python local é só para desenvolvimento).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| INFRA-01 | P1: template SAM provisiona Lambda+APIGW+Dynamo | - | Pending |
| INFRA-02 | P1: endpoint /health responde 200 | - | Pending |
| INFRA-03 | P1: FastAPI+Mangum com roteamento interno | - | Pending |
| INFRA-04 | P1: CORS habilitado | - | Pending |
| INFRA-05 | P1: tabela PK/SK on-demand (AD-005) | - | Pending |
| INFRA-06 | P1: IAM menor privilégio + env var do nome da tabela | - | Pending |

**ID format:** `INFRA-[NUMBER]`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 6 total, 0 mapped to tasks, 6 unmapped ⚠️

---

## Success Criteria

- [ ] `sam deploy` sobe a stack sem erros (uma vez o SAM CLI instalado).
- [ ] `GET /health` retorna `200 {"status":"ok"}` pela URL do API Gateway.
- [ ] Tabela DynamoDB existe com `PK`/`SK` on-demand.
- [ ] Lambda tem permissão apenas na sua tabela (menor privilégio).
- [ ] Estrutura de projeto Python pronta para receber os endpoints de pacientes.
