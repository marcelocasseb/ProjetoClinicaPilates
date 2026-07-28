# State

**Last Updated:** 2026-07-27 — **Registro de Sessões (Aula de Pilates): COMPLETO (back + front) e NO AR.** Backend deployado (S1 schemas + S2 repo + S3 router, 44 testes novos → suíte **180 verde**; smoke-test público OK). Front: aba **"Pilates"** publicada no CloudFront — busca aluno → combo de aparelho + chips de treino que montam uma **lista de pares aparelho→treino** ("Exercícios da aula": Mat—Membros superiores, Mat—Membros inferiores, Reformer—Força…; cada linha removível), mesmo aparelho repetível → observação/profissional → salvar; histórico datado no rodapé (mostra aparelhos(treinos) por aula) com consultar/editar/remover. **Modelo de pares veio de UAT (2026-07-28)** — o payload pro back segue agrupado por aparelho (`{nome, treinos[]}`, inalterado). Verificado ponta a ponta (Playwright com API mockada; browser do ambiente não alcança a API real). Feature `registro-sessoes` **concluída**. Commitado e **pushado** (`origin/main`).
**Current Work:** 🎯 **DEMO NO AR** — https://d1th2j57vyxahs.cloudfront.net (HTTPS). Estado atual do produto:
- **Backend** (stack `clinica-pilates`): CRUD de **Pacientes**, **Aparelhos** e **Avaliações/consultas** (por paciente), multi-tenant por clínica (AD-007), **136 tests verdes**, deployado. Avaliação tem campo `observacao` (texto livre, no DynamoDB). CORS tratado no FastAPI (CORSMiddleware).
- **Frontend** (React+Vite em `frontend/`, stack `clinica-pilates-frontend`): login simples (seletor de clínica → `X-Clinic-Id`). **Fluxo de Pacientes em 2 telas (2026-07-24):** (1) tela de **consulta** — campo de busca (nome/CPF/telefone) + botão "+ Adicionar paciente" + lista clicável (sem form à vista); (2) **ficha do paciente** — abre ao clicar numa linha ou em Adicionar: form de dados (máscaras CPF/telefone/CEP + ViaCEP + validação CPF) **e a seção de Avaliações/consultas embutida** (só liberada após salvar o paciente novo). Avaliação: título "Nova avaliação/consulta" + campo largo **Observação** no rodapé. Aparelhos em aba separada. CRUD completo. Hospedado em S3+CloudFront. Dados de demo semeados (Zen/Corpo).
- Local: `cd frontend; npm run dev` → http://localhost:5173.

**Polimento de UX da avaliação (2026-07-24, no ar):** fluxo de Pacientes em 2 telas (consulta+ficha); campo **Observação** (largo, no DynamoDB); validações de front (nome obrigatório; avaliação em branco bloqueada); fluxo **consultar → Editar → Salvar** (consulta abre em leitura, botão Editar destrava). Três bugs de front caçados e resolvidos: tradução do Chrome ([[browser-autotranslate-front]]), cache do index.html (agora `no-cache`), e submit-fantasma por type-swap de botão ([[react-button-type-swap-submit]]).

⏭️ **AO RETOMAR ("continuar"):** nada pendente/quebrado — **Registro de Sessões concluído** (back + front no ar) e **aprovado no UAT do usuário (2026-07-28)**: front de Pilates usa **lista de pares aparelho→treino** (ver descrição acima). Tudo commitado e pushado (`origin/main`), árvore limpa. O demo tem 3 abas: **Pacientes**, **Aparelhos**, **Pilates** (aula). **Próximo passo = ESCOLHER a frente** (perguntar ao usuário):
1. **Cognito** (login real, M3; troca só o `get_clinic_id` no back — ver Todos) → tela de login no front.
2. **Front definitivo** (spec "impecable", idealmente com feedback do cliente).
3. **Polimento extra do Pilates** (ex.: banner de nº de aulas na ficha do paciente igual ao de consultas; seed de aula de demo pro pitch; ordenar/agrupar a lista de pares).
4. Ideias deferidas: detalhe estruturado por aparelho (séries/reps/carga), tipos de treino editáveis por clínica.
⚠️ **Teste manual recomendado:** a verificação do front rodou com API **mockada** (o browser do ambiente automatizado não tem egress de rede — [[front-verify-mock-sandbox]]). Vale um teste manual rápido no demo contra a API viva (Clínica Zen/Corpo têm aparelhos+alunos semeados).

