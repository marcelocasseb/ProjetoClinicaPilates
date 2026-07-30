# Auth (Cognito) — Tasks

Feature **Complexa** (novo domínio: Cognito, JWT, provisionamento, infra nova). Deriva de `spec.md` (AUTH-01..09) e `context.md` (D1–D4).

## Design notes (decisões de implementação)

- **Claims → FastAPI:** o JWT Authorizer do HTTP API injeta as claims em `event.requestContext.authorizer.jwt.claims`. Com Mangum, o evento fica em `request.scope["aws.event"]`. `get_clinic_id` e um helper `get_claims(request)` leem de lá. (D4)
- **Teste sem authorizer (baixo atrito):** o `conftest` instala `app.dependency_overrides[get_clinic_id]` reproduzindo o comportamento antigo de header (`X-Clinic-Id or default`). Assim os **180 testes atuais passam sem alteração**; testes novos cobrem a extração real de claim. Idem override para o papel (`get_current_role`).
- **Front (lib):** `amazon-cognito-identity-js` (SRP, leve, sem Amplify inteiro). Trata `newPasswordRequired`. → App Client com `ALLOW_USER_SRP_AUTH` + `ALLOW_REFRESH_TOKEN_AUTH` (sem client secret; SPA público).
- **Segurança do App Client (AD-012):** `WriteAttributes` **exclui** `custom:clinicId` e `custom:role` (usuário nunca altera a própria clínica/papel); `ReadAttributes` os inclui (viajam no idToken).
- **Provisionamento compartilhado:** script CLI (AUTH-01) e endpoint de membro (AUTH-07) chamam o mesmo helper `cognito_admin.criar_usuario(...)`.
- **Sequência de deploy (não quebrar o demo no ar):**
  - **Fase A (aditiva, deploy isolado seguro):** T1 (User Pool + App Client) + T2 (script). Demo segue no header, intacto.
  - **Fase B (cutover, deploy tudo junto):** T3 (authorizer) + T4 (get_clinic_id) + T5 (membros) + T6 (front). É quando o header morre e o login entra.

## Tasks

### Fase A — provisionamento (aditivo)

- [x] **T1 — User Pool + App Client no `template.yaml`** (AUTH-02) ✅ `sam validate --lint` OK
  - **Where:** `template.yaml`
  - **Done when:** `AWS::Cognito::UserPool` (login por email; `AllowAdminCreateUserOnly=true`; schema `clinicId`, `role` string mutáveis; MFA off; `PreventUserExistenceErrors`) + `AWS::Cognito::UserPoolClient` (SRP+refresh, sem secret, `WriteAttributes` sem custom:*). Outputs: `UserPoolId`, `UserPoolClientId`, `UserPoolProviderUrl`. `sam validate --lint` OK.
  - **Tests:** validação de template (sem teste unitário); verificação real no deploy.

- [x] **T2 — Helper de provisionamento + script CLI "criar clínica + admin"** (AUTH-01) ✅ 4 testes verdes (suíte 184)
  - **Where:** `src/app/cognito_admin.py` (helper boto3), `scripts/criar_clinica.py` (CLI), `tests/test_cognito_admin.py`
  - **Reuses:** boto3 (já dep do repositório)
  - **Done when:** `cognito_admin.criar_usuario(email, clinic_id, role)` faz `AdminCreateUser` (`MessageAction=SUPPRESS`, senha temporária gerada, carimba `custom:clinicId`/`custom:role`) e retorna `{email, senha_temporaria}`; o script gera `clinicId` novo, chama o helper com `role=admin`, imprime clinicId+senha; e-mail duplicado → erro claro sem clinicId órfão.
  - **Tests:** moto `mock_aws` (cognito-idp) — cria pool+client, roda o helper, confere atributos do usuário criado; caso e-mail duplicado.
  - **Gate:** `pytest -q` verde.

### Fase B — cutover (deploy tudo junto)

- [x] **T3 — JWT Authorizer no HTTP API; `/health` público** (AUTH-03) ✅ CORS movido p/ API GW (preflight não passa pelo authorizer); CORSMiddleware removido do app; `sam validate --lint` OK
  - **Where:** `template.yaml`
  - **Done when:** authorizer JWT (issuer = User Pool, audience = App Client) como default nas rotas; `/health` com `Auth: Authorizer: NONE`. Sem token → 401 na borda.
  - **Tests:** verificação real no deploy (401 sem token, 200 com token).

