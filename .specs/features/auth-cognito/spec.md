# Autenticação (Cognito) — Login real e provisionamento Specification

## Problem Statement

Hoje o "login" é um **andaime**: o front mostra um seletor de clínicas chumbadas ([[Login.jsx]]) e manda o `clinicId` num header `X-Clinic-Id` que **qualquer um pode forjar** — não há autenticação nenhuma, e o demo está no ar com link aberto. O isolamento multi-tenant (AD-007) já existe no back (os `_pk()` prefixam `CLINIC#<clinicId>#`), mas ele confia num header, não numa identidade. Esta feature (M3) fecha esse buraco: **usuários reais** (email+senha via Cognito), com o `clinicId` viajando num **token assinado pela AWS** (não mais escolhido pelo usuário), e um **fluxo de provisionamento** (AD-012) que deixa o dono do produto criar clínicas e admins sem depender do console AWS, e o admin criar sua equipe.

## Goals

- [x] Criar um **AWS Cognito User Pool** com atributos customizados `custom:clinicId` e `custom:role`, auto-cadastro público **desligado** (`AllowAdminCreateUserOnly=true`).
- [x] Proteger a API com **JWT Authorizer** no HTTP API: token inválido/ausente/expirado → **401 na borda**.
- [x] Trocar a fonte do `clinicId` em `get_clinic_id` ([[deps.py]]): de header `X-Clinic-Id` → **claim do token**. Só essa função muda; routers e repositórios continuam iguais.
- [x] **Script CLI local** de onboarding ("criar clínica + 1º admin"): gera `clinicId` novo, cria o admin via `AdminCreateUser` carimbando `custom:clinicId` + `custom:role=admin`, imprime a senha temporária (D1/D2).
- [x] Endpoint **"adicionar membro"** (admin-only): cria usuário herdando o `clinicId` do token do admin, `custom:role=membro`, senha temporária mostrada ao admin (D2/D3).
- [x] **Login real no front** (email+senha) substituindo o seletor de clínica; tratamento de **troca de senha no 1º acesso** (`NEW_PASSWORD_REQUIRED`); token enviado como `Authorization: Bearer` em toda chamada; logout.
- [x] Preservar o isolamento (AD-007): clínica A nunca vê nem altera dados da B — agora ancorado na **identidade**, não no header.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Onboarding self-service de clínica (tela web pública) | D1: nascimento de clínica é via **script CLI local** (zero superfície de ataque). Deferido (Deferred Ideas) |
| Convite por e-mail (Cognito/SES envia senha) | D2: senha temporária é **mostrada a quem cria** (SUPPRESS); e-mail exige SES/domínio. Deferido |
| Roles granulares (recepcionista, fisio via Cognito groups) | D3: só **admin vs membro** neste M3. Deferido (Deferred Ideas do STATE) |
| Um usuário em várias clínicas (seletor pós-login) | AD-012: modelo **1-email→1-clínica** (`custom:clinicId` escalar). Deferido |
| Recuperação de senha (forgot password) via e-mail | Depende de e-mail configurado (SES). Deferido para pós-M3 |
| MFA / federação social (Google, etc.) | Fora do escopo do login básico do M3 |
| Auditoria/log de quem-criou-quem | Não pedido; Cognito já registra criação. Candidato futuro |
| Remover/desativar usuário (CRUD de equipe) | M3 entrega **criar** admin/membro; gestão completa da equipe vira feature própria |

---

## User Stories

### P1: Provisionar clínica + 1º admin via CLI ⭐ MVP

**User Story**: Como dono do produto, quero rodar um comando na minha máquina para criar uma clínica nova e seu primeiro admin, para fazer onboarding de clientes sem depender do console AWS nem de código manual.

**Why P1**: É o **único ponto onde um `clinicId` nasce** (AD-012). Sem ele não há como ter uma clínica real no sistema autenticado.

**Acceptance Criteria**:

1. WHEN o dono roda o script com um e-mail e nome de clínica THEN o sistema SHALL **gerar um `clinicId` novo** e criar um usuário no User Pool via `AdminCreateUser` com `custom:clinicId=<novo>`, `custom:role=admin` e `MessageAction=SUPPRESS`.
2. WHEN o admin é criado THEN o script SHALL **imprimir** o `clinicId` gerado e a **senha temporária** para o operador repassar fora de banda.
3. WHEN o e-mail já existe no pool THEN o script SHALL falhar com mensagem clara (não duplica usuário) e **não** gerar um clinicId órfão.
4. WHEN o script roda THEN ele SHALL usar as **credenciais AWS admin locais** (boto3) e **não** expor nenhuma rota web.

**Independent Test**: Rodar `python scripts/criar_clinica.py --email dono@zen.com --clinica "Clínica Zen"` cria o usuário no pool com os atributos corretos (verificável via `admin-get-user`) e imprime clinicId + senha temporária.

---

### P1: User Pool + JWT Authorizer protegendo a API ⭐ MVP

**User Story**: Como plataforma, quero um User Pool e um authorizer na borda, para que só requisições com token Cognito válido cheguem à Lambda.

**Why P1**: É a fundação da autenticação; sem ela nada mais do M3 se sustenta.

**Acceptance Criteria**:

1. WHEN a infra é deployada THEN o sistema SHALL criar um **Cognito User Pool** + **App Client** (fluxo `USER_PASSWORD_AUTH` habilitado) com atributos customizados `custom:clinicId` (string, mutável só por admin) e `custom:role` (string), e `AllowAdminCreateUserOnly=true` (sem auto-cadastro público).
2. WHEN o App Client é criado THEN ele SHALL **não** ter permissão de escrita sobre `custom:clinicId` (o usuário nunca altera a própria clínica — AD-012).
3. WHEN uma requisição chega **sem** token ou com token inválido/expirado THEN o **JWT Authorizer** SHALL rejeitar com **401** antes de invocar a Lambda.
4. WHEN uma requisição chega com token válido THEN as claims (incl. `custom:clinicId`, `custom:role`, `email`) SHALL estar disponíveis no **request context** do evento para a Lambda ler.
5. WHEN `/health` é chamado THEN ele SHALL permanecer **público** (sem authorizer) para o smoke-test.

**Independent Test**: `GET /pacientes` sem `Authorization` retorna **401**; com um `idToken` válido de um admin retorna **200**.

---

### P1: `get_clinic_id` lê o `clinicId` do token ⭐ MVP

**User Story**: Como sistema multi-tenant, quero derivar o `clinicId` da identidade autenticada (claim do token), para que o isolamento não dependa mais de um header forjável.

**Why P1**: É a troca que transforma o isolamento "de brincadeira" (header) no isolamento real (token). Miolo do M3 no back.

**Acceptance Criteria**:

1. WHEN um endpoint autenticado é chamado THEN `get_clinic_id` ([[deps.py]]) SHALL retornar o `custom:clinicId` extraído das **claims do request context** (não mais do header `X-Clinic-Id`).
2. WHEN o token não traz `custom:clinicId` THEN o sistema SHALL retornar **401/403** (usuário sem clínica não opera) — nunca cair num clinicId "default".
3. WHEN `get_clinic_id` muda THEN **routers e repositórios SHALL permanecer inalterados** (a assinatura de dependência continua entregando uma string clinicId).
4. WHEN o header `X-Clinic-Id` é enviado junto com um token THEN ele SHALL ser **ignorado** (a fonte de verdade é o token).

**Independent Test**: Dois admins de clínicas diferentes chamam `GET /pacientes` com seus tokens; cada um vê só os pacientes da sua clínica; nenhum header influencia o resultado.

---

### P1: Login real no front (email+senha, 1º acesso) ⭐ MVP

**User Story**: Como membro da equipe, quero entrar com e-mail e senha (e definir minha senha no primeiro acesso), para usar o sistema com a minha identidade e ver só a minha clínica.

**Why P1**: A feature só entrega valor com a tela; o seletor de clínica chumbado precisa sair.

**Acceptance Criteria**:

1. WHEN o usuário informa e-mail+senha válidos THEN o front SHALL autenticar no Cognito (`USER_PASSWORD_AUTH`), guardar os tokens e entrar no app.
2. WHEN o Cognito responde `NEW_PASSWORD_REQUIRED` (1º acesso com senha temporária) THEN o front SHALL pedir uma **nova senha** e concluir o desafio (`RespondToAuthChallenge`) antes de entrar.
3. WHEN o usuário está autenticado THEN toda chamada de API ([[api.js]]) SHALL enviar `Authorization: Bearer <idToken>` e **deixar de enviar** `X-Clinic-Id`.
4. WHEN o usuário clica em sair THEN o front SHALL descartar os tokens e voltar à tela de login (o botão "Trocar clínica" vira **"Sair"**).
5. WHEN o e-mail/senha são inválidos THEN o front SHALL exibir uma mensagem de erro legível (sem vazar se o e-mail existe).
6. WHEN o app carrega THEN ele SHALL exibir o **nome/clínica** do usuário logado a partir das claims do token (não mais do seletor).

**Independent Test**: Logar com o admin recém-criado (senha temporária → define nova senha) entra no app; a aba Pacientes lista os pacientes daquela clínica; "Sair" volta ao login.

---

### P2: Admin adiciona membro à equipe

**User Story**: Como admin da clínica, quero adicionar um membro da minha equipe informando o e-mail dele, para que ele acesse o sistema herdando a minha clínica — sem eu mexer no console AWS.

**Why P2**: A clínica opera com 1 admin antes disso; expandir a equipe é o próximo passo natural.

**Acceptance Criteria**:

1. WHEN um **admin** chama `POST /membros` com um e-mail THEN o sistema SHALL criar o usuário via `AdminCreateUser` com `custom:clinicId` = **o clinicId do token do admin** (não do corpo), `custom:role=membro`, `MessageAction=SUPPRESS`, e retornar a **senha temporária** para o admin repassar.
2. WHEN o corpo tenta enviar um `clinicId`/`role` THEN o sistema SHALL **ignorá-los** (o clinicId vem do token; o role é sempre `membro` por esse endpoint).
3. WHEN o e-mail já existe THEN o sistema SHALL retornar erro claro (**409/400**) sem duplicar.
4. WHEN o front recebe a senha temporária THEN ele SHALL **exibi-la ao admin** com aviso de repasse fora de banda (D2).

**Independent Test**: Admin da Clínica Zen cria `membro@zen.com`; o usuário nasce com `custom:clinicId` da Zen e `custom:role=membro`; logar com ele mostra só dados da Zen.

---

### P2: Distinção admin vs membro (autorização de papel)

**User Story**: Como admin, quero que só admins possam adicionar membros, para a equipe não criar contas à revelia.

**Why P2**: Higiene de acesso; o M3 funciona com um admin mesmo sem essa trava, mas ela é necessária ao abrir para membros.

**Acceptance Criteria**:

1. WHEN um usuário com `custom:role=membro` chama `POST /membros` THEN o sistema SHALL rejeitar com **403** (só admin adiciona).
2. WHEN um usuário com `custom:role=admin` chama `POST /membros` THEN o sistema SHALL permitir.
3. WHEN o token não traz `custom:role` THEN o sistema SHALL tratar como **não-admin** (nega o provisionamento — fail-closed).
4. WHEN um membro usa as demais telas (pacientes/aparelhos/aulas) THEN ele SHALL ter **acesso total** aos dados da própria clínica (a distinção de papel só restringe "adicionar membro" — D3).

**Independent Test**: Com um token de `role=membro`, `POST /membros` retorna **403**; com `role=admin`, retorna **201**.

---

## Edge Cases