**Recursos AWS provisionados (stack `clinica-pilates`, us-east-1):**
- API base: https://8f1ffym997.execute-api.us-east-1.amazonaws.com
- Tabela DynamoDB: `clinica-pilates-ClinicaTable-8YQAEIFAKZGE` (PK/SK, on-demand)
- Lambda: `clinica-pilates-ClinicaApiFunction-3huxBJXkP1qi`
- Redeploy backend: `sam build --use-container; sam deploy` (config em samconfig.toml)

**Frontend hospedado (stack SEPARADO `clinica-pilates-frontend`, us-east-1):**
- 🔗 Site (demo): https://d1th2j57vyxahs.cloudfront.net
- Bucket S3 (privado): `clinica-pilates-frontend-sitebucket-n6oomystbesc`
- CloudFront DistributionId: `EGYNGZONKGVLT` (OAC, HTTPS, PriceClass_All)
- Template: `frontend-infra.yaml` (CloudFormation puro, sem Docker/SAM)
- **Publicar/atualizar o site** (sem Docker) — ⚠️ headers de cache IMPORTAM (senão o navegador segura um `index.html` velho apontando pra JS antigo → "não atualiza"):
  1. `cd frontend; npm run build`
  2. assets com hash = imutáveis (cache longo), **exceto** o index.html:
     `aws s3 sync frontend/dist s3://clinica-pilates-frontend-sitebucket-n6oomystbesc --delete --exclude "index.html" --cache-control "public, max-age=31536000, immutable"`
  3. index.html sempre revalidado:
     `aws s3 cp frontend/dist/index.html s3://clinica-pilates-frontend-sitebucket-n6oomystbesc/index.html --cache-control "no-cache, must-revalidate" --content-type "text/html"`
  4. `aws cloudfront create-invalidation --distribution-id EGYNGZONKGVLT --paths "/*"` (limpa o cache do CDN)
- Custo: dentro do free tier (~$0). Budget de $5/mês criado (alerta e-mail em 80%/100%).
- ⚠️ Link ABERTO (sem login ainda) — dados de demo Zen/Corpo semeados. Autenticação real = M3 (Cognito).