- [x] **T4 — `get_clinic_id` lê a claim; helper `get_claims`; conftest override** (AUTH-04, AUTH-06) ✅ + `get_current_role`/`require_admin` (adianta T5); 9 testes em test_deps.py; suíte 192 verde
  - **Where:** `src/app/deps.py`, `tests/conftest.py`, `tests/test_deps.py`
  - **Done when:** `get_claims(request)` extrai claims do `aws.event`; `get_clinic_id` retorna `custom:clinicId` (sem clinicId → 401/403, nunca `default`; header ignorado). `conftest` instala override reproduzindo header p/ os 180 testes existentes.
  - **Tests:** `test_deps.py` — extrai clinicId de evento simulado; sem claim → erro. Suíte inteira segue verde.
  - **Gate:** `pytest -q` verde (180 + novos).

- [x] **T5 — Endpoint `POST /membros` (admin-only)** (AUTH-07, AUTH-08) ✅ router+schema_membro; IAM `AdminCreateUser` + env `USER_POOL_ID` no template; 6 testes (admin-201/membro-403/sem-role-403/corpo-ignorado/dup-409/email-400); suíte 198
  - **Where:** `src/app/routers/membros.py`, fiar em `main.py`, `tests/test_membros.py`, `deps.get_current_role`
  - **Reuses:** `cognito_admin.criar_usuario` (T2)
  - **Done when:** admin cria membro herdando `clinicId` do token, `role=membro`, retorna senha temporária; `role=membro`/sem role → 403 (fail-closed); email duplicado → 409/400; clinicId/role do corpo ignorados.
  - **Tests:** admin cria (201), membro barrado (403), duplicado, isolamento (clinicId vem do token).
  - **Gate:** `pytest -q` verde.

- [x] **T6 — Front: login real + Bearer + logout + adicionar membro** (AUTH-05, parte AUTH-07) ✅ CÓDIGO (E2E no browser pendente — sandbox sem rede/Playwright; teste real = T7). `auth.js` (fetch puro Cognito USER_PASSWORD_AUTH + NEW_PASSWORD_REQUIRED + decode JWT verificado em node), `Login.jsx` reescrito, `api.js` (Bearer, 401→logout, membrosApi), `App.jsx` (auth + Sair + botão "+ Membro" só admin), `AdicionarMembro.jsx`, CSS. `npm run build` OK.
  - **Where:** `frontend/src/components/Login.jsx` (email+senha + NEW_PASSWORD_REQUIRED), `frontend/src/auth.js` (novo, wrap do cognito-identity-js), `frontend/src/api.js` (Bearer, remove X-Clinic-Id), `frontend/src/App.jsx` (logout, lê clínica/role da claim), `frontend/src/config.js` (poolId/clientId via VITE_*), tela "adicionar membro" (admin)
  - **Done when:** logar com senha temporária → troca de senha → entra; toda chamada manda `Authorization: Bearer <idToken>`; "Sair" limpa tokens; admin vê botão "adicionar membro" (membro não); erro de login legível.
  - **Tests:** verificação via Playwright com Cognito/API mockados ([[front-verify-mock-sandbox]]); teste manual real no deploy.

- [x] **T7 — Deploy da Fase B + smoke-test + provisionar demo** (AUTH-09, Success Criteria) ✅ DEPLOYADO e NO AR. Backend (`sam build --use-container; sam deploy`) + front publicado no CloudFront. Verificado end-to-end via curl/CLI: /health 200, /pacientes sem token 401, login completo (InitiateAuth→NEW_PASSWORD→idToken→/pacientes 200), /membros admin 201. Admin `marcelo.casseb@gmail.com` criado em `clinica-zen`. User Pool `us-east-1_tusTZNRL6`, Client `6cke2rskmcq3ogim7c7ns4qqbn`.
  - **Where:** terminal do usuário (SAM/AWS/Docker)
  - **Done when:** `sam build --use-container; sam deploy`; publicar front; rodar `scripts/criar_clinica.py` p/ Zen e Corpo; login real ponta a ponta; 401 sem token; membro não adiciona membro.
  - **Nota:** só o usuário roda (SAM não está no PATH da sessão automatizada; sem egress/Docker aqui).

## Traceability (atualizar conforme conclui)

| Req | Task(s) | Status |
| --- | ------- | ------ |
| AUTH-01 | T2 | ✅ Código+testes (deploy pendente Fase B/T7) |
| AUTH-02 | T1 | ✅ Template (deploy pendente T7) |
| AUTH-03 | T3 | ✅ Template (deploy pendente T7) |
| AUTH-04 | T4 | ✅ Código+testes (deploy pendente T7) |
| AUTH-05 | T6 | ✅ Código (E2E real = T7) |
| AUTH-06 | T4 | ✅ Código+testes (deploy pendente T7) |
| AUTH-07 | T5, T6 | ✅ Código+testes (back); front pronto (E2E = T7) |
| AUTH-08 | T5 | ✅ Código+testes |
| AUTH-09 | T3, T4, T6, T7 | Pending |
