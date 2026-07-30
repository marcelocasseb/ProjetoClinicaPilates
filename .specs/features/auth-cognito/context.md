# Auth (Cognito) — Decisões de Contexto (Discuss)

Decisões do usuário para as áreas cinzentas, capturadas em 2026-07-28. Complementam o **AD-012** (provisionamento e binding usuário↔clínica) e o **AD-007** (uso do clinicId no isolamento).

## D1 — Onboarding de clínica nova = **script CLI local** (não endpoint web)

O comando "criar clínica + 1º admin" roda **na máquina do dono** com credencial AWS admin (boto3). Ele:
1. **gera** um `clinicId` novo (único ponto onde um clinicId nasce — AD-012);
2. cria o admin via `AdminCreateUser` carimbando `custom:clinicId` (o novo) e `custom:role=admin`;
3. imprime `clinicId` + senha temporária para o operador.

**Por quê:** zero superfície de ataque — o nascimento de clínica nunca fica exposto na internet. Foi o combinado no STATE ("script/comando criar clínica+admin").
**Trade-off:** onboarding self-service (tela web) fica **deferido** (já estava nas Deferred Ideas).

## D2 — Primeira senha = **temporária mostrada a quem cria** (SUPPRESS e-mail)

`AdminCreateUser` usa `MessageAction=SUPPRESS` (Cognito **não** envia e-mail). A senha temporária é **exibida a quem criou** (o operador do CLI para o admin; o painel do admin para o membro) e repassada fora de banda. No 1º login o Cognito força a troca (`NEW_PASSWORD_REQUIRED`).

**Por quê:** não depende de SES/domínio verificado — funciona no demo e em produção sem infra de e-mail.
**Trade-off:** repasse manual da senha temporária; convite por e-mail fica deferido.

## D3 — Papéis = **admin vs membro (mínimo)**

Dois papéis só, guardados em `custom:role` (`admin` | `membro`):
- **admin**: tudo + pode **adicionar membro**;
- **membro**: tudo nos dados da clínica (pacientes/aparelhos/aulas), **menos** adicionar membro.

Roles granulares (recepcionista, fisio etc. via Cognito groups) ficam **deferidos** (Deferred Ideas do STATE).

## D4 — Verificação do token = **JWT Authorizer do API Gateway** (borda)

O HTTP API valida assinatura/expiração do token Cognito **antes** da Lambda. As claims (incl. `custom:clinicId` e `custom:role`) chegam no **request context** do evento; `get_clinic_id` passa a lê-las de lá (em vez do header `X-Clinic-Id`). Token ausente/inválido/expirado → **401 na borda** (nem chega na Lambda).

**Por quê:** menos código, padrão AWS, a Lambda nunca roda em requisição não autenticada.
**Trade-off:** teste local dos routers precisa injetar claims simuladas (fixture) já que não há authorizer localmente — resolver na fase de Design/Tasks.

## Fonte de verdade da autenticação (resumo)

- **Autenticação** ("quem é você") = Cognito User Pool + JWT Authorizer (borda).
- **Autorização/isolamento** ("só a sua clínica") = filtro por `clinicId` **do token** — os `_pk()` dos repositórios já prefixam `CLINIC#<clinicId>#` (AD-007), então o isolamento já está pronto; só muda a **fonte** do clinicId.
- **Autorização de papel** ("só admin adiciona membro") = checagem de `custom:role` no endpoint de provisionamento de membro.