**Onde paramos (retomar aqui):**
- ✅ Projeto inicializado (PROJECT/ROADMAP/STATE), commit `621b608`
- ✅ Planejamento da infra + TESTING.md commitados, commit `8e855b6`
- ✅ Decisão de banco: DynamoDB single-table (AD-005)
- ✅ Spec `cadastro-pacientes` escrita (PAC-01..09) — aguarda infra
- ✅ Spec + tasks `infra-base-sam` (INFRA-01..06, T1..T6)
- ✅ Convenção de testes: pytest + moto, cobertura pragmática (TESTING.md)
- ✅ **T1 scaffold done** (`6d3fc75`): src/app, tests/, requirements, pyproject, .gitignore; venv `.venv` criado, deps instaladas OK no Python 3.14
- ✅ **T2 done**: `src/app/main.py` (FastAPI + GET /health) + `tests/test_health.py` (2 testes verdes)
- ✅ **T3 done**: `src/app/handler.py` (Mangum) + `tests/test_handler.py` (smoke test v2, 200) — 3 testes no total
- ✅ **T4+T5 done**: `template.yaml` (Lambda py3.13 + HTTP API proxy + CORS + DynamoDB PK/SK on-demand + IAM DynamoDBCrudPolicy + TABLE_NAME). Validado: `sam validate --lint` OK
- ✅ **T6 done**: `sam build --use-container` + `sam deploy` → stack `clinica-pilates` no ar; `/health` → `{"status":"ok"}`
- ✅ SAM CLI 1.163.0 instalado → **B-001 resolvido**; Docker build → **B-002 resolvido** (AD-006)
- ✅ **Feature `infra-base-sam` COMPLETA**
- ✅ **Feature `cadastro-pacientes` COMPLETA no código** (tasks.md T1–T4):
  - T1: `src/app/schemas.py` (Pydantic — nome obrigatório, email regex, dataNascimento YYYY-MM-DD, vazios→None, extra ignorado)
  - T2: `src/app/repository.py` (`PacienteRepository` — create/get/list_ativos/update/soft_delete; PK=CLIENT#id, SK=PROFILE; testes moto)
  - T3: `src/app/routers/pacientes.py` (POST /pacientes, GET /pacientes/{id}) fiado em `main.py` via `include_router`
  - T4: mesmo router — GET /pacientes (listar ativos), PUT /pacientes/{id}, DELETE /pacientes/{id} (soft delete, 204)
  - Suíte: 45 tests verdes (`.\.venv\Scripts\python.exe -m pytest -q`)
  - Ajuste pós-review: validação retorna 400 com msg legível (`nome é obrigatório`, `email inválido`); DELETE retorna 200 `{"detail":"Paciente removido com sucesso"}` / 404 `{"detail":"Paciente não encontrado"}`
  - ✅ **DEPLOYADO** (`sam build --use-container` + `sam deploy`): `/pacientes` no ar; smoke-test público OK
- ✅ **Milestone M1 CONCLUÍDO**
- ✅ **Refactor multi-tenant + cpf + endereço CONCLUÍDO e DEPLOYADO** (2026-07-21, R1–R4):
  - R1: `schemas.py` — `cpf` validado (AD-008) + submodelo `Endereco` (AD-009) — commit `2137b16`... (ver git)
  - R2/R3/R4: chave `CLINIC#<clinicId>#CLIENT#<id>`, GSI1 (`template.yaml` + `conftest.py`), `get_clinic_id` (header `X-Clinic-Id` / default; token no M3), isolamento testado
  - Chave multi-tenant escolhida: **cliente-na-PK + GSI** (não clínica-na-PK) — preserva "ficha do paciente = 1 Query por PK" (AD-005). B-003 resolvido.
- ✅ **Feature `avaliacao-pacientes` COMPLETA no BACK e no FRONT, no ar** (2026-07-22..24, AD-010): CRUD de **avaliações por paciente** como histórico datado. Front: `frontend/src/components/Avaliacoes.jsx` (form + lista datada) via link "avaliações" na linha do paciente; `avaliacoesApi` em `api.js`; publicado no CloudFront. O front envia `data` explícita (fuso local), contornando o desvio UTC do back. **Polido pós-review (2026-07-24):** botão "Salvar avaliação", campos PA/FC alinhados pela base (`.row { align-items: flex-end }`), rótulos sem "(opcional)". Paciente de demo completo semeado em `clinica-corpo` (Mariana Oliveira Souza, CPF válido fictício). `PK=CLINIC#<clinicId>#CLIENT#<pacienteId>`, `SK=AVALIACAO#<id>` (sob o paciente, AD-005). Campos definidos pelo cliente (diagnosticoMedico, queixaPrincipal, hma, pressaoArterial, fc, `avaliacaoPostural` MAP, `medidas` MAP, inspecaoGeral, examesComplementares) — todos texto livre e opcionais; `data` default hoje. Endpoints aninhados `/pacientes/{id}/avaliacoes` (POST/GET/PUT/DELETE) com 404 se paciente inexistente na clínica (dependência de router). 3 tasks (A1 schemas, A2 repo, A3 router), 38 testes novos (suíte 135). Smoke-test público OK (ciclo completo + isolamento + validações). ⚠️ Nota: `data` default usa a data **UTC** — perto da meia-noite pode divergir do fuso BR; o front deve enviar `data` explícita.
- ⏭️ FAZER A SEGUIR: **M2 — Registro de Sessões e Aparelhos**. Escrever a spec (endpoints de sessão por paciente, `SK=SESSION#<data>` com lista denormalizada de aparelhos/exercícios), **sob a mesma PK multi-tenant** (`CLINIC#<clinicId>#CLIENT#<clientId>`). Rodar app local: `TABLE_NAME=clinica-pilates-ClinicaTable-8YQAEIFAKZGE .venv\Scripts\python -m uvicorn app.main:app --app-dir src --reload` (header `X-Clinic-Id` opcional). Deploy: `sam build --use-container; sam deploy` (Docker aberto).

**Ambiente local:** venv em `.venv` (Python 3.14). Testes: `.\.venv\Scripts\python.exe -m pytest -q`.
**SAM CLI:** não está no PATH da sessão automatizada; caminho completo = `C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd` (no terminal do usuário, `sam` funciona direto).

---

## Recent Decisions (Last 60 days)

### AD-012: Provisionamento de usuários e binding usuário↔clínica (planejado, M3) (2026-07-28)

**Decision:** O vínculo usuário↔clínica é um atributo **imutável pelo usuário** gravado **no ato de criação da conta**, nunca escolhido no login. Detalhes:
- **Onde fica gravado:** atributo `custom:clinicId` (valor **único/escalar**) no registro do usuário no Cognito User Pool. Por ser escalar, um usuário pertence a exatamente **uma** clínica (não há lista) — modelo 1-login→1-clínica.
- **A clínica NÃO faz parte do login:** a tela de login (M3) pede só e-mail+senha. O `custom:clinicId` viaja no token (assinado pela AWS) e o back o lê de lá. O **seletor de clínica atual** (`frontend/src/components/Login.jsx`, andaime do demo) **some** no M3.
- **Quem grava (cadeia de confiança):**
  - *1º admin de uma clínica nova:* criado pela **plataforma/super-admin (= o dono do produto)** no onboarding da clínica; o back **gera** o `clinicId` novo e carimba no admin. Único ponto onde um `clinicId` novo nasce.
  - *Demais usuários (equipe):* criados pelo **admin da própria clínica** via tela "adicionar membro"; o endpoint do back grava `custom:clinicId` = **o clinicId do admin, lido do token dele** (não de um campo do form). Assim o admin só cria gente na própria clínica.
- **Segurança (Cognito):** desligar auto-cadastro público (`AllowAdminCreateUserOnly=true`); não dar permissão de escrita do `custom:clinicId` ao app client; criação de conta via `AdminCreateUser` (back com credencial de admin).
- **Enforcement (já meio pronto):** `get_clinic_id` (`src/app/deps.py`) passa a ler o claim do token (hoje lê o header); os `_pk()` dos repositórios já prefixam `CLINIC#<clinicId>#`, confinando toda query à partição da clínica. Pedir id de outra clínica → chave montada com o clinicId do token → 404.

**Reason:** Fecha o buraco de "usuário se auto-atribui a qualquer clínica" (o valor nunca é escolhido pelo usuário nem passa no corpo/URL). Complementa AD-007 (que definia o *uso* do clinicId, mas não o *provisionamento*).
**Trade-off:** 1-email→1-clínica; pessoa que atue em 2 clínicas precisa de 2 contas (ou o modelo multi-clínica-por-usuário, que fica deferido — aí sim entraria um seletor **pós-login** mostrando só as clínicas já vinculadas àquela conta).
**Impact (M3):** trocar a fonte do `clinicId` em `get_clinic_id`; criar endpoint de provisionamento (`AdminCreateUser` carimbando o clinicId do admin) + tela "adicionar membro"; onboarding de clínica (gera clinicId). Ver Todos e ideias deferidas (roles via Cognito groups; onboarding self-service).

### AD-011: Registro de Sessões (Aula) — `SK=SESSION#<id>` com `aparelhos` snapshot em lista de maps (2026-07-27)

**Decision:** A aula de Pilates é um **item time-series** sob a PK do paciente (`PK=CLINIC#<clinicId>#CLIENT#<pacienteId>`, `SK=SESSION#<id>`, id no SK como AD-010 — permite +1 aula/dia e CRUD por id trivial). A aula carrega `data` (default hoje, front envia explícita), `profissional` e `observacao` (texto livre, opcionais) e um campo **obrigatório** `aparelhos`: **lista de maps** `{aparelhoId, nome, treinos[]}` com **≥1 item**. Cada aparelho é um **snapshot** (id+nome copiados no registro) — o back **não revalida** contra o catálogo, deixando o histórico imune a edição/remoção posterior do aparelho (mesma lógica do soft delete de aparelho, APR-07). Os **tipos de treino** vêm de uma lista **fixa hardcoded no front** (Membros superiores, Membros inferiores, Abdômen, Força, Mobilidade); o back só guarda os textos escolhidos (sem enum server-side, coerente com o cadastro flexível do resto). Treinos ficam **por aparelho** (não no nível da aula); observação/profissional são **gerais da aula**.
**Reason:** Casa com o modelo centrado no cliente (AD-005) — "última aula / evolução" = 1 Query por PK + `begins_with`. Espelha a arquitetura de `avaliacao-pacientes` (router aninhado com dependência que exige paciente ativo → 404/isolamento). O snapshot é o que torna o histórico confiável mesmo com o catálogo mudando.
**Trade-off:** Ordenação por data na aplicação (não no SK) — aceito no volume esperado. `aparelhos` é o único campo obrigatório (uma aula sem aparelho não faz sentido) → 400 legível via handler global.
**Impact:** `schemas_sessao.py`, `repository_sessao.py`, `routers/sessoes.py`, fiação no `main.py`. SES-01..11; 44 testes (suíte 180). Deployado na stack `clinica-pilates`. Front (aba "Pilates") pendente.

### AD-010: Avaliação do paciente — histórico datado com `SK=AVALIACAO#<id>` (2026-07-22)

**Decision:** A avaliação física do paciente é um **item time-series** sob a PK do paciente (`PK=CLINIC#<clinicId>#CLIENT#<pacienteId>`, `SK=AVALIACAO#<id>`), permitindo **várias avaliações no tempo** (histórico/evolução). A identidade é a `data` (obrigatória, default hoje) + um `id` uuid. Optou-se por `SK=AVALIACAO#<id>` (id no SK, como aparelhos) em vez de `SK=AVALIACAO#<data>` — mantém GET/PUT/DELETE por id triviais e evita colisão de duas avaliações no mesmo dia; a ordenação por data é feita na aplicação (volume por paciente é baixo). Blocos `avaliacaoPostural` e `medidas` são **MAPs aninhados** (AD-009). Todos os campos clínicos são texto livre e opcionais (cadastro flexível). Campos definidos pelo cliente.
**Reason:** Casa com o modelo centrado no cliente (AD-005) — "evolução do paciente" = 1 Query por PK + `begins_with`. Endpoints aninhados em `/pacientes/{id}/avaliacoes` deixam a relação explícita e reaproveitam `PacienteRepository.get` para 404/isolamento.
**Trade-off:** Ordenação por data na aplicação (não no SK) — aceito no volume esperado. `data` default em UTC pode divergir do fuso BR perto da meia-noite (front deve enviar `data` explícita).
**Impact:** `schemas_avaliacao.py`, `repository_avaliacao.py`, `routers/avaliacoes.py`, fiação no `main.py`. AVL-01..10, 38 testes. Deployado na stack `clinica-pilates`.

### AD-009: Endereço do paciente como MAP (objeto aninhado), preenchido via CEP no front (2026-07-21)

**Decision:** O endereço do paciente será um **MAP** (objeto aninhado) no item DynamoDB, não um campo string único nem vários atributos soltos. Submodelo Pydantic `Endereco`:
```
endereco: { cep, logradouro, numero, complemento, bairro, cidade, uf }
```
Campo **opcional**. A consulta ao CEP (ViaCEP) é feita **no front-end** — o back apenas recebe e armazena o objeto já montado (não chama ViaCEP).
**Reason:** Casa 1-para-1 com o retorno do ViaCEP (`logradouro`, `bairro`, `localidade`, `uf`) e com o formulário do front; mantém o endereço coeso e fácil de exibir/editar; DynamoDB suporta Map nativo. Campo único perde estrutura; atributos soltos poluem o item.
**Trade-off:** Front assume a responsabilidade da consulta de CEP (aceito — evita chamada externa na Lambda).
**Impact:** `schemas.py` ganha submodelo `Endereco` (troca `endereco: Optional[str]` por `Optional[Endereco]`). Aplicar junto com o refactor multi-tenant (B-003).

### AD-008: CPF do paciente — opcional e validado (2026-07-21)

**Decision:** Adicionar `cpf` ao paciente. Campo **opcional**, mas **validado** quando informado (11 dígitos + dígitos verificadores, não só tamanho). Armazenado **normalizado** (só números); o front formata na exibição.
**Reason:** Mantém a regra de cadastro rápido (só `nome` obrigatório) sem abrir mão da integridade do dado quando o CPF é preenchido.
**Trade-off:** Não impede duplicidade por ora.
**Impact:** `schemas.py` ganha campo `cpf` + validador de dígitos verificadores. **Futuro:** CPF é bom candidato a **único por clínica** (impedir cadastro duplicado) — avaliar quando o multi-tenant existir. Aplicar junto com o refactor multi-tenant (B-003).

### AD-007: Multi-tenancy modelo pool — `clinicId` na PK (planejado, aplicar antes do M2) (2026-07-20)

**Decision:** O sistema servirá **várias clínicas** (multi-tenant) na mesma tabela/stack, modelo **pool** (compartilhado, isolamento lógico). Cada registro carrega o `clinicId` no início da partition key:
- Perfil: `PK=CLINIC#<clinicId>#CLIENT#<clientId>`, `SK=PROFILE`
- Demais itens do cliente: mesma PK, `SK=SESSION#<data>` / `MEASURE#<data>` / etc.
- Listar pacientes de uma clínica: via **GSI** (`GSI1PK=CLINIC#<clinicId>`) — substitui o `Scan` atual por `Query` escopado.

**Isolamento (o ponto crítico de segurança):** toda query filtra pelo `clinicId` **derivado do token do login** (custom claim do Cognito, M3) — **NUNCA** do corpo/params da requisição. Assim, usuário da clínica 1 pedindo id da clínica 2 → busca só dentro de `CLINIC#1` → 404. É o token + filtro server-side que garantem o isolamento, não a URL.

**Reason:** Habilita vender pra 1, 10 ou 500 clínicas sem re-arquitetura (DynamoDB e Lambda escalam sozinhos; chave por paciente já espalha a carga). Custo continua por uso. Padrão de mercado para SaaS serverless.
**Trade-off:** Isolamento lógico (não físico) — exige disciplina de sempre filtrar por tenant. Cresce a necessidade de features de produto (onboarding de clínica, billing por clínica, super-admin), que são módulos por cima, não re-arquitetura.
**Impact:** Revisa a convenção de chaves do AD-005 (prefixa `CLINIC#<clinicId>#`). Deve ser aplicado **antes** do M2 para evitar migração de dados (ver B-003). Até o Cognito (M3), usar um `clinicId` "default" fixo já deixa o modelo pronto.

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

### AD-006: Build da Lambda via `sam build --use-container` (Docker como ferramenta de build) (2026-07-18)

**Decision:** Usar Docker apenas como ferramenta de build local (`sam build --use-container`) para gerar wheels Linux (manylinux) das dependências nativas. A entrega continua sendo ZIP.
**Reason:** `pydantic-core` (dep do FastAPI) é nativo/compilado; build no Windows gera wheel incompatível com o Lambda (Linux). O container replica o ambiente do Lambda e resolve as wheels corretas. Python local é 3.14, sem 3.13 no PATH — o container também elimina esse requisito.
**Trade-off:** Precisa do Docker Desktop rodando para buildar. Não fere a decisão original ("sem Docker" referia-se ao modelo de entrega — ZIP em vez de imagem container/Fargate).
**Impact:** Fluxo de deploy: abrir Docker Desktop → `sam build --use-container` → `sam deploy`. Resolve o restante do B-002.

### AD-005: Manter DynamoDB com single-table design centrado no cliente (2026-07-18)

**Decision:** Confirmado DynamoDB (não migrar para relacional). Modelo single-table onde tudo pende do cliente. Convenção de chaves compartilhada por todas as features:
- Perfil: `PK=CLIENT#<id>`, `SK=PROFILE`
- Medida corporal: `PK=CLIENT#<id>`, `SK=MEASURE#<ISO-date>`
- Pressão arterial: `PK=CLIENT#<id>`, `SK=BP#<ISO-date>`
- Aula/sessão: `PK=CLIENT#<id>`, `SK=SESSION#<ISO-date>` (com lista denormalizada de exercícios/procedimentos)
- Consulta: `PK=CLIENT#<id>`, `SK=CONSULT#<ISO-date>`

> ⚠️ **ATUALIZADO por AD-007 (multi-tenant, 2026-07-21):** a PK agora carrega o prefixo da clínica —
> `PK=CLINIC#<clinicId>#CLIENT#<clientId>`. Os SKs acima permanecem iguais. Toda feature nova (M2+)
> deve usar essa PK. Listagem de pacientes de uma clínica via GSI1 (`GSI1PK=CLINIC#<clinicId>`).
- Catálogo de exercícios: `PK=EXERCISE`, `SK=EX#<id>`
**Reason:** Os dados são centrados no cliente e em série temporal (medidas, pressão, aulas, consultas). "Última aula" e "evolução do paciente" são queries nativas do DynamoDB (Query por PK + range no SK). Schema-less facilita adicionar novos tipos (ex: consultas) sem migração. Mantém meta de custo $0–5/mês.
**Trade-off:** Relatórios cruzados entre pacientes (agregações da clínica inteira) exigem GSI ou exportação — aceito por ora; o sistema é uma ficha por paciente.
**Impact:** Todas as feature specs referenciam esta convenção de chaves. Reverte a avaliação anterior que considerava Aurora/relacional.

---

## Active Blockers

### B-003: Ajustar convenção de chaves para multi-tenant ANTES do M2 — ✅ RESOLVIDO (2026-07-21)

**Discovered:** 2026-07-20 (dúvida do usuário sobre vender para várias clínicas)
**Impact:** O `clinicId` faz parte da partition key (AD-007). Sem isso antes do M2, haveria migração de dados depois.
**Resolution:** Refactor R1–R4 aplicado e deployado em 2026-07-21. Chave `PK=CLINIC#<clinicId>#CLIENT#<clientId>` + GSI1 de listagem por clínica. Estratégia escolhida: **cliente-na-PK + GSI** (preserva "ficha do paciente = 1 Query por PK", AD-005) — descartado o clínica-na-PK. `clinicId` vem de `get_clinic_id` (header `X-Clinic-Id` / default hoje; token Cognito no M3). Junto foram aplicados AD-008 (cpf) e AD-009 (endereço MAP). 61 tests + smoke-test público de isolamento OK. M2 pode ser construído já multi-tenant.

### B-001: SAM CLI não instalado — ✅ RESOLVIDO (2026-07-18)

**Discovered:** 2026-07-18
**Impact:** Bloqueava `sam build`/`sam deploy` da feature Infra Base.
**Resolution:** SAM CLI 1.163.0 instalado (via winget). Deploy destravado. Pendente ainda: confirmar credenciais AWS (`aws sts get-caller-identity`) antes da T6.

### B-002: Python local 3.14 vs runtime Lambda — ✅ RESOLVIDO (via AD-006)

**Discovered:** 2026-07-18
**Impact:** `sam build` local falhou: (1) sem python3.13 no PATH; (2) mesmo com ele, wheels Windows do pydantic-core não rodam no Lambda (Linux).
**Resolution:** Decidido (AD-006) usar `sam build --use-container` — o container Linux gera as wheels manylinux corretas e dispensa python3.13 local. Pré-requisito: Docker Desktop rodando (instalado v29.3.1, precisa estar aberto).

---

## Lessons Learned

### LL-001: "Textos estranhos" no front podem ser tradução automática do navegador (2026-07-24)

Usuário reportou o link aparecendo como "removedor" (print) enquanto o código/bundle diziam "remover". Causa: **tradução automática do Chrome** reescrevendo a página PT→PT. Antes de "corrigir" um texto que já está certo no código, **conferir o bundle no ar** (`curl <site>/assets/index-*.js | grep`) e lembrar dessa hipótese. Solução do lado do usuário: desativar tradução automática da página.

---

## Quick Tasks Completed

| #   | Description | Date | Commit | Status |
| --- | ----------- | ---- | ------ | ------ |

---

## Deferred Ideas

- [ ] Upload de fotos/laudos/anexos por paciente (S3) — Captured during: inicialização
- [ ] Relatórios de uso de aparelhos — Captured during: inicialização
- [ ] **Papéis/permissões dentro da clínica (roles via Cognito groups)** — ex.: recepcionista vê pacientes mas não edita; fisioterapeuta vê tudo. Camada ADICIONAL à do `clinicId` (que já isola entre clínicas). Refinamento pós-M3. — Captured during: discussão multi-tenant (2026-07-21)
- [ ] **Onboarding de nova clínica** (self-service) — tela que cria o `clinicId` + primeiro usuário admin da clínica. Necessário para virar SaaS de fato. — Captured during: discussão multi-tenant (2026-07-21)

---

## Todos

- [ ] Especificar frontend via spec "impecable" (M4)
- [ ] **M3 (login/Cognito) — trocar a fonte do `clinicId`:** hoje `get_clinic_id()` (em `src/app/routers/pacientes.py`) lê o header temporário `X-Clinic-Id` (andaime inseguro). No M3, passar a extrair o `clinicId` do **token** do usuário logado (custom claim do Cognito, gravado na conta na criação). **Só essa função muda** — endpoints e repositório continuam iguais. Autenticação (validar assinatura/expiração do token) fica no API Gateway + Cognito, antes da Lambda. Duas camadas: autenticação ("quem é você" = Cognito) + autorização/isolamento ("só a sua clínica" = filtro pelo `clinicId` do token, já pronto).

---

## Preferences

**Model Guidance Shown:** never