- WHEN o token está expirado durante o uso THEN a API SHALL retornar **401** e o front SHALL redirecionar ao login (sessão expirada).
- WHEN o script/endpoint tenta criar um usuário com e-mail já existente THEN SHALL falhar claramente **sem** deixar um `clinicId` órfão (no script) nem duplicar (no endpoint).
- WHEN a senha temporária expira antes do 1º login THEN o Cognito SHALL exigir novo provisionamento/reset (documentar; janela padrão do Cognito).
- WHEN a nova senha (no `NEW_PASSWORD_REQUIRED`) não atende à política do pool THEN o front SHALL exibir a regra de senha e não concluir o desafio.
- WHEN alguém envia `X-Clinic-Id` tentando "trocar de clínica" com um token válido THEN o sistema SHALL **ignorar o header** e usar só a claim.
- WHEN um token válido não traz `custom:clinicId` (mal provisionado) THEN o sistema SHALL negar (401/403), não cair no `default`.
- WHEN os testes de back rodam localmente (sem authorizer) THEN eles SHALL **injetar claims simuladas** via override de dependência (o authorizer não existe fora da AWS).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| AUTH-01 | P1: Script CLI criar clínica + 1º admin (gera clinicId, AdminCreateUser) | - | Verified |
| AUTH-02 | P1: User Pool + App Client (custom:clinicId/role, AllowAdminCreateUserOnly) | - | Verified |
| AUTH-03 | P1: JWT Authorizer no HTTP API (401 na borda; claims no request context) | - | Verified |
| AUTH-04 | P1: `get_clinic_id` lê clinicId da claim (não do header); routers/repos intactos | - | Verified |
| AUTH-05 | P1: Front — login email+senha + NEW_PASSWORD_REQUIRED + Bearer token + logout | - | Verified |
| AUTH-06 | P1: Isolamento ancorado na identidade (header ignorado; sem default) | - | Verified |
| AUTH-07 | P2: Endpoint `POST /membros` (herda clinicId do token, role=membro, senha temp) | - | Verified |
| AUTH-08 | P2: Autorização de papel (só admin adiciona membro; fail-closed) | - | Verified |
| AUTH-09 | Edge cases (token expirado→401→relogin; email duplicado; senha fraca; sem clinicId) | - | Verified |

**ID format:** `AUTH-[NUMBER]`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 9 total, 0 mapped to tasks, 9 unmapped ⚠️ (mapear na fase de Tasks)

---

## Notas de Referência (para Design)

- **Fonte das claims (JWT Authorizer HTTP API):** as claims chegam em `event.requestContext.authorizer.jwt.claims`. Com Mangum, o evento fica acessível ao FastAPI (via `request.scope`), então `get_clinic_id` passa a lê-las de lá. Detalhar o acesso exato na fase de Design.
- **Teste local sem authorizer:** os testes usam `app.dependency_overrides[get_clinic_id]` (padrão já usado na suíte) — a troca da fonte não deve quebrar as fixtures; ajustar os overrides para simular claims.
- **Provisionamento compartilhado:** o script CLI (AUTH-01) e o endpoint de membro (AUTH-07) chamam o mesmo `AdminCreateUser`; considerar um helper comum (`cognito_admin.py`) para não duplicar a lógica.
- **Frontend:** avaliar na Design se usa a lib oficial (amazon-cognito-identity-js / Amplify Auth) ou chamadas diretas ao endpoint do Cognito — manter a linha "hand-rolled" leve do front atual pesa a favor de algo enxuto.
- **`get_clinic_id` hoje** ([deps.py](src/app/deps.py)): 1 função, retorna `x_clinic_id or "default"`. A mudança é cirúrgica e localizada (AD-012 / Todo do STATE).
- **Config do front** ([config.js](frontend/src/config.js)): `CLINICS` chumbadas e o seletor saem; entram os dados do User Pool (poolId, clientId, região) via `VITE_*`.

---

## Success Criteria

- [x] O dono cria uma clínica nova e seu admin rodando **um comando local**, e recebe clinicId + senha temporária — sem tocar no console AWS.
- [x] O admin loga com e-mail+senha (define a senha no 1º acesso) e vê **só** a sua clínica; nenhum header troca isso.
- [x] Requisição sem token válido é barrada com **401 na borda** (nem chega na Lambda).
- [x] O admin adiciona um membro pela tela; o membro loga e opera na mesma clínica, mas **não** consegue adicionar outros membros (403).
- [x] O isolamento (AD-007) segue intacto — agora ancorado no token, não no `X-Clinic-Id` — com os testes de isolamento passando via claims simuladas.
- [x] Todos os requisitos (AUTH-01..09) cobertos por teste (back/script) e verificados no front (login real no ar).
